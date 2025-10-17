# -*- coding: utf-8 -*-
"""群聊路由模块"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.auth import (
    create_group_chat,
    list_group_chats,
    add_group_member,
    list_group_members,
    add_group_message,
    list_group_messages,
    delete_group_chat,
    get_group_chat_detail,
    remove_group_member,
    get_user_settings,
    get_user_id_by_username,
    _get_conn,
    update_group_message_moderator_info,
)
from fastnpc.api.utils import _require_user, _load_character_profile
from fastnpc.chat.prompt_builder import build_chat_system_prompt, _remove_timestamp_suffix
from fastnpc.chat.group_moderator import judge_next_speaker
from fastnpc.llm.openrouter import (
    get_openrouter_completion,
    get_openrouter_completion_async,
    stream_openrouter_text_async
)

router = APIRouter()


def _judge_next_speaker_after_message(group_id: int, message_id: int, uid: int) -> None:
    """角色发言后，调用中控判断下一个说话者，并更新到该消息中
    
    这样查看消息时，显示的是"该角色发言后，下一个该谁发言"的判断
    """
    try:
        # 获取群聊成员
        members = list_group_members(group_id)
        # 获取最近消息（只读取未压缩的）
        messages = list_group_messages(group_id, limit=50, only_uncompressed=True)
        
        # 获取成员简介
        member_profiles = []
        
        for member in members:
            if member['member_type'] == 'user':
                # 根据成员用户名查询其用户ID和简介
                member_user_id = get_user_id_by_username(member['member_name'])
                if member_user_id:
                    member_user_settings = get_user_settings(member_user_id)
                    member_user_profile = member_user_settings.get('profile') or "普通用户"
                else:
                    member_user_profile = "普通用户"
                
                member_profiles.append({
                    "name": member['member_name'],
                    "type": "user",
                    "profile": member_user_profile
                })
            else:
                # 从数据库读取角色简介
                try:
                    structured = _load_character_profile(member['member_name'], uid)
                    if structured:
                        base = structured.get('基础身份信息', {})
                        personality = structured.get('个性与行为设定', {})
                        brief = f"{base.get('职业', '')} · {personality.get('性格特质', '')}"
                        member_profiles.append({
                            "name": _remove_timestamp_suffix(member['member_name']),
                            "type": "character",
                            "profile": brief[:200]
                        })
                    else:
                        member_profiles.append({
                            "name": _remove_timestamp_suffix(member['member_name']),
                            "type": "character",
                            "profile": "角色"
                        })
                except Exception as e:
                    print(f"[ERROR] 加载角色简介失败: {e}")
                    member_profiles.append({
                        "name": _remove_timestamp_suffix(member['member_name']),
                        "type": "character",
                        "profile": "角色"
                    })
        
        # 调用中控判断下一个说话者
        result = judge_next_speaker(member_profiles, messages)
        
        # 更新消息的中控信息
        moderator_prompt = result.get("moderator_prompt", "")
        moderator_response = result.get("moderator_response", "")
        
        update_group_message_moderator_info(message_id, moderator_prompt, moderator_response)
        print(f"[INFO] 已更新消息{message_id}的中控判断: 下一个说话者={result.get('next_speaker')}, 置信度={result.get('confidence')}")
        
    except Exception as e:
        print(f"[ERROR] 调用中控判断更新消息失败: {e}")


async def _compress_single_character_memory(
    group_id: int,
    character_name: str,
    to_compress: list,
    messages: list,
    split_idx: int,
    participants: list,
    uid: int,
    user_settings: dict
) -> None:
    """为单个角色压缩记忆（异步执行）"""
    import asyncio
    from fastnpc.chat.memory_manager import calculate_memory_size, compress_to_short_term_memory_group_chat
    from fastnpc.api.utils import _append_short_term_memory, _read_memories_from_profile, _write_memories_to_profile, _get_role_summary
    from fastnpc.chat.memory_manager import integrate_to_long_term_memory, trim_long_term_memory_weighted
    
    # 格式化消息（从该角色的视角）
    formatted_msgs = []
    for msg in to_compress:
        if msg['sender_name'] == character_name:
            formatted_msgs.append({"role": "assistant", "content": msg['content']})
        else:
            sender_display = _remove_timestamp_suffix(msg['sender_name'])
            formatted_msgs.append({"role": "user", "content": f"{sender_display}: {msg['content']}"})
    
    if not formatted_msgs:
        return
    
    # 计算重叠上下文（取split_idx前后各5条）
    overlap_start = max(0, split_idx - 5)
    overlap_msgs = messages[overlap_start:split_idx]
    
    overlap_formatted = []
    for msg in overlap_msgs:
        if msg['sender_name'] == character_name:
            overlap_formatted.append({"role": "assistant", "content": msg['content']})
        else:
            sender_display = _remove_timestamp_suffix(msg['sender_name'])
            overlap_formatted.append({"role": "user", "content": f"{sender_display}: {msg['content']}"})
    
    # 使用 asyncio.to_thread 将同步函数异步化
    new_stm = await asyncio.to_thread(
        compress_to_short_term_memory_group_chat,
        formatted_msgs,
        character_name,
        participants,
        overlap_formatted
    )
    
    if new_stm:
        _append_short_term_memory(character_name, uid, new_stm)
        print(f"[INFO] 群聊{group_id} 为角色 {character_name} 压缩生成 {len(new_stm)} 条短期记忆")
        
        # 检查该角色的短期记忆是否超预算
        ctx_max_stm = user_settings.get('ctx_max_stm') or 3000
        ctx_max_ltm = user_settings.get('ctx_max_ltm') or 4000
        
        stm_list, ltm_list = _read_memories_from_profile(character_name, uid)
        stm_size = calculate_memory_size(stm_list)
        
        if stm_size > ctx_max_stm:
            print(f"[INFO] 角色 {character_name} 短期记忆超预算({stm_size} > {ctx_max_stm})，整合到长期记忆...")
            
            # 整合前 2/3 到长期记忆
            split_idx_stm = len(stm_list) * 2 // 3
            to_integrate = stm_list[:split_idx_stm]
            remaining_stm = stm_list[split_idx_stm:]
            
            # 获取角色简介
            role_summary = _get_role_summary(character_name, uid)
            
            # 整合为长期记忆
            new_ltm = integrate_to_long_term_memory(to_integrate, ltm_list, role_summary)
            print(f"[INFO] 角色 {character_name} 整合生成 {len(new_ltm)} 条长期记忆")
            
            # 写回文件
            _write_memories_to_profile(character_name, uid, short_memories=remaining_stm, long_memories=new_ltm)
            
            # 检查长期记忆是否超预算
            ltm_size = calculate_memory_size(new_ltm)
            if ltm_size > ctx_max_ltm:
                print(f"[INFO] 角色 {character_name} 长期记忆超预算({ltm_size} > {ctx_max_ltm})，裁剪...")
                
                trimmed_ltm = trim_long_term_memory_weighted(new_ltm, ctx_max_ltm)
                _write_memories_to_profile(character_name, uid, short_memories=remaining_stm, long_memories=trimmed_ltm)
                print(f"[INFO] 角色 {character_name} 裁剪后长期记忆: {len(trimmed_ltm)} 条")


async def _compress_group_session_memory_if_needed(group_id: int, uid: int) -> None:
    """统一的群聊会话记忆压缩逻辑（异步并发版本）
    
    当群聊消息总数超过ctx_max_chat预算时：
    1. 将前2/3消息凝练成短期记忆
    2. 并发为所有角色生成短期记忆（显著提升速度）
    3. 标记已压缩的消息
    
    Args:
        group_id: 群聊ID
        uid: 用户ID
    """
    import asyncio
    
    # 获取用户设置
    user_settings = get_user_settings(uid)
    ctx_max_chat = user_settings.get('ctx_max_chat') or 8000
    
    # 只获取未压缩的群聊消息
    messages = list_group_messages(group_id, limit=1000, only_uncompressed=True)
    
    if len(messages) < 20:
        # 消息太少，不需要压缩
        return
    
    # 计算当前会话记忆的token数
    # 简单估算：每条消息约100-200 tokens
    estimated_tokens = sum(len(msg.get('content', '')) * 2 for msg in messages)
    
    if estimated_tokens < ctx_max_chat:
        # 未超预算，不需要压缩
        return
    
    print(f"[INFO] 群聊{group_id} 会话记忆({estimated_tokens} tokens)超过预算({ctx_max_chat})，开始并发压缩...")
    
    # 压缩前 2/3 消息
    split_idx = len(messages) * 2 // 3
    to_compress = messages[:split_idx]
    
    # 获取群聊成员
    members = list_group_members(group_id)
    
    # 获取所有参与者名称（去掉时间后缀）
    participants = [_remove_timestamp_suffix(m['member_name']) for m in members]
    
    # 并发为所有角色压缩记忆
    character_members = [m for m in members if m['member_type'] == 'character']
    
    if not character_members:
        return
    
    print(f"[INFO] 群聊{group_id} 开始并发为 {len(character_members)} 个角色压缩记忆...")
    
    tasks = [
        _compress_single_character_memory(
            group_id,
            member['member_name'],
            to_compress,
            messages,
            split_idx,
            participants,
            uid,
            user_settings
        )
        for member in character_members
    ]
    
    # 并发执行所有任务
    await asyncio.gather(*tasks)
    
    # 标记所有已压缩的消息
    compressed_ids = [msg.get('id') for msg in to_compress if msg.get('id')]
    if compressed_ids:
        from fastnpc.api.auth import mark_group_messages_as_compressed
        mark_group_messages_as_compressed(group_id, compressed_ids)
        print(f"[INFO] 群聊{group_id} 已标记 {len(compressed_ids)} 条消息为已压缩")
    
    print(f"[INFO] 群聊{group_id} 会话记忆并发压缩完成")
CHAR_DIR_STR = CHAR_DIR.as_posix()


@router.post("/api/groups")
async def api_create_group(request: Request):
    """创建群聊"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    data = await request.json()
    name = str(data.get("name", "")).strip()
    member_names = data.get("members", [])  # 角色名列表
    
    if not name:
        return JSONResponse({"error": "群聊名称不能为空"}, status_code=400)
    
    uid = int(user['uid'])
    group_id = create_group_chat(uid, name)
    
    # 添加成员（用户自己 + 角色）
    add_group_member(group_id, 'user', user.get('u') or user.get('username'), None)
    for member_name in member_names:
        if member_name:
            add_group_member(group_id, 'character', normalize_role_name(member_name), None)
    
    return {"group_id": group_id}


