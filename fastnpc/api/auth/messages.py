# -*- coding: utf-8 -*-
"""
消息管理

提供消息添加、查询、标记压缩等消息管理功能。
"""

from __future__ import annotations

import time
from typing import List

from fastnpc.api.auth.db_utils import _get_conn, _row_to_dict
from fastnpc.config import USE_POSTGRESQL


def add_message(user_id: int, character_id: int, role: str, content: str, system_prompt_snapshot: str = None) -> int:
    """添加消息
    
    Args:
        user_id: 用户ID
        character_id: 角色ID
        role: 消息角色（user/assistant）
        content: 消息内容
        system_prompt_snapshot: 可选，保存实际发送给LLM时的system prompt（仅user消息）
    
    Returns:
        消息ID
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRESQL:
            cur.execute(
                "INSERT INTO messages(user_id, character_id, role, content, created_at, system_prompt_snapshot) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
                (user_id, character_id, role, content, int(time.time()), system_prompt_snapshot),
            )
            msg_id = int(cur.fetchone()[0])
            conn.commit()
            return msg_id
        else:
            cur.execute(
                "INSERT INTO messages(user_id, character_id, role, content, created_at, system_prompt_snapshot) VALUES(%s,%s,%s,%s,%s,%s)",
                (user_id, character_id, role, content, int(time.time()), system_prompt_snapshot),
            )
            conn.commit()
            return int(cur.lastrowid)
    finally:
        conn.close()


def list_messages(user_id: int, character_id: int, limit: int = 100, after_id: int = 0, only_uncompressed: bool = False):
    """读取消息列表
    
    Args:
        user_id: 用户ID
        character_id: 角色ID
        limit: 最多返回多少条
        after_id: 只返回id大于这个值的消息
        only_uncompressed: 是否只返回未压缩的消息（用于会话记忆）
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if only_uncompressed:
            # 只读取未压缩的消息（会话记忆）
            if after_id > 0:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=%s AND character_id=%s AND id>%s AND (compressed IS NULL OR compressed=0) ORDER BY id ASC LIMIT %s",
                    (user_id, character_id, after_id, limit),
                )
            else:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=%s AND character_id=%s AND (compressed IS NULL OR compressed=0) ORDER BY id ASC LIMIT %s",
                    (user_id, character_id, limit),
                )
        else:
            # 读取所有消息（包括已压缩的）
            if after_id > 0:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=%s AND character_id=%s AND id>%s ORDER BY id ASC LIMIT %s",
                    (user_id, character_id, after_id, limit),
                )
            else:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=%s AND character_id=%s ORDER BY id ASC LIMIT %s",
                    (user_id, character_id, limit),
                )
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_messages_as_compressed(user_id: int, character_id: int, message_ids: List[int]) -> None:
    """标记消息为已压缩
    
    Args:
        user_id: 用户ID
        character_id: 角色ID
        message_ids: 要标记的消息ID列表
    """
    if not message_ids:
        return
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 批量更新
        placeholders = ','.join(['%s'] * len(message_ids))
        sql = f"UPDATE messages SET compressed=1 WHERE user_id=%s AND character_id=%s AND id IN ({placeholders})"
        cur.execute(sql, (user_id, character_id, *message_ids))
        conn.commit()
    finally:
        conn.close()


def mark_group_messages_as_compressed(group_id: int, message_ids: List[int]) -> None:
    """标记群聊消息为已压缩
    
    Args:
        group_id: 群聊ID
        message_ids: 要标记的消息ID列表
    """
    if not message_ids:
        return
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholders = ','.join(['%s'] * len(message_ids))
        cur.execute(
            f"UPDATE group_messages SET compressed=1 WHERE group_id=%s AND id IN ({placeholders})",
            [group_id] + message_ids
        )
        conn.commit()
    finally:
        conn.close()


def update_message_system_prompt(message_id: int, system_prompt: str) -> None:
    """更新消息的system_prompt_snapshot字段（保存实际发送给LLM的system prompt）
    
    Args:
        message_id: 消息ID
        system_prompt: 实际发送给LLM的system prompt
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE messages SET system_prompt_snapshot=%s WHERE id=%s",
            (system_prompt, message_id)
        )
        conn.commit()
    finally:
        conn.close()

