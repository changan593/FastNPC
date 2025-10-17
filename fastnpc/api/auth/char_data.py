# -*- coding: utf-8 -*-
"""
角色完整数据操作

提供角色完整数据的保存、加载以及记忆管理功能。
这些函数较长，单独放在一个文件中以便维护。
"""
from __future__ import annotations
import time
import json
from typing import Dict, Any, List, Optional

# 注意：_get_conn, _row_to_dict, USE_POSTGRESQL 作为参数传入，避免循环导入


def save_character_full_data(user_id: int, name: str, structured_data: Dict[str, Any], baike_content: str = None, _get_conn=None, USE_POSTGRESQL=None) -> int:
    """保存完整角色数据到所有相关表
    
    Args:
        user_id: 用户ID
        name: 角色名称
        structured_data: 结构化数据（字典格式）
        baike_content: 百科全文（JSON字符串）
        _get_conn: 数据库连接函数（内部使用）
        USE_POSTGRESQL: 是否使用PostgreSQL（内部使用）
    
    Returns:
        character_id: 角色ID
    """
    # 如果没有传入_get_conn和USE_POSTGRESQL，从auth导入（向后兼容）
    if _get_conn is None or USE_POSTGRESQL is None:
        from fastnpc.api.auth.db_utils import _get_conn as default_get_conn, _return_conn
        from fastnpc.config import USE_POSTGRESQL as default_use_pg
        _get_conn = default_get_conn
        USE_POSTGRESQL = default_use_pg
    else:
        from fastnpc.api.auth.db_utils import _return_conn
    
    from fastnpc.api.auth.db_utils import _row_to_dict
    
    conn = _get_conn()
    now = int(time.time())
    
    try:
        cur = conn.cursor()
        
        # 1. 先创建或更新角色主记录
        cur.execute("SELECT id FROM characters WHERE user_id=%s AND name=%s", (user_id, name))
        row = cur.fetchone()
        
        if row:
            # 更新现有角色
            character_id = int(_row_to_dict(row, cur)['id']) if USE_POSTGRESQL else int(row['id'])
            cur.execute(
                "UPDATE characters SET baike_content=%s, updated_at=%s WHERE id=%s",
                (baike_content, now, character_id)
            )
        else:
            # 创建新角色
            if USE_POSTGRESQL:
                cur.execute(
                    "INSERT INTO characters(user_id, name, model, source, structured_json, baike_content, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (user_id, name, '', '', json.dumps(structured_data, ensure_ascii=False), baike_content, now, now)
                )
                character_id = int(cur.fetchone()[0])
                conn.commit()  # 立即提交，确保后续外键关联能找到这条记录
            else:
                cur.execute(
                    "INSERT INTO characters(user_id, name, model, source, structured_json, baike_content, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    (user_id, name, '', '', json.dumps(structured_data, ensure_ascii=False), baike_content, now, now)
                )
                conn.commit()
                character_id = int(cur.lastrowid)
        
        # 辅助函数：将复杂类型转换为JSON字符串
        def _safe_json_value(value):
            if value is None:
                return None
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value) if value else None
        
        # 2. 保存基础身份信息
        basic_info = structured_data.get('基础身份信息', {})
        if basic_info:
            cur.execute("DELETE FROM character_basic_info WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_basic_info(character_id, name, age, gender, occupation, identity_background, appearance, titles, brief_intro)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (character_id, 
                 _safe_json_value(basic_info.get('姓名')),
                 _safe_json_value(basic_info.get('年龄')),
                 _safe_json_value(basic_info.get('性别')),
                 _safe_json_value(basic_info.get('职业')),
                 _safe_json_value(basic_info.get('身份背景')),
                 _safe_json_value(basic_info.get('外貌特征')),
                 _safe_json_value(basic_info.get('称谓/头衔')),
                 _safe_json_value(basic_info.get('人物简介')))
            )
        
        # 3. 保存知识与能力
        knowledge = structured_data.get('知识与能力', {})
        if knowledge:
            cur.execute("DELETE FROM character_knowledge WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_knowledge(character_id, knowledge_domain, skills, limitations)
                   VALUES(%s,%s,%s,%s)""",
                (character_id, _safe_json_value(knowledge.get('知识领域')), 
                 _safe_json_value(knowledge.get('技能')), _safe_json_value(knowledge.get('限制')))
            )
        
        # 4. 保存个性与行为设定
        personality = structured_data.get('个性与行为设定', {})
        if personality:
            cur.execute("DELETE FROM character_personality WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_personality(character_id, traits, values, emotion_style, speaking_style, preferences, dislikes, motivation_goals)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(personality.get('性格特质')), 
                 _safe_json_value(personality.get('价值观')), _safe_json_value(personality.get('情绪风格')),
                 _safe_json_value(personality.get('说话方式')), _safe_json_value(personality.get('偏好')), 
                 _safe_json_value(personality.get('厌恶')), _safe_json_value(personality.get('动机与目标')))
            )
        
        # 5. 保存对话与交互规范
        dialogue = structured_data.get('对话与交互规范', {})
        if dialogue:
            cur.execute("DELETE FROM character_dialogue_rules WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_dialogue_rules(character_id, tone, language_style, behavior_constraints, interaction_pattern)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(dialogue.get('语气')), _safe_json_value(dialogue.get('语言风格')), 
                 _safe_json_value(dialogue.get('行为约束')), _safe_json_value(dialogue.get('互动模式')))
            )
        
        # 6. 保存任务/功能性信息
        tasks = structured_data.get('任务/功能性信息', {})
        if tasks:
            cur.execute("DELETE FROM character_tasks WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_tasks(character_id, task_goal, dialogue_intent, interaction_limits, trigger_conditions)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(tasks.get('任务目标')), _safe_json_value(tasks.get('对话意图')), 
                 _safe_json_value(tasks.get('交互限制')), _safe_json_value(tasks.get('触发条件')))
            )
        
        # 7. 保存环境与世界观
        worldview = structured_data.get('环境与世界观', {})
        if worldview:
            cur.execute("DELETE FROM character_worldview WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_worldview(character_id, worldview, timeline, social_rules, external_resources)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(worldview.get('世界观')), _safe_json_value(worldview.get('时间线')), 
                 _safe_json_value(worldview.get('社会规则')), _safe_json_value(worldview.get('外部资源')))
            )
        
        # 8. 保存背景故事
        background = structured_data.get('背景故事', {})
        if background:
            cur.execute("DELETE FROM character_background WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_background(character_id, origin, current_situation, secrets)
                   VALUES(%s,%s,%s,%s)""",
                (character_id, _safe_json_value(background.get('出身')), 
                 _safe_json_value(background.get('当前处境')), _safe_json_value(background.get('秘密')))
            )
            
            # 保存经历
            experiences = background.get('经历', [])
            if experiences:
                cur.execute("DELETE FROM character_experiences WHERE character_id=%s", (character_id,))
                for idx, exp in enumerate(experiences):
                    cur.execute(
                        """INSERT INTO character_experiences(character_id, experience_text, sequence_order, created_at)
                           VALUES(%s,%s,%s,%s)""",
                        (character_id, exp, idx, now)
                    )
            
            # 保存关系网络
            relationships = background.get('关系网络', [])
            if relationships:
                cur.execute("DELETE FROM character_relationships WHERE character_id=%s", (character_id,))
                for rel in relationships:
                    cur.execute(
                        """INSERT INTO character_relationships(character_id, relationship_text, created_at)
                           VALUES(%s,%s,%s)""",
                        (character_id, rel, now)
                    )
        
        # 9. 保存系统与控制参数
        system_params = structured_data.get('系统与控制参数', {})
        if system_params:
            cur.execute("DELETE FROM character_system_params WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_system_params(character_id, consistency_control, preference_control, safety_limits, deduction_range)
                   VALUES(%s,%s,%s,%s,%s)""",
                (character_id, _safe_json_value(system_params.get('一致性控制')), 
                 _safe_json_value(system_params.get('偏好控制')), 
                 _safe_json_value(system_params.get('安全限制')), _safe_json_value(system_params.get('演绎范围')))
            )
        
        # 10. 保存来源信息
        source_info = structured_data.get('来源信息', {})
        if source_info:
            # 获取现有的 source_info_size（如果 baike_content 为 None，保留原值）
            if baike_content is not None:
                source_info_size = len(baike_content)
            else:
                # 保留原有的值
                cur.execute("SELECT source_info_size FROM character_source_info WHERE character_id=%s", (character_id,))
                existing_row = cur.fetchone()
                if existing_row:
                    source_info_size = existing_row[0] if existing_row[0] is not None else 0
                else:
                    source_info_size = 0
            
            cur.execute("DELETE FROM character_source_info WHERE character_id=%s", (character_id,))
            cur.execute(
                """INSERT INTO character_source_info(character_id, unique_id, source_url, source_info_size)
                   VALUES(%s,%s,%s,%s)""",
                (character_id, _safe_json_value(source_info.get('唯一标识')), 
                 _safe_json_value(source_info.get('链接')), source_info_size)
            )
        
        conn.commit()
        return character_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        _return_conn(conn)


def load_character_full_data_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id: int) -> Optional[Dict[str, Any]]:
    """从所有相关表加载完整角色数据
    
    Args:
        character_id: 角色ID
    
    Returns:
        完整的角色数据字典，如果角色不存在则返回 None
    """
    from fastnpc.api.auth.db_utils import _return_conn
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 1. 加载主表数据
        cur.execute("SELECT id, user_id, name, model, source, baike_content, created_at, updated_at FROM characters WHERE id=%s", (character_id,))
        main_row = cur.fetchone()
        if not main_row:
            return None
        
        main_data = _row_to_dict(main_row, cur)
        
        result = {
            "_metadata": {
                "character_id": main_data['id'],
                "user_id": main_data['user_id'],
                "name": main_data['name'],
                "model": main_data['model'],
                "source": main_data['source'],
                "created_at": main_data['created_at'],
                "updated_at": main_data['updated_at'],
            },
            "baike_content": main_data.get('baike_content'),
        }
        
        # 2. 加载基础身份信息
        cur.execute("SELECT * FROM character_basic_info WHERE character_id=%s", (character_id,))
        basic_row = cur.fetchone()
        if basic_row:
            basic_data = _row_to_dict(basic_row, cur)
            result['基础身份信息'] = {
                "姓名": basic_data.get('name'),
                "年龄": basic_data.get('age'),
                "性别": basic_data.get('gender'),
                "职业": basic_data.get('occupation'),
                "身份背景": basic_data.get('identity_background'),
                "外貌特征": basic_data.get('appearance'),
                "称谓/头衔": basic_data.get('titles'),
                "人物简介": basic_data.get('brief_intro'),
            }
        
        # 3. 加载知识与能力
        cur.execute("SELECT * FROM character_knowledge WHERE character_id=%s", (character_id,))
        knowledge_row = cur.fetchone()
        if knowledge_row:
            knowledge_data = _row_to_dict(knowledge_row, cur)
            result['知识与能力'] = {
                "知识领域": knowledge_data.get('knowledge_domain'),
                "技能": knowledge_data.get('skills'),
                "限制": knowledge_data.get('limitations'),
            }
        
        # 4. 加载个性与行为设定
        cur.execute("SELECT * FROM character_personality WHERE character_id=%s", (character_id,))
        personality_row = cur.fetchone()
        if personality_row:
            personality_data = _row_to_dict(personality_row, cur)
            result['个性与行为设定'] = {
                "性格特质": personality_data.get('traits'),
                "价值观": personality_data.get('values'),
                "情绪风格": personality_data.get('emotion_style'),
                "说话方式": personality_data.get('speaking_style'),
                "偏好": personality_data.get('preferences'),
                "厌恶": personality_data.get('dislikes'),
                "动机与目标": personality_data.get('motivation_goals'),
            }
        
        # 5. 加载对话与交互规范
        cur.execute("SELECT * FROM character_dialogue_rules WHERE character_id=%s", (character_id,))
        dialogue_row = cur.fetchone()
        if dialogue_row:
            dialogue_data = _row_to_dict(dialogue_row, cur)
            result['对话与交互规范'] = {
                "语气": dialogue_data.get('tone'),
                "语言风格": dialogue_data.get('language_style'),
                "行为约束": dialogue_data.get('behavior_constraints'),
                "互动模式": dialogue_data.get('interaction_pattern'),
            }
        
        # 6. 加载任务/功能性信息
        cur.execute("SELECT * FROM character_tasks WHERE character_id=%s", (character_id,))
        tasks_row = cur.fetchone()
        if tasks_row:
            tasks_data = _row_to_dict(tasks_row, cur)
            result['任务/功能性信息'] = {
                "任务目标": tasks_data.get('task_goal'),
                "对话意图": tasks_data.get('dialogue_intent'),
                "交互限制": tasks_data.get('interaction_limits'),
                "触发条件": tasks_data.get('trigger_conditions'),
            }
        
        # 7. 加载环境与世界观
        cur.execute("SELECT * FROM character_worldview WHERE character_id=%s", (character_id,))
        worldview_row = cur.fetchone()
        if worldview_row:
            worldview_data = _row_to_dict(worldview_row, cur)
            result['环境与世界观'] = {
                "世界观": worldview_data.get('worldview'),
                "时间线": worldview_data.get('timeline'),
                "社会规则": worldview_data.get('social_rules'),
                "外部资源": worldview_data.get('external_resources'),
            }
        
        # 8. 加载背景故事
        cur.execute("SELECT * FROM character_background WHERE character_id=%s", (character_id,))
        background_row = cur.fetchone()
        if background_row:
            background_data = _row_to_dict(background_row, cur)
            result['背景故事'] = {
                "出身": background_data.get('origin'),
                "当前处境": background_data.get('current_situation'),
                "秘密": background_data.get('secrets'),
            }
            
            # 加载经历
            cur.execute("SELECT experience_text FROM character_experiences WHERE character_id=%s ORDER BY sequence_order ASC", (character_id,))
            exp_rows = cur.fetchall()
            if exp_rows:
                result['背景故事']['经历'] = [_row_to_dict(row, cur)['experience_text'] for row in exp_rows]
            
            # 加载关系网络
            cur.execute("SELECT relationship_text FROM character_relationships WHERE character_id=%s ORDER BY created_at ASC", (character_id,))
            rel_rows = cur.fetchall()
            if rel_rows:
                result['背景故事']['关系网络'] = [_row_to_dict(row, cur)['relationship_text'] for row in rel_rows]
        
        # 9. 加载系统与控制参数
        cur.execute("SELECT * FROM character_system_params WHERE character_id=%s", (character_id,))
        system_row = cur.fetchone()
        if system_row:
            system_data = _row_to_dict(system_row, cur)
            result['系统与控制参数'] = {
                "一致性控制": system_data.get('consistency_control'),
                "偏好控制": system_data.get('preference_control'),
                "安全限制": system_data.get('safety_limits'),
                "演绎范围": system_data.get('deduction_range'),
            }
        
        # 10. 加载来源信息
        cur.execute("SELECT * FROM character_source_info WHERE character_id=%s", (character_id,))
        source_row = cur.fetchone()
        if source_row:
            source_data = _row_to_dict(source_row, cur)
            result['来源信息'] = {
                "唯一标识": source_data.get('unique_id'),
                "链接": source_data.get('source_url'),
                "来源信息量": source_data.get('source_info_size'),
            }
        
        return result
        
    finally:
        _return_conn(conn)


def save_character_memories_impl(_get_conn, USE_POSTGRESQL, character_id: int, short_term: List[str] = None, long_term: List[str] = None) -> None:
    """保存角色记忆到数据库（并清除缓存）
    
    Args:
        character_id: 角色ID
        short_term: 短期记忆列表
        long_term: 长期记忆列表
    """
    from fastnpc.api.auth.db_utils import _return_conn
    from fastnpc.api.cache import get_redis_cache
    
    conn = _get_conn()
    now = int(time.time())
    
    try:
        cur = conn.cursor()
        
        # 保存短期记忆
        if short_term is not None:
            # 先删除旧的短期记忆
            cur.execute("DELETE FROM character_memories WHERE character_id=%s AND memory_type=%s", (character_id, 'short_term'))
            # 插入新的短期记忆
            for memory in short_term:
                cur.execute(
                    "INSERT INTO character_memories(character_id, memory_type, content, created_at) VALUES(%s,%s,%s,%s)",
                    (character_id, 'short_term', memory, now)
                )
        
        # 保存长期记忆
        if long_term is not None:
            # 先删除旧的长期记忆
            cur.execute("DELETE FROM character_memories WHERE character_id=%s AND memory_type=%s", (character_id, 'long_term'))
            # 插入新的长期记忆
            for memory in long_term:
                cur.execute(
                    "INSERT INTO character_memories(character_id, memory_type, content, created_at) VALUES(%s,%s,%s,%s)",
                    (character_id, 'long_term', memory, now)
                )
        
        conn.commit()
        
        # 清除角色配置缓存（因为包含记忆）
        try:
            cache = get_redis_cache()
            # 获取角色名称和user_id来构建缓存key
            cur.execute("SELECT name, user_id FROM characters WHERE id=%s", (character_id,))
            row = cur.fetchone()
            if row:
                name, user_id = row[0], row[1]
                cache.delete(f"char_profile:{user_id}:{name}")
        except Exception as cache_error:
            # 缓存清除失败不影响主逻辑
            print(f"[WARN] 清除缓存失败: {cache_error}")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        _return_conn(conn)


def load_character_memories_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id: int) -> Dict[str, List[str]]:
    """从数据库加载角色记忆
    
    Args:
        character_id: 角色ID
    
    Returns:
        包含 'short_term' 和 'long_term' 键的字典
    """
    from fastnpc.api.auth.db_utils import _return_conn
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 加载短期记忆
        cur.execute(
            "SELECT content FROM character_memories WHERE character_id=%s AND memory_type=%s ORDER BY created_at ASC",
            (character_id, 'short_term')
        )
        short_rows = cur.fetchall()
        short_term = [_row_to_dict(row, cur)['content'] for row in short_rows]
        
        # 加载长期记忆
        cur.execute(
            "SELECT content FROM character_memories WHERE character_id=%s AND memory_type=%s ORDER BY created_at ASC",
            (character_id, 'long_term')
        )
        long_rows = cur.fetchall()
        long_term = [_row_to_dict(row, cur)['content'] for row in long_rows]
        
        return {
            "short_term": short_term,
            "long_term": long_term,
        }
        
    finally:
        _return_conn(conn)

