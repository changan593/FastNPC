# -*- coding: utf-8 -*-
"""
任务路由模块
"""
from __future__ import annotations

import uuid
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastnpc.config import TEMPLATES_DIR
from fastnpc.api.state import TaskState, tasks, tasks_lock, _collect_and_structure


router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR.as_posix())


@router.post("/collect", response_class=HTMLResponse)
def collect(request: Request, background_tasks: BackgroundTasks, role: str = Form(...), source: str = Form(...), model: str = Form("z-ai/glm-4-32b"),
            detail: str = Form("detailed"), choice_index: Optional[int] = Form(None), filter_text: Optional[str] = Form(None),
            export_facts: Optional[str] = Form(None), export_bullets: Optional[str] = Form(None)):
    task_id = uuid.uuid4().hex
    try:
        ci = int(choice_index) if choice_index is not None else None
    except Exception:
        ci = None
    ef = bool(export_facts)
    eb = bool(export_bullets)
    state = TaskState(role=role, source=source, model=model, detail=detail, choice_index=ci, filter_text=filter_text,
                      export_facts=ef, export_bullets=eb)
    with tasks_lock:
        tasks[task_id] = state
    background_tasks.add_task(_collect_and_structure, task_id)
    # 返回进度条部件
    return templates.TemplateResponse(
        "partials/progress.html",
        {
            "request": request,
            "task_id": task_id,
            "progress": state.progress,
            "status": state.status,
            "message": state.message,
        },
    )


@router.get("/progress/{task_id}", response_class=HTMLResponse)
def progress(request: Request, task_id: str):
    t = tasks.get(task_id)
    if not t:
        return HTMLResponse("<div class=\"text-red-600\">任务不存在</div>")
    now = int(time.time())
    elapsed = max(0, now - getattr(t, 'started_at', now))
    def _fmt(sec: int) -> str:
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return (f"{h:02d}:{m:02d}:{s:02d}") if h else (f"{m:02d}:{s:02d}")
    return templates.TemplateResponse(
        "partials/progress.html",
        {
            "request": request,
            "task_id": task_id,
            "progress": t.progress,
            "status": t.status,
            "message": t.message,
            "elapsed_text": _fmt(elapsed),
            "role": t.role,
        },
    )


@router.get("/api/tasks/{task_id}")
def api_task(task_id: str):
    t = tasks.get(task_id)
    if not t:
        return {"status": "not_found"}
    now = int(time.time())
    return {
        "status": t.status,
        "progress": t.progress,
        "message": t.message,
        "role": t.role,
        "raw_path": t.raw_path,
        "structured_path": t.structured_path,
        "started_at": getattr(t, 'started_at', None),
        "elapsed_sec": (max(0, now - getattr(t, 'started_at', now)) if getattr(t, 'started_at', None) else None),
    }

