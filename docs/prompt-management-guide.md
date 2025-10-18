# 提示词管理系统使用指南

## 一、系统概览

FastNPC 提示词管理系统是一个完整的提示词版本控制和测试评估平台，支持：

- ✅ 提示词的创建、编辑、版本管理
- ✅ 自动化测试和评估
- ✅ 版本对比和历史追踪
- ✅ 从硬编码到数据库的平滑迁移
- ✅ Redis 缓存加速
- ✅ 向后兼容机制

## 二、快速开始

### 2.1 初始化提示词数据库

首次使用需要将现有提示词导入数据库：

```bash
cd /home/changan/MyProject/FastNPC
python -m fastnpc.scripts.init_prompts
```

这将创建17个提示词模板（9个类别），所有提示词初始版本为 `v1.0.0`，并设置为激活状态。

### 2.2 初始化测试用例

导入预定义的12个测试用例：

```bash
python -m fastnpc.scripts.init_test_cases
```

### 2.3 启用数据库提示词

编辑 `.env` 文件（或设置环境变量）：

```bash
USE_DB_PROMPTS=true
```

如果设置为 `false`，系统将使用硬编码的提示词（向后兼容）。

### 2.4 访问管理界面

1. 启动后端服务器
2. 以管理员身份登录
3. 点击顶部"管理员"按钮进入管理视图
4. 点击右上角"🎯 提示词管理"按钮

## 三、提示词分类

系统管理以下9类提示词：

### 3.1 结构化生成 (STRUCTURED_GENERATION)

用于从原始文本生成角色结构化描述，包含9个子分类：

1. **基础身份信息**：姓名、年龄、性别、职业等
2. **个性与行为设定**：性格特质、价值观、情绪风格等
3. **背景故事**：出身、经历、当前处境等
4. **知识与能力**：技能、专业知识、语言能力等
5. **对话与交互规范**：说话方式、禁忌话题、交互规则等
6. **任务/功能性信息**：角色职能、工作流程等
7. **环境与世界观**：所处环境、时代背景等
8. **系统与控制参数**：系统级配置参数
9. **来源**：角色信息来源

**使用场景**：创建新角色时，从百度百科/维基百科等数据源生成结构化角色档案。

**可用变量**：`{persona_name}`, `{facts_markdown}`

### 3.2 简介生成 (BRIEF_GENERATION)

从完整的结构化角色档案生成简洁的人物简介（2-4句）。

**使用场景**：
- 角色列表展示
- 聊天界面右侧信息面板
- 群聊成员列表

**可用变量**：`{persona_name}`, `{person}`, `{role_json}`

### 3.3 单聊系统提示 (SINGLE_CHAT_SYSTEM)

单个角色与用户对话时的系统提示（固定规则层）。

**核心规则**：
- 第一人称对话
- 不暴露设定
- 简洁回答（通常不超过3句话）
- 避免重复
- 正面回答问题

**可用变量**：`{display_name}`, `{user_name}`

### 3.4 短期记忆凝练 - 单聊 (SINGLE_CHAT_STM_COMPRESSION)

将单聊的对话历史凝练为结构化短期记忆。

**输出格式**：`主语 | 动作/事实 | 补充`

**可用变量**：`{role_name}`, `{user_name}`, `{chat_to_compress}`, `{overlap_context}`

### 3.5 短期记忆凝练 - 群聊 (GROUP_CHAT_STM_COMPRESSION)

将群聊的对话历史凝练为结构化短期记忆。

**特点**：明确记录"谁对谁说了什么"

**可用变量**：`{role_name}`, `{participants_list}`, `{chat_to_compress}`, `{overlap_context}`

### 3.6 长期记忆整合 (LTM_INTEGRATION)

将多条短期记忆整合、去重、评分为长期记忆。

**输出字段**：
- `content`：记忆内容
- `importance`：重要性评分（0-10）
- `reason`：保留理由

**可用变量**：`{role_profile_summary}`, `{short_memories_to_integrate}`, `{existing_long_term_memories}`

### 3.7 群聊中控 (GROUP_MODERATOR)

判断群聊中下一个发言者。

**输出字段**：
- `next_speaker`：下一位发言者的角色名
- `reason`：选择理由
- `confidence`：置信度（0-1）

**可用变量**：`{participants}`, `{recent_messages}`

### 3.8 群聊角色发言 (GROUP_CHAT_CHARACTER)

群聊中单个角色发言时的系统提示。

**特点**：与单聊类似，但需考虑多人对话场景

**可用变量**：`{display_name}`, `{other_members}`

### 3.9 结构化系统消息 (STRUCTURED_SYSTEM_MESSAGE)

