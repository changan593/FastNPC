# -*- coding: utf-8 -*-
"""
提示词初始化脚本
将现有的9类提示词从源代码导入到数据库
"""
from __future__ import annotations

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from fastnpc.prompt_manager import PromptManager, PromptCategory, StructuredSubCategory


def init_structured_generation_prompts():
    """初始化结构化生成提示词（9个子分类）"""
    print("\n===== 初始化结构化生成提示词 =====")
    
    # 9个子分类的提示词内容（从 fastnpc/pipeline/structure/prompts.py 提取）
    structured_prompts = {
        StructuredSubCategory.BASIC_INFO: (
            "从提供的完整事实列表中，提取与{persona_name}身份特征相关的信息，生成以下字段：\n"
            "姓名：{persona_name}的真实姓名或常用称呼。若有多个别名，注明。\n"
            "年龄：明确年龄，若只出现'青年/中年'等模糊描述，按原文保留。\n"
            "性别：从事实中提取，若无相关信息则留空。\n"
            "职业：当前职业、身份、职务。\n"
            "身份背景：社会身份、出身、籍贯、民族、阶层。\n"
            "外貌特征：角色的外貌描述，包括身材、衣着、发型等。\n"
            "称谓/头衔：角色在社会或组织中使用的正式或非正式称号。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "请以严格 JSON 输出：{\"姓名\":...,\"年龄\":...,\"性别\":...,\"职业\":...,\"职业\":...,\"身份背景\":...,\"外貌特征\":...,\"称谓/头衔\":...}"
        ),
        StructuredSubCategory.PERSONALITY: (
            "从完整角色信息中提取{persona_name}个性与行为模式，生成以下字段（除特别说明外，用1-3句自然中文描述，不要列表）：\n"
            "性格特质：核心性格标签（可用简短句描述）。\n"
            "价值观：核心信念（1-2句）。\n"
            "情绪风格：常见情绪表现（1句）。\n"
            "说话方式：语言习惯（1句）。\n"
            "偏好：喜欢/倾向（1句；如多项请合并成句）。\n"
            "厌恶：不喜欢/回避（1句；如多项请合并成句）。\n"
            "动机与目标：追求的目的（1-2句）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"性格特质\":...,\"价值观\":...,\"情绪风格\":...,\"说话方式\":...,\"偏好\":...,\"厌恶\":...,\"动机与目标\":...}"
        ),
        StructuredSubCategory.BACKGROUND: (
            "根据完整角色信息，生成{persona_name}的背景故事（规范：只有'经历'与'关系网络'使用字符串列表，其他均用自然句）：\n"
            "出身：出生地/家庭背景/阶层（1-2句自然中文）。\n"
            "经历：重要经历/重大事件/转折点（字符串列表，每项一句）。\n"
            "当前处境：目前状态/社会地位/所处环境（1句）。\n"
            "关系网络：主要人际关系（字符串列表，每项格式如'关系：姓名'）。\n"
            "秘密：如有隐秘信息（1句，若无则空字符串）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"出身\":...,\"经历\":[...],\"当前处境\":...,\"关系网络\":[...],\"秘密\":...}"
        ),
        StructuredSubCategory.KNOWLEDGE: (
            "从完整角色信息中提取{persona_name}掌握的知识与能力（尽量用自然句）：\n"
            "知识领域：1句描述涉猎领域（如多项请合并成句）。\n"
            "技能：1-2句描述具体技能/专长。\n"
            "限制：1句描述能力边界或缺陷。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"知识领域\":...,\"技能\":...,\"限制\":...}"
        ),
        StructuredSubCategory.DIALOGUE: (
            "根据完整角色信息，提取{persona_name}在对话与交互中的特征：\n"
            "语气：平时说话的情绪基调。\n"
            "语言风格：如正式/随意/诗意/军事化。\n"
            "行为约束：在交互中不能做的事。\n"
            "互动模式：与他人交互的方式。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"语气\":...,\"语言风格\":...,\"行为约束\":...,\"互动模式\":...}"
        ),
        StructuredSubCategory.TASK: (
            "从完整角色信息中提取{persona_name}的功能性目标和对话意图（用自然句）：\n"
            "任务目标：1句描述当前最重要的任务。\n"
            "对话意图：1句描述交互核心目的。\n"
            "交互限制：1句描述不应涉及的范围。\n"
            "触发条件：1句描述关键触发（可选）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"任务目标\":...,\"对话意图\":...,\"交互限制\":...,\"触发条件\":...}"
        ),
        StructuredSubCategory.WORLDVIEW: (
            "基于完整角色信息，生成{persona_name}所处的宏观设定（用自然句）：\n"
            "世界观：1句描述世界体系/文化背景。\n"
            "时间线：1句描述时代。\n"
            "社会规则：1句描述主要规则/制度/约束。\n"
            "外部资源：1句描述可利用的资源（装备/组织支持）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"世界观\":...,\"时间线\":...,\"社会规则\":...,\"外部资源\":...}"
        ),
        StructuredSubCategory.SYSTEM_PARAMS: (
            "根据完整角色信息，整理{persona_name}的系统级约束（用自然句）：\n"
            "一致性控制：1句描述保持设定一致的要求。\n"
            "偏好控制：1句描述语言/行为偏好。\n"
            "安全限制：合并为一段通用安全约束文本（无需罗列通用清单）。\n"
            "演绎范围：1句描述允许展开的边界。\n"
            "严格 JSON 输出：{\"一致性控制\":...,\"偏好控制\":...,\"安全限制\":...,\"演绎范围\":...}"
        ),
        StructuredSubCategory.SOURCE: (
            "根据完整角色信息和数据来源，整理{persona_name}的来源元数据：\n"
            "唯一标识：角色的唯一标识符（如baike页面ID、wiki ID等）。\n"
            "链接：角色信息的来源URL地址。\n"
            "来源信息量：原始数据的大致字数或信息量（如'约5000字'）。\n"
            "若完整角色信息中无相关信息，则标注'未知'或留空。\n"
            "严格 JSON 输出：{\"唯一标识\":...,\"链接\":...,\"来源信息量\":...}"
        ),
    }
    
    count = 0
    for sub_category, template_content in structured_prompts.items():
        prompt_id = PromptManager.create_prompt(
            category=PromptCategory.STRUCTURED_GENERATION,
            sub_category=sub_category,
            name=f"结构化生成 - {sub_category}",
            description=f"{sub_category}的结构化信息提取提示词",
            template_content=template_content,
            version="1.0.0",
            is_active=True,  # 作为当前激活版本
            metadata={
                "variables": ["persona_name", "facts_markdown"],
                "output_format": "JSON"
            }
        )
        if prompt_id:
            count += 1
            print(f"  ✓ 创建: {sub_category} (ID: {prompt_id})")
        else:
            print(f"  ✗ 失败: {sub_category}")
    
    print(f"完成: {count}/9")


def init_structured_system_message():
    """初始化结构化生成系统消息"""
    print("\n===== 初始化结构化生成系统消息 =====")
    
    system_message = (
        "你是严谨的中文信息抽取助手。\n"
        "任务：仅基于用户给出的'完整事实列表'文本，生成严格 JSON，键为中文且与提示字段完全一致。\n"
        "若完整角色信息中无相关信息，则依据材料合理推测。"
    )
    
    prompt_id = PromptManager.create_prompt(
        category=PromptCategory.STRUCTURED_SYSTEM_MESSAGE,
        name="结构化生成系统消息",
        description="用于结构化信息提取的系统消息",
        template_content=system_message,
        version="1.0.0",
        is_active=True,
        metadata={
            "usage": "结构化生成任务的system消息"
        }
    )
    
    if prompt_id:
        print(f"  ✓ 创建成功 (ID: {prompt_id})")
    else:
        print(f"  ✗ 创建失败")


def init_brief_generation_prompt():
    """初始化简介生成提示词"""
    print("\n===== 初始化简介生成提示词 =====")
    
    template_content = (
        "任务：根据下面的 role JSON，生成一段 2-4 句的关于{persona_name}的中文人物简介（自然段）。要求：\n"
        "1) 使用{person}；\n"
        "2) 句子简洁、信息密度高，包含：职业、性格一两个关键点、当前处境或目标；\n"
        "3) 不要包含 JSON、要点列表或元数据。\n"
        "4) role JSON：\n{role_json}"
    )
    
    prompt_id = PromptManager.create_prompt(
        category=PromptCategory.BRIEF_GENERATION,
        name="角色简介生成",
        description="从结构化数据生成简洁的人物简介",
        template_content=template_content,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["persona_name", "person", "role_json"],
            "person_options": ["第一人称", "第三人称"],
            "output_format": "自然段落"
        }
    )
    
    if prompt_id:
        print(f"  ✓ 创建成功 (ID: {prompt_id})")
    else:
        print(f"  ✗ 创建失败")


