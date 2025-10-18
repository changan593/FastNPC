# -*- coding: utf-8 -*-
"""
提示词管理器核心模块
提供提示词的CRUD、版本管理、缓存等功能
"""
from __future__ import annotations

import json
import time
from typing import Dict, Any, List, Optional

from fastnpc.config import USE_DB_PROMPTS, USE_POSTGRESQL
from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
from fastnpc.api.cache import get_redis_cache


# 提示词类别常量
class PromptCategory:
    """提示词类别枚举"""
    STRUCTURED_GENERATION = "STRUCTURED_GENERATION"  # 结构化描述生成（有9个子分类）
    BRIEF_GENERATION = "BRIEF_GENERATION"  # 简介生成
    SINGLE_CHAT_SYSTEM = "SINGLE_CHAT_SYSTEM"  # 单聊系统提示
    SINGLE_CHAT_STM_COMPRESSION = "SINGLE_CHAT_STM_COMPRESSION"  # 单聊短期记忆凝练
    GROUP_CHAT_STM_COMPRESSION = "GROUP_CHAT_STM_COMPRESSION"  # 群聊短期记忆凝练
    LTM_INTEGRATION = "LTM_INTEGRATION"  # 长期记忆整合
    GROUP_MODERATOR = "GROUP_MODERATOR"  # 群聊中控
    GROUP_CHAT_CHARACTER = "GROUP_CHAT_CHARACTER"  # 群聊角色发言系统提示
    STRUCTURED_SYSTEM_MESSAGE = "STRUCTURED_SYSTEM_MESSAGE"  # 结构化生成系统消息
    
    # 评估器类别
    EVALUATOR_STRUCTURED_GEN = "EVALUATOR_STRUCTURED_GEN"  # 结构化生成评估器
    EVALUATOR_BRIEF_GEN = "EVALUATOR_BRIEF_GEN"  # 简介生成评估器
    EVALUATOR_SINGLE_CHAT = "EVALUATOR_SINGLE_CHAT"  # 单聊对话评估器
    EVALUATOR_GROUP_CHAT = "EVALUATOR_GROUP_CHAT"  # 群聊对话评估器
    EVALUATOR_STM_COMPRESSION = "EVALUATOR_STM_COMPRESSION"  # 短期记忆凝练评估器
    EVALUATOR_LTM_INTEGRATION = "EVALUATOR_LTM_INTEGRATION"  # 长期记忆整合评估器
    EVALUATOR_GROUP_MODERATOR = "EVALUATOR_GROUP_MODERATOR"  # 群聊中控评估器


# 结构化生成的子分类
class StructuredSubCategory:
    """结构化生成子分类"""
    BASIC_INFO = "基础身份信息"
    PERSONALITY = "个性与行为设定"
    BACKGROUND = "背景故事"
    KNOWLEDGE = "知识与能力"
    DIALOGUE = "对话与交互规范"
    TASK = "任务/功能性信息"
    WORLDVIEW = "环境与世界观"
    SYSTEM_PARAMS = "系统与控制参数"
    SOURCE = "来源"


