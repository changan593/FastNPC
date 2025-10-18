# -*- coding: utf-8 -*-
"""
记忆管理器：三层记忆系统的核心逻辑
"""
from __future__ import annotations

import json
import random
from typing import Dict, List, Tuple, Optional

from fastnpc.llm.openrouter import get_openrouter_completion
from fastnpc.config import USE_DB_PROMPTS
from fastnpc.prompt_manager import PromptManager, PromptCategory


# ============= Prompt 模板 =============

SHORT_TERM_COMPRESSION_PROMPT = """你是记忆整理助手。将下列对话记录凝练为结构化短期记忆。

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


GROUP_CHAT_SHORT_TERM_COMPRESSION_PROMPT = """你是群聊记忆整理助手。将下列群聊对话记录凝练为结构化短期记忆。

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


LONG_TERM_INTEGRATION_PROMPT = """你是长期记忆管理助手。将短期记忆整合为长期记忆。

## 角色画像（用于判断重要性）
{role_profile_summary}

## 待整合的短期记忆
{short_memories_to_integrate}

## 已有长期记忆（需去重合并）
{existing_long_term_memories}

## 整合规则
1. **去重合并**：相同或相似事实合并，保留最新/最详细版本
2. **重要性评估**（保留高分项，低分项可丢弃）：
   - 与角色长期目标的相关性 (0-5分)
   - 信息的新颖性和独特性 (0-5分)
   - 对未来决策的潜在影响 (0-5分)
   - 总分 >= 8 的必须保留，4-7分选择性保留，<4分丢弃
3. **格式统一**："{{主语}} | {{事实}} | {{补充}}"

## 输出要求
1. **必须**输出标准JSON格式，不要使用markdown代码块
2. **必须**严格遵守JSON语法：
   - 字符串使用双引号""而不是单引号''
   - 对象和数组元素之间用逗号分隔
   - 最后一个元素后不加逗号
   - 数字不加引号，字符串必须加引号
3. 严格按照以下格式：
{{{{
  "long_term_memories": [
    {{"content": "记忆内容", "importance": 12, "reason": "评分理由"}},
    {{"content": "另一条记忆", "importance": 10, "reason": "评分理由"}}
  ],
  "merged_count": 3,
  "discarded_count": 2
}}}}

**请直接输出JSON，不要使用```json```标记，不要添加额外说明：**"""


# ============= 提示词加载函数（支持数据库） =============

def _get_stm_compression_prompt(is_group: bool = False) -> str:
    """获取短期记忆凝练提示词（支持从数据库加载）"""
    if USE_DB_PROMPTS:
        try:
            category = PromptCategory.GROUP_CHAT_STM_COMPRESSION if is_group else PromptCategory.SINGLE_CHAT_STM_COMPRESSION
            prompt_data = PromptManager.get_active_prompt(category)
            if prompt_data:
                print(f"[INFO] 使用数据库{'群聊' if is_group else '单聊'}短期记忆凝练提示词")
                return prompt_data['template_content']
        except Exception as e:
            print(f"[WARN] 从数据库加载STM凝练提示词失败: {e}")
    
    # 降级到硬编码版本
    return GROUP_CHAT_SHORT_TERM_COMPRESSION_PROMPT if is_group else SHORT_TERM_COMPRESSION_PROMPT


def _get_ltm_integration_prompt() -> str:
    """获取长期记忆整合提示词（支持从数据库加载）"""
    if USE_DB_PROMPTS:
        try:
            prompt_data = PromptManager.get_active_prompt(PromptCategory.LTM_INTEGRATION)
            if prompt_data:
                print("[INFO] 使用数据库长期记忆整合提示词")
                return prompt_data['template_content']
        except Exception as e:
            print(f"[WARN] 从数据库加载LTM整合提示词失败: {e}")
    
    # 降级到硬编码版本
    return LONG_TERM_INTEGRATION_PROMPT


# ============= 核心函数 =============

def _clean_llm_json_response(response: str) -> str:
    """清理LLM响应中的markdown代码块标记
    
    LLM有时会返回:
    ```json
    {"key": "value"}
    ```
    
    需要提取中间的纯JSON
    """
    response = response.strip()
    
    # 移除开头的 ```json 或 ```
    if response.startswith('```json'):
        response = response[7:].strip()
    elif response.startswith('```'):
        response = response[3:].strip()
    
    # 移除结尾的 ```
    if response.endswith('```'):
        response = response[:-3].strip()
    
    return response


