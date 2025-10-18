# -*- coding: utf-8 -*-
"""
提示词管理API路由
管理员专用
"""
from __future__ import annotations

import json
import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastnpc.api.utils import _require_admin
from fastnpc.api.auth import _get_conn, _return_conn, _row_to_dict
from fastnpc.config import USE_POSTGRESQL
from fastnpc.prompt_manager import PromptManager
from fastnpc.prompt_evaluator import PromptEvaluator


router = APIRouter()


@router.get('/admin/prompts')
async def list_prompts(request: Request, category: Optional[str] = None, include_inactive: bool = False):
    """列出所有提示词"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    prompts = PromptManager.list_prompts(category=category, include_inactive=include_inactive)
    return {"ok": True, "items": prompts}


@router.get('/admin/prompts/{prompt_id}')
async def get_prompt_detail(prompt_id: int, request: Request):
    """获取提示词详情"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
    from fastnpc.config import USE_POSTGRESQL
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        cur.execute(f"""
            SELECT id, category, sub_category, name, description, template_content,
                   version, is_active, created_by, created_at, updated_at, metadata
            FROM prompt_templates
            WHERE id = {placeholder}
        """, (prompt_id,))
        
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "未找到提示词"}, status_code=404)
        
        if USE_POSTGRESQL:
            prompt = _row_to_dict(row, cur)
        else:
            prompt = dict(row)
        
        # 解析metadata
        if prompt.get('metadata'):
            try:
                prompt['metadata'] = json.loads(prompt['metadata'])
            except:
                prompt['metadata'] = {}
        
        return {"ok": True, "prompt": prompt}
    
    finally:
        _return_conn(conn)


@router.post('/admin/prompts')
async def create_prompt(request: Request):
    """创建新提示词"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    user = _require_admin(request)
    user_id = user.get('uid') if user else None
    
    prompt_id = PromptManager.create_prompt(
        category=data.get('category'),
        sub_category=data.get('sub_category'),
        name=data.get('name'),
        description=data.get('description'),
        template_content=data.get('template_content'),
        version=data.get('version', '1.0.0'),
        is_active=data.get('is_active', False),
        created_by=user_id,
        metadata=data.get('metadata')
    )
    
    if prompt_id:
        return {"ok": True, "prompt_id": prompt_id}
    else:
        return JSONResponse({"error": "创建失败"}, status_code=500)


@router.put('/admin/prompts/{prompt_id}')
async def update_prompt(prompt_id: int, request: Request):
    """更新提示词"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    user = _require_admin(request)
    user_id = user.get('uid') if user else None
    
    success = PromptManager.update_prompt(
        prompt_id=prompt_id,
        template_content=data.get('template_content'),
        name=data.get('name'),
        description=data.get('description'),
        version=data.get('version'),
        metadata=data.get('metadata'),
        updated_by=user_id,
        create_history=data.get('create_history', True)
    )
    
    if success:
        return {"ok": True}
    else:
        return JSONResponse({"error": "更新失败"}, status_code=500)


@router.post('/admin/prompts/{prompt_id}/activate')
async def activate_prompt(prompt_id: int, request: Request):
    """激活提示词版本"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    user = _require_admin(request)
    user_id = user.get('uid') if user else None
    
    success = PromptManager.activate_version(prompt_id, updated_by=user_id)
    
    if success:
        return {"ok": True}
    else:
        return JSONResponse({"error": "激活失败"}, status_code=500)


@router.get('/admin/prompts/{prompt_id}/history')
async def get_prompt_history(prompt_id: int, request: Request, limit: int = 20):
    """获取版本历史"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    history = PromptManager.get_version_history(prompt_id, limit=limit)
    return {"ok": True, "history": history}


@router.post('/admin/prompts/{prompt_id}/duplicate')
async def duplicate_prompt(prompt_id: int, request: Request):
    """复制为新版本"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
        new_version = data.get('new_version', '2.0.0')
    except:
        new_version = '2.0.0'
    
    user = _require_admin(request)
    user_id = user.get('uid') if user else None
    
    new_id = PromptManager.duplicate_prompt(prompt_id, new_version, created_by=user_id)
    
    if new_id:
        return {"ok": True, "new_prompt_id": new_id}
    else:
        return JSONResponse({"error": "复制失败"}, status_code=500)


# ===== 测试用例相关 API =====

@router.get('/admin/prompts/test-cases')
async def list_test_cases(request: Request, category: Optional[str] = None):
    """列出测试用例"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
    from fastnpc.config import USE_POSTGRESQL
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        if category:
            query = f"""
                SELECT id, prompt_category, prompt_sub_category, name, description, created_at
                FROM prompt_test_cases
                WHERE prompt_category = {placeholder}
                ORDER BY created_at DESC
            """
            cur.execute(query, (category,))
        else:
            query = """
                SELECT id, prompt_category, prompt_sub_category, name, description, created_at
                FROM prompt_test_cases
                ORDER BY created_at DESC
            """
            cur.execute(query)
        
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            if USE_POSTGRESQL:
                results.append(_row_to_dict(row, cur))
            else:
                results.append(dict(row))
        
        return {"ok": True, "items": results}
    
    finally:
        _return_conn(conn)


