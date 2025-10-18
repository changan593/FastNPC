# -*- coding: utf-8 -*-
"""
评估提示词初始化脚本

为各类提示词创建专业的评估器
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import time
from fastnpc.api.auth import _get_conn, _return_conn
from fastnpc.config import USE_POSTGRESQL


EVALUATION_PROMPTS = [
    {
        "category": "EVALUATOR_STRUCTURED_GEN",
        "name": "结构化生成评估器",
        "description": "评估结构化角色生成的质量（完整性、准确性、一致性）",
        "template_content": """你是一个专业的角色结构化生成质量评估专家。请评估以下生成的结构化角色信息的质量。

【原始素材】
{source_text}

【生成的结构化信息】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **完整性** (Completeness)
   - 是否涵盖了所有关键信息分类
   - 每个分类下的内容是否充实
   
2. **准确性** (Accuracy)
   - 提取的信息是否与原文一致
   - 是否有事实性错误或曲解

3. **一致性** (Consistency)
   - 各分类之间是否存在矛盾
   - 整体人物形象是否统一

4. **结构性** (Structure)
   - 信息组织是否清晰
   - 分类是否合理

5. **可用性** (Usability)
   - 生成的信息是否便于理解和使用
   - 是否包含足够的细节用于对话生成

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "completeness": 8.5,
    "accuracy": 9.0,
    "consistency": 8.0,
    "structure": 9.0,
    "usability": 8.5
  },
  "total_score": 43.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```

评分标准：
- 总分 >= 40: 优秀 (passed: true)
- 总分 35-39: 良好 (passed: true)
- 总分 30-34: 合格 (passed: true)
- 总分 < 30: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-50"
        }
    },
    {
        "category": "EVALUATOR_BRIEF_GEN",
        "name": "简介生成评估器",
        "description": "评估角色简介生成的质量（吸引力、准确性、长度适中）",
        "template_content": """你是一个专业的角色简介质量评估专家。请评估以下生成的角色简介的质量。

【角色名称】{character_name}

【角色完整信息】
{full_character_info}

【生成的简介】
{generated_brief}

请从以下维度进行评估（每项0-10分）：

1. **吸引力** (Appeal)
   - 简介是否引人入胜
   - 是否能激发用户对话兴趣

2. **准确性** (Accuracy)
   - 简介是否准确概括角色特征
   - 是否有事实错误

3. **简洁性** (Conciseness)
   - 长度是否适中（建议80-150字）
   - 是否言简意赅

4. **完整性** (Completeness)
   - 是否涵盖核心特征（身份、性格、特色）
   - 关键信息是否完整

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "appeal": 8.5,
    "accuracy": 9.0,
    "conciseness": 8.0,
    "completeness": 8.5
  },
  "total_score": 34.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "word_count": 120,
  "suggestions": ["改进建议1", "改进建议2"]
}
```