def calculate_memory_size(memories: List[str]) -> int:
    """计算记忆列表的字符总数"""
    try:
        return sum(len(m) for m in memories if isinstance(m, str))
    except Exception:
        return 0


def split_messages_by_ratio(
    messages: List[Dict], budget: int, min_turns: int = 4
) -> Tuple[List[Dict], List[Dict]]:
    """按字符占比分割消息，至少保留min_turns轮（user+assistant=1轮）
    
    Args:
        messages: 消息列表，格式 [{"role": "user/assistant", "content": "..."}]
        budget: 预算字符数
        min_turns: 最少保留轮次（默认4轮，即8条消息）
    
    Returns:
        (前半部分, 后半部分)
    """
    if not messages:
        return [], []
    
    # 计算总字符数
    total_chars = sum(len(m.get('content', '')) for m in messages)
    
    # 如果没超预算，不分割
    if total_chars <= budget:
        return [], messages
    
    # 目标：前半部分约占50%
    target = total_chars * 0.5
    accumulated = 0
    split_idx = 0
    min_messages = min_turns * 2  # 每轮2条消息
    
    for i, msg in enumerate(messages):
        accumulated += len(msg.get('content', ''))
        if accumulated >= target and i >= min_messages:
            split_idx = i
            break
    
    # 如果没找到合适分割点（消息太少），默认分一半
    if split_idx == 0:
        split_idx = max(min_messages, len(messages) // 2)
    
    return messages[:split_idx], messages[split_idx:]


def get_overlap_context(messages: List[Dict], split_idx: int) -> List[Dict]:
    """获取重叠上下文：动态取前段末尾的1/4，最多2轮（4条消息）"""
    if not messages or split_idx <= 0:
        return []
    
    # 动态重叠：前段长度的1/4，但不超过4条消息
    overlap_size = min(4, max(2, split_idx // 4))
    start = max(0, split_idx - overlap_size)
    
    return messages[start:split_idx]


def compress_to_short_term_memory(
    messages: List[Dict],
    role_name: str,
    user_name: str,
    overlap_context: Optional[List[Dict]] = None,
) -> List[str]:
    """调用LLM将会话记录压缩为短期记忆列表
    
    Args:
        messages: 待压缩的消息列表
        role_name: 角色名
        user_name: 用户名
        overlap_context: 重叠上下文（可选）
    
    Returns:
        短期记忆列表，格式 ["主语 | 动作 | 宾语", ...]
    """
    if not messages:
        return []
    
    # 格式化对话记录
    chat_lines = []
    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        if role == 'user':
            chat_lines.append(f"{user_name}: {content}")
        elif role == 'assistant':
            chat_lines.append(f"{role_name}: {content}")
    
    chat_to_compress = '\n'.join(chat_lines)
    
    # 格式化重叠上下文
    overlap_lines = []
    if overlap_context:
        for msg in overlap_context:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'user':
                overlap_lines.append(f"{user_name}: {content}")
            elif role == 'assistant':
                overlap_lines.append(f"{role_name}: {content}")
    
    overlap_text = '\n'.join(overlap_lines) if overlap_lines else "（无）"
    
    # 构建Prompt（支持从数据库加载）
    prompt_template = _get_stm_compression_prompt(is_group=False)
    prompt = prompt_template.format(
        role_name=role_name,
        user_name=user_name,
        chat_to_compress=chat_to_compress,
        overlap_context=overlap_text,
    )
    
    # 调用LLM（带重试机制）
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = get_openrouter_completion([{"role": "user", "content": prompt}])
            # 清理响应（移除markdown代码块标记）
            cleaned_response = _clean_llm_json_response(response)
            # 解析JSON
            data = json.loads(cleaned_response)
            memories = data.get('short_memories', [])
            # 确保是字符串列表
            result = [str(m).strip() for m in memories if str(m).strip()]
            if result:  # 成功且有结果
                return result
            elif attempt < max_retries - 1:  # 结果为空但还有重试机会
                print(f"[WARN] 压缩生成0条记忆，重试 ({attempt + 1}/{max_retries})...")
                continue
            else:
                return []
        except json.JSONDecodeError as e:
            # JSON解析失败
            if attempt < max_retries - 1:
                print(f"[WARN] JSON解析错误，重试 ({attempt + 1}/{max_retries}): {e}")
                continue
            else:
                print(f"[ERROR] 压缩短期记忆失败 - JSON解析错误: {e}")
                print(f"[DEBUG] LLM原始响应: {response[:500] if len(response) < 500 else response[:500] + '...'}")
                return []
        except Exception as e:
            # 其他错误
            if attempt < max_retries - 1:
                print(f"[WARN] 压缩失败，重试 ({attempt + 1}/{max_retries}): {e}")
                continue
            else:
                print(f"[ERROR] 压缩短期记忆失败: {e}")
                return []
    return []


def compress_to_short_term_memory_group_chat(
    messages: List[Dict],
    role_name: str,
    participants: List[str],
    overlap_context: Optional[List[Dict]] = None,
) -> List[str]:
    """群聊专用：调用LLM将群聊记录压缩为短期记忆列表
    
    Args:
        messages: 待压缩的消息列表，格式 [{"role": "user/assistant", "content": "发言者: 内容"}]
        role_name: 当前角色名
        participants: 所有参与者名称列表（包括用户）
        overlap_context: 重叠上下文（可选）
    
    Returns:
        短期记忆列表，格式 ["发言者 | 对象 | 内容", ...]
    """
    if not messages:
        return []
    
    # 格式化对话记录（已经包含发言者前缀）
    chat_lines = []
    for msg in messages:
        content = msg.get('content', '')
        # 群聊消息已经格式化为 "发言者: 内容"，直接使用
        chat_lines.append(content)
    
    chat_to_compress = '\n'.join(chat_lines)
    
    # 格式化重叠上下文
    overlap_lines = []
    if overlap_context:
        for msg in overlap_context:
            content = msg.get('content', '')
            overlap_lines.append(content)
    
    overlap_text = '\n'.join(overlap_lines) if overlap_lines else "（无）"
    
    # 格式化参与者列表
    participants_text = '\n'.join([f"- {p}" for p in participants])
    
    # 构建Prompt（支持从数据库加载）
    prompt_template = _get_stm_compression_prompt(is_group=True)
    prompt = prompt_template.format(
        role_name=role_name,
        participants_list=participants_text,
        chat_to_compress=chat_to_compress,
        overlap_context=overlap_text,
    )
    
    # 调用LLM（带重试机制，复用单聊的逻辑）
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = get_openrouter_completion([{"role": "user", "content": prompt}])
            cleaned_response = _clean_llm_json_response(response)
            data = json.loads(cleaned_response)
            memories = data.get('short_memories', [])
            result = [str(m).strip() for m in memories if str(m).strip()]
            if result:
                return result
            elif attempt < max_retries - 1:
                print(f"[WARN] 群聊压缩生成0条记忆，重试 ({attempt + 1}/{max_retries})...")
                continue
            else:
                return []
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"[WARN] 群聊压缩JSON解析错误，重试 ({attempt + 1}/{max_retries}): {e}")
                continue
            else:
                print(f"[ERROR] 群聊压缩短期记忆失败 - JSON解析错误: {e}")
                print(f"[DEBUG] LLM原始响应: {response[:500] if len(response) < 500 else response[:500] + '...'}")
                return []
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[WARN] 群聊压缩失败，重试 ({attempt + 1}/{max_retries}): {e}")
                continue
            else:
                print(f"[ERROR] 群聊压缩短期记忆失败: {e}")
                return []
    return []


def integrate_to_long_term_memory(
    short_memories: List[str],
    existing_long_memories: List[str],
    role_profile_summary: str,
) -> List[str]:
    """调用LLM将短期记忆整合到长期记忆
    
    Args:
        short_memories: 待整合的短期记忆
        existing_long_memories: 已有的长期记忆
        role_profile_summary: 角色简介（用于判断重要性）
    
    Returns:
        去重、合并、评分后的长期记忆列表
    """
    if not short_memories:
        return existing_long_memories
    
    # 构建Prompt（支持从数据库加载）
    stm_text = '\n'.join([f"- {m}" for m in short_memories])
    ltm_text = '\n'.join([f"- {m}" for m in existing_long_memories]) if existing_long_memories else "（无）"
    
    prompt_template = _get_ltm_integration_prompt()
    prompt = prompt_template.format(
        role_profile_summary=role_profile_summary,
        short_memories_to_integrate=stm_text,
        existing_long_term_memories=ltm_text,
    )
    
    # 调用LLM（带重试机制）
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = get_openrouter_completion([{"role": "user", "content": prompt}])
            # 清理响应（移除markdown代码块标记）
            cleaned_response = _clean_llm_json_response(response)
            # 解析JSON
            data = json.loads(cleaned_response)
            memories_with_meta = data.get('long_term_memories', [])
            
            # 提取纯记忆内容（忽略评分信息，因为我们用字符串列表存储）
            result = []
            for item in memories_with_meta:
                if isinstance(item, dict):
                    content = item.get('content', '')
                else:
                    content = str(item)
                if content.strip():
                    result.append(content.strip())
            
            if result:  # 成功且有结果
                return result
            elif attempt < max_retries - 1:  # 结果为空但还有重试机会
                print(f"[WARN] 整合生成0条记忆，重试 ({attempt + 1}/{max_retries})...")
                continue
            else:
                # 最后一次尝试失败，使用简单合并
                break
        except json.JSONDecodeError as e:
            # JSON解析失败
            if attempt < max_retries - 1:
                print(f"[WARN] JSON解析错误，重试 ({attempt + 1}/{max_retries}): {e}")
                continue
            else:
                print(f"[ERROR] 整合长期记忆失败 - JSON解析错误: {e}")
                print(f"[DEBUG] LLM原始响应: {response[:500] if len(response) < 500 else response[:500] + '...'}")
                break
        except Exception as e:
            # 其他错误
            if attempt < max_retries - 1:
                print(f"[WARN] 整合失败，重试 ({attempt + 1}/{max_retries}): {e}")
                continue
            else:
                print(f"[ERROR] 整合长期记忆失败: {e}")
                break
    
    # 失败时，简单合并去重作为后备方案
    print(f"[INFO] 使用后备方案：简单合并去重")
    combined = list(existing_long_memories) + list(short_memories)
    seen = set()
    result = []
    for m in combined:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def trim_long_term_memory_weighted(memories: List[str], target_size: int) -> List[str]:
    """加权随机丢弃30%的长期记忆
    
    权重：索引位置越靠前权重越大（越容易被丢弃）
    
    Args:
        memories: 长期记忆列表
        target_size: 目标字符数
    
    Returns:
        裁剪后的记忆列表
    """
    if not memories:
        return []
    
    current_size = calculate_memory_size(memories)
    if current_size <= target_size:
        return memories
    
    # 计算需要丢弃的数量（30%）
    discard_count = max(1, int(len(memories) * 0.3))
    
    # 权重：索引越小权重越大（越容易被丢弃）
    # 例如：[5, 4, 3, 2, 1] 对于长度为5的列表
    weights = [len(memories) - i for i in range(len(memories))]
    
    # 加权随机选择要丢弃的索引
    indices_to_discard = set()
    while len(indices_to_discard) < discard_count and len(indices_to_discard) < len(memories):
        chosen = random.choices(range(len(memories)), weights=weights, k=1)[0]
        indices_to_discard.add(chosen)
    
    # 保留未被选中的
    result = [m for i, m in enumerate(memories) if i not in indices_to_discard]
    
    # 如果还是超预算，继续从头部丢弃
    while calculate_memory_size(result) > target_size and result:
        result.pop(0)
    
    return result


def get_session_memory_for_chat(
    messages: List[Dict], budget: int
) -> List[Dict]:
    """动态读取会话记忆，保证不超过预算
    
    Args:
        messages: 所有消息列表
        budget: 预算字符数
    
    Returns:
        限制在预算内的消息列表（优先保留最新的）
    """
    if not messages:
        return []
    
    # 从后往前取，直到达到预算
    result = []
    total_chars = 0
    
    for msg in reversed(messages):
        msg_size = len(msg.get('content', ''))
        if total_chars + msg_size > budget and result:
            break
        result.insert(0, msg)
        total_chars += msg_size
    
    return result

