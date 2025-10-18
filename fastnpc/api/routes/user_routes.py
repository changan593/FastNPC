# -*- coding: utf-8 -*-
"""
用户设置路由模块
"""
from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from pathlib import Path

from fastnpc.config import BASE_DIR, USE_POSTGRESQL
from fastnpc.api.auth import (
    get_user_settings,
    update_user_settings,
    change_password,
    delete_account,
    verify_user,
    _get_conn,
    _return_conn,
    _row_to_dict,
)
from fastnpc.api.utils import _require_user
from fastnpc.utils.image_utils import process_uploaded_avatar


router = APIRouter()

ALLOWED_MODELS = [
    "z-ai/glm-4-32b",
    "z-ai/glm-4.5-air:free",
    "deepseek/deepseek-chat-v3.1:free",
    "tencent/hunyuan-a13b-instruct:free",
]

AVATAR_DIR = BASE_DIR / "Avatars"


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
    
    # 验证记忆预算范围（50-5000）
    if ctx_max_chat is not None and (ctx_max_chat < 50 or ctx_max_chat > 5000):
        return JSONResponse({"error": "会话记忆预算必须在50-5000之间"}, status_code=400)
    if ctx_max_stm is not None and (ctx_max_stm < 50 or ctx_max_stm > 5000):
        return JSONResponse({"error": "短期记忆预算必须在50-5000之间"}, status_code=400)
    if ctx_max_ltm is not None and (ctx_max_ltm < 50 or ctx_max_ltm > 5000):
        return JSONResponse({"error": "长期记忆预算必须在50-5000之间"}, status_code=400)
    
    # 读取用户简介（限制200字）
    profile = payload.get('profile')
    if profile is not None:
        profile = str(profile).strip() or None
        if profile and len(profile) > 200:
            return JSONResponse({"error": "个人简介不能超过200字"}, status_code=400)
    
    # 读取群聊最大角色回复轮数（3-10）
    max_group_reply_rounds = _to_int(payload.get('max_group_reply_rounds'), default=3)
    if max_group_reply_rounds < 3 or max_group_reply_rounds > 10:
        return JSONResponse({"error": "群聊最大角色回复轮数必须在3-10之间"}, status_code=400)
    
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


@router.post("/api/user/avatar")
async def upload_user_avatar(request: Request, file: UploadFile = File(...)):
    """上传用户头像"""
    user = _require_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    uid = int(user['uid'])

    try:
        # 处理上传的图片
        avatar_filename = f"user_{uid}_avatar"
        avatar_url = await process_uploaded_avatar(file, avatar_filename)

        # 更新数据库
        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE users SET avatar_url=%s WHERE id=%s",
                (avatar_url, uid)
            )
            conn.commit()
        finally:
            _return_conn(conn)

        return JSONResponse({"ok": True, "avatar_url": avatar_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {e}")


@router.delete("/api/user/avatar")
async def delete_user_avatar(request: Request):
    """删除用户头像"""
    user = _require_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    uid = int(user['uid'])

    try:
        # 删除头像文件
        pattern = f"user_{uid}_avatar_*.jpg"
        for f in AVATAR_DIR.glob(pattern):
            try:
                os.remove(f)
                print(f"[INFO] 已删除用户头像文件: {f}")
            except Exception as e:
                print(f"[WARN] 删除用户头像文件失败 {f}: {e}")

        # 更新数据库
        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE users SET avatar_url=%s WHERE id=%s",
                (None, uid)
            )
            conn.commit()
        finally:
            _return_conn(conn)

        return JSONResponse({"ok": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete avatar: {e}")


@router.get("/api/user/profile")
async def get_user_profile(request: Request):
    """获取用户信息（包括头像）"""
    user = _require_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    uid = int(user['uid'])

    try:
        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, username, avatar_url, is_admin FROM users WHERE id=%s",
                (uid,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            if USE_POSTGRESQL:
                user_data = _row_to_dict(row, cur)
            else:
                user_data = dict(row)
            
            return JSONResponse({
                "ok": True,
                "user": {
                    "id": user_data['id'],
                    "username": user_data['username'],
                    "avatar_url": user_data.get('avatar_url') or '',
                    "is_admin": bool(user_data.get('is_admin', 0))
                }
            })
        finally:
            _return_conn(conn)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {e}")

