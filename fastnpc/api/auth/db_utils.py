# -*- coding: utf-8 -*-
"""
数据库工具函数

提供数据库连接、行转换等基础工具函数。
支持 PostgreSQL 和 SQLite 两种数据库。
"""

from __future__ import annotations

import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional

from fastnpc.config import (
    DB_PATH as CONFIG_DB_PATH, 
    USE_POSTGRESQL,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD
)


DB_PATH = CONFIG_DB_PATH.as_posix()


def _get_conn():
    """获取数据库连接（支持 PostgreSQL 和 SQLite）"""
    if USE_POSTGRESQL:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        return conn
    else:
        # 保留 SQLite 支持（需要导入 sqlite3）
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _row_to_dict(row, cursor) -> Dict[str, Any]:
    """将数据库行转换为字典"""
    if USE_POSTGRESQL:
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    else:
        # SQLite Row 可以直接转换为 dict
        return dict(row) if row else None


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    if USE_POSTGRESQL:
        cursor.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=%s AND column_name=%s
            """,
            (table_name, column_name)
        )
        return cursor.fetchone() is not None
    else:
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [r[1] for r in cursor.fetchall()]
        return column_name in cols

