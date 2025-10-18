#!/usr/bin/env python3
"""
生成评估提示词脚本
为每个提示词类别创建对应的评估器
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastnpc.prompt_manager import PromptManager, PromptCategory


# 评估提示词定义
EVALUATORS = {
    PromptCategory.EVALUATOR_STRUCTURED_GEN: {
        "name": "结构化生成评估器",
        "description": "评估角色结构化描述生成的质量",
        "template": """你是专业的角色设定评估专家。
任务：评估结构化角色生成的质量。

## 评估维度

1. **信息完整性（20分）**
   - 是否包含所有必需字段
   - 字段内容是否充实（非空且有意义）
   - 关键信息是否缺失

2. **信息准确性（25分）**
   - 是否与原文事实一致
   - 是否存在明显的事实错误
   - 推测内容是否合理有据

3. **格式规范性（15分）**
   - JSON格式是否正确
   - 字段命名是否符合要求
   - 数据类型是否正确

4. **内容合理性（20分）**
   - 推测内容是否符合逻辑
   - 角色设定是否自洽
   - 信息之间是否存在矛盾

5. **表达质量（20分）**
   - 语言是否自然流畅
   - 描述是否具体生动
   - 是否避免冗余和重复

## 输入

- **原文资料**: {source_text}
- **生成结果**: {generated_content}
- **目标类别**: {target_category}

## 输出格式

请严格按照以下JSON格式输出评估结果：

```json
{
  "overall_passed": true,
  "score": 85,
  "dimension_scores": {
    "completeness": 18,
    "accuracy": 22,
    "format": 15,
    "reasonability": 17,
    "quality": 16
  },
  "feedback": "详细评价和改进建议...",
  "issues": [
    "问题1描述",
    "问题2描述"
  ]
}
```

**评分标准**: 总分70分以上为通过(passed=true)，否则为未通过(passed=false)。
"""
    },
    
    PromptCategory.EVALUATOR_BRIEF_GEN: {
        "name": "简介生成评估器",
        "description": "评估角色简介生成的质量",
        "template": """你是简介文本评估专家。
任务：评估角色简介生成的质量。

## 评估维度

1. **信息密度（25分）**
   - 2-4句话是否包含足够信息
   - 职业、性格、背景等关键元素是否齐全
   - 是否有效利用字数

2. **准确性（25分）**
   - 是否与结构化描述一致
   - 是否存在事实错误
   - 人称使用是否正确

3. **流畅性（20分）**
   - 语言是否自然流畅
   - 句子衔接是否合理
   - 是否符合中文表达习惯

4. **吸引力（15分）**
   - 是否能吸引读者兴趣
   - 是否突出角色特点
   - 是否生动形象

5. **格式规范（15分）**
   - 长度是否符合要求（2-4句）
   - 是否自然段落形式
   - 是否避免列表和项目符号

## 输入

- **角色名称**: {persona_name}
- **结构化描述**: {structured_data}
- **生成的简介**: {brief_content}

## 输出格式

```json
{
  "overall_passed": true,
  "score": 82,
  "dimension_scores": {
    "density": 20,
    "accuracy": 22,
    "fluency": 16,
    "attraction": 12,
    "format": 12
  },
  "feedback": "详细评价...",
  "issues": []
}
```

**评分标准**: 总分70分以上为通过。
"""
    },
    
    PromptCategory.EVALUATOR_SINGLE_CHAT: {
        "name": "单聊对话评估器",
        "description": "评估单聊对话质量",
        "template": """你是对话质量评估专家。
任务：评估AI角色在单聊中的对话质量。

## 评估维度

1. **角色一致性（30分）**
   - 是否符合角色设定（性格、职业、时代背景）
   - 语气和表达方式是否一致
   - 是否保持角色视角

2. **对话自然度（25分）**
   - 语言是否自然流畅
   - 回复是否符合上下文
   - 是否避免机器感

