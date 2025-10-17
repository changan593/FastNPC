# -*- coding: utf-8 -*-
"""
认证核心功能

提供用户注册、登录验证、Cookie 管理等核心认证功能。
"""

from __future__ import annotations

import time
import psycopg2
from typing import Optional, Tuple, Dict, Any

from passlib.hash import bcrypt
from itsdangerous import URLSafeSerializer, BadSignature

from fastnpc.api.auth.db_utils import _get_conn, _row_to_dict
from fastnpc.config import FASTNPC_SECRET, FASTNPC_ADMIN_USER, USE_POSTGRESQL


def _signer() -> URLSafeSerializer:
    return URLSafeSerializer(secret_key=FASTNPC_SECRET, salt='fastnpc-cookie')


def create_user(username: str, password: str) -> Tuple[bool, str]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        is_admin = 1 if (FASTNPC_ADMIN_USER and username == FASTNPC_ADMIN_USER) else 0
        cur.execute(
            "INSERT INTO users(username, password_hash, created_at, is_admin) VALUES(%s,%s,%s,%s)",
            (username, bcrypt.hash(password), int(time.time()), is_admin),
        )
        conn.commit()
        return True, 'ok'
    except (psycopg2.IntegrityError if USE_POSTGRESQL else Exception):
        return False, '用户名已存在'
    finally:
        conn.close()


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        if not row:
            return None
        
        row_dict = _row_to_dict(row, cur)
        if not bcrypt.verify(password, row_dict['password_hash']):
            return None
        return {"id": row_dict['id'], "username": row_dict['username'], "is_admin": int(row_dict['is_admin'])}
    finally:
        conn.close()


def issue_cookie(user_id: int, username: str) -> str:
    s = _signer()
    return s.dumps({"uid": user_id, "u": username, "t": int(time.time())})


def verify_cookie(token: str) -> Optional[Dict[str, Any]]:
    s = _signer()
    try:
        data = s.loads(token)
        return data
    except BadSignature:
        return None

