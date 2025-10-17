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


def get_or_create_character(user_id: int, name: str) -> int:
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
            return int(cur.fetchone()[0])
        else:
            cur.execute(
                "INSERT INTO characters(user_id, name, model, source, structured_json, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (user_id, name, '', '', '', now, now),
            )
            conn.commit()
            return int(cur.lastrowid)
    finally:
        if not USE_POSTGRESQL:
            _return_conn(conn)
        else:
            conn.commit()
            _return_conn(conn)


def get_character_id(user_id: int, name: str) -> Optional[int]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            return int(row_dict['id'])
        return None
    finally:
        _return_conn(conn)


def rename_character(user_id: int, old_name: str, new_name: str) -> Tuple[bool, str]:
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
        return True, 'ok'
    finally:
        _return_conn(conn)


def delete_character(user_id: int, name: str) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            cid = int(row_dict['id'])
            cur.execute("DELETE FROM messages WHERE user_id=%s AND character_id=%s", (user_id, cid))
            cur.execute("DELETE FROM characters WHERE id=%s", (cid,))
            conn.commit()
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

