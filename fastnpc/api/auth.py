# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
import sqlite3
from typing import Optional, Tuple, Dict, Any

from passlib.hash import bcrypt
from itsdangerous import URLSafeSerializer, BadSignature
from fastnpc.config import DB_PATH as CONFIG_DB_PATH, FASTNPC_SECRET, FASTNPC_ADMIN_USER


DB_PATH = CONFIG_DB_PATH.as_posix()


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
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
    
    # 为messages表添加compressed字段（标记是否已压缩为短期记忆）
    try:
        cur.execute("PRAGMA table_info(messages)")
        cols = [r[1] for r in cur.fetchall()]
        if 'compressed' not in cols:
            cur.execute("ALTER TABLE messages ADD COLUMN compressed INTEGER DEFAULT 0")
            conn.commit()
    except Exception:
        pass
    
    # 为messages表添加system_prompt_snapshot字段（保存实际发送时的system prompt）
    try:
        cur.execute("PRAGMA table_info(messages)")
        cols = [r[1] for r in cur.fetchall()]
        if 'system_prompt_snapshot' not in cols:
            cur.execute("ALTER TABLE messages ADD COLUMN system_prompt_snapshot TEXT")
            conn.commit()
    except Exception:
        pass
    
    # 用户设置表：默认模型等
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
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if 'is_admin' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            conn.commit()
    except Exception:
        pass
    # 为已有库补充 user_settings 的记忆预算字段
    try:
        cur.execute("PRAGMA table_info(user_settings)")
        cols = [r[1] for r in cur.fetchall()]
        to_add = []
        if 'ctx_max_chat' not in cols:
            to_add.append("ALTER TABLE user_settings ADD COLUMN ctx_max_chat INTEGER")
        if 'ctx_max_stm' not in cols:
            to_add.append("ALTER TABLE user_settings ADD COLUMN ctx_max_stm INTEGER")
        if 'ctx_max_ltm' not in cols:
            to_add.append("ALTER TABLE user_settings ADD COLUMN ctx_max_ltm INTEGER")
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
        cur.execute("PRAGMA table_info(user_settings)")
        cols = [r[1] for r in cur.fetchall()]
        if 'profile' not in cols:
            cur.execute("ALTER TABLE user_settings ADD COLUMN profile TEXT")
            conn.commit()
    except Exception:
        pass
    
    # 为 user_settings 添加 max_group_reply_rounds 字段（群聊最大角色回复轮数）
    try:
        cur.execute("PRAGMA table_info(user_settings)")
        cols = [r[1] for r in cur.fetchall()]
        if 'max_group_reply_rounds' not in cols:
            cur.execute("ALTER TABLE user_settings ADD COLUMN max_group_reply_rounds INTEGER DEFAULT 3")
            conn.commit()
    except Exception:
        pass
    
    # 群聊表
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
    
    # 为已存在的表添加中控相关字段
    try:
        cur.execute("PRAGMA table_info(group_messages)")
        cols = [r[1] for r in cur.fetchall()]
        if 'moderator_prompt' not in cols:
            cur.execute("ALTER TABLE group_messages ADD COLUMN moderator_prompt TEXT")
        if 'moderator_response' not in cols:
            cur.execute("ALTER TABLE group_messages ADD COLUMN moderator_response TEXT")
        if 'compressed' not in cols:
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
            "INSERT INTO users(username, password_hash, created_at, is_admin) VALUES(?,?,?,?)",
            (username, bcrypt.hash(password), int(time.time()), is_admin),
        )
        conn.commit()
        return True, 'ok'
    except sqlite3.IntegrityError:
        return False, '用户名已存在'
    finally:
        conn.close()


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            return None
        if not bcrypt.verify(password, row['password_hash']):
            return None
        return {"id": row['id'], "username": row['username'], "is_admin": int(row['is_admin'])}
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
        cur.execute("SELECT id FROM characters WHERE user_id=? AND name=?", (user_id, name))
        row = cur.fetchone()
        if row:
            return int(row['id'])
        now = int(time.time())
        cur.execute(
            "INSERT INTO characters(user_id, name, model, source, structured_json, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
            (user_id, name, '', '', '', now, now),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
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
        cur.execute(
            "INSERT INTO messages(user_id, character_id, role, content, created_at, system_prompt_snapshot) VALUES(?,?,?,?,?,?)",
            (user_id, character_id, role, content, int(time.time()), system_prompt_snapshot),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


# ----- User settings & password -----

def get_user_settings(user_id: int) -> Dict[str, Any]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, updated_at FROM user_settings WHERE user_id=?",
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
        cur.execute("SELECT 1 FROM user_settings WHERE user_id=?", (user_id,))
        if cur.fetchone():
            cur.execute(
                "UPDATE user_settings SET default_model=?, ctx_max_chat=?, ctx_max_stm=?, ctx_max_ltm=?, profile=?, max_group_reply_rounds=?, updated_at=? WHERE user_id=?",
                (default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, now, user_id),
            )
        else:
            cur.execute(
                "INSERT INTO user_settings(user_id, default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (user_id, default_model, ctx_max_chat, ctx_max_stm, ctx_max_ltm, profile, max_group_reply_rounds, now),
            )
        conn.commit()
    finally:
        conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return False, '用户不存在'
        if not bcrypt.verify(old_password, row['password_hash']):
            return False, '原密码不正确'
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (bcrypt.hash(new_password), user_id))
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
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=? AND character_id=? AND id>? AND (compressed IS NULL OR compressed=0) ORDER BY id ASC LIMIT ?",
                    (user_id, character_id, after_id, limit),
                )
            else:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=? AND character_id=? AND (compressed IS NULL OR compressed=0) ORDER BY id ASC LIMIT ?",
                    (user_id, character_id, limit),
                )
        else:
            # 读取所有消息（包括已压缩的）
            if after_id > 0:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=? AND character_id=? AND id>? ORDER BY id ASC LIMIT ?",
                    (user_id, character_id, after_id, limit),
                )
            else:
                cur.execute(
                    "SELECT id, role, content, created_at, compressed, system_prompt_snapshot FROM messages WHERE user_id=? AND character_id=? ORDER BY id ASC LIMIT ?",
                    (user_id, character_id, limit),
                )
        rows = cur.fetchall()
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
        placeholders = ','.join('?' * len(message_ids))
        sql = f"UPDATE messages SET compressed=1 WHERE user_id=? AND character_id=? AND id IN ({placeholders})"
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
        placeholders = ','.join(['?'] * len(message_ids))
        cur.execute(
            f"UPDATE group_messages SET compressed=1 WHERE group_id=? AND id IN ({placeholders})",
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
            "UPDATE messages SET system_prompt_snapshot=? WHERE id=?",
            (system_prompt, message_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_character_id(user_id: int, name: str) -> Optional[int]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=? AND name=?", (user_id, name))
        row = cur.fetchone()
        return int(row['id']) if row else None
    finally:
        conn.close()


def rename_character(user_id: int, old_name: str, new_name: str) -> Tuple[bool, str]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=? AND name=?", (user_id, old_name))
        row = cur.fetchone()
        if not row:
            # 如果不存在则创建
            cid = get_or_create_character(user_id, old_name)
        else:
            cid = int(row['id'])
        # 检查新名是否已存在
        cur.execute("SELECT 1 FROM characters WHERE user_id=? AND name=?", (user_id, new_name))
        if cur.fetchone():
            return False, '新名称已存在'
        cur.execute("UPDATE characters SET name=?, updated_at=? WHERE id=?", (new_name, int(time.time()), cid))
        conn.commit()
        return True, 'ok'
    finally:
        conn.close()


def delete_character(user_id: int, name: str) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM characters WHERE user_id=? AND name=?", (user_id, name))
        row = cur.fetchone()
        if row:
            cid = int(row['id'])
            cur.execute("DELETE FROM messages WHERE user_id=? AND character_id=?", (user_id, cid))
            cur.execute("DELETE FROM characters WHERE id=?", (cid,))
            conn.commit()
    finally:
        conn.close()


def list_users() -> list[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, created_at, is_admin FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_characters(user_id: int) -> list[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, model, source, created_at, updated_at FROM characters WHERE user_id=? ORDER BY updated_at DESC", (user_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_character_structured(user_id: int, name: str, structured_json: str) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 确保角色存在
        cur.execute("SELECT id FROM characters WHERE user_id=? AND name=?", (user_id, name))
        row = cur.fetchone()
        if row:
            cid = int(row['id'])
        else:
            cid = get_or_create_character(user_id, name)
        cur.execute("UPDATE characters SET structured_json=?, updated_at=? WHERE id=?", (structured_json, int(time.time()), cid))
        conn.commit()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, created_at, is_admin FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_character_detail(user_id: int, character_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, model, source, structured_json, created_at, updated_at FROM characters WHERE id=? AND user_id=?",
            (character_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
# ----- Account deletion -----

def delete_account(user_id: int) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 删除该用户的所有消息
        cur.execute("SELECT id FROM characters WHERE user_id=?", (user_id,))
        char_ids = [int(r[0]) for r in cur.fetchall()]
        if char_ids:
            for cid in char_ids:
                cur.execute("DELETE FROM messages WHERE user_id=? AND character_id=?", (user_id, cid))
        # 删除角色
        cur.execute("DELETE FROM characters WHERE user_id=?", (user_id,))
        # 删除用户设置
        cur.execute("DELETE FROM user_settings WHERE user_id=?", (user_id,))
        # 删除用户
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
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
        cur.execute(
            "INSERT INTO group_chats(user_id, name, created_at, updated_at) VALUES(?,?,?,?)",
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
            WHERE gc.user_id=? 
            GROUP BY gc.id
            ORDER BY gc.updated_at DESC
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_group_member(group_id: int, member_type: str, member_name: str, member_id: int = None) -> None:
    """添加群聊成员"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO group_members(group_id, member_type, member_id, member_name, joined_at) VALUES(?,?,?,?,?)",
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
            "SELECT member_type, member_id, member_name FROM group_members WHERE group_id=? ORDER BY joined_at ASC",
            (group_id,)
        )
        rows = cur.fetchall()
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
        cur.execute(
            "INSERT INTO group_messages(group_id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response) VALUES(?,?,?,?,?,?,?,?,?)",
            (group_id, sender_type, sender_id, sender_name, content, int(time.time()), system_prompt_snapshot, moderator_prompt, moderator_response)
        )
        conn.commit()
        # 更新群聊的 updated_at
        cur.execute("UPDATE group_chats SET updated_at=? WHERE id=?", (int(time.time()), group_id))
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_group_message_moderator_info(message_id: int, moderator_prompt: str, moderator_response: str) -> None:
    """更新群聊消息的中控判断信息"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE group_messages SET moderator_prompt=?, moderator_response=? WHERE id=?",
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
                "SELECT id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response, compressed FROM group_messages WHERE group_id=? AND (compressed IS NULL OR compressed=0) ORDER BY id ASC LIMIT ?",
                (group_id, limit)
            )
        else:
            cur.execute(
                "SELECT id, sender_type, sender_id, sender_name, content, created_at, system_prompt_snapshot, moderator_prompt, moderator_response, compressed FROM group_messages WHERE group_id=? ORDER BY id ASC LIMIT ?",
                (group_id, limit)
            )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_group_chat(user_id: int, group_id: int) -> None:
    """删除群聊"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # 验证权限
        cur.execute("SELECT 1 FROM group_chats WHERE id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return
        cur.execute("DELETE FROM group_messages WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM group_chats WHERE id=?", (group_id,))
        conn.commit()
    finally:
        conn.close()


def get_group_chat_detail(group_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """获取群聊详情（含成员列表）"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at, updated_at FROM group_chats WHERE id=? AND user_id=?", (group_id, user_id))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        result['members'] = list_group_members(group_id)
        return result
    finally:
        conn.close()


def remove_group_member(group_id: int, member_name: str) -> None:
    """移除群聊成员"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM group_members WHERE group_id=? AND member_name=?", (group_id, member_name))
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
        cur.execute(
            "INSERT INTO feedbacks(user_id, title, content, attachments, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
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
            query += " AND f.user_id=?"
            params.append(user_id)
        
        if status is not None:
            query += " AND f.status=?"
            params.append(status)
        
        query += " ORDER BY f.created_at DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
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
            WHERE f.id=?
            """,
            (feedback_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
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
                "UPDATE feedbacks SET status=?, admin_reply=?, updated_at=? WHERE id=?",
                (status, admin_reply, now, feedback_id)
            )
        else:
            cur.execute(
                "UPDATE feedbacks SET status=?, updated_at=? WHERE id=?",
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
        cur.execute("DELETE FROM feedbacks WHERE id=?", (feedback_id,))
        conn.commit()
    finally:
        conn.close()


