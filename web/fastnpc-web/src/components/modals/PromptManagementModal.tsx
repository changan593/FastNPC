import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { PromptVersionSwitcher } from '../PromptVersionSwitcher'
import type { TestCase, TestExecution } from '../../types'
import './PromptManagementModal.css'

interface Prompt {
  id: number
  category: string
  sub_category?: string
  name: string
  description?: string
  template_content: string
  version: string
  is_active: number
  created_at: number
  updated_at: number
  metadata?: any
}

interface PromptManagementModalProps {
  show: boolean
  onClose: () => void
}

const PROMPT_CATEGORIES = {
  'STRUCTURED_GENERATION': {
    name: '结构化生成',
    subCategories: [
      '基础身份信息',
      '个性与行为设定',
      '背景故事',
      '知识与能力',
      '对话与交互规范',
      '任务/功能性信息',
      '环境与世界观',
      '系统与控制参数',
      '来源'
    ]
  },
  'BRIEF_GENERATION': { name: '简介生成', subCategories: [] },
  'SINGLE_CHAT_SYSTEM': { name: '单聊系统提示', subCategories: [] },
  'SINGLE_CHAT_STM_COMPRESSION': { name: '短期记忆凝练（单聊）', subCategories: [] },
  'GROUP_CHAT_STM_COMPRESSION': { name: '短期记忆凝练（群聊）', subCategories: [] },
  'LTM_INTEGRATION': { name: '长期记忆整合', subCategories: [] },
  'GROUP_MODERATOR': { name: '群聊中控', subCategories: [] },
  'GROUP_CHAT_CHARACTER': { name: '群聊角色发言', subCategories: [] },
  'STRUCTURED_SYSTEM_MESSAGE': { name: '结构化系统消息', subCategories: [] }
}

// 评估提示词分类定义
const EVALUATION_CATEGORIES = {
  'EVALUATOR_STRUCTURED_GEN': { name: '结构化生成评估器', icon: '📋' },
  'EVALUATOR_BRIEF_GEN': { name: '简介生成评估器', icon: '📝' },
  'EVALUATOR_SINGLE_CHAT': { name: '单聊对话评估器', icon: '💬' },
  'EVALUATOR_GROUP_CHAT': { name: '群聊对话评估器', icon: '👥' },
  'EVALUATOR_STM_COMPRESSION': { name: '短期记忆凝练评估器', icon: '🧠' },
  'EVALUATOR_LTM_INTEGRATION': { name: '长期记忆整合评估器', icon: '💾' },
  'EVALUATOR_GROUP_MODERATOR': { name: '群聊中控评估器', icon: '🎯' }
}

// 测试分类定义
const TEST_CATEGORIES = [
  { id: 'SINGLE_CHAT', name: '单聊测试', icon: '💬' },
  { id: 'GROUP_CHAT', name: '群聊测试', icon: '👥' },
  { id: 'STRUCTURED_GEN', name: '结构化生成', icon: '📋' },
  { id: 'BRIEF_GEN', name: '简介生成', icon: '📝' },
  { id: 'STM_COMPRESSION', name: '短期记忆', icon: '🧠' },
  { id: 'LTM_INTEGRATION', name: '长期记忆', icon: '💾' },
  { id: 'GROUP_MODERATOR', name: '群聊中控', icon: '🎯' }
]

