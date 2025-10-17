# -*- coding: utf-8 -*-
"""
聊天路由模块
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from fastnpc.config import CHAR_DIR, TEMPLATES_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.auth import (
    get_or_create_character,
    add_message,
    list_messages,
    get_user_settings,
    get_user_by_id,
    mark_messages_as_compressed,
    update_message_system_prompt,
)
from fastnpc.api.utils import (
    _require_user,
    _structured_path_for_role,
    _truncate_structured_profile_text,
    _truncate_messages,
    _ensure_chat_session_for_role,
    _read_memories_from_profile,
    _write_memories_to_profile,
    _append_short_term_memory,
    _get_role_summary,
)
from fastnpc.api.state import sessions, sessions_lock
from fastnpc.chat.prompt_builder import build_chat_system_prompt
from fastnpc.chat.memory_manager import (
    calculate_memory_size,
    split_messages_by_ratio,
    get_overlap_context,
    compress_to_short_term_memory,
    integrate_to_long_term_memory,
    trim_long_term_memory_weighted,
)
from fastnpc.llm.openrouter import get_openrouter_completion, stream_openrouter_text


router = APIRouter()
CHAR_DIR_STR = CHAR_DIR.as_posix()
templates = Jinja2Templates(directory=TEMPLATES_DIR.as_posix())


def _check_and_compress_memories(
    role: str,
    uid: int,
    cid: int,
    user_name: str,
    ctx_max_chat: int,
    ctx_max_stm: int,
    ctx_max_ltm: int,
) -> None:
    """检查并压缩三层记忆（会话→短期→长期）"""
    try:
        # 1. 检查会话记忆（只读取未压缩的消息）
        session_messages = list_messages(uid, cid, limit=200, only_uncompressed=True)
        if not session_messages:
            return
        
        # 计算会话记忆大小
        session_contents = [m.get('content', '') for m in session_messages]
        session_size = calculate_memory_size(session_contents)
        
        if session_size > ctx_max_chat:
            print(f"[INFO] 会话记忆超预算({session_size} > {ctx_max_chat})，开始压缩...")
            
            # 分割消息：前一半压缩，后一半保留
            to_compress, to_keep = split_messages_by_ratio(session_messages, ctx_max_chat)
            
            if to_compress:
                # 获取重叠上下文
                overlap = get_overlap_context(session_messages, len(to_compress))
                
                # 压缩为短期记忆
                new_stm = compress_to_short_term_memory(to_compress, role, user_name, overlap)
                print(f"[INFO] 压缩生成 {len(new_stm)} 条短期记忆")
                
                if new_stm:
                    _append_short_term_memory(role, uid, new_stm)
                    
                    # 标记这些消息为已压缩
                    compressed_ids = [m.get('id') for m in to_compress if m.get('id')]
                    if compressed_ids:
                        mark_messages_as_compressed(uid, cid, compressed_ids)
                        print(f"[INFO] 已标记 {len(compressed_ids)} 条消息为已压缩")
                    
                    # 2. 检查短期记忆
                    stm_list, ltm_list = _read_memories_from_profile(role, uid)
                    stm_size = calculate_memory_size(stm_list)
                    
                    if stm_size > ctx_max_stm:
                        print(f"[INFO] 短期记忆超预算({stm_size} > {ctx_max_stm})，开始整合...")
                        
                        # 整合前一半到长期记忆
                        split_point = len(stm_list) // 2
                        to_integrate = stm_list[:split_point]
                        remaining_stm = stm_list[split_point:]
                        
                        # 获取角色简介
                        role_summary = _get_role_summary(role, uid)
                        
                        # 整合为长期记忆
                        new_ltm = integrate_to_long_term_memory(to_integrate, ltm_list, role_summary)
                        print(f"[INFO] 整合生成 {len(new_ltm)} 条长期记忆")
                        
                        # 写回文件
                        _write_memories_to_profile(role, uid, short_memories=remaining_stm, long_memories=new_ltm)
                        
                        # 3. 检查长期记忆
                        ltm_size = calculate_memory_size(new_ltm)
                        if ltm_size > ctx_max_ltm:
                            print(f"[INFO] 长期记忆超预算({ltm_size} > {ctx_max_ltm})，开始裁剪...")
                            
                            # 加权随机丢弃30%
                            trimmed_ltm = trim_long_term_memory_weighted(new_ltm, ctx_max_ltm)
                            print(f"[INFO] 裁剪后剩余 {len(trimmed_ltm)} 条长期记忆")
                            
                            _write_memories_to_profile(role, uid, long_memories=trimmed_ltm)
    except Exception as e:
        print(f"[ERROR] 记忆压缩失败: {e}")


@router.get("/api/chat/{role}/messages")
def api_get_messages(role: str, request: Request, after_id: int = 0, limit: int = 200):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    # DB 历史
    role = normalize_role_name(role)
    uid = int(user['uid'])
    cid = get_or_create_character(uid, role)
    items = list_messages(uid, cid, limit=limit, after_id=after_id)
    return {"messages": items}


@router.post("/api/chat/{role}/messages")
async def api_post_message(role: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    content = str(data.get("content", "")).strip()
    if not content:
        return JSONResponse({"error": "content 不能为空"}, status_code=400)
    export_ctx = bool(data.get('export_ctx'))
    # 写入用户消息（暂不保存system_prompt，等构建完成后更新）
    role = normalize_role_name(role)
    uid = int(user['uid'])
    # 读取管理员标志
    try:
        _udb = get_user_by_id(uid)
        _is_admin = int(_udb.get('is_admin', 0)) if _udb else 0
    except Exception:
        _is_admin = 0
    cid = get_or_create_character(uid, role)
    user_msg_id = add_message(int(user['uid']), cid, 'user', content)
    # 生成回复并写入
    sid = _ensure_chat_session_for_role(role, user_id=uid)
    with sessions_lock:
        msgs: List[Dict[str, str]] = sessions[sid]["messages"]  # type: ignore
        msgs.append({"role": "user", "content": content})
    # 获取用户记忆预算
    try:
        user_settings = get_user_settings(int(user['uid']))
    except Exception:
        user_settings = {"ctx_max_chat": None, "ctx_max_stm": None, "ctx_max_ltm": None}
    ctx_max_chat = int(user_settings.get('ctx_max_chat') or 3000)
    ctx_max_stm = int(user_settings.get('ctx_max_stm') or 3000)
    ctx_max_ltm = int(user_settings.get('ctx_max_ltm') or 4000)

    # 加载结构化画像和记忆
    structured_profile = None
    short_term_memories = []
    long_term_memories = []
    try:
        path = _structured_path_for_role(role, user_id=uid)
        with open(path, 'r', encoding='utf-8') as f:
            structured_profile = json.load(f)
        # 读取记忆
        short_term_memories, long_term_memories = _read_memories_from_profile(role, uid)
    except Exception:
        structured_profile = {}
    
    # 读取会话历史（从DB，避免会话重启丢失）
    # 只读取未压缩的消息，已压缩的消息已经凝练成短期/长期记忆
    try:
        db_items = list_messages(uid, cid, limit=200, only_uncompressed=True)
        msgs_for_model = [
            {"role": str(it.get("role", "")), "content": str(it.get("content", ""))}
            for it in db_items if str(it.get("role", "")) in {"user", "assistant"}
        ]
    except Exception:
        msgs_for_model = []
    msgs_for_model = _truncate_messages(msgs_for_model, ctx_max_chat)

    # 构建六段式 system prompt（包含记忆）
    from fastnpc.chat.prompt_builder import _remove_timestamp_suffix
    from fastnpc.api.auth import get_user_settings
    
    user_name = str(user.get('u') or user.get('username') or '用户')
    role_display_name = _remove_timestamp_suffix(role)
    
    # 获取用户简介
    user_settings = get_user_settings(uid)
    user_profile_text = user_settings.get('profile') or ""
    user_profile_dict = {"简介": user_profile_text} if user_profile_text else None
    
    transcript_lines: List[str] = []
    try:
        for it in msgs_for_model:
            r = str(it.get('role', ''))
            c = str(it.get('content', ''))
            if r == 'user':
                transcript_lines.append(f"{user_name}: {c}")
            elif r == 'assistant':
                transcript_lines.append(f"{role_display_name}: {c}")
    except Exception:
        pass
    
    system_prompt = build_chat_system_prompt(
        role_name=role,
        user_name=user_name,
        role_profile=structured_profile,
        user_profile=user_profile_dict,
        chat_transcript_lines=transcript_lines,
        include_ltm=True,
        include_stm=True,
        long_term_memories=long_term_memories,
        short_term_memories=short_term_memories,
        max_chars_transcript=ctx_max_chat,
        max_chars_ltm=ctx_max_ltm,
        max_chars_stm=ctx_max_stm,
    )
    
    # 保存实际发送给LLM的system prompt到user消息
    update_message_system_prompt(user_msg_id, system_prompt)
    
    # 上下文导出已移除（完全依赖数据库）
    
    # 调用 OpenRouter
    prompt_msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]
    reply = get_openrouter_completion(prompt_msgs)
    add_message(int(user['uid']), cid, 'assistant', reply)
    with sessions_lock:
        msgs.append({"role": "assistant", "content": reply})
    
    # 检查并压缩三层记忆
    _check_and_compress_memories(role, uid, cid, user_name, ctx_max_chat, ctx_max_stm, ctx_max_ltm)
    
    return {"reply": reply}


@router.get("/api/chat/{role}/stream")
def api_stream_message(role: str, content: str, request: Request, export_ctx: int = 0):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    # 写入用户消息（暂不保存system_prompt，等构建完成后更新）
    role = normalize_role_name(role)
    uid = int(user['uid'])
    cid = get_or_create_character(uid, role)
    user_msg_id = add_message(int(user['uid']), cid, 'user', content)

    sid = _ensure_chat_session_for_role(role, user_id=uid)
    with sessions_lock:
        msgs: List[Dict[str, str]] = sessions[sid]["messages"]  # type: ignore
        msgs.append({"role": "user", "content": content})

    def gen():
        acc = ""
        try:
            # 获取用户记忆预算
            try:
                user_settings = get_user_settings(int(user['uid']))
            except Exception:
                user_settings = {"ctx_max_chat": None, "ctx_max_stm": None, "ctx_max_ltm": None}
            ctx_max_chat = int(user_settings.get('ctx_max_chat') or 3000)
            ctx_max_stm = int(user_settings.get('ctx_max_stm') or 3000)
            ctx_max_ltm = int(user_settings.get('ctx_max_ltm') or 4000)

            # 加载结构化画像和记忆
            structured_profile = None
            short_term_memories = []
            long_term_memories = []
            try:
                path = _structured_path_for_role(role, user_id=uid)
                with open(path, 'r', encoding='utf-8') as f:
                    structured_profile = json.load(f)
                # 读取记忆
                short_term_memories, long_term_memories = _read_memories_from_profile(role, uid)
            except Exception:
                structured_profile = {}
            
            # 读取会话历史（从DB）
            # 只读取未压缩的消息，已压缩的消息已经凝练成短期/长期记忆
            try:
                db_items = list_messages(uid, cid, limit=200, only_uncompressed=True)
                msgs_model = [
                    {"role": str(it.get("role", "")), "content": str(it.get("content", ""))}
                    for it in db_items if str(it.get("role", "")) in {"user", "assistant"}
                ]
            except Exception:
                msgs_model = []
            msgs_model = _truncate_messages(msgs_model, ctx_max_chat)

            # 构建六段式 system prompt（包含记忆）
            from fastnpc.chat.prompt_builder import _remove_timestamp_suffix
            from fastnpc.api.auth import get_user_settings
            
            user_name = str(user.get('u') or user.get('username') or '用户')
            role_display_name = _remove_timestamp_suffix(role)
            
            # 获取用户简介
            user_settings = get_user_settings(uid)
            user_profile_text = user_settings.get('profile') or ""
            user_profile_dict = {"简介": user_profile_text} if user_profile_text else None
            
            transcript_lines: List[str] = []
            try:
                for it in msgs_model:
                    r = str(it.get('role', ''))
                    c = str(it.get('content', ''))
                    if r == 'user':
                        transcript_lines.append(f"{user_name}: {c}")
                    elif r == 'assistant':
                        transcript_lines.append(f"{role_display_name}: {c}")
            except Exception:
                pass
            
            if not isinstance(structured_profile, dict):
                structured_profile = {}
            
            system_prompt = build_chat_system_prompt(
                role_name=role,
                user_name=user_name,
                role_profile=structured_profile,
                user_profile=user_profile_dict,
                chat_transcript_lines=transcript_lines,
                include_ltm=True,
                include_stm=True,
                long_term_memories=long_term_memories,
                short_term_memories=short_term_memories,
                max_chars_transcript=ctx_max_chat,
                max_chars_ltm=ctx_max_ltm,
                max_chars_stm=ctx_max_stm,
            )
            
            # 保存实际发送给LLM的system prompt到user消息
            update_message_system_prompt(user_msg_id, system_prompt)
            
            # 导出上下文（仅管理员且开启）
            try:
                _udb = get_user_by_id(uid)
                _is_admin = int(_udb.get('is_admin', 0)) if _udb else 0
            except Exception:
                _is_admin = 0
            # 上下文导出已移除（完全依赖数据库）

            # 调用 OpenRouter 流式
            prompt_msgs = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ]
            for text in stream_openrouter_text(prompt_msgs):
                if not isinstance(text, str):
                    continue
                yield f"data: {text}\n\n"
                acc += text
        finally:
            if acc:
                add_message(int(user['uid']), cid, 'assistant', acc)
                with sessions_lock:
                    msgs.append({"role": "assistant", "content": acc})
                
                # 检查并压缩三层记忆
                try:
                    user_settings = get_user_settings(int(user['uid']))
                    ctx_max_chat = int(user_settings.get('ctx_max_chat') or 3000)
                    ctx_max_stm = int(user_settings.get('ctx_max_stm') or 3000)
                    ctx_max_ltm = int(user_settings.get('ctx_max_ltm') or 4000)
                    user_name = str(user.get('u') or user.get('username') or '用户')
                    _check_and_compress_memories(role, uid, cid, user_name, ctx_max_chat, ctx_max_stm, ctx_max_ltm)
                except Exception as e:
                    print(f"[ERROR] 流式API记忆压缩失败: {e}")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


@router.post("/api/chat/{role}/compress-all")
async def compress_all_session_memory(role: str, request: Request):
    """用户离开聊天界面时，将所有会话记忆压缩为短期记忆"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    role = normalize_role_name(role)
    uid = int(user['uid'])
    cid = get_or_create_character(uid, role)
    user_name = str(user.get('u') or user.get('username') or '用户')
    
    try:
        # 读取所有未压缩的会话记忆
        session_messages = list_messages(uid, cid, limit=200, only_uncompressed=True)
        
        if not session_messages:
            return {"status": "ok", "compressed": 0, "message": "无会话记忆"}
        
        # 全部压缩为短期记忆
        new_stm = compress_to_short_term_memory(session_messages, role, user_name)
        
        if new_stm:
            _append_short_term_memory(role, uid, new_stm)
            
            # 标记这些消息为已压缩
            compressed_ids = [m.get('id') for m in session_messages if m.get('id')]
            if compressed_ids:
                mark_messages_as_compressed(uid, cid, compressed_ids)
            
            print(f"[INFO] 用户离开，压缩 {len(session_messages)} 条会话记忆为 {len(new_stm)} 条短期记忆")
            return {"status": "ok", "compressed": len(new_stm), "message": f"成功压缩 {len(new_stm)} 条短期记忆"}
        else:
            return {"status": "ok", "compressed": 0, "message": "压缩失败或无有效记忆"}
    except Exception as e:
        print(f"[ERROR] 压缩会话记忆失败: {e}")
        return JSONResponse({"error": f"压缩失败: {str(e)}"}, status_code=500)


# HTML 模板路由

@router.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, role: str = Form(...), session_id: str = Form(...), prompt: str = Form(...)):
    with sessions_lock:
        sess = sessions.get(session_id)
        if not sess:
            return HTMLResponse("<div class=\"text-red-600\">会话不存在</div>")
        messages: List[Dict[str, str]] = sess["messages"]  # type: ignore
        messages.append({"role": "user", "content": prompt})
    reply = get_openrouter_completion(messages)
    with sessions_lock:
        messages.append({"role": "assistant", "content": reply})
    # 返回一条聊天气泡，追加到日志
    html = (
        f"<div class=\"chat-item user\"><div class=\"who\">你</div><div class=\"text\">{prompt}</div></div>"
        f"<div class=\"chat-item bot\"><div class=\"who\">角色</div><div class=\"text\">{reply}</div></div>"
    )
    return HTMLResponse(html)

