# -*- coding: utf-8 -*-
"""
提示词测试评估引擎
提供自动化测试和指标计算功能
"""
from __future__ import annotations

import json
import time
import re
from typing import Dict, Any, List, Optional

from fastnpc.prompt_manager import PromptManager
from fastnpc.llm.openrouter import get_openrouter_completion_async
from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
from fastnpc.config import USE_POSTGRESQL


class PromptEvaluator:
    """提示词评估器"""
    
    @staticmethod
    async def run_test_case(prompt_id: int, test_case_id: int) -> Dict[str, Any]:
        """运行单个测试用例
        
        Args:
            prompt_id: 提示词ID
            test_case_id: 测试用例ID
        
        Returns:
            评估结果字典
        """
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            # 获取提示词
            cur.execute(f"""
                SELECT id, template_content, category, sub_category, metadata
                FROM prompt_templates
                WHERE id = {placeholder}
            """, (prompt_id,))
            
            prompt_row = cur.fetchone()
            if not prompt_row:
                return {"error": "提示词不存在"}
            
            if USE_POSTGRESQL:
                prompt_data = _row_to_dict(prompt_row, cur)
            else:
                prompt_data = dict(prompt_row)
            
            # 获取测试用例
            cur.execute(f"""
                SELECT id, name, input_data, expected_output, evaluation_metrics
                FROM prompt_test_cases
                WHERE id = {placeholder}
            """, (test_case_id,))
            
            test_row = cur.fetchone()
            if not test_row:
                return {"error": "测试用例不存在"}
            
            if USE_POSTGRESQL:
                test_data = _row_to_dict(test_row, cur)
            else:
                test_data = dict(test_row)
            
            # 解析输入数据和评估指标
            try:
                input_data = json.loads(test_data['input_data'])
                evaluation_metrics = json.loads(test_data.get('evaluation_metrics') or '{}')
            except:
                return {"error": "测试用例数据格式错误"}
            
            # 渲染提示词
            try:
                rendered_prompt = PromptManager.render_prompt(
                    prompt_data['template_content'],
                    input_data
                )
            except Exception as e:
                return {"error": f"渲染提示词失败: {str(e)}"}
            
            # 调用LLM
            try:
                messages = [{"role": "user", "content": rendered_prompt}]
                
                # 如果是结构化生成类别，添加系统消息
                if prompt_data['category'] == 'STRUCTURED_GENERATION':
                    system_prompt = PromptManager.get_active_prompt('STRUCTURED_SYSTEM_MESSAGE')
                    if system_prompt:
                        messages.insert(0, {"role": "system", "content": system_prompt['template_content']})
                
                output = await get_openrouter_completion_async(messages)
                output_content = str(output or "")
            except Exception as e:
                return {"error": f"LLM调用失败: {str(e)}"}
            
            # 计算自动化指标
            auto_metrics = PromptEvaluator.calculate_auto_metrics(
                output_content,
                evaluation_metrics
            )
            
            # 保存评估记录
            now = int(time.time())
            auto_metrics_json = json.dumps(auto_metrics, ensure_ascii=False)
            
            if USE_POSTGRESQL:
                query = """
                    INSERT INTO prompt_evaluations
                    (prompt_template_id, test_case_id, output_content, auto_metrics, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """
                cur.execute(query, (prompt_id, test_case_id, output_content, auto_metrics_json, now))
                eval_id = cur.fetchone()[0]
            else:
                query = """
                    INSERT INTO prompt_evaluations
                    (prompt_template_id, test_case_id, output_content, auto_metrics, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """
                cur.execute(query, (prompt_id, test_case_id, output_content, auto_metrics_json, now))
                eval_id = cur.lastrowid
            
            conn.commit()
            
            return {
                "evaluation_id": eval_id,
                "test_case_name": test_data['name'],
                "output_content": output_content,
                "auto_metrics": auto_metrics,
                "expected_output": test_data.get('expected_output'),
                "passed": auto_metrics.get('overall_passed', False)
            }
        
        except Exception as e:
            print(f"[ERROR] 运行测试失败: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"运行测试失败: {str(e)}"}
        finally:
            _return_conn(conn)
    
    @staticmethod
    async def batch_test(prompt_id: int) -> List[Dict[str, Any]]:
        """批量测试（运行所有相关测试用例）"""
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            # 获取提示词的类别
            cur.execute(f"""
                SELECT category, sub_category
                FROM prompt_templates
                WHERE id = {placeholder}
            """, (prompt_id,))
            
            row = cur.fetchone()
            if not row:
                return [{"error": "提示词不存在"}]
            
            if USE_POSTGRESQL:
                data = _row_to_dict(row, cur)
            else:
                data = dict(row)
            
            category = data['category']
            sub_category = data.get('sub_category')
            
            # 获取相关测试用例
            if sub_category:
                query = f"""
                    SELECT id
                    FROM prompt_test_cases
                    WHERE prompt_category = {placeholder} AND prompt_sub_category = {placeholder}
                """
                cur.execute(query, (category, sub_category))
            else:
                query = f"""
                    SELECT id
                    FROM prompt_test_cases
                    WHERE prompt_category = {placeholder}
                """
                cur.execute(query, (category,))
            
            test_case_ids = [row[0] for row in cur.fetchall()]
            
            if not test_case_ids:
                return [{"info": "没有找到相关测试用例"}]
            
            # 运行所有测试用例
            results = []
            for test_case_id in test_case_ids:
                result = await PromptEvaluator.run_test_case(prompt_id, test_case_id)
                results.append(result)
            
            return results
        
        finally:
            _return_conn(conn)
    
    @staticmethod
    def calculate_auto_metrics(output: str, metrics_config: Dict[str, Any]) -> Dict[str, Any]:
        """计算自动化指标
        
        Args:
            output: LLM输出内容
            metrics_config: 评估指标配置
        
        Returns:
            指标结果字典
        """
        metrics = {}
        passed_checks = []
        failed_checks = []
        
        # 1. JSON格式检查
        if metrics_config.get('json_valid', False):
            try:
                # 尝试清理可能的markdown标记
                cleaned = output.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:].strip()
                elif cleaned.startswith('```'):
                    cleaned = cleaned[3:].strip()
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3].strip()
                
                parsed = json.loads(cleaned)
                metrics['json_valid'] = True
                passed_checks.append("JSON格式正确")
                
                # 检查必需字段
                required_fields = metrics_config.get('fields_complete', [])
                if required_fields:
                    missing_fields = [f for f in required_fields if f not in parsed]
                    if missing_fields:
                        metrics['fields_complete'] = False
                        failed_checks.append(f"缺少字段: {', '.join(missing_fields)}")
                    else:
                        metrics['fields_complete'] = True
                        passed_checks.append("所有必需字段完整")
            
            except json.JSONDecodeError as e:
                metrics['json_valid'] = False
                failed_checks.append(f"JSON解析失败: {str(e)}")
        
        # 2. 长度检查
        output_length_range = metrics_config.get('output_length')
        if output_length_range and isinstance(output_length_range, list) and len(output_length_range) == 2:
            min_len, max_len = output_length_range
            actual_len = len(output)
            metrics['output_length'] = actual_len
            
            if min_len <= actual_len <= max_len:
                metrics['length_ok'] = True
                passed_checks.append(f"长度符合要求 ({actual_len} 字符)")
            else:
                metrics['length_ok'] = False
                failed_checks.append(f"长度不符 ({actual_len} vs {min_len}-{max_len})")
        
        # 3. 第一人称检查
        if metrics_config.get('first_person_check', False):
            # 检查是否包含第一人称代词
            first_person_patterns = ['我', '我的', '我们', '咱们']
            has_first_person = any(p in output for p in first_person_patterns)
            
            # 检查是否不包含第三人称叙述
            third_person_patterns = ['他是', '她是', '这个角色', '该角色']
            has_third_person = any(p in output for p in third_person_patterns)
            
            if has_first_person and not has_third_person:
                metrics['first_person_ok'] = True
                passed_checks.append("使用第一人称")
            else:
                metrics['first_person_ok'] = False
                failed_checks.append("未正确使用第一人称")
        
        # 4. 不输出JSON检查
        if metrics_config.get('no_json_output', False):
            # 检查输出是否不包含JSON结构
            has_json_markers = '{' in output or '[' in output or '"' in output[:50]
            if not has_json_markers:
                metrics['no_json_ok'] = True
                passed_checks.append("未输出JSON结构")
            else:
                metrics['no_json_ok'] = False
                failed_checks.append("输出包含JSON结构")
        
        # 5. 关键词覆盖检查
        required_keywords = metrics_config.get('keywords', [])
        if required_keywords:
            found_keywords = [kw for kw in required_keywords if kw in output]
            missing_keywords = [kw for kw in required_keywords if kw not in output]
            
            metrics['keywords_found'] = len(found_keywords)
            metrics['keywords_total'] = len(required_keywords)
            
            if not missing_keywords:
                metrics['keywords_ok'] = True
                passed_checks.append("所有关键词覆盖")
            else:
                metrics['keywords_ok'] = False
                failed_checks.append(f"缺少关键词: {', '.join(missing_keywords)}")
        
        # 总体评价
        total_checks = len(passed_checks) + len(failed_checks)
        if total_checks > 0:
            metrics['pass_rate'] = len(passed_checks) / total_checks
            metrics['overall_passed'] = len(failed_checks) == 0
        else:
            metrics['pass_rate'] = 1.0
            metrics['overall_passed'] = True
        
        metrics['passed_checks'] = passed_checks
        metrics['failed_checks'] = failed_checks
        
        return metrics

