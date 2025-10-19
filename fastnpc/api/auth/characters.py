# -*- coding: utf-8 -*-
"""
角色管理

提供角色创建、查询、重命名、删除等角色管理功能。
"""

from __future__ import annotations

import time
from typing import Optional, Tuple, Dict, Any

from fastnpc.api.auth.db_utils import _get_conn, _row_to_dict, _return_conn
from fastnpc.config import USE_POSTGRESQL
from fastnpc.api.cache import get_redis_cache

# 缓存键前缀
CACHE_KEY_CHARACTER_ID = "char_id"
CACHE_KEY_CHARACTER_PROFILE = "char_profile"
CACHE_KEY_CHARACTER_LIST = "char_list"


def get_or_create_character(user_id: int, name: str) -> int:
    """获取或创建角色（并更新缓存）"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            return int(row_dict['id'])
        
        now = int(time.time())
        if USE_POSTGRESQL:
            cur.execute(
                "INSERT INTO characters(user_id, name, model, source, structured_json, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (user_id, name, '', '', '', now, now),
            )
            character_id = int(cur.fetchone()[0])
            conn.commit()  # 立即提交事务
        else:
            cur.execute(
                "INSERT INTO characters(user_id, name, model, source, structured_json, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (user_id, name, '', '', '', now, now),
            )
            conn.commit()
            character_id = int(cur.lastrowid)
        
        # 清除相关缓存（创建了新角色）
        # 缓存操作失败不应该影响主流程
        try:
            cache = get_redis_cache()
            cache.delete(f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{name}")
            cache.delete(f"{CACHE_KEY_CHARACTER_LIST}:{user_id}")
        except Exception as e:
            print(f"[WARN] 清除缓存失败: {e}")
        
        return character_id
    
    except Exception as e:
        # 发生异常时回滚事务
        conn.rollback()
        raise e
    
    finally:
        # 无论如何都归还连接
        _return_conn(conn)


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
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            character_id = int(row_dict['id'])
            # 保存到缓存
            cache.set(cache_key, character_id)
            return character_id
        return None
    finally:
        _return_conn(conn)


def rename_character(user_id: int, old_name: str, new_name: str) -> Tuple[bool, str]:
    """重命名角色（并清除缓存）"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, old_name))
        row = cur.fetchone()
        if not row:
            # 如果不存在则创建
            cid = get_or_create_character(user_id, old_name)
        else:
            row_dict = _row_to_dict(row, cur)
            cid = int(row_dict['id'])
        # 检查新名是否已存在
        cur.execute("SELECT 1 FROM characters WHERE user_id=%s AND name=%s", (user_id, new_name))
        if cur.fetchone():
            return False, '新名称已存在'
        cur.execute("UPDATE characters SET name=%s, updated_at=%s WHERE id=%s", (new_name, int(time.time()), cid))
        conn.commit()
        
        # 清除所有相关缓存（旧名和新名）
        cache = get_redis_cache()
        cache.delete(f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{old_name}")
        cache.delete(f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{new_name}")
        cache.delete(f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{old_name}")
        cache.delete(f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{new_name}")
        cache.delete(f"{CACHE_KEY_CHARACTER_LIST}:{user_id}")
        
        return True, 'ok'
    finally:
        _return_conn(conn)


def delete_character(user_id: int, name: str) -> None:
    """删除角色（并清除缓存）"""
    print(f"[DEBUG] delete_character: user_id={user_id}, name={name}")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            cid = int(row_dict['id'])
            print(f"[DEBUG] delete_character: 找到角色 id={cid}")
            
            # 删除所有相关表中的数据（按照数据库实际的表名）
            # 注意：由于设置了 ON DELETE CASCADE 外键约束，理论上删除 characters 记录会自动级联删除
            # 但为了兼容旧数据库（可能没有外键约束），这里显式删除所有子表数据
            try:
                # 删除消息
                cur.execute("DELETE FROM messages WHERE user_id=%s AND character_id=%s", (user_id, cid))
                
                # 删除角色详细信息（9个分类表）
                cur.execute("DELETE FROM character_basic_info WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_knowledge WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_personality WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_dialogue_rules WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_tasks WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_worldview WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_background WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_experiences WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_relationships WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_system_params WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_source_info WHERE character_id=%s", (cid,))
                cur.execute("DELETE FROM character_memories WHERE character_id=%s", (cid,))
                
                # 从所有群聊中移除该角色（按名称匹配）
                cur.execute("DELETE FROM group_members WHERE member_type=%s AND member_name=%s", ('character', name))
                
                # 最后删除角色主记录
                cur.execute("DELETE FROM characters WHERE id=%s", (cid,))
                conn.commit()
                print(f"[DEBUG] delete_character: 数据库删除完成")
                
                # 清除所有相关缓存
                cache = get_redis_cache()
                print(f"[DEBUG] delete_character: 开始清除缓存")
                cache.delete(f"{CACHE_KEY_CHARACTER_ID}:{user_id}:{name}")
                cache.delete(f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{name}")
                cache.delete(f"{CACHE_KEY_CHARACTER_LIST}:{user_id}")
                print(f"[DEBUG] delete_character: 缓存清除完成: char_list:{user_id}")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] 删除角色失败: {e}")
                raise
    finally:
        _return_conn(conn)


def list_characters(user_id: int) -> list[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, model, source, created_at, updated_at FROM characters WHERE user_id=%s ORDER BY updated_at DESC", (user_id,))
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        _return_conn(conn)


def update_character_structured(user_id: int, name: str, structured_json: str) -> None:
    """更新角色结构化数据（并清除缓存）"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 确保角色存在
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            cid = int(row_dict['id'])
        else:
            cid = get_or_create_character(user_id, name)
        cur.execute("UPDATE characters SET structured_json=%s, updated_at=%s WHERE id=%s", (structured_json, int(time.time()), cid))
        conn.commit()
        
        # 清除角色配置缓存
        cache = get_redis_cache()
        cache.delete(f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{name}")
    finally:
        _return_conn(conn)


def get_character_detail(user_id: int, character_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, model, source, structured_json, created_at, updated_at FROM characters WHERE id=%s AND user_id=%s",
            (character_id, user_id),
        )
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None
    finally:
        _return_conn(conn)


def mark_character_as_test_case(user_id: int, character_id: int, is_test_case: bool) -> Tuple[bool, str]:
    """标记/取消标记角色为测试用例"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 验证角色属于该用户
        cur.execute("SELECT id, name FROM characters WHERE id=%s AND user_id=%s", (character_id, user_id))
        row = cur.fetchone()
        if not row:
            return False, '角色不存在或无权限'
        
        row_dict = _row_to_dict(row, cur)
        name = row_dict['name']
        
        # 更新标记（PostgreSQL 使用 boolean，SQLite 使用 integer）
        value = is_test_case if USE_POSTGRESQL else (1 if is_test_case else 0)
        cur.execute("UPDATE characters SET is_test_case=%s WHERE id=%s", (value, character_id))
        conn.commit()
        
        # 清除缓存
        cache = get_redis_cache()
        cache.delete(f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{name}")
        cache.delete(f"{CACHE_KEY_CHARACTER_LIST}:{user_id}")
        
        return True, 'ok'
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 标记测试角色失败: {e}")
        return False, str(e)
    finally:
        _return_conn(conn)


def reset_character_state(user_id: int, character_id: int) -> Tuple[bool, str, int]:
    """重置角色状态（清空对话历史和记忆）
    
    Returns:
        (success, message, deleted_count)
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 验证角色属于该用户
        cur.execute("SELECT id, name FROM characters WHERE id=%s AND user_id=%s", (character_id, user_id))
        row = cur.fetchone()
        if not row:
            return False, '角色不存在或无权限', 0
        
        row_dict = _row_to_dict(row, cur)
        name = row_dict['name']
        
        # 删除对话消息
        cur.execute("DELETE FROM messages WHERE user_id=%s AND character_id=%s", (user_id, character_id))
        message_count = cur.rowcount
        
        # 删除记忆
        cur.execute("DELETE FROM character_memories WHERE character_id=%s", (character_id,))
        memory_count = cur.rowcount
        
        conn.commit()
        
        # 清除缓存
        cache = get_redis_cache()
        cache.delete(f"{CACHE_KEY_CHARACTER_PROFILE}:{user_id}:{name}")
        
        total_deleted = message_count + memory_count
        return True, f'已清空 {message_count} 条消息和 {memory_count} 条记忆', total_deleted
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 重置角色状态失败: {e}")
        return False, str(e), 0
    finally:
        _return_conn(conn)

