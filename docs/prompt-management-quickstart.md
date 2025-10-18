# 提示词管理系统快速入门

## 🚀 5分钟上手

### 1. 初始化数据（首次使用）

```bash
cd /home/changan/MyProject/FastNPC

# 导入17个提示词模板
python -m fastnpc.scripts.init_prompts

# 导入12个测试用例
python -m fastnpc.scripts.init_test_cases
```

### 2. 启用数据库提示词

编辑 `.env` 文件：

```bash
USE_DB_PROMPTS=true
```

### 3. 访问管理界面

1. 启动服务器：`python -m uvicorn fastnpc.api.server:app --reload`
2. 访问 http://localhost:8000
3. 管理员登录
4. 点击顶部"管理员"按钮
5. 点击"🎯 提示词管理"

### 4. 编辑提示词

```
1. 左侧选择分类
2. 中间编辑内容
3. 点击"💾 保存"
4. 点击"✓ 激活此版本"
```

### 5. 运行测试

点击右侧"▶️ 运行测试"按钮，查看自动化测试结果。

## 📊 提示词分类速查

| 类别 | 用途 | 变量 |
|------|------|------|
| 结构化生成 | 从原始文本生成角色档案 | `persona_name`, `facts_markdown` |
| 简介生成 | 生成简洁人物简介 | `persona_name`, `person`, `role_json` |
| 单聊系统 | 单聊固定规则 | `display_name`, `user_name` |
| 短期记忆凝练（单聊） | 提取对话关键信息 | `role_name`, `user_name`, `chat_to_compress` |
| 短期记忆凝练（群聊） | 提取群聊关键信息 | `role_name`, `participants_list`, `chat_to_compress` |
| 长期记忆整合 | 整合短期记忆 | `role_profile_summary`, `short_memories_to_integrate` |
| 群聊中控 | 判断下一位发言者 | `participants`, `recent_messages` |
| 群聊角色发言 | 群聊角色系统提示 | `display_name`, `other_members` |
| 结构化系统消息 | 结构化生成通用指令 | 无 |

## 🧪 命令行工具

```bash
# 运行所有测试
python -m fastnpc.scripts.run_prompt_tests

# 运行单个测试
python -m fastnpc.scripts.run_prompt_tests <prompt_id> <test_case_id>

# 生成测试报告
python -m fastnpc.scripts.generate_test_report
```

## 🔧 常用API

### 获取激活的提示词

```python
from fastnpc.prompt_manager import PromptManager, PromptCategory

prompt = PromptManager.get_active_prompt(PromptCategory.SINGLE_CHAT_SYSTEM)
```

### 渲染提示词

```python
rendered = PromptManager.render_prompt(
    prompt['template_content'],
    {"display_name": "李白", "user_name": "小明"}
)
```

### 清除缓存

```python
PromptManager.clear_cache()  # 清除所有
PromptManager.clear_cache("SINGLE_CHAT_SYSTEM")  # 清除指定类别
```

## ⚠️ 注意事项

1. **每次保存创建新版本**：无法直接修改已有版本
2. **需要手动激活**：保存后需点击"激活"才能生效
3. **变量区分大小写**：`{Display_Name}` ≠ `{display_name}`
4. **清除缓存**：激活新版本后建议清除Redis缓存
5. **测试先行**：修改提示词后务必运行测试

## 📚 完整文档

查看 [提示词管理系统使用指南](./prompt-management-guide.md) 获取详细信息。

---

**提示**: 遇到问题先检查：
1. 提示词是否已激活？
2. Redis缓存是否已清除？
3. `USE_DB_PROMPTS` 是否为 `true`？
4. 数据库表是否已创建？

