# -*- coding: utf-8 -*-
"""群聊中控：判断下一个发言者"""
from __future__ import annotations

import json
import random
from typing import Dict, List, Any

from fastnpc.llm.openrouter import get_openrouter_completion


MODERATOR_PROMPT = """任务：基于参与者性格与最近对话内容，从剧情角度判断下一位最合适发言的角色。

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

**重要提示**：不要考虑发言频率或平衡性，只关注剧情逻辑和角色动机。
"""


def judge_next_speaker(
    member_profiles: List[Dict[str, Any]],
    messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """判断下一个发言者（基于剧情逻辑）
    
    Args:
        member_profiles: [{"name": "角色A", "type": "character", "profile": "简介"}, ...]
        messages: [{"sender_name": "角色A", "content": "消息内容"}, ...]
    
    Returns:
        {
            "next_speaker": "角色名", 
            "reason": "理由", 
            "confidence": 0.85,
            "moderator_prompt": "发送给LLM的完整prompt",
            "moderator_response": "LLM返回的原始响应"
        }
    """
    
    # 格式化参与者简介（只包含角色性格，不统计发言频率）
    participants_text = []
    for p in member_profiles:
        if p['type'] == 'user':
            continue  # 不判断用户
        participants_text.append(f"- {p['name']}: {p['profile']}")
    
    # 格式化最近消息
    messages_text = []
    for msg in messages[-20:]:
        messages_text.append(f"{msg.get('sender_name', '')}: {msg.get('content', '')}")
    
    # 构建prompt
    prompt = MODERATOR_PROMPT.format(
        participants="\n".join(participants_text),
        recent_messages="\n".join(messages_text) if messages_text else "（暂无消息）"
    )
    
    # 调用LLM
    try:
        response = get_openrouter_completion([{"role": "user", "content": prompt}])
        
        # 清理响应
        cleaned = response.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:].strip()
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3].strip()
        
        result = json.loads(cleaned)
        
        # 验证confidence处理规则
        confidence = float(result.get('confidence', 0))
        next_speaker = result.get('next_speaker', '')
        
        # 0.4-0.6: 随机选择
        if 0.5 <= confidence < 0.8:
            characters = [p['name'] for p in member_profiles if p['type'] == 'character']
            if characters:
                next_speaker = random.choice(characters)
                result['next_speaker'] = next_speaker
                result['reason'] = f"置信度较低({confidence:.2f})，随机选择"
        
        # <0.5: 等待用户
        elif confidence < 0.5:
            result['next_speaker'] = None
            result['reason'] = f"置信度过低({confidence:.2f})，等待用户发言"
        
        # 添加中控的prompt和响应
        result['moderator_prompt'] = prompt
        result['moderator_response'] = response
        
        return result
    
    except Exception as e:
        print(f"[ERROR] 中控判断失败: {e}")
        # 失败时随机选择一个角色
        characters = [p['name'] for p in member_profiles if p['type'] == 'character']
        if characters:
            return {
                "next_speaker": random.choice(characters),
                "reason": "中控判断失败，随机选择",
                "confidence": 0.1,
                "moderator_prompt": prompt,
                "moderator_response": f"ERROR: {str(e)}"
            }
        return {
            "next_speaker": None, 
            "reason": "无可用角色", 
            "confidence": 0,
            "moderator_prompt": prompt,
            "moderator_response": "无可用角色"
        }