评分标准：
- 总分 >= 32: 优秀 (passed: true)
- 总分 28-31: 良好 (passed: true)
- 总分 24-27: 合格 (passed: true)
- 总分 < 24: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["character_name", "full_character_info", "generated_brief"],
            "output_format": "json",
            "scoring_range": "0-40"
        }
    },
    {
        "category": "EVALUATOR_SINGLE_CHAT",
        "name": "单聊对话评估器",
        "description": "评估单聊对话的质量（角色一致性、流畅性、合理性）",
        "template_content": """你是一个专业的对话质量评估专家。请评估以下单聊对话的质量。

【角色信息】
{character_profile}

【对话历史】
{conversation_history}

【用户输入】{user_message}

【AI回复】{ai_response}

请从以下维度进行评估（每项0-10分）：

1. **角色一致性** (Character Consistency)
   - 回复是否符合角色设定
   - 语气、风格是否保持一致

2. **内容相关性** (Relevance)
   - 回复是否切题
   - 是否恰当回应用户问题

3. **流畅性** (Fluency)
   - 语言是否自然流畅
   - 是否有语法错误或表达不清

4. **深度** (Depth)
   - 回复是否有深度和见解
   - 是否展现了角色的专业知识

5. **互动性** (Engagement)
   - 回复是否能推进对话
   - 是否引导用户继续交流

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "character_consistency": 9.0,
    "relevance": 8.5,
    "fluency": 9.0,
    "depth": 8.0,
    "engagement": 8.5
  },
  "total_score": 43.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "highlights": ["精彩之处1", "精彩之处2"],
  "issues": ["问题点1", "问题点2"]
}
```

评分标准：
- 总分 >= 40: 优秀 (passed: true)
- 总分 35-39: 良好 (passed: true)
- 总分 30-34: 合格 (passed: true)
- 总分 < 30: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["character_profile", "conversation_history", "user_message", "ai_response"],
            "output_format": "json",
            "scoring_range": "0-50"
        }
    },
    {
        "category": "EVALUATOR_GROUP_CHAT",
        "name": "群聊对话评估器",
        "description": "评估群聊对话的质量（多角色协调、氛围营造）",
        "template_content": """你是一个专业的群聊对话质量评估专家。请评估以下群聊对话的质量。

【群聊成员】
{group_members}

【对话历史】
{conversation_history}

【用户输入】{user_message}

【AI回复轮次】
{ai_responses}

请从以下维度进行评估（每项0-10分）：

1. **角色区分度** (Character Differentiation)
   - 各角色是否保持各自特色
   - 发言风格是否有区分度

2. **互动质量** (Interaction Quality)
   - 角色间的互动是否自然
   - 是否有有趣的碰撞和火花

3. **调度合理性** (Moderation)
   - 发言顺序是否合理
   - 轮次分配是否适当

4. **内容连贯性** (Coherence)
   - 对话是否连贯
   - 话题是否聚焦

5. **氛围营造** (Atmosphere)
   - 是否营造了良好的群聊氛围
   - 是否有群聊的"群感"

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "character_differentiation": 8.5,
    "interaction_quality": 9.0,
    "moderation": 8.0,
    "coherence": 8.5,
    "atmosphere": 9.0
  },
  "total_score": 43.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "best_moments": ["精彩互动1", "精彩互动2"],
  "improvements": ["改进建议1", "改进建议2"]
}
```

评分标准：
- 总分 >= 40: 优秀 (passed: true)
- 总分 35-39: 良好 (passed: true)
- 总分 30-34: 合格 (passed: true)
- 总分 < 30: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["group_members", "conversation_history", "user_message", "ai_responses"],
            "output_format": "json",
            "scoring_range": "0-50"
        }
    },
    {
        "category": "EVALUATOR_STM_COMPRESSION",
        "name": "短期记忆凝练评估器",
        "description": "评估短期记忆凝练的质量（信息提取、压缩比、重点突出）",
        "template_content": """你是一个专业的记忆凝练质量评估专家。请评估以下短期记忆凝练的质量。

【原始对话】
{original_messages}

【凝练后的短期记忆】
{compressed_memory}

请从以下维度进行评估（每项0-10分）：

1. **信息保留度** (Information Retention)
   - 关键信息是否完整保留
   - 是否遗漏重要细节

2. **压缩率** (Compression Ratio)
   - 压缩是否适度（建议压缩到20-30%）
   - 是否去除了冗余信息

3. **重点突出** (Focus)
   - 是否突出了核心内容
   - 主次是否分明

4. **可读性** (Readability)
   - 凝练后的内容是否清晰易懂
   - 结构是否合理

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "information_retention": 8.5,
    "compression_ratio": 9.0,
    "focus": 8.5,
    "readability": 9.0
  },
  "total_score": 35.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "compression_percentage": 25.5,
  "key_points_extracted": 5
}
```

