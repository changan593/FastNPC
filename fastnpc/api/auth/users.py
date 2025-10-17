# -*- coding: utf-8 -*-
"""
用户管理

提供用户设置、密码修改、用户列表、账户删除等用户管理功能。
"""

from __future__ import annotations

import time
from typing import Optional, Tuple, Dict, Any

from passlib.hash import bcrypt

from fastnpc.api.auth.db_utils import _get_conn, _row_to_dict, _return_conn
from fastnpc.config import USE_POSTGRESQL
from fastnpc.api.cache import get_redis_cache

# 缓存键前缀
CACHE_KEY_USER_SETTINGS = "user_settings"


def get_user_id_by_username(username: str) -> Optional[int]:
    """根据用户名查询用户ID"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        _return_conn(conn)


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
    now = int(time.time())
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM user_settings WHERE user_id=%s", (user_id,))
        if cur.fetchone():
            cur.execute(
                "UPDATE user_settings SET default_model=%s, ctx_max_chat=%s, ctx_max_stm=%s, ctx_max_ltm=%s, profile=%s, max_group_reply_rounds=%s, updated_at=%s WHERE user_id=%s",
                (default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, now, user_id),
            )
        else:
            cur.execute(
                "INSERT INTO user_settings(user_id, default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (user_id, default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, now),
            )
        conn.commit()
        
        # 清除缓存（立即失效）
        cache = get_redis_cache()
        cache_key = f"{CACHE_KEY_USER_SETTINGS}:{user_id}"
        cache.delete(cache_key)
    finally:
        _return_conn(conn)


def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            return False, '用户不存在'
        row_dict = _row_to_dict(row, cur)
        if not bcrypt.verify(old_password, row_dict['password_hash']):
            return False, '原密码不正确'
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (bcrypt.hash(new_password), user_id))
        conn.commit()
        return True, 'ok'
    finally:
        _return_conn(conn)


def list_users() -> list[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, created_at, is_admin FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        _return_conn(conn)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, created_at, is_admin FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None
    finally:
        _return_conn(conn)


def delete_account(user_id: int) -> None:
    """删除用户账户
    
    由于数据库配置了外键约束 ON DELETE CASCADE，
    删除用户时会自动级联删除：
    - 用户的所有角色 (characters)
    - 用户的所有消息 (messages)
    - 用户的设置 (user_settings)
    - 用户的群聊 (group_chats)
    - 群聊的成员和消息 (group_members, group_messages)
    - 用户的反馈 (feedbacks)
    - 角色的所有详细信息（9个相关表）
    """
    from fastnpc.api.cache import get_redis_cache
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 清除用户相关的所有缓存
        try:
            cache = get_redis_cache()
            cache.delete(f"user_settings:{user_id}")
            cache.delete(f"char_list:{user_id}")
            # 注意：单个角色的缓存会随着角色删除自动失效（TTL 5分钟）
        except Exception as cache_err:
            print(f"[WARNING] 清除缓存失败（不影响删除）: {cache_err}")
        
        # 一条SQL搞定！数据库会自动级联删除所有相关数据
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        
        print(f"[INFO] 用户 {user_id} 及其所有相关数据已删除")
    finally:
        _return_conn(conn)

