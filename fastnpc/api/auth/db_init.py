# -*- coding: utf-8 -*-
"""
数据库初始化

创建所有数据库表结构，支持 PostgreSQL 和 SQLite。
包含数据库迁移逻辑（添加新字段）。
"""

from fastnpc.api.auth.db_utils import _get_conn, _column_exists, _return_conn
from fastnpc.config import USE_POSTGRESQL


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
                is_admin INT NOT NULL DEFAULT 0,
                avatar_url TEXT
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
                avatar_url TEXT,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                UNIQUE(user_id, name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                created_at BIGINT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
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
                is_admin INTEGER NOT NULL DEFAULT 0,
                avatar_url TEXT
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
                avatar_url TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(user_id, name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
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
                updated_at BIGINT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings(
                user_id INTEGER PRIMARY KEY,
                default_model TEXT,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
    
    # 为 characters 表添加 avatar_url 字段（角色头像）
    try:
        if not _column_exists(cur, 'characters', 'avatar_url'):
            cur.execute("ALTER TABLE characters ADD COLUMN avatar_url TEXT")
            conn.commit()
            print("[INFO] 已为characters表添加avatar_url字段")
    except Exception as e:
        print(f"[WARN] 添加avatar_url字段失败（可能已存在）: {e}")
    
    # 群聊表
    if USE_POSTGRESQL:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_chats(
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                name TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                UNIQUE(group_id, member_type, member_name),
                FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE
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
                moderator_response TEXT,
                FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                UNIQUE(group_id, member_type, member_name),
                FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE
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
                moderator_response TEXT,
                FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
    
    # 为 users 表添加 avatar_url 字段（用户头像）
    try:
        if not _column_exists(cur, 'users', 'avatar_url'):
            cur.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            conn.commit()
            print("[INFO] 已为users表添加avatar_url字段")
    except Exception as e:
        print(f"[WARN] 添加users.avatar_url字段失败（可能已存在）: {e}")
    conn.commit()
    _return_conn(conn)

