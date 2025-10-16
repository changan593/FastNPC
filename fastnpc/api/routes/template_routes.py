# -*- coding: utf-8 -*-
"""
HTML 模板路由模块
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastnpc.config import TEMPLATES_DIR


router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR.as_posix())


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    models = [
        "z-ai/glm-4-32b",
        "z-ai/glm-4.5-air:free",
        "deepseek/deepseek-chat-v3.1:free",
        "tencent/hunyuan-a13b-instruct:free",
    ]
    sources = [
        {"value": "zhwiki", "label": "中文维基 (zhwiki)"},
        {"value": "baike", "label": "百度百科 (baike)"},
    ]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "models": models,
            "sources": sources,
        },
    )


@router.get("/health")
def health():
    return {"ok": True}

