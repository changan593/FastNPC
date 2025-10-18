import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import './PromptVersionCompare.css'

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
}

interface PromptVersionCompareProps {
  promptId1: number
  promptId2: number
  onClose: () => void
}

export function PromptVersionCompare({ promptId1, promptId2, onClose }: PromptVersionCompareProps) {
  const { api } = useAuth()
  const [prompt1, setPrompt1] = useState<Prompt | null>(null)
  const [prompt2, setPrompt2] = useState<Prompt | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPrompts()
  }, [promptId1, promptId2])

  async function loadPrompts() {
    setLoading(true)
    try {
      const [res1, res2] = await Promise.all([
        api.get(`/admin/prompts/${promptId1}`),
        api.get(`/admin/prompts/${promptId2}`)
      ])
      setPrompt1(res1.data)
      setPrompt2(res2.data)
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  function getDiff(text1: string, text2: string): { added: string[]; removed: string[]; unchanged: string[] } {
    const lines1 = text1.split('\n')
    const lines2 = text2.split('\n')
    
    const added: string[] = []
    const removed: string[] = []
    const unchanged: string[] = []
    
    // 简单的逐行对比（可以使用更复杂的diff算法）
    const maxLen = Math.max(lines1.length, lines2.length)
    
    for (let i = 0; i < maxLen; i++) {
      const line1 = lines1[i] || ''
      const line2 = lines2[i] || ''
      
      if (line1 === line2) {
        unchanged.push(line1)
      } else {
        if (line1) removed.push(line1)
        if (line2) added.push(line2)
      }
    }
    
    return { added, removed, unchanged }
  }

  if (loading) {
    return (
      <div className="version-compare-container">
        <div className="loading">加载中...</div>
      </div>
    )
  }

  if (!prompt1 || !prompt2) {
    return (
      <div className="version-compare-container">
        <div className="error">无法加载提示词</div>
      </div>
    )
  }

  const diff = getDiff(prompt1.template_content, prompt2.template_content)

  return (
    <div className="version-compare-container">
      <div className="version-compare-header">
        <h3>🔄 版本对比</h3>
        <button onClick={onClose} className="close-btn">×</button>
      </div>

      <div className="version-compare-body">
        <div className="compare-info">
          <div className="prompt-info">
            <h4>{prompt1.name}</h4>
            <span className="version-badge">v{prompt1.version}</span>
            {prompt1.is_active === 1 && <span className="active-tag">激活</span>}
          </div>
          <div className="vs">VS</div>
          <div className="prompt-info">
            <h4>{prompt2.name}</h4>
            <span className="version-badge">v{prompt2.version}</span>
            {prompt2.is_active === 1 && <span className="active-tag">激活</span>}
          </div>
        </div>

        <div className="diff-summary">
          <div className="diff-stat added">+ {diff.added.length} 行新增</div>
          <div className="diff-stat removed">- {diff.removed.length} 行删除</div>
          <div className="diff-stat unchanged">{diff.unchanged.length} 行未变更</div>
        </div>

        <div className="compare-panels">
          <div className="compare-panel">
            <h5>版本 {prompt1.version}</h5>
            <pre className="content-display">
              {prompt1.template_content}
            </pre>
          </div>

          <div className="compare-panel">
            <h5>版本 {prompt2.version}</h5>
            <pre className="content-display">
              {prompt2.template_content}
            </pre>
          </div>
        </div>

        <div className="diff-view">
          <h5>差异视图</h5>
          <div className="diff-content">
            {diff.removed.map((line, i) => (
              <div key={`removed-${i}`} className="diff-line removed">
                <span className="diff-marker">-</span>
                <span className="diff-text">{line || ' '}</span>
              </div>
            ))}
            {diff.added.map((line, i) => (
              <div key={`added-${i}`} className="diff-line added">
                <span className="diff-marker">+</span>
                <span className="diff-text">{line || ' '}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

