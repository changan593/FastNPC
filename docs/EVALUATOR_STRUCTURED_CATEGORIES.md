# 评估提示词结构化类别扩展

## 概述

本文档记录了将结构化生成评估器从单一评估器扩展为9大类别专用评估器的改进工作。

## 问题背景

原有的评估提示词系统中，结构化生成只有一个通用评估器 `EVALUATOR_STRUCTURED_GEN`，但实际的结构化生成包含9大类别：

1. 基础身份信息
2. 性格特征
3. 背景经历
4. 外貌特征
5. 行为习惯
6. 人际关系
7. 技能特长
8. 价值观信念
9. 情感倾向

每个类别的评估侧重点和标准都不同，使用单一评估器无法提供针对性的评估。

## 解决方案

### 1. 前端改进

**文件**: `web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`

#### 1.1 扩展评估类别定义

```typescript
const EVALUATION_CATEGORIES = {
  // 结构化生成评估器（9大类别）
  'EVALUATOR_BASIC_INFO': { name: '基础身份信息评估器', icon: '📋' },
  'EVALUATOR_PERSONALITY': { name: '性格特征评估器', icon: '🎭' },
  'EVALUATOR_BACKGROUND': { name: '背景经历评估器', icon: '📖' },
  'EVALUATOR_APPEARANCE': { name: '外貌特征评估器', icon: '👤' },
  'EVALUATOR_BEHAVIOR': { name: '行为习惯评估器', icon: '🚶' },
  'EVALUATOR_RELATIONSHIPS': { name: '人际关系评估器', icon: '🤝' },
  'EVALUATOR_SKILLS': { name: '技能特长评估器', icon: '🎯' },
  'EVALUATOR_VALUES': { name: '价值观信念评估器', icon: '💭' },
  'EVALUATOR_EMOTIONS': { name: '情感倾向评估器', icon: '❤️' },
  
  // 其他评估器
  'EVALUATOR_BRIEF_GEN': { name: '简介生成评估器', icon: '📝' },
  'EVALUATOR_SINGLE_CHAT': { name: '单聊对话评估器', icon: '💬' },
  'EVALUATOR_GROUP_CHAT': { name: '群聊对话评估器', icon: '👥' },
  'EVALUATOR_STM_COMPRESSION': { name: '短期记忆凝练评估器', icon: '🧠' },
  'EVALUATOR_LTM_INTEGRATION': { name: '长期记忆整合评估器', icon: '💾' },
  'EVALUATOR_GROUP_MODERATOR': { name: '群聊中控评估器', icon: '🎮' }
}
```

#### 1.2 更新评估器映射逻辑

```typescript
function getAvailableEvaluatorVersions(config: TestConfig) {
  // 根据提示词类别映射到评估器类别
  let evaluatorCategory = ''
  
  // 结构化生成需要根据子类别细化
  if (config.promptCategory === 'STRUCTURED_GEN' && config.promptSubCategory) {
    const structuredEvaluatorMap: Record<string, string> = {
      '基础身份信息': 'EVALUATOR_BASIC_INFO',
      '性格特征': 'EVALUATOR_PERSONALITY',
      '背景经历': 'EVALUATOR_BACKGROUND',
      '外貌特征': 'EVALUATOR_APPEARANCE',
      '行为习惯': 'EVALUATOR_BEHAVIOR',
      '人际关系': 'EVALUATOR_RELATIONSHIPS',
      '技能特长': 'EVALUATOR_SKILLS',
      '价值观信念': 'EVALUATOR_VALUES',
      '情感倾向': 'EVALUATOR_EMOTIONS'
    }
    evaluatorCategory = structuredEvaluatorMap[config.promptSubCategory] || ''
  } else {
    // 其他类别的映射
    const evaluatorCategoryMap: Record<string, string> = {
      'SINGLE_CHAT_SYSTEM': 'EVALUATOR_SINGLE_CHAT',
      'GROUP_CHAT_CHARACTER': 'EVALUATOR_GROUP_CHAT',
      'BRIEF_GEN': 'EVALUATOR_BRIEF_GEN',
      'SINGLE_CHAT_STM_COMPRESSION': 'EVALUATOR_STM_COMPRESSION',
      'GROUP_CHAT_STM_COMPRESSION': 'EVALUATOR_STM_COMPRESSION',
      'LTM_INTEGRATION': 'EVALUATOR_LTM_INTEGRATION',
      'GROUP_MODERATOR': 'EVALUATOR_GROUP_MODERATOR'
    }
    evaluatorCategory = evaluatorCategoryMap[config.promptCategory] || ''
  }
  
  if (!evaluatorCategory) return []
  
  return prompts.filter(p => p.category === evaluatorCategory)
}
```

### 2. 后端改进

**文件**: `fastnpc/scripts/init_evaluation_prompts.py`

#### 2.1 创建9个专用评估器

为每个结构化生成类别创建了专门的评估器，每个评估器都有针对性的评估维度：

1. **基础身份信息评估器** (`EVALUATOR_BASIC_INFO`)
   - 评估维度：完整性、准确性、相关性
   
2. **性格特征评估器** (`EVALUATOR_PERSONALITY`)
   - 评估维度：深度、准确性、可用性
   
3. **背景经历评估器** (`EVALUATOR_BACKGROUND`)
   - 评估维度：时间线清晰度、重要性筛选、叙述质量
   
4. **外貌特征评估器** (`EVALUATOR_APPEARANCE`)
   - 评估维度：具体性、准确性、视觉化
   
5. **行为习惯评估器** (`EVALUATOR_BEHAVIOR`)
   - 评估维度：代表性、具体性、可操作性
   
