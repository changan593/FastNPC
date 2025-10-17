import { useCharacter } from '../../contexts/CharacterContext'
import { useAuth } from '../../contexts/AuthContext'

interface CreateCharacterModalProps {
  show: boolean
  onClose: () => void
  onOpenPoly: () => Promise<void>
}

export function CreateCharacterModal({ show, onClose, onOpenPoly }: CreateCharacterModalProps) {
  const { user } = useAuth()
  const {
    newRole,
    setNewRole,
    newSource,
    setNewSource,
    newDetail,
    setNewDetail,
    creating,
    progress,
    setProgress,
    createDone,
    setCreateDone,
    setCreating,
    exportFacts,
    setExportFacts,
    exportBullets,
    setExportBullets,
    exportSummary,
    setExportSummary,
    exportMd,
    setExportMd,
    exportCtx,
    setExportCtx,
    createRole,
    polyChoiceIdx,
  } = useCharacter()

  function handleClose() {
    setNewRole('')
    setProgress(null)
    setCreateDone(false)
    setCreating(false)
    onClose()
  }

  async function handleCreate() {
    if (!newRole.trim()) {
      alert('请填写角色名')
      return
    }
    // 如果是百科/维基源且尚未选择义项，先打开消歧弹窗
    if ((newSource === 'baike' || newSource === 'zhwiki') && polyChoiceIdx == null) {
      await onOpenPoly()
      return
    }
    // 否则直接创建
    await createRole()
  }

  if (!show) return null

  return (
    <div className="modal">
      <div className="dialog">
        <h3>新建角色</h3>
        <label>
          角色名
          <input value={newRole} onChange={e => setNewRole(e.target.value)} placeholder="输入角色名" />
        </label>
        <label>
          数据源
          <select value={newSource} onChange={e => setNewSource(e.target.value as any)}>
            <option value="baike">百度百科 (baike)</option>
            <option value="zhwiki">中文维基 (zhwiki)</option>
          </select>
        </label>
        {/* 义项选择入口已改为"点击创建时自动弹窗"，此处不再显示 */}
        <label>
          结构化程度
          <select value={newDetail} onChange={e => setNewDetail(e.target.value as any)}>
            <option value="concise">简洁（仅核心八类与默认安全限制、基本任务与对话意图）</option>
            <option value="detailed">细化（含经历/关系网络/知识领域/世界观/时间线/社会规则/外部资源/行为约束/著名故事/组织/安全限制）</option>
          </select>
        </label>
        {user?.is_admin === 1 && (
          <details style={{ margin: '6px 0' }}>
            <summary style={{ cursor: 'pointer', color: '#374151' }}>管理员测试选项（导出中间产物）</summary>
            <div className="opt-grid">
              <label className="opt-chip" title="导出模型分块事实抽取（mapreduce策略下）">
                <input type="checkbox" checked={exportFacts} onChange={e => setExportFacts(e.target.checked)} />
                <div className="chip">
                  <span className="title">导出事实</span>
                  <span className="suffix">facts_*.json</span>
                </div>
              </label>
              <label className="opt-chip" title="导出要点文本（旧版 bullets）">
                <input type="checkbox" checked={exportBullets} onChange={e => setExportBullets(e.target.checked)} />
                <div className="chip">
                  <span className="title">导出要点</span>
                  <span className="suffix">bullets_*.txt</span>
                </div>
              </label>
              <label className="opt-chip" title="导出全局详细摘要（global 策略）">
                <input type="checkbox" checked={exportSummary} onChange={e => setExportSummary(e.target.checked)} />
                <div className="chip">
                  <span className="title">导出摘要</span>
                  <span className="suffix">summary_*.txt</span>
                </div>
              </label>
              <label className="opt-chip" title="导出 JSON→Markdown 的中间结果">
                <input type="checkbox" checked={exportMd} onChange={e => setExportMd(e.target.checked)} />
                <div className="chip">
                  <span className="title">导出 Markdown</span>
                  <span className="suffix">md_*.md</span>
                </div>
              </label>
              <label className="opt-chip" title="导出每次请求发送到模型前的上下文（含来源标注）">
                <input type="checkbox" checked={exportCtx} onChange={e => setExportCtx(e.target.checked)} />
                <div className="chip">
                  <span className="title">导出请求上下文</span>
                  <span className="suffix">ctx_*.json</span>
                </div>
              </label>
            </div>
          </details>
        )}
        {creating && !progress && (
          <div style={{ marginTop: 12, padding: '10px 12px', background: '#f3f4f6', borderRadius: 6, color: '#6b7280', fontSize: 14 }}>
            ⏱️ 预计创建时间约 2 分钟，请耐心等待...
          </div>
        )}
        {progress && (
          <div className="progress">
            <div>
              {progress.message} ({progress.progress ?? 0}%)
              {typeof progress.elapsed_sec === 'number' && (
                <span style={{ marginLeft: 8, color: '#6b7280' }}>
                  用时{' '}
                  {(() => {
                    const sec = Math.max(0, progress.elapsed_sec || 0)
                    const h = Math.floor(sec / 3600),
                      m = Math.floor((sec % 3600) / 60),
                      s = sec % 60
                    return h ? `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
                  })()}
                </span>
              )}
            </div>
            <progress value={progress.progress || 0} max={100}></progress>
          </div>
        )}
        <div className="actions">
          <button onClick={handleClose}>取消</button>
          {createDone ? (
            <button className="primary" onClick={handleClose}>
              完成
            </button>
          ) : (
            <button onClick={handleCreate} className="primary" disabled={creating}>
              {creating ? '创建中...' : '创建'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

