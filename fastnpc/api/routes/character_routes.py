# -*- coding: utf-8 -*-
"""
角色管理路由模块
"""
from __future__ import annotations

import json
import os
import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from fastnpc.config import CHAR_DIR, TEMPLATES_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.auth import (
    update_character_structured,
    rename_character,
    delete_character,
)
from fastnpc.api.utils import (
    _require_user,
    _structured_path_for_role,
    _list_structured_files,
)
from fastnpc.api.state import TaskState, tasks, tasks_lock, sessions, sessions_lock
from fastnpc.pipeline.structure import build_system_prompt


router = APIRouter()
CHAR_DIR_STR = CHAR_DIR.as_posix()
templates = Jinja2Templates(directory=TEMPLATES_DIR.as_posix())


@router.get("/api/characters")
def api_characters(request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return {"items": _list_structured_files(user_id=user.get('uid'))}


@router.post("/api/characters")
async def api_create_character(background_tasks: BackgroundTasks, request: Request):
    from fastnpc.api.state import _collect_and_structure
    
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    role = normalize_role_name(str(data.get("role", "")).strip())
    source = str(data.get("source", "baike"))
    model = str(data.get("model", "moonshotai/kimi-k2:free"))
    detail = str(data.get("detail", "detailed"))
    # 同名选择参数（可选）
    choice_index = data.get('choice_index')
    try:
        choice_index = int(choice_index) if choice_index is not None else None
    except Exception:
        choice_index = None
    filter_text = data.get('filter_text')
    if filter_text is not None:
        filter_text = str(filter_text)
    chosen_href = data.get('chosen_href')
    if chosen_href is not None:
        chosen_href = str(chosen_href)
    # 导出开关（前端传 boolean）
    export_facts = bool(data.get('export_facts'))
    export_bullets = bool(data.get('export_bullets'))
    export_summary = bool(data.get('export_summary'))
    export_md = bool(data.get('export_md'))
    if detail not in ("concise", "detailed"):
        detail = "detailed"
    if not role:
        return JSONResponse({"error": "role 不能为空"}, status_code=400)
    task_id = uuid.uuid4().hex
    state = TaskState(role=role, source=source, model=model, user_id=user.get('uid'), detail=detail,
                      choice_index=choice_index, filter_text=filter_text, chosen_href=chosen_href,
                      export_facts=export_facts, export_bullets=export_bullets,
                      export_summary=export_summary, export_md=export_md)
    with tasks_lock:
        tasks[task_id] = state
    background_tasks.add_task(_collect_and_structure, task_id)
    return {"task_id": task_id}


@router.put('/api/characters/{old_name}/rename')
async def api_rename_character(old_name: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    old_name = normalize_role_name(old_name)
    new_name = normalize_role_name(str(data.get('new_name', '')).strip())
    if not new_name:
        return JSONResponse({"error": "新名称不能为空"}, status_code=400)
    ok, msg = rename_character(int(user['uid']), old_name, new_name)
    if not ok:
        return JSONResponse({"error": msg}, status_code=400)
    # 同步文件重命名（包含 raw、structured 与中间产物）
    base = os.path.join(CHAR_DIR_STR, str(user['uid']))
    def _rename_if_exists(prefix_old: str, prefix_new: str) -> None:
        oldp = os.path.join(base, f"{prefix_old}{old_name}.json")
        newp = os.path.join(base, f"{prefix_new}{new_name}.json")
        if os.path.exists(oldp):
            try:
                shutil.move(oldp, newp)
            except Exception:
                pass
    # raw
    _rename_if_exists("baike_", "baike_")
    _rename_if_exists("zhwiki_", "zhwiki_")
    # structured
    for prefix in ("structured_", "structured_baike_", "structured_zhwiki_"):
        oldp = os.path.join(base, f"{prefix}{old_name}.json")
        newp = os.path.join(base, f"{prefix}{new_name}.json")
        if os.path.exists(oldp):
            try:
                shutil.move(oldp, newp)
            except Exception:
                pass
    # 中间件
    for ext, pref in ((".json", "facts_"), (".txt", "bullets_"), (".txt", "summary_"), (".md", "md_")):
        oldp = os.path.join(base, f"{pref}{old_name}{ext}")
        newp = os.path.join(base, f"{pref}{new_name}{ext}")
        if os.path.exists(oldp):
            try:
                shutil.move(oldp, newp)
            except Exception:
                pass
    # ctx_* 带时间戳，需批量改名前缀
    try:
        for fname in os.listdir(base):
            if fname.startswith(f"ctx_{old_name}_") and fname.endswith('.json'):
                suffix = fname[len(f"ctx_{old_name}_"):]
                src = os.path.join(base, fname)
                dst = os.path.join(base, f"ctx_{new_name}_" + suffix)
                try:
                    shutil.move(src, dst)
                except Exception:
                    pass
    except Exception:
        pass
    return {"ok": True}


@router.delete('/api/characters/{name}')
def api_delete_character(name: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    delete_character(int(user['uid']), name)
    # 删除用户私有目录的结构化 json
    name = normalize_role_name(name)
    base = os.path.join(CHAR_DIR_STR, str(user['uid']))
    for prefix in ("structured_", "structured_baike_", "structured_zhwiki_"):
        p = os.path.join(base, f"{prefix}{name}.json")
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    # 同时删除原始抓取文件（baike_/zhwiki_）
    for raw_prefix in ("baike_", "zhwiki_"):
        rawp = os.path.join(base, f"{raw_prefix}{name}.json")
        if os.path.exists(rawp):
            try:
                os.remove(rawp)
            except Exception:
                pass
    # 删除中间件（facts/bullets/summary/md）
    for ext, pref in ((".json", "facts_"), (".txt", "bullets_"), (".txt", "summary_"), (".md", "md_")):
        p = os.path.join(base, f"{pref}{name}{ext}")
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    # 删除 ctx_*（带时间戳）
    try:
        for fname in os.listdir(base):
            if fname.startswith(f"ctx_{name}_") and fname.endswith('.json'):
                fp = os.path.join(base, fname)
                try:
                    os.remove(fp)
                except Exception:
                    pass
    except Exception:
        pass
    return {"ok": True}


@router.post('/api/characters/{name}/copy')
async def api_copy_character(name: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    name = normalize_role_name(name)
    # 生成新名称（在现有列表上追加 -副本N）
    base = os.path.join(CHAR_DIR_STR, str(user['uid']))
    os.makedirs(base, exist_ok=True)
    # 读取原文件路径
    path = _structured_path_for_role(name, user_id=user.get('uid'))
    if not os.path.exists(path):
        return JSONResponse({"error": "not_found"}, status_code=404)
    # 生成目标名
    def gen_new(n: int) -> str:
        return f"{name}-副本{n}" if n > 1 else f"{name}-副本"
    idx = 1
    new_name = gen_new(idx)
    while True:
        # 检查文件与 DB 是否存在
        candidate = _structured_path_for_role(normalize_role_name(new_name), user_id=user.get('uid'))
        if not os.path.exists(candidate):
            break
        idx += 1
        new_name = gen_new(idx)
    # 复制文件（structured、raw 与中间件）
    with open(path, 'r', encoding='utf-8') as f:
        prof = json.load(f)
    new_path = _structured_path_for_role(normalize_role_name(new_name), user_id=user.get('uid'))
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(prof, f, ensure_ascii=False, indent=2)
    # raw 同名复制
    base_dir = os.path.join(CHAR_DIR_STR, str(user['uid']))
    for raw_prefix in ("baike_", "zhwiki_"):
        src = os.path.join(base_dir, f"{raw_prefix}{name}.json")
        dst = os.path.join(base_dir, f"{raw_prefix}{normalize_role_name(new_name)}.json")
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copyfile(src, dst)
            except Exception:
                pass
    # 中间件复制
    for ext, pref in ((".json", "facts_"), (".txt", "bullets_"), (".txt", "summary_"), (".md", "md_")):
        src = os.path.join(base_dir, f"{pref}{name}{ext}")
        dst = os.path.join(base_dir, f"{pref}{normalize_role_name(new_name)}{ext}")
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copyfile(src, dst)
            except Exception:
                pass
    # ctx_* 复制并更换前缀
    try:
        for fname in os.listdir(base_dir):
            if fname.startswith(f"ctx_{name}_") and fname.endswith('.json'):
                suffix = fname[len(f"ctx_{name}_"):]
                src = os.path.join(base_dir, fname)
                dst = os.path.join(base_dir, f"ctx_{normalize_role_name(new_name)}_" + suffix)
                if os.path.exists(src) and not os.path.exists(dst):
                    try:
                        shutil.copyfile(src, dst)
                    except Exception:
                        pass
    except Exception:
        pass
    # 同步 DB
    try:
        update_character_structured(int(user['uid']), normalize_role_name(new_name), json.dumps(prof, ensure_ascii=False))
    except Exception:
        pass
    return {"ok": True, "new_name": new_name}


@router.get("/api/characters/{role}/structured")
def api_get_structured(role: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    role = normalize_role_name(role)
    path = _structured_path_for_role(role, user_id=user.get('uid'))
    if not os.path.exists(path):
        return JSONResponse({"error": "not_found"}, status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.put("/api/characters/{role}/structured")
async def api_put_structured(role: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid json: {e}"}, status_code=400)
    role = normalize_role_name(role)
    path = _structured_path_for_role(role, user_id=user.get('uid'))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # 重置该角色会话，以便基于新设定生成 system 提示
    with sessions_lock:
        for sid, sess in list(sessions.items()):
            if sess.get("role") == role:
                del sessions[sid]
    return {"ok": True}


# HTML 模板路由

@router.get("/structured/view", response_class=HTMLResponse)
def structured_view(request: Request, role: str):
    user = _require_user(request)
    uid = user.get('uid') if user else None
    role = normalize_role_name(role)
    path = _structured_path_for_role(role, user_id=uid)
    if not os.path.exists(path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="结构化文件不存在")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 初始化会话
    session_id = uuid.uuid4().hex
    profile = json.loads(content)
    system_prompt = build_system_prompt(profile)
    with sessions_lock:
        sessions[session_id] = {"messages": [{"role": "system", "content": system_prompt}], "role": role}
    return templates.TemplateResponse(
        "partials/structured_editor.html",
        {"request": request, "role": role, "content": content, "session_id": session_id},
    )


@router.put("/structured/{role}")
async def structured_save(role: str, request: Request):
    # 接收表单或 JSON
    content_type = request.headers.get("content-type", "")
    raw_text = ""
    if "application/json" in content_type:
        data = await request.json()
        raw_text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        form = await request.form()
        raw_text = str(form.get("content", ""))
    # 校验 JSON
    try:
        parsed = json.loads(raw_text)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"JSON 解析失败: {e}"}, status_code=400)
    role = normalize_role_name(role)
    user = _require_user(request)
    uid = user.get('uid') if user else None
    path = _structured_path_for_role(role, user_id=uid)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    # 同步至 DB
    try:
        if uid:
            update_character_structured(int(uid), role, json.dumps(parsed, ensure_ascii=False))
    except Exception:
        pass
    return JSONResponse({"ok": True})

