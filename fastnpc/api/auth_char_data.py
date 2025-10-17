# -*- coding: utf-8 -*-
"""
角色完整数据加载和记忆相关函数的扩展模块
这些函数太长，单独放在一个文件中以便维护
"""
from __future__ import annotations
import time
from typing import Dict, Any, List, Optional

# 这些会从 auth.py 导入
# from fastnpc.api.auth import _get_conn, _row_to_dict, USE_POSTGRESQL


def load_character_full_data_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id: int) -> Optional[Dict[str, Any]]:
    """从所有相关表加载完整角色数据
    
    Args:
        character_id: 角色ID
    
    Returns:
        完整的角色数据字典，如果角色不存在则返回 None
    """
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
        conn.close()


def save_character_memories_impl(_get_conn, USE_POSTGRESQL, character_id: int, short_term: List[str] = None, long_term: List[str] = None) -> None:
    """保存角色记忆到数据库
    
    Args:
        character_id: 角色ID
        short_term: 短期记忆列表
        long_term: 长期记忆列表
    """
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
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def load_character_memories_impl(_get_conn, _row_to_dict, USE_POSTGRESQL, character_id: int) -> Dict[str, List[str]]:
    """从数据库加载角色记忆
    
    Args:
        character_id: 角色ID
    
    Returns:
        包含 'short_term' 和 'long_term' 键的字典
    """
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
        conn.close()

