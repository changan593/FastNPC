# -*- coding: utf-8 -*-
"""
Redis缓存管理模块
提供统一的缓存接口，支持多Worker共享和立即失效
"""
import redis
import json
import logging
import os
from typing import Any, Optional, Dict
from functools import wraps

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

