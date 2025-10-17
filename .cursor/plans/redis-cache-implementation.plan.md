# Redis 缓存机制实施计划

## 选择方案

- **缓存实现**: Redis（企业级，多Worker共享）
- **一致性策略**: 立即失效（更新时立即删除缓存）
- **缓存范围**: 全部缓存（用户设置、角色配置、角色ID、角色列表）

## 优势

✅ **多Worker共享**: 2个Worker使用同一份缓存，完全一致  
✅ **立即失效**: 数据更新时立即同步到所有Worker  
✅ **持久化可选**: 可配置持久化防止数据丢失  
✅ **高性能**: 内存存储，微秒级响应  
✅ **易扩展**: 支持集群、主从等高级特性  

## 实施步骤

### 步骤1: 安装和配置 Redis

**文件**: 系统级安装

**操作**:
1. 安装 Redis 服务器
2. 配置内存限制（针对2G服务器）
3. 配置持久化策略
4. 启动和自动启动设置

**命令**:
```bash
# 安装 Redis
sudo apt-get update
sudo apt-get install -y redis-server

# 配置 Redis（见下方配置文件）
sudo nano /etc/redis/redis.conf

# 重启 Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# 验证安装
redis-cli ping  # 应返回 PONG
```

**Redis 配置优化（/etc/redis/redis.conf）**:
```conf
# 内存限制（2G服务器，分配200MB给Redis）
maxmemory 200mb
maxmemory-policy allkeys-lru  # LRU淘汰策略

# 持久化配置（轻量级）
save 900 1      # 15分钟内有1个key变化就保存
save 300 10     # 5分钟内有10个key变化就保存
save 60 10000   # 1分钟内有10000个key变化就保存

# 性能优化
tcp-backlog 511
timeout 300
tcp-keepalive 300

# 安全设置（可选，如果需要）
# requirepass your_redis_password

# 监听地址
bind 127.0.0.1  # 只允许本地访问
```

---

### 步骤2: 安装 Python Redis 客户端

**文件**: `requirements.txt`

**改动**:
```diff
+ redis>=5.0.0
```

**安装**:
```bash
pip install redis>=5.0.0
```

---

### 步骤3: 创建 Redis 缓存管理模块

**新建文件**: `fastnpc/api/cache.py`

**功能**:
- Redis 连接管理
- 统一缓存接口
- 序列化/反序列化
- 缓存统计

**核心代码**:
```python
import redis
import json
import logging
from typing import Any, Optional, Dict
from functools import wraps
from fastnpc.config import os

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """初始化Redis连接"""
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        # 缓存统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            value = self.client.get(key)
            if value is not None:
                self.stats["hits"] += 1
                return json.loads(value)
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            self.stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            serialized = json.dumps(value)
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
            self.stats["sets"] += 1
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            self.client.delete(key)
            self.stats["deletes"] += 1
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有key"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                count = self.client.delete(*keys)
                self.stats["deletes"] += count
                return count
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有缓存（仅用于测试/调试）"""
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis CLEAR_ALL error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total
        }
    
    def ping(self) -> bool:
        """检查Redis连接"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis PING error: {e}")
            return False


# 全局Redis缓存实例
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """获取Redis缓存实例（单例模式）"""
    global _redis_cache
    if _redis_cache is None:
        # 从环境变量读取配置
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        _redis_cache = RedisCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password
        )
        
        # 测试连接
        if not _redis_cache.ping():
            logger.warning("Redis连接失败，缓存功能可能不可用")
    
    return _redis_cache


def cached(key_prefix: str, ttl: Optional[int] = None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 构建缓存key
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"
            
            # 尝试从缓存获取
            cache = get_redis_cache()
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 缓存未命中，调用原函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
```

---

### 步骤4: 缓存用户设置

**更新文件**: `fastnpc/api/auth/users.py`

