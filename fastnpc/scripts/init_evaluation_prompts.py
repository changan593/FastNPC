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
    # ===== 结构化生成评估器（9大类别）=====
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
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_PERSONALITY",
        "name": "性格特征评估器",
        "description": "评估性格特征描述的质量",
        "template_content": """你是一个专业的性格特征描述质量评估专家。请评估以下生成的性格特征的质量。

【原始素材】
{source_text}

【生成的性格特征】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **深度** (Depth)
   - 性格描述是否深入细致
   - 是否涵盖了性格的多个层面

2. **准确性** (Accuracy)
   - 性格描述是否与原文一致
   - 是否有曲解或误读

3. **可用性** (Usability)
   - 描述是否具体，便于角色扮演
   - 是否提供了足够的行为指导

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "depth": 8.5,
    "accuracy": 9.0,
    "usability": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```

评分标准：
- 总分 >= 24: 优秀
- 总分 21-23: 良好
- 总分 18-20: 合格
- 总分 < 18: 不合格
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_BACKGROUND",
        "name": "背景经历评估器",
        "description": "评估背景经历叙述的质量",
        "template_content": """你是一个专业的背景经历质量评估专家。请评估以下生成的背景经历的质量。

【原始素材】
{source_text}

【生成的背景经历】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **时间线清晰度** (Timeline Clarity)
   - 时间顺序是否清晰
   - 关键事件是否按时间组织

2. **重要性筛选** (Importance)
   - 是否抓住了关键转折点
   - 是否过滤了不重要的信息

3. **叙述质量** (Narrative Quality)
   - 叙述是否流畅连贯
   - 是否有助于理解角色的成长

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "timeline_clarity": 8.5,
    "importance": 9.0,
    "narrative_quality": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_APPEARANCE",
        "name": "外貌特征评估器",
        "description": "评估外貌特征描述的质量",
        "template_content": """你是一个专业的外貌特征描述质量评估专家。请评估以下生成的外貌特征的质量。

【原始素材】
{source_text}

【生成的外貌特征】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **具体性** (Specificity)
   - 描述是否具体而非笼统
   - 是否包含可识别的细节

2. **准确性** (Accuracy)
   - 描述是否与原文一致
   - 是否有捏造或夸大

3. **视觉化** (Visualization)
   - 描述是否易于在脑海中形成图像
   - 是否突出了特征性的外貌元素

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "specificity": 8.5,
    "accuracy": 9.0,
    "visualization": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_BEHAVIOR",
        "name": "行为习惯评估器",
        "description": "评估行为习惯描述的质量",
        "template_content": """你是一个专业的行为习惯描述质量评估专家。请评估以下生成的行为习惯的质量。

【原始素材】
{source_text}

【生成的行为习惯】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **代表性** (Representativeness)
   - 是否抓住了最具代表性的行为习惯
   - 是否能体现角色的个性

2. **具体性** (Specificity)
   - 行为描述是否具体可观察
   - 是否避免了模糊泛泛的描述

3. **可操作性** (Actionability)
   - 描述是否能指导实际的角色扮演
   - 是否便于在对话中体现

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "representativeness": 8.5,
    "specificity": 9.0,
    "actionability": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_RELATIONSHIPS",
        "name": "人际关系评估器",
        "description": "评估人际关系描述的质量",
        "template_content": """你是一个专业的人际关系描述质量评估专家。请评估以下生成的人际关系的质量。

【原始素材】
{source_text}

【生成的人际关系】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **完整性** (Completeness)
   - 是否涵盖了重要的人际关系
   - 关系网络是否完整

2. **关系深度** (Depth)
   - 关系描述是否深入具体
   - 是否说明了关系的性质和情感色彩

3. **重要性排序** (Prioritization)
   - 是否突出了最重要的关系
   - 是否合理分配了描述的篇幅

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "completeness": 8.5,
    "depth": 9.0,
    "prioritization": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_SKILLS",
        "name": "技能特长评估器",
        "description": "评估技能特长描述的质量",
        "template_content": """你是一个专业的技能特长描述质量评估专家。请评估以下生成的技能特长的质量。