export function PromptManagementModal({ show, onClose }: PromptManagementModalProps) {
  const { api } = useAuth()
  
  // 标签页状态
  const [activeTab, setActiveTab] = useState<'prompts' | 'tests' | 'evaluation'>('prompts')
  
  // 提示词相关状态
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [promptTestCases, setPromptTestCases] = useState<TestCase[]>([])
  const [, setLoading] = useState(false)
  
  // 选择状态
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedSubCategory, setSelectedSubCategory] = useState<string>('')
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null)
  
  // 编辑状态
  const [editedContent, setEditedContent] = useState('')
  const [editedDescription, setEditedDescription] = useState('')
  
  // 测试状态
  const [testResults, setTestResults] = useState<any>(null)
  const [testingPromptId, setTestingPromptId] = useState<number | null>(null)
  
  // 版本切换状态
  const [showVersionSwitcher, setShowVersionSwitcher] = useState(false)
  
  // 测试用例相关状态
  const [testCategory, setTestCategory] = useState<string>('SINGLE_CHAT')
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null)
  const [executions, setExecutions] = useState<TestExecution[]>([])
  const [testLoading, setTestLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  
  // 测试配置编辑状态
  const [editingConfig, setEditingConfig] = useState(false)
  const [configCtxMaxChat, setConfigCtxMaxChat] = useState('')
  const [configCtxMaxStm, setConfigCtxMaxStm] = useState('')
  const [configCtxMaxLtm, setConfigCtxMaxLtm] = useState('')
  const [configMaxGroupRounds, setConfigMaxGroupRounds] = useState('')
  const [configTemperature, setConfigTemperature] = useState('')
  const [configMaxTokens, setConfigMaxTokens] = useState('')
  const [configModel, setConfigModel] = useState('')

  useEffect(() => {
    if (show) {
      loadPrompts()
      loadPromptTestCases()
      
      // 如果是测试标签页，加载测试用例
      if (activeTab === 'tests') {
        loadTestCases(testCategory)
      }
    }
  }, [show, activeTab, testCategory])
  
  // 加载测试执行历史和配置
  useEffect(() => {
    if (selectedTestCase) {
      loadExecutions(selectedTestCase.id)
      loadTestConfig(selectedTestCase)
    }
  }, [selectedTestCase])
  
  // 加载测试配置到编辑状态
  function loadTestConfig(testCase: TestCase) {
    const config = testCase.test_config || {}
    setConfigCtxMaxChat(config.ctx_max_chat?.toString() || '')
    setConfigCtxMaxStm(config.ctx_max_stm?.toString() || '')
    setConfigCtxMaxLtm(config.ctx_max_ltm?.toString() || '')
    setConfigMaxGroupRounds(config.max_group_reply_rounds?.toString() || '')
    setConfigTemperature(config.temperature?.toString() || '')
    setConfigMaxTokens(config.max_tokens?.toString() || '')
    setConfigModel(config.model || '')
    setEditingConfig(false)
  }

  useEffect(() => {
    if (selectedPrompt) {
      setEditedContent(selectedPrompt.template_content)
      setEditedDescription(selectedPrompt.description || '')
    }
  }, [selectedPrompt])

  async function loadPrompts() {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/prompts?include_inactive=true')
      setPrompts(data.items || [])
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载提示词失败')
    } finally {
      setLoading(false)
    }
  }

  async function loadPromptTestCases() {
    try {
      const { data } = await api.get('/admin/prompts/test-cases')
      setPromptTestCases(data.items || [])
    } catch (e: any) {
      console.error('加载提示词测试用例失败:', e)
    }
  }
  
  // 加载测试用例（按分类）
  async function loadTestCases(category: string) {
    setTestLoading(true)
    try {
      const response = await fetch(`/admin/test-cases?category=${category}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setTestCases(data.items || [])
        // 自动选中第一个测试用例
        if (data.items && data.items.length > 0) {
          setSelectedTestCase(data.items[0])
        } else {
          setSelectedTestCase(null)
        }
      } else {
        console.error('加载测试用例失败:', await response.text())
        setTestCases([])
        setSelectedTestCase(null)
      }
    } catch (error) {
      console.error('加载测试用例失败:', error)
      setTestCases([])
      setSelectedTestCase(null)
    } finally {
      setTestLoading(false)
    }
  }
  
  // 加载测试执行历史
  async function loadExecutions(testCaseId: number) {
    try {
      const response = await fetch(`/admin/test-reports?test_case_id=${testCaseId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setExecutions(data.executions || [])
      } else {
        console.error('加载执行历史失败:', await response.text())
        setExecutions([])
      }
    } catch (error) {
      console.error('加载执行历史失败:', error)
      setExecutions([])
    }
  }

  function selectPrompt(category: string, subCategory?: string) {
    setSelectedCategory(category)
    setSelectedSubCategory(subCategory || '')
    
    // 查找对应的激活提示词
    const prompt = prompts.find(p => 
      p.category === category && 
      (subCategory ? p.sub_category === subCategory : !p.sub_category) &&
      p.is_active === 1
    )
    
    setSelectedPrompt(prompt || null)
    setTestResults(null)
  }

  async function handleSave() {
    if (!selectedPrompt) return
    
    if (!confirm('确定保存修改吗？这将创建一个新版本。')) return
    
    try {
      // 更新提示词
      await api.put(`/admin/prompts/${selectedPrompt.id}`, {
        template_content: editedContent,
        description: editedDescription,
        create_history: true
      })
      
      alert('保存成功')
      await loadPrompts()
    } catch (e: any) {
      alert(e?.response?.data?.error || '保存失败')
    }
  }

  async function handleActivate() {
    if (!selectedPrompt) return
    
    if (!confirm('确定激活此版本吗？')) return
    
    try {
      await api.post(`/admin/prompts/${selectedPrompt.id}/activate`)
      alert('激活成功')
      await loadPrompts()
    } catch (e: any) {
      alert(e?.response?.data?.error || '激活失败')
    }
  }

  async function handleDuplicate() {
    if (!selectedPrompt) return
    
    const newVersion = prompt('请输入新版本号:', '2.0.0')
    if (!newVersion) return
    
    try {
      const { data } = await api.post(`/admin/prompts/${selectedPrompt.id}/duplicate`, {
        new_version: newVersion
      })
      
      alert(`已复制为新版本 (ID: ${data.new_prompt_id})`)
      await loadPrompts()
    } catch (e: any) {
      alert(e?.response?.data?.error || '复制失败')
    }
  }

  async function handleRunTest() {
    if (!selectedPrompt) return
    
    setTestingPromptId(selectedPrompt.id)
    setTestResults(null)
    
    try {
      const { data } = await api.post(`/admin/prompts/${selectedPrompt.id}/test`)
      setTestResults(data.results || [])
    } catch (e: any) {
      alert(e?.response?.data?.error || '测试失败')
    } finally {
      setTestingPromptId(null)
    }
  }

  async function loadPromptVersion(versionId: number) {
    try {
      const { data } = await api.get(`/admin/prompts/${versionId}`)
      setSelectedPrompt(data)
      setEditedContent(data.template_content)
      setEditedDescription(data.description || '')
      await loadPrompts() // 刷新列表以更新激活状态
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载版本失败')
    }
  }
  
  // 执行测试用例
  async function handleExecuteTest() {
    if (!selectedTestCase) return
    
    setExecuting(true)
    try {
      const response = await fetch(`/admin/test-cases/${selectedTestCase.id}/execute`, {
        method: 'POST',
        credentials: 'include'
      })
      if (response.ok) {
        const result = await response.json()
        alert(`测试执行完成！\n通过: ${result.passed ? '是' : '否'}\n评分: ${result.score || 'N/A'}`)
        // 重新加载执行历史
        await loadExecutions(selectedTestCase.id)
      } else {
        const error = await response.text()
        alert(`测试执行失败: ${error}`)
      }
    } catch (error) {
      console.error('测试执行失败:', error)
      alert(`测试执行失败: ${error}`)
    } finally {
      setExecuting(false)
    }
  }
  
  // 重置测试状态
  async function handleResetState() {
    if (!selectedTestCase) return
    
    const confirmMsg = `确定要重置 "${selectedTestCase.name}" 的状态吗？\n这将清空所有对话历史和记忆。`
    if (!confirm(confirmMsg)) return
    
    try {
      const targetType = selectedTestCase.target_type.toLowerCase()
      const targetId = selectedTestCase.target_id
      const endpoint = targetType === 'character' 
        ? `/admin/test-cases/reset-character/${targetId}`
        : `/admin/test-cases/reset-group/${targetId}`
      
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'include'
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`状态重置成功！\n清理项: ${result.reset_count || 0}`)
      } else {
        const error = await response.text()
        alert(`状态重置失败: ${error}`)
      }
    } catch (error) {
      console.error('状态重置失败:', error)
      alert(`状态重置失败: ${error}`)
    }
  }
  
  // 保存测试配置
  async function handleSaveConfig() {
    if (!selectedTestCase) return
    
    try {
      const newConfig: any = {}
      
      // 只保存已填写的配置项
      if (configCtxMaxChat) newConfig.ctx_max_chat = Number(configCtxMaxChat)
      if (configCtxMaxStm) newConfig.ctx_max_stm = Number(configCtxMaxStm)
      if (configCtxMaxLtm) newConfig.ctx_max_ltm = Number(configCtxMaxLtm)
      if (configMaxGroupRounds) newConfig.max_group_reply_rounds = Number(configMaxGroupRounds)
      if (configTemperature) newConfig.temperature = Number(configTemperature)
      if (configMaxTokens) newConfig.max_tokens = Number(configMaxTokens)
      if (configModel) newConfig.model = configModel
      
      const response = await fetch(`/admin/test-cases/${selectedTestCase.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          test_config: newConfig
        })
      })
      
      if (response.ok) {
        alert('测试配置已保存！')
        setEditingConfig(false)
        // 重新加载测试用例以获取最新数据
        await loadTestCases(testCategory)
        // 更新选中的测试用例
        const updatedCase = testCases.find(tc => tc.id === selectedTestCase.id)
        if (updatedCase) {
          setSelectedTestCase(updatedCase)
        }
      } else {
        const error = await response.text()
        alert(`保存配置失败: ${error}`)
      }
    } catch (error) {
      console.error('保存配置失败:', error)
      alert(`保存配置失败: ${error}`)
    }
  }
  
  // 取消编辑测试配置
  function handleCancelConfigEdit() {
    if (selectedTestCase) {
      loadTestConfig(selectedTestCase)
    }
    setEditingConfig(false)
  }
  
  // 格式化工具函数
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('zh-CN')
  }
  
  const formatDuration = (ms?: number) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  if (!show) return null

  return (
    <div className="modal prompt-management-modal">
      <div className="dialog" style={{ width: '95vw', height: '90vh', maxWidth: 'none' }}>
        <div className="prompt-management-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <h2>🎯 提示词与测试管理</h2>
            <div className="tab-buttons">
              <button 
                className={`tab-btn ${activeTab === 'prompts' ? 'active' : ''}`}
                onClick={() => setActiveTab('prompts')}
              >
                🎯 提示词
              </button>
              <button 
                className={`tab-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
                onClick={() => setActiveTab('evaluation')}
              >
                ⭐ 评估
              </button>
              <button 
                className={`tab-btn ${activeTab === 'tests' ? 'active' : ''}`}
                onClick={() => setActiveTab('tests')}
              >
                🧪 测试用例
              </button>
            </div>
          </div>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="prompt-management-body">{activeTab === 'prompts' ? (
          // ========== 提示词管理界面 ==========
          <>
          {/* 左侧：分类树 */}
          <div className="category-sidebar">
            <h3>提示词分类</h3>
            <div className="category-tree">
              {Object.entries(PROMPT_CATEGORIES).map(([key, config]) => (
                <div key={key} className="category-group">
                  <div className="category-parent">{config.name}</div>
                  {config.subCategories.length > 0 ? (
                    <div className="category-children">
                      {config.subCategories.map(sub => {
                        const isActive = selectedCategory === key && selectedSubCategory === sub
                        return (
                          <div
                            key={sub}
                            className={`category-child ${isActive ? 'active' : ''}`}
                            onClick={() => selectPrompt(key, sub)}
                          >
                            {sub}
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div
                      className={`category-child ${selectedCategory === key ? 'active' : ''}`}
                      onClick={() => selectPrompt(key)}
                      style={{ marginLeft: 0 }}
                    >
                      点击查看
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 中间：编辑器 */}
          <div className="editor-area">
            {selectedPrompt ? (
              <>
                <div className="editor-header">
                  <div>
                    <h3>{selectedPrompt.name}</h3>
                    <span className="version-badge">
                      v{selectedPrompt.version}
                      {selectedPrompt.is_active === 1 && <span className="active-tag"> (激活)</span>}
                    </span>
                  </div>
                  <div className="editor-actions">
                    <button 
                      onClick={() => setShowVersionSwitcher(true)} 
                      className="btn-secondary"
                      title="查看和切换版本"
                    >
                      🔄 切换版本
                    </button>
                    <button onClick={handleSave} className="btn-primary">
                      💾 保存
                    </button>
                    {selectedPrompt.is_active !== 1 && (
                      <button onClick={handleActivate} className="btn-success">
                        ✓ 激活此版本
                      </button>
                    )}
                    <button onClick={handleDuplicate}>
                      📋 复制为新版本
                    </button>
                  </div>
                </div>

                <div className="editor-fields">
                  <label>
                    描述
                    <input
                      type="text"
                      value={editedDescription}
                      onChange={(e) => setEditedDescription(e.target.value)}
                      placeholder="提示词描述..."
                    />
                  </label>

                  <label>
                    提示词内容
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      rows={20}
                      placeholder="输入提示词内容，支持 {变量} 占位符..."
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                    />
                  </label>

                  {selectedPrompt.metadata?.variables && (
                    <div className="variables-info">
                      <strong>可用变量：</strong>
                      {selectedPrompt.metadata.variables.map((v: string) => (
                        <code key={v}>{`{${v}}`}</code>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>👈 请从左侧选择一个提示词分类</p>
              </div>
            )}
          </div>

          {/* 右侧：测试面板 */}
          <div className="test-panel">
            <h3>测试与评估</h3>
            
            {selectedPrompt ? (
              <>
                <div className="test-controls">
                  <button
                    onClick={handleRunTest}
                    disabled={testingPromptId !== null}
                    className="btn-primary"
                    style={{ width: '100%' }}
                  >
                    {testingPromptId ? '⏳ 测试中...' : '▶️ 运行测试'}
                  </button>
                </div>

                {testResults && (
                  <div className="test-results">
                    <h4>测试结果</h4>
                    {testResults.map((result: any, idx: number) => {
                      if (result.error) {
                        return (
                          <div key={idx} className="test-result error">
                            <strong>❌ 错误</strong>
                            <p>{result.error}</p>
                          </div>
                        )
                      }
                      
                      if (result.info) {
                        return (
                          <div key={idx} className="test-result info">
                            <p>{result.info}</p>
                          </div>
                        )
                      }

                      const passed = result.passed || false
                      const metrics = result.auto_metrics || {}
                      
                      return (
                        <div key={idx} className={`test-result ${passed ? 'passed' : 'failed'}`}>
                          <div className="test-result-header">
                            <strong>{passed ? '✅' : '❌'} {result.test_case_name}</strong>
                            <span className="pass-rate">
                              {(metrics.pass_rate * 100).toFixed(0)}%
                            </span>
                          </div>
                          
                          {metrics.passed_checks && metrics.passed_checks.length > 0 && (
                            <div className="checks passed-checks">
                              {metrics.passed_checks.map((check: string, i: number) => (
                                <div key={i}>✓ {check}</div>
                              ))}
                            </div>
                          )}
                          
                          {metrics.failed_checks && metrics.failed_checks.length > 0 && (
                            <div className="checks failed-checks">
                              {metrics.failed_checks.map((check: string, i: number) => (
                                <div key={i}>✗ {check}</div>
                              ))}
                            </div>
                          )}
                          
                          {result.output_content && (
                            <details>
                              <summary>查看输出</summary>
                              <pre>{result.output_content.substring(0, 500)}...</pre>
                            </details>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* 相关测试用例 */}
                <div className="related-test-cases">
                  <h4>相关测试用例</h4>
                  {promptTestCases
                    .filter(tc => 
                      tc.prompt_category === selectedPrompt.category &&
                      (!tc.prompt_sub_category || tc.prompt_sub_category === selectedPrompt.sub_category)
                    )
                    .map(tc => (
                      <div key={tc.id} className="test-case-item">
                        <strong>{tc.name}</strong>
                        <p>{tc.description}</p>
                      </div>
                    ))
                  }
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>选择提示词后可运行测试</p>
              </div>
            )}
          </div>
          </>
        ) : activeTab === 'evaluation' ? (
          // ========== 评估提示词管理界面 ==========
          <>
          {/* 左侧：评估器分类 */}
          <div className="category-sidebar">
            <h3>评估器分类</h3>
            <div className="category-tree">
              {Object.entries(EVALUATION_CATEGORIES).map(([key, config]) => (
                <div
                  key={key}
                  className={`category-child ${selectedCategory === key ? 'active' : ''}`}
                  onClick={() => selectPrompt(key)}
                  style={{ marginLeft: 0 }}
                >
                  <span style={{ marginRight: '8px' }}>{config.icon}</span>
                  {config.name}
                </div>
              ))}
            </div>
          </div>
          
          {/* 中间：评估器内容编辑 */}
          <div className="editor-area">
            {selectedPrompt ? (
              <>
                <div className="editor-header">
                  <div>
                    <h3>{selectedPrompt.name}</h3>
                    <div className="version-badge">
                      <span>v{selectedPrompt.version}</span>
                      {selectedPrompt.is_active === 1 && <span className="active-tag">● Active</span>}
                    </div>
                  </div>
                  <div className="editor-actions">
                    <button onClick={() => setShowVersionSwitcher(true)} className="btn-secondary">
                      📋 版本历史
                    </button>
                    <button onClick={handleSave} className="btn-primary">
                      💾 保存新版本
                    </button>
                    <button onClick={handleActivate} disabled={selectedPrompt.is_active === 1} className="btn-success">
                      ✓ 激活此版本
                    </button>
                    <button onClick={handleDuplicate} className="btn-secondary">
                      📑 复制
                    </button>
                  </div>
                </div>

                <div className="editor-fields">
                  <label>
                    描述
                    <input
                      type="text"
                      value={editedDescription}
                      onChange={(e) => setEditedDescription(e.target.value)}
                      placeholder="评估器描述..."
                    />
                  </label>

                  <label>
                    评估提示词内容
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      rows={20}
                      placeholder="输入评估提示词内容..."
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                    />
                  </label>

                  {selectedPrompt.metadata?.variables && selectedPrompt.metadata.variables.length > 0 && (
                    <div className="variables-info">
                      <strong>可用变量：</strong>
                      {selectedPrompt.metadata.variables.map((v: string) => (
                        <code key={v}>{`{${v}}`}</code>
                      ))}
                    </div>
                  )}

                  {selectedPrompt.metadata?.scoring_range && (
                    <div style={{ padding: '12px', background: '#e0f2fe', borderRadius: '8px', fontSize: '13px' }}>
                      <strong>评分范围：</strong> {selectedPrompt.metadata.scoring_range}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>👈 请从左侧选择一个评估器</p>
              </div>
            )}
          </div>

          {/* 右侧：评估器信息面板 */}
          <div className="test-panel">
            <h3>评估器信息</h3>
            
            {selectedPrompt ? (
              <>
                <div style={{ fontSize: '13px', lineHeight: 1.8 }}>
                  <div style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', color: '#374151' }}>
                      用途说明
                    </strong>
                    <p style={{ margin: 0, color: '#6b7280' }}>
                      {selectedPrompt.description || '暂无描述'}
                    </p>
                  </div>

                  <div style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', color: '#374151' }}>
                      版本信息
                    </strong>
                    <p style={{ margin: '4px 0', color: '#6b7280' }}>
                      当前版本: v{selectedPrompt.version}
                    </p>
                    <p style={{ margin: '4px 0', color: '#6b7280' }}>
                      状态: {selectedPrompt.is_active === 1 ? '✓ 已激活' : '未激活'}
                    </p>
                    <p style={{ margin: '4px 0', color: '#6b7280' }}>
                      更新时间: {new Date(selectedPrompt.updated_at * 1000).toLocaleString('zh-CN')}
                    </p>
                  </div>

                  <div style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', color: '#374151' }}>
                      输出格式
                    </strong>
                    <p style={{ margin: 0, color: '#6b7280' }}>
                      {selectedPrompt.metadata?.output_format === 'json' ? 'JSON 格式' : '文本格式'}
                    </p>
                  </div>

                  <div style={{ padding: '12px', background: '#fef3c7', borderRadius: '8px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', fontSize: '12px' }}>
                      💡 使用提示
                    </strong>
                    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px', color: '#78350f' }}>
                      <li>评估器用于自动评价LLM输出质量</li>
                      <li>修改评估标准会影响测试结果</li>
                      <li>建议保持评分体系的一致性</li>
                      <li>可以通过版本管理对比不同评估策略</li>
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>选择评估器后查看详情</p>
              </div>
            )}
          </div>
          </>
        ) : (
          // ========== 测试用例管理界面 ==========
          <>
          {/* 左侧：分类和测试用例列表 */}
          <div className="category-sidebar">
            {/* 测试分类 */}
            <div>
              <h3>测试分类</h3>
              <div className="category-tree">
                {TEST_CATEGORIES.map((category) => (
                  <div
                    key={category.id}
                    className={`category-child ${testCategory === category.id ? 'active' : ''}`}
                    onClick={() => setTestCategory(category.id)}
                    style={{ marginLeft: 0 }}
                  >
                    <span style={{ marginRight: '8px' }}>{category.icon}</span>
                    {category.name}
                  </div>
                ))}
              </div>
            </div>

            {/* 测试用例列表 */}
            <div className="test-cases-section" style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #e5e7eb' }}>
              <h3>测试用例</h3>
              <div className="category-tree">
                {testLoading ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>加载中...</div>
                ) : testCases.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#999', fontSize: '13px' }}>
                    暂无测试用例
                  </div>
                ) : (
                  testCases.map((testCase) => (
                    <div
                      key={testCase.id}
                      className={`category-child ${selectedTestCase?.id === testCase.id ? 'active' : ''}`}
                      onClick={() => setSelectedTestCase(testCase)}
                      style={{ marginLeft: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}
                    >
                      <div style={{ fontWeight: 500 }}>{testCase.name}</div>
                      {testCase.is_active === 1 && (
                        <span style={{ fontSize: '10px', background: '#10b981', color: 'white', padding: '2px 6px', borderRadius: '3px', marginTop: '4px' }}>
                          Active
                        </span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 中间：测试用例详情 */}
          <div className="editor-area">
            {!selectedTestCase ? (
              <div className="empty-state">
                <p>👈 请从左侧选择一个测试用例</p>
              </div>
            ) : (
              <>
                <div className="editor-header">
                  <div>
                    <h3>{selectedTestCase.name}</h3>
                    <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                      版本 {selectedTestCase.version} · {selectedTestCase.target_type} · 
                      创建于 {formatTimestamp(selectedTestCase.created_at)}
                    </div>
                  </div>
                  <div className="editor-actions">
                    <button 
                      className="btn-primary" 
                      onClick={handleExecuteTest}
                      disabled={executing}
                    >
                      {executing ? '⏳ 执行中...' : '▶️ 执行测试'}
                    </button>
                    <button 
                      onClick={handleResetState}
                      style={{ background: '#f59e0b', color: 'white' }}
                    >
                      🔄 重置状态
                    </button>
                  </div>
                </div>

                <div className="editor-fields" style={{ overflowY: 'auto' }}>
                  {/* 测试描述 */}
                  {selectedTestCase.description && (
                    <div style={{ marginBottom: '20px' }}>
                      <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>描述</label>
                      <p style={{ margin: 0, lineHeight: 1.6 }}>{selectedTestCase.description}</p>
                    </div>
                  )}

                  {/* 目标信息 */}
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>目标信息</label>
                    <p style={{ margin: '4px 0' }}>类型: {selectedTestCase.target_type}</p>
                    <p style={{ margin: '4px 0' }}>ID: {selectedTestCase.target_id}</p>
                  </div>

                  {/* 测试内容 */}
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>测试内容</label>
                    <pre style={{ 
                      background: '#f5f5f5', 
                      padding: '12px', 
                      borderRadius: '8px', 
                      fontSize: '13px', 
                      overflow: 'auto',
                      maxHeight: '200px',
                      border: '1px solid #e0e0e0'
                    }}>
                      {JSON.stringify(selectedTestCase.test_content, null, 2)}
                    </pre>
                  </div>

                  {/* 期望行为 */}
                  {selectedTestCase.expected_behavior && (
                    <div style={{ marginBottom: '20px' }}>
                      <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>期望行为</label>
                      <p style={{ margin: 0, lineHeight: 1.6 }}>{selectedTestCase.expected_behavior}</p>
                    </div>
                  )}

                  {/* 测试配置 */}
                  <div style={{ marginBottom: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <label style={{ fontWeight: 600, margin: 0 }}>测试配置</label>
                      {!editingConfig ? (
                        <button 
                          onClick={() => setEditingConfig(true)}
                          style={{ fontSize: '13px', padding: '4px 12px' }}
                        >
                          ⚙️ 编辑配置
                        </button>
                      ) : (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            onClick={handleSaveConfig}
                            className="btn-primary"
                            style={{ fontSize: '13px', padding: '4px 12px' }}
                          >
                            💾 保存
                          </button>
                          <button 
                            onClick={handleCancelConfigEdit}
                            style={{ fontSize: '13px', padding: '4px 12px' }}
                          >
                            ❌ 取消
                          </button>
                        </div>
                      )}
                    </div>
                    
                    {!editingConfig ? (
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: '12px', 
                        borderRadius: '8px', 
                        fontSize: '13px', 
                        overflow: 'auto',
                        maxHeight: '200px',
                        border: '1px solid #e0e0e0'
                      }}>
                        {selectedTestCase.test_config ? JSON.stringify(selectedTestCase.test_config, null, 2) : '{}'}
                      </pre>
                    ) : (
                      <div style={{ 
                        background: '#f5f5f5', 
                        padding: '16px', 
                        borderRadius: '8px',
                        border: '1px solid #e0e0e0'
                      }}>
                        {/* 记忆预算配置 */}
                        <div style={{ marginBottom: '16px' }}>
                          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                            记忆预算（字符数）
                          </label>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                            <input
                              type="number"
                              placeholder="会话记忆"
                              value={configCtxMaxChat}
                              onChange={e => setConfigCtxMaxChat(e.target.value)}
                              min="50"
                              max="5000"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                            <input
                              type="number"
                              placeholder="短期记忆"
                              value={configCtxMaxStm}
                              onChange={e => setConfigCtxMaxStm(e.target.value)}
                              min="50"
                              max="5000"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                            <input
                              type="number"
                              placeholder="长期记忆"
                              value={configCtxMaxLtm}
                              onChange={e => setConfigCtxMaxLtm(e.target.value)}
                              min="50"
                              max="5000"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                          </div>
                        </div>
                        
                        {/* 群聊配置 */}
                        <div style={{ marginBottom: '16px' }}>
                          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                            群聊轮次
                          </label>
                          <input
                            type="number"
                            placeholder="最大回复轮数（3-10）"
                            value={configMaxGroupRounds}
                            onChange={e => setConfigMaxGroupRounds(e.target.value)}
                            min="3"
                            max="10"
                            style={{ fontSize: '13px', padding: '6px 10px', width: '100%' }}
                          />
                        </div>
                        
                        {/* LLM 参数配置 */}
                        <div>
                          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                            LLM 参数
                          </label>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                            <input
                              type="number"
                              placeholder="Temperature (0-2)"
                              value={configTemperature}
                              onChange={e => setConfigTemperature(e.target.value)}
                              min="0"
                              max="2"
                              step="0.1"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                            <input
                              type="number"
                              placeholder="Max Tokens"
                              value={configMaxTokens}
                              onChange={e => setConfigMaxTokens(e.target.value)}
                              min="100"
                              max="4096"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                          </div>
                          <select
                            value={configModel}
                            onChange={e => setConfigModel(e.target.value)}
                            style={{ fontSize: '13px', padding: '6px 10px', width: '100%' }}
                          >
                            <option value="">（使用默认模型）</option>
                            <option value="z-ai/glm-4-32b">z-ai/glm-4-32b</option>
                            <option value="z-ai/glm-4.5-air:free">z-ai/glm-4.5-air:free</option>
                            <option value="deepseek/deepseek-chat-v3.1:free">deepseek/deepseek-chat-v3.1:free</option>
                            <option value="tencent/hunyuan-a13b-instruct:free">tencent/hunyuan-a13b-instruct:free</option>
                          </select>
                        </div>
                        
                        <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '12px' }}>
                          💡 留空表示使用全局默认值
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* 右侧：执行历史 */}
          <div className="test-panel">
            <h3>执行历史</h3>
            
            {!selectedTestCase ? (
              <div className="empty-state">
                <p>选择测试用例后查看执行历史</p>
              </div>
            ) : executions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
                <p>暂无执行记录</p>
                <p style={{ fontSize: '13px', color: '#bbb', marginTop: '8px' }}>点击"执行测试"开始测试</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {executions.map((execution) => (
                  <div 
                    key={execution.id} 
                    style={{
                      padding: '12px',
                      border: `1px solid ${execution.passed ? '#10b981' : '#ef4444'}`,
                      borderRadius: '8px',
                      background: execution.passed ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)'
                    }}
                  >
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', fontSize: '12px' }}>
                      <span style={{ color: '#666' }}>
                        {formatTimestamp(execution.execution_time)}
                      </span>
                      <span style={{ 
                        fontWeight: 600, 
                        padding: '2px 8px', 
                        borderRadius: '4px',
                        color: execution.passed ? '#10b981' : '#ef4444',
                        background: execution.passed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'
                      }}>
                        {execution.passed ? '✓ 通过' : '✗ 失败'}
                      </span>
                      {execution.score !== undefined && execution.score !== null && (
                        <span style={{ 
                          fontWeight: 600, 
                          color: '#667eea',
                          padding: '2px 8px',
                          background: 'rgba(102, 126, 234, 0.1)',
                          borderRadius: '4px'
                        }}>
                          {execution.score.toFixed(1)} 分
                        </span>
                      )}
                      <span style={{ 
                        color: '#666',
                        padding: '2px 6px',
                        background: '#f0f0f0',
                        borderRadius: '4px'
                      }}>
                        {formatDuration(execution.duration_ms)}
                      </span>
                    </div>
                    
                    {execution.evaluation_feedback && (
                      <div style={{ fontSize: '13px', color: '#333', lineHeight: 1.6, marginTop: '8px' }}>
                        <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>评估反馈:</strong>
                        {execution.evaluation_feedback}
                      </div>
                    )}

                    <details style={{ marginTop: '8px', fontSize: '13px' }}>
                      <summary style={{ cursor: 'pointer', fontWeight: 500, color: '#667eea', padding: '4px 0' }}>
                        查看详细信息
                      </summary>
                      {execution.llm_response && (
                        <div style={{ marginTop: '8px' }}>
                          <strong>LLM 响应:</strong>
                          <pre style={{ 
                            background: '#f5f5f5', 
                            padding: '8px', 
                            borderRadius: '4px',
                            fontSize: '12px',
                            overflow: 'auto',
                            marginTop: '4px',
                            border: '1px solid #e0e0e0',
                            maxHeight: '200px'
                          }}>
                            {execution.llm_response}
                          </pre>
                        </div>
                      )}
                      {execution.evaluation_result && (
                        <div style={{ marginTop: '8px' }}>
                          <strong>评估结果:</strong>
                          <pre style={{ 
                            background: '#f5f5f5', 
                            padding: '8px', 
                            borderRadius: '4px',
                            fontSize: '12px',
                            overflow: 'auto',
                            marginTop: '4px',
                            border: '1px solid #e0e0e0',
                            maxHeight: '200px'
                          }}>
                            {JSON.stringify(execution.evaluation_result, null, 2)}
                          </pre>
                        </div>
                      )}
                    </details>
                  </div>
                ))}
              </div>
            )}
          </div>
          </>
        )}
        </div>

        {/* 版本切换弹窗 */}
        {showVersionSwitcher && selectedPrompt && (
          <PromptVersionSwitcher
            promptId={selectedPrompt.id}
            currentVersion={selectedPrompt.version}
            onClose={() => setShowVersionSwitcher(false)}
            onVersionChange={(versionId) => {
              loadPromptVersion(versionId)
              setShowVersionSwitcher(false)
            }}
          />
        )}
      </div>
    </div>
  )
}