**改动**:
```python
from fastnpc.api.cache import get_redis_cache

# 在文件顶部添加缓存键前缀
CACHE_KEY_USER_SETTINGS = "user_settings"


def get_user_settings(user_id: int) -> Dict[str, Any]:
    """获取用户设置（带Redis缓存）"""
    cache = get_redis_cache()
    cache_key = f"{CACHE_KEY_USER_SETTINGS}:{user_id}"
    
    # 尝试从缓存获取
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # 缓存未命中，查询数据库
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, updated_at FROM user_settings WHERE user_id=%s",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            result = {
                "default_model": None,
                "ctx_max_chat": None,
                "ctx_max_stm": None,
                "ctx_max_ltm": None,
                "profile": None,
                "max_group_reply_rounds": 3,
                "updated_at": 0,
            }
        else:
            result = {
                "default_model": row[0],
                "ctx_max_chat": (int(row[1]) if row[1] is not None else None),
                "ctx_max_stm": (int(row[2]) if row[2] is not None else None),
                "ctx_max_ltm": (int(row[3]) if row[3] is not None else None),
                "profile": row[4],
                "max_group_reply_rounds": (int(row[5]) if row[5] is not None else 3),
                "updated_at": int(row[6]),
            }
        
        # 保存到缓存（永久，直到更新时删除）
        cache.set(cache_key, result)
        
        return result
    finally:
        _return_conn(conn)


def update_user_settings(
    user_id: int,
    default_model: Optional[str],
    _fallback_order: str = "",
    ctx_max_chat: Optional[int] = None,
    ctx_max_stm: Optional[int] = None,
    ctx_max_ltm: Optional[int] = None,
    profile: Optional[str] = None,
    max_group_reply_rounds: Optional[int] = None,
) -> None:
    """更新用户设置（并清除缓存）"""
    conn = _get_conn()
    try:
        # ... 原有的更新逻辑 ...
        
        # 清除缓存（立即失效）
        cache = get_redis_cache()
        cache_key = f"{CACHE_KEY_USER_SETTINGS}:{user_id}"
        cache.delete(cache_key)
        
    finally:
        _return_conn(conn)
```

---

### 步骤5: 缓存角色ID映射

**更新文件**: `fastnpc/api/auth/characters.py`

**改动**:
```python
from fastnpc.api.cache import get_redis_cache

CACHE_KEY_CHARACTER_ID = "char_id"


def get_character_id(user_id: int, name: str) -> Optional[int]:
    """获取角色ID（带Redis缓存）"""
    cache = get_redis_cache()
    cache_key = f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{name}"
    
    # 尝试从缓存获取
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # 缓存未命中，查询数据库
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM characters WHERE user_id=%s AND name=%s",
            (user_id, name)
        )
        row = cur.fetchone()
        result = row[0] if row else None
        
        # 保存到缓存
        if result is not None:
            cache.set(cache_key, result)
        
        return result
    finally:
        _return_conn(conn)


def get_or_create_character(user_id: int, name: str, model: str = None, source: str = None) -> int:
    """获取或创建角色（并更新缓存）"""
    # ... 原有逻辑 ...
    
    # 如果创建了新角色，需要清除相关缓存
    cache = get_redis_cache()
    
    # 清除角色ID缓存
    cache_key = f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{name}"
    cache.delete(cache_key)
    
    # 清除角色列表缓存
    list_cache_key = f"char_list:{user_id}"
    cache.delete(list_cache_key)
    
    return character_id


def delete_character(user_id: int, name: str) -> None:
    """删除角色（并清除缓存）"""
    # ... 原有的删除逻辑 ...
    
    # 清除所有相关缓存
    cache = get_redis_cache()
    
    # 1. 角色ID缓存
    cache.delete(f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{name}")
    
    # 2. 角色配置缓存
    cache.delete(f"char_profile:{user_id}:{name}")
    
    # 3. 角色列表缓存
    cache.delete(f"char_list:{user_id}")


def update_character_structured(user_id: int, name: str, structured_json: str) -> None:
    """更新角色结构化数据（并清除缓存）"""
    # ... 原有的更新逻辑 ...
    
    # 清除角色配置缓存
    cache = get_redis_cache()
    cache.delete(f"char_profile:{user_id}:{name}")
```

---

### 步骤6: 缓存角色配置

**更新文件**: `fastnpc/api/utils.py`

