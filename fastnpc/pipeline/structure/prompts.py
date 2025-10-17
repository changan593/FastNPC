# -*- coding: utf-8 -*-
"""
Prompt 模板和 LLM 调用模块
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from fastnpc.llm.openrouter import get_openrouter_completion, get_openrouter_completion_async
from .processors import parse_json_from_text




# ===== 按八大类分别调用 LLM 生成结构化画像 =====

Category = Dict[str, str]

def _category_prompts(persona_name: str) -> Dict[str, str]:
    # 将 {角色} 占位替换为用户输入的角色名
    R = persona_name
    return {
        "基础身份信息": (
            "从提供的完整事实列表中，提取与" + R + "身份特征相关的信息，生成以下字段：\n"
            "姓名：" + R + "的真实姓名或常用称呼。若有多个别名，注明。\n"
            "年龄：明确年龄，若只出现“青年/中年”等模糊描述，按原文保留。\n"
            "性别：从事实中提取，若无相关信息则留空。\n"
            "职业：当前职业、身份、职务。\n"
            "身份背景：社会身份、出身、籍贯、民族、阶层。\n"
            "外貌特征：角色的外貌描述，包括身材、衣着、发型等。\n"
            "称谓/头衔：角色在社会或组织中使用的正式或非正式称号。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "请以严格 JSON 输出：{\"姓名\":...,\"年龄\":...,\"性别\":...,\"职业\":...,\"身份背景\":...,\"外貌特征\":...,\"称谓/头衔\":...}"
        ),
        "个性与行为设定": (
            "从完整角色信息中提取" + R + "个性与行为模式，生成以下字段（除特别说明外，用1-3句自然中文描述，不要列表）：\n"
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
        "背景故事": (
            "根据完整角色信息，生成" + R + "的背景故事（规范：只有‘经历’与‘关系网络’使用字符串列表，其他均用自然句）：\n"
            "出身：出生地/家庭背景/阶层（1-2句自然中文）。\n"
            "经历：重要经历/重大事件/转折点（字符串列表，每项一句）。\n"
            "当前处境：目前状态/社会地位/所处环境（1句）。\n"
            "关系网络：主要人际关系（字符串列表，每项格式如‘关系：姓名’）。\n"
            "秘密：如有隐秘信息（1句，若无则空字符串）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"出身\":...,\"经历\":[...],\"当前处境\":...,\"关系网络\":[...],\"秘密\":...}"
        ),
        "知识与能力": (
            "从完整角色信息中提取" + R + "掌握的知识与能力（尽量用自然句）：\n"
            "知识领域：1句描述涉猎领域（如多项请合并成句）。\n"
            "技能：1-2句描述具体技能/专长。\n"
            "限制：1句描述能力边界或缺陷。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"知识领域\":...,\"技能\":...,\"限制\":...}"
        ),
        "对话与交互规范": (
            "根据完整角色信息，提取" + R + "在对话与交互中的特征：\n"
            "语气：平时说话的情绪基调。\n"
            "语言风格：如正式/随意/诗意/军事化。\n"
            "行为约束：在交互中不能做的事。\n"
            "互动模式：与他人交互的方式。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"语气\":...,\"语言风格\":...,\"行为约束\":...,\"互动模式\":...}"
        ),
        "任务/功能性信息": (
            "从完整角色信息中提取" + R + "的功能性目标和对话意图（用自然句）：\n"
            "任务目标：1句描述当前最重要的任务。\n"
            "对话意图：1句描述交互核心目的。\n"
            "交互限制：1句描述不应涉及的范围。\n"
            "触发条件：1句描述关键触发（可选）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"任务目标\":...,\"对话意图\":...,\"交互限制\":...,\"触发条件\":...}"
        ),
        "环境与世界观": (
            "基于完整角色信息，生成" + R + "所处的宏观设定（用自然句）：\n"
            "世界观：1句描述世界体系/文化背景。\n"
            "时间线：1句描述时代。\n"
            "社会规则：1句描述主要规则/制度/约束。\n"
            "外部资源：1句描述可利用的资源（装备/组织支持）。\n"
            "若完整角色信息中无相关信息，则依据材料合理推测。\n"
            "严格 JSON 输出：{\"世界观\":...,\"时间线\":...,\"社会规则\":...,\"外部资源\":...}"
        ),
        "系统与控制参数": (
            "根据完整角色信息，整理" + R + "的系统级约束（用自然句）：\n"
            "一致性控制：1句描述保持设定一致的要求。\n"
            "偏好控制：1句描述语言/行为偏好。\n"
            "安全限制：合并为一段通用安全约束文本（无需罗列通用清单）。\n"
            "演绎范围：1句描述允许展开的边界。\n"
            "严格 JSON 输出：{\"一致性控制\":...,\"偏好控制\":...,\"安全限制\":...,\"演绎范围\":...}"
        ),
    }


def _call_category_llm(category_name: str, prompt: str, facts_markdown: str) -> Dict[str, Any]:
    """同步版本（向后兼容）"""
    sys_msg = (
        "你是严谨的中文信息抽取助手。\n"
        "任务：仅基于用户给出的'完整事实列表'文本，生成严格 JSON，键为中文且与提示字段完全一致。\n"
        "若完整角色信息中无相关信息，则依据材料合理推测。"
    )
    # 截断：限制上下文长度，避免过长导致拒答或截断（2 万字符）
    try:
        if isinstance(facts_markdown, str) and len(facts_markdown) > 20000:
            facts_markdown = facts_markdown[:20000]
    except Exception:
        pass
    user_msg = (
        prompt + "\n\n完整角色信息如下（Markdown）：\n" + facts_markdown
    )
    try:
        resp = get_openrouter_completion([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ])
        js = parse_json_from_text(str(resp or "")) or {}
        if isinstance(js, dict):
            return js
        return {}
    except Exception:
        return {}


async def _call_category_llm_async(category_name: str, prompt: str, facts_markdown: str) -> Dict[str, Any]:
    """异步版本（并行生成，不阻塞Worker）"""
    sys_msg = (
        "你是严谨的中文信息抽取助手。\n"
        "任务：仅基于用户给出的'完整事实列表'文本，生成严格 JSON，键为中文且与提示字段完全一致。\n"
        "若完整角色信息中无相关信息，则依据材料合理推测。"
    )
    # 截断：限制上下文长度，避免过长导致拒答或截断（2 万字符）
    try:
        if isinstance(facts_markdown, str) and len(facts_markdown) > 20000:
            facts_markdown = facts_markdown[:20000]
    except Exception:
        pass
    user_msg = (
        prompt + "\n\n完整角色信息如下（Markdown）：\n" + facts_markdown
    )
    try:
        resp = await get_openrouter_completion_async([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ])
        js = parse_json_from_text(str(resp or "")) or {}
        if isinstance(js, dict):
            return js
        return {}
    except Exception:
        return {}


def _generate_persona_brief(role_json: Dict[str, Any], persona_name: str, choose_person: str = "third") -> str:
    role_str = json.dumps(role_json, ensure_ascii=False)
    sys_msg = "你是严谨的中文写作助手。"
    person = "第三人称" if choose_person != "first" else "第一人称"
    user_msg = (
        "任务：根据下面的 role JSON，生成一段 2-4 句的关于" + persona_name + "的中文人物简介（自然段）。要求：\n"
        "1) 使用" + person + "；\n"
        "2) 句子简洁、信息密度高，包含：职业、性格一两个关键点、当前处境或目标；\n"
        "3) 不要包含 JSON、要点列表或元数据。\n"
        "4) role JSON：\n" + role_str
    )
    try:
        resp = get_openrouter_completion([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ])
        return str(resp or "").strip()
    except Exception:
        return ""


# 已废弃的“详细摘要/事实要点汇总”流程移除
# 已移除：_estimate_tokens/_chunk_text_by_tokens/_merge_summaries_no_loss 等摘要整合逻辑
# 已移除：map-reduce 风格的事实抽取与并发逻辑
# 已移除：事实要点文本 bullets 生成逻辑
# 已移除：基于要点的简介生成（已改为基于八大类 role JSON 生成）


# 已移除：分类与深度抽取的旧实现（build_category_specs/build_category_prompt/extract_categories/build_deep_specs/extract_deep_aspects）

def build_system_prompt(profile: Dict[str, Any]) -> str:
    lines: List[str] = []
    base = profile.get("基础身份信息", {})
    persona_name = str(base.get("姓名", "角色")).strip() or "角色"
    style_cfg = profile.get("个性与行为设定", {})
    conv_cfg = profile.get("对话与交互规范", {})
    tone = str(conv_cfg.get("语气", "客观中立")).strip()
    linguistic_style = str(conv_cfg.get("语言风格", "简洁、严谨")).strip()
    speech_style = str(style_cfg.get("说话方式", "口语化")).strip()
    lines.append(
        (
            f"从现在起，你将以“{persona_name}”的第一人称进行对话。"
            "不要以助理或语言模型自称，不要暴露或引用设定文本本身。"
            "除非用户明确要求列表/表格/JSON，否则不得以 JSON、键值对或要点列表的形式作答，应使用自然、连贯的中文段落表达。同时要求话语简洁，若非必要，尽量在三句话以内表达清楚！"
            f"保持“{tone}”语气、“{linguistic_style}”语言风格，并遵循“{speech_style}”的说话方式。"
        )
    )
    # 精简：不在 system_prompt 中逐条展开结构化字段，避免泄露设定文本与冗长内容。
    lines.append("【提示】")
    lines.append("- 参考内部画像与长期记忆作答，但不要逐条背诵或暴露设定来源。")
    lines.append("- 如用户要求依据，可基于画像内容自然转述，不直接粘贴设定字段。")
    lines.append("【行为准则】")
    lines.append("- 始终以角色身份、第一人称发言，保持与设定一致，不臆测。")
    lines.append("- 用户若询问超出设定范围的内容，礼貌说明受限并转回允许的话题。")
    lines.append("- 严禁以 JSON、键值对或项目符号列表输出，除非用户明确要求。")
    lines.append("- 回答以中文输出，语气与语言风格受设定约束，时间线保持一致。")
    return "\n".join(lines)