def init_single_chat_system_prompt():
    """初始化单聊系统提示词"""
    print("\n===== 初始化单聊系统提示词 =====")
    
    # 固定规则层（从 fastnpc/chat/prompt_builder.py 提取）
    fixed_rules = (
        "你现在的身份是 {display_name}。\n"
        "你必须始终以第一人称与 {user_name} 进行对话。\n"
        "不要以助理或语言模型自称，不要暴露或引用设定文本本身。\n"
        "回答必须自然流畅，避免逐条罗列，不使用 JSON、键值对或项目符号列表，除非用户明确要求。\n"
        "回答应尽量简洁，若非必要，不超过三句话。\n"
        "如果用户要求的内容超出你的设定范围，请礼貌说明限制，并转回允许的话题。\n"
        "严格要求注意不要重复自己或用户已表达过的观点或内容，避免冗余。\n"
        "严格要求不要说空话、废话、套话，要言之有物，言之有理。\n"
        "要多与用户互动，可以回应、提问或引用用户或自己的发言，营造自然的对话氛围。\n"
        "如果当前话题已经讨论完了，就不要再重复讨论，可以适当引导到新的话题，但不要重复以前讨论过的话题，这个新的话题可以是旧话题的延伸，也可以是和自己或用户有关的话题。\n"
        "严格要求应该正面回答用户的问题，不要回避问题，不要说'两者都好'等类似的话。\n"
        "严格要求不要理性客观中立，和用户可以针锋相对，可以批评其它角色，可以批评用户，但不要过度，不要人身攻击，不要侮辱人格，不要涉及政治、宗教、种族、性别等敏感话题。"
    )
    
    prompt_id = PromptManager.create_prompt(
        category=PromptCategory.SINGLE_CHAT_SYSTEM,
        name="单聊系统提示（固定规则层）",
        description="单聊对话的系统提示，定义角色扮演规则",
        template_content=fixed_rules,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["display_name", "user_name"],
            "usage": "单聊系统提示的第①部分：固定规则层"
        }
    )
    
    if prompt_id:
        print(f"  ✓ 创建成功 (ID: {prompt_id})")
    else:
        print(f"  ✗ 创建失败")


