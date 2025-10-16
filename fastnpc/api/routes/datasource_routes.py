# -*- coding: utf-8 -*-
"""
数据源路由模块
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastnpc.api.utils import _require_user
from fastnpc.datasources.baike import get_polysemant_options as baike_get_polysemant_options, get_full as baike_get_full
from fastnpc.datasources.zhwiki import get_polysemant_options as zhwiki_get_polysemant_options


router = APIRouter()


@router.get('/api/baike/polysemant')
def api_baike_polysemant(keyword: str, request: Request, limit: int = 120, strict: int = 1):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    kw = str(keyword or '').strip()
    if not kw:
        return JSONResponse({"error": "keyword 不能为空"}, status_code=400)
    try:
        items, route = baike_get_polysemant_options(kw, limit=limit, strict=bool(strict), return_route=True)
        if not items:
            # 即时重试一次以对抗偶发风控
            time.sleep(0.4)
            items = baike_get_polysemant_options(kw, limit=limit)
    except Exception as e:
        return JSONResponse({"error": f"failed: {e}"}, status_code=500)
    return {"items": items, "route": route}


@router.get('/api/zhwiki/polysemant')
def api_zhwiki_polysemant(keyword: str, request: Request, limit: int = 80):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    kw = str(keyword or '').strip()
    if not kw:
        return JSONResponse({"error": "keyword 不能为空"}, status_code=400)
    try:
        items, route = zhwiki_get_polysemant_options(kw, limit=limit, return_route=True)
    except Exception as e:
        return JSONResponse({"error": f"failed: {e}"}, status_code=500)
    return {"items": items, "route": route}


@router.post('/api/baike/full')
async def api_baike_full(request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid json: {e}"}, status_code=400)
    keyword = str(payload.get('keyword', '')).strip()
    if not keyword:
        return JSONResponse({"error": "keyword 不能为空"}, status_code=400)
    retries = int(payload.get('retries') or 3)
    min_sections = int(payload.get('min_sections') or 0)
    min_chars = int(payload.get('min_chars') or 500)
    choice_index = payload.get('choice_index')
    try:
        if choice_index is not None:
            choice_index = int(choice_index)
    except Exception:
        choice_index = None
    filter_text = payload.get('filter_text')
    if filter_text is not None:
        filter_text = str(filter_text)
    try:
        data = baike_get_full(keyword, retries=retries, min_sections=min_sections, min_chars=min_chars,
                               choice_index=choice_index, filter_text=filter_text)
    except Exception as e:
        return JSONResponse({"error": f"failed: {e}"}, status_code=500)
    return data

