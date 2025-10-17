# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
from typing import Optional, Tuple, Dict, Any, List

import psycopg2
import psycopg2.extras

from passlib.hash import bcrypt
from itsdangerous import URLSafeSerializer, BadSignature
from fastnpc.config import (
    DB_PATH as CONFIG_DB_PATH, 
    FASTNPC_SECRET, 
    FASTNPC_ADMIN_USER,
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


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRESQL:
        # PostgreSQL 建表语句
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                is_admin INT NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS characters(
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                name TEXT NOT NULL,
                model TEXT,
                source TEXT,
                structured_json TEXT,
                baike_content TEXT,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                UNIQUE(user_id, name)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages(
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                character_id INT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at BIGINT NOT NULL
            )
            """
        )
    else:
        # SQLite 建表语句
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS characters(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                model TEXT,
                source TEXT,
                structured_json TEXT,
                baike_content TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(user_id, name)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
    conn.commit()
    
    # 为characters表添加baike_content字段（存储百科全文）
    try:
        if not _column_exists(cur, 'characters', 'baike_content'):
            cur.execute("ALTER TABLE characters ADD COLUMN baike_content TEXT")
            conn.commit()
    except Exception:
        pass
    
    # 为messages表添加compressed字段（标记是否已压缩为短期记忆）
    try:
        if not _column_exists(cur, 'messages', 'compressed'):
            if USE_POSTGRESQL:
                cur.execute("ALTER TABLE messages ADD COLUMN compressed INT DEFAULT 0")
            else:
                cur.execute("ALTER TABLE messages ADD COLUMN compressed INTEGER DEFAULT 0")
            conn.commit()
    except Exception:
        pass
    
    # 为messages表添加system_prompt_snapshot字段（保存实际发送时的system prompt）
    try:
        if not _column_exists(cur, 'messages', 'system_prompt_snapshot'):
            cur.execute("ALTER TABLE messages ADD COLUMN system_prompt_snapshot TEXT")
            conn.commit()
    except Exception:
        pass
    
    # 为character_source_info表添加source_info_size字段（存储百科内容字符数）
    try:
        if not _column_exists(cur, 'character_source_info', 'source_info_size'):
            if USE_POSTGRESQL:
                cur.execute("ALTER TABLE character_source_info ADD COLUMN source_info_size INT")
            else:
                cur.execute("ALTER TABLE character_source_info ADD COLUMN source_info_size INTEGER")
            conn.commit()
    except Exception:
        pass
    
    # 用户设置表：默认模型等
    if USE_POSTGRESQL:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings(
                user_id INT PRIMARY KEY,
                default_model TEXT,
                updated_at BIGINT NOT NULL
            )
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings(
                user_id INTEGER PRIMARY KEY,
                default_model TEXT,
                updated_at INTEGER NOT NULL
            )
            """
        )
    conn.commit()
    
    # 兼容老库：补充 is_admin 列
    try:
        if not _column_exists(cur, 'users', 'is_admin'):
            if USE_POSTGRESQL:
                cur.execute("ALTER TABLE users ADD COLUMN is_admin INT NOT NULL DEFAULT 0")
            else:
                cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            conn.commit()
    except Exception:
        pass
    
    # 为已有库补充 user_settings 的记忆预算字段
    try:
        to_add = []
        if not _column_exists(cur, 'user_settings', 'ctx_max_chat'):
            to_add.append("ALTER TABLE user_settings ADD COLUMN ctx_max_chat INT" if USE_POSTGRESQL else "ALTER TABLE user_settings ADD COLUMN ctx_max_chat INTEGER")
        if not _column_exists(cur, 'user_settings', 'ctx_max_stm'):
            to_add.append("ALTER TABLE user_settings ADD COLUMN ctx_max_stm INT" if USE_POSTGRESQL else "ALTER TABLE user_settings ADD COLUMN ctx_max_stm INTEGER")
        if not _column_exists(cur, 'user_settings', 'ctx_max_ltm'):
            to_add.append("ALTER TABLE user_settings ADD COLUMN ctx_max_ltm INT" if USE_POSTGRESQL else "ALTER TABLE user_settings ADD COLUMN ctx_max_ltm INTEGER")
        
        for sql in to_add:
            try:
                cur.execute(sql)
            except Exception:
                pass
        if to_add:
            conn.commit()
    except Exception:
        pass
    
    # 为 user_settings 添加 profile 字段（用户简介）
    try:
        if not _column_exists(cur, 'user_settings', 'profile'):
            cur.execute("ALTER TABLE user_settings ADD COLUMN profile TEXT")
            conn.commit()
    except Exception:
        pass
    
    # 为 user_settings 添加 max_group_reply_rounds 字段（群聊最大角色回复轮数）
    try:
        if not _column_exists(cur, 'user_settings', 'max_group_reply_rounds'):
            if USE_POSTGRESQL:
                cur.execute("ALTER TABLE user_settings ADD COLUMN max_group_reply_rounds INT DEFAULT 3")
            else:
                cur.execute("ALTER TABLE user_settings ADD COLUMN max_group_reply_rounds INTEGER DEFAULT 3")
            conn.commit()
    except Exception:
        pass
    
    # 群聊表
    if USE_POSTGRESQL:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_chats(
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                name TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            )
            """
        )
        
        # 群聊成员表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_members(
                id SERIAL PRIMARY KEY,
                group_id INT NOT NULL,
                member_type TEXT NOT NULL,
                member_id INT,
                member_name TEXT NOT NULL,
                joined_at BIGINT NOT NULL,
                UNIQUE(group_id, member_type, member_name)
            )
            """
        )
        
        # 群聊消息表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_messages(
                id SERIAL PRIMARY KEY,
                group_id INT NOT NULL,
                sender_type TEXT NOT NULL,
                sender_id INT,
                sender_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                system_prompt_snapshot TEXT,
                moderator_prompt TEXT,
                moderator_response TEXT
            )
            """
        )
        
        # 反馈表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedbacks(
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_reply TEXT,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        
        # ===== 角色详细信息表 =====
        
        # 基础身份信息
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_basic_info(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                name TEXT,
                age TEXT,
                gender TEXT,
                occupation TEXT,
                identity_background TEXT,
                appearance TEXT,
                titles TEXT,
                brief_intro TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 知识与能力
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_knowledge(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                knowledge_domain TEXT,
                skills TEXT,
                limitations TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 个性与行为设定
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_personality(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                traits TEXT,
                values TEXT,
                emotion_style TEXT,
                speaking_style TEXT,
                preferences TEXT,
                dislikes TEXT,
                motivation_goals TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 对话与交互规范
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_dialogue_rules(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                tone TEXT,
                language_style TEXT,
                behavior_constraints TEXT,
                interaction_pattern TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 任务/功能性信息
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_tasks(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                task_goal TEXT,
                dialogue_intent TEXT,
                interaction_limits TEXT,
                trigger_conditions TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 环境与世界观
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_worldview(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                worldview TEXT,
                timeline TEXT,
                social_rules TEXT,
                external_resources TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 背景故事
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_background(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                origin TEXT,
                current_situation TEXT,
                secrets TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 经历表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_experiences(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL,
                experience_text TEXT NOT NULL,
                sequence_order INT NOT NULL,
                created_at BIGINT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char_exp ON character_experiences(character_id, sequence_order)")
        
        # 关系网络表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_relationships(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL,
                relationship_text TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char_rel ON character_relationships(character_id)")
        
        # 系统与控制参数
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_system_params(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                consistency_control TEXT,
                preference_control TEXT,
                safety_limits TEXT,
                deduction_range TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 来源信息
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_source_info(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL UNIQUE,
                unique_id TEXT,
                source_url TEXT,
                source_info_size INT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 记忆表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_memories(
                id SERIAL PRIMARY KEY,
                character_id INT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char_memory ON character_memories(character_id, memory_type, created_at)")
        
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        
        # 群聊成员表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_members(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                member_type TEXT NOT NULL,
                member_id INTEGER,
                member_name TEXT NOT NULL,
                joined_at INTEGER NOT NULL,
                UNIQUE(group_id, member_type, member_name)
            )
            """
        )
        
        # 群聊消息表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                sender_type TEXT NOT NULL,
                sender_id INTEGER,
                sender_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                system_prompt_snapshot TEXT,
                moderator_prompt TEXT,
                moderator_response TEXT
            )
            """
        )
        
        # 反馈表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedbacks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_reply TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        
        # ===== 角色详细信息表 (SQLite) =====
        
        # 基础身份信息
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_basic_info(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                name TEXT,
                age TEXT,
                gender TEXT,
                occupation TEXT,
                identity_background TEXT,
                appearance TEXT,
                titles TEXT,
                brief_intro TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 知识与能力
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_knowledge(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                knowledge_domain TEXT,
                skills TEXT,
                limitations TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 个性与行为设定
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_personality(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                traits TEXT,
                values TEXT,
                emotion_style TEXT,
                speaking_style TEXT,
                preferences TEXT,
                dislikes TEXT,
                motivation_goals TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 对话与交互规范
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_dialogue_rules(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                tone TEXT,
                language_style TEXT,
                behavior_constraints TEXT,
                interaction_pattern TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 任务/功能性信息
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                task_goal TEXT,
                dialogue_intent TEXT,
                interaction_limits TEXT,
                trigger_conditions TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 环境与世界观
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_worldview(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                worldview TEXT,
                timeline TEXT,
                social_rules TEXT,
                external_resources TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 背景故事
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_background(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                origin TEXT,
                current_situation TEXT,
                secrets TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 经历表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_experiences(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                experience_text TEXT NOT NULL,
                sequence_order INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char_exp ON character_experiences(character_id, sequence_order)")
        
        # 关系网络表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_relationships(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                relationship_text TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char_rel ON character_relationships(character_id)")
        
        # 系统与控制参数
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_system_params(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                consistency_control TEXT,
                preference_control TEXT,
                safety_limits TEXT,
                deduction_range TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 来源信息
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_source_info(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                unique_id TEXT,
                source_url TEXT,
                source_info_size INTEGER,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        
        # 记忆表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS character_memories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char_memory ON character_memories(character_id, memory_type, created_at)")
    
    # 为已存在的表添加中控相关字段
    try:
        if not _column_exists(cur, 'group_messages', 'moderator_prompt'):
            cur.execute("ALTER TABLE group_messages ADD COLUMN moderator_prompt TEXT")
        if not _column_exists(cur, 'group_messages', 'moderator_response'):
            cur.execute("ALTER TABLE group_messages ADD COLUMN moderator_response TEXT")
        if not _column_exists(cur, 'group_messages', 'compressed'):
            if USE_POSTGRESQL:
                cur.execute("ALTER TABLE group_messages ADD COLUMN compressed INT DEFAULT 0")
            else:
                cur.execute("ALTER TABLE group_messages ADD COLUMN compressed INTEGER DEFAULT 0")
            print("[INFO] 已为 group_messages 表添加 compressed 字段")
        conn.commit()
    except Exception as e:
        print(f"[WARN] 添加字段失败: {e}")
    conn.commit()
    conn.close()


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


# ----- Characters & Messages helpers -----

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
            conn.close()
        else:
            conn.commit()
            conn.close()


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


# ----- User settings & password -----

def get_user_id_by_username(username: str) -> Optional[int]:
    """根据用户名查询用户ID"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_user_settings(user_id: int) -> Dict[str, Any]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, updated_at FROM user_settings WHERE user_id=%s",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return {
                "default_model": None,
                "ctx_max_chat": None,
                "ctx_max_stm": None,
                "ctx_max_ltm": None,
                "profile": None,
                "max_group_reply_rounds": 3,
                "updated_at": 0,
            }
        return {
            "default_model": row[0],
            "ctx_max_chat": (int(row[1]) if row[1] is not None else None),
            "ctx_max_stm": (int(row[2]) if row[2] is not None else None),
            "ctx_max_ltm": (int(row[3]) if row[3] is not None else None),
            "profile": row[4],
            "max_group_reply_rounds": (int(row[5]) if row[5] is not None else 3),
            "updated_at": int(row[6]),
        }
    finally:
        conn.close()


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
    finally:
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, created_at, is_admin FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None
    finally:
        conn.close()


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
        conn.close()


