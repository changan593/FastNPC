#!/usr/bin/env python3
"""
数据库迁移脚本：添加测试用例管理相关表和字段
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from fastnpc.api.auth.db_utils import _get_conn, _return_conn
from fastnpc.config import USE_POSTGRESQL


def migrate():
    """执行数据库迁移"""
    conn = _get_conn()
    
    try:
        cur = conn.cursor()
        
        print("=" * 80)
        print("开始数据库迁移：添加测试用例管理功能")
        print("=" * 80)
        
        # 1. 为 group_chats 表添加 is_test_case 字段
        print("\n[1/3] 为 group_chats 表添加 is_test_case 字段...")
        try:
            if USE_POSTGRESQL:
                cur.execute("""
                    ALTER TABLE group_chats 
                    ADD COLUMN IF NOT EXISTS is_test_case BOOLEAN DEFAULT FALSE
                """)
            else:
                # SQLite - 先检查列是否存在
                cur.execute("PRAGMA table_info(group_chats)")
                columns = [row[1] for row in cur.fetchall()]
                if 'is_test_case' not in columns:
                    cur.execute("""
                        ALTER TABLE group_chats 
                        ADD COLUMN is_test_case INTEGER DEFAULT 0
                    """)
            conn.commit()
            print("   ✓ 成功添加 is_test_case 字段")
        except Exception as e:
            print(f"   ⚠ 字段可能已存在: {e}")
            conn.rollback()
        
        # 2. 创建 test_cases 表
        print("\n[2/3] 创建 test_cases 表...")
        try:
            if USE_POSTGRESQL:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_cases (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(50) NOT NULL,
                        category VARCHAR(100) NOT NULL,
                        target_type VARCHAR(50) NOT NULL,
                        target_id VARCHAR(200) NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        
                        -- 测试内容
                        test_content JSONB NOT NULL,
                        expected_behavior TEXT,
                        
                        -- 测试配置
                        test_config JSONB,
                        
                        -- 版本管理
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建索引
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_target ON test_cases(target_type, target_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_active ON test_cases(is_active)")
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version VARCHAR(50) NOT NULL,
                        category VARCHAR(100) NOT NULL,
                        target_type VARCHAR(50) NOT NULL,
                        target_id VARCHAR(200) NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        
                        test_content TEXT NOT NULL,
                        expected_behavior TEXT,
                        test_config TEXT,
                        
                        is_active INTEGER DEFAULT 1,
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_target ON test_cases(target_type, target_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_active ON test_cases(is_active)")
            
            conn.commit()
            print("   ✓ 成功创建 test_cases 表")
        except Exception as e:
            print(f"   ⚠ 表可能已存在: {e}")
            conn.rollback()
        
        # 3. 创建 test_executions 表
        print("\n[3/3] 创建 test_executions 表...")
        try:
            if USE_POSTGRESQL:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_executions (
                        id SERIAL PRIMARY KEY,
                        test_case_id INTEGER REFERENCES test_cases(id),
                        prompt_template_id INTEGER REFERENCES prompt_templates(id),
                        
                        -- 执行信息
                        execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        duration_ms INTEGER,
                        
                        -- 测试结果
                        llm_response TEXT,
                        evaluation_result JSONB,
                        passed BOOLEAN,
                        score DECIMAL(5,2),
                        
                        -- 评估详情
                        evaluator_prompt_id INTEGER REFERENCES prompt_templates(id),
                        evaluation_feedback TEXT,
                        
                        -- 元数据
                        metadata JSONB,
                        executed_by INTEGER
                    )
                """)
                
                # 创建索引
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_test_case ON test_executions(test_case_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_prompt ON test_executions(prompt_template_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_time ON test_executions(execution_time)")
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_case_id INTEGER,
                        prompt_template_id INTEGER,
                        
                        execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        duration_ms INTEGER,
                        
                        llm_response TEXT,
                        evaluation_result TEXT,
                        passed INTEGER,
                        score REAL,
                        
                        evaluator_prompt_id INTEGER,
                        evaluation_feedback TEXT,
                        
                        metadata TEXT,
                        executed_by INTEGER,
                        
                        FOREIGN KEY (test_case_id) REFERENCES test_cases(id),
                        FOREIGN KEY (prompt_template_id) REFERENCES prompt_templates(id),
                        FOREIGN KEY (evaluator_prompt_id) REFERENCES prompt_templates(id)
                    )
                """)
                
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_test_case ON test_executions(test_case_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_prompt ON test_executions(prompt_template_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_time ON test_executions(execution_time)")
            
            conn.commit()
            print("   ✓ 成功创建 test_executions 表")
        except Exception as e:
            print(f"   ⚠ 表可能已存在: {e}")
            conn.rollback()
        
        print("\n" + "=" * 80)
        print("✓ 数据库迁移完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    
    finally:
        _return_conn(conn)


if __name__ == '__main__':
    migrate()

