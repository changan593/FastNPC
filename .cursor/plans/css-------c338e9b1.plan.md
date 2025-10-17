<!-- c338e9b1-4bdf-409d-9a1c-bb08ec3905e6 73775833-c7fe-4271-852a-871a645a9647 -->
# auth.py 模块拆分计划

## 目标

将 `fastnpc/api/auth.py` (1857行) 拆分为多个模块文件，提高代码可维护性和可读性。

## 拆分策略

- 粗粒度拆分（7个功能模块 + 2个基础模块）
- 保留 `auth.py` 作为入口文件，重新导出所有函数（向后兼容）
- 数据库初始化独立为 `db_init.py`
- 仅拆分函数，不改变架构

## 文件结构

```
fastnpc/api/
├── auth.py (入口文件，重新导出所有函数，约60行)
├── db_utils.py (数据库连接和工具，约80行)
├── db_init.py (数据库初始化，约720行)
├── auth_core.py (认证核心功能，约60行)
├── auth_users.py (用户管理，约150行)
├── auth_characters.py (角色管理，约200行)
├── auth_messages.py (消息管理，约240行)
├── auth_groups.py (群聊功能，约220行)
├── auth_feedbacks.py (反馈系统，约120行)
└── auth_char_data.py (角色完整数据，约250行)
```

## 实施步骤

### 1. 创建 db_utils.py

**内容** (约80行):
- `_get_conn()` - 数据库连接函数
- `_row_to_dict()` - 行转字典工具
- `_column_exists()` - 检查列是否存在
- 导入所有配置变量

**来源**: auth.py 第1-76行

### 2. 创建 db_init.py

**内容** (约720行):
- `init_db()` - 完整的数据库初始化函数
- 从 `db_utils` 导入所需的工具函数

**来源**: auth.py 第78-792行

### 3. 创建 auth_core.py

**内容** (约60行):
- `_signer()` - Cookie签名器
- `create_user()` - 创建用户
- `verify_user()` - 验证用户
- `issue_cookie()` - 签发Cookie
- `verify_cookie()` - 验证Cookie

**来源**: auth.py 第795-844行

### 4. 创建 auth_users.py

**内容** (约150行):
- `get_user_id_by_username()` - 根据用户名查询ID
- `get_user_settings()` - 获取用户设置
- `update_user_settings()` - 更新用户设置
- `change_password()` - 修改密码
- `list_users()` - 列出所有用户
- `get_user_by_id()` - 根据ID获取用户
- `delete_account()` - 删除账户

**来源**: auth.py 第917-1264行（用户相关函数）

### 5. 创建 auth_characters.py

**内容** (约200行):
- `get_or_create_character()` - 获取或创建角色
- `get_character_id()` - 获取角色ID
- `rename_character()` - 重命名角色
- `delete_character()` - 删除角色
- `list_characters()` - 列出角色
- `update_character_structured()` - 更新结构化数据
- `get_character_detail()` - 获取角色详情

**来源**: auth.py 第849-878行、第1120-1242行

### 6. 创建 auth_messages.py

**内容** (约240行):
- `add_message()` - 添加消息
- `list_messages()` - 列出消息
- `mark_messages_as_compressed()` - 标记消息为已压缩
- `mark_group_messages_as_compressed()` - 标记群聊消息为已压缩
- `update_message_system_prompt()` - 更新系统提示词

**来源**: auth.py 第880-1118行

### 7. 创建 auth_groups.py

**内容** (约220行):
- `create_group_chat()` - 创建群聊
- `list_group_chats()` - 列出群聊
- `add_group_member()` - 添加成员
- `list_group_members()` - 列出成员
- `add_group_message()` - 添加群聊消息
- `update_group_message_moderator_info()` - 更新中控信息
- `list_group_messages()` - 列出群聊消息
- `delete_group_chat()` - 删除群聊
- `get_group_chat_detail()` - 获取群聊详情
- `remove_group_member()` - 移除成员

**来源**: auth.py 第1267-1488行

### 8. 创建 auth_feedbacks.py

**内容** (约120行):
- `create_feedback()` - 创建反馈
- `list_feedbacks()` - 列出反馈
- `get_feedback_detail()` - 获取反馈详情
- `update_feedback_status()` - 更新反馈状态
- `delete_feedback()` - 删除反馈

