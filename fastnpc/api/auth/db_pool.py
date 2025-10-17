# -*- coding: utf-8 -*-
"""
数据库连接池管理

使用 psycopg2.pool.ThreadedConnectionPool 实现线程安全的连接池。
支持 PostgreSQL 和 SQLite 两种数据库。
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Optional, Any

import psycopg2
from psycopg2 import pool

from fastnpc.config import (
    USE_POSTGRESQL,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    DB_PATH as CONFIG_DB_PATH,
    DB_POOL_MIN_CONN,
    DB_POOL_MAX_CONN
)


# 全局连接池实例
_pg_connection_pool: Optional[pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

DB_PATH = CONFIG_DB_PATH.as_posix()


def _create_pg_connection_pool() -> pool.ThreadedConnectionPool:
    """创建 PostgreSQL 连接池"""
    print(f"[INFO] 创建PostgreSQL连接池: minconn={DB_POOL_MIN_CONN}, maxconn={DB_POOL_MAX_CONN}")
    return pool.ThreadedConnectionPool(
        minconn=DB_POOL_MIN_CONN,
        maxconn=DB_POOL_MAX_CONN,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def get_pg_connection_pool() -> pool.ThreadedConnectionPool:
    """获取或创建 PostgreSQL 连接池（单例模式）"""
    global _pg_connection_pool
    
    if _pg_connection_pool is None:
        with _pool_lock:
            # 双重检查锁定
            if _pg_connection_pool is None:
                _pg_connection_pool = _create_pg_connection_pool()
    
    return _pg_connection_pool


def get_connection_from_pool():
    """从连接池获取连接
    
    当连接池满时，会自动等待并重试（最多等待30秒）。
    
    Returns:
        数据库连接对象
        
    Note:
        使用完毕后必须调用 return_connection_to_pool() 归还连接！
        推荐使用 get_db_connection() 上下文管理器，自动归还。
    """
    if USE_POSTGRESQL:
        pg_pool = get_pg_connection_pool()
        
        # 重试机制：连接池满时等待
        max_retries = 100  # 最多重试100次
        retry_delay = 0.05  # 每次等待50ms
        
        for attempt in range(max_retries):
            try:
                conn = pg_pool.getconn()
                
                # 验证连接是否有效
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                except Exception as e:
                    # 连接无效，归还并重新获取
                    print(f"[WARN] 连接无效，重新获取: {e}")
                    pg_pool.putconn(conn, close=True)
                    continue
                
                return conn
                
            except pool.PoolError as e:
                # 连接池耗尽
                if attempt < max_retries - 1:
                    if attempt == 0:
                        print(f"[INFO] 连接池已满，等待空闲连接... (尝试 {attempt+1}/{max_retries})")
                    import time
                    time.sleep(retry_delay)
                else:
                    # 最后一次尝试失败，抛出异常
                    raise Exception(f"连接池耗尽：等待{max_retries}秒后仍无法获取连接") from e
        
        # 理论上不会到这里
        raise Exception("无法从连接池获取连接")
        
    else:
        # SQLite 不使用连接池（轻量级，直接创建）
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def return_connection_to_pool(conn, close: bool = False):
    """将连接归还到连接池
    
    Args:
        conn: 数据库连接对象
        close: 是否关闭连接（用于连接失效的情况）
    """
    if conn is None:
        return
    
    if USE_POSTGRESQL:
        pg_pool = get_pg_connection_pool()
        pg_pool.putconn(conn, close=close)
    else:
        # SQLite 直接关闭连接
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def get_db_connection():
    """数据库连接上下文管理器（推荐使用）
    
    自动获取和归还连接，异常时也能正确归还。
    
    Example:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users")
            # ... 数据库操作 ...
            conn.commit()
        # 连接自动归还到池
    """
    conn = get_connection_from_pool()
    try:
        yield conn
    except Exception as e:
        # 异常时回滚事务
        try:
            conn.rollback()
        except Exception:
            pass
        raise e
    finally:
        # 无论是否异常，都归还连接
        return_connection_to_pool(conn)


def close_all_connections():
    """关闭所有连接池（应用关闭时调用）"""
    global _pg_connection_pool
    
    if _pg_connection_pool is not None:
        with _pool_lock:
            if _pg_connection_pool is not None:
                print("[INFO] 关闭PostgreSQL连接池")
                _pg_connection_pool.closeall()
                _pg_connection_pool = None


def get_pool_status() -> dict:
    """获取连接池状态（用于监控）
    
    Returns:
        dict: 包含连接池状态信息
    """
    if not USE_POSTGRESQL:
        return {
            "database": "SQLite",
            "pool_enabled": False
        }
    
    if _pg_connection_pool is None:
        return {
            "database": "PostgreSQL",
            "pool_enabled": True,
            "pool_created": False
        }
    
    # 注意：psycopg2.pool 没有直接获取连接数的方法
    # 这里只返回配置信息
    return {
        "database": "PostgreSQL",
        "pool_enabled": True,
        "pool_created": True,
        "min_connections": DB_POOL_MIN_CONN,
        "max_connections": DB_POOL_MAX_CONN,
    }

