# -*- coding: utf-8 -*-
"""
角色管理路由模块
"""
from __future__ import annotations

import json
import os
import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from fastnpc.config import CHAR_DIR, TEMPLATES_DIR, BASE_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.auth import (
    update_character_structured,
    rename_character,
    delete_character,
    load_character_full_data,
    save_character_full_data,
    get_character_id,
    load_character_memories,
    save_character_memories,
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
    # 立即设置初始进度（避免前端轮询时看到0%）
    state.status = "pending"
    state.progress = 1
    state.message = "任务已创建，等待执行..."
    
    with tasks_lock:
        tasks[task_id] = state
    
    print(f"[INFO] 创建角色任务: task_id={task_id}, role={role}, user_id={user.get('uid')}")
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
    # 数据库操作已完成，不再操作文件系统
    return {"ok": True}


@router.delete('/api/characters/{name}')
def api_delete_character(name: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    uid = int(user['uid'])
    print(f"[DEBUG] API: 开始删除角色 {name}, user_id={uid}")
    delete_character(uid, name)
    print(f"[DEBUG] API: 角色删除完成 {name}, user_id={uid}")
    # 数据库级联删除已完成，不再操作文件系统
    return {"ok": True}


@router.post('/api/characters/{name}/copy')
async def api_copy_character(name: str, request: Request):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    name = normalize_role_name(name)
    uid = int(user['uid'])
    
    # 从数据库获取原角色数据
    char_id = get_character_id(uid, name)
    if not char_id:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    # 加载完整数据（包括百科内容）
    full_data = load_character_full_data(char_id)
    if not full_data:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    # 提取百科内容、头像URL和结构化数据
    baike_content = full_data.pop('baike_content', None)
    metadata = full_data.get('_metadata', {})
    original_avatar = metadata.get('avatar_url', '')
    structured_data = {k: v for k, v in full_data.items() if k != '_metadata'}
    
    # 生成新名称（在现有列表上追加 -副本N）
    def gen_new(n: int) -> str:
        return f"{name}-副本{n}" if n > 1 else f"{name}-副本"
    
    idx = 1
    new_name = gen_new(idx)
    while True:
        # 检查数据库中是否存在
        if not get_character_id(uid, normalize_role_name(new_name)):
            break
        idx += 1
        new_name = gen_new(idx)
    
    new_name = normalize_role_name(new_name)
    
    # 复制头像（如果有）
    new_avatar_url = None
    if original_avatar:
        try:
            from fastnpc.config import BASE_DIR
            import shutil
            
            # 提取原头像文件名
            orig_filename = original_avatar.split('/')[-1]
            orig_path = (BASE_DIR / "Avatars" / orig_filename).as_posix()
            
            if os.path.exists(orig_path):
                # 生成新头像文件名
                new_filename = f"user_{uid}_{new_name}.jpg"
                new_path = (BASE_DIR / "Avatars" / new_filename).as_posix()
                
                # 复制文件
                shutil.copy2(orig_path, new_path)
                new_avatar_url = f"/avatars/{new_filename}"
                print(f"[INFO] 头像已复制: {orig_path} -> {new_path}")
            else:
                print(f"[WARN] 原头像文件不存在: {orig_path}")
        except Exception as e:
            print(f"[WARN] 复制头像失败: {e}")
    
    # 保存到数据库
    try:
        save_character_full_data(
            user_id=uid,
            name=new_name,
            structured_data=structured_data,
            baike_content=baike_content,
            avatar_url=new_avatar_url or original_avatar
        )
        
        # 清除角色列表缓存，确保前端立即看到新角色
        try:
            from fastnpc.api.cache import get_redis_cache
            cache = get_redis_cache()
            cache.delete(f"char_list:{uid}")
            print(f"[INFO] 复制角色后清除缓存: char_list:{uid}")
        except Exception as cache_err:
            print(f"[WARNING] 清除缓存失败（不影响功能）: {cache_err}")
            
    except Exception as e:
        return JSONResponse({"error": f"复制失败: {e}"}, status_code=500)
    
    return {"ok": True, "new_name": new_name}


@router.get("/api/characters/{role}/structured")
def api_get_structured(role: str, request: Request):
    """从数据库获取角色的结构化数据"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    role = normalize_role_name(role)
    
    # 获取角色ID
    char_id = get_character_id(user.get('uid'), role)
    if not char_id:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    # 从数据库加载完整数据
    full_data = load_character_full_data(char_id)
    if not full_data:
        # 如果数据库没有，尝试从文件加载（向后兼容）
        path = _structured_path_for_role(role, user_id=user.get('uid'))
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    # 移除内部元数据和百科内容，只返回结构化数据
    response_data = {k: v for k, v in full_data.items() if k not in ['_metadata', 'baike_content']}
    return response_data


@router.put("/api/characters/{role}/structured")
async def api_put_structured(role: str, request: Request):
    """更新角色的结构化数据到数据库"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid json: {e}"}, status_code=400)
    
    role = normalize_role_name(role)
    
    # 获取角色ID
    char_id = get_character_id(user.get('uid'), role)
    if not char_id:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    try:
        # 保存到数据库
        save_character_full_data(
            user_id=user.get('uid'),
            name=role,
            structured_data=payload,
            baike_content=None  # 不更新百科内容
        )
        
        # 重置该角色会话，以便基于新设定生成 system 提示
        with sessions_lock:
            for sid, sess in list(sessions.items()):
                if sess.get("role") == role:
                    del sessions[sid]
        
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": f"save failed: {e}"}, status_code=500)


