import { useAdmin } from '../../contexts/AdminContext'
import { useAuth } from '../../contexts/AuthContext'

export function AdminPanel() {
  const { user, api } = useAuth()
  const {
    adminUsers,
    adminSelectedUser,
    setAdminSelectedUser,
    adminUserChars,
    setAdminUserChars,
    adminSelectedChar,
    setAdminSelectedChar,
    adminMessages,
    adminTab,
    setAdminTab,
    adminSearchQuery,
    setAdminSearchQuery,
    adminUserGroups,
    adminSelectedGroup,
    adminGroupMessages,
    adminFeedbacks,
    adminSelectedFeedback,
    setAdminSelectedFeedback,
    feedbackReply,
    setFeedbackReply,
    feedbackStatus,
    setFeedbackStatus,
    setShowInspect,
    setInspectText,
    loadAdminUser,
    loadAdminUserGroups,
    loadAdminGroup,
    loadAdminFeedbacks,
    loadAdminFeedback,
    updateFeedbackStatus,
    deleteFeedback,
    loadAdminChar,
    cleanupAdminUserChars,
    refreshAdminData,
  } = useAdmin()

  return (
    <div className="admin-page">
      <div className="admin-header">
        <div className="admin-tabs">
          <button
            className={adminTab === 'users' ? 'active' : ''}
            onClick={() => {
              setAdminTab('users')
              setAdminSelectedUser(null)
              setAdminUserChars([])
              setAdminSelectedChar(null)
            }}
          >
            用户列表
          </button>
          <button className={adminTab === 'characters' ? 'active' : ''} onClick={() => setAdminTab('characters')} disabled={!adminSelectedUser}>
            角色列表 {adminSelectedUser ? `(${adminSelectedUser.username})` : ''}
          </button>
          <button className={adminTab === 'groups' ? 'active' : ''} onClick={() => setAdminTab('groups')} disabled={!adminSelectedUser}>
            群聊列表 {adminSelectedUser ? `(${adminSelectedUser.username})` : ''}
          </button>
          <button className={adminTab === 'feedbacks' ? 'active' : ''} onClick={() => loadAdminFeedbacks()}>
            用户反馈
          </button>
          <button className={adminTab === 'detail' ? 'active' : ''} onClick={() => setAdminTab('detail')} disabled={!adminSelectedChar}>
            详情 {adminSelectedChar ? `(${adminSelectedChar.name})` : ''}
          </button>
        </div>
        <div className="admin-actions">
          <input type="text" placeholder="搜索..." value={adminSearchQuery} onChange={e => setAdminSearchQuery(e.target.value)} className="admin-search" />
          <button onClick={refreshAdminData} className="settings">
            刷新数据
          </button>
          {adminTab === 'characters' && adminSelectedUser && (
            <button onClick={() => cleanupAdminUserChars(adminSelectedUser.id)} className="settings">
              清理无效角色
            </button>
          )}
        </div>
      </div>

      {adminTab === 'users' && (
        <div className="admin-content">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户名</th>
                <th>创建时间</th>
                <th>角色</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {adminUsers
                .filter(u => !adminSearchQuery || u.username.toLowerCase().includes(adminSearchQuery.toLowerCase()) || String(u.id).includes(adminSearchQuery))
                .map(u => (
                  <tr key={u.id}>
                    <td>#{u.id}</td>
                    <td>
                      {u.username} {u.is_admin ? <span className="badge">管理员</span> : ''}
                    </td>
                    <td>{new Date(u.created_at * 1000).toLocaleString()}</td>
                    <td>-</td>
                    <td>
                      <button onClick={() => loadAdminUser(u.id)} className="btn-link">
                        查看角色
                      </button>
                      {' | '}
                      <button onClick={() => loadAdminUserGroups(u.id)} className="btn-link">
                        查看群聊
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div className="admin-card-list">
            {adminUsers
              .filter(u => !adminSearchQuery || u.username.toLowerCase().includes(adminSearchQuery.toLowerCase()) || String(u.id).includes(adminSearchQuery))
              .map(u => (
                <div key={u.id} className="admin-card" onClick={() => loadAdminUser(u.id)}>
                  <div className="admin-card-header">
                    <div>
                      <div className="admin-card-title">{u.username}</div>
                      <div className="admin-card-id">#{u.id}</div>
                    </div>
                    {u.is_admin ? <span className="badge">管理员</span> : null}
                  </div>
                  <div className="admin-card-meta">
                    <div className="admin-card-row">
                      <span className="admin-card-label">创建时间</span>
                      <span className="admin-card-value">{new Date(u.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {adminTab === 'characters' && adminSelectedUser && (
        <div className="admin-content">
          <div className="admin-content-header">
            <h3>用户 "{adminSelectedUser.username}" 的角色列表</h3>
            <div className="muted">共 {adminUserChars.length} 个角色</div>
          </div>
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>角色名称</th>
                <th>模型</th>
                <th>来源</th>
                <th>最后更新</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {adminUserChars
                .filter(c => !adminSearchQuery || c.name.toLowerCase().includes(adminSearchQuery.toLowerCase()) || String(c.id).includes(adminSearchQuery))
                .map(c => (
                  <tr key={c.id}>
                    <td>#{c.id}</td>
                    <td>{c.name}</td>
                    <td>
                      <span className="muted">{c.model || '-'}</span>
                    </td>
                    <td>
                      <span className="muted">{c.source || '-'}</span>
                    </td>
                    <td>{new Date(c.updated_at * 1000).toLocaleString()}</td>
                    <td>
                      <button onClick={() => loadAdminChar(adminSelectedUser.id, c.id)} className="btn-link">
                        查看详情
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div className="admin-card-list">
            {adminUserChars
              .filter(c => !adminSearchQuery || c.name.toLowerCase().includes(adminSearchQuery.toLowerCase()) || String(c.id).includes(adminSearchQuery))
              .map(c => (
                <div key={c.id} className="admin-card" onClick={() => loadAdminChar(adminSelectedUser.id, c.id)}>
                  <div className="admin-card-header">
                    <div>
                      <div className="admin-card-title">{c.name}</div>
                      <div className="admin-card-id">#{c.id}</div>
                    </div>
                  </div>
                  <div className="admin-card-meta">
                    <div className="admin-card-row">
                      <span className="admin-card-label">模型</span>
                      <span className="admin-card-value">{c.model || '-'}</span>
                    </div>
                    <div className="admin-card-row">
                      <span className="admin-card-label">来源</span>
                      <span className="admin-card-value">{c.source || '-'}</span>
                    </div>
                    <div className="admin-card-row">
                      <span className="admin-card-label">最后更新</span>
                      <span className="admin-card-value">{new Date(c.updated_at * 1000).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {adminTab === 'groups' && adminSelectedUser && (
        <div className="admin-content">
          <div className="admin-content-header">
            <h3>用户 "{adminSelectedUser.username}" 的群聊列表</h3>
            <div className="muted">共 {adminUserGroups.length} 个群聊</div>
          </div>
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>群聊名称</th>
                <th>成员数量</th>
                <th>创建时间</th>
                <th>最后更新</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {adminUserGroups
                .filter(g => !adminSearchQuery || g.name.toLowerCase().includes(adminSearchQuery.toLowerCase()) || String(g.id).includes(adminSearchQuery))
                .map(g => (
                  <tr key={g.id}>
                    <td>#{g.id}</td>
                    <td>{g.name}</td>
                    <td>
                      <span className="muted">{g.member_count || 0} 人</span>
                    </td>
                    <td>{new Date(g.created_at * 1000).toLocaleString()}</td>
                    <td>{new Date(g.updated_at * 1000).toLocaleString()}</td>
                    <td>
                      <button onClick={() => loadAdminGroup(g.id)} className="btn-link">
                        查看详情
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div className="admin-card-list">
            {adminUserGroups
              .filter(g => !adminSearchQuery || g.name.toLowerCase().includes(adminSearchQuery.toLowerCase()) || String(g.id).includes(adminSearchQuery))
              .map(g => (
                <div key={g.id} className="admin-card" onClick={() => loadAdminGroup(g.id)}>
                  <div className="admin-card-header">
                    <div>
                      <div className="admin-card-title">{g.name}</div>
                      <div className="admin-card-id">#{g.id}</div>
                    </div>
                  </div>
                  <div className="admin-card-meta">
                    <div className="admin-card-row">
                      <span className="admin-card-label">成员数量</span>
                      <span className="admin-card-value">{g.member_count || 0} 人</span>
                    </div>
                    <div className="admin-card-row">
                      <span className="admin-card-label">创建时间</span>
                      <span className="admin-card-value">{new Date(g.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                    <div className="admin-card-row">
                      <span className="admin-card-label">最后更新</span>
                      <span className="admin-card-value">{new Date(g.updated_at * 1000).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
          {adminSelectedGroup && (
            <div className="admin-detail-page" style={{ marginTop: '2rem' }}>
              <div className="admin-detail-header">
                <h3>{adminSelectedGroup.name}</h3>
                <div className="muted">ID: #{adminSelectedGroup.id}</div>
              </div>
              <div className="admin-detail-section">
                <h4>成员列表 ({adminSelectedGroup.members?.length || 0} 人)</h4>
                <div className="member-list">
                  {adminSelectedGroup.members?.map((member: any, idx: number) => (
                    <div key={idx} className="member-item">
                      <div className="member-avatar">{member.is_moderator ? '🎭' : '👤'}</div>
                      <div className="member-info">
                        <span className="member-name">
                          {member.member_name}
                          {member.is_moderator ? <span className="badge">主持人</span> : null}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="admin-detail-section">
                <h4>群聊记录 ({adminGroupMessages.length} 条)</h4>
                <div className="admin-msgs">
                  {adminGroupMessages.map((m, i) => {
                    const mid = (m as any).id as number | undefined
                    const msgType = m.sender_type === 'user' ? 'user-msg' : m.sender_type === 'moderator' ? 'moderator-msg' : 'character-msg'
                    const avatar = m.sender_type === 'user' ? '👤' : m.sender_type === 'moderator' ? '🎭' : '🤖'
                    const displayName = m.sender_name || (m.sender_type === 'user' ? adminSelectedUser?.username || '用户' : '未知')
                    const badgeText = m.sender_type === 'user' ? '用户' : m.sender_type === 'moderator' ? '主持人' : '角色'
                    return (
                      <div key={i} className={`admin-group-msg ${msgType}`}>
                        <div className="msg-avatar">{avatar}</div>
                        <div className="msg-body">
                          <div className="msg-meta">
                            <span className="msg-sender">{displayName}</span>
                            <span className="msg-badge">{badgeText}</span>
                            {mid && <span className="msg-id">#{mid}</span>}
                          </div>
                          <div className="msg-text">{m.content}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {adminTab === 'detail' && adminSelectedChar && (
        <div className="admin-content">
          <div className="admin-detail-page">
            <div className="admin-detail-header">
              <h3>{adminSelectedChar.name}</h3>
              <div className="muted">ID: #{adminSelectedChar.id}</div>
            </div>
            <div className="admin-detail-section">
              <h4>结构化 JSON</h4>
              <pre className="json-view">{adminSelectedChar.structured_json || '（无）'}</pre>
            </div>
            <div className="admin-detail-section">
              <h4>聊天记录 ({adminMessages.length} 条)</h4>
              <div className="admin-msgs">
                {adminMessages.map((m, i) => {
                  const mid = (m as any).id as number | undefined
                  const canInspect = user?.is_admin === 1 && m.role === 'user' && adminSelectedUser && adminSelectedChar
                  const msgType = m.role === 'user' ? 'user-msg' : 'character-msg'
                  const avatar = m.role === 'user' ? '👤' : '🤖'
                  const senderName = m.role === 'user' ? adminSelectedUser?.username || '用户' : adminSelectedChar.name
                  const badgeText = m.role === 'user' ? '用户' : '角色'

                  return (
                    <div key={i} className={`admin-group-msg ${msgType}`}>
                      <div className="msg-avatar">{avatar}</div>
                      <div className="msg-body">
                        <div className="msg-meta">
                          <span className="msg-sender">{senderName}</span>
                          <span className="msg-badge">{badgeText}</span>
                          {mid && <span className="msg-id">#{mid}</span>}
                        </div>
                        <div className="msg-text">{m.content}</div>
                        {canInspect && mid ? (
                          <button
                            className="admin-inspect-btn"
                            onClick={async () => {
                              try {
                                const { data } = await api.get('/admin/chat/compiled', {
                                  params: { uid: adminSelectedUser!.id, cid: adminSelectedChar!.id, msg_id: mid, role: adminSelectedChar!.name },
                                })
                                const pretty = JSON.stringify(data, null, 2)
                                setInspectText(pretty)
                                setShowInspect(true)
                              } catch (e: any) {
                                alert(e?.response?.data?.error || '获取失败')
                              }
                            }}
                          >
                            📋 查看完整提示词
                          </button>
                        ) : null}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {adminTab === 'feedbacks' && (
        <div className="admin-content">
          <div className="admin-content-header">
            <h3>用户反馈</h3>
            <div className="muted">共 {adminFeedbacks.length} 条反馈</div>
          </div>
          {!adminSelectedFeedback ? (
            <>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>用户</th>
                    <th>标题</th>
                    <th>状态</th>
                    <th>提交时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {adminFeedbacks
                    .filter(f => !adminSearchQuery || f.title.toLowerCase().includes(adminSearchQuery.toLowerCase()) || f.username.toLowerCase().includes(adminSearchQuery.toLowerCase()))
                    .map(f => (
                      <tr key={f.id}>
                        <td>#{f.id}</td>
                        <td>{f.username}</td>
                        <td>{f.title}</td>
                        <td>
                          <span className={`feedback-status ${f.status}`}>
                            {f.status === 'pending' ? '待处理' : f.status === 'in_progress' ? '处理中' : f.status === 'resolved' ? '已解决' : '已拒绝'}
                          </span>
                        </td>
                        <td>{new Date(f.created_at * 1000).toLocaleString()}</td>
                        <td>
                          <button onClick={() => loadAdminFeedback(f.id)} className="btn-link">
                            查看详情
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              <div className="admin-card-list">
                {adminFeedbacks
                  .filter(f => !adminSearchQuery || f.title.toLowerCase().includes(adminSearchQuery.toLowerCase()) || f.username.toLowerCase().includes(adminSearchQuery.toLowerCase()))
                  .map(f => (
                    <div key={f.id} className="admin-card" onClick={() => loadAdminFeedback(f.id)}>
                      <div className="admin-card-header">
                        <div>
                          <div className="admin-card-title">{f.title}</div>
                          <div className="admin-card-id">#{f.id}</div>
                        </div>
                        <span className={`feedback-status ${f.status}`}>
                          {f.status === 'pending' ? '待处理' : f.status === 'in_progress' ? '处理中' : f.status === 'resolved' ? '已解决' : '已拒绝'}
                        </span>
                      </div>
                      <div className="admin-card-meta">
                        <div className="admin-card-row">
                          <span className="admin-card-label">用户</span>
                          <span className="admin-card-value">{f.username}</span>
                        </div>
                        <div className="admin-card-row">
                          <span className="admin-card-label">提交时间</span>
                          <span className="admin-card-value">{new Date(f.created_at * 1000).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </>
          ) : (
            <div className="admin-detail-page">
              <div className="admin-detail-header">
                <h3>{adminSelectedFeedback.title}</h3>
                <div>
                  <button onClick={() => setAdminSelectedFeedback(null)} className="settings">
                    返回列表
                  </button>
                </div>
              </div>
              <div className="admin-detail-section">
                <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                  <div>
                    <strong>反馈ID:</strong> #{adminSelectedFeedback.id}
                  </div>
                  <div>
                    <strong>用户:</strong> {adminSelectedFeedback.username}
                  </div>
                  <div>
                    <strong>提交时间:</strong> {new Date(adminSelectedFeedback.created_at * 1000).toLocaleString()}
                  </div>
                </div>
                <h4>反馈内容</h4>
                <div className="feedback-content">{adminSelectedFeedback.content}</div>
                {adminSelectedFeedback.attachments && JSON.parse(adminSelectedFeedback.attachments).length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <h4>附件图片</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '12px' }}>
                      {JSON.parse(adminSelectedFeedback.attachments).map((url: string, idx: number) => (
                        <a key={idx} href={url} target="_blank" rel="noreferrer">
                          <img src={url} alt="" style={{ width: '150px', height: '150px', objectFit: 'cover', borderRadius: '8px', border: '1px solid var(--border)' }} />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="admin-detail-section">
                <h4>管理员回复</h4>
                <label>
                  状态
                  <select value={feedbackStatus} onChange={e => setFeedbackStatus(e.target.value as any)}>
                    <option value="pending">待处理</option>
                    <option value="in_progress">处理中</option>
                    <option value="resolved">已解决</option>
                    <option value="rejected">已拒绝</option>
                  </select>
                </label>
                <label>
                  回复内容
                  <textarea
                    value={feedbackReply}
                    onChange={e => setFeedbackReply(e.target.value)}
                    placeholder="给用户的回复..."
                    rows={6}
                    style={{ width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '8px', resize: 'vertical' }}
                  />
                </label>
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                  <button className="primary" onClick={() => updateFeedbackStatus(adminSelectedFeedback.id)}>
                    保存更新
                  </button>
                  <button onClick={() => deleteFeedback(adminSelectedFeedback.id)} style={{ background: '#ef4444', color: 'white' }}>
                    删除反馈
                  </button>
                </div>
                {adminSelectedFeedback.admin_reply && (
                  <div style={{ marginTop: '16px', padding: '12px', background: '#f3f4f6', borderRadius: '8px' }}>
                    <strong>当前回复:</strong>
                    <div style={{ marginTop: '8px' }}>{adminSelectedFeedback.admin_reply}</div>
                    <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280' }}>更新时间: {new Date(adminSelectedFeedback.updated_at * 1000).toLocaleString()}</div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

