# -*- coding: utf-8 -*-
"""
FastNPC 认证和数据访问层 - 入口文件

此文件保持向后兼容性，直接从 auth 包重新导出所有函数。
实际实现位于 fastnpc/api/auth/ 子包中：

fastnpc/api/auth/
├── __init__.py       (主导出文件)
├── db_utils.py       (数据库连接和工具)
├── db_init.py        (数据库初始化)
├── core.py           (认证核心功能)
├── users.py          (用户管理)
├── characters.py     (角色管理)
├── messages.py       (消息管理)
├── groups.py         (群聊功能)
├── feedbacks.py      (反馈系统)
└── char_data.py      (角色完整数据操作)
"""

# 直接从 auth 包导入所有内容
from fastnpc.api.auth import *  # noqa: F401, F403

# 保持 __all__ 以支持 from fastnpc.api.auth import *
__all__ = [
    # 数据库工具
    '_get_conn',
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