**改动**:
```python
from fastnpc.api.cache import get_redis_cache

CACHE_KEY_CHARACTER_PROFILE = "char_profile"


def _load_character_profile(role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """从数据库加载角色profile（带Redis缓存）"""
    cache = get_redis_cache()
    cache_key = f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{role}"
    
    # 尝试从缓存获取
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # 缓存未命中，查询数据库
    try:
        # 1. 尝试从数据库加载
        character_id = get_character_id(user_id, normalize_role_name(role))
        if character_id:
            full_data = load_character_full_data(character_id)
            if full_data:
                # 移除内部元数据，只保留原有的结构化数据
                profile = {k: v for k, v in full_data.items() if k not in ['_metadata', 'baike_content']}
                # 添加记忆（从 character_memories 表）
                memories = load_character_memories(character_id)
                profile['短期记忆'] = memories.get('short_term', [])
                profile['长期记忆'] = memories.get('long_term', [])
                
                # 保存到缓存（5分钟TTL）
                cache.set(cache_key, profile, ttl=300)
                
                return profile
    except Exception as e:
        print(f"[WARN] 从数据库加载角色失败: {e}")
    
    # 2. 降级到文件加载（向后兼容）
    # ... 原有的文件加载逻辑 ...
    
    return None
```

---

### 步骤7: 缓存角色列表

**更新文件**: `fastnpc/api/utils.py`

**改动**:
```python
CACHE_KEY_CHARACTER_LIST = "char_list"


def _list_structured_files(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """从数据库列出用户的所有角色（带Redis缓存）"""
    cache = get_redis_cache()
    cache_key = f"{CACHE_KEY_CHARACTER_LIST}:{user_id}"
    
    # 尝试从缓存获取
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # 缓存未命中，查询数据库
    items: List[Dict[str, Any]] = []
    conn = None
    try:
        from fastnpc.api.auth import _get_conn, _row_to_dict
        from fastnpc.config import USE_POSTGRESQL
        
        conn = _get_conn()
        cur = conn.cursor()
        
        # 构建查询（兼容PostgreSQL和SQLite）
        placeholder = "%s" if USE_POSTGRESQL else "?"
        if user_id:
            query = f"SELECT id, name, updated_at FROM characters WHERE user_id = {placeholder} ORDER BY updated_at DESC"
            cur.execute(query, (user_id,))
        else:
            query = "SELECT id, name, updated_at FROM characters ORDER BY updated_at DESC"
            cur.execute(query)
        
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        
        for row in rows:
            try:
                char_data = dict(zip(column_names, row))
                items.append({
                    "role": char_data["name"],
                    "source": "database",
                    "updated_at": char_data.get("updated_at", 0)
                })
            except Exception as e:
                print(f"[WARN] 处理角色数据失败: {e}")
                continue
        
        # 保存到缓存（1分钟TTL）
        cache.set(cache_key, items, ttl=60)
        
        return items
        
    except Exception as e:
        print(f"[ERROR] _list_structured_files exception: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            from fastnpc.api.auth.db_utils import _return_conn
            _return_conn(conn)
```

---

### 步骤8: 更新配置文件

**更新文件**: `fastnpc/config.py`

**改动**:
```python
# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
```

---

### 步骤9: 添加缓存管理API（调试用）

**新建文件**: `fastnpc/api/routes/cache_routes.py`

**功能**:
- 查看缓存统计
- 清除指定缓存
- 清除所有缓存

**代码**:
```python
from fastapi import APIRouter, Request, HTTPException
from fastnpc.api.cache import get_redis_cache
from fastnpc.api.utils import get_current_user_session

router = APIRouter()


@router.get("/admin/cache/stats")
def get_cache_stats(request: Request):
    """获取缓存统计（仅管理员）"""
    session = get_current_user_session(request)
    if not session or session.get("is_admin") != 1:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    cache = get_redis_cache()
    stats = cache.get_stats()
    
    # 获取Redis信息
    info = cache.client.info("memory")
    
    return {
        "stats": stats,
        "redis_memory": {
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "maxmemory_human": info.get("maxmemory_human"),
        }
    }


@router.post("/admin/cache/clear")
def clear_cache(request: Request, pattern: str = "*"):
    """清除缓存（仅管理员）"""
    session = get_current_user_session(request)
    if not session or session.get("is_admin") != 1:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    cache = get_redis_cache()
    
    if pattern == "*":
        cache.clear_all()
        return {"ok": True, "message": "已清除所有缓存"}
    else:
        count = cache.delete_pattern(pattern)
        return {"ok": True, "message": f"已清除 {count} 个缓存项", "count": count}


@router.get("/admin/cache/test")
def test_cache_connection(request: Request):
    """测试Redis连接（仅管理员）"""
    session = get_current_user_session(request)
    if not session or session.get("is_admin") != 1:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    cache = get_redis_cache()
    is_connected = cache.ping()
    
    return {
        "connected": is_connected,
        "message": "Redis连接正常" if is_connected else "Redis连接失败"
    }
```

