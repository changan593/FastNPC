#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速查看角色的来源信息量
"""

import sys
from fastnpc.api.auth import _get_conn, load_character_full_data

def main():
    if len(sys.argv) > 1:
        # 指定角色名
        search_name = sys.argv[1]
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM characters WHERE name LIKE %s", (f'%{search_name}%',))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            print(f"未找到包含 '{search_name}' 的角色")
            return
        
        for row in rows:
            char_id, name = row[0], row[1]
            show_character(char_id, name)
    else:
        # 显示所有角色
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM characters ORDER BY created_at DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()
        
        print("=" * 80)
        print("最近10个角色的来源信息量".center(80))
        print("=" * 80)
        
        for row in rows:
            char_id, name = row[0], row[1]
            show_character_brief(char_id, name)

def show_character(char_id, name):
    print("\n" + "=" * 80)
    print(f"角色: {name} (ID: {char_id})")
    print("=" * 80)
    
    data = load_character_full_data(char_id)
    if not data:
        print("❌ 无法加载角色数据")
        return
    
    source_info = data.get('来源信息', {})
    if not source_info:
        print("❌ 没有来源信息")
        return
    
    print(f"\n唯一标识: {source_info.get('唯一标识', '无')}")
    print(f"链接: {source_info.get('链接', '无')}")
    
    info_size = source_info.get('来源信息量', 0)
    print(f"来源信息量: {info_size:,} 字符")
    
    # 判断状态
    if info_size > 10000:
        status = "✅ 优秀"
        desc = "爬虫成功抓取了大量内容"
    elif info_size > 1000:
        status = "✅ 良好"
        desc = "爬虫成功抓取了基本内容"
    elif info_size > 100:
        status = "⚠️  一般"
        desc = "内容较少，可能抓取不完整"
    else:
        status = "❌ 失败"
        desc = "几乎没有内容，爬虫可能失败"
    
    print(f"\n状态: {status}")
    print(f"说明: {desc}")

def show_character_brief(char_id, name):
    data = load_character_full_data(char_id)
    if not data:
        print(f"  ID:{char_id:3d} | {name:35s} | ❌ 无法加载")
        return
    
    source_info = data.get('来源信息', {})
    info_size = source_info.get('来源信息量', 0) if source_info else 0
    
    if info_size > 10000:
        status = "✅ 优秀"
    elif info_size > 1000:
        status = "✅ 良好"
    elif info_size > 100:
        status = "⚠️  一般"
    else:
        status = "❌ 失败"
    
    print(f"  ID:{char_id:3d} | {name:35s} | {info_size:6,} 字符 | {status}")

if __name__ == "__main__":
    main()

