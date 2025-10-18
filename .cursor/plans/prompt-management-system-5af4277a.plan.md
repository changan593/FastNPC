<!-- 5af4277a-bbc3-41af-a90a-bbeb3c38ffe7 67576cff-d527-413f-976a-f6c34012ba0b -->
# 测试用例管理和评估系统实施计划

## 阶段一：数据库设计与迁移 (1.5小时)

### 1.1 角色/群聊星标功能

**数据库迁移脚本**: `fastnpc/scripts/migrations/add_test_markers.py`

```sql
-- 为角色添加星标（通过 structured.json 的 metadata 字段）
-- 为群聊表添加 is_test_case 字段
ALTER TABLE groups ADD COLUMN is_test_case BOOLEAN DEFAULT FALSE;
```

### 1.2 测试用例表结构

**新建表**: `test_cases` (存储测试对话和场景)

```sql
CREATE TABLE test_cases (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,  -- SINGLE_CHAT, GROUP_CHAT, STRUCTURED_GEN等
    target_type VARCHAR(50) NOT NULL, -- CHARACTER, GROUP
    target_id VARCHAR(200) NOT NULL,  -- 角色ID或群聊ID
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 测试内容
    test_content JSONB NOT NULL,  -- 存储测试对话序列或输入数据
    expected_behavior TEXT,        -- 期望行为描述
    
    -- 测试配置
    test_config JSONB,  -- 用户设置覆盖（如记忆预算、群聊轮次等）
    
    -- 版本管理
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_category (category),
    INDEX idx_target (target_type, target_id),
    INDEX idx_active (is_active)
);
```

### 1.3 测试执行结果表

**新建表**: `test_executions` (记录每次测试运行)

```sql
CREATE TABLE test_executions (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER REFERENCES test_cases(id),
    prompt_template_id INTEGER REFERENCES prompt_templates(id),
    
    -- 执行信息
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    
    -- 测试结果
    llm_response TEXT,           -- LLM实际输出
    evaluation_result JSONB,     -- 评估结果
    passed BOOLEAN,
    score DECIMAL(5,2),          -- 0-100分
    
    -- 评估详情
    evaluator_prompt_id INTEGER REFERENCES prompt_templates(id),
    evaluation_feedback TEXT,    -- 评估器的详细反馈
    
    -- 元数据
    metadata JSONB,
    executed_by INTEGER
);
```

### 1.4 评估提示词类别

**新增 PromptCategory**: 在 `fastnpc/prompt_manager.py` 中添加评估类别

```python
EVALUATOR_STRUCTURED_GEN = "EVALUATOR_STRUCTURED_GEN"
EVALUATOR_BRIEF_GEN = "EVALUATOR_BRIEF_GEN"
EVALUATOR_SINGLE_CHAT = "EVALUATOR_SINGLE_CHAT"
EVALUATOR_GROUP_CHAT = "EVALUATOR_GROUP_CHAT"
EVALUATOR_STM_COMPRESSION = "EVALUATOR_STM_COMPRESSION"
EVALUATOR_LTM_INTEGRATION = "EVALUATOR_LTM_INTEGRATION"
EVALUATOR_GROUP_MODERATOR = "EVALUATOR_GROUP_MODERATOR"
```

**命令**: `python fastnpc/scripts/migrations/add_test_markers.py`

---

## 阶段二：后端API开发 (3小时)

### 2.1 角色/群聊星标管理

**文件**: `fastnpc/api/routes/character_routes.py`

新增端点:

```python
@router.post('/api/characters/{persona_id}/toggle-test-marker')
async def toggle_character_test_marker(persona_id: str, request: Request)
    # 读取 structured.json，修改 metadata.is_test_case
    # 返回更新后的状态
```

**文件**: `fastnpc/api/routes/group_routes.py`

新增端点:

```python
@router.post('/api/groups/{group_id}/toggle-test-marker')
async def toggle_group_test_marker(group_id: str, request: Request)
    # 更新 groups 表的 is_test_case 字段
```

### 2.2 测试用例管理API

**新文件**: `fastnpc/api/routes/test_case_routes.py`

```python
@router.get('/admin/test-cases')  # 列出测试用例（支持筛选）

@router.post('/admin/test-cases')  # 创建测试用例

@router.get('/admin/test-cases/{id}')  # 获取详情

@router.put('/admin/test-cases/{id}')  # 更新（创建新版本）

@router.post('/admin/test-cases/{id}/activate')  # 激活版本

@router.get('/admin/test-cases/versions')  # 获取版本历史
```

