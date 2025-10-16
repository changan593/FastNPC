# -*- coding: utf-8 -*-
"""
用户设置路由模块
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastnpc.api.auth import (
    get_user_settings,
    update_user_settings,
    change_password,
    delete_account,
    verify_user,
)
from fastnpc.api.utils import _require_user


router = APIRouter()

ALLOWED_MODELS = [
    "z-ai/glm-4-32b",
    "z-ai/glm-4.5-air:free",
    "deepseek/deepseek-chat-v3.1:free",
    "tencent/hunyuan-a13b-instruct:free",
]


@router.get('/api/me/settings')
def api_get_settings(request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    uid = int(user['uid'])
    s = get_user_settings(uid)
    return {"settings": s}


@router.put('/api/me/settings')
async def api_put_settings(request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    uid = int(user['uid'])
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid json: {e}"}, status_code=400)
    default_model = str(payload.get('default_model') or '').strip() or None
    if default_model and default_model not in ALLOWED_MODELS:
        return JSONResponse({"error": "default_model 不在允许列表"}, status_code=400)
    # 读取三项记忆预算（字符数量）
    def _to_int(v, default=None):
        try:
            if v is None or v == "":
                return default
            return int(v)
        except Exception:
            return default
    ctx_max_chat = _to_int(payload.get('ctx_max_chat'))
    ctx_max_stm = _to_int(payload.get('ctx_max_stm'))
    ctx_max_ltm = _to_int(payload.get('ctx_max_ltm'))
    # 读取用户简介
    profile = payload.get('profile')
    if profile is not None:
        profile = str(profile).strip() or None
    # 读取群聊最大角色回复轮数
    max_group_reply_rounds = _to_int(payload.get('max_group_reply_rounds'), default=3)
    update_user_settings(uid, default_model, "", ctx_max_chat=ctx_max_chat, ctx_max_stm=ctx_max_stm, ctx_max_ltm=ctx_max_ltm, profile=profile, max_group_reply_rounds=max_group_reply_rounds)
    return {"ok": True}


@router.put('/api/me/password')
async def api_put_password(request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    uid = int(user['uid'])
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid json: {e}"}, status_code=400)
    old_password = str(payload.get('old_password') or '')
    new_password = str(payload.get('new_password') or '')
    if len(new_password) < 6:
        return JSONResponse({"error": "新密码至少6位"}, status_code=400)
    ok, msg = change_password(uid, old_password, new_password)
    if not ok:
        return JSONResponse({"error": msg}, status_code=400)
    return {"ok": True}


@router.post('/api/me/delete')
async def api_delete_me(request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    uid = int(user['uid'])
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid json: {e}"}, status_code=400)
    password = str(payload.get('password') or '')
    # 验证密码
    u = verify_user(str(user.get('u', '')), password)
    if not u:
        return JSONResponse({"error": "密码不正确"}, status_code=400)
    # 删除账号数据
    try:
        delete_account(uid)
    except Exception as e:
        return JSONResponse({"error": f"删除失败: {e}"}, status_code=500)
    # 清理 Cookie
    resp = JSONResponse({"ok": True})
    resp.delete_cookie('fastnpc_auth', path='/')
    return resp