# HTML 模板路由

@router.get("/structured/view", response_class=HTMLResponse)
def structured_view(request: Request, role: str):
    """查看角色结构化数据（从数据库加载）"""
    user = _require_user(request)
    uid = user.get('uid') if user else None
    role = normalize_role_name(role)
    
    # 获取角色ID
    char_id = get_character_id(uid, role)
    if not char_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 从数据库加载
    full_data = load_character_full_data(char_id)
    if not full_data:
        # 向后兼容：如果数据库没有，从文件加载
        path = _structured_path_for_role(role, user_id=uid)
        if not os.path.exists(path):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="结构化文件不存在")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # 从数据库数据生成JSON字符串
        profile = {k: v for k, v in full_data.items() if k not in ['_metadata', 'baike_content']}
        content = json.dumps(profile, ensure_ascii=False, indent=2)
    
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
    """保存角色结构化数据到数据库"""
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
    
    if not uid:
        return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
    
    # 获取角色ID
    char_id = get_character_id(uid, role)
    if not char_id:
        return JSONResponse({"ok": False, "error": "角色不存在"}, status_code=404)
    
    try:
        # 保存到数据库
        save_character_full_data(
            user_id=uid,
            name=role,
            structured_data=parsed,
            baike_content=None  # 不更新百科内容
        )
        
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"保存失败: {e}"}, status_code=500)


@router.get("/api/characters/{role}/memories")
def api_get_memories(role: str, request: Request):
    """获取角色的记忆（短期和长期）"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    role = normalize_role_name(role)
    
    # 获取角色ID
    char_id = get_character_id(user.get('uid'), role)
    if not char_id:
        return JSONResponse({"error": "角色不存在"}, status_code=404)
    
    try:
        # 从数据库加载记忆
        memories = load_character_memories(char_id)
        return {
            "short_term": memories.get('short_term', []),
            "long_term": memories.get('long_term', [])
        }
    except Exception as e:
        print(f"[ERROR] 加载记忆失败: {e}")
        return {"short_term": [], "long_term": []}


@router.put("/api/characters/{role}/memories")
async def api_put_memories(role: str, request: Request):
    """保存角色的记忆（短期和长期）"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    role = normalize_role_name(role)
    
    # 获取角色ID
    char_id = get_character_id(user.get('uid'), role)
    if not char_id:
        return JSONResponse({"error": "角色不存在"}, status_code=404)
    
    try:
        payload = await request.json()
        short_term = payload.get('short_term', [])
        long_term = payload.get('long_term', [])
        
        # 保存到数据库
        save_character_memories(char_id, short_term=short_term, long_term=long_term)
        
        return {"ok": True}
    except Exception as e:
        print(f"[ERROR] 保存记忆失败: {e}")
        return JSONResponse({"error": f"保存失败: {e}"}, status_code=500)

