# -*- coding: utf-8 -*-
"""
认证路由模块
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastnpc.api.auth import create_user, verify_user, issue_cookie, get_user_by_id
from fastnpc.api.utils import _require_user


router = APIRouter()


@router.post('/auth/register')
async def auth_register(request: Request):
    data = await request.json()
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    if not username or not password:
        return JSONResponse({"error": "用户名与密码必填"}, status_code=400)
    ok, msg = create_user(username, password)
    if not ok:
        return JSONResponse({"error": msg}, status_code=400)
    user = verify_user(username, password)
    token = issue_cookie(user['id'], user['username']) if user else ''
    resp = JSONResponse({"ok": True, "user": user})
    if token:
        resp.set_cookie('fastnpc_auth', token, httponly=True, samesite='lax', path='/')
    return resp


@router.post('/auth/login')
async def auth_login(request: Request):
    data = await request.json()
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    user = verify_user(username, password)
    if not user:
        return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
    token = issue_cookie(user['id'], user['username'])
    resp = JSONResponse({"ok": True, "user": user})
    resp.set_cookie('fastnpc_auth', token, httponly=True, samesite='lax', path='/')
    return resp


@router.post('/auth/logout')
async def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie('fastnpc_auth', path='/')
    return resp


@router.get('/auth/me')
def auth_me(request: Request):
    data = _require_user(request)
    if not data:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    # 补充 is_admin 信息
    try:
        uid = int(data.get('uid'))
        user = get_user_by_id(uid)
        if user:
            return {"id": uid, "username": data.get('u'), "is_admin": int(user.get('is_admin', 0))}
    except Exception:
        pass
    return {"id": data.get('uid'), "username": data.get('u'), "is_admin": 0}

