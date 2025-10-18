import { useState, useEffect } from 'react'
import { useCharacter } from '../../contexts/CharacterContext'
import { useAuth } from '../../contexts/AuthContext'
import { ImageCropper } from '../ImageCropper'

interface CreateCharacterModalProps {
  show: boolean
  onClose: () => void
  onOpenPoly: () => Promise<void>
}

export function CreateCharacterModal({ show, onClose, onOpenPoly }: CreateCharacterModalProps) {
  const { user, api } = useAuth()
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
    currentTaskId,
    cancelCurrentTask,
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
    characters,
    setCharacters,
    activeRole,
  } = useCharacter()

  const [showAvatarPrompt, setShowAvatarPrompt] = useState(false)
  const [showAvatarCrop, setShowAvatarCrop] = useState(false)
  const [avatarToProcess, setAvatarToProcess] = useState<string>('')
  const [processingAvatar, setProcessingAvatar] = useState(false)
  const [avatarProcessed, setAvatarProcessed] = useState(false)

  // 监听角色创建完成，检查是否需要裁剪头像
  useEffect(() => {
    if (createDone && activeRole && characters.length > 0 && !avatarProcessed) {
      const newChar = characters.find(c => c.role === activeRole)
      if (newChar?.avatar_url) {
        // 下载头像到本地进行裁剪
        fetch(newChar.avatar_url)
          .then(res => res.blob())
          .then(blob => {
            const url = URL.createObjectURL(blob)
            setAvatarToProcess(url)
            setShowAvatarPrompt(true)
          })
          .catch(err => {
            console.error('加载头像失败:', err)
          })
      }
    }
  }, [createDone, activeRole, characters, avatarProcessed])

  async function handleAvatarCropComplete(croppedBlob: Blob) {
    setProcessingAvatar(true)
    
    // 先关闭所有头像相关弹窗，并标记为已处理
    setShowAvatarPrompt(false)
    setShowAvatarCrop(false)
    setAvatarProcessed(true)
    if (avatarToProcess) {
      URL.revokeObjectURL(avatarToProcess)
    }
    setAvatarToProcess('')
    
    try {
      const formData = new FormData()
      formData.append('file', croppedBlob, 'avatar.jpg')

      await api.post(`/api/characters/${encodeURIComponent(activeRole)}/avatar`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      // 刷新角色列表
      const { data: list } = await api.get('/api/characters')
      setCharacters(list.items || [])
      
      alert('头像已更新')
    } catch (e: any) {
      alert(e?.response?.data?.detail || '头像更新失败')
    } finally {
      setProcessingAvatar(false)
    }
  }

  function handleSkipCrop() {
    setShowAvatarPrompt(false)
    setShowAvatarCrop(false)
    setAvatarProcessed(true)
    if (avatarToProcess) {
      URL.revokeObjectURL(avatarToProcess)
    }
    setAvatarToProcess('')
  }

  function handleStartCrop() {
    setShowAvatarPrompt(false)
    setShowAvatarCrop(true)
  }

  async function handleClose() {
    // 如果正在创建且有任务ID，先取消任务
    if (creating && currentTaskId) {
      await cancelCurrentTask()
      console.log('[INFO] 已取消创建任务')
    }
    
    // 重置所有状态
    setNewRole('')
    setProgress(null)
    setCreateDone(false)
    setCreating(false)
    setShowAvatarPrompt(false)
    setShowAvatarCrop(false)
    setAvatarProcessed(false)
    if (avatarToProcess) {
      URL.revokeObjectURL(avatarToProcess)
    }
    setAvatarToProcess('')
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

      {/* 头像裁剪提示 */}
      {showAvatarPrompt && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            zIndex: 10001,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: '12px',
              padding: '24px',
              maxWidth: '500px',
              width: '90%',
            }}
          >
            <h3 style={{ margin: '0 0 16px', fontSize: '18px', fontWeight: 600 }}>
              🎭 检测到角色头像
            </h3>
            <p style={{ margin: '0 0 20px', color: '#6b7280', lineHeight: 1.6 }}>
              我们为您的角色找到了头像图片。由于爬取的图片可能不是正方形，建议您裁剪调整以获得最佳显示效果。
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleSkipCrop}
                style={{
                  flex: 1,
                  padding: '10px',
                  background: '#f3f4f6',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#374151',
                }}
              >
                使用原图
              </button>
              <button
                onClick={handleStartCrop}
                style={{
                  flex: 1,
                  padding: '10px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#fff',
                }}
              >
                裁剪调整
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 图片裁剪器 */}
      {showAvatarCrop && avatarToProcess && (
        <ImageCropper
          image={avatarToProcess}
          onCropComplete={handleAvatarCropComplete}
          onCancel={handleSkipCrop}
        />
      )}
    </div>
  )
}