def init_memory_compression_prompts():
    """初始化记忆凝练提示词"""
    print("\n===== 初始化记忆凝练提示词 =====")
    
    # 单聊短期记忆凝练（从 fastnpc/chat/memory_manager.py 提取）
    single_chat_stm = """你是记忆整理助手。将下列对话记录凝练为结构化短期记忆。

## 参与者
- 角色: {role_name}
- 用户: {user_name}

## 对话记录（待凝练部分）
{chat_to_compress}

## 上下文（仅供参考，不需凝练）
{overlap_context}

## 输出要求
1. **必须**输出标准JSON格式，不要使用markdown代码块
2. **必须**严格遵守JSON语法：
   - 字符串使用双引号""而不是单引号''
   - 数组元素之间用逗号分隔
   - 最后一个元素后不加逗号
   - 不要在JSON中添加注释
3. 格式：{{"short_memories": [...]}}
4. 每条记忆："{{主语}} | {{动作/状态/事实}} | {{宾语/补充}}"
5. 主语必须明确（{role_name}、{user_name}、或具体人名）
6. 只记录对后续对话有影响的事实：
   - ✅ 承诺、计划、请求、偏好变化
   - ✅ 重要信息披露、情绪转折
   - ❌ 问候、确认、无实质内容的回应
7. 示例：
   - "{user_name} | 提到明天要去北京出差 | 为期3天"
   - "{role_name} | 答应帮 {user_name} 准备会议资料 | 明天早上前"
   - "{user_name} | 表达对项目进度的担忧 | 担心延期"

**请直接输出JSON，不要使用```json```标记，不要添加额外说明：**"""
    
    prompt_id1 = PromptManager.create_prompt(
        category=PromptCategory.SINGLE_CHAT_STM_COMPRESSION,
        name="单聊短期记忆凝练",
        description="将单聊对话记录凝练为结构化短期记忆",
        template_content=single_chat_stm,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["role_name", "user_name", "chat_to_compress", "overlap_context"],
            "output_format": "JSON"
        }
    )
    
    # 群聊短期记忆凝练
    group_chat_stm = """你是群聊记忆整理助手。将下列群聊对话记录凝练为结构化短期记忆。

## 当前角色
- 角色名: {role_name}
- 说明: 你正在为这个角色整理记忆，请从该角色的视角记录

## 群聊参与者
{participants_list}

## 群聊对话记录（待凝练部分）
{chat_to_compress}

## 上下文（仅供参考，不需凝练）
{overlap_context}

## 输出要求
1. **必须**输出标准JSON格式，不要使用markdown代码块
2. **必须**严格遵守JSON语法：
   - 字符串使用双引号""而不是单引号''
   - 数组元素之间用逗号分隔
   - 最后一个元素后不加逗号
3. 格式：{{"short_memories": [...]}}
4. 每条记忆格式："{{发言者}} | {{对象}} | {{内容/行为}}"
5. **群聊特殊要求**：
   - 必须明确记录"谁对谁说了什么"
   - 保留群体互动的细节（多人讨论、分组对话等）
   - 记录话题切换和引导者
   - 记录群体共识或分歧
6. 优先记录内容：
   - ✅ 明确的请求、承诺、计划
   - ✅ 重要信息披露、观点表达
   - ✅ 角色间的关系变化或互动模式
   - ✅ 话题转折点和讨论结论
   - ❌ 简单的问候、附和、无实质内容的回应
7. 示例（群聊场景）：
   - "李白 | 杜甫 | 邀请一起饮酒赏月"
   - "杜甫 | 李白 | 表达对其诗才的赞赏"
   - "用户admin | 李白和杜甫 | 询问两人的创作风格差异"
   - "李白 | 群组 | 提议将话题转向盛唐气象"

**请直接输出JSON，不要使用```json```标记，不要添加额外说明：**"""
    
    prompt_id2 = PromptManager.create_prompt(
        category=PromptCategory.GROUP_CHAT_STM_COMPRESSION,
        name="群聊短期记忆凝练",
        description="将群聊对话记录凝练为结构化短期记忆",
        template_content=group_chat_stm,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["role_name", "participants_list", "chat_to_compress", "overlap_context"],
            "output_format": "JSON"
        }
    )
    
    if prompt_id1 and prompt_id2:
        print(f"  ✓ 创建成功: 单聊 (ID: {prompt_id1}), 群聊 (ID: {prompt_id2})")
    else:
        print(f"  ✗ 部分创建失败")


