# -*- coding: utf-8 -*-
"""
调试脚本：检查数据库中的角色和群聊
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from fastnpc.api.auth import _get_conn, _return_conn, _row_to_dict
from fastnpc.config import USE_POSTGRESQL


def debug_database():
    """调试数据库，显示所有用户、角色和群聊"""
    print("=" * 60)
    print("FastNPC 数据库调试工具")
    print("=" * 60)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 1. 查询所有用户
        print("\n[1] 数据库中的所有用户:")
        print("-" * 60)
        cur.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY id")
        users = cur.fetchall()
        
        if not users:
            print("  ⚠️  没有找到任何用户！")
        else:
            for row in users:
                user_dict = _row_to_dict(row, cur)
                admin_flag = "👑 管理员" if user_dict['is_admin'] else "👤 普通用户"
                print(f"  ID: {user_dict['id']:<5} 用户名: {user_dict['username']:<20} {admin_flag}")
        
        # 2. 查询每个用户的角色
        print("\n[2] 数据库中的所有角色（按用户分组）:")
        print("-" * 60)
        
        for row in users:
            user_dict = _row_to_dict(row, cur)
            user_id = user_dict['id']
            username = user_dict['username']
            
            placeholder = "%s" if USE_POSTGRESQL else "?"
            cur.execute(
                f"SELECT id, name, created_at FROM characters WHERE user_id={placeholder} ORDER BY name",
                (user_id,)
            )
            chars = cur.fetchall()
            
            if chars:
                print(f"\n  用户: {username} (ID: {user_id}) - 共 {len(chars)} 个角色")
                for char_row in chars[:10]:  # 只显示前10个
                    char_dict = _row_to_dict(char_row, cur)
                    print(f"    - {char_dict['name']} (ID: {char_dict['id']})")
                if len(chars) > 10:
                    print(f"    ... 还有 {len(chars) - 10} 个角色")
            else:
                print(f"\n  用户: {username} (ID: {user_id}) - 没有角色")
        
        # 3. 查询每个用户的群聊
        print("\n[3] 数据库中的所有群聊（按用户分组）:")
        print("-" * 60)
        
        # 重新获取用户列表
        cur.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY id")
        users_for_groups = cur.fetchall()
        
        for row in users_for_groups:
            user_dict = _row_to_dict(row, cur)
            user_id = user_dict['id']
            username = user_dict['username']
            
            cur.execute(
                f"SELECT id, name, created_at FROM group_chats WHERE user_id={placeholder} ORDER BY name",
                (user_id,)
            )
            groups = cur.fetchall()
            
            if groups:
                # 先把所有群聊信息转换为字典
                groups_data = []
                for group_row in groups:
                    group_dict = _row_to_dict(group_row, cur)
                    groups_data.append(group_dict)
                
                print(f"\n  用户: {username} (ID: {user_id}) - 共 {len(groups_data)} 个群聊")
                
                # 然后查询每个群聊的成员数量
                for group_dict in groups_data:
                    cur.execute(
                        f"SELECT COUNT(*) as count FROM group_members WHERE group_id={placeholder}",
                        (group_dict['id'],)
                    )
                    member_count_row = cur.fetchone()
                    member_count = _row_to_dict(member_count_row, cur)['count'] if member_count_row else 0
                    
                    print(f"    - {group_dict['name']} (ID: {group_dict['id']}, {member_count} 个成员)")
            else:
                print(f"\n  用户: {username} (ID: {user_id}) - 没有群聊")
        
        # 4. 总结
        print("\n" + "=" * 60)
        print("总结:")
        print("-" * 60)
        
        cur.execute("SELECT COUNT(*) as count FROM users")
        user_count = _row_to_dict(cur.fetchone(), cur)['count']
        
        cur.execute("SELECT COUNT(*) as count FROM characters")
        char_count = _row_to_dict(cur.fetchone(), cur)['count']
        
        cur.execute("SELECT COUNT(*) as count FROM group_chats")
        group_count = _row_to_dict(cur.fetchone(), cur)['count']
        
        print(f"  总用户数: {user_count}")
        print(f"  总角色数: {char_count}")
        print(f"  总群聊数: {group_count}")
        
        # 5. 建议
        print("\n" + "=" * 60)
        print("💡 使用建议:")
        print("-" * 60)
        
        # 重新获取用户以查找管理员（避免游标问题）
        cur.execute("SELECT id, username, is_admin FROM users WHERE is_admin != 0 ORDER BY id")
        admin_users = cur.fetchall()
        
        if admin_users:
            for admin_row in admin_users:
                admin_dict = _row_to_dict(admin_row, cur)
                print(f"\n  找到管理员账号 '{admin_dict['username']}' (ID: {admin_dict['id']})")
                print(f"\n  现在可以运行测试用例生成脚本:")
                print(f"     python fastnpc/scripts/generate_test_cases_smart.py")
                print(f"\n  脚本会自动找到管理员账号并生成测试用例。")
        else:
            print("\n  ⚠️  未找到管理员账号")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _return_conn(conn)


if __name__ == "__main__":
    debug_database()