@router.get("/api/groups")
def api_list_groups(request: Request):
    """列出群聊"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    groups = list_group_chats(int(user['uid']))
    return {"items": groups}


@router.get("/api/groups/{group_id}")
def api_get_group(group_id: int, request: Request):
    """获取群聊详情"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    detail = get_group_chat_detail(group_id, int(user['uid']))
    if not detail:
        return JSONResponse({"error": "群聊不存在或无权访问"}, status_code=404)
    
    return {"group": detail}


@router.delete("/api/groups/{group_id}")
def api_delete_group(group_id: int, request: Request):
    """删除群聊"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    delete_group_chat(int(user['uid']), group_id)
    return {"ok": True}


@router.post("/api/groups/{group_id}/members")
async def api_add_member(group_id: int, request: Request):
    """添加成员"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    data = await request.json()
    member_name = normalize_role_name(str(data.get("member_name", "")).strip())
    
    if not member_name:
        return JSONResponse({"error": "成员名称不能为空"}, status_code=400)
    
    add_group_member(group_id, 'character', member_name, None)
    return {"ok": True}


@router.delete("/api/groups/{group_id}/members/{member_name}")
def api_remove_member(group_id: int, member_name: str, request: Request):
    """移除成员"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    remove_group_member(group_id, member_name)
    return {"ok": True}


@router.get("/api/groups/{group_id}/messages")
def api_get_group_messages(group_id: int, request: Request):
    """获取群聊消息"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    messages = list_group_messages(group_id, limit=200)
    return {"messages": messages}