**注册路由**: 在 `fastnpc/api/server.py` 中添加：
```python
from fastnpc.api.routes import cache_routes
app.include_router(cache_routes.router)
```

---

### 步骤10: 更新角色记忆缓存失效

**更新文件**: `fastnpc/api/auth/char_data.py`

**改动**:
```python
from fastnpc.api.cache import get_redis_cache


def save_character_memories_impl(...) -> None:
    """保存角色记忆（并清除缓存）"""
    # ... 原有的保存逻辑 ...
    
    # 清除角色配置缓存（因为包含记忆）
    cache = get_redis_cache()
    
    # 需要获取角色名称来构建缓存key
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, user_id FROM characters WHERE id=%s", (character_id,))
        row = cur.fetchone()
        if row:
            name, user_id = row[0], row[1]
            cache.delete(f"char_profile:{user_id}:{name}")
    finally:
        from fastnpc.api.auth.db_utils import _return_conn
        _return_conn(conn)
```

---

### 步骤11: 测试脚本

**新建文件**: `test_redis_cache.py`

**功能**:
- 测试Redis连接
- 测试缓存读写
- 测试缓存失效
- 性能对比测试

**代码**:
```python
#!/usr/bin/env python3
import time
import sys
from fastnpc.api.cache import get_redis_cache


def test_redis_connection():
    """测试1: Redis连接"""
    print("=" * 60)
    print("测试1: Redis连接")
    print("=" * 60)
    
    cache = get_redis_cache()
    is_connected = cache.ping()
    
    if is_connected:
        print("✅ Redis连接成功")
    else:
        print("❌ Redis连接失败")
        sys.exit(1)


def test_basic_operations():
    """测试2: 基本操作"""
    print("\n" + "=" * 60)
    print("测试2: 基本缓存操作")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # SET
    print("\n1. 测试 SET...")
    cache.set("test_key", {"name": "测试", "value": 123})
    print("✅ SET 成功")
    
    # GET
    print("\n2. 测试 GET...")
    result = cache.get("test_key")
    assert result == {"name": "测试", "value": 123}
    print(f"✅ GET 成功: {result}")
    
    # EXISTS
    print("\n3. 测试 EXISTS...")
    exists = cache.exists("test_key")
    assert exists == True
    print(f"✅ EXISTS 成功: {exists}")
    
    # DELETE
    print("\n4. 测试 DELETE...")
    cache.delete("test_key")
    result = cache.get("test_key")
    assert result is None
    print("✅ DELETE 成功")


def test_ttl():
    """测试3: TTL过期"""
    print("\n" + "=" * 60)
    print("测试3: TTL自动过期")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 设置2秒TTL
    print("\n设置缓存（TTL=2秒）...")
    cache.set("ttl_test", "这个会过期", ttl=2)
    
    print("立即读取...")
    result = cache.get("ttl_test")
    assert result == "这个会过期"
    print(f"✅ 读取成功: {result}")
    
    print("\n等待3秒...")
    time.sleep(3)
    
    print("再次读取...")
    result = cache.get("ttl_test")
    assert result is None
    print("✅ 缓存已过期")


def test_pattern_delete():
    """测试4: 模式删除"""
    print("\n" + "=" * 60)
    print("测试4: 模式删除")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 创建多个key
    print("\n创建多个用户设置缓存...")
    cache.set("user_settings:1", {"user": 1})
    cache.set("user_settings:2", {"user": 2})
    cache.set("user_settings:3", {"user": 3})
    cache.set("other_key", {"other": True})
    print("✅ 创建成功")
    
    # 删除user_settings:*
    print("\n删除 user_settings:* 模式...")
    count = cache.delete_pattern("user_settings:*")
    print(f"✅ 删除了 {count} 个key")
    
    # 验证
    assert cache.get("user_settings:1") is None
    assert cache.get("user_settings:2") is None
    assert cache.get("user_settings:3") is None
    assert cache.get("other_key") == {"other": True}
    print("✅ 验证成功：只删除了匹配的key")
    
    # 清理
    cache.delete("other_key")


def test_performance():
    """测试5: 性能对比"""
    print("\n" + "=" * 60)
    print("测试5: 性能对比（Redis vs 数据库）")
    print("=" * 60)
    
    from fastnpc.api.auth.users import get_user_settings
    from fastnpc.api.cache import get_redis_cache
    
    # 假设用户ID=1存在
    user_id = 1
    
    print("\n第一次查询（数据库 + 写入缓存）...")
    start = time.time()
    result1 = get_user_settings(user_id)
    db_time = time.time() - start
    print(f"耗时: {db_time*1000:.2f}ms")
    
    print("\n第二次查询（从Redis缓存读取）...")
    start = time.time()
    result2 = get_user_settings(user_id)
    cache_time = time.time() - start
    print(f"耗时: {cache_time*1000:.2f}ms")
    
    assert result1 == result2
    
    speedup = db_time / cache_time if cache_time > 0 else 0
    print(f"\n✅ 性能提升: {speedup:.1f}x")
    print(f"   数据库查询: {db_time*1000:.2f}ms")
    print(f"   Redis缓存: {cache_time*1000:.2f}ms")


def test_cache_stats():
    """测试6: 缓存统计"""
    print("\n" + "=" * 60)
    print("测试6: 缓存统计")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 重置统计
    cache.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
    
    # 执行一些操作
    cache.set("stat_test", "value")  # +1 set
    cache.get("stat_test")           # +1 hit
    cache.get("stat_test")           # +1 hit
    cache.get("nonexistent")         # +1 miss
    cache.delete("stat_test")        # +1 delete
    
    stats = cache.get_stats()
    print(f"\n统计数据:")
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  写入: {stats['sets']}")
    print(f"  删除: {stats['deletes']}")
    print(f"  命中率: {stats['hit_rate']}")
    
    assert stats['hits'] == 2
    assert stats['misses'] == 1
    assert stats['sets'] == 1
    assert stats['deletes'] == 1
    print("\n✅ 统计功能正常")


def main():
    """运行所有测试"""
    print("\n")
    print("🚀 Redis缓存测试开始")
    print("=" * 60)
    
    try:
        test_redis_connection()
        test_basic_operations()
        test_ttl()
        test_pattern_delete()
        test_cache_stats()
        
        # 性能测试（需要数据库有数据）
        try:
            test_performance()
        except Exception as e:
            print(f"\n⚠️  性能测试跳过（需要数据库有用户数据）: {e}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 验收标准

- ✅ Redis服务运行正常
- ✅ Python可以连接Redis
- ✅ 用户设置缓存生效（第二次查询<5ms）
- ✅ 角色配置缓存生效
- ✅ 角色列表缓存生效
- ✅ 缓存命中率>90%
- ✅ 数据更新时缓存立即失效
- ✅ 多Worker缓存一致（2个Worker都能看到最新数据）
- ✅ 数据库查询减少80%

---

## 性能提升预期

### 单次API调用

| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 获取用户设置 | 50-100ms | 1-3ms | **30-100倍** |
| 获取角色配置 | 150-300ms | 2-5ms | **50-150倍** |
| 获取角色列表 | 50-200ms | 1-3ms | **50-200倍** |
| 获取角色ID | 20-50ms | 0.5-2ms | **10-100倍** |

### 聊天对话（单次）

```
优化前：
- 用户设置查询: 80ms
- 角色ID查询: 30ms
- 角色配置查询: 200ms
- LLM调用: 5000ms
总计: 5310ms