def init_ltm_integration_prompt():
    """初始化长期记忆整合提示词"""
    print("\n===== 初始化长期记忆整合提示词 =====")
    
    # 从 fastnpc/chat/memory_manager.py 提取
    ltm_integration = """你是长期记忆管理助手。将短期记忆整合为长期记忆。

## 角色画像（用于判断重要性）
{role_profile_summary}

## 待整合的短期记忆
{short_memories_to_integrate}

## 当前长期记忆
{current_long_term_memories}

## 任务说明
1. 从短期记忆中识别出对角色未来发展有长期影响的内容
2. 优先保留：承诺、重大决定、关系变化、性格转折、知识获取
3. 过滤掉：日常琐事、已完成的临时任务、过时的信息
4. 如果新记忆与现有长期记忆冲突，进行合并或更新
5. 整合后的长期记忆应保持简洁（每条20-50字）

## 输出要求
1. 输出标准JSON格式，不使用markdown代码块
2. 格式：{{"long_term_memories": [...]}}
3. 每条记忆为一个字符串
4. 示例：
   - "与用户约定每周二讨论项目进展"
   - "用户表达了对隐私安全的高度重视"
   - "学会了使用Python处理数据的新方法"

**请直接输出JSON：**"""
    
    prompt_id = PromptManager.create_prompt(
        category=PromptCategory.LTM_INTEGRATION,
        name="长期记忆整合",
        description="将短期记忆整合为长期记忆",
        template_content=ltm_integration,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["role_profile_summary", "short_memories_to_integrate", "current_long_term_memories"],
            "output_format": "JSON"
        }
    )
    
    if prompt_id:
        print(f"  ✓ 创建成功 (ID: {prompt_id})")
    else:
        print(f"  ✗ 创建失败")