### 2.3 状态恢复API

**文件**: `fastnpc/api/routes/test_case_routes.py`

```python
@router.post('/admin/test-cases/reset-character/{persona_id}')
async def reset_character_state(persona_id: str, request: Request)
    # 1. 删除 Chat_Sessions/{persona_id}/ 下所有对话文件
    # 2. 清空 Redis 中的短期记忆
    # 3. 清空数据库中的长期记忆
    # 4. 返回成功状态

@router.post('/admin/test-cases/reset-group/{group_id}')
async def reset_group_state(group_id: str, request: Request)
    # 类似角色重置，但针对群聊
```

### 2.4 测试执行API

**文件**: `fastnpc/api/routes/test_case_routes.py`

```python
@router.post('/admin/test-cases/{id}/execute')
async def execute_test_case(id: int, request: Request)
    # 1. 加载测试用例
    # 2. 根据 category 调用对应的功能模块
    # 3. 收集实际输出
    # 4. 调用评估器评估
    # 5. 保存到 test_executions
    # 6. 返回结果

@router.post('/admin/test-cases/batch-execute')
async def batch_execute_tests(request: Request)
    # 批量执行多个测试用例
    # 支持按 category、target_id 筛选
    # 返回汇总报告
```

### 2.5 测试报告API

**文件**: `fastnpc/api/routes/test_case_routes.py`

```python
@router.get('/admin/test-reports')
async def get_test_reports(request: Request)
    # 查询 test_executions，生成报告
    # 支持按时间、提示词版本、测试用例筛选
    # 返回统计数据和详细结果
```

### 2.6 评估提示词管理

**文件**: `fastnpc/api/routes/prompt_routes.py`

```python
# 复用现有的提示词管理API
# 评估提示词作为特殊 category 存储
# 支持版本管理和编辑
```

---

## 阶段三：测试数据自动生成 (4小时)

### 3.1 生成器核心类

**新文件**: `fastnpc/scripts/test_data_generator.py`

```python
class TestDataGenerator:
    def generate_character_chat_tests(self, persona_id: str) -> List[Dict]:
        """根据角色特点生成单聊测试对话"""
        # 1. 读取角色的 structured.json
        # 2. 分析角色特点（职业、性格、时代背景）
        # 3. 生成5-10组符合角色特点的测试对话
        # 示例：李白 -> 诗词创作、饮酒、游历话题
        
    def generate_group_chat_tests(self, group_id: str, members: List[str]) -> List[Dict]:
        """根据群聊成员特点生成群聊测试场景"""
        # 1. 分析群聊主题（如"政治局"、"诗词局"）
        # 2. 生成符合群聊氛围的话题
        # 3. 设计用户发言引导对话
        # 示例：政治局 -> 国际关系、政策讨论
        
    def generate_structured_gen_tests(self, persona_id: str) -> Dict:
        """为结构化生成准备测试数据"""
        # 使用角色的百科全文作为输入
        # 针对8大类分别生成测试用例
```

### 3.2 测试用例生成脚本

**新文件**: `fastnpc/scripts/generate_initial_test_cases.py`

```python
# 针对50个角色生成测试用例
CHARACTERS = [
    "特朗普", "普京", "泽连斯基",
    "李白", "杜甫", "苏轼", "李商隐", "李清照",
    # ... 其余角色
]

# 针对11个群聊生成测试用例
GROUPS = [
    {"name": "政治局", "members": ["特朗普", "普京", "泽连斯基"]},
    {"name": "诗词局", "members": ["李白", "杜甫", "苏轼", "李商隐", "李清照"]},
    # ... 其余群聊
]

def main():
    generator = TestDataGenerator()
    
    # 生成单聊测试
    for char in CHARACTERS:
        tests = generator.generate_character_chat_tests(char)
        save_test_cases(tests, version="1.0.0")
    
    # 生成群聊测试
    for group in GROUPS:
        tests = generator.generate_group_chat_tests(group["name"], group["members"])
        save_test_cases(tests, version="1.0.0")
```

**命令**: `python fastnpc/scripts/generate_initial_test_cases.py`

### 3.3 评估提示词生成

**新文件**: `fastnpc/scripts/generate_evaluator_prompts.py`

为每个提示词类别设计评估提示词：