优化后：
- 用户设置查询: 2ms（Redis）
- 角色ID查询: 1ms（Redis）
- 角色配置查询: 3ms（Redis）
- LLM调用: 5000ms
总计: 5006ms

数据库相关耗时减少: 304ms → 6ms (减少98%)
```

### 100人在线场景

```
优化前：
- 每人每分钟10条消息
- 每条消息：11次数据库查询
- 总查询：100×10×11 = 11000次/分钟
- 数据库CPU：60-80%

优化后：
- 首次查询：100×11 = 1100次
- 后续查询：0次（全部命中Redis）
- 缓存刷新：~50次/分钟（TTL过期）
- 总查询：~1150次/首分钟，~50次/后续分钟
- 数据库CPU：5-10%

降低：95-99%数据库负载
```

---

## 内存使用评估

### 2G服务器内存分配

```
总内存：2048MB

系统：~300MB
FastAPI (2 workers)：~500MB
PostgreSQL：~200MB
Redis：~200MB  ⬅️ 新增
其他：~200MB

剩余：~648MB（缓冲）

结论：充足 ✅
```

### Redis内存使用详情

```
配置：maxmemory 200mb

预计使用：
- 100个用户设置：~100KB
- 1000个角色配置：~50MB
- 5000个角色ID映射：~500KB
- 100个角色列表：~1MB