def init_group_moderator_prompt():
    """初始化群聊中控提示词"""
    print("\n===== 初始化群聊中控提示词 =====")
    
    # 从 fastnpc/chat/group_moderator.py 提取
    moderator_prompt = """任务：基于参与者性格与最近对话内容，从剧情角度判断下一位最合适发言的角色。

## 核心原则
**必须从剧情逻辑出发**，判断哪个角色在当前情境下最有发言动机和必要性。

## 评判维度
1. **话题相关性**（0-3分）：该角色与当前话题的关联程度
2. **角色动机**（0-3分）：基于角色性格，此刻是否有强烈的表达欲望
3. **剧情推动力**（0-2分）：该角色发言是否能推动对话深入或产生新的戏剧张力
4. **对话连贯性**（0-2分）：该角色是否是前一句话的直接回应对象，或是否需要对某个问题作出回应

## 参与者简介
{participants}

## 最近消息（最多20条）
{recent_messages}

## 输出要求
严格输出JSON格式，不要使用markdown代码块：
{{
  "next_speaker": "角色名",
  "reason": "从剧情角度的选择理由（50字内）",
  "confidence": 0.85
}}

**置信度说明**：
- 0.7-1.0：有明确的剧情逻辑支持该角色发言（如被直接提问、话题与其强相关）
- 0.5-0.7：该角色较为适合发言，但也可以是其他角色
- 0.3-0.5：不确定谁更合适，建议随机选择
- 0-0.3：当前更适合等待用户发言或引导

**重要提示**：不要考虑发言频率或平衡性，只关注剧情逻辑和角色动机。"""
    
    prompt_id = PromptManager.create_prompt(
        category=PromptCategory.GROUP_MODERATOR,
        name="群聊中控判断",
        description="判断群聊中下一个发言者",
        template_content=moderator_prompt,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["participants", "recent_messages"],
            "output_format": "JSON"
        }
    )
    
    if prompt_id:
        print(f"  ✓ 创建成功 (ID: {prompt_id})")
    else:
        print(f"  ✗ 创建失败")


def init_group_chat_character_prompt():
    """初始化群聊角色发言系统提示词"""
    print("\n===== 初始化群聊角色发言系统提示词 =====")
    
    # 群聊角色发言提示词（从群聊逻辑推断）
    group_character_prompt = (
        "你现在的身份是 {display_name}，正在参与一个群聊。\n"
        "群聊中还有其他成员：{other_members}。\n"
        "你必须始终以第一人称发言，保持角色设定一致。\n"
        "回答应简洁自然，不超过三句话（紧急情况除外）。\n"
        "注意：\n"
        "- 如果你被直接@或提问，需要及时回应\n"
        "- 可以与其他角色互动、讨论、甚至辩论\n"
        "- 保持角色性格，不要说违反设定的话\n"
        "- 避免重复已说过的内容\n"
        "- 不要以助理或AI自称"
    )
    
    prompt_id = PromptManager.create_prompt(
        category=PromptCategory.GROUP_CHAT_CHARACTER,
        name="群聊角色发言系统提示",
        description="群聊中单个角色的发言系统提示",
        template_content=group_character_prompt,
        version="1.0.0",
        is_active=True,
        metadata={
            "variables": ["display_name", "other_members"],
            "usage": "群聊角色发言的系统提示"
        }
    )
    
    if prompt_id:
        print(f"  ✓ 创建成功 (ID: {prompt_id})")
    else:
        print(f"  ✗ 创建失败")


def main():
    """主函数"""
    print("=" * 60)
    print("提示词初始化脚本")
    print("将现有9类提示词导入到数据库")
    print("=" * 60)
    
    try:
        # 初始化各类提示词
        init_structured_generation_prompts()  # 9个子分类
        init_structured_system_message()
        init_brief_generation_prompt()
        init_single_chat_system_prompt()
        init_memory_compression_prompts()  # 2个
        init_ltm_integration_prompt()
        init_group_moderator_prompt()
        init_group_chat_character_prompt()
        
        print("\n" + "=" * 60)
        print("✓ 所有提示词初始化完成！")
        print("=" * 60)
        
        # 统计信息
        all_prompts = PromptManager.list_prompts(include_inactive=False)
        print(f"\n当前激活的提示词总数: {len(all_prompts)}")
        
        # 按类别统计
        from collections import Counter
        category_counts = Counter(p['category'] for p in all_prompts)
        print("\n各类别提示词数量:")
        for category, count in category_counts.items():
            print(f"  - {category}: {count}")
    
    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