```python
EVALUATORS = {
    "EVALUATOR_STRUCTURED_GEN": """
你是专业的角色设定评估专家。
任务：评估结构化角色生成的质量。

评估维度：
1. 信息完整性（20分）：是否包含所有必需字段
2. 信息准确性（25分）：是否与原文事实一致
3. 格式规范性（15分）：JSON格式是否正确
4. 内容合理性（20分）：推测内容是否符合逻辑
5. 表达质量（20分）：语言是否自然流畅

输出格式（严格JSON）：
{
  "overall_passed": true/false,
  "score": 85,
  "dimension_scores": {...},
  "feedback": "详细评价..."
}
""",
    
    "EVALUATOR_SINGLE_CHAT": """
你是对话质量评估专家。
任务：评估角色单聊对话的质量。

评估维度：
1. 角色一致性（30分）：是否符合角色设定
2. 对话自然度（25分）：是否自然流畅
3. 内容相关性（20分）：是否紧扣话题
4. 创意性（15分）：是否有趣生动
5. 规范遵守（10分）：是否遵守系统规则

输出格式（严格JSON）：{...}
""",
    
    # ... 其他8个评估器
}
```

**命令**: `python fastnpc/scripts/generate_evaluator_prompts.py`

---

## 阶段四：前端界面开发 (5小时)

### 4.1 角色列表星标显示

**文件**: `web/fastnpc-web/src/components/CharacterList.tsx`

```typescript
// 在角色卡片右上角添加星标图标
<div className="character-card">
  {character.is_test_case && (
    <span className="test-marker" title="测试用例">⭐</span>
  )}
  <img src={character.avatar} />
  <h4>{character.name}</h4>
</div>

// 点击星标切换状态
async function toggleTestMarker(personaId: string) {
  await api.post(`/api/characters/${personaId}/toggle-test-marker`)
  // 刷新列表
}
```

### 4.2 独立测试管理入口

**文件**: `web/fastnpc-web/src/components/admin/AdminPanel.tsx`

```typescript
// 在管理面板中添加新按钮（与"提示词管理"平级）
<button onClick={() => setShowTestManagement(true)}>
  🧪 测试管理
</button>
```

**文件**: `web/fastnpc-web/src/App.tsx`

```typescript
const [showTestManagement, setShowTestManagement] = useState(false)

// 添加测试管理模态框
{showTestManagement && (
  <TestManagementModal 
    show={showTestManagement}
    onClose={() => setShowTestManagement(false)}
  />
)}
```

### 4.3 测试管理主界面

**新文件**: `web/fastnpc-web/src/components/modals/TestManagementModal.tsx`

三栏布局：

```
┌─────────────┬──────────────────┬────────────────┐
│  测试分类    │   测试用例列表    │   测试详情      │
│  树形结构    │   版本+状态      │   内容+执行     │
├─────────────┼──────────────────┼────────────────┤
│ 单聊测试     │ 李白-诗词创作v1.0│ 对话内容        │
│  ├─李白     │ 李白-饮酒v1.0    │ 期望行为        │
│  ├─杜甫     │ ...              │ [执行测试]      │
│  └─...      │                  │ [查看历史]      │
│ 群聊测试     │ 政治局-辩论v1.0  │ [重置状态]      │
│  ├─政治局   │ ...              │ [编辑用例]      │
│  └─...      │                  │                │
│ 结构化生成   │                  │ 测试结果:       │
│  └─...      │                  │ - 通过率        │
│             │                  │ - 评分          │
│             │                  │ - 详细反馈      │
└─────────────┴──────────────────┴────────────────┘
```

关键功能：

- 测试用例版本管理（类似提示词版本切换）
- 单个测试执行
- 批量测试执行
- 测试结果可视化
- 状态重置按钮

### 4.4 测试用例编辑器

**新文件**: `web/fastnpc-web/src/components/TestCaseEditor.tsx`

```typescript
interface TestCaseEditorProps {
  testCase: TestCase | null
  onSave: (data: TestCaseData) => void
}

// 根据 category 渲染不同的编辑界面
// - SINGLE_CHAT: 对话序列编辑器（用户消息 + 期望特征）
// - GROUP_CHAT: 群聊场景编辑器
// - STRUCTURED_GEN: 输入文本 + 期望字段
```

### 4.5 批量测试界面

**新文件**: `web/fastnpc-web/src/components/BatchTestRunner.tsx`

```typescript
// 选择测试范围
// - 按分类（所有单聊/所有群聊）
// - 按角色/群聊
// - 按提示词版本

// 执行进度显示
// 实时结果更新
// 生成测试报告
```

### 4.6 测试报告查看

**新文件**: `web/fastnpc-web/src/components/TestReportViewer.tsx`

