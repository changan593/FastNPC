import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { ImageCropper } from '../ImageCropper'

interface SettingsModalProps {
  show: boolean
  onClose: () => void
}

const allowedModels = [
  'z-ai/glm-4-32b',
  'z-ai/glm-4.5-air:free',
  'deepseek/deepseek-chat-v3.1:free',
  'tencent/hunyuan-a13b-instruct:free',
] as const

export function SettingsModal({ show, onClose }: SettingsModalProps) {
  const { api } = useAuth()

  const [defaultModel, setDefaultModel] = useState<string>('')
  const [ctxMaxChat, setCtxMaxChat] = useState<string>('')
  const [ctxMaxStm, setCtxMaxStm] = useState<string>('')
  const [ctxMaxLtm, setCtxMaxLtm] = useState<string>('')
  const [oldPwd, setOldPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [deletePwd, setDeletePwd] = useState('')
  const [userProfile, setUserProfile] = useState<string>('')
  const [maxGroupReplyRounds, setMaxGroupReplyRounds] = useState<string>('3')
  const [avatarUrl, setAvatarUrl] = useState<string>('')
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const [showCropper, setShowCropper] = useState(false)
  const [originalImage, setOriginalImage] = useState<string>('')

  useEffect(() => {
    if (show) {
      loadSettings()
    }
  }, [show])

  async function loadSettings() {
    try {
      const { data } = await api.get('/api/me/settings')
      const s = data.settings || {}
      setDefaultModel(s.default_model || '')
      setCtxMaxChat(s.ctx_max_chat != null ? String(s.ctx_max_chat) : '')
      setCtxMaxStm(s.ctx_max_stm != null ? String(s.ctx_max_stm) : '')
      setCtxMaxLtm(s.ctx_max_ltm != null ? String(s.ctx_max_ltm) : '')
      setUserProfile(s.profile || '')
      setMaxGroupReplyRounds(s.max_group_reply_rounds != null ? String(s.max_group_reply_rounds) : '3')
      
      // 加载用户头像
      try {
        const profileRes = await api.get('/api/user/profile')
        setAvatarUrl(profileRes.data.user?.avatar_url || '')
      } catch {}
    } catch {}
  }

  async function saveSettings() {
    try {
      await api.put('/api/me/settings', {
        default_model: defaultModel || null,
        ctx_max_chat: ctxMaxChat ? Number(ctxMaxChat) : null,
        ctx_max_stm: ctxMaxStm ? Number(ctxMaxStm) : null,
        ctx_max_ltm: ctxMaxLtm ? Number(ctxMaxLtm) : null,
        profile: userProfile || null,
        max_group_reply_rounds: maxGroupReplyRounds ? Number(maxGroupReplyRounds) : 3,
      })
      if (oldPwd && newPwd) {
        await api.put('/api/me/password', { old_password: oldPwd, new_password: newPwd })
        setOldPwd('')
        setNewPwd('')
      }
      alert('已保存')
      onClose()
    } catch (e: any) {
      alert(e?.response?.data?.error || '保存失败')
    }
  }

  async function deleteAccount() {
    if (!deletePwd.trim()) {
      alert('请输入密码确认')
      return
    }
    if (!confirm('确定注销账户吗？该操作不可恢复，将删除你的所有角色与消息。')) return
    try {
      const { data } = await api.post('/api/me/delete', { password: deletePwd })
      if (data?.ok) {
        alert('账户已注销')
        onClose()
        // 需要触发登出
        window.location.reload()
      }
    } catch (e: any) {
      alert(e?.response?.data?.error || '注销失败')
    }
  }

  async function handleAvatarSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      alert('请选择图片文件')
      return
    }

    // 验证文件大小（10MB）
    if (file.size > 10 * 1024 * 1024) {
      alert('图片大小不能超过10MB')
      return
    }

    // 读取文件并显示裁剪器
    const reader = new FileReader()
    reader.onload = () => {
      setOriginalImage(reader.result as string)
      setShowCropper(true)
    }
    reader.readAsDataURL(file)

    // 重置input，允许重新选择同一文件
    e.target.value = ''
  }

  async function handleCropComplete(croppedBlob: Blob) {
    setUploadingAvatar(true)
    setShowCropper(false)
    
    try {
      const formData = new FormData()
      formData.append('file', croppedBlob, 'avatar.jpg')

      const { data } = await api.post('/api/user/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (data?.ok && data.avatar_url) {
        setAvatarUrl(data.avatar_url)
        alert('头像上传成功')
      }
    } catch (e: any) {
      alert(e?.response?.data?.detail || '头像上传失败')
    } finally {
      setUploadingAvatar(false)
    }
  }

  function handleCropCancel() {
    setShowCropper(false)
    setOriginalImage('')
  }

  async function handleDeleteAvatar() {
    if (!confirm('确定删除头像吗？')) return

    try {
      const { data } = await api.delete('/api/user/avatar')
      if (data?.ok) {
        setAvatarUrl('')
        alert('头像已删除')
      }
    } catch (e: any) {
      alert(e?.response?.data?.detail || '删除头像失败')
    }
  }

  if (!show) return null

  return (
    <div className="modal">
      <div className="dialog">
        <h3>用户设置</h3>
        
        {/* 用户头像 */}
        <label>
          用户头像
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8 }}>
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: '8px',
                overflow: 'hidden',
                backgroundColor: '#f3f4f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '2px solid var(--border)',
              }}
            >
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt="用户头像"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <span style={{ fontSize: 40 }}>👤</span>
              )}
            </div>
            <div style={{ flex: 1 }}>
              <input
                type="file"
                accept="image/*"
                onChange={handleAvatarSelect}
                disabled={uploadingAvatar}
                style={{ marginBottom: 8 }}
              />
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
                支持JPG、PNG等格式，最大10MB，上传后可裁剪
              </div>
              {avatarUrl && (
                <button
                  onClick={handleDeleteAvatar}
                  style={{ fontSize: 12, padding: '4px 8px' }}
                >
                  删除头像
                </button>
              )}
            </div>
          </div>
        </label>
        
        <label>
          默认模型
          <select value={defaultModel} onChange={e => setDefaultModel(e.target.value)}>
            <option value="">（使用系统/环境默认）</option>
            {allowedModels.map(m => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label>
          上下文预算（字符）
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>可选范围: 50-5000</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <input type="number" min={50} max={5000} placeholder="会话记忆（默认 3000）" value={ctxMaxChat} onChange={e => setCtxMaxChat(e.target.value)} />
            <input type="number" min={50} max={5000} placeholder="短期记忆（默认 3000）" value={ctxMaxStm} onChange={e => setCtxMaxStm(e.target.value)} />
            <input type="number" min={50} max={5000} placeholder="长期记忆（默认 4000）" value={ctxMaxLtm} onChange={e => setCtxMaxLtm(e.target.value)} />
          </div>
        </label>
        <label>
          个人简介（用于群聊）
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
            {userProfile.length}/200 字
          </div>
          <textarea
            value={userProfile}
            onChange={e => setUserProfile(e.target.value)}
            placeholder="简单介绍自己，用于群聊中其他角色了解你"
            maxLength={200}
            rows={3}
            style={{ width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '8px', boxSizing: 'border-box', resize: 'vertical' }}
          />
        </label>
        <label>
          群聊最大角色回复轮数
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>可选范围: 3-10（默认3）</div>
          <input type="number" min={3} max={10} value={maxGroupReplyRounds} onChange={e => setMaxGroupReplyRounds(e.target.value)} placeholder="默认3" />
          <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>角色连续发言达到此轮数后，将等待用户输入</div>
        </label>
        {/* 模型回退顺序由系统随机，不提供手动设置 */}
        <label>
          修改密码
          <input type="password" placeholder="原密码" value={oldPwd} onChange={e => setOldPwd(e.target.value)} />
          <input type="password" placeholder="新密码（≥6位）" value={newPwd} onChange={e => setNewPwd(e.target.value)} />
        </label>
        <label>
          注销账户（请输入当前密码以确认）
          <input type="password" placeholder="当前密码" value={deletePwd} onChange={e => setDeletePwd(e.target.value)} />
          <button style={{ marginTop: 8 }} onClick={deleteAccount}>
            确认注销
          </button>
        </label>
        <div className="actions">
          <button onClick={onClose}>关闭</button>
          <button className="primary" onClick={saveSettings}>
            保存
          </button>
        </div>
      </div>

      {/* 图片裁剪器 */}
      {showCropper && originalImage && (
        <ImageCropper
          image={originalImage}
          onCropComplete={handleCropComplete}
          onCancel={handleCropCancel}
        />
      )}
    </div>
  )
}