@router.post("/api/groups/{group_id}/messages")
async def api_post_group_message(group_id: int, request: Request):
    """发送群聊消息"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    data = await request.json()
    content = str(data.get("content", "")).strip()
    
    if not content:
        return JSONResponse({"error": "内容不能为空"}, status_code=400)
    
    uid = int(user['uid'])
    user_name = str(user.get('u') or user.get('username'))
    
    # 保存用户消息
    add_group_message(group_id, 'user', uid, user_name, content, None)
    
    # 检查并压缩群聊会话记忆（异步并发）
    await _compress_group_session_memory_if_needed(group_id, uid)
    
    return {"ok": True}


@router.post("/api/groups/{group_id}/judge-next")
async def api_judge_next_speaker(group_id: int, request: Request):
    """调用中控判断下一个发言者"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    uid = int(user['uid'])
    
    # 获取群聊成员
    members = list_group_members(group_id)
    # 获取最近消息（只读取未压缩的）
    messages = list_group_messages(group_id, limit=50, only_uncompressed=True)
    
    # 获取成员简介
    member_profiles = []
    
    from fastnpc.chat.prompt_builder import _remove_timestamp_suffix
    
    for member in members:
        if member['member_type'] == 'user':
            # 根据成员用户名查询其用户ID和简介
            member_user_id = get_user_id_by_username(member['member_name'])
            if member_user_id:
                member_user_settings = get_user_settings(member_user_id)
                member_user_profile = member_user_settings.get('profile') or "普通用户"
            else:
                member_user_profile = "普通用户"
            
            member_profiles.append({
                "name": member['member_name'],  # 用户名不需要去后缀
                "type": "user",
                "profile": member_user_profile
            })
        else:
            # 从数据库读取角色简介
            try:
                structured = _load_character_profile(member['member_name'], uid)
                if structured:
                    base = structured.get('基础身份信息', {})
                    personality = structured.get('个性与行为设定', {})
                    brief = f"{base.get('职业', '')} · {personality.get('性格特质', '')}"
                    member_profiles.append({
                        "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                        "type": "character",
                        "profile": brief[:200]
                    })
                else:
                    member_profiles.append({
                        "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                        "type": "character",
                        "profile": "角色"
                    })
            except Exception as e:
                print(f"[ERROR] 加载角色简介失败: {e}")
                member_profiles.append({
                    "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                    "type": "character",
                    "profile": "角色"
                })
    
    # 调用中控
    result = judge_next_speaker(member_profiles, messages)
    
    return {
        "next_speaker": result.get("next_speaker"),
        "reason": result.get("reason"),
        "confidence": result.get("confidence", 0),
        "moderator_prompt": result.get("moderator_prompt"),
        "moderator_response": result.get("moderator_response")
    }


