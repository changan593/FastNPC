#!/usr/bin/env python3
"""测试用户删除功能（包含级联删除验证）"""

import sys
sys.path.insert(0, '/home/changan/MyProject/FastNPC')

from fastnpc.api.auth.core import create_user
from fastnpc.api.auth.users import delete_account, get_user_id_by_username
from fastnpc.api.auth.characters import get_or_create_character, list_characters
from fastnpc.api.auth.messages import add_message, list_messages
from fastnpc.api.auth.groups import create_group_chat, list_group_chats, add_group_member, add_group_message
from fastnpc.api.auth.feedbacks import create_feedback, list_feedbacks
from fastnpc.api.auth.db_utils import _get_conn, _return_conn


def test_cascade_delete():
    """测试级联删除功能"""
    print("=" * 60)
    print("测试用户删除的级联功能")
    print("=" * 60)
    
    # 1. 创建测试用户
    print("\n[步骤1] 创建测试用户...")
    try:
        test_username = "test_delete_cascade"
        test_user_id = create_user(test_username, "password123")
        print(f"✓ 测试用户创建成功: {test_username} (ID: {test_user_id})")
    except Exception as e:
        # 用户可能已存在，尝试获取ID
        test_user_id = get_user_id_by_username("test_delete_cascade")
        if test_user_id:
            print(f"⊙ 测试用户已存在: {test_username} (ID: {test_user_id})")
        else:
            print(f"✗ 创建用户失败: {e}")
            return False
    
    # 2. 创建测试角色
    print("\n[步骤2] 创建测试角色...")
    try:
        char_id = get_or_create_character(test_user_id, "测试角色1", "test", "test")
        print(f"✓ 测试角色创建成功: 测试角色1 (ID: {char_id})")
    except Exception as e:
        print(f"✗ 创建角色失败: {e}")
        return False
    
    # 3. 创建测试消息
    print("\n[步骤3] 创建测试消息...")
    try:
        add_message(test_user_id, char_id, "user", "测试消息1")
        add_message(test_user_id, char_id, "assistant", "测试回复1")
        print(f"✓ 测试消息创建成功")
    except Exception as e:
        print(f"✗ 创建消息失败: {e}")
        return False
    
    # 4. 创建测试群聊
    print("\n[步骤4] 创建测试群聊...")
    try:
        group_id = create_group_chat(test_user_id, "测试群聊")
        add_group_member(group_id, "character", char_id, "测试角色1")
        add_group_message(group_id, "user", test_user_id, "测试用户", "群聊测试消息")
        print(f"✓ 测试群聊创建成功 (ID: {group_id})")
    except Exception as e:
        print(f"✗ 创建群聊失败: {e}")
        return False
    
    # 5. 创建测试反馈
    print("\n[步骤5] 创建测试反馈...")
    try:
        feedback_id = create_feedback(test_user_id, "测试反馈", "这是测试内容", None)
        print(f"✓ 测试反馈创建成功 (ID: {feedback_id})")
    except Exception as e:
        print(f"✗ 创建反馈失败: {e}")
        return False
    
    # 6. 验证数据已创建
    print("\n[步骤6] 验证测试数据...")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 检查角色
        cur.execute("SELECT COUNT(*) FROM characters WHERE user_id=%s", (test_user_id,))
        char_count = cur.fetchone()[0]
        print(f"  • 角色数量: {char_count}")
        
        # 检查消息
        cur.execute("SELECT COUNT(*) FROM messages WHERE user_id=%s", (test_user_id,))
        msg_count = cur.fetchone()[0]
        print(f"  • 消息数量: {msg_count}")
        
        # 检查群聊
        cur.execute("SELECT COUNT(*) FROM group_chats WHERE user_id=%s", (test_user_id,))
        group_count = cur.fetchone()[0]
        print(f"  • 群聊数量: {group_count}")
        
        # 检查群聊成员
        cur.execute("SELECT COUNT(*) FROM group_members WHERE group_id=%s", (group_id,))
        member_count = cur.fetchone()[0]
        print(f"  • 群聊成员数量: {member_count}")
        
        # 检查群聊消息
        cur.execute("SELECT COUNT(*) FROM group_messages WHERE group_id=%s", (group_id,))
        group_msg_count = cur.fetchone()[0]
        print(f"  • 群聊消息数量: {group_msg_count}")
        
        # 检查反馈
        cur.execute("SELECT COUNT(*) FROM feedbacks WHERE user_id=%s", (test_user_id,))
        feedback_count = cur.fetchone()[0]
        print(f"  • 反馈数量: {feedback_count}")
        
        if char_count == 0 or msg_count == 0 or group_count == 0 or feedback_count == 0:
            print("✗ 测试数据创建不完整")
            return False
        
        print("✓ 所有测试数据创建完成")
        
    finally:
        _return_conn(conn)
    
    # 7. 执行用户删除
    print("\n[步骤7] 删除用户账户...")
    print("⚠️  即将执行CASCADE删除，所有相关数据将被删除...")
    input("按Enter继续...")
    
    try:
        delete_account(test_user_id)
        print(f"✓ 用户删除成功")
    except Exception as e:
        print(f"✗ 用户删除失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. 验证级联删除
    print("\n[步骤8] 验证级联删除...")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 检查用户
        cur.execute("SELECT COUNT(*) FROM users WHERE id=%s", (test_user_id,))
        user_count = cur.fetchone()[0]
        print(f"  • 用户数量: {user_count} (应为0)")
        
        # 检查角色
        cur.execute("SELECT COUNT(*) FROM characters WHERE user_id=%s", (test_user_id,))
        char_count = cur.fetchone()[0]
        print(f"  • 角色数量: {char_count} (应为0)")
        
        # 检查消息
        cur.execute("SELECT COUNT(*) FROM messages WHERE user_id=%s", (test_user_id,))
        msg_count = cur.fetchone()[0]
        print(f"  • 消息数量: {msg_count} (应为0)")
        
        # 检查群聊
        cur.execute("SELECT COUNT(*) FROM group_chats WHERE user_id=%s", (test_user_id,))
        group_count = cur.fetchone()[0]
        print(f"  • 群聊数量: {group_count} (应为0)")
        
        # 检查群聊成员
        cur.execute("SELECT COUNT(*) FROM group_members WHERE group_id=%s", (group_id,))
        member_count = cur.fetchone()[0]
        print(f"  • 群聊成员数量: {member_count} (应为0)")
        
        # 检查群聊消息
        cur.execute("SELECT COUNT(*) FROM group_messages WHERE group_id=%s", (group_id,))
        group_msg_count = cur.fetchone()[0]
        print(f"  • 群聊消息数量: {group_msg_count} (应为0)")
        
        # 检查反馈
        cur.execute("SELECT COUNT(*) FROM feedbacks WHERE user_id=%s", (test_user_id,))
        feedback_count = cur.fetchone()[0]
        print(f"  • 反馈数量: {feedback_count} (应为0)")
        
        # 验证所有数据都已删除
        if all([
            user_count == 0,
            char_count == 0,
            msg_count == 0,
            group_count == 0,
            member_count == 0,
            group_msg_count == 0,
            feedback_count == 0
        ]):
            print("\n✅ 级联删除验证成功！所有相关数据已被自动删除！")
            return True
        else:
            print("\n✗ 级联删除验证失败：部分数据未被删除")
            return False
            
    finally:
        _return_conn(conn)


if __name__ == "__main__":
    print("\n🧪 开始测试用户删除功能...\n")
    
    success = test_cascade_delete()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试通过！用户删除功能工作正常！")
        print("\n✅ 确认以下功能正常：")
        print("  1. 删除用户时自动删除所有角色")
        print("  2. 删除用户时自动删除所有消息")
        print("  3. 删除用户时自动删除所有群聊")
        print("  4. 删除群聊时自动删除群聊成员和消息")
        print("  5. 删除用户时自动删除所有反馈")
    else:
        print("❌ 测试失败！请检查错误信息")
    print("=" * 60)

