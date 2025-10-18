# -*- coding: utf-8 -*-
"""
数据库表结构检查工具

显示所有表和字段信息
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from fastnpc.api.auth import _get_conn, _return_conn
from fastnpc.config import USE_POSTGRESQL


def inspect_database():
    """检查数据库结构"""
    print("=" * 80)
    print("FastNPC 数据库结构检查")
    print("=" * 80)
    print(f"数据库类型: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
    print()
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        if USE_POSTGRESQL:
            # PostgreSQL: 查询所有表
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            print(f"找到 {len(tables)} 个表:\n")
            
            for table_name in tables:
                print(f"📋 表: {table_name}")
                print("-" * 80)
                
                # 查询表的字段信息
                cur.execute("""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cur.fetchall()
                
                for col in columns:
                    col_name, col_type, nullable, default = col
                    null_str = "NULL" if nullable == 'YES' else "NOT NULL"
                    default_str = f"DEFAULT {default}" if default else ""
                    print(f"  • {col_name:<30} {col_type:<20} {null_str:<10} {default_str}")
                
                print()
        
        else:
            # SQLite: 查询所有表
            cur.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            print(f"找到 {len(tables)} 个表:\n")
            
            for table_name in tables:
                print(f"📋 表: {table_name}")
                print("-" * 80)
                
                # 查询表的字段信息
                cur.execute(f"PRAGMA table_info({table_name})")
                columns = cur.fetchall()
                
                for col in columns:
                    cid, col_name, col_type, notnull, default_val, pk = col
                    null_str = "NOT NULL" if notnull else "NULL"
                    pk_str = " [PRIMARY KEY]" if pk else ""
                    default_str = f"DEFAULT {default_val}" if default_val else ""
                    print(f"  • {col_name:<30} {col_type:<20} {null_str:<10} {default_str}{pk_str}")
                
                print()
        
        print("=" * 80)
        print("✓ 检查完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _return_conn(conn)


if __name__ == "__main__":
    inspect_database()

