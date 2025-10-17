import { useState, useEffect } from 'react'
import type { Feedback } from '../types'
import { useAuth } from '../contexts/AuthContext'

interface FeedbackModalProps {
  show: boolean
  onClose: () => void
}

export function FeedbackModal({ show, onClose }: FeedbackModalProps) {
  const { api } = useAuth()
  
  const [feedbackTitle, setFeedbackTitle] = useState('')
  const [feedbackContent, setFeedbackContent] = useState('')
  const [feedbackAttachments, setFeedbackAttachments] = useState<string[]>([])
  const [feedbackUploading, setFeedbackUploading] = useState(false)
  const [feedbackTab, setFeedbackTab] = useState<'submit' | 'history'>('submit')
  const [myFeedbacks, setMyFeedbacks] = useState<Feedback[]>([])
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null)

  useEffect(() => {
    if (show && feedbackTab === 'history') {
      loadMyFeedbacks()
    }
  }, [show, feedbackTab])

  async function handleFeedbackImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      alert('只支持图片格式')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('图片大小不能超过5MB')
      return
    }

    try {
      setFeedbackUploading(true)
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post('/api/feedbacks/upload', formData)
      setFeedbackAttachments([...feedbackAttachments, data.url])
    } catch (e: any) {
      alert(e?.response?.data?.error || '上传失败')
    } finally {
      setFeedbackUploading(false)
    }
  }

  async function loadMyFeedbacks() {
    try {
      const { data } = await api.get('/api/feedbacks')
      setMyFeedbacks(data.items || [])
    } catch (e: any) {
      console.error('加载反馈记录失败:', e)
    }
  }

  async function submitFeedback() {
    if (!feedbackTitle.trim()) {
      alert('请填写反馈标题')
      return
    }
    if (!feedbackContent.trim()) {
      alert('请填写反馈内容')
      return
    }

    try {
      const attachments = feedbackAttachments.length > 0 ? JSON.stringify(feedbackAttachments) : null
      await api.post('/api/feedbacks', {
        title: feedbackTitle,
        content: feedbackContent,
        attachments,
      })
      alert('反馈提交成功！感谢您的反馈')
      setFeedbackTitle('')
      setFeedbackContent('')
      setFeedbackAttachments([])
      setFeedbackTab('history')
      await loadMyFeedbacks()
    } catch (e: any) {
      alert(e?.response?.data?.error || '提交失败')
    }
  }

  function handleClose() {
    setFeedbackTitle('')
    setFeedbackContent('')
    setFeedbackAttachments([])
    setSelectedFeedback(null)
    onClose()
  }

  if (!show) return null

  return (
    <div className="modal" onClick={handleClose}>
      <div className="dialog feedback-dialog" onClick={e => e.stopPropagation()}>
        <div className="feedback-header">
          <h3>💬 用户反馈</h3>
          <button className="close-btn" onClick={handleClose}>
            ×
          </button>
        </div>

        <div className="feedback-tabs">
          <button
            className={feedbackTab === 'submit' ? 'active' : ''}
            onClick={() => {
              setFeedbackTab('submit')
              setSelectedFeedback(null)
            }}
          >
            ✍️ 提交反馈
          </button>
          <button className={feedbackTab === 'history' ? 'active' : ''} onClick={() => setFeedbackTab('history')}>
            📋 我的反馈 {myFeedbacks.length > 0 && `(${myFeedbacks.length})`}
          </button>
        </div>

        {feedbackTab === 'submit' ? (
          <div className="feedback-content">
            <label>
              标题
              <input type="text" value={feedbackTitle} onChange={e => setFeedbackTitle(e.target.value)} placeholder="请简要描述问题" />
            </label>
            <label>
              详细内容
              <textarea
                value={feedbackContent}
                onChange={e => setFeedbackContent(e.target.value)}
                placeholder="请详细描述您遇到的问题或建议"
                rows={6}
                style={{ width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '8px', resize: 'vertical' }}
              />
            </label>
            <label>
              上传图片（可选）
              <input type="file" accept="image/*" onChange={handleFeedbackImageUpload} disabled={feedbackUploading} />
              {feedbackUploading && <div style={{ marginTop: '8px', color: '#6b7280' }}>上传中...</div>}
            </label>
            {feedbackAttachments.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>已上传的图片：</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                  {feedbackAttachments.map((url, idx) => (
                    <div key={idx} style={{ position: 'relative' }}>
                      <img
                        src={url}
                        alt={`附件${idx + 1}`}
                        style={{
                          width: '120px',
                          height: '120px',
                          objectFit: 'cover',
                          borderRadius: '8px',
                          border: '2px solid var(--border)',
                          cursor: 'pointer',
                        }}
                        onClick={() => window.open(url, '_blank')}
                        title="点击查看大图"
                      />
                      <button
                        onClick={() => setFeedbackAttachments(feedbackAttachments.filter((_, i) => i !== idx))}
                        style={{
                          position: 'absolute',
                          top: '-8px',
                          right: '-8px',
                          width: '24px',
                          height: '24px',
                          borderRadius: '50%',
                          background: '#ef4444',
                          color: 'white',
                          border: 'none',
                          cursor: 'pointer',
                          fontSize: '16px',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                        }}
                        title="删除"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="feedback-actions">
              <button onClick={handleClose} className="btn-secondary">
                取消
              </button>
              <button className="btn-primary" onClick={submitFeedback}>
                ✅ 提交反馈
              </button>
            </div>
          </div>
        ) : (
          <div className="feedback-content">
            {!selectedFeedback ? (
              <>
                {myFeedbacks.length === 0 ? (
                  <div className="empty-state">
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>📭</div>
                    <p style={{ color: '#6b7280' }}>暂无反馈记录</p>
                  </div>
                ) : (
                  <div className="feedback-list">
                    {myFeedbacks.map(fb => (
                      <div key={fb.id} className="feedback-item" onClick={() => setSelectedFeedback(fb)}>
                        <div className="feedback-item-header">
                          <h4>{fb.title}</h4>
                          <span className={`feedback-status ${fb.status}`}>
                            {fb.status === 'pending' ? '⏳ 待处理' : fb.status === 'in_progress' ? '🔄 处理中' : fb.status === 'resolved' ? '✅ 已解决' : '❌ 已拒绝'}
                          </span>
                        </div>
                        <p className="feedback-item-content">{fb.content}</p>
                        <div className="feedback-item-footer">
                          <span className="feedback-item-time">{new Date(fb.created_at * 1000).toLocaleString()}</span>
                          {fb.admin_reply && <span className="has-reply">💬 有回复</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="feedback-detail">
                <button onClick={() => setSelectedFeedback(null)} className="back-btn">
                  ← 返回列表
                </button>

                <div className="feedback-detail-header">
                  <h3>{selectedFeedback.title}</h3>
                  <span className={`feedback-status ${selectedFeedback.status}`}>
                    {selectedFeedback.status === 'pending'
                      ? '⏳ 待处理'
                      : selectedFeedback.status === 'in_progress'
                        ? '🔄 处理中'
                        : selectedFeedback.status === 'resolved'
                          ? '✅ 已解决'
                          : '❌ 已拒绝'}
                  </span>
                </div>

                <div className="feedback-detail-section">
                  <label>反馈内容</label>
                  <div className="feedback-text">{selectedFeedback.content}</div>
                </div>

                {selectedFeedback.attachments && JSON.parse(selectedFeedback.attachments).length > 0 && (
                  <div className="feedback-detail-section">
                    <label>附件图片</label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                      {JSON.parse(selectedFeedback.attachments).map((url: string, idx: number) => (
                        <a key={idx} href={url} target="_blank" rel="noreferrer">
                          <img
                            src={url}
                            alt={`附件${idx + 1}`}
                            style={{
                              width: '100px',
                              height: '100px',
                              objectFit: 'cover',
                              borderRadius: '6px',
                              border: '1px solid var(--border)',
                            }}
                          />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {selectedFeedback.admin_reply && (
                  <div className="feedback-detail-section admin-reply-section">
                    <label>📢 管理员回复</label>
                    <div className="admin-reply-box">{selectedFeedback.admin_reply}</div>
                    <div className="reply-time">回复时间: {new Date(selectedFeedback.updated_at * 1000).toLocaleString()}</div>
                  </div>
                )}

                <div className="feedback-detail-footer">
                  <span>提交时间: {new Date(selectedFeedback.created_at * 1000).toLocaleString()}</span>
                  <span>反馈ID: #{selectedFeedback.id}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