【原始素材】
{source_text}

【生成的技能特长】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **准确性** (Accuracy)
   - 技能描述是否准确
   - 是否有夸大或低估

2. **相关性** (Relevance)
   - 是否提取了与角色最相关的技能
   - 是否遗漏了重要技能

3. **层次性** (Hierarchy)
   - 是否区分了核心技能和次要技能
   - 是否体现了技能的熟练程度

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "accuracy": 8.5,
    "relevance": 9.0,
    "hierarchy": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_VALUES",
        "name": "价值观信念评估器",
        "description": "评估价值观信念描述的质量",
        "template_content": """你是一个专业的价值观信念描述质量评估专家。请评估以下生成的价值观信念的质量。

【原始素材】
{source_text}

【生成的价值观信念】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **深度** (Depth)
   - 价值观描述是否深入本质
   - 是否能够指导角色的重大决策

2. **一致性** (Consistency)
   - 各价值观之间是否和谐统一
   - 是否符合角色的整体形象

3. **可操作性** (Actionability)
   - 价值观是否能够体现在具体行为中
   - 是否便于在对话中表达

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "depth": 8.5,
    "consistency": 9.0,
    "actionability": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_EMOTIONS",
        "name": "情感倾向评估器",
        "description": "评估情感倾向描述的质量",
        "template_content": """你是一个专业的情感倾向描述质量评估专家。请评估以下生成的情感倾向的质量。

【原始素材】
{source_text}

【生成的情感倾向】
{generated_content}

请从以下维度进行评估（每项0-10分）：

1. **准确性** (Accuracy)
   - 情感倾向是否准确反映原文
   - 是否捕捉到了关键的情感特质

2. **丰富性** (Richness)
   - 是否涵盖了多种情感维度
   - 是否避免了片面单一的描述

3. **表现力** (Expressiveness)
   - 描述是否生动具体
   - 是否便于在对话中展现

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "accuracy": 8.5,
    "richness": 9.0,
    "expressiveness": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["source_text", "generated_content"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    
    # ===== 其他评估器 =====
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

1. **吸引力** (Attractiveness)
   - 简介是否能吸引读者兴趣
   - 是否突出了角色的独特性

2. **准确性** (Accuracy)
   - 简介是否准确概括了角色特点
   - 是否有误导性信息

3. **长度适中** (Length)
   - 长度是否适合快速阅读（推荐50-150字）
   - 信息密度是否合适

4. **完整性** (Completeness)
   - 是否涵盖了角色的核心特征
   - 是否给读者完整的第一印象

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "attractiveness": 8.5,
    "accuracy": 9.0,
    "length": 8.0,
    "completeness": 8.5
  },
  "total_score": 34.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
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
        "description": "评估单聊对话的质量",
        "template_content": """你是一个专业的对话质量评估专家。请评估以下单聊对话的质量。

【角色信息】
{character_info}

【对话历史】
{chat_history}

【最新回复】
{latest_response}

请从以下维度进行评估（每项0-10分）：

1. **角色一致性** (Character Consistency)
   - 回复是否符合角色设定
   - 语气、用词是否符合角色性格

2. **上下文连贯性** (Context Coherence)
   - 回复是否与对话历史连贯
   - 是否正确理解了用户意图

3. **回复质量** (Response Quality)
   - 回复是否自然流畅
   - 是否有趣、有深度

4. **适当性** (Appropriateness)
   - 回复长度是否适中
   - 情感表达是否适当

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "character_consistency": 8.5,
    "context_coherence": 9.0,
    "response_quality": 8.5,
    "appropriateness": 8.0
  },
  "total_score": 34.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["character_info", "chat_history", "latest_response"],
            "output_format": "json",
            "scoring_range": "0-40"
        }
    },
    {
        "category": "EVALUATOR_GROUP_CHAT",
        "name": "群聊对话评估器",
        "description": "评估群聊对话的质量",
        "template_content": """你是一个专业的群聊对话质量评估专家。请评估以下群聊对话的质量。

