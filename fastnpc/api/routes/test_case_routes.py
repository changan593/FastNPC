# -*- coding: utf-8 -*-
"""
测试用例管理路由模块
提供测试用例的CRUD、执行、状态重置、报告生成等功能
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastnpc.config import USE_POSTGRESQL, BASE_DIR
from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
from fastnpc.api.utils import _require_admin
from fastnpc.api.cache import get_redis_cache
from fastnpc.prompt_manager import PromptManager


router = APIRouter()


@router.get('/admin/test-cases')
async def list_test_cases(
    request: Request,
    category: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    include_inactive: bool = False
):
    """列出测试用例（支持筛选）"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        conditions = []
        params = []
        
        if category:
            conditions.append(f"category = {placeholder}")
            params.append(category)
        
        if target_type:
            conditions.append(f"target_type = {placeholder}")
            params.append(target_type)
        
        if target_id:
            conditions.append(f"target_id = {placeholder}")
            params.append(target_id)
        
        if not include_inactive:
            conditions.append(f"is_active = {placeholder}")
            params.append(True if USE_POSTGRESQL else 1)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT id, version, category, target_type, target_id, name, description,
                   test_content, expected_behavior, test_config,
                   is_active, created_by, created_at, updated_at
            FROM test_cases
            WHERE {where_clause}
            ORDER BY category, target_id, version DESC
        """
        
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            if USE_POSTGRESQL:
                item = _row_to_dict(row, cur)
            else:
                item = dict(row)
                # SQLite: 解析JSON字段
                if item.get('test_content'):
                    try:
                        item['test_content'] = json.loads(item['test_content'])
                    except:
                        pass
                if item.get('test_config'):
                    try:
                        item['test_config'] = json.loads(item['test_config'])
                    except:
                        pass
            
            results.append(item)
        
        return {"ok": True, "items": results}
    
    except Exception as e:
        print(f"[ERROR] 列出测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"查询失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.post('/admin/test-cases')
async def create_test_case(request: Request):
    """创建测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 准备数据
        test_content = data.get('test_content')
        test_config = data.get('test_config')
        
        if USE_POSTGRESQL:
            test_content_str = json.dumps(test_content) if test_content else '{}'
            test_config_str = json.dumps(test_config) if test_config else None
        else:
            test_content_str = json.dumps(test_content, ensure_ascii=False) if test_content else '{}'
            test_config_str = json.dumps(test_config, ensure_ascii=False) if test_config else None
        
        query = f"""
            INSERT INTO test_cases (
                version, category, target_type, target_id, name, description,
                test_content, expected_behavior, test_config,
                is_active, created_by
            ) VALUES (
                {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}
            )
        """
        
        if USE_POSTGRESQL:
            query += " RETURNING id"
        
        params = (
            data.get('version', '1.0.0'),
            data.get('category'),
            data.get('target_type'),
            data.get('target_id'),
            data.get('name'),
            data.get('description'),
            test_content_str,
            data.get('expected_behavior'),
            test_config_str,
            data.get('is_active', True),
            user.get('uid')
        )
        
        cur.execute(query, params)
        
        if USE_POSTGRESQL:
            new_id = cur.fetchone()[0]
        else:
            new_id = cur.lastrowid
        
        conn.commit()
        
        print(f"[INFO] 创建测试用例成功: ID={new_id}")
        
        return {"ok": True, "test_case_id": new_id}
    
    except Exception as e:
        print(f"[ERROR] 创建测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"创建失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.get('/admin/test-cases/{id}')
async def get_test_case_detail(id: int, request: Request):
    """获取测试用例详情"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"""
            SELECT id, version, category, target_type, target_id, name, description,
                   test_content, expected_behavior, test_config,
                   is_active, created_by, created_at, updated_at
            FROM test_cases
            WHERE id = {placeholder}
        """
        
        cur.execute(query, (id,))
        row = cur.fetchone()
        
        if not row:
            return JSONResponse({"error": "测试用例不存在"}, status_code=404)
        
        if USE_POSTGRESQL:
            test_case = _row_to_dict(row, cur)
        else:
            test_case = dict(row)
            # SQLite: 解析JSON字段
            if test_case.get('test_content'):
                try:
                    test_case['test_content'] = json.loads(test_case['test_content'])
                except:
                    pass
            if test_case.get('test_config'):
                try:
                    test_case['test_config'] = json.loads(test_case['test_config'])
                except:
                    pass
        
        return {"ok": True, "test_case": test_case}
    
    except Exception as e:
        print(f"[ERROR] 获取测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"查询失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.put('/admin/test-cases/{id}')
async def update_test_case(id: int, request: Request):
    """更新测试用例（创建新版本）"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 检查原测试用例是否存在
        cur.execute(f"SELECT * FROM test_cases WHERE id = {placeholder}", (id,))
        if not cur.fetchone():
            return JSONResponse({"error": "测试用例不存在"}, status_code=404)
        
        # 如果创建新版本
        create_new_version = data.get('create_new_version', False)
        
        if create_new_version:
            # 先停用同category/target的其他测试用例
            cur.execute(f"""
                UPDATE test_cases 
                SET is_active = {placeholder}
                WHERE category = {placeholder} 
                  AND target_type = {placeholder} 
                  AND target_id = {placeholder}
            """, (False if USE_POSTGRESQL else 0, data.get('category'), 
                  data.get('target_type'), data.get('target_id')))
            
            # 创建新版本
            test_content = data.get('test_content')
            test_config = data.get('test_config')
            
            if USE_POSTGRESQL:
                test_content_str = json.dumps(test_content) if test_content else '{}'
                test_config_str = json.dumps(test_config) if test_config else None
            else:
                test_content_str = json.dumps(test_content, ensure_ascii=False) if test_content else '{}'
                test_config_str = json.dumps(test_config, ensure_ascii=False) if test_config else None
            
            insert_query = f"""
                INSERT INTO test_cases (
                    version, category, target_type, target_id, name, description,
                    test_content, expected_behavior, test_config,
                    is_active, created_by
                ) VALUES (
                    {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                    {placeholder}, {placeholder}, {placeholder},
                    {placeholder}, {placeholder}
                )
            """
            
            if USE_POSTGRESQL:
                insert_query += " RETURNING id"
            
            params = (
                data.get('version'),
                data.get('category'),
                data.get('target_type'),
                data.get('target_id'),
                data.get('name'),
                data.get('description'),
                test_content_str,
                data.get('expected_behavior'),
                test_config_str,
                True,
                user.get('uid')
            )
            
            cur.execute(insert_query, params)
            
            if USE_POSTGRESQL:
                new_id = cur.fetchone()[0]
            else:
                new_id = cur.lastrowid
            
            conn.commit()
            return {"ok": True, "test_case_id": new_id, "message": "已创建新版本"}
        
        else:
            # 直接更新现有测试用例
            test_content = data.get('test_content')
            test_config = data.get('test_config')
            
            if USE_POSTGRESQL:
                test_content_str = json.dumps(test_content) if test_content else None
                test_config_str = json.dumps(test_config) if test_config else None
            else:
                test_content_str = json.dumps(test_content, ensure_ascii=False) if test_content else None
                test_config_str = json.dumps(test_config, ensure_ascii=False) if test_config else None
            
            update_fields = []
            update_params = []
            
            if 'name' in data:
                update_fields.append(f"name = {placeholder}")
                update_params.append(data['name'])
            
            if 'description' in data:
                update_fields.append(f"description = {placeholder}")
                update_params.append(data['description'])
            
            if test_content_str is not None:
                update_fields.append(f"test_content = {placeholder}")
                update_params.append(test_content_str)
            
            if 'expected_behavior' in data:
                update_fields.append(f"expected_behavior = {placeholder}")
                update_params.append(data['expected_behavior'])
            
            if test_config_str is not None:
                update_fields.append(f"test_config = {placeholder}")
                update_params.append(test_config_str)
            
            if not update_fields:
                return {"ok": True, "message": "无需更新"}
            
            update_fields.append(f"updated_at = {placeholder}")
            update_params.append(datetime.now())
            
            update_params.append(id)
            
            update_query = f"""
                UPDATE test_cases 
                SET {', '.join(update_fields)}
                WHERE id = {placeholder}
            """
            
            cur.execute(update_query, tuple(update_params))
            conn.commit()
            
            return {"ok": True, "message": "更新成功"}
    
    except Exception as e:
        print(f"[ERROR] 更新测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"更新失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.delete('/admin/test-cases/{id}')
async def delete_test_case(id: int, request: Request):
    """删除测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 检查测试用例是否存在
        cur.execute(f"SELECT * FROM test_cases WHERE id = {placeholder}", (id,))
        test_case = cur.fetchone()
        if not test_case:
            return JSONResponse({"error": "测试用例不存在"}, status_code=404)
        
        # 删除相关的测试执行记录
        cur.execute(f"DELETE FROM test_executions WHERE test_case_id = {placeholder}", (id,))
        
        # 删除测试用例
        cur.execute(f"DELETE FROM test_cases WHERE id = {placeholder}", (id,))
        
        conn.commit()
        return {"ok": True, "message": "删除成功"}
    
    except Exception as e:
        print(f"[ERROR] 删除测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"删除失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.post('/admin/test-cases/{id}/activate')
async def activate_test_case(id: int, request: Request):
    """激活测试用例版本"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 获取测试用例信息
        cur.execute(f"""
            SELECT category, target_type, target_id 
            FROM test_cases 
            WHERE id = {placeholder}
        """, (id,))
        
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "测试用例不存在"}, status_code=404)
        
        if USE_POSTGRESQL:
            info = _row_to_dict(row, cur)
        else:
            info = dict(row)
        
        # 停用同category/target的其他测试用例
        cur.execute(f"""
            UPDATE test_cases 
            SET is_active = {placeholder}
            WHERE category = {placeholder} 
              AND target_type = {placeholder} 
              AND target_id = {placeholder}
        """, (False if USE_POSTGRESQL else 0, info['category'], 
              info['target_type'], info['target_id']))
        
        # 激活当前测试用例
        cur.execute(f"""
            UPDATE test_cases 
            SET is_active = {placeholder}
            WHERE id = {placeholder}
        """, (True if USE_POSTGRESQL else 1, id))
        
        conn.commit()
        
        print(f"[INFO] 激活测试用例: ID={id}")
        
        return {"ok": True, "message": "激活成功"}
    
    except Exception as e:
        print(f"[ERROR] 激活测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"激活失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.get('/admin/test-cases/versions')
async def get_test_case_versions(
    request: Request,
    category: str,
    target_type: str,
    target_id: str
):
    """获取某个测试目标的所有版本"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"""
            SELECT id, version, name, description, is_active, created_at, updated_at
            FROM test_cases
            WHERE category = {placeholder} 
              AND target_type = {placeholder} 
              AND target_id = {placeholder}
            ORDER BY created_at DESC
        """
        
        cur.execute(query, (category, target_type, target_id))
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            if USE_POSTGRESQL:
                results.append(_row_to_dict(row, cur))
            else:
                results.append(dict(row))
        
        return {"ok": True, "versions": results}
    
    except Exception as e:
        print(f"[ERROR] 获取版本历史失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"查询失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.post('/admin/test-cases/reset-character/{persona_id}')
async def reset_character_state(persona_id: str, request: Request):
    """重置角色状态：清空对话历史和记忆"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        from fastnpc.api.auth import get_character_id, save_character_memories
        
        # 获取角色ID
        char_id = get_character_id(user.get('uid'), persona_id)
        if not char_id:
            return JSONResponse({"error": "角色不存在"}, status_code=404)
        
        reset_count = 0
        
        # 1. 删除数据库中的对话消息
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        cur.execute(f"DELETE FROM messages WHERE character_id = {placeholder}", (char_id,))
        deleted_msgs = cur.rowcount
        conn.commit()
        print(f"[INFO] 已删除角色 {persona_id} 的 {deleted_msgs} 条消息")
        reset_count += deleted_msgs
        
        # 2. 清空Redis中的短期记忆
        try:
            redis_cache = get_redis_cache()
            stm_key = f"stm:{char_id}"
            if redis_cache.exists(stm_key):
                redis_cache.delete(stm_key)
                print(f"[INFO] 已清空角色 {persona_id} 的Redis短期记忆")
                reset_count += 1
        except Exception as e:
            print(f"[WARN] 清空Redis失败: {e}")
        
        # 3. 清空数据库中的长期记忆
        save_character_memories(char_id, short_term=[], long_term=[])
        print(f"[INFO] 已清空角色 {persona_id} 的长期记忆")
        reset_count += 1
        
        return {
            "ok": True,
            "message": f"已重置角色状态（{reset_count}项操作完成）"
        }
    
    except Exception as e:
        print(f"[ERROR] 重置角色状态失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"重置失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.post('/admin/test-cases/reset-group/{group_id}')
async def reset_group_state(group_id: int, request: Request):
    """重置群聊状态：删除群聊消息和成员记忆"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 检查群聊是否存在
        cur.execute(f"SELECT id FROM groups WHERE id = {placeholder}", (group_id,))
        if not cur.fetchone():
            return JSONResponse({"error": "群聊不存在"}, status_code=404)
        
        reset_count = 0
        
        # 1. 删除群聊消息
        cur.execute(f"DELETE FROM group_messages WHERE group_id = {placeholder}", (group_id,))
        deleted_msgs = cur.rowcount
        reset_count += deleted_msgs
        print(f"[INFO] 已删除群聊 {group_id} 的 {deleted_msgs} 条消息")
        
        # 2. 清空群聊成员的Redis记忆（如果需要的话）
        # TODO: 根据实际需求决定是否清空群聊成员的记忆
        
        conn.commit()
        
        return {
            "ok": True,
            "message": f"已重置群聊状态（删除了{deleted_msgs}条消息）"
        }
    
    except Exception as e:
        print(f"[ERROR] 重置群聊状态失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"重置失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.post('/admin/test-cases/{id}/execute')
async def execute_test_case(id: int, request: Request):
    """执行单个测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    # 暂时返回占位响应，实际执行逻辑将在阶段五实现
    return {
        "ok": True,
        "message": "测试执行功能将在阶段五实现",
        "test_case_id": id
    }


@router.post('/admin/test-cases/batch-execute')
async def batch_execute_tests(request: Request):
    """批量执行测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    executions = data.get('executions', [])
    if not executions:
        return JSONResponse({"error": "No executions provided"}, status_code=400)
    
    results = []
    
    for exec_config in executions:
        test_case_id = exec_config.get('test_case_id')
        prompt_template_id = exec_config.get('prompt_template_id')
        evaluator_prompt_id = exec_config.get('evaluator_prompt_id')
        
        try:
            # 获取测试用例
            test_case = _get_test_case(test_case_id)
            if not test_case:
                results.append({
                    "test_case_id": test_case_id,
                    "success": False,
                    "error": "Test case not found"
                })
                continue
            
            # 执行测试
            start_time = time.time()
            llm_response = await _execute_test_logic_mock(test_case, prompt_template_id)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 评估结果
            evaluation_result, evaluation_feedback = await _evaluate_result_mock(
                test_case, llm_response, evaluator_prompt_id
            )
            
            # 保存执行记录
            execution_id = _save_execution_record(
                test_case_id=test_case_id,
                prompt_template_id=prompt_template_id,
                evaluator_prompt_id=evaluator_prompt_id,
                duration_ms=duration_ms,
                llm_response=llm_response,
                evaluation_result=evaluation_result,
                evaluation_feedback=evaluation_feedback,
                executed_by=user['uid']
            )
            
            # 计算分数
            score = evaluation_result.get('score') or evaluation_result.get('总分') if evaluation_result else None
            
            results.append({
                "test_case_id": test_case_id,
                "success": True,
                "execution_id": execution_id,
                "duration_ms": duration_ms,
                "evaluation_result": evaluation_result,
                "evaluation_feedback": evaluation_feedback,
                "score": score,
                "execution_time": int(time.time())
            })
            
        except Exception as e:
            print(f"[ERROR] 执行测试用例 {test_case_id} 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_case_id": test_case_id,
                "success": False,
                "error": str(e)
            })
    
    return {
        "ok": True,
        "results": results,
        "total": len(executions),
        "succeeded": sum(1 for r in results if r.get('success')),
        "failed": sum(1 for r in results if not r.get('success'))
    }


@router.get('/admin/test-reports')
async def get_test_reports(
    request: Request,
    test_case_id: Optional[int] = None,
    prompt_template_id: Optional[int] = None,
    limit: int = 100
):
    """获取测试报告"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        conditions = []
        params = []
        
        if test_case_id:
            conditions.append(f"test_case_id = {placeholder}")
            params.append(test_case_id)
        
        if prompt_template_id:
            conditions.append(f"prompt_template_id = {placeholder}")
            params.append(prompt_template_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        params.append(limit)
        
        query = f"""
            SELECT id, test_case_id, prompt_template_id,
                   execution_time, duration_ms,
                   llm_response, evaluation_result, passed, score,
                   evaluator_prompt_id, evaluation_feedback,
                   metadata, executed_by
            FROM test_executions
            WHERE {where_clause}
            ORDER BY execution_time DESC
            LIMIT {placeholder}
        """
        
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            if USE_POSTGRESQL:
                item = _row_to_dict(row, cur)
            else:
                item = dict(row)
                # SQLite: 解析JSON字段
                if item.get('evaluation_result'):
                    try:
                        item['evaluation_result'] = json.loads(item['evaluation_result'])
                    except:
                        pass
                if item.get('metadata'):
                    try:
                        item['metadata'] = json.loads(item['metadata'])
                    except:
                        pass
            
            results.append(item)
        
        # 计算统计信息
        total = len(results)
        passed = sum(1 for r in results if r.get('passed'))
        pass_rate = (passed / total * 100) if total > 0 else 0
        avg_score = sum(r.get('score', 0) for r in results) / total if total > 0 else 0
        
        return {
            "ok": True,
            "executions": results,
            "statistics": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": round(pass_rate, 2),
                "average_score": round(avg_score, 2)
            }
        }
    
    except Exception as e:
        print(f"[ERROR] 获取测试报告失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"查询失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)


@router.post('/admin/characters/{character_id}/mark-test-case')
async def mark_character_test_case(character_id: int, request: Request, is_test_case: bool):
    """标记/取消标记角色为测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    from fastnpc.api.auth import mark_character_as_test_case
    
    success, message = mark_character_as_test_case(user.get('uid'), character_id, is_test_case)
    
    if success:
        return {"ok": True, "message": message}
    else:
        return JSONResponse({"error": message}, status_code=400)


@router.post('/admin/groups/{group_id}/mark-test-case')
async def mark_group_test_case(group_id: int, request: Request, is_test_case: bool):
    """标记/取消标记群聊为测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    from fastnpc.api.auth import mark_group_as_test_case
    
    success, message = mark_group_as_test_case(user.get('uid'), group_id, is_test_case)
    
    if success:
        return {"ok": True, "message": message}
    else:
        return JSONResponse({"error": message}, status_code=400)


# ========== 测试执行辅助函数 ==========

def _get_test_case(test_case_id: int):
    """获取测试用例详情"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"SELECT * FROM test_cases WHERE id = {placeholder}"
        cur.execute(query, (test_case_id,))
        row = cur.fetchone()
        
        if not row:
            return None
        
        if USE_POSTGRESQL:
            return _row_to_dict(row, cur)
        else:
            return dict(row)
    finally:
        _return_conn(conn)


def _get_prompt_by_id(prompt_id: int):
    """获取提示词详情"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"SELECT * FROM prompt_templates WHERE id = {placeholder}"
        cur.execute(query, (prompt_id,))
        row = cur.fetchone()
        
        if not row:
            return None
        
        if USE_POSTGRESQL:
            return _row_to_dict(row, cur)
        else:
            return dict(row)
    finally:
        _return_conn(conn)


async def _execute_test_logic_mock(test_case, prompt_template_id):
    """模拟执行测试逻辑（基础版本）
    
    TODO: 实际实现需要根据test_case的target_type和category调用相应的功能
    - character + SINGLE_CHAT: 调用单聊API
    - group + GROUP_CHAT: 调用群聊API
    - STRUCTURED_GEN: 调用结构化生成
    - BRIEF_GEN: 调用简介生成
    等等
    """
    # 模拟LLM响应
    test_content = test_case.get('test_content', {})
    category = test_case.get('category', '')
    
    mock_response = f"[模拟响应] 测试类别: {category}\n"
    mock_response += f"测试内容: {json.dumps(test_content, ensure_ascii=False)}\n"
    mock_response += "此为测试执行的模拟响应。完整实现将调用实际的角色对话、结构化生成等功能。"
    
    return mock_response


async def _evaluate_result_mock(test_case, llm_response, evaluator_prompt_id):
    """模拟评估结果（基础版本）
    
    TODO: 实际实现需要调用LLM API使用评估器提示词进行评估
    """
    # 获取评估器提示词
    evaluator = _get_prompt_by_id(evaluator_prompt_id) if evaluator_prompt_id else None
    
    if not evaluator:
        evaluator_name = "默认评估器"
    else:
        evaluator_name = evaluator.get('name', '评估器')
    
    # 模拟评估结果
    evaluation_result = {
        "score": 85,
        "总分": 85,
        "优点": [
            "响应内容与测试预期基本一致",
            "格式规范，表达清晰"
        ],
        "缺点": [
            "部分细节可以更完善"
        ],
        "建议": [
            "可以增加更多上下文信息",
            "建议优化回复的连贯性"
        ],
        "详细评分": {
            "准确性": 90,
            "完整性": 85,
            "流畅性": 80
        }
    }
    
    evaluation_feedback = f"""【评估报告】

使用评估器: {evaluator_name}

总分: 85/100

✅ 优点:
• 响应内容与测试预期基本一致
• 格式规范，表达清晰

⚠️ 缺点:
• 部分细节可以更完善

💡 改进建议:
• 可以增加更多上下文信息
• 建议优化回复的连贯性

详细评分:
• 准确性: 90/100
• 完整性: 85/100
• 流畅性: 80/100

[注意: 此为模拟评估结果。完整实现将调用LLM进行实际评估]
"""
    
    return evaluation_result, evaluation_feedback


def _save_execution_record(test_case_id, prompt_template_id, evaluator_prompt_id,
                           duration_ms, llm_response, evaluation_result, evaluation_feedback,
                           executed_by):
    """保存测试执行记录"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        now = int(time.time())
        
        # 解析评分
        score = None
        passed = None
        if evaluation_result:
            score = evaluation_result.get('score') or evaluation_result.get('总分')
            if score is not None:
                passed = score >= 60  # 60分以上算通过
        
        # 序列化evaluation_result
        eval_result_json = json.dumps(evaluation_result, ensure_ascii=False) if evaluation_result else None
        
        if USE_POSTGRESQL:
            query = """
                INSERT INTO test_executions 
                (test_case_id, prompt_template_id, evaluator_prompt_id, 
                 execution_time, duration_ms, llm_response, evaluation_result, 
                 evaluation_feedback, passed, score, executed_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                RETURNING id
            """
            cur.execute(query, (
                test_case_id, prompt_template_id, evaluator_prompt_id,
                now, duration_ms, llm_response, eval_result_json,
                evaluation_feedback, passed, score, executed_by
            ))
            execution_id = cur.fetchone()[0]
        else:
            query = """
                INSERT INTO test_executions 
                (test_case_id, prompt_template_id, evaluator_prompt_id,
                 execution_time, duration_ms, llm_response, evaluation_result,
                 evaluation_feedback, passed, score, executed_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cur.execute(query, (
                test_case_id, prompt_template_id, evaluator_prompt_id,
                now, duration_ms, llm_response, eval_result_json,
                evaluation_feedback, passed, score, executed_by
            ))
            execution_id = cur.lastrowid
        
        conn.commit()
        return execution_id
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 保存执行记录失败: {e}")
        raise
    finally:
        _return_conn(conn)

