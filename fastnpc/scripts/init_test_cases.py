# -*- coding: utf-8 -*-
"""
测试用例初始化脚本
为9类提示词创建测试用例
"""
from __future__ import annotations

import sys
import os
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from fastnpc.config import USE_POSTGRESQL
from fastnpc.api.auth.db_utils import _get_conn, _return_conn


def create_test_case(prompt_category: str, prompt_sub_category: str, name: str, description: str,
                     input_data: dict, expected_output: str, evaluation_metrics: dict):
    """创建测试用例"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        now = int(time.time())
        
        input_data_json = json.dumps(input_data, ensure_ascii=False)
        evaluation_metrics_json = json.dumps(evaluation_metrics, ensure_ascii=False)
        
        if USE_POSTGRESQL:
            query = """
                INSERT INTO prompt_test_cases 
                (prompt_category, prompt_sub_category, name, description, input_data, expected_output, evaluation_metrics, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            cur.execute(query, (
                prompt_category, prompt_sub_category, name, description,
                input_data_json, expected_output, evaluation_metrics_json, now
            ))
            test_case_id = cur.fetchone()[0]
        else:
            query = """
                INSERT INTO prompt_test_cases 
                (prompt_category, prompt_sub_category, name, description, input_data, expected_output, evaluation_metrics, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cur.execute(query, (
                prompt_category, prompt_sub_category, name, description,
                input_data_json, expected_output, evaluation_metrics_json, now
            ))
            test_case_id = cur.lastrowid
        
        conn.commit()
        print(f"  ✓ 创建测试用例: {name} (ID: {test_case_id})")
        return test_case_id
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ 创建测试用例失败 {name}: {e}")
        return None
    finally:
        _return_conn(conn)


def init_structured_generation_test_cases():
    """初始化结构化生成测试用例"""
    print("\n===== 结构化生成测试用例 =====")
    
    # 测试用例1：历史人物
    create_test_case(
        prompt_category="STRUCTURED_GENERATION",
        prompt_sub_category="基础身份信息",
        name="历史人物-李白",
        description="测试提取历史人物的基础身份信息",
        input_data={
            "persona_name": "李白",
            "facts_markdown": """
李白（701年—762年12月），字太白，号青莲居士，又号"谪仙人"。
是唐代伟大的浪漫主义诗人，被后人誉为"诗仙"。
祖籍陇西成纪（待考），出生于西域碎叶城，4岁再迁回剑南道绵州。
李白存世诗文千余篇，有《李太白集》传世。
762年病逝，享年61岁。
            """
        },
        expected_output="包含姓名、年龄、性别、职业、身份背景、外貌特征、称谓/头衔等完整字段的JSON",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["姓名", "年龄", "性别", "职业", "身份背景", "称谓/头衔"],
            "output_length": [100, 500]
        }
    )
    
    # 测试用例2：现代职场角色
    create_test_case(
        prompt_category="STRUCTURED_GENERATION",
        prompt_sub_category="个性与行为设定",
        name="现代职场-产品经理",
        description="测试提取现代职场角色的性格特质",
        input_data={
            "persona_name": "张明",
            "facts_markdown": """
张明，32岁，互联网公司产品经理。
性格果断、追求效率，善于分析用户需求。
工作中注重数据驱动决策，团队协作能力强。
业余时间喜欢阅读科技类书籍，关注行业动态。
目标是成为一名优秀的产品总监。
            """
        },
        expected_output="包含性格特质、价值观、情绪风格、说话方式、偏好、厌恶、动机与目标的JSON",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["性格特质", "价值观", "情绪风格", "说话方式", "偏好", "厌恶", "动机与目标"],
            "output_length": [150, 600]
        }
    )
    
    # 测试用例3：虚构角色
    create_test_case(
        prompt_category="STRUCTURED_GENERATION",
        prompt_sub_category="背景故事",
        name="奇幻角色-精灵法师",
        description="测试提取虚构角色的背景故事",
        input_data={
            "persona_name": "艾莉娅",
            "facts_markdown": """
艾莉娅，精灵族法师，外表年轻但已有300岁。
出生于月光森林的贵族家庭，自幼展现魔法天赋。
曾在魔法学院学习十年，师从大贤者莫里斯。
因探索禁忌魔法被学院驱逐，开始流浪冒险生涯。
与冒险团队结识了人类战士雷克斯、矮人工匠格林等伙伴。
内心深处渴望找到失散多年的妹妹。
            """
        },
        expected_output="包含出身、经历、当前处境、关系网络、秘密的JSON，其中经历和关系网络为数组",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["出身", "经历", "当前处境", "关系网络", "秘密"],
            "output_length": [200, 800]
        }
    )


def init_brief_generation_test_cases():
    """初始化简介生成测试用例"""
    print("\n===== 简介生成测试用例 =====")
    
    create_test_case(
        prompt_category="BRIEF_GENERATION",
        prompt_sub_category=None,
        name="历史人物简介-李白",
        description="测试生成简洁的人物简介",
        input_data={
            "persona_name": "李白",
            "person": "第三人称",
            "role_json": json.dumps({
                "基础身份信息": {"姓名": "李白", "年龄": "61岁", "职业": "诗人"},
                "个性与行为设定": {"性格特质": "豪放不羁、才华横溢"}
            }, ensure_ascii=False)
        },
        expected_output="2-4句的自然段落，使用第三人称，简洁描述角色",
        evaluation_metrics={
            "no_json_output": True,
            "output_length": [50, 200],
            "keywords": ["李白", "诗人"]
        }
    )
    
    create_test_case(
        prompt_category="BRIEF_GENERATION",
        prompt_sub_category=None,
        name="第一人称简介",
        description="测试生成第一人称简介",
        input_data={
            "persona_name": "张明",
            "person": "第一人称",
            "role_json": json.dumps({
                "基础身份信息": {"姓名": "张明", "年龄": "32岁", "职业": "产品经理"},
                "个性与行为设定": {"性格特质": "果断、追求效率"}
            }, ensure_ascii=False)
        },
        expected_output="2-4句的自然段落，使用第一人称（我），简洁描述角色",
        evaluation_metrics={
            "first_person_check": True,
            "no_json_output": True,
            "output_length": [50, 200]
        }
    )


def init_single_chat_test_cases():
    """初始化单聊系统提示测试用例"""
    print("\n===== 单聊系统提示测试用例 =====")
    
    create_test_case(
        prompt_category="SINGLE_CHAT_SYSTEM",
        prompt_sub_category=None,
        name="基础对话规则检查",
        description="测试单聊系统提示是否包含必要的对话规则",
        input_data={
            "display_name": "李白",
            "user_name": "小明"
        },
        expected_output="包含第一人称要求、不暴露设定、自然流畅、简洁回答等规则的系统提示",
        evaluation_metrics={
            "keywords": ["第一人称", "李白", "小明", "自然流畅"],
            "output_length": [200, 1000]
        }
    )


def init_memory_compression_test_cases():
    """初始化记忆凝练测试用例"""
    print("\n===== 记忆凝练测试用例 =====")
    
    # 单聊短期记忆凝练
    create_test_case(
        prompt_category="SINGLE_CHAT_STM_COMPRESSION",
        prompt_sub_category=None,
        name="单聊对话记忆提取",
        description="测试从单聊对话中提取关键记忆",
        input_data={
            "role_name": "李白",
            "user_name": "小明",
            "chat_to_compress": """
小明: 李白兄，明天我要去长安参加诗会，你能帮我准备一首诗吗？
李白: 好啊，我明天上午就给你写好。你想要什么主题的？
小明: 我想要一首咏月的诗。
李白: 没问题，我最擅长咏月了。
            """,
            "overlap_context": ""
        },
        expected_output="JSON格式的短期记忆列表，每条格式为'主语 | 动作/事实 | 补充'",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["short_memories"],
            "keywords": ["小明", "李白", "诗会", "明天"]
        }
    )
    
    # 群聊短期记忆凝练
    create_test_case(
        prompt_category="GROUP_CHAT_STM_COMPRESSION",
        prompt_sub_category=None,
        name="群聊对话记忆提取",
        description="测试从群聊对话中提取关键记忆",
        input_data={
            "role_name": "李白",
            "participants_list": "- 李白: 唐代诗人\n- 杜甫: 唐代诗人\n- 用户小明",
            "chat_to_compress": """
小明: 两位诗人都擅长什么风格？
李白: 我更喜欢浪漫主义，抒发豪情。
杜甫: 我偏向现实主义，关注民生疾苦。
小明: 能否合作创作一首诗？
            """,
            "overlap_context": ""
        },
        expected_output="JSON格式的群聊短期记忆列表，明确记录'谁对谁说了什么'",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["short_memories"],
            "keywords": ["李白", "杜甫", "浪漫主义", "现实主义"]
        }
    )


def init_ltm_integration_test_cases():
    """初始化长期记忆整合测试用例"""
    print("\n===== 长期记忆整合测试用例 =====")
    
    create_test_case(
        prompt_category="LTM_INTEGRATION",
        prompt_sub_category=None,
        name="短期记忆整合为长期记忆",
        description="测试将短期记忆整合、去重、评分为长期记忆",
        input_data={
            "role_profile_summary": "李白，唐代诗人，性格豪放，喜好饮酒作诗",
            "short_memories_to_integrate": """
- 小明 | 邀请李白明天参加诗会 | 在长安举办
- 李白 | 答应帮小明准备一首咏月诗 | 明天上午完成
- 小明 | 表达对李白诗才的赞赏 | 称其为诗仙
            """,
            "current_long_term_memories": """
- 李白擅长咏月诗，常以月为题材创作
- 李白喜欢与朋友饮酒论诗
            """
        },
        expected_output="JSON格式的长期记忆列表，每条包含content、importance、reason字段",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["long_term_memories", "merged_count", "discarded_count"]
        }
    )


def init_group_moderator_test_cases():
    """初始化群聊中控测试用例"""
    print("\n===== 群聊中控测试用例 =====")
    
    create_test_case(
        prompt_category="GROUP_MODERATOR",
        prompt_sub_category=None,
        name="判断下一个发言者",
        description="测试根据对话上下文判断最合适的下一位发言者",
        input_data={
            "participants": """
- 李白: 唐代浪漫主义诗人，性格豪放洒脱，擅长饮酒作诗
- 杜甫: 唐代现实主义诗人，关注民生，文风沉郁顿挫
            """,
            "recent_messages": """
用户小明: 李白，你觉得什么是真正的诗？
李白: 诗应当抒发胸中豪情，挥洒自如。
用户小明: 杜甫先生，你怎么看？
            """
        },
        expected_output="JSON格式，包含next_speaker（角色名）、reason（理由）、confidence（置信度）",
        evaluation_metrics={
            "json_valid": True,
            "fields_complete": ["next_speaker", "reason", "confidence"]
        }
    )


def init_group_chat_character_test_cases():
    """初始化群聊角色发言测试用例"""
    print("\n===== 群聊角色发言测试用例 =====")
    
    create_test_case(
        prompt_category="GROUP_CHAT_CHARACTER",
        prompt_sub_category=None,
        name="群聊角色系统提示",
        description="测试群聊中单个角色的发言系统提示",
        input_data={
            "display_name": "李白",
            "other_members": "杜甫、用户小明"
        },
        expected_output="包含第一人称、群聊互动规则、保持角色设定的系统提示",
        evaluation_metrics={
            "keywords": ["李白", "第一人称", "群聊", "杜甫"],
            "output_length": [100, 500]
        }
    )


def init_structured_system_message_test_cases():
    """初始化结构化生成系统消息测试用例"""
    print("\n===== 结构化生成系统消息测试用例 =====")
    
    create_test_case(
        prompt_category="STRUCTURED_SYSTEM_MESSAGE",
        prompt_sub_category=None,
        name="系统消息格式检查",
        description="测试结构化生成的系统消息是否包含必要指令",
        input_data={},
        expected_output="包含严格JSON输出要求、基于事实列表提取、中文字段等指令的系统消息",
        evaluation_metrics={
            "keywords": ["JSON", "中文", "事实"],
            "output_length": [50, 300]
        }
    )


def main():
    """主函数"""
    print("=" * 60)
    print("测试用例初始化脚本")
    print("为9类提示词创建测试用例")
    print("=" * 60)
    
    try:
        init_structured_generation_test_cases()  # 3个
        init_brief_generation_test_cases()  # 2个
        init_single_chat_test_cases()  # 1个
        init_memory_compression_test_cases()  # 2个
        init_ltm_integration_test_cases()  # 1个
        init_group_moderator_test_cases()  # 1个
        init_group_chat_character_test_cases()  # 1个
        init_structured_system_message_test_cases()  # 1个
        
        print("\n" + "=" * 60)
        print("✓ 所有测试用例创建完成！")
        print("=" * 60)
        
        # 统计信息
        from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
        from fastnpc.config import USE_POSTGRESQL
        
        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM prompt_test_cases")
            count = cur.fetchone()[0]
            print(f"\n当前测试用例总数: {count}")
            
            # 按类别统计
            if USE_POSTGRESQL:
                cur.execute("""
                    SELECT prompt_category, COUNT(*) as cnt 
                    FROM prompt_test_cases 
                    GROUP BY prompt_category 
                    ORDER BY prompt_category
                """)
            else:
                cur.execute("""
                    SELECT prompt_category, COUNT(*) as cnt 
                    FROM prompt_test_cases 
                    GROUP BY prompt_category 
                    ORDER BY prompt_category
                """)
            
            rows = cur.fetchall()
            print("\n各类别测试用例数量:")
            for row in rows:
                if USE_POSTGRESQL:
                    data = _row_to_dict(row, cur)
                    print(f"  - {data['prompt_category']}: {data['cnt']}")
                else:
                    print(f"  - {row[0]}: {row[1]}")
        finally:
            _return_conn(conn)
    
    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

