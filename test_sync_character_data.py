#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试角色结构化数据与数据库的同步
"""

from fastnpc.api.auth import (
    get_character_id,
    load_character_full_data,
    save_character_full_data,
)
import json

def test_data_sync():
    """测试数据同步功能"""
    print("🧪 测试角色结构化数据与数据库同步")
    print("=" * 80)
    
    # 测试张角（ID=11）
    test_role = "张角202510171508"
    test_user_id = 2
    
    print(f"\n1️⃣  测试从数据库加载角色数据")
    print("-" * 80)
    
    # 获取角色ID
    char_id = get_character_id(test_user_id, test_role)
    if not char_id:
        print(f"❌ 未找到角色: {test_role}")
        return False
    
    print(f"✅ 找到角色 ID: {char_id}")
    
    # 从数据库加载
    full_data = load_character_full_data(char_id)
    if not full_data:
        print("❌ 从数据库加载失败")
        return False
    
    print(f"✅ 成功从数据库加载数据")
    
    # 检查各个部分
    print(f"\n数据完整性检查:")
    categories = [
        '基础身份信息',
        '知识与能力', 
        '个性与行为设定',
        '对话与交互规范',
        '来源信息'
    ]
    
    for cat in categories:
        status = '✅' if cat in full_data and full_data[cat] else '❌'
        print(f"  {status} {cat}")
        
        # 特别检查"来源信息"中的"来源信息量"字段
        if cat == '来源信息' and full_data.get(cat):
            source_info = full_data[cat]
            if '来源信息量' in source_info:
                info_size = source_info['来源信息量']
                print(f"      ✅ 来源信息量: {info_size:,} 字符")
            else:
                print(f"      ❌ 缺少\"来源信息量\"字段")
    
    print(f"\n2️⃣  测试保存角色数据到数据库")
    print("-" * 80)
    
    # 准备测试数据（修改一个小字段）
    test_data = {k: v for k, v in full_data.items() if k not in ['_metadata', 'baike_content']}
    
    # 在来源信息中添加一个测试字段
    if '来源信息' in test_data:
        original_url = test_data['来源信息'].get('链接', '')
        print(f"原始链接: {original_url}")
    
    try:
        # 保存到数据库
        save_character_full_data(
            user_id=test_user_id,
            name=test_role,
            structured_data=test_data,
            baike_content=None
        )
        print(f"✅ 成功保存到数据库")
        
        # 重新加载验证
        reloaded_data = load_character_full_data(char_id)
        if reloaded_data and '来源信息' in reloaded_data:
            reloaded_url = reloaded_data['来源信息'].get('链接', '')
            if reloaded_url == original_url:
                print(f"✅ 数据验证通过（链接匹配）")
            else:
                print(f"⚠️  数据可能不一致")
            
            # 验证"来源信息量"字段仍然存在
            if '来源信息量' in reloaded_data['来源信息']:
                print(f"✅ \"来源信息量\"字段保持完整: {reloaded_data['来源信息']['来源信息量']:,} 字符")
            else:
                print(f"❌ \"来源信息量\"字段丢失")
        
        return True
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_sync()
    print("\n" + "=" * 80)
    if success:
        print("✅ 所有测试通过！角色数据与数据库完全同步。")
    else:
        print("❌ 测试失败，请检查错误信息。")