class PromptManager:
    """提示词管理器"""
    
    @staticmethod
    def _get_cache_key(category: str, sub_category: Optional[str] = None) -> str:
        """生成缓存键"""
        if sub_category:
            return f"prompt:active:{category}:{sub_category}"
        return f"prompt:active:{category}"
    
    @staticmethod
    def get_active_prompt(category: str, sub_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取激活的提示词
        
        Args:
            category: 提示词类别
            sub_category: 子分类（可选，仅用于STRUCTURED_GENERATION）
        
        Returns:
            提示词字典，包含 id, template_content, metadata 等字段
            如果未找到则返回 None
        """
        # 检查是否启用数据库提示词
        if not USE_DB_PROMPTS:
            return None
        
        # 尝试从缓存获取
        cache = get_redis_cache()
        cache_key = PromptManager._get_cache_key(category, sub_category)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 从数据库查询
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            if sub_category:
                query = f"""
                    SELECT id, category, sub_category, name, description, template_content, 
                           version, metadata, created_at, updated_at
                    FROM prompt_templates
                    WHERE category = {placeholder} AND sub_category = {placeholder} AND is_active = {placeholder}
                    LIMIT 1
                """
                cur.execute(query, (category, sub_category, 1))
            else:
                query = f"""
                    SELECT id, category, sub_category, name, description, template_content, 
                           version, metadata, created_at, updated_at
                    FROM prompt_templates
                    WHERE category = {placeholder} AND is_active = {placeholder}
                    LIMIT 1
                """
                cur.execute(query, (category, 1))
            
            row = cur.fetchone()
            if not row:
                return None
            
            if USE_POSTGRESQL:
                result = _row_to_dict(row, cur)
            else:
                result = dict(row)
            
            # 解析 metadata JSON
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except:
                    result['metadata'] = {}
            else:
                result['metadata'] = {}
            
            # 缓存结果（5分钟）
            cache.set(cache_key, result, ttl=300)
            
            return result
        
        except Exception as e:
            print(f"[ERROR] 获取提示词失败: {e}")
            return None
        finally:
            _return_conn(conn)
    
    @staticmethod
    def list_prompts(category: Optional[str] = None, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """列出提示词
        
        Args:
            category: 筛选类别（可选）
            include_inactive: 是否包含未激活的提示词
        
        Returns:
            提示词列表
        """
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            conditions = []
            params = []
            
            if category:
                conditions.append(f"category = {placeholder}")
                params.append(category)
            
            if not include_inactive:
                conditions.append(f"is_active = {placeholder}")
                params.append(1)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT id, category, sub_category, name, description, template_content,
                       version, is_active, created_at, updated_at, metadata
                FROM prompt_templates
                WHERE {where_clause}
                ORDER BY category, sub_category, version DESC
            """
            
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                if USE_POSTGRESQL:
                    results.append(_row_to_dict(row, cur))
                else:
                    results.append(dict(row))
            
            return results
        
        except Exception as e:
            print(f"[ERROR] 列出提示词失败: {e}")
            return []
        finally:
            _return_conn(conn)
    
    @staticmethod
    def create_prompt(
        category: str,
        name: str,
        template_content: str,
        sub_category: Optional[str] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        is_active: bool = False,
        created_by: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """创建新提示词
        
        Returns:
            新创建的提示词ID，失败返回 None
        """
        conn = _get_conn()
        try:
            cur = conn.cursor()
            now = int(time.time())
            
            metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
            
            if USE_POSTGRESQL:
                query = """
                    INSERT INTO prompt_templates 
                    (category, sub_category, name, description, template_content, version, 
                     is_active, created_by, created_at, updated_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                cur.execute(query, (
                    category, sub_category, name, description, template_content, version,
                    1 if is_active else 0, created_by, now, now, metadata_json
                ))
                prompt_id = cur.fetchone()[0]
            else:
                query = """
                    INSERT INTO prompt_templates 
                    (category, sub_category, name, description, template_content, version, 
                     is_active, created_by, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cur.execute(query, (
                    category, sub_category, name, description, template_content, version,
                    1 if is_active else 0, created_by, now, now, metadata_json
                ))
                prompt_id = cur.lastrowid
            
            conn.commit()
            
            # 如果是激活状态，清除缓存
            if is_active:
                cache = get_redis_cache()
                cache.delete(PromptManager._get_cache_key(category, sub_category))
            
            print(f"[INFO] 创建提示词成功: {name} (ID: {prompt_id})")
            return prompt_id
        
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] 创建提示词失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            _return_conn(conn)
    
    @staticmethod
    def update_prompt(
        prompt_id: int,
        template_content: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        updated_by: Optional[int] = None,
        create_history: bool = True
    ) -> bool:
        """更新提示词
        
        Args:
            prompt_id: 提示词ID
            template_content: 新的提示词内容
            name: 新的名称
            description: 新的描述
            version: 新的版本号
            metadata: 新的元数据
            updated_by: 更新者ID
            create_history: 是否创建历史记录
        
        Returns:
            是否成功
        """
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            # 获取旧数据（用于历史记录）
            cur.execute(f"SELECT * FROM prompt_templates WHERE id = {placeholder}", (prompt_id,))
            old_row = cur.fetchone()
            if not old_row:
                return False
            
            if USE_POSTGRESQL:
                old_data = _row_to_dict(old_row, cur)
            else:
                old_data = dict(old_row)
            
            # 构建更新语句
            updates = []
            params = []
            
            if template_content is not None:
                updates.append(f"template_content = {placeholder}")
                params.append(template_content)
            
            if name is not None:
                updates.append(f"name = {placeholder}")
                params.append(name)
            
            if description is not None:
                updates.append(f"description = {placeholder}")
                params.append(description)
            
            if version is not None:
                updates.append(f"version = {placeholder}")
                params.append(version)
            
            if metadata is not None:
                updates.append(f"metadata = {placeholder}")
                params.append(json.dumps(metadata, ensure_ascii=False))
            
            if not updates:
                return True  # 没有更新内容
            
            now = int(time.time())
            updates.append(f"updated_at = {placeholder}")
            params.append(now)
            
            params.append(prompt_id)
            
            query = f"UPDATE prompt_templates SET {', '.join(updates)} WHERE id = {placeholder}"
            cur.execute(query, tuple(params))
            
            # 创建历史记录
            if create_history and template_content is not None:
                PromptManager._create_version_history(
                    cur, prompt_id, old_data['version'], old_data['template_content'],
                    "内容更新", updated_by, now
                )
            
            conn.commit()
            
            # 如果是激活状态，清除缓存
            if old_data.get('is_active'):
                cache = get_redis_cache()
                cache.delete(PromptManager._get_cache_key(
                    old_data['category'], old_data.get('sub_category')
                ))
            
            return True
        
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] 更新提示词失败: {e}")
            return False
        finally:
            _return_conn(conn)
    
    @staticmethod
    def activate_version(prompt_id: int, updated_by: Optional[int] = None) -> bool:
        """激活指定提示词版本
        
        激活时会将同类别（含子分类）的其他提示词设为未激活
        """
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            # 获取提示词信息
            cur.execute(f"SELECT category, sub_category FROM prompt_templates WHERE id = {placeholder}", (prompt_id,))
            row = cur.fetchone()
            if not row:
                return False
            
            if USE_POSTGRESQL:
                data = _row_to_dict(row, cur)
            else:
                data = dict(row)
            
            category = data['category']
            sub_category = data.get('sub_category')
            
            # 将同类别的其他提示词设为未激活
            if sub_category:
                cur.execute(
                    f"UPDATE prompt_templates SET is_active = {placeholder} WHERE category = {placeholder} AND sub_category = {placeholder}",
                    (0, category, sub_category)
                )
            else:
                cur.execute(
                    f"UPDATE prompt_templates SET is_active = {placeholder} WHERE category = {placeholder}",
                    (0, category)
                )
            
            # 激活目标提示词
            now = int(time.time())
            cur.execute(
                f"UPDATE prompt_templates SET is_active = {placeholder}, updated_at = {placeholder} WHERE id = {placeholder}",
                (1, now, prompt_id)
            )
            
            conn.commit()
            
            # 清除缓存
            cache = get_redis_cache()
            cache.delete(PromptManager._get_cache_key(category, sub_category))
            
            print(f"[INFO] 激活提示词: {prompt_id} (类别: {category}, 子分类: {sub_category})")
            return True
        
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] 激活提示词失败: {e}")
            return False
        finally:
            _return_conn(conn)
    
    @staticmethod
    def get_version_history(prompt_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """获取版本历史"""
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            query = f"""
                SELECT id, version, change_log, previous_content, created_by, created_at
                FROM prompt_version_history
                WHERE prompt_template_id = {placeholder}
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            
            cur.execute(query, (prompt_id,))
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                if USE_POSTGRESQL:
                    results.append(_row_to_dict(row, cur))
                else:
                    results.append(dict(row))
            
            return results
        
        except Exception as e:
            print(f"[ERROR] 获取版本历史失败: {e}")
            return []
        finally:
            _return_conn(conn)
    
    @staticmethod
    def _create_version_history(
        cur, prompt_id: int, version: str, previous_content: str,
        change_log: str, created_by: Optional[int], created_at: int
    ):
        """创建版本历史记录（内部方法）"""
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        query = f"""
            INSERT INTO prompt_version_history 
            (prompt_template_id, version, change_log, previous_content, created_by, created_at)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        
        cur.execute(query, (prompt_id, version, change_log, previous_content, created_by, created_at))
    
    @staticmethod
    def render_prompt(template: str, variables: Dict[str, Any]) -> str:
        """渲染提示词模板，替换变量
        
        Args:
            template: 提示词模板，包含 {变量名} 占位符
            variables: 变量字典
        
        Returns:
            渲染后的提示词
        """
        try:
            return template.format(**variables)
        except KeyError as e:
            print(f"[WARN] 提示词模板缺少变量: {e}")
            return template
        except Exception as e:
            print(f"[ERROR] 渲染提示词失败: {e}")
            return template
    
    @staticmethod
    def duplicate_prompt(prompt_id: int, new_version: str, created_by: Optional[int] = None) -> Optional[int]:
        """复制提示词为新版本
        
        Returns:
            新提示词的ID
        """
        conn = _get_conn()
        try:
            cur = conn.cursor()
            placeholder = "%s" if USE_POSTGRESQL else "?"
            
            # 获取原提示词
            cur.execute(f"SELECT * FROM prompt_templates WHERE id = {placeholder}", (prompt_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            if USE_POSTGRESQL:
                data = _row_to_dict(row, cur)
            else:
                data = dict(row)
            
            # 创建新提示词（未激活状态）
            now = int(time.time())
            
            if USE_POSTGRESQL:
                query = """
                    INSERT INTO prompt_templates 
                    (category, sub_category, name, description, template_content, version, 
                     is_active, created_by, created_at, updated_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                cur.execute(query, (
                    data['category'], data.get('sub_category'), 
                    data['name'] + f" (v{new_version})",
                    data.get('description'), data['template_content'], new_version,
                    0, created_by, now, now, data.get('metadata')
                ))
                new_id = cur.fetchone()[0]
            else:
                query = """
                    INSERT INTO prompt_templates 
                    (category, sub_category, name, description, template_content, version, 
                     is_active, created_by, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cur.execute(query, (
                    data['category'], data.get('sub_category'), 
                    data['name'] + f" (v{new_version})",
                    data.get('description'), data['template_content'], new_version,
                    0, created_by, now, now, data.get('metadata')
                ))
                new_id = cur.lastrowid
            
            conn.commit()
            
            print(f"[INFO] 复制提示词成功: {prompt_id} -> {new_id} (v{new_version})")
            return new_id
        
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] 复制提示词失败: {e}")
            return None
        finally:
            _return_conn(conn)