# ----- Account deletion -----

def delete_account(user_id: int) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 删除该用户的所有消息
        cur.execute("SELECT id FROM characters WHERE user_id=%s", (user_id,))
        char_ids = [int(r[0]) for r in cur.fetchall()]
        if char_ids:
            for cid in char_ids:
                cur.execute("DELETE FROM messages WHERE user_id=%s AND character_id=%s", (user_id, cid))
        # 删除角色
        cur.execute("DELETE FROM characters WHERE user_id=%s", (user_id,))
        # 删除用户设置
        cur.execute("DELETE FROM user_settings WHERE user_id=%s", (user_id,))
        # 删除用户
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ----- Group Chat Functions -----

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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


def remove_group_member(group_id: int, member_name: str) -> None:
    """移除群聊成员"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM group_members WHERE group_id=%s AND member_name=%s", (group_id, member_name))
        conn.commit()
    finally:
        conn.close()


# ============= 反馈相关函数 =============

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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


def delete_feedback(feedback_id: int) -> None:
    """删除反馈"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM feedbacks WHERE id=%s", (feedback_id,))
        conn.commit()
    finally:
        conn.close()


# ============= 角色完整数据保存/加载函数 =============

def save_character_full_data(user_id: int, name: str, structured_data: Dict[str, Any], baike_content: str = None) -> int:
    """保存完整角色数据到所有相关表
    
    Args:
        user_id: 用户ID
        name: 角色名称
        structured_data: 结构化数据（字典格式）
        baike_content: 百科全文（JSON字符串）
    
    Returns:
        character_id: 角色ID
    """
    import json
    conn = _get_conn()
    now = int(time.time())
    
    try:
        cur = conn.cursor()
        
        # 1. 先创建或更新角色主记录
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        
        if row:
            # 更新现有角色
            character_id = int(_row_to_dict(row, cur)['id']) if USE_POSTGRESQL else int(row['id'])
            cur.execute(
                "UPDATE characters SET baike_content=%s, updated_at=%s WHERE id=%s",
                (baike_content, now, character_id)
            )
        else:
            # 创建新角色
            if USE_POSTGRESQL:
                cur.execute(
                    "INSERT INTO characters(user_id, name, model, source, structured_json, baike_content, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (user_id, name, '', '', json.dumps(structured_data, ensure_ascii=False), baike_content, now, now)
                )
                character_id = int(cur.fetchone()[0])
                conn.commit()  # 立即提交，确保后续外键关联能找到这条记录
            else:
                cur.execute(
                    "INSERT INTO characters(user_id, name, model, source, structured_json, baike_content, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    (user_id, name, '', '', json.dumps(structured_data, ensure_ascii=False), baike_content, now, now)
                )
                conn.commit()
                character_id = int(cur.lastrowid)
        
        # 辅助函数：将复杂类型转换为JSON字符串
        def _safe_json_value(value):
            if value is None:
                return None
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value) if value else None
        
        # 2. 保存基础身份信息
        basic_info = structured_data.get('基础身份信息', {})
        if basic_info:
            cur.execute("DELETE FROM character_basic_info WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_basic_info(character_id, name, age, gender, occupation, identity_background, appearance, titles, brief_intro)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (character_id, 
                 _safe_json_value(basic_info.get('姓名')),
                 _safe_json_value(basic_info.get('年龄')),
                 _safe_json_value(basic_info.get('性别')),
                 _safe_json_value(basic_info.get('职业')),
                 _safe_json_value(basic_info.get('身份背景')),
                 _safe_json_value(basic_info.get('外貌特征')),
                 _safe_json_value(basic_info.get('称谓/头衔')),
                 _safe_json_value(basic_info.get('人物简介')))
            )
        
        # 3. 保存知识与能力
        knowledge = structured_data.get('知识与能力', {})
        if knowledge:
            cur.execute("DELETE FROM character_knowledge WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_knowledge(character_id, knowledge_domain, skills, limitations)
                   VALUES(%s,%s,%s,%s)""",
                (character_id, _safe_json_value(knowledge.get('知识领域')), 
                 _safe_json_value(knowledge.get('技能')), _safe_json_value(knowledge.get('限制')))
            )
        
        # 4. 保存个性与行为设定
        personality = structured_data.get('个性与行为设定', {})
        if personality:
            cur.execute("DELETE FROM character_personality WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_personality(character_id, traits, values, emotion_style, speaking_style, preferences, dislikes, motivation_goals)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(personality.get('性格特质')), 
                 _safe_json_value(personality.get('价值观')), _safe_json_value(personality.get('情绪风格')),
                 _safe_json_value(personality.get('说话方式')), _safe_json_value(personality.get('偏好')), 
                 _safe_json_value(personality.get('厌恶')), _safe_json_value(personality.get('动机与目标')))
            )
        
        # 5. 保存对话与交互规范
        dialogue = structured_data.get('对话与交互规范', {})
        if dialogue:
            cur.execute("DELETE FROM character_dialogue_rules WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_dialogue_rules(character_id, tone, language_style, behavior_constraints, interaction_pattern)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(dialogue.get('语气')), _safe_json_value(dialogue.get('语言风格')), 
                 _safe_json_value(dialogue.get('行为约束')), _safe_json_value(dialogue.get('互动模式')))
            )
        
        # 6. 保存任务/功能性信息
        tasks = structured_data.get('任务/功能性信息', {})
        if tasks:
            cur.execute("DELETE FROM character_tasks WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_tasks(character_id, task_goal, dialogue_intent, interaction_limits, trigger_conditions)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(tasks.get('任务目标')), _safe_json_value(tasks.get('对话意图')), 
                 _safe_json_value(tasks.get('交互限制')), _safe_json_value(tasks.get('触发条件')))
            )
        
        # 7. 保存环境与世界观
        worldview = structured_data.get('环境与世界观', {})
        if worldview:
            cur.execute("DELETE FROM character_worldview WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_worldview(character_id, worldview, timeline, social_rules, external_resources)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(worldview.get('世界观')), _safe_json_value(worldview.get('时间线')), 
                 _safe_json_value(worldview.get('社会规则')), _safe_json_value(worldview.get('外部资源')))
            )
        
        # 8. 保存背景故事
        background = structured_data.get('背景故事', {})
        if background:
            cur.execute("DELETE FROM character_background WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_background(character_id, origin, current_situation, secrets)
                   VALUES(%s,%s,%s,%s)""",
                (character_id, _safe_json_value(background.get('出身')), 
                 _safe_json_value(background.get('当前处境')), _safe_json_value(background.get('秘密')))
            )
            
            # 保存经历
            experiences = background.get('经历', [])
            if experiences:
                cur.execute("DELETE FROM character_experiences WHERE character_id=%s", (character_id,))
                for idx, exp in enumerate(experiences):
                    cur.execute(
                        """INSERT INTO character_experiences(character_id, experience_text, sequence_order, created_at)
                           VALUES(%s,%s,%s,%s)""",
                        (character_id, exp, idx, now)
                    )
            
            # 保存关系网络
            relationships = background.get('关系网络', [])
            if relationships:
                cur.execute("DELETE FROM character_relationships WHERE character_id=%s", (character_id,))
                for rel in relationships:
                    cur.execute(
                        """INSERT INTO character_relationships(character_id, relationship_text, created_at)
                           VALUES(%s,%s,%s)""",
                        (character_id, rel, now)
                    )
        
        # 9. 保存系统与控制参数
        system_params = structured_data.get('系统与控制参数', {})
        if system_params:
            cur.execute("DELETE FROM character_system_params WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_system_params(character_id, consistency_control, preference_control, safety_limits, deduction_range)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(system_params.get('一致性控制')), 
                 _safe_json_value(system_params.get('偏好控制')), 
                 _safe_json_value(system_params.get('安全限制')), _safe_json_value(system_params.get('演绎范围')))
            )
        
        # 10. 保存来源信息
        source_info = structured_data.get('来源信息', {})
        if source_info:
            # 获取现有的 source_info_size（如果 baike_content 为 None，保留原值）
            if baike_content is not None:
                source_info_size = len(baike_content)
            else:
                # 保留原有的值
                cur.execute("SELECT source_info_size FROM character_source_info WHERE character_id=%s", (character_id,))
                existing_row = cur.fetchone()
                if existing_row:
                    source_info_size = existing_row[0] if existing_row[0] is not None else 0
                else:
                    source_info_size = 0
            
            cur.execute("DELETE FROM character_source_info WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_source_info(character_id, unique_id, source_url, source_info_size)
                   VALUES(%s,%s,%s,%s)""",
                (character_id, _safe_json_value(source_info.get('唯一标识')), 
                 _safe_json_value(source_info.get('链接')), source_info_size)
            )
        
        conn.commit()
        return character_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def load_character_full_data(character_id: int) -> Optional[Dict[str, Any]]:
    """从所有相关表加载完整角色数据
    
    Args:
        character_id: 角色ID
    
    Returns:
        完整的角色数据字典，如果角色不存在则返回 None
    """
    from fastnpc.api.auth_char_data import load_character_full_data_impl
    return load_character_full_data_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id)


def save_character_memories(character_id: int, short_term: List[str] = None, long_term: List[str] = None) -> None:
    """保存角色记忆到数据库
    
    Args:
        character_id: 角色ID
        short_term: 短期记忆列表
        long_term: 长期记忆列表
    """
    from fastnpc.api.auth_char_data import save_character_memories_impl
    return save_character_memories_impl(_get_conn, USE_POSTGRESQL, character_id, short_term, long_term)


def load_character_memories(character_id: int) -> Dict[str, List[str]]:
    """从数据库加载角色记忆
    
    Args:
        character_id: 角色ID
    
    Returns:
        包含 'short_term' 和 'long_term' 键的字典
    """
    from fastnpc.api.auth_char_data import load_character_memories_impl
    return load_character_memories_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id)


