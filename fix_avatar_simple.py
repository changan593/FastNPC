#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据库修复脚本（不依赖项目模块）
"""
import os
import sqlite3
from pathlib import Path

# 查找数据库
base_dir = Path(__file__).parent
possible_paths = [
    base_dir / "fastnpc.db",
    base_dir / "data" / "fastnpc.db",
    base_dir / "Characters" / "fastnpc.db",
    Path.home() / ".fastnpc" / "fastnpc.db",
]

db_path = None
for p in possible_paths:
    if p.exists():
        db_path = p
        break

if not db_path:
    print("找不到数据库，尝试查找所有.db文件：")
    for p in base_dir.rglob("*.db"):
        print(f"  {p}")
        if "fastnpc" in p.name.lower() or "characters" in str(p).lower():
            db_path = p
            break

if not db_path:
    print("❌ 找不到数据库文件")
    exit(1)

print(f"✅ 数据库: {db_path}")

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 检查表结构
print("\n检查表结构...")
cur.execute("PRAGMA table_info(characters)")
cols = {row[1]: row[2] for row in cur.fetchall()}
print(f"字段: {list(cols.keys())}")

if 'avatar_url' not in cols:
    print("添加avatar_url字段...")
    cur.execute("ALTER TABLE characters ADD COLUMN avatar_url TEXT")
    conn.commit()

# 查询角色
cur.execute("SELECT id, name, avatar_url FROM characters ORDER BY id DESC LIMIT 10")
print(f"\n最近10个角色：")
print("-" * 80)
for row in cur.fetchall():
    print(f"ID:{row['id']:3d} | {row['name']:35s} | {row['avatar_url'] or 'NULL'}")

# 查找头像文件
avatars_dir = base_dir / "Avatars"
if avatars_dir.exists():
    files = list(avatars_dir.glob("*.jpg"))
    print(f"\n✅ Avatars目录: {avatars_dir}")
    print(f"找到 {len(files)} 个文件:")
    for f in files:
        print(f"  {f.name}")
    
    # 修复
    print("\n开始修复...")
    cur.execute("SELECT id, name, avatar_url FROM characters")
    for row in cur.fetchall():
        if row['avatar_url']:
            continue
        # 尝试匹配
        name = row['name']
        for f in files:
            if name in f.name:
                new_url = f"/avatars/{f.name}"
                cur.execute("UPDATE characters SET avatar_url=? WHERE id=?", (new_url, row['id']))
                print(f"  ✅ {name} -> {new_url}")
    conn.commit()
else:
    print(f"\n⚠️  Avatars目录不存在: {avatars_dir}")

conn.close()
print("\n✅ 完成！")

