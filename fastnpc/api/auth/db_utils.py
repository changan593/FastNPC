# -*- coding: utf-8 -*-
"""
数据库工具函数

提供数据库连接、行转换等基础工具函数。
支持 PostgreSQL 和 SQLite 两种数据库。

使用连接池优化性能：
- PostgreSQL: 使用 ThreadedConnectionPool
- SQLite: 直接创建连接（轻量级）
"""

from __future__ import annotations

import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional
from contextlib import contextmanager

from fastnpc.config import USE_POSTGRESQL

# 导入连接池管理
from fastnpc.api.auth.db_pool import (
    get_connection_from_pool,
    return_connection_to_pool,
    get_db_connection as pool_get_db_connection,
    DB_PATH  # 重新导出，供其他模块使用
)


def _get_conn():
    """获取数据库连接（从连接池）
    
    注意：使用完毕后必须调用 _return_conn(conn) 归还连接！
    推荐使用 get_db_connection() 上下文管理器，自动归还。
    
    Returns:
        数据库连接对象
    """
    return get_connection_from_pool()


def _return_conn(conn):
    """归还连接到连接池
    
    Args:
        conn: 数据库连接对象
    """
    return_connection_to_pool(conn)


def get_db_connection():
    """获取数据库连接上下文管理器（推荐使用）
    
    自动获取和归还连接，异常时也能正确归还。
    
    Example:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users")
            conn.commit()
        # 连接自动归还到池
    """
    return pool_get_db_connection()


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