【群聊信息】
{group_info}

【角色信息】
{character_info}

【对话历史】
{chat_history}

【最新回复】
{latest_response}

请从以下维度进行评估（每项0-10分）：

1. **角色一致性** (Character Consistency)
   - 回复是否符合角色设定

2. **互动性** (Interactivity)
   - 是否与其他角色产生互动
   - 是否推动群聊氛围

3. **回复质量** (Response Quality)
   - 回复是否自然有趣

4. **时机把握** (Timing)
   - 发言时机是否合适
   - 是否避免了抢话或沉默

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "character_consistency": 8.5,
    "interactivity": 9.0,
    "response_quality": 8.5,
    "timing": 8.0
  },
  "total_score": 34.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["group_info", "character_info", "chat_history", "latest_response"],
            "output_format": "json",
            "scoring_range": "0-40"
        }
    },
    {
        "category": "EVALUATOR_STM_COMPRESSION",
        "name": "短期记忆凝练评估器",
        "description": "评估短期记忆压缩的质量",
        "template_content": """你是一个专业的记忆压缩质量评估专家。请评估以下短期记忆凝练的质量。

【原始对话】
{original_messages}

【凝练后的记忆】
{compressed_memory}

请从以下维度进行评估（每项0-10分）：

1. **信息保留** (Information Retention)
   - 是否保留了关键信息
   - 是否遗漏了重要细节

2. **压缩效率** (Compression Efficiency)
   - 压缩比例是否合理
   - 是否去除了冗余信息

3. **可读性** (Readability)
   - 凝练后的文本是否通顺
   - 是否易于理解

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "information_retention": 8.5,
    "compression_efficiency": 9.0,
    "readability": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["original_messages", "compressed_memory"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_LTM_INTEGRATION",
        "name": "长期记忆整合评估器",
        "description": "评估长期记忆整合的质量",
        "template_content": """你是一个专业的长期记忆整合质量评估专家。请评估以下长期记忆整合的质量。

【短期记忆】
{short_term_memory}

【现有长期记忆】
{existing_long_term_memory}

【整合后的长期记忆】
{integrated_memory}

请从以下维度进行评估（每项0-10分）：

1. **整合质量** (Integration Quality)
   - 新旧记忆是否合理融合
   - 是否保持了时间线的连贯性

2. **去重能力** (Deduplication)
   - 是否避免了重复信息
   - 是否合并了相似内容

3. **重要性排序** (Prioritization)
   - 是否保留了最重要的记忆
   - 是否合理淘汰了次要信息

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "integration_quality": 8.5,
    "deduplication": 9.0,
    "prioritization": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["short_term_memory", "existing_long_term_memory", "integrated_memory"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    },
    {
        "category": "EVALUATOR_GROUP_MODERATOR",
        "name": "群聊中控评估器",
        "description": "评估群聊中控决策的质量",
        "template_content": """你是一个专业的群聊中控质量评估专家。请评估以下群聊中控的发言者选择决策的质量。

【群聊信息】
{group_info}

【对话历史】
{chat_history}

【可选角色】
{available_characters}

【中控决策】
选择的角色: {selected_character}
决策理由: {decision_reason}

请从以下维度进行评估（每项0-10分）：

1. **合理性** (Rationality)
   - 选择是否符合对话逻辑
   - 是否考虑了上下文

2. **多样性** (Diversity)
   - 是否避免了某个角色过度发言
   - 是否给不同角色合理的发言机会

3. **推进力** (Momentum)
   - 选择是否有助于推进对话
   - 是否避免了冷场或混乱

请以JSON格式输出评估结果：
```json
{
  "scores": {
    "rationality": 8.5,
    "diversity": 9.0,
    "momentum": 8.5
  },
  "total_score": 26.0,
  "passed": true,
  "feedback": "详细的评估反馈...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["待改进点1", "待改进点2"]
}
```
""",
        "metadata": {
            "variables": ["group_info", "chat_history", "available_characters", "selected_character", "decision_reason"],
            "output_format": "json",
            "scoring_range": "0-30"
        }
    }
]


