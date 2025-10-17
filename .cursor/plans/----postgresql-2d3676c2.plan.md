<!-- 2d3676c2-00b4-4b82-ad76-472346bdd4ff 0bce7738-7136-468d-8abd-a24c882d3315 -->
# 角色数据迁移到数据库

## 1. 数据库表结构设计

### 核心表

#### characters（角色主表）
```sql
CREATE TABLE characters(
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    name TEXT NOT NULL,
    model TEXT,
    source TEXT,
    baike_content TEXT,  -- 百科全文（JSON格式存储）
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    UNIQUE(user_id, name),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### character_basic_info（基础身份信息）
```sql
CREATE TABLE character_basic_info(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    name TEXT,
    age TEXT,
    gender TEXT,
    occupation TEXT,
    identity_background TEXT,
    appearance TEXT,
    titles TEXT,  -- 称谓/头衔，多个用分号分隔
    brief_intro TEXT,  -- 人物简介
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_knowledge（知识与能力）
```sql
CREATE TABLE character_knowledge(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    knowledge_domain TEXT,  -- 知识领域
    skills TEXT,  -- 技能
    limitations TEXT,  -- 限制
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_personality（个性与行为设定）
```sql
CREATE TABLE character_personality(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    traits TEXT,  -- 性格特质
    values TEXT,  -- 价值观
    emotion_style TEXT,  -- 情绪风格
    speaking_style TEXT,  -- 说话方式
    preferences TEXT,  -- 偏好
    dislikes TEXT,  -- 厌恶
    motivation_goals TEXT,  -- 动机与目标
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_dialogue_rules（对话与交互规范）
```sql
CREATE TABLE character_dialogue_rules(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    tone TEXT,  -- 语气
    language_style TEXT,  -- 语言风格
    behavior_constraints TEXT,  -- 行为约束
    interaction_pattern TEXT,  -- 互动模式
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_tasks（任务/功能性信息）
```sql
CREATE TABLE character_tasks(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    task_goal TEXT,  -- 任务目标
    dialogue_intent TEXT,  -- 对话意图
    interaction_limits TEXT,  -- 交互限制
    trigger_conditions TEXT,  -- 触发条件
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_worldview（环境与世界观）
```sql
CREATE TABLE character_worldview(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    worldview TEXT,  -- 世界观
    timeline TEXT,  -- 时间线
    social_rules TEXT,  -- 社会规则
    external_resources TEXT,  -- 外部资源
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_background（背景故事）
```sql
CREATE TABLE character_background(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    origin TEXT,  -- 出身
    current_situation TEXT,  -- 当前处境
    secrets TEXT,  -- 秘密
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_experiences（经历表）
```sql
CREATE TABLE character_experiences(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL,
    experience_text TEXT NOT NULL,
    sequence_order INT NOT NULL,  -- 顺序
    created_at BIGINT NOT NULL,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX idx_char_exp ON character_experiences(character_id, sequence_order);
```

#### character_relationships（关系网络表）
```sql
CREATE TABLE character_relationships(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL,
    relationship_text TEXT NOT NULL,  -- 完整关系描述
    created_at BIGINT NOT NULL,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX idx_char_rel ON character_relationships(character_id);
```

#### character_system_params（系统与控制参数）
```sql
CREATE TABLE character_system_params(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    consistency_control TEXT,  -- 一致性控制
    preference_control TEXT,  -- 偏好控制
    safety_limits TEXT,  -- 安全限制
    演绎范围 TEXT,  -- 演绎范围
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_source_info（来源信息）
```sql
CREATE TABLE character_source_info(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL UNIQUE,
    unique_id TEXT,  -- 唯一标识
    source_url TEXT,  -- 链接
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

#### character_memories（记忆表）
```sql
CREATE TABLE character_memories(
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL,
    memory_type TEXT NOT NULL,  -- 'short_term' 或 'long_term'
    content TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX idx_char_memory ON character_memories(character_id, memory_type, created_at);
```

## 2. 修改数据库初始化函数

**文件**: `fastnpc/api/auth.py`

在 `init_db()` 函数中添加所有新表的创建语句，确保按照依赖顺序创建（先 characters，再其他关联表）。

## 3. 重构角色相关数据库函数

### 需要重构的函数：

1. **`get_or_create_character()`** - 只创建主表记录
2. **`update_character_structured()`** - 改为多个函数，分别保存到不同表
3. **新增函数**:
   - `save_character_full_data()` - 保存完整角色数据到所有表
   - `load_character_full_data()` - 从所有表加载完整角色数据
   - `save_character_memories()` - 保存记忆到 character_memories 表
   - `load_character_memories()` - 加载记忆从 character_memories 表
   - `delete_character()` - 删除角色（级联删除所有关联数据）

## 4. 修改角色创建逻辑

**文件**: `fastnpc/api/routes/char_routes.py`

修改 `/api/characters` POST 端点：
- 爬虫获取数据后，不再保存 JSON 文件
- 直接调用 `save_character_full_data()` 保存到数据库
- 百科全文保存到 `characters.baike_content` 字段

## 5. 修改聊天逻辑

**文件**: `fastnpc/core/chat.py` 和 `fastnpc/core/group_chat.py`

- 修改 `build_system_prompt()` 从数据库加载角色数据而非 JSON 文件
- 修改记忆压缩后保存逻辑，调用 `save_character_memories()`
- 修改记忆加载逻辑，调用 `load_character_memories()`

## 6. 修改管理员查看角色功能

**文件**: `fastnpc/api/routes/admin_routes.py`

修改 `GET /admin/characters/{character_id}` 端点：
- 调用 `load_character_full_data()` 获取完整数据
- 格式化返回给前端

## 7. 清理文件系统操作

删除或注释掉所有对 `Characters/` 目录的读写操作（保留目录作为备份）。

## 8. 全面测试

按优先级测试：
1. **角色创建** - 测试爬虫创建新角色，数据是否正确保存到所有表
2. **角色列表** - 验证列表显示正常
3. **单角色对话** - 验证从数据库加载角色数据，对话功能正常
4. **记忆压缩** - 验证短期/长期记忆保存到数据库
5. **群聊功能** - 验证多个角色的群聊功能
6. **管理员查看** - 验证管理员可以查看完整角色数据
7. **角色删除** - 验证删除角色时级联删除所有关联数据

## 注意事项

- **事务一致性**: 保存角色数据时使用数据库事务，确保全部成功或全部回滚
- **查询优化**: 创建必要的索引，优化关联查询性能
- **向后兼容**: 暂时保留 Characters/ 目录，不要删除现有文件
- **错误处理**: 添加详细的错误日志，便于调试
- **数据验证**: 保存前验证数据完整性

### To-dos

- [ ] 在 auth.py 的 init_db() 中添加所有新表的创建语句
- [ ] 在 auth.py 中添加 save_character_full_data 和 load_character_full_data 函数
- [ ] 在 auth.py 中添加 save_character_memories 和 load_character_memories 函数
- [ ] 修改 char_routes.py 的角色创建逻辑，保存到数据库而非文件
- [ ] 修改 chat.py 和 group_chat.py，从数据库加载角色数据
- [ ] 修改记忆压缩逻辑，保存到 character_memories 表
- [ ] 修改 admin_routes.py 的角色查看功能，从数据库加载
- [ ] 测试角色创建功能（爬虫 + 数据库保存）
- [ ] 测试单角色对话功能
- [ ] 测试记忆压缩和加载功能
- [ ] 测试群聊功能
- [ ] 测试管理员查看角色功能
- [ ] 测试角色删除功能（验证级联删除）