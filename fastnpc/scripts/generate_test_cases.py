# -*- coding: utf-8 -*-
"""
测试用例批量生成工具

为指定的角色和群聊生成针对性的测试用例
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import time
from typing import List, Dict, Any

from fastnpc.api.auth import _get_conn, _return_conn, _row_to_dict
from fastnpc.config import USE_POSTGRESQL


# 测试群聊配置
TEST_GROUPS = {
    "政治局": ["特朗普", "普京", "泽连斯基"],
    "诗词局": ["李白", "杜甫", "苏轼", "李商隐", "李清照"],
    "神仙局": ["哪吒", "孙悟空", "杨戬", "观音菩萨"],
    "资本局": ["马斯克", "马云", "马化腾", "雷军", "黄仁勋"],
    "三国局": ["曹操", "刘备", "吕布", "诸葛亮", "周瑜", "孙权", "司马懿", "貂蝉", "小乔"],
    "明星局": ["胡歌", "马嘉祺", "蔡徐坤", "杨幂"],
    "名人局": ["罗永浩", "罗翔", "贾国龙"],
    "巨人局": ["艾伦·耶格尔", "阿明·阿诺德", "三笠·阿克曼", "利威尔·阿克曼", "莱纳·布朗"],
    "医疗局": ["张伯礼", "钟南山", "李时珍", "孙思邈"],
    "科学局": ["爱因斯坦", "牛顿", "玛丽·居里", "杨振宁"],
    "异人局": ["张楚岚", "冯宝宝", "张之维", "王也"]
}

# 单聊测试用例模板（针对不同角色类型）
SINGLE_CHAT_TEST_TEMPLATES = {
    "政治人物": [
        "你对当前的国际形势有什么看法？",
        "如果你能改变历史上的一个决定，你会改变什么？",
        "你认为领导者最重要的品质是什么？",
        "面对危机时，你通常如何决策？"
    ],
    "诗人": [
        "能为我即兴作一首诗吗？",
        "你最满意的作品是哪一首？为什么？",
        "你的创作灵感从何而来？",
        "如果生活在现代，你会写些什么？"
    ],
    "神话人物": [
        "你最引以为傲的本领是什么？",
        "修炼到你这个境界需要多久？",
        "天庭的生活是什么样的？",
        "你有什么趣事可以分享吗？"
    ],
    "企业家": [
        "你认为创业最重要的是什么？",
        "你是如何看待失败的？",
        "对年轻创业者有什么建议？",
        "未来十年你看好哪些行业？"
    ],
    "三国人物": [
        "你认为三国时期谁最有可能统一天下？",
        "如果重来一次，你会改变什么决策？",
        "你最敬佩的对手是谁？",
        "讲讲你最得意的一场战役"
    ],
    "明星": [
        "你是如何保持演技的？",
        "拍戏时有什么难忘的经历？",
        "对粉丝有什么想说的？",
        "未来有什么新作品计划？"
    ],
    "名人": [
        "你对年轻人有什么建议？",
        "你的人生哲学是什么？",
        "分享一个改变你的重要时刻",
        "你认为教育最重要的是什么？"
    ],
    "动漫角色": [
        "你的梦想是什么？",
        "战斗时你在想什么？",
        "你最珍视的人是谁？",
        "如果可以回到过去，你想改变什么？"
    ],
    "医学家": [
        "中西医结合的关键是什么？",
        "疫情给你带来了什么启发？",
        "如何看待现代医学的发展？",
        "对普通人养生有什么建议？"
    ],
    "科学家": [
        "你的研究最大的突破是什么？",
        "科学研究最困难的是什么？",
        "如何培养科学思维？",
        "对未来科技有什么展望？"
    ]
}

# 群聊测试用例模板（针对不同群组类型）
GROUP_CHAT_TEST_TEMPLATES = {
    "政治局": [
        "各位领导人，如何看待全球化的未来？",
        "如果让你们合作解决一个全球危机，会怎么分工？",
        "你们认为理想的国际秩序应该是怎样的？"
    ],
    "诗词局": [
        "各位诗人，能否以'明月'为题各作一首诗？",
        "你们觉得唐诗和宋词哪个更好？",
        "如何评价彼此的诗风？"
    ],
    "神仙局": [
        "如果要选一个最强战力，你们觉得是谁？",
        "天庭和灵山哪个更厉害？",
        "讲讲你们最精彩的一场斗法"
    ],
    "资本局": [
        "下一个改变世界的技术会是什么？",
        "如何看待AI对人类社会的影响？",
        "你们会如何投资未来？"
    ],
    "三国局": [
        "如果重新来过，天下该归谁？",
        "谁的谋略最高？",
        "讨论一下赤壁之战的成败因素"
    ],
    "明星局": [
        "娱乐圈最重要的是什么？",
        "如何平衡事业和生活？",
        "分享一下拍戏的趣事"
    ],
    "名人局": [
        "如何定义成功？",
        "对当下年轻人有什么建议？",
        "各自领域的核心是什么？"
    ],
    "巨人局": [
        "如何才能真正获得自由？",
        "面对敌人时的信念是什么？",
        "为了梦想可以付出什么代价？"
    ],
    "医疗局": [
        "中医和西医应该如何结合？",
        "未来医学的发展方向是什么？",
        "如何提高全民健康水平？"
    ],
    "科学局": [
        "物理学的终极问题是什么？",
        "科学和哲学的关系是什么？",
        "如何激发年轻人对科学的兴趣？"
    ],
    "异人局": [
        "异人界的规则合理吗？",
        "八奇技的秘密是什么？",
        "如何看待异人和普通人的关系？"
    ]
}

# 角色类型映射
CHARACTER_TYPE_MAP = {
    "特朗普": "政治人物", "普京": "政治人物", "泽连斯基": "政治人物",
    "李白": "诗人", "杜甫": "诗人", "苏轼": "诗人", "李商隐": "诗人", "李清照": "诗人",
    "哪吒": "神话人物", "孙悟空": "神话人物", "杨戬": "神话人物", "观音菩萨": "神话人物",
    "马斯克": "企业家", "马云": "企业家", "马化腾": "企业家", "雷军": "企业家", "黄仁勋": "企业家",
    "曹操": "三国人物", "刘备": "三国人物", "吕布": "三国人物", "诸葛亮": "三国人物", 
    "周瑜": "三国人物", "孙权": "三国人物", "司马懿": "三国人物", "貂蝉": "三国人物", "小乔": "三国人物",
    "胡歌": "明星", "马嘉祺": "明星", "蔡徐坤": "明星", "杨幂": "明星",
    "罗永浩": "名人", "罗翔": "名人", "贾国龙": "名人",
    "艾伦·耶格尔": "动漫角色", "阿明·阿诺德": "动漫角色", "三笠·阿克曼": "动漫角色", 
    "利威尔·阿克曼": "动漫角色", "莱纳·布朗": "动漫角色",
    "张伯礼": "医学家", "钟南山": "医学家", "李时珍": "医学家", "孙思邈": "医学家",
    "爱因斯坦": "科学家", "牛顿": "科学家", "玛丽·居里": "科学家", "杨振宁": "科学家",
    "张楚岚": "动漫角色", "冯宝宝": "动漫角色", "张之维": "动漫角色", "王也": "动漫角色"
}


def get_character_id(user_id: int, name: str) -> int:
    """获取角色ID"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        cur.execute(f"SELECT id FROM characters WHERE user_id={placeholder} AND name={placeholder}", (user_id, name))
        row = cur.fetchone()
        if row:
            return int(_row_to_dict(row, cur)['id'])
        return None
    finally:
        _return_conn(conn)