@router.post("/api/groups/{group_id}/generate-reply")
async def api_generate_group_reply(group_id: int, request: Request):
    """生成角色回复（由中控判断后调用）- 流式版本"""
    from fastnpc.chat.prompt_builder import _remove_timestamp_suffix
    
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    data = await request.json()
    character_name_input = str(data.get("character_name", "")).strip()
    moderator_prompt = data.get("moderator_prompt")
    moderator_response = data.get("moderator_response")
    
    if not character_name_input:
        return JSONResponse({"error": "角色名不能为空"}, status_code=400)
    
    uid = int(user['uid'])
    user_name = str(user.get('u') or user.get('username'))
    
    # 获取群聊成员和消息（只读取未压缩的）
    members = list_group_members(group_id)
    messages = list_group_messages(group_id, limit=200, only_uncompressed=True)
    
    # 在群成员中查找匹配的完整角色名（处理时间后缀）
    character_name = None
    for member in members:
        if member['member_type'] != 'character':
            continue
        # 去掉时间后缀后比较
        clean_name = _remove_timestamp_suffix(member['member_name'])
        if clean_name == character_name_input or member['member_name'] == character_name_input:
            character_name = member['member_name']
            break
    
    if not character_name:
        return JSONResponse({"error": f"群聊中未找到角色: {character_name_input}"}, status_code=404)
    
    # 从数据库读取角色结构化信息
    try:
        structured_profile = _load_character_profile(character_name, uid)
        if not structured_profile:
            return JSONResponse({"error": "角色不存在"}, status_code=404)
    except Exception as e:
        print(f"[ERROR] 加载角色信息失败: {e}")
        return JSONResponse({"error": "角色不存在"}, status_code=404)
    
    # 读取角色的短期/长期记忆
    from fastnpc.api.utils import _read_memories_from_profile
    short_term_memories, long_term_memories = _read_memories_from_profile(character_name, uid)
    
    # 获取用户信息
    user_settings = get_user_settings(uid)
    user_profile_text = user_settings.get('profile') or "普通用户"
    
    # 构建群聊专用的其他角色列表
    other_characters = []
    for member in members:
        if member['member_name'] == character_name:
            continue
        if member['member_type'] != 'character':
            continue  # 用户在交谈对象中单独处理
        
        try:
            prof = _load_character_profile(member['member_name'], uid)
            if prof:
                base = prof.get('基础身份信息', {})
                personality = prof.get('个性与行为设定', {})
                brief = f"{base.get('职业', '')} · {personality.get('性格特质', '')}"
                other_characters.append({
                    "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                    "brief": brief[:200]
                })
            else:
                other_characters.append({
                    "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                    "brief": "无简介"
                })
        except Exception as e:
            print(f"[ERROR] 加载其他角色信息失败: {e}")
            other_characters.append({
                "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                "brief": "无简介"
            })
    
    # 格式化群聊消息（标记发言者）
    transcript_lines = []
    for msg in messages[-50:]:  # 最近50条
        sender = msg.get('sender_name', '')
        sender_display = _remove_timestamp_suffix(sender)  # 去除时间戳
        content = msg.get('content', '')
        transcript_lines.append(f"{sender_display}: {content}")
    
    # 构建群聊系统提示（完整6部分结构）
    system_prompt = _build_group_chat_system_prompt(
        role_name=character_name,
        user_name=user_name,
        user_profile_text=user_profile_text,
        role_profile=structured_profile,
        chat_transcript_lines=transcript_lines,
        other_characters=other_characters,
        long_term_memories=long_term_memories,
        short_term_memories=short_term_memories,
    )
    
    # 调用LLM生成回复（流式）
    last_message = messages[-1]['content'] if messages else ""
    prompt_msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"当前对话：\n{chr(10).join(transcript_lines[-10:])}\n\n请以{character_name}的身份回复："}
    ]
    
    import re
    
    # 清理角色名称前缀的函数
    def clean_character_prefix(text: str, char_name: str) -> str:
        """清理输出中的角色名称前缀"""
        # 匹配 "角色名:" 或 "角色名时间戳:"
        pattern = rf'^{re.escape(char_name)}(\d{{12}})?[:：]\s*'
        return re.sub(pattern, '', text).strip()
    
    # 流式生成器（异步，不阻塞Worker）
    async def gen():
        full_reply = ""
        
        try:
            async for chunk in stream_openrouter_text_async(prompt_msgs):
                full_reply += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # 清理角色名称前缀
            cleaned_reply = clean_character_prefix(full_reply, _remove_timestamp_suffix(character_name))
            
            # 保存消息（先用当前的中控信息保存）
            message_id = add_group_message(
                group_id, 
                'character', 
                None, 
                character_name, 
                cleaned_reply, 
                system_prompt,
                moderator_prompt,
                moderator_response
            )
            
            # 再次调用中控判断"该角色发言后，下一个该谁发言"，并更新到该消息中
            _judge_next_speaker_after_message(group_id, message_id, uid)
            
            # 检查并压缩群聊会话记忆（异步并发）
            await _compress_group_session_memory_if_needed(group_id, uid)
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            print(f"[ERROR] 群聊流式生成失败: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


def _build_group_chat_system_prompt(
    role_name: str,
    user_name: str,
    user_profile_text: str,
    role_profile: Dict[str, Any],
    chat_transcript_lines: List[str],
    other_characters: List[Dict[str, str]],  # [{"name": "角色A", "brief": "简介"}, ...]
    long_term_memories: List[str],
    short_term_memories: List[str],
) -> str:
    """构建群聊专用system prompt（完整6部分结构）"""
    from fastnpc.chat.prompt_builder import _safe_get, _join_list, _truncate, _remove_timestamp_suffix
    
    # 解析结构化描述
    base = role_profile.get("基础身份信息", {})
    behavior = role_profile.get("个性与行为设定", {})
    story = role_profile.get("背景故事", {})
    knowledge = role_profile.get("知识与能力", {})
    convo = role_profile.get("对话与交互规范", {})
    task = role_profile.get("任务/功能性信息", {})
    world = role_profile.get("环境与世界观", {})
    control = role_profile.get("系统与控制参数", {})
    
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
    
    # ③ 长期记忆
    ltm_text = "（无）"
    if long_term_memories:
        ltm_lines = [f"- {m}" for m in long_term_memories]
        ltm_text = "\n".join(ltm_lines)
        ltm_text = _truncate(ltm_text, 4000)
    
    # ④ 短期记忆
    stm_text = "（无）"
    if short_term_memories:
        stm_lines = [f"- {m}" for m in short_term_memories]
        stm_text = "\n".join(stm_lines)
        stm_text = _truncate(stm_text, 3000)
    
    # 获取去掉时间后缀的角色名
    display_name = _remove_timestamp_suffix(role_name)
    
    # ⑤ 交谈对象（群聊版）- 去掉其他角色名的时间后缀
    character_display_names = ", ".join([_remove_timestamp_suffix(c['name']) for c in other_characters])
    interaction_text = f"与我交互的对象是 {user_name}，他的简介是：{user_profile_text}。\n"
    if other_characters:
        interaction_text += "在群聊中，我还会和这些角色交互：\n"
        for char in other_characters:
            char_display_name = _remove_timestamp_suffix(char['name'])
            interaction_text += f"- {char_display_name}: {char['brief']}\n"
    
    # ⑥ 会话记忆
    transcript_text = "\n".join(chat_transcript_lines)
    transcript_text = _truncate(transcript_text, 3000)
    
    # ① 系统提示（群聊版）
    all_names = user_name
    if character_display_names:
        all_names = f"{user_name}、{character_display_names}"
    
    fixed_rules = (
        f"你现在的身份是 {display_name}。\n"
        f"你必须始终以第一人称与 {all_names} 等人进行群聊对话。\n"
        "不要以助理或语言模型自称，不要暴露或引用设定文本本身。\n"
        "回答必须自然流畅，避免逐条罗列，不使用 JSON、键值对或项目符号列表，除非用户明确要求。\n"
        "回答应尽量简洁，若非必要，不超过两句话。\n"
        "如果用户要求的内容超出你的设定范围，请礼貌说明限制，并转回允许的话题。\n"
        "【群聊专用规则】在群聊中，严格要求注意不要重复自己或他人已表达过的观点或内容，避免冗余。\n"
        "【群聊专用规则】在群聊中，严格要求不要说空话、废话、套话，要言之有物，言之有理。\n"
        "【群聊专用规则】在群聊中，要多与包括用户在内的其他角色互动，可以回应、提问或引用包括用户在内的其他角色的发言，营造自然的多人对话氛围。"
        "【群聊专用规则】在群聊中，如果当前话题已经讨论完了，就不要再重复讨论，可以适当引导到新的话题，但不要重复以前讨论过的话题，这个新的话题可以是旧话题的延伸，也可以是和群里某个或某几个角色有关的话题，或者和用户有关的话题。"
        "【群聊专用规则】在群聊中，严格要求应该正面回答用户的问题，不要回避问题，不要说“两者都好”等类似的话"
        "【群聊专用规则】在群聊中，严格要求不要理性客观中立，和其它角色可以针锋相对，可以批评其它角色，可以批评用户，但不要过度，不要人身攻击，不要侮辱人格，不要涉及政治、宗教、种族、性别等敏感话题。"
    )
    
    # 拼接六部分
    lines: List[str] = []
    lines.append("① 系统提示（固定规则层）\n" + fixed_rules)
    lines.append("\n② 角色结构化描述（转化为自然语言画像）\n以下是关于 {姓名} 的完整画像，你必须在对话中保持与这些设定一致：\n\n".replace("{姓名}", display_name) + structured_text)
    lines.append("\n③ 长期记忆\n这是我至今为止的重要长期记忆：\n" + ltm_text)
    lines.append("\n④ 短期记忆\n这是我最近的短期记忆：\n" + stm_text)
    lines.append("\n⑤ 交谈对象\n" + interaction_text.strip())
    lines.append("\n⑥ 会话记忆（聊天上下文）\n以下是群聊中的对话记录，请从最新的部分继续：\n\n" + transcript_text)
    
    return "\n\n".join(lines)


@router.get("/api/groups/{group_id}/members/briefs")
def api_get_member_briefs(group_id: int, request: Request):
    """获取群聊成员简介（用于右侧信息面板）"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    uid = int(user['uid'])
    members = list_group_members(group_id)
    briefs = []
    
    from fastnpc.chat.prompt_builder import _remove_timestamp_suffix
    
    for member in members:
        if member['member_type'] == 'user':
            # 根据成员用户名查询其用户ID和简介
            member_user_id = get_user_id_by_username(member['member_name'])
            if member_user_id:
                member_user_settings = get_user_settings(member_user_id)
                member_user_profile = member_user_settings.get('profile') or "普通用户"
            else:
                member_user_profile = "普通用户"
            
            briefs.append({
                "name": member['member_name'],  # 用户名不需要去后缀
                "type": "user",
                "brief": member_user_profile[:100]
            })
        else:
            try:
                prof = _load_character_profile(member['member_name'], uid)
                if prof:
                    base = prof.get('基础身份信息', {})
                    personality = prof.get('个性与行为设定', {})
                    brief = f"{base.get('职业', '')} · {personality.get('性格特质', '')}"
                    briefs.append({
                        "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                        "type": "character",
                        "brief": brief[:100]
                    })
                else:
                    briefs.append({
                        "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                        "type": "character",
                        "brief": "角色"
                    })
            except Exception as e:
                print(f"[ERROR] 加载角色简介失败: {e}")
                briefs.append({
                    "name": _remove_timestamp_suffix(member['member_name']),  # 去掉时间后缀
                    "type": "character",
                    "brief": "无简介"
                })
    
    return {"members": briefs}


async def _compress_single_character_on_leave(
    group_id: int,
    character_name: str,
    messages: list,
    participants: list,
    uid: int,
    ctx_max_stm: int,
    ctx_max_ltm: int
) -> bool:
    """离开时为单个角色压缩记忆（异步执行）"""
    import asyncio
    from fastnpc.chat.memory_manager import compress_to_short_term_memory_group_chat
    from fastnpc.api.utils import _append_short_term_memory, _read_memories_from_profile, _write_memories_to_profile, _get_role_summary
    from fastnpc.chat.memory_manager import calculate_memory_size, integrate_to_long_term_memory, trim_long_term_memory_weighted
    
    # 格式化消息（从该角色的视角）
    formatted_msgs = []
    for msg in messages:
        if msg['sender_name'] == character_name:
            formatted_msgs.append({"role": "assistant", "content": msg['content']})
        else:
            sender_display = _remove_timestamp_suffix(msg['sender_name'])
            formatted_msgs.append({"role": "user", "content": f"{sender_display}: {msg['content']}"})
    
    if not formatted_msgs:
        return False
    
    # 计算重叠上下文（最近20%或最多10条）
    overlap_size = min(10, max(2, len(formatted_msgs) // 5))
    overlap = formatted_msgs[:overlap_size] if overlap_size > 0 else []
    to_compress = formatted_msgs[overlap_size:] if overlap_size > 0 else formatted_msgs
    
    # 使用 asyncio.to_thread 将同步函数异步化
    new_stm = await asyncio.to_thread(
        compress_to_short_term_memory_group_chat,
        to_compress,
        character_name, 
        participants,
        overlap
    )
    
    if new_stm:
        _append_short_term_memory(character_name, uid, new_stm)
        print(f"[INFO] 群聊{group_id} 为角色 {character_name} 压缩生成 {len(new_stm)} 条短期记忆")
        
        # 检查该角色的短期记忆是否超预算
        stm_list, ltm_list = _read_memories_from_profile(character_name, uid)
        stm_size = calculate_memory_size(stm_list)
        
        if stm_size > ctx_max_stm:
            print(f"[INFO] 角色 {character_name} 短期记忆超预算({stm_size} > {ctx_max_stm})，整合到长期记忆...")
            
            # 整合前 2/3 到长期记忆
            split_idx = len(stm_list) * 2 // 3
            to_integrate = stm_list[:split_idx]
            remaining_stm = stm_list[split_idx:]
            
            # 获取角色简介
            role_summary = _get_role_summary(character_name, uid)
            
            # 整合为长期记忆
            new_ltm = integrate_to_long_term_memory(to_integrate, ltm_list, role_summary)
            print(f"[INFO] 角色 {character_name} 整合生成 {len(new_ltm)} 条长期记忆")
            
            # 写回文件
            _write_memories_to_profile(character_name, uid, short_memories=remaining_stm, long_memories=new_ltm)
            
            # 检查长期记忆是否超预算
            ltm_size = calculate_memory_size(new_ltm)
            if ltm_size > ctx_max_ltm:
                print(f"[INFO] 角色 {character_name} 长期记忆超预算({ltm_size} > {ctx_max_ltm})，裁剪...")
                
                trimmed_ltm = trim_long_term_memory_weighted(new_ltm, ctx_max_ltm)
                _write_memories_to_profile(character_name, uid, short_memories=remaining_stm, long_memories=trimmed_ltm)
                print(f"[INFO] 角色 {character_name} 裁剪后长期记忆: {len(trimmed_ltm)} 条")
        
        return True
    
    return False


@router.post("/api/groups/{group_id}/compress-memories")
async def api_compress_group_memories(group_id: int, request: Request):
    """离开群聊时，强制压缩会话记忆到各角色的短期记忆（异步并发版本）
    
    与 _compress_group_session_memory_if_needed 不同，此接口会强制压缩，
    不管是否超过预算，因为用户离开了群聊。
    """
    import asyncio
    
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    uid = int(user['uid'])
    
    # 强制压缩：只读取未压缩的消息进行压缩
    from fastnpc.api.auth import list_group_messages, mark_group_messages_as_compressed
    messages = list_group_messages(group_id, limit=1000, only_uncompressed=True)
    
    if len(messages) < 5:
        # 消息太少（少于5条），不需要压缩
        print(f"[INFO] 群聊{group_id} 未压缩消息太少({len(messages)}条)，跳过压缩")
        return {"ok": True, "message": f"未压缩消息太少({len(messages)}条)，跳过压缩"}
    
    print(f"[INFO] 用户离开群聊{group_id}，开始并发压缩 {len(messages)} 条未压缩消息...")
    
    # 获取用户设置
    user_settings = get_user_settings(uid)
    ctx_max_stm = user_settings.get('ctx_max_stm') or 3000
    ctx_max_ltm = user_settings.get('ctx_max_ltm') or 4000
    
    # 获取群聊成员
    members = list_group_members(group_id)
    
    # 获取所有参与者名称（去掉时间后缀）
    participants = [_remove_timestamp_suffix(m['member_name']) for m in members]
    
    # 并发为所有角色压缩记忆
    character_members = [m for m in members if m['member_type'] == 'character']
    
    if not character_members:
        print(f"[INFO] 群聊{group_id} 没有角色成员，跳过压缩")
        return {"ok": True, "compressed_characters": 0}
    
    print(f"[INFO] 群聊{group_id} 开始并发为 {len(character_members)} 个角色压缩记忆...")
    
    tasks = [
        _compress_single_character_on_leave(
            group_id,
            member['member_name'],
            messages,
            participants,
            uid,
            ctx_max_stm,
            ctx_max_ltm
        )
        for member in character_members
    ]
    
    # 并发执行所有任务
    results = await asyncio.gather(*tasks)
    compressed_count = sum(1 for r in results if r)
    
    # 标记所有已压缩的消息
    compressed_ids = [msg.get('id') for msg in messages if msg.get('id')]
    if compressed_ids:
        mark_group_messages_as_compressed(group_id, compressed_ids)
        print(f"[INFO] 群聊{group_id} 离开时已标记 {len(compressed_ids)} 条消息为已压缩")
    
    print(f"[INFO] 群聊{group_id} 离开时并发压缩完成，处理了 {compressed_count} 个角色")
    return {"ok": True, "compressed_characters": compressed_count}


@router.get("/admin/groups/{group_id}/messages/{msg_id}/prompt")
async def get_group_message_prompt(group_id: int, msg_id: int, request: Request):
    """获取群聊消息的完整prompt"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    # 验证用户是否是该群聊的成员
    uid = int(user['uid'])
    detail = get_group_chat_detail(group_id, uid)
    if not detail:
        return JSONResponse({"error": "无权访问该群聊"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sender_type, sender_name, content, system_prompt_snapshot, moderator_prompt, moderator_response FROM group_messages WHERE id=? AND group_id=?",
            (msg_id, group_id)
        )
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "消息不存在"}, status_code=404)
        
        return {
            "sender_type": row['sender_type'],
            "sender_name": row['sender_name'],
            "user_content": row['content'],
            "system_prompt": row['system_prompt_snapshot'] or "（无）",
            "moderator_prompt": row['moderator_prompt'] or "（无）",
            "moderator_response": row['moderator_response'] or "（无）"
        }
    finally:
        conn.close()