def find_admin_user():
    """自动查找管理员用户ID"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username FROM users WHERE is_admin != 0 LIMIT 1")
        row = cur.fetchone()
        if row:
            if USE_POSTGRESQL:
                return {"id": row[0], "username": row[1]}
            else:
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        return None
    finally:
        _return_conn(conn)


def init_evaluators():
    """初始化评估器提示词"""
    admin_user = find_admin_user()
    if not admin_user:
        print("[ERROR] 未找到管理员用户，请先创建管理员账号")
        return
    
    admin_id = admin_user['id']
    print(f"[INFO] 使用管理员账号: {admin_user['username']} (ID: {admin_id})")
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        for prompt_data in EVALUATION_PROMPTS:
            category = prompt_data['category']
            name = prompt_data['name']
            
            # 检查是否已存在
            cur.execute(
                "SELECT id FROM prompt_templates WHERE category = ? AND is_active != 0",
                (category,)
            ) if not USE_POSTGRESQL else cur.execute(
                "SELECT id FROM prompt_templates WHERE category = %s AND is_active != 0",
                (category,)
            )
            
            existing = cur.fetchone()
            if existing:
                print(f"[SKIP] {name} 已存在（ID: {existing[0]}）")
                continue
            
            # 插入新评估器
            now = int(time.time())
            metadata_json = str(prompt_data['metadata']).replace("'", '"')
            
            if USE_POSTGRESQL:
                cur.execute("""
                    INSERT INTO prompt_templates 
                    (category, sub_category, name, description, template_content, metadata, version, is_active, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    category,
                    None,
                    name,
                    prompt_data['description'],
                    prompt_data['template_content'],
                    metadata_json,
                    '1.0.0',
                    1,  # PostgreSQL中is_active是integer类型
                    admin_id,
                    now,  # created_at是bigint类型
                    now   # updated_at是bigint类型
                ))
            else:
                cur.execute("""
                    INSERT INTO prompt_templates 
                    (category, sub_category, name, description, template_content, metadata, version, is_active, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category,
                    None,
                    name,
                    prompt_data['description'],
                    prompt_data['template_content'],
                    metadata_json,
                    '1.0.0',
                    1,
                    admin_id,
                    now,
                    now
                ))
            
            prompt_id = cur.fetchone()[0]
            
            # 创建版本历史
            if USE_POSTGRESQL:
                cur.execute("""
                    INSERT INTO prompt_version_history
                    (prompt_template_id, version, change_log, previous_content, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    prompt_id,
                    '1.0.0',
                    '初始版本',
                    None,  # 初始版本没有previous_content
                    admin_id,
                    now  # created_at是bigint类型
                ))
            else:
                cur.execute("""
                    INSERT INTO prompt_version_history
                    (prompt_template_id, version, change_log, previous_content, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prompt_id,
                    '1.0.0',
                    '初始版本',
                    None,  # 初始版本没有previous_content
                    admin_id,
                    now
                ))
            
            conn.commit()
            print(f"[SUCCESS] 创建评估器: {name} (ID: {prompt_id})")
    
    except Exception as e:
        print(f"[ERROR] 初始化评估器失败: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        _return_conn(conn)


if __name__ == '__main__':
    print("=" * 60)
    print("开始初始化评估器提示词...")
    print("=" * 60)
    init_evaluators()
    print("=" * 60)
    print("初始化完成！")
    print("=" * 60)