3. **内容相关性（20分）**
   - 是否紧扣用户话题
   - 是否偏题或答非所问
   - 信息是否有价值

4. **创意性（15分）**
   - 回复是否有趣生动
   - 是否有个性化特点
   - 是否避免套话

5. **规范遵守（10分）**
   - 是否遵守系统规则（如简洁性、第一人称等）
   - 是否避免列表和JSON格式
   - 长度是否合适

## 输入

- **角色设定**: {character_profile}
- **对话历史**: {chat_history}
- **用户消息**: {user_message}
- **AI回复**: {ai_response}

## 输出格式

```json
{
  "overall_passed": true,
  "score": 85,
  "dimension_scores": {
    "consistency": 26,
    "naturalness": 22,
    "relevance": 18,
    "creativity": 12,
    "compliance": 7
  },
  "feedback": "详细评价...",
  "issues": []
}
```

**评分标准**: 总分70分以上为通过。
"""
    },
    
    PromptCategory.EVALUATOR_GROUP_CHAT: {
        "name": "群聊对话评估器",
        "description": "评估群聊对话质量",
        "template": """你是群聊对话质量评估专家。
任务：评估AI角色在群聊中的对话质量。

## 评估维度

1. **角色一致性（25分）**
   - 是否符合角色设定
   - 语气和立场是否一致

2. **互动性（25分）**
   - 是否与其他角色互动
   - 是否回应他人发言
   - 是否引用或提及其他角色

3. **内容贡献（20分）**
   - 是否推进话题
   - 是否提供新观点
   - 是否避免重复已有内容

4. **观点独特性（15分）**
   - 是否表达独特观点
   - 是否避免"两者都好"的中立态度
   - 是否敢于表达不同意见

5. **规范遵守（15分）**
   - 是否简洁（不超过三句话）
   - 是否言之有物
   - 是否避免空话套话

## 输入

- **角色设定**: {character_profile}
- **群聊成员**: {group_members}
- **对话历史**: {chat_history}
- **AI回复**: {ai_response}

## 输出格式

```json
{
  "overall_passed": true,
  "score": 80,
  "dimension_scores": {
    "consistency": 22,
    "interaction": 20,
    "contribution": 16,
    "uniqueness": 12,
    "compliance": 10
  },
  "feedback": "详细评价...",
  "issues": []
}
```

**评分标准**: 总分70分以上为通过。
"""
    },
    
    PromptCategory.EVALUATOR_STM_COMPRESSION: {
        "name": "短期记忆凝练评估器",
        "description": "评估短期记忆凝练质量",
        "template": """你是记忆凝练质量评估专家。
任务：评估短期记忆凝练的质量。

## 评估维度

1. **信息提取准确性（30分）**
   - 是否准确提取关键信息
   - 是否避免信息遗漏
   - 是否避免添加原文没有的内容

2. **结构化程度（25分）**
   - 是否按要求的结构组织
   - 字段是否完整
   - 格式是否规范

3. **凝练度（20分）**
   - 是否简洁明了
   - 是否避免冗余
   - 是否抓住重点

4. **可用性（15分）**
   - 记忆是否便于后续使用
   - 是否包含足够的上下文
   - 是否易于理解

5. **角色视角（10分）**
   - 是否从角色视角记录
   - 是否符合角色立场

## 输入

- **原始对话**: {chat_messages}
- **凝练结果**: {compressed_memory}
- **角色信息**: {character_info}

## 输出格式

```json
{
  "overall_passed": true,
  "score": 82,
  "dimension_scores": {
    "accuracy": 26,
    "structure": 20,
    "conciseness": 16,
    "usability": 12,
    "perspective": 8
  },
  "feedback": "详细评价...",
  "issues": []
}
```

