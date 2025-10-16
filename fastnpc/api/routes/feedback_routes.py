# -*- coding: utf-8 -*-
"""
反馈路由模块
"""
from __future__ import annotations

import os
import json
import base64
from typing import Optional

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse

from fastnpc.config import CHAR_DIR
from fastnpc.api.auth import (
    create_feedback,
    list_feedbacks,
    get_feedback_detail,
    update_feedback_status,
    delete_feedback,
)
from fastnpc.api.utils import _require_user, _require_admin


router = APIRouter()

# 创建反馈附件目录
FEEDBACK_DIR = CHAR_DIR.parent / "Feedbacks"
FEEDBACK_DIR.mkdir(exist_ok=True)


@router.post('/api/feedbacks')
async def submit_feedback(request: Request):
    """提交反馈"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    try:
        body = await request.json()
        title = body.get('title', '')
        content = body.get('content', '')
        attachments = body.get('attachments')
        
        feedback_id = create_feedback(
            user_id=user['uid'],
            title=title,
            content=content,
            attachments=attachments
        )
        return {"ok": True, "id": feedback_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post('/api/feedbacks/upload')
async def upload_feedback_attachment(request: Request, file: UploadFile = File(...)):
    """上传反馈附件（图片）"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    # 只允许图片
    if not file.content_type or not file.content_type.startswith('image/'):
        return JSONResponse({"error": "只支持图片格式"}, status_code=400)
    
    # 限制文件大小 5MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return JSONResponse({"error": "图片大小不能超过5MB"}, status_code=400)
    
    try:
        # 生成文件名
        import time
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"{user['uid']}_{int(time.time())}_{file.filename}"
        filepath = FEEDBACK_DIR / filename
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(content)
        
        return {"ok": True, "filename": filename, "url": f"/feedbacks/{filename}"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get('/api/feedbacks')
def get_user_feedbacks(request: Request):
    """获取当前用户的反馈列表"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    feedbacks = list_feedbacks(user_id=user['uid'])
    return {"items": feedbacks}


@router.get('/api/feedbacks/{feedback_id}')
def get_feedback(request: Request, feedback_id: int):
    """获取反馈详情"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    feedback = get_feedback_detail(feedback_id)
    if not feedback:
        return JSONResponse({"error": "反馈不存在"}, status_code=404)
    
    # 非管理员只能查看自己的反馈
    if user['is_admin'] != 1 and feedback['user_id'] != user['uid']:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    return {"feedback": feedback}


# ============= 管理员接口 =============

@router.get('/admin/feedbacks')
def admin_list_feedbacks(request: Request, status: Optional[str] = None):
    """管理员查看所有反馈"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    feedbacks = list_feedbacks(status=status)
    return {"items": feedbacks}


@router.get('/admin/feedbacks/{feedback_id}')
def admin_get_feedback(request: Request, feedback_id: int):
    """管理员查看反馈详情"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    feedback = get_feedback_detail(feedback_id)
    if not feedback:
        return JSONResponse({"error": "反馈不存在"}, status_code=404)
    
    return {"feedback": feedback}


@router.put('/admin/feedbacks/{feedback_id}')
async def admin_update_feedback(request: Request, feedback_id: int):
    """管理员更新反馈状态和回复"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        body = await request.json()
        status = body.get('status')
        admin_reply = body.get('admin_reply')
        
        if not status:
            return JSONResponse({"error": "status is required"}, status_code=400)
        
        update_feedback_status(feedback_id, status, admin_reply)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete('/admin/feedbacks/{feedback_id}')
def admin_delete_feedback(request: Request, feedback_id: int):
    """管理员删除反馈"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        delete_feedback(feedback_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