6. **人际关系评估器** (`EVALUATOR_RELATIONSHIPS`)
   - 评估维度：完整性、关系深度、重要性排序
   
7. **技能特长评估器** (`EVALUATOR_SKILLS`)
   - 评估维度：准确性、相关性、层次性
   
8. **价值观信念评估器** (`EVALUATOR_VALUES`)
   - 评估维度：深度、一致性、可操作性
   
9. **情感倾向评估器** (`EVALUATOR_EMOTIONS`)
   - 评估维度：准确性、丰富性、表现力

#### 2.2 评估器模板示例

以基础身份信息评估器为例：

```python
{
    "category": "EVALUATOR_BASIC_INFO",
    "name": "基础身份信息评估器",
    "description": "评估基础身份信息提取的质量",
    "template_content": """你是一个专业的基础身份信息质量评估专家。请评估以下生成的基础身份信息的质量。

【原始素材】
{source_text}

【生成的基础身份信息】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **完整性** (Completeness)
   - 是否包含姓名、年龄、性别、职业等核心信息
   - 信息是否足够详实
   
2. **准确性** (Accuracy)
   - 提取的信息是否与原文一致
   - 是否有事实性错误
   
3. **相关性** (Relevance)
   - 提取的信息是否都属于基础身份范畴
   - 是否混入了其他类别的信息

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "completeness": 8.5,
    "accuracy": 9.0,
    "relevance": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```

评分标准：
- 总分 >= 24: 优秀 (passed: true)
- 总分 21-23: 良好 (passed: true)
- 总分 18-20: 合格 (passed: true)
- 总分 < 18: 不合格 (passed: false)
"""
}
```

## 实施结果

### 数据库记录

运行 `init_evaluation_prompts.py` 脚本后，成功创建了9个新的评估器：

```
[SUCCESS] 创建评估器: 基础身份信息评估器 (ID: 43)
[SUCCESS] 创建评估器: 性格特征评估器 (ID: 44)
[SUCCESS] 创建评估器: 背景经历评估器 (ID: 45)
[SUCCESS] 创建评估器: 外貌特征评估器 (ID: 46)
[SUCCESS] 创建评估器: 行为习惯评估器 (ID: 47)
[SUCCESS] 创建评估器: 人际关系评估器 (ID: 48)
[SUCCESS] 创建评估器: 技能特长评估器 (ID: 49)
[SUCCESS] 创建评估器: 价值观信念评估器 (ID: 50)
[SUCCESS] 创建评估器: 情感倾向评估器 (ID: 51)
```

### 前端界面

在"提示词与测试管理"模态框的"⭐ 评估提示词"标签页中，现在显示15个评估器类别（9个结构化生成 + 6个其他类型）。

## 使用方法

### 1. 在测试执行标签页

当配置测试时，如果选择的是结构化生成类别的提示词：
- 系统会根据提示词的子类别（如"基础身份信息"）自动匹配对应的评估器（如"基础身份信息评估器"）
- 在评估器版本下拉框中，只会显示该类别的评估器版本

### 2. 在评估提示词标签页

可以：
- 查看每个评估器的模板内容
- 编辑评估维度和评分标准
- 创建新版本
- 激活/停用特定版本

### 3. 评估器模板变量

每个评估器都支持特定的模板变量：

- **结构化生成评估器**（9大类）：
  - `{source_text}`: 原始素材
  - `{generated_content}`: 生成的结构化内容

- **其他评估器**：
  - 单聊/群聊：`{character_info}`, `{chat_history}`, `{latest_response}`, 等
  - 记忆凝练/整合：`{original_messages}`, `{compressed_memory}`, 等
  - 群聊中控：`{group_info}`, `{available_characters}`, `{selected_character}`, 等

## 技术细节

### 1. 数据类型处理

在脚本中正确处理了 PostgreSQL 的数据类型：

```python
if USE_POSTGRESQL:
    # is_active 是 integer 类型，不是 boolean
    is_active = 1  # 而非 True
    
    # created_at 是 bigint 类型，不需要 to_timestamp()
    created_at = now  # 而非 to_timestamp(now)
```

### 2. 版本历史记录

为每个新创建的评估器都创建了初始版本历史：

```python
cur.execute("""
    INSERT INTO prompt_version_history
    (prompt_template_id, version, change_log, previous_content, created_by, created_at)
    VALUES (%s, %s, %s, %s, %s, %s)
""", (
    prompt_id,
    '1.0.0',
    '初始版本',
    None,  # 初始版本没有 previous_content
    admin_id,
    now
))
```

### 3. 前端清理

移除了以下不再使用的代码：
- `const [executions, setExecutions] = useState<TestExecution[]>([])` 状态
- `async function loadExecutions(testCaseId: number)` 函数
- `TestExecution` 类型导入
- 相关的 useEffect 依赖

## 优势

1. **精准评估**：每个结构化生成类别都有针对性的评估标准
2. **灵活配置**：可以为每个类别独立调整评估维度和权重
3. **版本管理**：支持对评估器进行版本控制和A/B测试
4. **可扩展性**：未来可以轻松添加新的评估维度或类别

## 后续改进建议

1. **评估结果可视化**：为每个维度添加雷达图或柱状图展示
2. **批量评估对比**：支持同时对比多个提示词版本的评估结果
3. **评估器质量监控**：追踪评估器的准确性和一致性
4. **自动化调优**：根据评估结果自动建议提示词优化方向

## 相关文件

- 前端：`web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`
- 初始化脚本：`fastnpc/scripts/init_evaluation_prompts.py`
- 数据库迁移：已在 `db_init.py` 中定义表结构
- 样式：`web/fastnpc-web/src/components/modals/PromptManagementModal.css`

## 更新日期

2025-10-19

