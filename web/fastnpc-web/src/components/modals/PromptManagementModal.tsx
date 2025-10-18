import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { PromptVersionSwitcher } from '../PromptVersionSwitcher'
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

interface TestCase {
  id: number
  prompt_category: string
  prompt_sub_category?: string
  name: string
  description?: string
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

export function PromptManagementModal({ show, onClose }: PromptManagementModalProps) {
  const { api } = useAuth()
  
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [testCases, setTestCases] = useState<TestCase[]>([])
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

  useEffect(() => {
    if (show) {
      loadPrompts()
      loadTestCases()
    }
  }, [show])

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

  async function loadTestCases() {
    try {
      const { data } = await api.get('/admin/prompts/test-cases')
      setTestCases(data.items || [])
    } catch (e: any) {
      console.error('加载测试用例失败:', e)
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

  if (!show) return null

  return (
    <div className="modal prompt-management-modal">
      <div className="dialog" style={{ width: '95vw', height: '90vh', maxWidth: 'none' }}>
        <div className="prompt-management-header">
          <h2>🎯 提示词管理</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="prompt-management-body">
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
                  {testCases
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