结构化生成任务的系统消息（通用指令）。

**核心要求**：
- 严格JSON输出
- 基于事实列表
- 中文字段

## 四、界面操作

### 4.1 主界面布局

```
┌─────────────────────────────────────────────────────────┐
│                    🎯 提示词管理                          │
├─────────────┬──────────────────────┬──────────────────┤
│  分类树     │    编辑器区域         │   测试与评估      │
│             │                      │                  │
│ ◆ 结构化生成 │  [版本选择]          │  [运行测试]      │
│   ▸ 基础身份 │                      │                  │
│   ▸ 个性行为 │  [提示词编辑器]       │  测试结果:       │
│   ...       │                      │  ✅ 测试1 通过    │
│ ◆ 简介生成   │  [变量说明]          │  ✅ 测试2 通过    │
│ ◆ 单聊系统   │                      │                  │
│ ...         │  [保存] [激活]       │  相关测试用例:   │
│             │  [复制为新版本]       │  - 测试用例1     │
└─────────────┴──────────────────────┴──────────────────┘
```

### 4.2 创建/编辑提示词

1. **选择分类**：点击左侧分类树选择要编辑的提示词
2. **编辑内容**：在中间编辑器修改提示词内容
3. **保存**：点击"💾 保存"按钮创建新版本
4. **激活**：如果新版本需要立即生效，点击"✓ 激活此版本"

**注意**：
- 每次保存都会创建新版本（自动递增版本号）
- 只有激活的版本才会被系统使用
- 同一类别同一时间只能有一个激活版本

### 4.3 使用变量

提示词支持使用 `{变量名}` 占位符，在运行时自动替换。

**示例**：

```
你现在的身份是 {display_name}。
你必须始终以第一人称与 {user_name} 进行对话。
```

运行时自动替换为：

```
你现在的身份是李白。
你必须始终以第一人称与小明进行对话。
```

### 4.4 运行测试

1. 选择要测试的提示词
2. 点击右侧"▶️ 运行测试"按钮
3. 查看测试结果：
   - ✅ 通过的检查项
   - ❌ 失败的检查项
   - 通过率
   - LLM输出预览

**自动化指标**：
- JSON格式验证
- 必需字段完整性
- 输出长度控制
- 关键词覆盖
- 第一人称检查

### 4.5 版本对比（待实现前端集成）

比较两个版本的差异：
- 文本差异高亮
- 逐行对比
- 新增/删除行统计

### 4.6 版本历史（待实现前端集成）

查看提示词的完整变更历史：
- 时间线展示
- 版本号和创建时间
- 变更说明
- 回滚功能

## 五、API使用

### 5.1 管理员API

所有管理API需要管理员权限（`is_admin=1`）。

#### 列出所有提示词

```http
GET /admin/prompts?category=SINGLE_CHAT_SYSTEM&include_inactive=true
```

**参数**：
- `category`（可选）：筛选指定类别
- `include_inactive`（可选）：是否包含未激活版本

#### 获取提示词详情

```http
GET /admin/prompts/{id}
```

#### 创建提示词

```http
POST /admin/prompts
Content-Type: application/json

{
  "category": "SINGLE_CHAT_SYSTEM",
  "name": "单聊系统提示",
  "template_content": "你现在的身份是 {display_name}...",
  "version": "1.0.0",
  "description": "单聊固定规则层提示",
  "metadata": {
    "variables": ["display_name", "user_name"]
  }
}
```

#### 更新提示词

```http
PUT /admin/prompts/{id}
Content-Type: application/json

{
  "template_content": "更新后的内容...",
  "description": "更新说明",
  "create_history": true
}
```

**参数**：
- `create_history`：是否创建版本历史记录

#### 激活版本

```http
POST /admin/prompts/{id}/activate
```

将指定提示词设置为激活状态，同类别的其他版本自动失活。

#### 复制为新版本

```http
POST /admin/prompts/{id}/duplicate
Content-Type: application/json

{
  "new_version": "2.0.0"
}
```

#### 运行测试

```http
POST /admin/prompts/{id}/test
```

返回所有相关测试用例的执行结果。

#### 获取版本历史

```http
GET /admin/prompts/{id}/history
```

#### 管理测试用例

```http
# 列出测试用例
GET /admin/prompts/test-cases?category=SINGLE_CHAT_SYSTEM

# 创建测试用例
POST /admin/prompts/test-cases
Content-Type: application/json

{
  "prompt_category": "SINGLE_CHAT_SYSTEM",
  "name": "测试用例名称",
  "description": "描述",
  "input_data": {...},
  "expected_output": "期望输出",
  "evaluation_metrics": {...}
}
```

