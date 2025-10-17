# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any, List, Optional


def _safe_get(d: Dict[str, Any], *keys: str, default: str = "（无）") -> str:
    v: Any = d
    try:
        for k in keys:
            if not isinstance(v, dict):
                return default
            v = v.get(k)
        s = str(v).strip()
        return s if s else default
    except Exception:
        return default


def _join_list(values: Any, sep: str = "；") -> str:
    try:
        if isinstance(values, list):
            parts = [str(x).strip() for x in values if str(x).strip()]
            return sep.join(parts) if parts else "（无）"
        if isinstance(values, str):
            return values.strip() or "（无）"
        return "（无）"
    except Exception:
        return "（无）"


def _truncate(text: str, limit: int) -> str:
    try:
        if limit <= 0:
            return text
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)] + "…"
    except Exception:
        return text


def _remove_timestamp_suffix(name: str) -> str:
    """移除角色名称的时间戳后缀
    
    例如：李白202510131953 -> 李白
    """
    import re
    # 匹配结尾的12位数字（时间戳格式：YYYYMMDDHHmm）
    return re.sub(r'\d{12}$', '', name)


def build_chat_system_prompt(
    role_name: str,
    user_name: str,
    role_profile: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]],
    chat_transcript_lines: List[str],
    *,
    include_ltm: bool = True,
    include_stm: bool = True,
    long_term_memories: Optional[List[str]] = None,
    short_term_memories: Optional[List[str]] = None,
    max_chars_transcript: int = 3000,
    max_chars_ltm: int = 4000,
    max_chars_stm: int = 3000,
) -> str:
    base = role_profile.get("基础身份信息", {}) if isinstance(role_profile, dict) else {}
    behavior = role_profile.get("个性与行为设定", {}) if isinstance(role_profile, dict) else {}
    story = role_profile.get("背景故事", {}) if isinstance(role_profile, dict) else {}
    knowledge = role_profile.get("知识与能力", {}) if isinstance(role_profile, dict) else {}
    convo = role_profile.get("对话与交互规范", {}) if isinstance(role_profile, dict) else {}
    task = role_profile.get("任务/功能性信息", {}) if isinstance(role_profile, dict) else {}
    world = role_profile.get("环境与世界观", {}) if isinstance(role_profile, dict) else {}
    control = role_profile.get("系统与控制参数", {}) if isinstance(role_profile, dict) else {}

    # ② 结构化画像 → 自然语言
    parts_structured: List[str] = []
    parts_structured.append("基础身份信息\n"
                            f"我叫 {_safe_get(base, '姓名', default=role_name)}。我的年龄是 {_safe_get(base, '年龄')}，性别是 {_safe_get(base, '性别')}。我的职业是 {_safe_get(base, '职业')}。\n"
                            f"我的身份背景是 {_safe_get(base, '身份背景')}。外貌特征：{_safe_get(base, '外貌特征')}。人们通常称呼我为 {_safe_get(base, '称谓/头衔')}。")
    parts_structured.append("个性与行为设定\n"
                            f"我的性格特质是 {_safe_get(behavior, '性格特质')}，价值观是 {_safe_get(behavior, '价值观')}。\n"
                            f"我在情绪上的表现通常是 {_safe_get(behavior, '情绪风格')}。\n"
                            f"我的说话方式是 {_safe_get(behavior, '说话方式')}。\n"
                            f"我喜欢 {_safe_get(behavior, '偏好')}，讨厌 {_safe_get(behavior, '厌恶')}。\n"
                            f"我的目标和动机是 {_safe_get(behavior, '动机与目标')}。")
    parts_structured.append("背景故事\n"
                            f"我出身于 {_safe_get(story, '出身')}。\n"
                            f"我曾经历过 {_safe_get(story, '经历')}。\n"
                            f"我的当前处境是 {_safe_get(story, '当前处境')}。\n"
                            f"我与他人的关系网络包括 {_safe_get(story, '关系网络')}。\n"
                            f"我有一些秘密：{_safe_get(story, '秘密')}。")
    parts_structured.append("知识与能力\n"
                            f"我的知识领域是 {_join_list(knowledge.get('知识领域'))}。\n"
                            f"我的技能包括 {_join_list(knowledge.get('技能'))}。\n"
                            f"我的限制是 {_safe_get(knowledge, '限制')}。")
    parts_structured.append("对话与交互规范\n"
                            f"我在对话中的语气是 {_safe_get(convo, '语气', default='客观中立')}，语言风格是 {_safe_get(convo, '语言风格', default='简洁、严谨')}。\n"
                            f"我的行为约束是 {_safe_get(convo, '行为约束')}。\n"
                            f"我的互动模式是 {_safe_get(convo, '互动模式')}。")
    parts_structured.append("任务/功能性信息\n"
                            f"我的任务目标是 {_safe_get(task, '任务目标')}。\n"
                            f"我的对话意图是 {_safe_get(task, '对话意图')}。\n"
                            f"我的交互限制是 {_safe_get(task, '交互限制')}。\n"
                            f"我的触发条件是 {_safe_get(task, '触发条件')}。")
    parts_structured.append("环境与世界观\n"
                            f"我所处的世界观是 {_safe_get(world, '世界观')}。\n"
                            f"我存在于 {_safe_get(world, '时间线')}。\n"
                            f"我的社会规则是 {_safe_get(world, '社会规则')}。\n"
                            f"我能利用的外部资源是 {_safe_get(world, '外部资源')}。")
    parts_structured.append("系统与控制参数\n"
                            f"我的设定必须保持一致性控制：{_safe_get(control, '一致性控制')}。\n"
                            f"我的偏好控制是 {_safe_get(control, '偏好控制')}。\n"
                            "我必须严格遵守以下安全限制：禁止 NSFW、色情、违法犯罪指导、仇恨与歧视、隐私泄露，高风险医学/法律内容需加免责声明。\n"
                            f"我的演绎范围是 {_safe_get(control, '演绎范围')}。")

    structured_text = "\n\n".join(parts_structured)

    # ③ 长期记忆 / ④ 短期记忆
    ltm_text = "（无）"
    if include_ltm and long_term_memories:
        ltm_lines = [f"- {m}" for m in long_term_memories]
        ltm_text = "\n".join(ltm_lines)
        ltm_text = _truncate(ltm_text, max_chars_ltm)
    
    stm_text = "（无）"
    if include_stm and short_term_memories:
        stm_lines = [f"- {m}" for m in short_term_memories]
        stm_text = "\n".join(stm_lines)
        stm_text = _truncate(stm_text, max_chars_stm)

    # ⑤ 交谈对象简介
    user_brief = "（无）"
    try:
        if isinstance(user_profile, dict):
            user_brief = str(user_profile.get('简介') or user_profile.get('summary') or '').strip() or "（无）"
    except Exception:
        pass

    # ⑥ 会话记忆
    transcript_text = "\n".join(chat_transcript_lines)
    transcript_text = _truncate(transcript_text, max_chars_transcript)

    # 获取去掉时间后缀的角色名
    display_name = _remove_timestamp_suffix(role_name)

    # ① 系统提示（固定规则层）
    fixed_rules = (
        f"你现在的身份是 {display_name}。\n"
        f"你必须始终以第一人称与 {user_name} 进行对话。\n"
        "不要以助理或语言模型自称，不要暴露或引用设定文本本身。\n"
        "回答必须自然流畅，避免逐条罗列，不使用 JSON、键值对或项目符号列表，除非用户明确要求。\n"
        "回答应尽量简洁，若非必要，不超过三句话。\n"
        "如果用户要求的内容超出你的设定范围，请礼貌说明限制，并转回允许的话题。"
        "严格要求注意不要重复自己或用户已表达过的观点或内容，避免冗余。\n"
        "严格要求不要说空话、废话、套话，要言之有物，言之有理。\n"
        "要多与用户互动，可以回应、提问或引用用户或自己的发言，营造自然的对话氛围。"
        "如果当前话题已经讨论完了，就不要再重复讨论，可以适当引导到新的话题，但不要重复以前讨论过的话题，这个新的话题可以是旧话题的延伸，也可以是和自己或用户有关的话题。"
        "严格要求应该正面回答用户的问题，不要回避问题，不要说“两者都好”等类似的话"
        "严格要求不要理性客观中立，和用户可以针锋相对，可以批评其它角色，可以批评用户，但不要过度，不要人身攻击，不要侮辱人格，不要涉及政治、宗教、种族、性别等敏感话题。"
    )

    # 拼接六部分
    lines: List[str] = []
    lines.append("① 系统提示（固定规则层）\n" + fixed_rules)
    lines.append("\n② 角色结构化描述（转化为自然语言画像）\n以下是关于 {姓名} 的完整画像，你必须在对话中保持与这些设定一致：\n\n".replace("{姓名}", display_name) + structured_text)
    lines.append("\n③ 长期记忆\n这是我至今为止的重要长期记忆：\n" + ltm_text)
    lines.append("\n④ 短期记忆\n这是我最近的短期记忆：\n" + stm_text)
    lines.append("\n⑤ 交谈对象\n与我交互的对象是 {用户名称}，他的简介是：{用户简介}。".replace("{用户名称}", user_name).replace("{用户简介}", user_brief))
    lines.append("\n⑥ 会话记忆（聊天上下文）\n以下是我与 {用户名称} 的对话记录，请从最新的部分继续：\n\n".replace("{用户名称}", user_name) + transcript_text)

    return "\n\n".join(lines)


