# 测试管理系统 - 前端实施指南

**当前时间**：2025-01-18  
**完成进度**：后端100%，前端20%

---

## ✅ 已完成的前端工作

### 1. 类型定义 ✅
**文件**：`web/fastnpc-web/src/types.ts`

```typescript
// 已添加字段：
CharacterItem.is_test_case?: boolean
GroupItem.is_test_case?: boolean

// 已添加接口：
export interface TestCase { ... }
export interface TestExecution { ... }
```

### 2. Sidebar 星标显示 ✅
**文件**：`web/fastnpc-web/src/components/Sidebar.tsx`

已修改120-142行，在角色和群聊名称后显示⭐星标。

### 3. AdminPanel 测试管理按钮 ✅
**文件**：`web/fastnpc-web/src/components/admin/AdminPanel.tsx`

- 已添加 `onOpenTestManagement` prop
- 已添加"🧪 测试管理"按钮（第83-87行）

---

## ⏳ 待完成的前端工作

### 步骤 1：修改 App.tsx 集成测试管理

**文件**：`web/fastnpc-web/src/App.tsx`

**需要添加的内容**：

```typescript
// 1. 在第99行后添加 state
const [showTestManagement, setShowTestManagement] = useState(false)

// 2. 导入 TestManagementModal（第19行后）
import { TestManagementModal } from './components/modals/TestManagementModal'

// 3. 在 AdminPanel 调用处添加 prop（约第434行）
<AdminPanel 
  onOpenPromptManagement={() => setShowPromptManagement(true)}
  onOpenTestManagement={() => setShowTestManagement(true)}  // 新增
/>

// 4. 在 PromptManagementModal 后添加（约第643行后）
{showTestManagement && (
  <TestManagementModal
    show={showTestManagement}
    onClose={() => setShowTestManagement(false)}
  />
)}
```

---

### 步骤 2：创建 TestManagementModal 主界面

**新文件**：`web/fastnpc-web/src/components/modals/TestManagementModal.tsx`

这是一个大型组件（预计800+行），包含三栏布局：

**布局结构**：
```
┌─────────────┬──────────────────┬────────────────┐
│  左栏        │   中栏            │   右栏          │
│  分类树      │   测试用例列表    │   详情面板      │
├─────────────┼──────────────────┼────────────────┤
│ □ 单聊测试   │ 李白-诗词 v1.0   │ 测试内容编辑    │
│   ├ 李白     │ ✓ 激活           │ 期望行为        │
│   ├ 杜甫     │ 李白-饮酒 v1.0   │ 测试配置        │
│   └ ...      │                  │ [执行测试]      │
│ □ 群聊测试   │ 政治局-辩论 v1.0 │ [查看历史]      │
│   ├ 政治局   │                  │ [重置状态]      │
│   └ ...      │                  │                │
│ □ 结构化生成 │                  │ 测试结果：      │
│ □ 简介生成   │                  │ - 通过率: 85%   │
│ □ 记忆凝练   │                  │ - 平均分: 78    │
└─────────────┴──────────────────┴────────────────┘
```

**核心代码框架**：

