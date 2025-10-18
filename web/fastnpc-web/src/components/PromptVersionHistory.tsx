import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import './PromptVersionHistory.css'

interface VersionHistoryItem {
  id: number
  prompt_template_id: number
  version: string
  change_log?: string
  previous_content?: string
  created_by?: number
  created_at: number
}

interface PromptVersionHistoryProps {
  promptId: number
  onClose: () => void
}

export function PromptVersionHistory({ promptId, onClose }: PromptVersionHistoryProps) {
  const { api } = useAuth()
  const [history, setHistory] = useState<VersionHistoryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHistory()
  }, [promptId])

  async function loadHistory() {
    setLoading(true)
    try {
      const { data } = await api.get(`/admin/prompts/${promptId}/history`)
      setHistory(data.items || [])
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载历史失败')
    } finally {
      setLoading(false)
    }
  }

  function formatDate(timestamp: number) {
    return new Date(timestamp * 1000).toLocaleString('zh-CN')
  }

  return (
    <div className="version-history-container">
      <div className="version-history-header">
        <h3>📜 版本历史</h3>
        <button onClick={onClose} className="close-btn">×</button>
      </div>

      <div className="version-history-body">
        {loading ? (
          <div className="loading">加载中...</div>
        ) : history.length === 0 ? (
          <div className="empty-state">暂无版本历史</div>
        ) : (
          <div className="timeline">
            {history.map((item) => (
              <div key={item.id} className="timeline-item">
                <div className="timeline-marker"></div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="version-badge">v{item.version}</span>
                    <span className="timestamp">{formatDate(item.created_at)}</span>
                  </div>
                  {item.change_log && (
                    <div className="change-log">
                      <strong>变更说明：</strong>
                      <p>{item.change_log}</p>
                    </div>
                  )}
                  {item.previous_content && (
                    <details>
                      <summary>查看变更前内容</summary>
                      <pre className="previous-content">{item.previous_content.substring(0, 500)}...</pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