**来源**: auth.py 第1490-1606行

### 9. 创建 auth_char_data.py

**内容** (约250行):
- `save_character_full_data()` - 保存完整角色数据
- `load_character_full_data()` - 加载完整角色数据
- `save_character_memories()` - 保存角色记忆
- `load_character_memories()` - 加载角色记忆
- 包含实现函数: `load_character_full_data_impl`, `save_character_memories_impl`, `load_character_memories_impl`

**来源**: auth.py 第1609-1857行

### 10. 重写 auth.py 入口文件

**内容** (约60行):

```python
# -*- coding: utf-8 -*-
"""
FastNPC 认证和数据访问层 - 入口文件

此文件重新导出所有数据库操作函数，保持向后兼容性。
实际实现已拆分到各个子模块中。
"""

# 导入所有模块
from fastnpc.api.db_utils import _get_conn, _row_to_dict, _column_exists
from fastnpc.api.db_init import init_db
from fastnpc.api.auth_core import (
    _signer, create_user, verify_user, 
    issue_cookie, verify_cookie
)
from fastnpc.api.auth_users import (
    get_user_id_by_username, get_user_settings, 
    update_user_settings, change_password,
    list_users, get_user_by_id, delete_account
)
from fastnpc.api.auth_characters import (
    get_or_create_character, get_character_id,
    rename_character, delete_character,
    list_characters, update_character_structured,
    get_character_detail
)
from fastnpc.api.auth_messages import (
    add_message, list_messages,
    mark_messages_as_compressed,
    mark_group_messages_as_compressed,
    update_message_system_prompt
)
from fastnpc.api.auth_groups import (
    create_group_chat, list_group_chats,
    add_group_member, list_group_members,
    add_group_message, update_group_message_moderator_info,
    list_group_messages, delete_group_chat,
    get_group_chat_detail, remove_group_member
)
from fastnpc.api.auth_feedbacks import (
    create_feedback, list_feedbacks,
    get_feedback_detail, update_feedback_status,
    delete_feedback
)
from fastnpc.api.auth_char_data import (
    save_character_full_data, load_character_full_data,
    save_character_memories, load_character_memories
)

# 重新导出所有函数（保持向后兼容）
__all__ = [
    # ... 所有函数名
]
```

## 关键要点

### 模块依赖关系

- `db_utils.py` - 基础层，无依赖
- `db_init.py` - 依赖 `db_utils`
- `auth_core.py` ~ `auth_char_data.py` - 都依赖 `db_utils`
- `auth.py` - 依赖所有子模块

### 函数签名保持不变

所有函数的签名、参数、返回值完全保持不变，确保向后兼容。

### 配置导入统一处理

所有模块都从 `fastnpc.config` 导入配置变量：
- `USE_POSTGRESQL`
- `POSTGRES_*` 系列变量
- `DB_PATH`
- `FASTNPC_SECRET`
- `FASTNPC_ADMIN_USER`

### 测试验证

拆分完成后需要验证：
1. 导入测试：`from fastnpc.api.auth import init_db` 可以正常工作
2. 功能测试：运行现有的所有API接口，确保无错误
3. 代码静态检查：确保没有循环导入

## 预期收益

- 单文件大小：1857行 → 平均150-200行/文件
- 可维护性：职责清晰，易于定位和修改
- 可读性：每个文件专注单一功能域
- 协作友好：减少文件冲突概率


### To-dos

- [ ] 创建 db_utils.py - 数据库连接和工具函数
- [ ] 创建 db_init.py - 数据库初始化
- [ ] 创建 auth_core.py - 认证核心功能
- [ ] 创建 auth_users.py - 用户管理
- [ ] 创建 auth_characters.py - 角色管理
- [ ] 创建 auth_messages.py - 消息管理
- [ ] 创建 auth_groups.py - 群聊功能
- [ ] 创建 auth_feedbacks.py - 反馈系统
- [ ] 创建 auth_char_data.py - 角色完整数据操作
- [ ] 重写 auth.py 为入口文件，重新导出所有函数
- [ ] 验证拆分：导入测试、功能测试、构建测试