@router.post('/admin/prompts/test-cases')
async def create_test_case(request: Request):
    """创建测试用例"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    from fastnpc.api.auth.db_utils import _get_conn, _return_conn
    from fastnpc.config import USE_POSTGRESQL
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        now = int(time.time())
        
        input_data_json = json.dumps(data.get('input_data', {}), ensure_ascii=False)
        evaluation_metrics_json = json.dumps(data.get('evaluation_metrics', {}), ensure_ascii=False)
        
        if USE_POSTGRESQL:
            query = """
                INSERT INTO prompt_test_cases 
                (prompt_category, prompt_sub_category, name, description, input_data, expected_output, evaluation_metrics, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            cur.execute(query, (
                data.get('prompt_category'),
                data.get('prompt_sub_category'),
                data.get('name'),
                data.get('description'),
                input_data_json,
                data.get('expected_output'),
                evaluation_metrics_json,
                now
            ))
            test_case_id = cur.fetchone()[0]
        else:
            query = """
                INSERT INTO prompt_test_cases 
                (prompt_category, prompt_sub_category, name, description, input_data, expected_output, evaluation_metrics, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cur.execute(query, (
                data.get('prompt_category'),
                data.get('prompt_sub_category'),
                data.get('name'),
                data.get('description'),
                input_data_json,
                data.get('expected_output'),
                evaluation_metrics_json,
                now
            ))
            test_case_id = cur.lastrowid
        
        conn.commit()
        
        return {"ok": True, "test_case_id": test_case_id}
    
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 创建测试用例失败: {e}")
        return JSONResponse({"error": f"创建失败: {str(e)}"}, status_code=500)
    finally:
        _return_conn(conn)


@router.post('/admin/prompts/{prompt_id}/test')
async def run_test(prompt_id: int, request: Request):
    """运行测试"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
        test_case_id = data.get('test_case_id')
    except:
        test_case_id = None
    
    if test_case_id:
        # 运行单个测试用例
        result = await PromptEvaluator.run_test_case(prompt_id, test_case_id)
        return {"ok": True, "result": result}
    else:
        # 运行所有相关测试用例
        results = await PromptEvaluator.batch_test(prompt_id)
        return {"ok": True, "results": results}


@router.get('/admin/prompts/{prompt_id}/evaluations')
async def get_evaluations(prompt_id: int, request: Request, limit: int = 50):
    """获取评估记录"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
    from fastnpc.config import USE_POSTGRESQL
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"""
            SELECT e.id, e.test_case_id, e.output_content, e.auto_metrics, 
                   e.manual_score, e.manual_feedback, e.evaluator_id, e.created_at,
                   t.name as test_case_name
            FROM prompt_evaluations e
            LEFT JOIN prompt_test_cases t ON e.test_case_id = t.id
            WHERE e.prompt_template_id = {placeholder}
            ORDER BY e.created_at DESC
            LIMIT {limit}
        """
        
        cur.execute(query, (prompt_id,))
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            if USE_POSTGRESQL:
                eval_data = _row_to_dict(row, cur)
            else:
                eval_data = dict(row)
            
            # 解析JSON字段
            if eval_data.get('auto_metrics'):
                try:
                    eval_data['auto_metrics'] = json.loads(eval_data['auto_metrics'])
                except:
                    eval_data['auto_metrics'] = {}
            
            results.append(eval_data)
        
        return {"ok": True, "evaluations": results}
    
    finally:
        _return_conn(conn)


@router.post('/admin/prompts/evaluations/{eval_id}/score')
async def manual_score(eval_id: int, request: Request):
    """人工打分"""
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
        manual_score = data.get('manual_score')
        manual_feedback = data.get('manual_feedback', '')
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    if not isinstance(manual_score, int) or manual_score < 1 or manual_score > 5:
        return JSONResponse({"error": "评分必须是1-5之间的整数"}, status_code=400)
    
    user = _require_admin(request)
    user_id = user.get('uid') if user else None
    
    from fastnpc.api.auth.db_utils import _get_conn, _return_conn
    from fastnpc.config import USE_POSTGRESQL
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"""
            UPDATE prompt_evaluations
            SET manual_score = {placeholder}, manual_feedback = {placeholder}, evaluator_id = {placeholder}
            WHERE id = {placeholder}
        """
        
        cur.execute(query, (manual_score, manual_feedback, user_id, eval_id))
        conn.commit()
        
        return {"ok": True}
    
    except Exception as e:
        conn.rollback()
        return JSONResponse({"error": f"打分失败: {str(e)}"}, status_code=500)
    finally:
        _return_conn(conn)


@router.get("/admin/prompts/{id}/versions")
async def get_prompt_versions(id: int, request: Request):
    """
    获取某个提示词的所有版本列表（包括激活状态和评估结果）
    
    返回同category、同sub_category的所有版本，按创建时间倒序
    每个版本包含：
    - 基本信息（id, version, is_active, created_at等）
    - 评估结果统计（测试次数、通过率、最后测试时间）
    """
    if not _require_admin(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 1. 获取当前提示词的category和sub_category
        cur.execute("""
            SELECT category, sub_category 
            FROM prompt_templates 
            WHERE id = %s
        """ if USE_POSTGRESQL else """
            SELECT category, sub_category 
            FROM prompt_templates 
            WHERE id = ?
        """, (id,))
        
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "提示词不存在"}, status_code=404)
        
        if USE_POSTGRESQL:
            data = _row_to_dict(row, cur)
            category = data['category']
            sub_category = data.get('sub_category')
        else:
            category = row[0]
            sub_category = row[1]
        
        # 2. 查询所有同类别的版本，并关联评估结果
        if USE_POSTGRESQL:
            # PostgreSQL版本 - 使用JSONB操作
            query = """
                SELECT 
                    pt.id,
                    pt.category,
                    pt.sub_category,
                    pt.name,
                    pt.description,
                    pt.template_content,
                    pt.version,
                    pt.is_active,
                    pt.created_at,
                    pt.updated_at,
                    pt.metadata,
                    COUNT(pe.id) as test_count,
                    COUNT(CASE 
                        WHEN pe.auto_metrics IS NOT NULL 
                        AND pe.auto_metrics::jsonb->>'overall_passed' = 'true'
                        THEN 1 
                    END)::float / NULLIF(COUNT(pe.id), 0) as pass_rate,
                    MAX(pe.created_at) as last_test_time
                FROM prompt_templates pt
                LEFT JOIN prompt_evaluations pe ON pt.id = pe.prompt_template_id
                WHERE pt.category = %s 
                    AND (pt.sub_category = %s OR (pt.sub_category IS NULL AND %s IS NULL))
                GROUP BY pt.id
                ORDER BY pt.created_at DESC
            """
            cur.execute(query, (category, sub_category, sub_category))
        else:
            # SQLite版本 - 简化处理
            query = """
                SELECT 
                    pt.id,
                    pt.category,
                    pt.sub_category,
                    pt.name,
                    pt.description,
                    pt.template_content,
                    pt.version,
                    pt.is_active,
                    pt.created_at,
                    pt.updated_at,
                    pt.metadata,
                    COUNT(pe.id) as test_count,
                    CAST(SUM(CASE 
                        WHEN json_extract(pe.auto_metrics, '$.overall_passed') = 1 
                        THEN 1 
                        ELSE 0 
                    END) AS FLOAT) / NULLIF(COUNT(pe.id), 0) as pass_rate,
                    MAX(pe.created_at) as last_test_time
                FROM prompt_templates pt
                LEFT JOIN prompt_evaluations pe ON pt.id = pe.prompt_template_id
                WHERE pt.category = ? 
                    AND (pt.sub_category = ? OR (pt.sub_category IS NULL AND ? IS NULL))
                GROUP BY pt.id
                ORDER BY pt.created_at DESC
            """
            cur.execute(query, (category, sub_category, sub_category))
        
        # 3. 构建返回结果
        versions = []
        for row in cur.fetchall():
            if USE_POSTGRESQL:
                version_data = _row_to_dict(row, cur)
            else:
                version_data = dict(row)
            
            # 处理pass_rate（可能为None）
            pass_rate = version_data.get('pass_rate')
            if pass_rate is None:
                pass_rate = 0.0
            
            # 构建版本信息
            version_info = {
                "id": version_data['id'],
                "category": version_data['category'],
                "sub_category": version_data.get('sub_category'),
                "name": version_data['name'],
                "description": version_data.get('description'),
                "template_content": version_data['template_content'],
                "version": version_data['version'],
                "is_active": version_data['is_active'],
                "created_at": version_data['created_at'],
                "updated_at": version_data.get('updated_at'),
                "test_count": version_data.get('test_count', 0),
                "pass_rate": round(pass_rate, 4) if pass_rate else 0.0,
                "last_test_time": version_data.get('last_test_time')
            }
            
            versions.append(version_info)
        
        return {"items": versions, "total": len(versions)}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"获取版本列表失败: {str(e)}"}, status_code=500)
    finally:
        _return_conn(conn)

