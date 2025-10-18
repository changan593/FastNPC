# -*- coding: utf-8 -*-
"""
批量创建测试角色和群聊的辅助脚本

使用说明：
1. 确保已启动 FastNPC 服务器
2. 修改下面的 ADMIN_USERNAME 为你的管理员账号
3. 运行脚本: python fastnpc/scripts/create_test_characters.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import time

# 测试群聊配置（与 generate_test_cases.py 保持一致）
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

# ======== 配置区域 ========
ADMIN_USERNAME = "admin"  # 修改为你的管理员账号用户名
# =========================


def main():
    """主函数：使用 FastNPC API 创建角色和群聊"""
    from fastnpc.api.auth import get_user_id_by_username, get_or_create_character, create_group_chat, add_group_member
    
    print("=" * 60)
    print("FastNPC 测试角色和群聊批量创建工具")
    print("=" * 60)
    
    # 获取管理员用户ID
    user_id = get_user_id_by_username(ADMIN_USERNAME)
    if not user_id:
        print(f"\n❌ 错误: 用户 '{ADMIN_USERNAME}' 不存在")
        print(f"请修改脚本中的 ADMIN_USERNAME 为你的管理员账号")
        return
    
    print(f"\n✓ 找到用户: {ADMIN_USERNAME} (ID: {user_id})")
    
    # 1. 创建所有角色
    print("\n[1/2] 创建角色...")
    all_characters = set()
    for members in TEST_GROUPS.values():
        all_characters.update(members)
    
    created_chars = 0
    existing_chars = 0
    
    for char_name in sorted(all_characters):
        try:
            # get_or_create_character 会自动处理已存在的角色
            char_id = get_or_create_character(user_id, char_name)
            
            # 检查是否是新创建的（简单判断）
            # 这里假设如果创建成功就是新的
            print(f"  ✓ {char_name} (ID: {char_id})")
            created_chars += 1
        except Exception as e:
            print(f"  ✗ {char_name}: {e}")
    
    print(f"\n  总计: {created_chars} 个角色已就绪")
    
    # 2. 创建群聊并添加成员
    print("\n[2/2] 创建群聊...")
    created_groups = 0
    
    for group_name, members in TEST_GROUPS.items():
        try:
            # 创建群聊
            group_id = create_group_chat(user_id, group_name)
            print(f"  ✓ {group_name} (ID: {group_id})")
            
            # 添加成员
            for member_name in members:
                try:
                    # 获取角色ID
                    char_id = get_or_create_character(user_id, member_name)
                    # 添加到群聊
                    add_group_member(group_id, 'character', member_name, char_id)
                    print(f"    - 添加成员: {member_name}")
                except Exception as e:
                    print(f"    ✗ 添加成员失败 {member_name}: {e}")
            
            created_groups += 1
        except Exception as e:
            # 群聊可能已存在
            if "已存在" in str(e) or "duplicate" in str(e).lower():
                print(f"  ⚠ {group_name}: 已存在")
            else:
                print(f"  ✗ {group_name}: {e}")
    
    print(f"\n  总计: {created_groups} 个群聊已创建")
    
    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)
    print("\n📝 后续步骤:")
    print("1. 为角色生成结构化信息（在Web界面中逐个创建）")
    print("2. 运行测试用例生成脚本:")
    print("   python fastnpc/scripts/generate_test_cases.py")
    print("3. 在Web界面中查看和管理测试用例")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