评分标准：
- 总分 >= 32: 优秀 (passed: true)
- 总分 28-31: 良好 (passed: true)
- 总分 24-27: 合格 (passed: true)
- 总分 < 24: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["original_messages", "compressed_memory"],
            "output_format": "json",
            "scoring_range": "0-40"
        }
    },
    {
        "category": "EVALUATOR_LTM_INTEGRATION",
        "name": "长期记忆整合评估器",
        "description": "评估长期记忆整合的质量（去重、归纳、重要性排序）",
        "template_content": """你是一个专业的记忆整合质量评估专家。请评估以下长期记忆整合的质量。

【原有长期记忆】
{existing_ltm}

【新增短期记忆】
{new_stm}

【整合后的长期记忆】
{integrated_ltm}

请从以下维度进行评估（每项0-10分）：

1. **去重效果** (Deduplication)
   - 是否成功去除重复信息
   - 相似信息是否合并

2. **归纳总结** (Summarization)
   - 是否进行了有效归纳
   - 概括是否准确

3. **重要性排序** (Priority Ranking)
   - 重要信息是否优先保留
   - 排序是否合理

4. **结构组织** (Organization)
   - 记忆结构是否清晰
   - 分类是否合理

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "deduplication": 8.5,
    "summarization": 8.0,
    "priority_ranking": 9.0,
    "organization": 8.5
  },
  "total_score": 34.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "memories_kept": 15,
  "memories_removed": 5,
  "memories_merged": 3
}
```

评分标准：
- 总分 >= 32: 优秀 (passed: true)
- 总分 28-31: 良好 (passed: true)
- 总分 24-27: 合格 (passed: true)
- 总分 < 24: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["existing_ltm", "new_stm", "integrated_ltm"],
            "output_format": "json",
            "scoring_range": "0-40"
        }
    },
    {
        "category": "EVALUATOR_GROUP_MODERATOR",
        "name": "群聊中控评估器",
        "description": "评估群聊中控决策的质量（选人准确性、理由合理性）",
        "template_content": """你是一个专业的群聊中控决策评估专家。请评估以下中控决策的质量。

【群聊成员】
{group_members}

【对话历史】
{conversation_history}

【用户输入】{user_message}

【中控决策】
选择角色: {chosen_character}
置信度: {confidence}
决策理由: {reasoning}

请从以下维度进行评估（每项0-10分）：

1. **选人准确性** (Selection Accuracy)
   - 选择的角色是否最适合回复
   - 是否考虑了角色特长和话题相关性

2. **理由合理性** (Reasoning Quality)
   - 决策理由是否充分
   - 逻辑是否清晰

3. **置信度校准** (Confidence Calibration)
   - 置信度是否与实际匹配度相符
   - 是否过于自信或不自信

4. **公平性** (Fairness)
   - 是否给所有角色合理的发言机会
   - 是否避免了某个角色过度发言

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "selection_accuracy": 9.0,
    "reasoning_quality": 8.5,
    "confidence_calibration": 8.0,
    "fairness": 9.0
  },
  "total_score": 34.5,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "alternative_choices": ["备选角色1", "备选角色2"]
}
```

评分标准：
- 总分 >= 32: 优秀 (passed: true)
- 总分 28-31: 良好 (passed: true)
- 总分 24-27: 合格 (passed: true)
- 总分 < 24: 不合格 (passed: false)
""",
        "metadata": {
            "variables": ["group_members", "conversation_history", "user_message", "chosen_character", "confidence", "reasoning"],
            "output_format": "json",
            "scoring_range": "0-40"
        }
    }
]


def init_evaluation_prompts():
    """初始化评估提示词到数据库"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        now = int(time.time())
        
        created_count = 0
        for prompt_data in EVALUATION_PROMPTS:
            # 检查是否已存在
            cur.execute(
                f"SELECT id FROM prompt_templates WHERE category={placeholder} AND name={placeholder}",
                (prompt_data['category'], prompt_data['name'])
            )
            existing = cur.fetchone()
            
            if existing:
                print(f"[INFO] 评估提示词已存在: {prompt_data['name']}")
                continue
            
            # 插入新提示词
            import json
            metadata_json = json.dumps(prompt_data.get('metadata', {}), ensure_ascii=False)
            
            if USE_POSTGRESQL:
                cur.execute(
                    """
                    INSERT INTO prompt_templates(
                        category, sub_category, name, description, template_content,
                        version, is_active, created_by, created_at, updated_at, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (prompt_data['category'], None, prompt_data['name'], prompt_data['description'],
                     prompt_data['template_content'], "1.0.0", 1, 1, now, now, metadata_json)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO prompt_templates(
                        category, sub_category, name, description, template_content,
                        version, is_active, created_by, created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (prompt_data['category'], None, prompt_data['name'], prompt_data['description'],
                     prompt_data['template_content'], "1.0.0", 1, 1, now, now, metadata_json)
                )
            
            created_count += 1
            print(f"[INFO] 创建评估提示词: {prompt_data['name']}")
        
        conn.commit()
        print(f"\n✓ 评估提示词初始化完成！共创建 {created_count} 个评估器")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 初始化失败: {e}")
        raise
    finally:
        _return_conn(conn)


if __name__ == "__main__":
    print("=" * 60)
    print("开始初始化评估提示词...")
    print("=" * 60)
    init_evaluation_prompts()