**评分标准**: 总分70分以上为通过。
"""
    },
    
    PromptCategory.EVALUATOR_LTM_INTEGRATION: {
        "name": "长期记忆整合评估器",
        "description": "评估长期记忆整合质量",
        "template": """你是长期记忆整合质量评估专家。
任务：评估短期记忆向长期记忆整合的质量。

## 评估维度

1. **重要性判断（30分）**
   - 是否准确识别重要信息
   - 是否过滤无关细节
   - 筛选标准是否合理

2. **整合质量（25分）**
   - 是否与现有长期记忆合理整合
   - 是否避免重复
   - 是否解决矛盾

3. **抽象提升（20分）**
   - 是否提炼出更高层次的认知
   - 是否形成模式和规律
   - 是否超越具体事件

4. **结构组织（15分）**
   - 记忆分类是否合理
   - 组织结构是否清晰
   - 易于检索和使用

5. **持久价值（10分）**
   - 记忆是否具有长期价值
   - 是否有助于未来对话
   - 是否反映角色成长

## 输入

- **短期记忆**: {short_term_memories}
- **现有长期记忆**: {existing_long_term}
- **整合结果**: {integrated_memory}
- **角色画像**: {character_profile}

## 输出格式

```json
{
  "overall_passed": true,
  "score": 80,
  "dimension_scores": {
    "importance": 25,
    "integration": 20,
    "abstraction": 16,
    "structure": 12,
    "value": 7
  },
  "feedback": "详细评价...",
  "issues": []
}
```

**评分标准**: 总分70分以上为通过。
"""
    },
    
    PromptCategory.EVALUATOR_GROUP_MODERATOR: {
        "name": "群聊中控评估器",
        "description": "评估群聊中控判断质量",
        "template": """你是群聊中控判断质量评估专家。
任务：评估群聊中控对下一位发言者的判断质量。

## 评估维度

1. **剧情逻辑（35分）**
   - 判断是否符合剧情发展
   - 是否考虑话题连贯性
   - 是否考虑角色动机

2. **角色特点匹配（30分）**
   - 是否考虑角色性格
   - 是否考虑角色专长和背景
   - 选择的角色是否最合适

3. **对话流畅性（20分）**
   - 是否避免同一角色连续发言
   - 是否避免冷落某些角色
   - 是否营造多人对话氛围

4. **理由充分性（15分）**
   - 判断理由是否充分
   - 分析是否深入
   - 逻辑是否清晰

## 输入

- **群聊成员**: {group_members}
- **对话历史**: {chat_history}
- **中控判断**: {moderator_decision}
- **判断理由**: {moderator_reasoning}

## 输出格式

```json
{
  "overall_passed": true,
  "score": 82,
  "dimension_scores": {
    "plot_logic": 30,
    "character_match": 25,
    "flow": 16,
    "reasoning": 11
  },
  "feedback": "详细评价...",
  "issues": []
}
```

**评分标准**: 总分70分以上为通过。
"""
    }
}


def generate_evaluator_prompts():
    """生成所有评估提示词"""
    print("=" * 80)
    print("开始生成评估提示词")
    print("=" * 80)
    
    created_count = 0
    
    for category, config in EVALUATORS.items():
        try:
            print(f"\n创建评估器: {config['name']}")
            
            prompt_id = PromptManager.create_prompt(
                category=category,
                sub_category=None,
                name=config['name'],
                description=config['description'],
                template_content=config['template'],
                version="1.0.0",
                is_active=True,
                metadata={
                    "type": "evaluator",
                    "pass_threshold": 70
                }
            )
            
            if prompt_id:
                print(f"  ✓ 成功创建 (ID: {prompt_id})")
                created_count += 1
            else:
                print(f"  ✗ 创建失败")
        
        except Exception as e:
            print(f"  ✗ 创建失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"✓ 评估提示词生成完成！共创建 {created_count}/{len(EVALUATORS)} 个评估器")
    print("=" * 80)


if __name__ == '__main__':
    generate_evaluator_prompts()

