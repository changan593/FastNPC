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
  const [feedbackTab, setFeedbackTab] = useState<'submit' | 'history'>('submit')
  const [myFeedbacks, setMyFeedbacks] = useState<Feedback[]>([])
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null)

  useEffect(() => {
    if (show && feedbackTab === 'history') {
      loadMyFeedbacks()
    }
  }, [show, feedbackTab])

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
      await api.post('/api/feedbacks', {
        title: feedbackTitle,
        content: feedbackContent,
      })
      alert('反馈提交成功！感谢您的反馈')
      setFeedbackTitle('')
      setFeedbackContent('')
      setFeedbackTab('history')
      await loadMyFeedbacks()
    } catch (e: any) {
      alert(e?.response?.data?.error || '提交失败')
    }
  }

  function handleClose() {
    setFeedbackTitle('')
    setFeedbackContent('')
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
                rows={8}
                style={{ width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '8px', resize: 'vertical' }}
              />
            </label>
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

