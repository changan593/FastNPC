# -*- coding: utf-8 -*-
"""
反馈系统

提供用户反馈的创建、查询、更新、删除等功能。
"""

from __future__ import annotations

import time
from typing import Optional, Dict, Any

from fastnpc.api.auth.db_utils import _get_conn, _row_to_dict, _return_conn
from fastnpc.config import USE_POSTGRESQL


def create_feedback(user_id: int, title: str, content: str, attachments: str = None) -> int:
    """创建反馈"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        now = int(time.time())
        if USE_POSTGRESQL:
            cur.execute(
                "INSERT INTO feedbacks(user_id, title, content, attachments, status, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (user_id, title, content, attachments, 'pending', now, now)
            )
            feedback_id = int(cur.fetchone()[0])
            conn.commit()
            return feedback_id
        else:
            cur.execute(
                "INSERT INTO feedbacks(user_id, title, content, attachments, status, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (user_id, title, content, attachments, 'pending', now, now)
            )
            conn.commit()
            return int(cur.lastrowid)
    finally:
        _return_conn(conn)


def list_feedbacks(user_id: int = None, status: str = None) -> list[Dict[str, Any]]:
    """列出反馈
    
    Args:
        user_id: 如果指定，只返回该用户的反馈；否则返回所有反馈（管理员）
        status: 如果指定，只返回该状态的反馈
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        query = """
            SELECT f.id, f.user_id, u.username, f.title, f.content, f.attachments, 
                   f.status, f.admin_reply, f.created_at, f.updated_at
            FROM feedbacks f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if user_id is not None:
            query += " AND f.user_id=%s"
            params.append(user_id)
        
        if status is not None:
            query += " AND f.status=%s"
            params.append(status)
        
        query += " ORDER BY f.created_at DESC"
        
        cur.execute(query, tuple(params) if params else ())
        rows = cur.fetchall()
        if USE_POSTGRESQL:
            return [_row_to_dict(r, cur) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        _return_conn(conn)


def get_feedback_detail(feedback_id: int) -> Optional[Dict[str, Any]]:
    """获取反馈详情"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.id, f.user_id, u.username, f.title, f.content, f.attachments, 
                   f.status, f.admin_reply, f.created_at, f.updated_at
            FROM feedbacks f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.id=%s
            """,
            (feedback_id,)
        )
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None
    finally:
        _return_conn(conn)


def update_feedback_status(feedback_id: int, status: str, admin_reply: str = None) -> None:
    """更新反馈状态和管理员回复"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        now = int(time.time())
        if admin_reply:
            cur.execute(
                "UPDATE feedbacks SET status=%s, admin_reply=%s, updated_at=%s WHERE id=%s",
                (status, admin_reply, now, feedback_id)
            )
        else:
            cur.execute(
                "UPDATE feedbacks SET status=%s, updated_at=%s WHERE id=%s",
                (status, now, feedback_id)
            )
        conn.commit()
    finally:
        _return_conn(conn)


def delete_feedback(feedback_id: int) -> None:
    """删除反馈"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM feedbacks WHERE id=%s", (feedback_id,))
        conn.commit()
    finally:
        _return_conn(conn)

