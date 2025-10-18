# -*- coding: utf-8 -*-
"""
FastNPC 认证和数据访问层

此包包含所有数据库操作相关的模块。
"""

from __future__ import annotations

# ===== 数据库工具 =====
from fastnpc.api.auth.db_utils import (
    _get_conn,
    _return_conn,
    _row_to_dict,
    _column_exists,
    DB_PATH
)

# ===== 数据库初始化 =====
from fastnpc.api.auth.db_init import init_db

# ===== 认证核心 =====
from fastnpc.api.auth.core import (
    _signer,
    create_user,
    verify_user,
    issue_cookie,
    verify_cookie
)

# ===== 用户管理 =====
from fastnpc.api.auth.users import (
    get_user_id_by_username,
    get_user_settings,
    update_user_settings,
    change_password,
    list_users,
    get_user_by_id,
    delete_account
)

# ===== 角色管理 =====
from fastnpc.api.auth.characters import (
    get_or_create_character,
    get_character_id,
    rename_character,
    delete_character,
    list_characters,
    update_character_structured,
    get_character_detail,
    mark_character_as_test_case,
    reset_character_state
)

# ===== 消息管理 =====
from fastnpc.api.auth.messages import (
    add_message,
    list_messages,
    mark_messages_as_compressed,
    mark_group_messages_as_compressed,
    update_message_system_prompt
)

# ===== 群聊功能 =====
from fastnpc.api.auth.groups import (
    create_group_chat,
    list_group_chats,
    add_group_member,
    list_group_members,
    add_group_message,
    update_group_message_moderator_info,
    list_group_messages,
    delete_group_chat,
    get_group_chat_detail,
    remove_group_member,
    mark_group_as_test_case,
    reset_group_state
)

# ===== 反馈系统 =====
from fastnpc.api.auth.feedbacks import (
    create_feedback,
    list_feedbacks,
    get_feedback_detail,
    update_feedback_status,
    delete_feedback
)

# ===== 角色完整数据操作 =====
from fastnpc.api.auth.char_data import (
    save_character_full_data,
    load_character_full_data_impl,
    save_character_memories_impl,
    load_character_memories_impl
)

# 为向后兼容，提供这三个包装函数
def load_character_full_data(character_id: int):
    """从所有相关表加载完整角色数据"""
    from fastnpc.config import USE_POSTGRESQL
    return load_character_full_data_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id)

def save_character_memories(character_id: int, short_term=None, long_term=None):
    """保存角色记忆到数据库"""
    from fastnpc.config import USE_POSTGRESQL
    return save_character_memories_impl(_get_conn, USE_POSTGRESQL, character_id, short_term, long_term)

def load_character_memories(character_id: int):
    """从数据库加载角色记忆"""
    from fastnpc.config import USE_POSTGRESQL
    return load_character_memories_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id)

# 导出所有公共函数
__all__ = [
    # 数据库工具
    '_get_conn',
    '_return_conn',
    '_row_to_dict',
    '_column_exists',
    'DB_PATH',
    
    # 数据库初始化
    'init_db',
    
    # 认证核心
    '_signer',
    'create_user',
    'verify_user',
    'issue_cookie',
    'verify_cookie',
    
    # 用户管理
    'get_user_id_by_username',
    'get_user_settings',
    'update_user_settings',
    'change_password',
    'list_users',
    'get_user_by_id',
    'delete_account',
    
    # 角色管理
    'get_or_create_character',
    'get_character_id',
    'rename_character',
    'delete_character',
    'list_characters',
    'update_character_structured',
    'get_character_detail',
    'mark_character_as_test_case',
    'reset_character_state',
    
    # 消息管理
    'add_message',
    'list_messages',
    'mark_messages_as_compressed',
    'mark_group_messages_as_compressed',
    'update_message_system_prompt',
    
    # 群聊功能
    'create_group_chat',
    'list_group_chats',
    'add_group_member',
    'list_group_members',
    'add_group_message',
    'update_group_message_moderator_info',
    'list_group_messages',
    'delete_group_chat',
    'get_group_chat_detail',
    'remove_group_member',
    'mark_group_as_test_case',
    'reset_group_state',
    
    # 反馈系统
    'create_feedback',
    'list_feedbacks',
    'get_feedback_detail',
    'update_feedback_status',
    'delete_feedback',
    
    # 角色完整数据操作
    'save_character_full_data',
    'load_character_full_data',
    'save_character_memories',
    'load_character_memories',
]