### 5.2 在代码中使用

#### Python后端

```python
from fastnpc.prompt_manager import PromptManager, PromptCategory

# 获取激活的提示词
prompt_data = PromptManager.get_active_prompt(
    PromptCategory.SINGLE_CHAT_SYSTEM
)

# 渲染提示词（替换变量）
rendered = PromptManager.render_prompt(
    prompt_data['template_content'],
    {
        "display_name": "李白",
        "user_name": "小明"
    }
)
```

#### 检查是否启用数据库提示词

```python
from fastnpc.config import USE_DB_PROMPTS

if USE_DB_PROMPTS:
    # 从数据库加载
    prompt = PromptManager.get_active_prompt(...)
else:
    # 使用硬编码版本
    prompt = HARDCODED_PROMPT
```

## 六、测试系统

### 6.1 命令行工具

#### 运行所有测试

```bash
python -m fastnpc.scripts.run_prompt_tests
```

输出示例：

```
================================================================================
测试提示词: 单聊系统提示
类别: SINGLE_CHAT_SYSTEM
版本: 1.0.0
================================================================================
  ✓ 测试通过: 基础对话规则检查
    通过率: 100.0%
    通过检查: 关键词覆盖, 长度符合
```

#### 运行单个测试

```bash
python -m fastnpc.scripts.run_prompt_tests <prompt_id> <test_case_id>
```

#### 生成测试报告

```bash
python -m fastnpc.scripts.generate_test_report [output_file.md]
```

生成Markdown格式的测试报告，包含：
- 提示词总数和激活数
- 测试用例列表
- 评估结果统计

### 6.2 编写测试用例

测试用例存储在 `prompt_test_cases` 表，包含以下字段：

- `prompt_category`：提示词类别
- `prompt_sub_category`：子分类（可选）
- `name`：测试用例名称
- `description`：描述
- `input_data`：JSON格式的测试输入
- `expected_output`：期望输出描述
- `evaluation_metrics`：JSON格式的评估指标

**示例**：

```json
{
  "prompt_category": "SINGLE_CHAT_SYSTEM",
  "name": "基础对话规则检查",
  "description": "测试系统提示是否包含必要规则",
  "input_data": {
    "display_name": "李白",
    "user_name": "小明"
  },
  "expected_output": "包含第一人称、不暴露设定等规则",
  "evaluation_metrics": {
    "keywords": ["第一人称", "李白", "小明"],
    "output_length": [200, 1000]
  }
}
```

### 6.3 评估指标

系统支持以下自动化评估指标：

#### `json_valid`

检查输出是否为有效JSON格式。

```json
{
  "json_valid": true
}
```

#### `fields_complete`

检查JSON输出是否包含必需字段。

```json
{
  "fields_complete": ["姓名", "年龄", "性别", "职业"]
}
```

#### `output_length`

检查输出长度是否在指定范围内。

```json
{
  "output_length": [100, 500]
}
```

#### `keywords`

检查输出是否包含指定关键词。

```json
{
  "keywords": ["李白", "诗人", "唐代"]
}
```

#### `first_person_check`

检查输出是否使用第一人称（检测"我"、"我的"等）。

```json
{
  "first_person_check": true
}
```

#### `no_json_output`

检查输出是否不包含JSON格式（用于自然语言回复）。

```json
{
  "no_json_output": true
}
```

## 七、性能优化

### 7.1 Redis缓存

系统使用Redis缓存激活的提示词，缓存键格式：

```
prompt:active:{category}:{sub_category}
```

**缓存策略**：
- 提示词激活时自动更新缓存
- 缓存无过期时间（手动清除）
- 支持一键清除所有提示词缓存

**清除缓存**：

```python
from fastnpc.prompt_manager import PromptManager

PromptManager.clear_cache()  # 清除所有提示词缓存
PromptManager.clear_cache("SINGLE_CHAT_SYSTEM")  # 清除指定类别
```

### 7.2 批量操作

批量激活、批量测试等操作使用数据库事务，确保一致性。

### 7.3 数据库索引

已创建以下索引优化查询性能：

- `idx_prompt_category`：(category, sub_category, is_active)
- `idx_test_case_category`：(prompt_category, prompt_sub_category)
- `idx_eval_prompt`：(prompt_template_id)
- `idx_version_history`：(prompt_template_id, created_at DESC)

## 八、向后兼容

### 8.1 降级机制

当数据库不可用或查询失败时，系统自动降级到硬编码提示词：

```python
try:
    prompt = PromptManager.get_active_prompt(PromptCategory.SINGLE_CHAT_SYSTEM)
    if prompt:
        content = prompt['template_content']
except Exception as e:
    print(f"[WARN] 数据库加载失败: {e}，使用硬编码版本")
    content = HARDCODED_PROMPT
```