```typescript
// 汇总统计
// - 总体通过率
// - 各类别通过率
// - 平均分数

// 详细结果列表
// - 失败用例高亮
// - 可展开查看详情
// - 支持导出报告
```

---

## 阶段五：测试执行引擎 (3小时)

### 5.1 测试执行器核心

**新文件**: `fastnpc/testing/test_executor.py`

```python
class TestExecutor:
    async def execute_single_chat_test(self, test_case: Dict) -> Dict:
        """执行单聊测试"""
        # 1. 应用测试配置（覆盖用户设置）
        # 2. 加载角色
        # 3. 逐条发送测试对话
        # 4. 收集LLM响应
        # 5. 调用评估器
        # 6. 返回结果
        
    async def execute_group_chat_test(self, test_case: Dict) -> Dict:
        """执行群聊测试"""
        # 类似单聊，但处理群聊逻辑
        
    async def execute_structured_gen_test(self, test_case: Dict) -> Dict:
        """执行结构化生成测试"""
        # 1. 使用测试输入调用结构化生成
        # 2. 获取生成结果
        # 3. 调用评估器
        # 4. 对比期望字段
        
    async def evaluate_result(self, 
                            category: str,
                            actual_output: str,
                            test_case: Dict) -> Dict:
        """调用LLM评估器评估结果"""
        # 1. 加载对应的评估提示词
        # 2. 构造评估请求
        # 3. 调用LLM
        # 4. 解析评分和反馈
        # 5. 返回评估结果
```

### 5.2 批量测试调度器

**新文件**: `fastnpc/testing/batch_scheduler.py`

```python
class BatchScheduler:
    async def run_batch_tests(self, test_case_ids: List[int]) -> Dict:
        """批量运行测试用例"""
        # 1. 并发执行测试（控制并发数）
        # 2. 收集结果
        # 3. 生成汇总报告
        # 4. 保存到数据库
```

---

## 阶段六：集成与测试 (2小时)

### 6.1 系统集成

1. 在 `fastnpc/api/server.py` 中注册新路由
2. 确保所有API端点正确连接
3. 测试前后端数据流

### 6.2 生成初始数据

按顺序执行以下命令：

```bash
# 1. 数据库迁移
python fastnpc/scripts/migrations/add_test_markers.py

# 2. 生成评估提示词
python fastnpc/scripts/generate_evaluator_prompts.py

# 3. 标记测试角色和群聊
python fastnpc/scripts/mark_test_entities.py

# 4. 生成测试用例
python fastnpc/scripts/generate_initial_test_cases.py

# 5. 重启后端服务
pkill -f uvicorn
nohup python -m uvicorn fastnpc.api.server:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# 6. 重新构建前端
cd web/fastnpc-web
npm run build
```

### 6.3 功能验证

1. 验证角色列表星标显示
2. 验证测试管理界面打开
3. 验证测试用例版本管理
4. 执行单个测试用例
5. 执行批量测试
6. 验证状态重置功能
7. 查看测试报告

---

## 预计时间分配

- 阶段一（数据库）: 1.5小时
- 阶段二（后端API）: 3小时
- 阶段三（数据生成）: 4小时
- 阶段四（前端界面）: 5小时
- 阶段五（执行引擎）: 3小时
- 阶段六（集成测试）: 2小时

**总计**: 约18.5小时

---

## 关键设计决策

1. **测试用例版本管理**: 每个测试用例独立版本，version字段控制
2. **评估提示词**: 作为特殊category存储在 prompt_templates，复用版本管理
3. **状态恢复**: 删除对话文件+清空内存，确保完全重置
4. **测试执行**: 异步执行，支持并发控制
5. **UI组织**: 独立测试管理入口，避免提示词管理界面过于复杂
6. **数据生成**: 基于角色特点的智能生成 + 手动编辑支持

---

## 需要提供的命令清单

所有命令将在实施过程中整理提供，便于您手动执行。

### To-dos

- [ ] 阶段一：数据库设计与迁移 - 创建测试用例表、执行结果表、添加星标字段
- [ ] 阶段二：后端API开发 - 测试用例CRUD、状态恢复、测试执行、报告生成
- [ ] 阶段三：测试数据自动生成 - 为50个角色和11个群聊生成测试用例、创建评估提示词
- [ ] 阶段四：前端界面开发 - 星标显示、独立测试管理入口、测试执行界面、报告查看
- [ ] 阶段五：测试执行引擎 - 单聊/群聊/结构化生成测试执行器、LLM评估器、批量调度
- [ ] 阶段六：集成与测试 - 系统集成、生成初始数据、功能验证