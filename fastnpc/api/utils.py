# -*- coding: utf-8 -*-
"""
工具函数模块：提供各种辅助功能
"""
from __future__ import annotations

import os
import json
import uuid
import fcntl
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Request, HTTPException

from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.auth import (
    verify_cookie, list_users, get_or_create_character, update_character_structured,
    load_character_full_data, get_character_id, save_character_memories, load_character_memories
)
from fastnpc.pipeline.structure import build_system_prompt
from fastnpc.api.state import sessions, sessions_lock
from fastnpc.api.cache import get_redis_cache


CHAR_DIR_STR = CHAR_DIR.as_posix()

# 缓存键前缀
CACHE_KEY_CHARACTER_PROFILE = "char_profile"
CACHE_KEY_CHARACTER_LIST = "char_list"


def _load_character_profile(role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """从数据库加载角色profile（带Redis缓存），失败则尝试从文件加载（向后兼容）
    
    返回格式与原来的 structured JSON 一致
    """
    cache = get_redis_cache()
    cache_key = f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{normalize_role_name(role)}"
    
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
    try:
        path = _structured_path_for_role(normalize_role_name(role), user_id=user_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                profile = json.load(f)
                # 文件加载的也缓存起来
                cache.set(cache_key, profile, ttl=300)
                return profile
    except Exception as e:
        print(f"[WARN] 从文件加载角色失败: {e}")
    
    return None


def _require_user(request: Request) -> Optional[Dict[str, Any]]:
    """验证用户身份"""
    token = request.cookies.get('fastnpc_auth', '')
    if not token:
        return None
    data = verify_cookie(token)
    return data


def _require_admin(request: Request) -> Optional[Dict[str, Any]]:
    """验证管理员权限"""
    data = _require_user(request)
    if not data:
        return None
    # 读取 DB 校验 is_admin
    try:
        users = list_users()
        for u in users:
            if int(u['id']) == int(data.get('uid')):
                return data if int(u.get('is_admin', 0)) == 1 else None
    except Exception:
        pass
    return None


def _structured_path_for_role(role: str, user_id: Optional[int] = None) -> str:
    """获取角色结构化文件的路径"""
    # 兼容 Test/test_structure.run 的命名：
    # - zhwiki 输入 -> structured_<role>.json（去掉前缀）
    # - baike 输入  -> structured_baike_<role>.json（未去掉）
    base = CHAR_DIR_STR if not user_id else os.path.join(CHAR_DIR_STR, str(user_id))
    candidates = [
        os.path.join(base, f"structured_{role}.json"),
        os.path.join(base, f"structured_baike_{role}.json"),
        os.path.join(base, f"structured_zhwiki_{role}.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 默认回落
    return candidates[0]


def _list_structured_files(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """从数据库列出用户的所有角色（带Redis缓存）"""
    cache = get_redis_cache()
    cache_key = f"{CACHE_KEY_CHARACTER_LIST}:{user_id}"
    
    # 尝试从缓存获取
    cached = cache.get(cache_key)
    if cached is not None:
        print(f"[DEBUG] _list_structured_files: 从缓存返回 {len(cached)} 个角色")
        return cached
    
    # 缓存未命中，查询数据库
    items: List[Dict[str, Any]] = []
    conn = None
    try:
        from fastnpc.api.auth import _get_conn, _row_to_dict
        from fastnpc.config import USE_POSTGRESQL
        
        print(f"[DEBUG] _list_structured_files: user_id={user_id}, USE_POSTGRESQL={USE_POSTGRESQL}")
        
        conn = _get_conn()
        cur = conn.cursor()
        
        # 构建查询（兼容PostgreSQL和SQLite）
        placeholder = "%s" if USE_POSTGRESQL else "?"
        if user_id:
            query = f"SELECT id, name, updated_at, avatar_url, is_test_case FROM characters WHERE user_id = {placeholder} ORDER BY updated_at DESC"
            print(f"[DEBUG] Executing query: {query} with user_id={user_id}")
            cur.execute(query, (user_id,))
        else:
            query = "SELECT id, name, updated_at, avatar_url, is_test_case FROM characters ORDER BY updated_at DESC"
            print(f"[DEBUG] Executing query: {query}")
            cur.execute(query)
        
        rows = cur.fetchall()
        # 保存列名，因为后续查询会改变cursor.description
        column_names = [desc[0] for desc in cur.description]
        print(f"[DEBUG] Found {len(rows)} characters, columns: {column_names}")
        
        for row in rows:
            try:
                # 手动转换tuple到dict
                if USE_POSTGRESQL:
                    row_dict = dict(zip(column_names, row))
                else:
                    row_dict = dict(row)
                    
                char_id = row_dict['id']
                role = row_dict['name']
                # 确保updated_at是整数
                updated_at = int(row_dict['updated_at']) if row_dict.get('updated_at') else 0
                avatar_url = row_dict.get('avatar_url', '')
                # 获取is_test_case字段（处理PostgreSQL boolean和SQLite integer）
                is_test_case_raw = row_dict.get('is_test_case')
                is_test_case = bool(is_test_case_raw) if is_test_case_raw is not None else False
                
                print(f"[DEBUG] Processing character: {role} (id={char_id}, updated_at={updated_at}, avatar_url={avatar_url}, is_test_case={is_test_case})")
                
                # 获取简介预览
                preview = ""
                try:
                    cur.execute(f"SELECT brief_intro FROM character_basic_info WHERE character_id = {placeholder}", (char_id,))
                    basic_row = cur.fetchone()
                    if basic_row:
                        # 直接访问第一个元素（brief_intro）
                        brief = basic_row[0] if basic_row else None
                        if brief and isinstance(brief, str):
                            preview = brief.strip().replace("\n", " ")
                            if len(preview) > 140:
                                preview = preview[:140] + "…"
                except Exception as e:
                    print(f"[DEBUG] Failed to get preview for {role}: {e}")
                
                items.append({
                    "role": role,
                    "path": f"db://characters/{char_id}",
                    "updated_at": updated_at,
                    "preview": preview,
                    "avatar_url": avatar_url or "",
                    "is_test_case": is_test_case,
                })
            except Exception as e:
                print(f"[ERROR] 处理角色数据失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[DEBUG] Returning {len(items)} items")
        
        # 保存到缓存（1分钟TTL）
        cache.set(cache_key, items, ttl=60)
        
    except Exception as e:
        print(f"[ERROR] 从数据库列出角色失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
    
    return items


def _update_long_term_memory(role: str, uid: int, mem_context_text: str) -> Optional[str]:
    """将 Mem0 检索得到的上下文写入数据库的 "知识与能力.长期记忆"，并返回最新的 system 提示。"""
    try:
        role = normalize_role_name(role)
        
        # 从数据库获取角色ID和数据
        character_id = get_character_id(uid, role)
        if not character_id:
            return None
        
        # 从数据库加载完整数据
        prof = load_character_full_data(character_id)
        if not prof:
            return None
        
        know = prof.get("知识与能力")
        if not isinstance(know, dict):
            know = {}
        
        # 读取既有长期记忆
        existing = know.get("长期记忆")
        existing_list: List[str]
        if isinstance(existing, list):
            existing_list = [str(x).strip() for x in existing if str(x).strip()]
        elif isinstance(existing, str):
            # 按行切分，兼容以 "- " 开头的项目
            existing_list = []
            for line in existing.splitlines():
                line = str(line).strip()
                if not line:
                    continue
                if line.startswith("- "):
                    line = line[2:].strip()
                existing_list.append(line)
        else:
            existing_list = []
        
        # 新增项
        new_items: List[str] = []
        for line in str(mem_context_text or "").splitlines():
            line = str(line).strip()
            if not line:
                continue
            if line.startswith("- "):
                line = line[2:].strip()
            new_items.append(line)
        
        # 合并去重（保持顺序，限制长度）
        merged: List[str] = []
        for x in [*existing_list, *new_items]:
            if x and x not in merged:
                merged.append(x)
        if len(merged) > 400:
            merged = merged[-400:]
        
        # 更新数据
        know["长期记忆"] = merged
        prof["知识与能力"] = know
        
        # 保存到数据库（移除内部元数据）
        structured_data = {k: v for k, v in prof.items() if k not in ['_metadata', 'baike_content']}
        save_character_full_data(
            user_id=uid,
            name=role,
            structured_data=structured_data,
            baike_content=None  # 不更新百科内容
        )
        
        # 返回最新 system 提示
        return build_system_prompt(prof)
    except Exception as e:
        print(f"[ERROR] 更新长期记忆失败: {e}")
        return None


def _truncate_structured_profile_text(profile: Dict[str, Any], limit_chars: int) -> Dict[str, Any]:
    """将结构化 JSON（不含长期记忆）随机丢弃一些键，直到字符串化后长度小于限制。"""
    import json as _json
    if limit_chars <= 0:
        return profile
    # 复制并去掉长期记忆
    from copy import deepcopy
    prof = deepcopy(profile)
    try:
        know = prof.get("知识与能力")
        if isinstance(know, dict) and "长期记忆" in know:
            know.pop("长期记忆", None)
    except Exception:
        pass
    s = _json.dumps(prof, ensure_ascii=False)
    if len(s) <= limit_chars:
        return prof
    # 可删分区（按顶层键随机移除）
    import random
    keys = [k for k in prof.keys() if k in [
        "基础身份信息", "个性与行为设定", "背景故事", "知识与能力", "对话与交互规范", "任务/功能性信息", "环境与世界观", "系统与控制参数"
    ]]
    random.shuffle(keys)
    for k in keys:
        try:
            prof.pop(k, None)
        except Exception:
            pass
        s = _json.dumps(prof, ensure_ascii=False)
        if len(s) <= limit_chars:
            break
    return prof


def _truncate_messages(messages: List[Dict[str, str]], limit_chars: int) -> List[Dict[str, str]]:
    """裁剪消息历史，保持在字符限制内"""
    if limit_chars <= 0:
        return messages
    import json as _json
    from collections import deque
    dq = deque(messages)
    while dq:
        s = _json.dumps(list(dq), ensure_ascii=False)
        if len(s) <= limit_chars:
            break
        # 丢弃最早的一条（保留 system/角色提示在会话外单独传入）
        left = dq[0]
        # 避免误删 system，如最左是 system 则跳过该条，删下一条
        if isinstance(left, dict) and left.get("role") == "system" and len(dq) >= 2:
            dq.popleft()
        dq.popleft()
    return list(dq)


def _truncate_long_term_memory(items: List[str], limit_chars: int) -> List[str]:
    """裁剪长期记忆，保持在字符限制内"""
    if limit_chars <= 0:
        return items
    import json as _json
    import random
    arr = list(items)
    # 根据索引越小（越早）被删概率越高的策略进行加权随机删减
    while arr:
        s = _json.dumps(arr, ensure_ascii=False)
        if len(s) <= limit_chars:
            break
        n = len(arr)
        # 权重：w_i = (n - i) 的反比，越早越大权重
        weights = [float(n - i) for i in range(n)]
        # 但我们想"越早越大概率被删"，因此选择 i=0 更容易选中
        # 转为概率
        total = sum(weights)
        probs = [w / total for w in weights]
        # 随机选择一个索引删除
        r = random.random()
        acc = 0.0
        idx = 0
        for i, p in enumerate(probs):
            acc += p
            if r <= acc:
                idx = i
                break
        arr.pop(idx)
    return arr


def _estimate_text_len(text: str) -> int:
    """估算文本长度"""
    return len(text or "")


def _ensure_chat_session_for_role(role: str, user_id: Optional[int] = None) -> str:
    """确保指定角色的聊天会话存在，返回 session_id"""
    with sessions_lock:
        for sid, sess in sessions.items():
            if sess.get("role") == role and sess.get("user_id") == user_id:
                return sid
    # 新建
    role = normalize_role_name(role)
    # 从数据库加载角色profile（自动降级到文件）
    profile = _load_character_profile(role, user_id) if user_id else None
    if not profile:
        # 尝试文件加载（兼容）
        path = _structured_path_for_role(role, user_id=user_id)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="角色不存在")
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    system_prompt = build_system_prompt(profile)
    sid = uuid.uuid4().hex
    with sessions_lock:
        sessions[sid] = {"messages": [{"role": "system", "content": system_prompt}], "role": role, "user_id": user_id}
    return sid


# ============= 记忆管理函数 =============

def _read_memories_from_profile(role: str, user_id: int) -> Tuple[List[str], List[str]]:
    """从数据库读取短期记忆和长期记忆
    
    Returns:
        (short_term_memories, long_term_memories)
    """
    try:
        role = normalize_role_name(role)
        character_id = get_character_id(user_id, role)
        if not character_id:
            return [], []
        
        # 从数据库加载记忆
        memories = load_character_memories(character_id)
        short_memories = memories.get('short_term', [])
        long_memories = memories.get('long_term', [])
        
        return short_memories, long_memories
    except Exception as e:
        print(f"[ERROR] 读取记忆失败: {e}")
        return [], []


def _write_memories_to_profile(
    role: str,
    user_id: int,
    short_memories: Optional[List[str]] = None,
    long_memories: Optional[List[str]] = None
) -> None:
    """写入记忆到数据库
    """
    try:
        role = normalize_role_name(role)
        character_id = get_character_id(user_id, role)
        if not character_id:
            print(f"[ERROR] 角色不存在: {role}")
            return
        
        # 如果只更新部分记忆，需要先读取现有记忆
        if short_memories is None or long_memories is None:
            current_memories = load_character_memories(character_id)
            if short_memories is None:
                short_memories = current_memories.get('short_term', [])
            if long_memories is None:
                long_memories = current_memories.get('long_term', [])
        
        # 保存到数据库
        save_character_memories(character_id, short_memories, long_memories)
    except Exception as e:
        print(f"[ERROR] 写入记忆失败: {e}")


def _append_short_term_memory(role: str, user_id: int, new_memories: List[str]) -> None:
    """追加短期记忆（按时间顺序）"""
    try:
        stm, ltm = _read_memories_from_profile(role, user_id)
        # 追加新记忆到末尾
        stm.extend(new_memories)
        _write_memories_to_profile(role, user_id, short_memories=stm)
    except Exception as e:
        print(f"[ERROR] 追加短期记忆失败: {e}")


def _append_long_term_memory(role: str, user_id: int, new_memories: List[str]) -> None:
    """追加长期记忆（按时间顺序）"""
    try:
        stm, ltm = _read_memories_from_profile(role, user_id)
        # 追加新记忆到末尾
        ltm.extend(new_memories)
        _write_memories_to_profile(role, user_id, long_memories=ltm)
    except Exception as e:
        print(f"[ERROR] 追加长期记忆失败: {e}")


def _get_role_summary(role: str, user_id: int) -> str:
    """从数据库提取角色简介（用于长期记忆整合）"""
    try:
        role = normalize_role_name(role)
        
        # 从数据库加载角色profile（带缓存）
        prof = _load_character_profile(role, user_id)
        if not prof:
            return "角色简介缺失"
        
        # 优先从基础身份信息获取
        base_info = prof.get("基础身份信息", {})
        if isinstance(base_info, dict):
            summary = base_info.get("人物简介") or base_info.get("简介") or base_info.get("自我描述") or base_info.get("brief_intro")
            if summary:
                return str(summary).strip()
        
        # 兜底：从顶层获取
        summary = prof.get("简介") or prof.get("summary") or prof.get("人物摘要")
        if summary:
            return str(summary).strip()
        
        return f"{role} 的角色画像"
    except Exception as e:
        print(f"[ERROR] 获取角色简介失败: {e}")
        return "角色简介缺失"

