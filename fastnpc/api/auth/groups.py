# -*- coding: utf-8 -*-
"""
群聊功能

提供群聊创建、成员管理、消息管理等群聊相关功能。
"""

from __future__ import annotations

import time
from typing import Optional, Dict, Any

from fastnpc.api.auth.db_utils import _get_conn, _row_to_dict, _return_conn
from fastnpc.config import USE_POSTGRESQL


def create_group_chat(user_id: int, name: str) -> int:
    """创建群聊"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        now = int(time.time())
        if USE_POSTGRESQL:
            cur.execute(
                "INSERT INTO group_chats(user_id, name, created_at, updated_at) VALUES(%s,%s,%s,%s) RETURNING id",
                (user_id, name, now, now)
            )
            group_id = int(cur.fetchone()[0])
            conn.commit()
            return group_id
        else:
            cur.execute(
                "INSERT INTO group_chats(user_id, name, created_at, updated_at) VALUES(%s,%s,%s,%s)",
                (user_id, name, now, now)
            )
            conn.commit()
            return int(cur.lastrowid)
    finally:
        _return_conn(conn)


def list_group_chats(user_id: int) -> list[Dict[str, Any]]:
    """列出用户的群聊"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                gc.id, 
                gc.name, 
                gc.created_at, 
                gc.updated_at,
                COUNT(gm.id) as member_count
            FROM group_chats gc
            LEFT JOIN group_members gm ON gc.id = gm.group_id
            WHERE gc.user_id=%s 
            GROUP BY gc.id, gc.name, gc.created_at, gc.updated_at
            ORDER BY gc.updated_at DESC
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        _return_conn(conn)


def add_group_member(group_id: int, member_type: str, member_name: str, member_id: int = None) -> None:
    """添加群聊成员"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRESQL:
            # PostgreSQL 使用 ON CONFLICT DO NOTHING
            cur.execute(
                "INSERT INTO group_members(group_id, member_type, member_id, member_name, joined_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT (group_id, member_type, member_name) DO NOTHING",
                (group_id, member_type, member_id, member_name, int(time.time()))
            )
        else:
            cur.execute(
                "INSERT OR IGNORE INTO group_members(group_id, member_type, member_id, member_name, joined_at) VALUES(%s,%s,%s,%s,%s)",
                (group_id, member_type, member_id, member_name, int(time.time()))
            )
        conn.commit()
    finally:
        _return_conn(conn)


def list_group_members(group_id: int) -> list[Dict[str, Any]]:
    """列出群聊成员"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT member_type, member_id, member_name FROM group_members WHERE group_id=%s ORDER BY joined_at ASC",
            (group_id,)
        )
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        _return_conn(conn)


def add_group_message(
    group_id: int, 
    sender_type: str, 
    sender_id: int, 
    sender_name: str, 
    content: str, 
    system_prompt_snapshot: str = None,
    moderator_prompt: str = None,
    moderator_response: str = None
) -> int:
    """添加群聊消息"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRESQL:
            cur.execute(
                "INSERT INTO group_messages(group_id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (group_id, sender_type, sender_id, sender_name, content, int(time.time()), system_prompt_snapshot, moderator_prompt, moderator_response)
            )
            msg_id = int(cur.fetchone()[0])
            # 更新群聊的 updated_at
            cur.execute("UPDATE group_chats SET updated_at=%s WHERE id=%s", (int(time.time()), group_id))
            conn.commit()
            return msg_id
        else:
            cur.execute(
                "INSERT INTO group_messages(group_id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (group_id, sender_type, sender_id, sender_name, content, int(time.time()), system_prompt_snapshot, moderator_prompt, moderator_response)
            )
            conn.commit()
            msg_id = int(cur.lastrowid)
            # 更新群聊的 updated_at
            cur.execute("UPDATE group_chats SET updated_at=%s WHERE id=%s", (int(time.time()), group_id))
            conn.commit()
            return msg_id
    finally:
        _return_conn(conn)


def update_group_message_moderator_info(message_id: int, moderator_prompt: str, moderator_response: str) -> None:
    """更新群聊消息的中控判断信息"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE group_messages SET moderator_prompt=%s, moderator_response=%s WHERE id=%s",
            (moderator_prompt, moderator_response, message_id)
        )
        conn.commit()
    finally:
        _return_conn(conn)


def list_group_messages(group_id: int, limit: int = 200, only_uncompressed: bool = False) -> list[Dict[str, Any]]:
    """列出群聊消息
    
    Args:
        group_id: 群聊ID
        limit: 最多返回多少条
        only_uncompressed: 是否只返回未压缩的消息（用于会话记忆）
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if only_uncompressed:
            cur.execute(
                "SELECT id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response, compressed FROM group_messages WHERE group_id=%s AND (compressed IS NULL OR compressed=0) ORDER BY id ASC LIMIT %s",
                (group_id, limit)
            )
        else:
            cur.execute(
                "SELECT id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response, compressed FROM group_messages WHERE group_id=%s ORDER BY id ASC LIMIT %s",
                (group_id, limit)
            )
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        _return_conn(conn)


def delete_group_chat(user_id: int, group_id: int) -> None:
    """删除群聊"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 验证权限
        cur.execute("SELECT 1 FROM group_chats WHERE id=%s AND user_id=%s", (group_id, user_id))
        if not cur.fetchone():
            return
        cur.execute("DELETE FROM group_messages WHERE group_id=%s", (group_id,))
        cur.execute("DELETE FROM group_members WHERE group_id=%s", (group_id,))
        cur.execute("DELETE FROM group_chats WHERE id=%s", (group_id,))
        conn.commit()
    finally:
        _return_conn(conn)


def get_group_chat_detail(group_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """获取群聊详情（含成员列表）"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at, updated_at FROM group_chats WHERE id=%s AND user_id=%s", (group_id, user_id))
        row = cur.fetchone()
        if not row:
            return None
        result = _row_to_dict(row, cur)
        result['members'] = list_group_members(group_id)
        return result
    finally:
        _return_conn(conn)


def remove_group_member(group_id: int, member_name: str) -> None:
    """移除群聊成员"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM group_members WHERE group_id=%s AND member_name=%s", (group_id, member_name))
        conn.commit()
    finally:
        _return_conn(conn)

