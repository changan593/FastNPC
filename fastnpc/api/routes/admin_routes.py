# -*- coding: utf-8 -*-
"""
管理员路由模块
"""
from __future__ import annotations

import json
import os
from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastnpc.config import CHAR_DIR
from fastnpc.api.auth import (
    list_users,
    list_characters,
    get_user_by_id,
    get_character_detail,
    list_messages,
    get_user_settings,
    get_or_create_character,
    list_group_chats,
    get_group_chat_detail,
    list_group_messages,
    list_group_members,
)
from fastnpc.api.utils import _require_admin, _require_user, _structured_path_for_role, _load_character_profile, _read_memories_from_profile
from fastnpc.utils.roles import normalize_role_name
from fastnpc.chat.prompt_builder import build_chat_system_prompt


router = APIRouter()
CHAR_DIR_STR = CHAR_DIR.as_posix()


@router.get('/admin/users')
def admin_users(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return {"items": list_users()}


@router.get('/admin/users/{uid}/characters')
def admin_user_characters(uid: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return {"items": list_characters(uid)}


@router.post('/admin/users/{uid}/characters/cleanup')
def admin_cleanup_characters(uid: int, request: Request):
    """清理数据库中文件已不存在的角色记录"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    from fastnpc.api.auth import _get_conn
    
    # 获取数据库中的所有角色
    characters = list_characters(uid)
    deleted_count = 0
    deleted_names = []
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        for char in characters:
            char_name = char['name']
            # 检查结构化文件是否存在
            struct_path = _structured_path_for_role(char_name, user_id=uid)
            if not os.path.exists(struct_path):
                # 文件不存在，删除数据库记录
                cur.execute("DELETE FROM characters WHERE id=?", (char['id'],))
                # 同时删除相关的消息记录
                cur.execute("DELETE FROM messages WHERE character_id=?", (char['id'],))
                deleted_count += 1
                deleted_names.append(char_name)
                print(f"[INFO] 已清理不存在的角色: {char_name} (用户{uid})")
        
        conn.commit()
    finally:
        conn.close()
    
    return {
        "ok": True,
        "deleted_count": deleted_count,
        "deleted_names": deleted_names
    }


@router.get('/admin/users/{uid}')
def admin_user_detail(uid: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    user = get_user_by_id(uid)
    if not user:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return {"user": user}


@router.get('/admin/users/{uid}/characters/{cid}')
def admin_user_character_detail(uid: int, cid: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    detail = get_character_detail(uid, cid)
    if not detail:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return {"character": detail}


@router.get('/admin/users/{uid}/characters/{cid}/messages')
def admin_user_character_messages(uid: int, cid: int, request: Request, limit: int = 200, after_id: int = 0):
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    items = list_messages(uid, cid, limit=limit, after_id=after_id)
    return {"messages": items}


@router.get('/admin/chat/compiled')
def admin_chat_compiled(request: Request, msg_id: int, uid: int = 0, cid: int = 0, role: str = ""):
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    # 仅管理员可查看任意用户上下文
    admin_user = _require_user(request)
    if not admin_user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    # 加载用户设置（字符预算）
    try:
        s = get_user_settings(uid)
    except Exception:
        s = {"ctx_max_chat": 3000, "ctx_max_stm": 3000, "ctx_max_ltm": 4000}
    ctx_max_chat = int(s.get('ctx_max_chat') or 3000)
    ctx_max_stm = int(s.get('ctx_max_stm') or 3000)
    ctx_max_ltm = int(s.get('ctx_max_ltm') or 4000)
    # 解析角色/角色ID（支持两种调用：指定 uid+cid 或仅 role= 当前登录者角色）
    role = normalize_role_name(role) if role else role
    detail = None
    if uid and cid:
        try:
            detail = get_character_detail(uid, cid)
            role = normalize_role_name(str(detail.get('name') or role))
        except Exception:
            detail = None
    else:
        # 使用当前管理员自己的 uid 与 role 获取/创建角色ID
        cu = _require_user(request)
        if not cu:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        uid = int(cu['uid'])
        role = normalize_role_name(role)
        cid = get_or_create_character(uid, role)
    try:
        # 只读取未压缩的消息（模拟实际发送给LLM的上下文）
        items = list_messages(uid, cid, limit=2000, only_uncompressed=True)
    except Exception:
        items = []
    # 仅取到 msg_id 为止的历史
    hist = [it for it in items if int(it.get('id', 0)) <= int(msg_id)]
    
    # 定位该条用户消息
    target_msg = next((it for it in hist if int(it.get('id', 0)) == int(msg_id) and str(it.get('role', '')) == 'user'), None)
    if not target_msg:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    user_msg = str(target_msg.get('content', ''))
    
    # 优先使用保存的system_prompt_snapshot（实际发送时的快照）
    system_prompt_snapshot = target_msg.get('system_prompt_snapshot')
    
    if system_prompt_snapshot:
        # 直接使用保存的快照（这是实际发送给LLM的内容）
        system_prompt = system_prompt_snapshot
    else:
        # 快照不存在，重新构建（向后兼容旧消息）
        # 构造带名称的对话记录（被对话的用户名称）
        try:
            if uid:
                uinfo = get_user_by_id(uid)
                user_name = str((uinfo or {}).get('username') or '用户')
            else:
                cu2 = _require_user(request)
                user_name = str((cu2 or {}).get('u') or '用户')
        except Exception:
            user_name = '用户'
        transcript_lines: List[str] = []
        for it in hist:
            r = str(it.get('role', ''))
            c = str(it.get('content', ''))
            if r == 'user':
                transcript_lines.append(f"{user_name}: {c}")
            elif r == 'assistant':
                transcript_lines.append(f"{role}: {c}")
        # 角色画像（从数据库加载）
        try:
            structured_profile = _load_character_profile(role, uid) or {}
        except Exception as e:
            print(f"[WARNING] 加载角色profile失败: {e}")
            structured_profile = {}
        
        # 读取短期和长期记忆
        try:
            stm_list, ltm_list = _read_memories_from_profile(role, uid)
        except Exception:
            stm_list, ltm_list = [], []
        
        # 生成六段式 system 提示
        system_prompt = build_chat_system_prompt(
            role_name=role,
            user_name=user_name,
            role_profile=structured_profile if isinstance(structured_profile, dict) else {},
            user_profile=None,
            chat_transcript_lines=transcript_lines,
            include_ltm=True,
            include_stm=True,
            long_term_memories=ltm_list,
            short_term_memories=stm_list,
            max_chars_transcript=ctx_max_chat,
            max_chars_ltm=ctx_max_ltm,
            max_chars_stm=ctx_max_stm,
        )
    prompt_msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    # 仅返回与 OpenRouter API 一致的 payload（messages 数组）
    return prompt_msgs


# ============= 群聊管理 =============

@router.get('/admin/users/{uid}/groups')
def admin_user_groups(uid: int, request: Request):
    """获取用户的群聊列表"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    groups = list_group_chats(uid)
    return {"items": groups}


@router.get('/admin/groups/{group_id}')
def admin_group_detail(group_id: int, request: Request):
    """获取群聊详情（包括成员列表）"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    # 获取群聊基本信息（需要验证权限，但管理员可以查看任何群聊）
    # 我们需要修改一下逻辑，先获取群聊的user_id
    from fastnpc.api.auth import _get_conn
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, created_at, updated_at FROM group_chats WHERE id=?", (group_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "群聊不存在"}, status_code=404)
        
        group_info = {
            "id": group_id,
            "user_id": row['user_id'],
            "name": row['name'],
            "created_at": row['created_at'],
            "updated_at": row['updated_at']
        }
        
        # 获取成员列表
        members = list_group_members(group_id)
        group_info['members'] = members
        
        return {"group": group_info}
    finally:
        conn.close()


@router.get('/admin/groups/{group_id}/messages')
def admin_group_messages(group_id: int, request: Request, limit: int = 200):
    """获取群聊消息"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    messages = list_group_messages(group_id, limit=limit)
    return {"messages": messages}