```typescript
import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import type { TestCase, TestExecution } from '../../types'
import './TestManagementModal.css'

interface TestManagementModalProps {
  show: boolean
  onClose: () => void
}

export function TestManagementModal({ show, onClose }: TestManagementModalProps) {
  const { api } = useAuth()
  
  // State management
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedTargetType, setSelectedTargetType] = useState<string>('')
  const [selectedTargetId, setSelectedTargetId] = useState<string>('')
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null)
  const [testExecutions, setTestExecutions] = useState<TestExecution[]>([])
  const [loading, setLoading] = useState(false)
  
  // Categories
  const categories = [
    { key: 'SINGLE_CHAT', name: '单聊测试', icon: '💬' },
    { key: 'GROUP_CHAT', name: '群聊测试', icon: '👥' },
    { key: 'STRUCTURED_GEN', name: '结构化生成', icon: '📋' },
    { key: 'BRIEF_GEN', name: '简介生成', icon: '📝' },
    { key: 'STM_COMPRESSION', name: '记忆凝练', icon: '🧠' },
    { key: 'LTM_INTEGRATION', name: '长期记忆', icon: '💾' },
    { key: 'GROUP_MODERATOR', name: '群聊中控', icon: '🎭' },
  ]
  
  // Load test cases
  useEffect(() => {
    if (show && selectedCategory) {
      loadTestCases()
    }
  }, [show, selectedCategory, selectedTargetId])
  
  async function loadTestCases() {
    setLoading(true)
    try {
      const params: any = { category: selectedCategory }
      if (selectedTargetId) {
        params.target_id = selectedTargetId
      }
      const { data } = await api.get('/admin/test-cases', { params })
      setTestCases(data.items || [])
    } catch (e: any) {
      console.error('加载测试用例失败:', e)
    } finally {
      setLoading(false)
    }
  }
  
  // Execute test
  async function executeTest(testCaseId: number) {
    try {
      const { data } = await api.post(`/admin/test-cases/${testCaseId}/execute`)
      alert('测试执行成功！')
      loadTestExecutions(testCaseId)
    } catch (e: any) {
      alert(e?.response?.data?.error || '执行失败')
    }
  }
  
  // Reset state
  async function resetState(targetType: string, targetId: string) {
    if (!confirm('确定要重置状态吗？这将清空所有对话记录和记忆。')) return
    
    try {
      const endpoint = targetType === 'CHARACTER' 
        ? `/admin/test-cases/reset-character/${targetId}`
        : `/admin/test-cases/reset-group/${targetId}`
      
      await api.post(endpoint)
      alert('状态重置成功！')
    } catch (e: any) {
      alert(e?.response?.data?.error || '重置失败')
    }
  }
  
  // Load test executions
  async function loadTestExecutions(testCaseId: number) {
    try {
      const { data } = await api.get('/admin/test-reports', {
        params: { test_case_id: testCaseId }
      })
      setTestExecutions(data.executions || [])
    } catch (e: any) {
      console.error('加载测试记录失败:', e)
    }
  }
  
  if (!show) return null
  
  return (
    <div className="modal test-management-modal">
      <div className="dialog" style={{ width: '95vw', height: '90vh', maxWidth: 'none' }}>
        <div className="test-management-header">
          <h2>🧪 测试管理</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        
        <div className="test-management-body">
          {/* 左栏：分类树 */}
          <div className="test-category-sidebar">
            <h3>测试分类</h3>
            <div className="category-list">
              {categories.map(cat => (
                <div
                  key={cat.key}
                  className={`category-item ${selectedCategory === cat.key ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedCategory(cat.key)
                    setSelectedTargetId('')
                    setSelectedTestCase(null)
                  }}
                >
                  <span className="category-icon">{cat.icon}</span>
                  <span className="category-name">{cat.name}</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* 中栏：测试用例列表 */}
          <div className="test-case-list">
            <div className="test-case-list-header">
              <h3>测试用例</h3>
              <button className="btn-primary">
                ➕ 新建
              </button>
            </div>
            
            {loading ? (
              <div className="loading">加载中...</div>
            ) : (
              <div className="test-cases">
                {testCases.map(tc => (
                  <div
                    key={tc.id}
                    className={`test-case-card ${selectedTestCase?.id === tc.id ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedTestCase(tc)
                      loadTestExecutions(tc.id)
                    }}
                  >
                    <div className="test-case-header">
                      <span className="test-case-name">{tc.name}</span>
                      {tc.is_active === 1 && <span className="badge active">激活</span>}
                    </div>
                    <div className="test-case-meta">
                      <span className="version">v{tc.version}</span>
                      <span className="target">{tc.target_id}</span>
                    </div>
                  </div>
                ))}
                
                {testCases.length === 0 && !loading && (
                  <div className="empty-state">
                    <p>暂无测试用例</p>
                    <p className="muted">请创建新的测试用例</p>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* 右栏：详情面板 */}
          <div className="test-detail-panel">
            {selectedTestCase ? (
              <>
                <div className="test-detail-header">
                  <h3>{selectedTestCase.name}</h3>
                  <div className="test-detail-actions">
                    <button onClick={() => executeTest(selectedTestCase.id)} className="btn-primary">
                      ▶ 执行测试
                    </button>
                    <button 
                      onClick={() => resetState(selectedTestCase.target_type, selectedTestCase.target_id)}
                      className="btn-warning"
                    >
                      🔄 重置状态
                    </button>
                  </div>
                </div>
                
                <div className="test-detail-content">
                  <div className="detail-section">
                    <h4>基本信息</h4>
                    <div className="detail-item">
                      <span className="label">版本:</span>
                      <span className="value">v{selectedTestCase.version}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">目标:</span>
                      <span className="value">{selectedTestCase.target_id}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">描述:</span>
                      <span className="value">{selectedTestCase.description || '无'}</span>
                    </div>
                  </div>
                  
                  <div className="detail-section">
                    <h4>测试内容</h4>
                    <pre className="test-content">
                      {JSON.stringify(selectedTestCase.test_content, null, 2)}
                    </pre>
                  </div>
                  
                  <div className="detail-section">
                    <h4>测试结果</h4>
                    {testExecutions.length > 0 ? (
                      <div className="executions-list">
                        {testExecutions.map(exec => (
                          <div key={exec.id} className={`execution-item ${exec.passed ? 'passed' : 'failed'}`}>
                            <div className="execution-header">
                              <span className="execution-time">
                                {new Date(exec.execution_time * 1000).toLocaleString()}
                              </span>
                              <span className={`execution-status ${exec.passed ? 'pass' : 'fail'}`}>
                                {exec.passed ? '✓ 通过' : '✗ 失败'}
                              </span>
                              {exec.score && (
                                <span className="execution-score">
                                  评分: {exec.score}
                                </span>
                              )}
                            </div>
                            {exec.evaluation_feedback && (
                              <div className="execution-feedback">
                                {exec.evaluation_feedback}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-state">
                        <p>暂无测试记录</p>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state" style={{ marginTop: '40%' }}>
                <p>请选择一个测试用例</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
```

---

### 步骤 3：创建 TestManagementModal.css

**新文件**：`web/fastnpc-web/src/components/modals/TestManagementModal.css`

```css
.test-management-modal .dialog {
  display: flex;
  flex-direction: column;
}

.test-management-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.test-management-header h2 {
  margin: 0;
  font-size: 24px;
}

.test-management-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左栏：分类树 */
.test-category-sidebar {
  width: 220px;
  border-right: 1px solid var(--border);
  padding: 16px;
  overflow-y: auto;
}

.test-category-sidebar h3 {
  font-size: 16px;
  margin: 0 0 12px;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.category-item:hover {
  background: var(--hover-bg);
}

.category-item.active {
  background: var(--primary);
  color: white;
}

.category-icon {
  font-size: 18px;
}

.category-name {
  font-size: 14px;
}

/* 中栏：测试用例列表 */
.test-case-list {
  width: 320px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

.test-case-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.test-case-list-header h3 {
  font-size: 16px;
  margin: 0;
}

.test-cases {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.test-case-card {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.test-case-card:hover {
  border-color: var(--primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.test-case-card.active {
  border-color: var(--primary);
  background: rgba(var(--primary-rgb), 0.05);
}

.test-case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.test-case-name {
  font-weight: 500;
  font-size: 14px;
}

.test-case-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 右栏：详情面板 */
.test-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.test-detail-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.test-detail-header h3 {
  font-size: 18px;
  margin: 0;
}

.test-detail-actions {
  display: flex;
  gap: 8px;
}

.test-detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  font-size: 14px;
  margin: 0 0 12px;
  color: var(--text-muted);
  text-transform: uppercase;
}

.detail-item {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.detail-item .label {
  font-weight: 500;
  min-width: 60px;
  color: var(--text-muted);
}

.test-content {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
  overflow-x: auto;
}

/* 测试执行结果 */
.executions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.execution-item {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.execution-item.passed {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.05);
}

.execution-item.failed {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.execution-header {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.execution-time {
  font-size: 12px;
  color: var(--text-muted);
}

.execution-status {
  font-size: 13px;
  font-weight: 500;
}

.execution-status.pass {
  color: #10b981;
}

.execution-status.fail {
  color: #ef4444;
}

.execution-score {
  font-size: 13px;
  font-weight: 500;
  color: var(--primary);
}

.execution-feedback {
  font-size: 13px;
  color: var(--text);
  line-height: 1.6;
}

/* 按钮样式 */
.btn-primary {
  background: var(--primary);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-warning {
  background: #f59e0b;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-state p {
  margin: 8px 0;
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.badge.active {
  background: #10b981;
  color: white;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
```

---

## 📝 实施步骤总结

1. ✅ 修改 `types.ts` - 完成
2. ✅ 修改 `Sidebar.tsx` - 完成
3. ✅ 修改 `AdminPanel.tsx` - 完成
4. ⏳ 修改 `App.tsx` - 需手动添加（参考步骤1）
5. ⏳ 创建 `TestManagementModal.tsx` - 需手动创建（参考步骤2）
6. ⏳ 创建 `TestManagementModal.css` - 需手动创建（参考步骤3）

---

## 🚀 前端构建和测试

完成上述步骤后，执行：

```bash
cd /home/changan/MyProject/FastNPC/web/fastnpc-web
npm run build
```

---

## 📌 注意事项

1. 测试管理Modal是简化版，只包含核心功能
2. 可以根据需要添加更多功能：
   - 测试用例编辑器
   - 批量测试执行
   - 版本管理
   - 导出测试报告
3. CSS变量依赖现有的App.css中的定义

---

**当前状态**：后端API完整，前端基础框架已搭建，核心测试管理界面代码已提供，可直接复制使用。