### 8.2 环境变量控制

通过 `USE_DB_PROMPTS` 环境变量控制是否使用数据库提示词：

```bash
# 启用数据库提示词（默认）
USE_DB_PROMPTS=true

# 禁用数据库提示词，使用硬编码版本
USE_DB_PROMPTS=false
```

### 8.3 迁移步骤

从硬编码迁移到数据库：

1. 运行初始化脚本导入提示词
2. 设置 `USE_DB_PROMPTS=true`
3. 重启服务
4. 验证功能正常
5. 在管理界面调整提示词
6. 运行测试确保质量

## 九、故障排查

### 9.1 提示词未生效

**问题**：修改了提示词但系统仍使用旧版本

**解决**：
1. 检查提示词是否已激活（`is_active=1`）
2. 清除Redis缓存：`PromptManager.clear_cache()`
3. 重启服务器

### 9.2 测试失败

**问题**：测试一直失败

**排查**：
1. 检查测试用例的 `input_data` 是否正确
2. 查看 LLM 输出内容
3. 调整 `evaluation_metrics` 阈值
4. 检查提示词是否包含必要变量

### 9.3 数据库错误

**问题**：数据库连接失败或查询错误

**排查**：
1. 检查数据库连接配置
2. 确认表结构已创建（运行 `db_init.py`）
3. 查看后端日志
4. 检查 `USE_DB_PROMPTS` 设置

### 9.4 变量未替换

**问题**：提示词中的 `{变量}` 没有被替换

**排查**：
1. 检查变量名是否正确（区分大小写）
2. 确认调用时传递了变量值
3. 使用 `PromptManager.render_prompt()` 方法
4. 检查 `metadata.variables` 字段

## 十、最佳实践

### 10.1 提示词编写

1. **明确目标**：清晰定义提示词的输入和输出
2. **使用变量**：避免硬编码，使用 `{变量}` 占位符
3. **简洁明了**：避免冗长的指令，突出核心要求
4. **示例驱动**：在提示词中提供输出示例
5. **版本管理**：记录每次修改的变更说明

### 10.2 测试驱动

1. **先写测试**：创建提示词前先设计测试用例
2. **覆盖场景**：为每个类别编写3-5个典型测试
3. **自动化评估**：充分利用自动化指标
4. **人工复核**：重要提示词需人工评分
5. **回归测试**：修改提示词后运行全部测试

### 10.3 版本控制

1. **语义化版本**：遵循 `主版本.次版本.修订号` 格式
2. **变更日志**：每次修改记录详细的变更说明
3. **谨慎激活**：充分测试后再激活新版本
4. **保留历史**：不要删除旧版本，便于回滚
5. **A/B测试**：重大变更先小范围测试

### 10.4 性能优化

1. **缓存预热**：服务启动时加载常用提示词到缓存
2. **批量查询**：一次性加载多个提示词
3. **异步测试**：测试任务使用异步执行
4. **定期清理**：清理过期的评估记录
5. **监控指标**：跟踪提示词加载耗时

## 十一、常见问题

**Q: 如何回滚到旧版本？**

A: 在版本历史中找到旧版本，点击"激活"按钮。系统会自动停用当前版本并激活选中的版本。

**Q: 可以删除提示词吗？**

A: 不建议删除。可以将提示词设置为未激活状态（`is_active=0`），这样系统不会使用它，但保留了历史记录。

**Q: 如何导出提示词？**

A: 使用API导出：`GET /admin/prompts?category=xxx`，或直接查询数据库 `prompt_templates` 表。

**Q: 支持多语言提示词吗？**

A: 当前版本主要支持中文。如需多语言，可为每种语言创建独立的提示词类别。

**Q: 测试用例会消耗多少LLM配额？**

A: 每个测试用例会调用一次LLM。建议使用成本较低的模型（如 GPT-3.5）进行测试。

**Q: 如何监控提示词性能？**

A: 查看 `prompt_evaluations` 表的评估记录，可按提示词ID统计平均分、通过率等指标。

## 十二、未来规划

- [ ] 前端集成版本对比组件
- [ ] 前端集成版本历史组件
- [ ] A/B测试功能
- [ ] 提示词性能监控仪表板
- [ ] 自动化提示词优化建议
- [ ] 多语言支持
- [ ] 提示词市场（社区分享）
- [ ] 高级diff算法（语义级对比）
- [ ] LLM自动评估（使用更强大的模型评估输出质量）

---

**更新时间**: 2025-10-18

**版本**: 1.0.0

**维护者**: FastNPC开发团队

