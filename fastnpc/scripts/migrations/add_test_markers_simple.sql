-- 测试用例管理系统数据库迁移脚本
-- 可以直接用 psql 执行

-- 1. 为 group_chats 表添加 is_test_case 字段
ALTER TABLE group_chats ADD COLUMN IF NOT EXISTS is_test_case BOOLEAN DEFAULT FALSE;

-- 2. 创建 test_cases 表
CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(200) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    test_content JSONB NOT NULL,
    expected_behavior TEXT,
    test_config JSONB,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category);
CREATE INDEX IF NOT EXISTS idx_test_cases_target ON test_cases(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_active ON test_cases(is_active);

-- 3. 创建 test_executions 表
CREATE TABLE IF NOT EXISTS test_executions (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER REFERENCES test_cases(id),
    prompt_template_id INTEGER REFERENCES prompt_templates(id),
    
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    
    llm_response TEXT,
    evaluation_result JSONB,
    passed BOOLEAN,
    score DECIMAL(5,2),
    
    evaluator_prompt_id INTEGER REFERENCES prompt_templates(id),
    evaluation_feedback TEXT,
    
    metadata JSONB,
    executed_by INTEGER
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_test_executions_test_case ON test_executions(test_case_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_prompt ON test_executions(prompt_template_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_time ON test_executions(execution_time);