def get_group_id(user_id: int, name: str) -> int:
    """获取群聊ID"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        cur.execute(f"SELECT id FROM group_chats WHERE user_id={placeholder} AND name={placeholder}", (user_id, name))
        row = cur.fetchone()
        if row:
            return int(_row_to_dict(row, cur)['id'])
        return None
    finally:
        _return_conn(conn)


def create_test_case(
    category: str,
    target_type: str,
    target_id: str,
    name: str,
    description: str,
    test_content: Dict[str, Any],
    expected_behavior: str,
    test_config: Dict[str, Any] = None,
    created_by: int = 1
) -> int:
    """创建测试用例"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        now = int(time.time())
        
        # 检查是否已存在相同的测试用例
        cur.execute(
            f"SELECT id FROM test_cases WHERE category={placeholder} AND target_type={placeholder} AND target_id={placeholder} AND name={placeholder}",
            (category, target_type, target_id, name)
        )
        existing = cur.fetchone()
        if existing:
            print(f"[INFO] 测试用例已存在: {name}")
            return int(_row_to_dict(existing, cur)['id'])
        
        # 准备JSON数据
        test_content_json = json.dumps(test_content, ensure_ascii=False)
        test_config_json = json.dumps(test_config or {}, ensure_ascii=False) if test_config else None
        
        if USE_POSTGRESQL:
            cur.execute(
                """
                INSERT INTO test_cases(
                    version, category, target_type, target_id, name, description,
                    test_content, expected_behavior, test_config,
                    is_active, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                ("1.0.0", category, target_type, target_id, name, description,
                 test_content_json, expected_behavior, test_config_json,
                 1, created_by, now, now)
            )
            test_case_id = int(cur.fetchone()[0])
        else:
            cur.execute(
                """
                INSERT INTO test_cases(
                    version, category, target_type, target_id, name, description,
                    test_content, expected_behavior, test_config,
                    is_active, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("1.0.0", category, target_type, target_id, name, description,
                 test_content_json, expected_behavior, test_config_json,
                 1, created_by, now, now)
            )
            test_case_id = int(cur.lastrowid)
        
        conn.commit()
        print(f"[INFO] 创建测试用例: {name} (ID: {test_case_id})")
        return test_case_id
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 创建测试用例失败: {e}")
        raise
    finally:
        _return_conn(conn)


def generate_single_chat_tests(user_id: int, character_name: str, character_id: int):
    """为单个角色生成单聊测试用例"""
    char_type = CHARACTER_TYPE_MAP.get(character_name, "政治人物")
    templates = SINGLE_CHAT_TEST_TEMPLATES.get(char_type, SINGLE_CHAT_TEST_TEMPLATES["政治人物"])
    
    test_cases_created = []
    for idx, question in enumerate(templates, 1):
        name = f"{character_name}-单聊测试{idx}"
        description = f"测试{character_name}在{char_type}相关话题的对话能力"
        
        test_content = {
            "messages": [
                {"role": "user", "content": question}
            ]
        }
        
        expected_behavior = f"{character_name}应该以符合其身份和性格的方式回答问题，回答应该体现其专业领域的知识和个人风格"
        
        test_config = {
            "max_tokens": 500,
            "temperature": 0.7,
            "memory_budget": {
                "ctx_max_chat": 20,
                "ctx_max_stm": 5,
                "ctx_max_ltm": 10
            }
        }
        
        test_case_id = create_test_case(
            category="SINGLE_CHAT",
            target_type="character",
            target_id=str(character_id),
            name=name,
            description=description,
            test_content=test_content,
            expected_behavior=expected_behavior,
            test_config=test_config,
            created_by=user_id
        )
        test_cases_created.append(test_case_id)
    
    return test_cases_created


def generate_group_chat_tests(user_id: int, group_name: str, group_id: int):
    """为群聊生成测试用例"""
    templates = GROUP_CHAT_TEST_TEMPLATES.get(group_name, [])
    
    test_cases_created = []
    for idx, question in enumerate(templates, 1):
        name = f"{group_name}-群聊测试{idx}"
        description = f"测试{group_name}群组成员的互动和群聊中控的调度能力"
        
        test_content = {
            "messages": [
                {"role": "user", "content": question}
            ],
            "expected_rounds": 3  # 期望的对话轮次
        }
        
        expected_behavior = f"群聊中各成员应该根据话题积极发言，中控应该合理调度发言顺序，确保对话连贯且各具特色"
        
        test_config = {
            "max_tokens": 300,
            "temperature": 0.8,
            "max_group_reply_rounds": 5,
            "memory_budget": {
                "ctx_max_chat": 15,
                "ctx_max_stm": 5,
                "ctx_max_ltm": 8
            }
        }
        
        test_case_id = create_test_case(
            category="GROUP_CHAT",
            target_type="group",
            target_id=str(group_id),
            name=name,
            description=description,
            test_content=test_content,
            expected_behavior=expected_behavior,
            test_config=test_config,
            created_by=user_id
        )
        test_cases_created.append(test_case_id)
    
    return test_cases_created


def generate_structured_gen_tests(user_id: int, character_name: str, character_id: int):
    """为角色生成结构化生成测试用例（使用百科全文）"""
    name = f"{character_name}-结构化生成测试"
    description = f"使用{character_name}的百科全文测试结构化角色生成的质量"
    
    # 获取角色的百科内容
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        cur.execute(f"SELECT baike_content FROM characters WHERE id={placeholder}", (character_id,))
        row = cur.fetchone()
        if row:
            row_dict = _row_to_dict(row, cur)
            baike_content = row_dict.get('baike_content', '')
        else:
            baike_content = f"{character_name}的相关介绍..."
    finally:
        _return_conn(conn)
    
    test_content = {
        "source_text": baike_content[:5000] if baike_content else f"{character_name}的相关介绍...",  # 限制长度
        "target_categories": [
            "基础身份信息", "个性与行为设定", "背景故事",
            "知识与能力", "对话与交互规范", "环境与世界观"
        ]
    }
    
    expected_behavior = "生成的结构化信息应该准确提取原文关键信息，符合角色特征，各分类内容完整且不重复"
    
    test_config = {
        "model": "gpt-4o-mini",
        "temperature": 0.3
    }
    
    test_case_id = create_test_case(
        category="STRUCTURED_GEN",
        target_type="character",
        target_id=str(character_id),
        name=name,
        description=description,
        test_content=test_content,
        expected_behavior=expected_behavior,
        test_config=test_config,
        created_by=user_id
    )
    
    return [test_case_id]


def main(user_id: int = 1):
    """主函数：批量生成所有测试用例"""
    print("=" * 60)
    print("开始生成测试用例...")
    print("=" * 60)
    
    total_created = 0
    
    # 1. 为所有角色生成测试用例
    print("\n[1/3] 生成单聊测试用例...")
    all_characters = set()
    for members in TEST_GROUPS.values():
        all_characters.update(members)
    
    for char_name in sorted(all_characters):
        char_id = get_character_id(user_id, char_name)
        if char_id:
            # 单聊测试
            single_tests = generate_single_chat_tests(user_id, char_name, char_id)
            total_created += len(single_tests)
            
            # 结构化生成测试
            struct_tests = generate_structured_gen_tests(user_id, char_name, char_id)
            total_created += len(struct_tests)
            
            print(f"  ✓ {char_name}: {len(single_tests)} 单聊 + {len(struct_tests)} 结构化")
        else:
            print(f"  ✗ {char_name}: 角色不存在")
    
    # 2. 为所有群聊生成测试用例
    print("\n[2/3] 生成群聊测试用例...")
    for group_name in TEST_GROUPS.keys():
        group_id = get_group_id(user_id, group_name)
        if group_id:
            group_tests = generate_group_chat_tests(user_id, group_name, group_id)
            total_created += len(group_tests)
            print(f"  ✓ {group_name}: {len(group_tests)} 个测试用例")
        else:
            print(f"  ✗ {group_name}: 群聊不存在")
    
    # 3. 标记所有角色和群聊为测试用例
    print("\n[3/3] 标记测试角色和群聊...")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # PostgreSQL 使用 TRUE/FALSE，SQLite 使用 1/0
        test_value = True if USE_POSTGRESQL else 1
        
        marked_chars = 0
        marked_groups = 0
        
        # 标记角色
        for char_name in all_characters:
            cur.execute(
                f"UPDATE characters SET is_test_case={placeholder} WHERE user_id={placeholder} AND name={placeholder}",
                (test_value, user_id, char_name)
            )
            if cur.rowcount > 0:
                marked_chars += 1
        
        # 标记群聊
        for group_name in TEST_GROUPS.keys():
            cur.execute(
                f"UPDATE group_chats SET is_test_case={placeholder} WHERE user_id={placeholder} AND name={placeholder}",
                (test_value, user_id, group_name)
            )
            if cur.rowcount > 0:
                marked_groups += 1
        
        conn.commit()
        print(f"  ✓ 已标记 {marked_chars}/{len(all_characters)} 个角色和 {marked_groups}/{len(TEST_GROUPS)} 个群聊")
    finally:
        _return_conn(conn)
    
    print("\n" + "=" * 60)
    print(f"测试用例生成完成！共创建 {total_created} 个测试用例")
    print("=" * 60)


if __name__ == "__main__":
    # 使用管理员用户ID（通常是1）
    main(user_id=1)

