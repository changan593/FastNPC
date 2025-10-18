#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库中已有角色的avatar_url字段
"""
import os
import sys
sys.path.insert(0, '.')

from fastnpc.config import BASE_DIR

# 不导入需要psycopg2的模块，直接操作数据库
print("正在查找数据库...")

# 查找数据库文件
possible_db_paths = [
    BASE_DIR / "fastnpc.db",
    BASE_DIR / "data" / "fastnpc.db",
    BASE_DIR / "Characters" / "fastnpc.db",
]

db_path = None
for path in possible_db_paths:
    if path.exists():
        db_path = path
        break

if not db_path:
    print("❌ 找不到数据库文件")
    print("可能的位置：", [str(p) for p in possible_db_paths])
    sys.exit(1)

print(f"✅ 找到数据库: {db_path}")

import sqlite3
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 检查avatar_url字段是否存在
cur.execute("PRAGMA table_info(characters)")
columns = [row[1] for row in cur.fetchall()]
print(f"\n当前字段: {columns}")

if 'avatar_url' not in columns:
    print("\n⚠️  avatar_url 字段不存在，正在添加...")
    cur.execute("ALTER TABLE characters ADD COLUMN avatar_url TEXT")
    conn.commit()
    print("✅ 字段已添加")

# 查询所有角色
cur.execute("SELECT id, name, avatar_url FROM characters ORDER BY updated_at DESC")
rows = cur.fetchall()

print(f"\n找到 {len(rows)} 个角色：")
print("-" * 100)

avatars_dir = BASE_DIR / "Avatars"
print(f"头像目录: {avatars_dir}")
print()

if avatars_dir.exists():
    avatar_files = [f for f in os.listdir(avatars_dir) if f.endswith('.jpg')]
    print(f"找到 {len(avatar_files)} 个头像文件：")
    for f in avatar_files:
        print(f"  - {f}")
    print()
else:
    avatar_files = []
    print("⚠️  头像目录不存在")
    print()

updated = 0
for row in rows:
    char_id = row['id']
    name = row['name']
    current_avatar = row['avatar_url']
    
    print(f"ID {char_id:3d} | {name:40s} | 当前: {current_avatar or 'NULL'}")
    
    # 如果没有avatar_url，尝试从文件系统找
    if not current_avatar:
        # 尝试多种可能的文件名
        possible_names = [
            f"user_5_{name}.jpg",  # 假设user_id=5
            f"user_1_{name}.jpg",
            f"{name}.jpg",
        ]
        
        for possible_name in possible_names:
            if possible_name in avatar_files:
                new_url = f"/avatars/{possible_name}"
                cur.execute("UPDATE characters SET avatar_url = ? WHERE id = ?", (new_url, char_id))
                conn.commit()
                print(f"       ✅ 已更新为: {new_url}")
                updated += 1
                break

print()
print(f"共更新了 {updated} 个角色的头像URL")
conn.close()

print("\n✅ 完成！请刷新浏览器页面。")

