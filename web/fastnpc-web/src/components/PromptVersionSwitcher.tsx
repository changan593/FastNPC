import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import './PromptVersionSwitcher.css'

interface PromptVersion {
  id: number
  category: string
  sub_category?: string
  name: string
  description?: string
  template_content: string
  version: string
  is_active: number
  created_at: number
  updated_at?: number
  test_count: number
  pass_rate: number
  last_test_time?: number
}

interface PromptVersionSwitcherProps {
  promptId: number
  currentVersion: string
  onClose: () => void
  onVersionChange: (versionId: number) => void
}

export function PromptVersionSwitcher({ promptId, onClose, onVersionChange }: PromptVersionSwitcherProps) {
  const { api } = useAuth()
  
  const [versions, setVersions] = useState<PromptVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedVersion, setExpandedVersion] = useState<number | null>(null)
  const [activatingId, setActivatingId] = useState<number | null>(null)

  useEffect(() => {
    loadVersions()
  }, [promptId])

  async function loadVersions() {
    setLoading(true)
    try {
      const { data } = await api.get(`/admin/prompts/${promptId}/versions`)
      setVersions(data.items || [])
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载版本列表失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleActivate(versionId: number) {
    if (!confirm('确定激活此版本吗？')) return
    
    setActivatingId(versionId)
    try {
      await api.post(`/admin/prompts/${versionId}/activate`)
      alert('版本已激活')
      await loadVersions()
      onVersionChange(versionId)
    } catch (e: any) {
      alert(e?.response?.data?.error || '激活失败')
    } finally {
      setActivatingId(null)
    }
  }

  function getResultClass(passRate: number): string {
    if (passRate >= 0.8) return 'high'
    if (passRate >= 0.5) return 'medium'
    return 'low'
  }

  function formatDate(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleString('zh-CN')
  }

  function toggleExpand(versionId: number) {
    setExpandedVersion(expandedVersion === versionId ? null : versionId)
  }

  return (
    <div className="modal version-switcher-modal">
      <div className="dialog version-switcher-dialog">
        <div className="version-switcher-header">
          <h3>🔄 版本切换</h3>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="version-switcher-body">
          {loading ? (
            <div className="loading">加载中...</div>
          ) : versions.length === 0 ? (
            <div className="empty-state">暂无版本</div>
          ) : (
            <div className="versions-list">
              {versions.map((version) => {
                const isActive = version.is_active === 1
                const isExpanded = expandedVersion === version.id
                const isActivating = activatingId === version.id
                
                return (
                  <div 
                    key={version.id} 
                    className={`version-card ${isActive ? 'active' : ''}`}
                  >
                    <div className="version-card-header">
                      <div className="version-info">
                        <span className="version-number">v{version.version}</span>
                        {isActive && <span className="active-badge">激活中</span>}
                        <span className="version-date">{formatDate(version.created_at)}</span>
                      </div>
                      <div className="version-actions">
                        <button 
                          onClick={() => toggleExpand(version.id)}
                          className="btn-icon"
                          title={isExpanded ? "收起" : "展开"}
                        >
                          {isExpanded ? '▲' : '▼'}
                        </button>
                        {!isActive && (
                          <button 
                            onClick={() => handleActivate(version.id)}
                            className="btn-activate"
                            disabled={isActivating}
                          >
                            {isActivating ? '激活中...' : '激活'}
                          </button>
                        )}
                      </div>
                    </div>

                    {version.description && (
                      <div className="version-description">
                        {version.description}
                      </div>
                    )}

                    <div className="version-test-summary">
                      {version.test_count > 0 ? (
                        <>
                          <span className={`test-result-badge ${getResultClass(version.pass_rate)}`}>
                            通过率: {(version.pass_rate * 100).toFixed(0)}%
                          </span>
                          <span className="test-count">
                            测试次数: {version.test_count}
                          </span>
                          {version.last_test_time && (
                            <span className="last-test-time">
                              最后测试: {formatDate(version.last_test_time)}
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="no-test">未测试</span>
                      )}
                    </div>

                    {isExpanded && (
                      <div className="version-content-preview">
                        <div className="content-label">提示词内容:</div>
                        <pre className="content-text">
                          {version.template_content.length > 500 
                            ? version.template_content.substring(0, 500) + '...' 
                            : version.template_content}
                        </pre>
                        {version.template_content.length > 500 && (
                          <div className="content-note">
                            显示前500字符，激活后可在编辑器中查看完整内容
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