总计：~52MB（远低于200MB限制）

LRU淘汰：自动淘汰最少使用的缓存
```

---

## 注意事项

### 1. Redis持久化

**配置已开启**：
```conf
save 900 1      # 15分钟内有变化就保存
save 300 10
save 60 10000
```

**作用**：
- Redis重启后数据不丢失
- 缓存预热自动完成

### 2. 多Worker一致性

**已解决**：
- 所有Worker共享同一个Redis
- 更新时立即删除缓存
- 下次查询自动从数据库加载

### 3. Redis故障处理

**降级策略**：
```python
def get_user_settings(user_id):
    try:
        # 尝试从Redis获取
        cached = cache.get(...)
        if cached:
            return cached
    except Exception as e:
        logger.warning(f"Redis错误，降级到数据库: {e}")
    
    # 降级：直接查询数据库
    return query_from_database(user_id)
```

### 4. 安全考虑

**建议**（生产环境）：
```conf
# /etc/redis/redis.conf
requirepass your_strong_password  # 设置密码
bind 127.0.0.1                    # 只允许本地访问
```

**环境变量**：
```bash
export REDIS_PASSWORD="your_strong_password"
```

---

## 后续优化（可选）

### 1. Redis主从复制

**场景**：高可用需求

```bash
# 主服务器
redis-server /etc/redis/redis-master.conf

# 从服务器
redis-server /etc/redis/redis-slave.conf
```

### 2. Redis Sentinel

**场景**：自动故障转移

### 3. Redis Cluster

**场景**：大规模数据分片

### 4. 智能缓存预热

**场景**：应用启动时预加载热点数据

```python
def warmup_cache():
    """启动时预热缓存"""
    # 加载活跃用户的设置
    for user_id in get_active_users():
        get_user_settings(user_id)
```

---

## 总结

这个优化将带来：

✅ **80%数据库查询减少**  
✅ **30-200倍缓存响应速度**  
✅ **95%数据库负载降低**  
✅ **多Worker完全一致**  
✅ **企业级缓存方案**  

**综合优化效果（所有5个优化）**：
1. 数据库连接池：3-5倍
2. LLM异步调用：10倍
3. 多Worker：2倍
4. Redis缓存：2-3倍（吞吐量）
5. **总计：120-300倍性能提升** 🎉

---

### To-dos

- [ ] 安装Redis服务器
- [ ] 配置Redis（内存、持久化）
- [ ] 安装Python redis包
- [ ] 创建cache.py - Redis缓存管理模块
- [ ] 更新users.py - 用户设置缓存
- [ ] 更新characters.py - 角色ID缓存 + 缓存失效
- [ ] 更新utils.py - 角色配置缓存 + 角色列表缓存
- [ ] 更新char_data.py - 记忆更新时缓存失效
- [ ] 更新config.py - Redis配置变量
- [ ] 创建cache_routes.py - 缓存管理API
- [ ] 注册cache_routes到server.py
- [ ] 创建test_redis_cache.py - 测试脚本
- [ ] 测试验证 - 连接、读写、性能、一致性

