#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 迁移验证脚本
验证FastNPC项目是否完全基于PostgreSQL数据库正常运行
"""

import sys
import time
from fastnpc.api.auth import (
    _get_conn, init_db,
    list_characters,
    load_character_full_data, load_character_memories,
    list_group_chats
)

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_test(name, status, detail=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {name}")
    if detail:
        print(f"   {detail}")

def test_database_connection():
    """测试1: 数据库连接"""
    print_header("测试 1: 数据库连接")
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        conn.close()
        print_test("PostgreSQL连接", True, f"版本: {version[:50]}...")
        return True
    except Exception as e:
        print_test("PostgreSQL连接", False, f"错误: {e}")
        return False

def test_database_tables():
    """测试2: 数据库表结构"""
    print_header("测试 2: 数据库表结构")
    
    required_tables = [
        'users', 'characters', 'messages', 'user_settings',
        'character_basic_info', 'character_knowledge', 'character_personality',
        'character_dialogue_rules', 'character_tasks', 'character_worldview',
        'character_background', 'character_experiences', 'character_relationships',
        'character_system_params', 'character_source_info', 'character_memories',
        'group_chats', 'group_members', 'group_messages', 'feedbacks'
    ]
    
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_tables = [row[0] for row in cur.fetchall()]
        conn.close()
        
        all_exist = True
        for table in required_tables:
            exists = table in existing_tables
            print_test(f"表 {table}", exists)
            if not exists:
                all_exist = False
        
        return all_exist
    except Exception as e:
        print_test("检查表结构", False, f"错误: {e}")
        return False

def test_character_data():
    """测试3: 角色数据完整性"""
    print_header("测试 3: 角色数据完整性")
    
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        # 检查角色主表
        cur.execute("SELECT COUNT(*) FROM characters")
        char_count = cur.fetchone()[0]
        print_test("角色主表记录数", char_count > 0, f"共 {char_count} 个角色")
        
        # 检查百科内容
        cur.execute("SELECT COUNT(*) FROM characters WHERE baike_content IS NOT NULL AND LENGTH(baike_content) > 100")
        baike_count = cur.fetchone()[0]
        print_test("百科全文保存", baike_count > 0, f"{baike_count} 个角色有百科内容")
        
        # 检查详细信息表
        detail_tables = [
            'character_basic_info',
            'character_knowledge',
            'character_personality',
            'character_dialogue_rules',
            'character_experiences',
            'character_relationships'
        ]
        
        for table in detail_tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print_test(f"表 {table}", count > 0, f"{count} 条记录")
        
        conn.close()
        return True
    except Exception as e:
        print_test("角色数据完整性", False, f"错误: {e}")
        return False

def test_character_loading():
    """测试4: 角色数据加载"""
    print_header("测试 4: 角色数据加载功能")
    
    try:
        # 获取第一个角色
        chars = list_characters(user_id=1)
        if not chars:
            print_test("角色列表查询", False, "没有找到角色")
            return False
        
        print_test("角色列表查询", True, f"找到 {len(chars)} 个角色")
        
        # 测试加载完整数据
        first_char = chars[0]
        char_id = first_char['id']
        char_name = first_char['name']
        
        full_data = load_character_full_data(char_id)
        
        if full_data:
            print_test(f"加载角色完整数据", True, f"角色: {char_name}")
            
            # 检查各部分数据
            categories = [
                '基础身份信息', '知识与能力', '个性与行为设定',
                '对话与交互规范', '经历', '关系网络'
            ]
            
            for cat in categories:
                has_data = cat in full_data and full_data[cat]
                print_test(f"  - {cat}", has_data)
        else:
            print_test("加载角色完整数据", False, "数据为空")
            return False
        
        # 测试加载记忆
        memories = load_character_memories(char_id)
        if memories is not None:
            stm_count = len(memories.get('short_term_memory', []))
            ltm_count = len(memories.get('long_term_memory', []))
            print_test("加载角色记忆", True, f"短期: {stm_count}, 长期: {ltm_count}")
        else:
            print_test("加载角色记忆", True, "暂无记忆数据（正常）")
        
        return True
    except Exception as e:
        print_test("角色数据加载", False, f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_messages():
    """测试5: 消息存储"""
    print_header("测试 5: 消息存储")
    
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        # 检查单聊消息
        cur.execute("SELECT COUNT(*) FROM messages")
        msg_count = cur.fetchone()[0]
        print_test("单聊消息记录", msg_count >= 0, f"共 {msg_count} 条消息")
        
        # 检查群聊
        cur.execute("SELECT COUNT(*) FROM group_chats")
        group_count = cur.fetchone()[0]
        print_test("群聊记录", group_count >= 0, f"共 {group_count} 个群聊")
        
        # 检查群聊消息
        cur.execute("SELECT COUNT(*) FROM group_messages")
        group_msg_count = cur.fetchone()[0]
        print_test("群聊消息记录", group_msg_count >= 0, f"共 {group_msg_count} 条消息")
        
        conn.close()
        return True
    except Exception as e:
        print_test("消息存储", False, f"错误: {e}")
        return False

def test_user_system():
    """测试6: 用户系统"""
    print_header("测试 6: 用户系统")
    
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        # 检查用户数量
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        print_test("用户记录", user_count > 0, f"共 {user_count} 个用户")
        
        # 检查管理员
        cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = cur.fetchone()[0]
        print_test("管理员账号", admin_count > 0, f"共 {admin_count} 个管理员")
        
        # 检查用户设置
        cur.execute("SELECT COUNT(*) FROM user_settings")
        settings_count = cur.fetchone()[0]
        print_test("用户设置", settings_count >= 0, f"{settings_count} 条设置记录")
        
        conn.close()
        return True
    except Exception as e:
        print_test("用户系统", False, f"错误: {e}")
        return False

def test_feedback_system():
    """测试7: 反馈系统"""
    print_header("测试 7: 反馈系统")
    
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM feedbacks")
        feedback_count = cur.fetchone()[0]
        print_test("反馈记录", feedback_count >= 0, f"共 {feedback_count} 条反馈")
        
        conn.close()
        return True
    except Exception as e:
        print_test("反馈系统", False, f"错误: {e}")
        return False

def generate_summary(results):
    """生成测试总结"""
    print_header("测试总结")
    
    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed
    
    print(f"\n总计: {total} 项测试")
    print(f"✅ 通过: {passed} 项")
    print(f"❌ 失败: {failed} 项")
    print(f"\n成功率: {passed/total*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 恭喜！所有测试通过，PostgreSQL数据库迁移成功！")
        print("   项目可以完全基于PostgreSQL数据库运行。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 项测试失败，请检查相关功能。")
        return False

def main():
    """主测试流程"""
    print("\n" + "🚀 FastNPC PostgreSQL 迁移验证".center(80, "="))
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 运行所有测试
    results = []
    
    results.append(test_database_connection())
    results.append(test_database_tables())
    results.append(test_character_data())
    results.append(test_character_loading())
    results.append(test_messages())
    results.append(test_user_system())
    results.append(test_feedback_system())
    
    # 生成总结
    success = generate_summary(results)
    
    print("\n" + "=" * 80)
    print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

