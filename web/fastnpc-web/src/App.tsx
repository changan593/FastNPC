import { useEffect, useState, useRef } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CharacterProvider, useCharacter } from './contexts/CharacterContext'
import { GroupProvider, useGroup } from './contexts/GroupContext'
import { AdminProvider, useAdmin } from './contexts/AdminContext'
import { AuthView } from './components/AuthView'
import { Sidebar } from './components/Sidebar'
import { InfoPanel } from './components/InfoPanel'
import { FeedbackModal } from './components/FeedbackModal'
import { InspectModal } from './components/modals/InspectModal'
import { SettingsModal } from './components/modals/SettingsModal'
import { CreateGroupModal } from './components/modals/CreateGroupModal'
import { CreateCharacterModal } from './components/modals/CreateCharacterModal'
import { PolysemantModal } from './components/modals/PolysemantModal'
import { ManageGroupModal } from './components/modals/ManageGroupModal'
import { ManageCharModal } from './components/modals/ManageCharModal'
import { AdminPanel } from './components/admin/AdminPanel'
import { PromptManagementModal } from './components/modals/PromptManagementModal'

function AppContent() {
  const { user, api } = useAuth()
  const {
    characters,
    setCharacters,
    activeRole,
    setActiveRole,
    messages,
    setMessages,
    input,
    setInput,
    typingStatus,
    setTypingStatus,
    showCreate,
    setShowCreate,
    newRole,
    newSource,
    polyChoiceIdx,
    setPolyChoiceIdx,
    setPolyChoiceHref,
    setPolyFilter,
    showPoly,
    setShowPoly,
    polyOptions,
    setPolyOptions,
    polyLoading,
    setPolyLoading,
    polyRoute,
    setPolyRoute,
    polyReqSeqRef,
    charIntro,
    showManageChar,
    setShowManageChar,
    send,
    reloadMessages,
    loadCharBrief,
    createRole,
  } = useCharacter()

  const {
    groups,
    setGroups,
    activeGroupId,
    setActiveGroupId,
    groupMessages,
    groupMemberBriefs,
    showCreateGroup,
    setShowCreateGroup,
    newGroupName,
    setNewGroupName,
    selectedMembers,
    setSelectedMembers,
    showManageGroup,
    setShowManageGroup,
    typingStatus: groupTypingStatus,
    reloadGroupMessages,
    loadGroupMemberBriefs,
    sendGroupMessage,
    handleUserTyping,
  } = useGroup()

  const {
    adminView,
    setAdminView,
    setAdminUsers,
    showInspect,
    setShowInspect,
    inspectText,
    setInspectText,
    openAdmin,
  } = useAdmin()

  const [activeType, setActiveType] = useState<'character' | 'group'>('character')
  const [showSettings, setShowSettings] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)
  const [maxGroupReplyRounds, setMaxGroupReplyRounds] = useState<string>('3')
  const [userAvatarUrl, setUserAvatarUrl] = useState<string>('')
  const [showPromptManagement, setShowPromptManagement] = useState(false)

  const chatBodyRef = useRef<HTMLDivElement | null>(null)
  const prevActiveRoleRef = useRef<string>('')
  const prevActiveGroupRef = useRef<number | null>(null)

  // 加载初始数据
  async function loadInitialData() {
      try {
        const me = await api.get('/auth/me')
      const [chars, grps] = await Promise.all([api.get('/api/characters'), api.get('/api/groups')])
        
        setCharacters(chars.data.items || [])
        setGroups(grps.data.items || [])
        
        if (me.data?.is_admin === 1) {
          try {
            const { data } = await api.get('/admin/users')
            if (data?.items) setAdminUsers(data.items)
          } catch {}
        }
        
        if (chars.data.items?.length && !activeRole && !activeGroupId) {
          setActiveRole(chars.data.items[0].role)
          setActiveType('character')
        }

      // 加载用户设置和头像
      const { data: settings } = await api.get('/api/me/settings')
      const s = settings.settings || {}
      setMaxGroupReplyRounds(s.max_group_reply_rounds != null ? String(s.max_group_reply_rounds) : '3')
      
      // 加载用户头像
      try {
        const { data: profile } = await api.get('/api/user/profile')
        setUserAvatarUrl(profile.user?.avatar_url || '')
      } catch {}
    } catch (e: any) {
        if (e?.response?.status === 401) {
        // 未登录，清空所有状态
          setCharacters([])
          setGroups([])
          setMessages([])
          setActiveRole('')
          setActiveGroupId(null)
          setAdminUsers([])
          setAdminView(false)
      }
    }
  }

  useEffect(() => {
    loadInitialData()
  }, [])

  // 监听角色/群聊切换
  useEffect(() => {
    console.log(`[DEBUG] useEffect触发 - activeType=${activeType}, activeGroupId=${activeGroupId}, activeRole=${activeRole}`)

    // 离开上一个单聊时压缩记忆（异步，不阻塞）
    if (prevActiveRoleRef.current && prevActiveRoleRef.current !== activeRole) {
      console.log(`[INFO] 切换单聊，压缩记忆: ${prevActiveRoleRef.current}`)
      api.post(`/api/chat/${prevActiveRoleRef.current}/compress-all`).catch(() => {
        console.log(`[INFO] 压缩单聊记忆: ${prevActiveRoleRef.current}`)
      })
    }

    // 离开上一个群聊时压缩记忆（异步，不阻塞）
    if (prevActiveGroupRef.current && prevActiveGroupRef.current !== activeGroupId) {
      console.log(`[INFO] 切换群聊，压缩记忆: ${prevActiveGroupRef.current}`)
      api.post(`/api/groups/${prevActiveGroupRef.current}/compress-memories`).catch(() => {
        console.log(`[INFO] 压缩群聊记忆: ${prevActiveGroupRef.current}`)
      })
    }

    // 更新当前活动的角色/群聊
    prevActiveRoleRef.current = activeRole || ''
    prevActiveGroupRef.current = activeGroupId

    setTypingStatus('')

    // 优化：并行加载，提升速度
    if (activeType === 'group' && activeGroupId) {
      Promise.all([
        reloadGroupMessages(),
        loadGroupMemberBriefs()
      ]).catch(err => console.error('加载群聊数据失败:', err))
    } else if (activeType === 'character' && activeRole) {
      // 显示加载提示
      setTypingStatus('加载中...')
      Promise.all([
        reloadMessages(),
        loadCharBrief()
      ]).then(() => {
        setTypingStatus('')
      }).catch(err => {
        console.error('加载角色数据失败:', err)
        setTypingStatus('')
      })
    }
  }, [activeType, activeGroupId, activeRole])

  // 自动滚动到聊天底部
  useEffect(() => {
    try {
      const el = chatBodyRef.current
      if (!el) return
      el.scrollTop = el.scrollHeight
    } catch {}
  }, [messages, groupMessages, adminView])

  // 打开消歧弹窗
  async function openPolyModal() {
    if (!newRole.trim()) {
      alert('请先填写角色名')
      return
    }
    setShowPoly(true)
    setPolyLoading(true)
    const seq = Date.now()
    polyReqSeqRef.current = seq
    const endpoint = newSource === 'zhwiki' ? '/api/zhwiki/polysemant' : '/api/baike/polysemant'
    const limit = newSource === 'zhwiki' ? 80 : 200
    const normalize = (arr: any[]) => (arr || []).map((it: any) => ({ text: it.text || it.title || '', href: it.href || '', snippet: (it.snippet || '').replace(/<[^>]+>/g, '') }))
    try {
      const { data } = await api.get(endpoint, { params: { keyword: newRole.trim(), limit } })
      if (polyReqSeqRef.current !== seq) return
      const items = normalize(data.items || [])
      setPolyOptions(items)
      setPolyRoute(data?.route || '')
      if (!Array.isArray(data.items) || data.items.length === 0) {
        setTimeout(async () => {
          try {
            if (polyReqSeqRef.current !== seq) return
            const r2 = await api.get(endpoint, { params: { keyword: newRole.trim(), limit } })
            if (polyReqSeqRef.current !== seq) return
            setPolyOptions(normalize(r2.data.items || []))
            setPolyRoute(r2.data?.route || '')
          } catch {}
        }, 600)
      }
    } catch (e: any) {
      console.error(e)
      alert(e?.response?.data?.error || '获取候选失败')
    } finally {
      if (polyReqSeqRef.current === seq) setPolyLoading(false)
    }
  }

  // 处理创建角色（需要先打开消歧）
  async function handleCreateRole() {
    if (!newRole.trim()) return
    if ((newSource === 'baike' || newSource === 'zhwiki') && polyChoiceIdx == null) {
      await openPolyModal()
      return
    }
    await createRole()
  }

  // 处理创建群聊成功
  async function handleGroupCreated(groupId: number) {
    const grps = await api.get('/api/groups')
    setGroups(grps.data.items || [])
    setActiveType('group')
    setActiveGroupId(groupId)
    setActiveRole('')
  }

  // 处理删除群聊
  async function handleDeleteGroup() {
    if (!confirm('确定删除该群聊？删除后无法恢复！')) return
    try {
      await api.delete(`/api/groups/${activeGroupId}`)
      const { data } = await api.get('/api/groups')
      setGroups(data.items || [])
      setShowManageGroup(false)
      setActiveType('character')
      setActiveGroupId(null)
      if (characters.length > 0) {
        setActiveRole(characters[0].role)
      }
    } catch (e: any) {
      alert(e?.response?.data?.error || '删除失败')
    }
  }

  // 未登录显示认证视图
  if (!user) {
    return <AuthView onLoginSuccess={loadInitialData} />
  }

  return (
    <div className={`layout ${showMobileSidebar ? 'mobile-sidebar-open' : ''}`}>
      <div className="mobile-overlay" onClick={() => setShowMobileSidebar(false)}></div>

      <Sidebar
        characters={characters}
        groups={groups}
        activeType={activeType}
        setActiveType={setActiveType}
        activeRole={activeRole}
        setActiveRole={setActiveRole}
        activeGroupId={activeGroupId}
        setActiveGroupId={setActiveGroupId}
        onCreateCharacter={() => {
          // 清空同名词选择状态和选项列表
          setPolyChoiceIdx(null)
          setPolyChoiceHref('')
          setPolyFilter('')
          setPolyOptions([])  // 清空旧的同名词列表
          setShowCreate(true)
        }}
        onCreateGroup={() => setShowCreateGroup(true)}
      />

      {/* 主聊天区域 - 这里保留原有的复杂逻辑 */}
      {activeType === 'group' && activeGroupId && !adminView ? (
        <main className="chat">
          <header className="chat-head">
            <button className="mobile-menu-btn" onClick={() => setShowMobileSidebar(true)} style={{ display: 'none' }}>
              ☰
            </button>
            <div className="title">
              {groups.find(g => g.id === activeGroupId)?.name || '群聊'}
              <span style={{ fontSize: 12, color: 'var(--muted)', marginLeft: 8 }}>({groupMemberBriefs.length} 成员)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="muted">{user.username}</span>
              <button className={`settings ${showSettings ? 'active' : ''}`} onClick={() => setShowSettings(!showSettings)}>
                设置
              </button>
              {user?.is_admin === 1 && (
                <button className={`settings ${adminView ? 'active' : ''}`} onClick={() => (adminView ? setAdminView(false) : openAdmin())}>
                  管理员
                </button>
              )}
              <button className="settings" onClick={async () => { await api.post('/auth/logout'); window.location.reload(); }}>
                退出
              </button>
            </div>
          </header>
          <div className="chat-body" ref={chatBodyRef}>
            {groupMessages.map((msg, idx) => {
              const text = String(msg.content || '')
              const parts = text ? text.match(/[^。！]+[。！]|[^。！]+/g) || [''] : ['']
              
              // 获取角色头像（如果是角色消息）
              const senderChar = msg.sender_type === 'character' 
                ? characters.find(c => c.role === msg.sender_name || c.role.includes(msg.sender_name.split('_')[0]))
                : null
              const avatarUrl = senderChar?.avatar_url
              
              return (
                <div key={idx} className={`group-msg-item ${msg.sender_type}`}>
                  <div className="avatar">
                    {msg.sender_type === 'user' ? (
                      userAvatarUrl ? (
                        <img 
                          src={userAvatarUrl} 
                          alt={user?.username || 'User'}
                          style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px' }}
                        />
                      ) : (
                        '👤'
                      )
                    ) : avatarUrl ? (
                      <img 
                        src={avatarUrl} 
                        alt={msg.sender_name}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px' }}
                      />
                    ) : (
                      '🎭'
                    )}
                  </div>
                  <div className="msg-right">
                    <div className="sender-name">{msg.sender_name}</div>
                    {parts.map((s, j) => (
                      <div key={j} className="bubble">
                        {s}
                      </div>
                    ))}
                    {user?.is_admin === 1 && msg.id ? (
                      <button
                        className="view-btn"
                        onClick={async () => {
                          try {
                          const { data } = await api.get(`/admin/groups/${activeGroupId}/messages/${msg.id}/prompt`)
                            const pretty = JSON.stringify(
                              {
                            sender: data.sender_name,
                            system_prompt: data.system_prompt,
                            user_content: data.user_content,
                            moderator_prompt: data.moderator_prompt,
                                moderator_response: data.moderator_response,
                              },
                              null,
                              2
                            )
                          setInspectText(pretty)
                          setShowInspect(true)
                          } catch (e: any) {
                          alert(e?.response?.data?.error || '获取失败')
                        }
                        }}
                      >
                        查看
                      </button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
          {groupTypingStatus && (
            <div className="status-bar">
              <span>{groupTypingStatus}</span>
            </div>
          )}
          <footer className="chat-input">
            <input 
              value={input} 
              onChange={e => {
                setInput(e.target.value)
                handleUserTyping()
              }}
              onKeyPress={e => e.key === 'Enter' && sendGroupMessage(input, setInput, maxGroupReplyRounds)}
              placeholder="输入消息..." 
            />
            <button onClick={() => sendGroupMessage(input, setInput, maxGroupReplyRounds)}>发送</button>
          </footer>
        </main>
      ) : (
        <main className="chat">
          <header className="chat-head">
            <button className="mobile-menu-btn" onClick={() => setShowMobileSidebar(true)} style={{ display: 'none' }}>
              ☰
            </button>
            <div className="title">{activeRole || '选择一个角色开始聊天'}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="muted">{user.username}</span>
              <button className={`settings ${showSettings ? 'active' : ''}`} onClick={() => setShowSettings(!showSettings)}>
                设置
              </button>
              {user?.is_admin === 1 && (
                <button className={`settings ${adminView ? 'active' : ''}`} onClick={() => (adminView ? setAdminView(false) : openAdmin())}>
                  管理员
                </button>
              )}
              <button className="settings" onClick={async () => { await api.post('/auth/logout'); window.location.reload(); }}>
                退出
              </button>
            </div>
          </header>
        <div className="chat-body" ref={chatBodyRef}>
            {/* 管理员视图或普通聊天视图 */}
          {adminView ? (
              <AdminPanel 
                onOpenPromptManagement={() => setShowPromptManagement(true)}
              />
            ) : (
              messages.map((m, i) => {
              const text = String(m.content || '')
                const parts = text ? text.match(/[^。！]+[。！]|[^。！]+/g) || [''] : ['']
              const senderType = m.role === 'user' ? 'user' : 'character'
                const senderName = m.role === 'user' ? user?.username || 'User' : activeRole
              
              // 获取角色头像
              const currentChar = characters.find(c => c.role === activeRole)
              const avatarUrl = currentChar?.avatar_url
              
              return (
                <div key={i} className={`group-msg-item ${senderType}`}>
                    <div className="avatar">
                      {m.role === 'user' ? (
                        userAvatarUrl ? (
                          <img 
                            src={userAvatarUrl} 
                            alt={user?.username || 'User'}
                            style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px' }}
                          />
                        ) : (
                          '👤'
                        )
                      ) : avatarUrl ? (
                        <img 
                          src={avatarUrl} 
                          alt={activeRole}
                          style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px' }}
                        />
                      ) : (
                        '🎭'
                      )}
                    </div>
                  <div className="msg-right">
                    <div className="sender-name">{senderName}</div>
                    {parts.map((s, j) => (
                        <div key={j} className="bubble">
                          {s}
                        </div>
                      ))}
                      {user?.is_admin === 1 && m.role === 'user' && (m as any).id ? (
                        <button
                          className="view-btn"
                          onClick={async () => {
                            try {
                          const { data } = await api.get('/admin/chat/compiled', { 
                            params: { 
                              msg_id: (m as any).id, 
                              role: activeRole,
                              uid: user.id,
                                  cid: 0,
                                },
                          })
                          const pretty = JSON.stringify(data, null, 2)
                          setInspectText(pretty)
                          setShowInspect(true)
                            } catch (e: any) {
                          alert(e?.response?.data?.error || '获取失败')
                        }
                          }}
                        >
                          查看
                        </button>
                    ) : null}
                  </div>
                </div>
              )
            })
          )}
        </div>
        {activeRole && !adminView && (
          <div className="status-bar">
            <span>{typingStatus || '就绪'}</span>
          </div>
        )}
        <footer className="chat-input">
          <input 
            value={input} 
              onChange={e => {
                setInput(e.target.value)
                if (e.target.value) setTypingStatus('用户输入中...')
                else setTypingStatus('')
              }}
            placeholder="和角色聊天..." 
              onKeyDown={e => {
                if (e.key === 'Enter') send()
              }}
          />
          <button onClick={send}>发送</button>
        </footer>
        </main>
      )}

      {/* 右侧信息面板 */}
      {!adminView && (
        <InfoPanel
          activeType={activeType}
          activeRole={activeRole}
          activeGroupId={activeGroupId}
          charIntro={charIntro}
          groupMemberBriefs={groupMemberBriefs}
          characters={characters}
          onManageCharacter={() => setShowManageChar(true)}
          onManageGroup={() => setShowManageGroup(true)}
          onShowFeedback={() => setShowFeedback(true)}
        />
      )}

      {/* 模态框组件 */}
      <CreateCharacterModal show={showCreate} onClose={() => setShowCreate(false)} onOpenPoly={openPolyModal} />
      
      <PolysemantModal
        show={showPoly}
        onClose={() => {
          setShowPoly(false)
          setPolyLoading(false)
        }}
        newRole={newRole}
        polyOptions={polyOptions}
        polyLoading={polyLoading}
        polyRoute={polyRoute}
        polyChoiceIdx={polyChoiceIdx}
        setPolyChoiceIdx={setPolyChoiceIdx}
        setPolyChoiceHref={setPolyChoiceHref}
        onConfirm={() => {
          setShowPoly(false)
          handleCreateRole()
        }}
      />

      <CreateGroupModal
        show={showCreateGroup}
        onClose={() => setShowCreateGroup(false)}
        characters={characters}
        selectedMembers={selectedMembers}
        setSelectedMembers={setSelectedMembers}
        newGroupName={newGroupName}
        setNewGroupName={setNewGroupName}
        onSuccess={handleGroupCreated}
      />

      <ManageGroupModal
        show={showManageGroup}
        onClose={() => setShowManageGroup(false)}
        activeGroupId={activeGroupId}
        characters={characters}
        groupMemberBriefs={groupMemberBriefs}
        loadGroupMemberBriefs={loadGroupMemberBriefs}
        onDeleteGroup={handleDeleteGroup}
      />

      <ManageCharModal show={showManageChar} onClose={() => setShowManageChar(false)} activeRole={activeRole} />

      <SettingsModal show={showSettings} onClose={async () => {
        setShowSettings(false)
        // 重新加载设置以确保最新值生效
        try {
          const { data: settings } = await api.get('/api/me/settings')
          const s = settings.settings || {}
          setMaxGroupReplyRounds(s.max_group_reply_rounds != null ? String(s.max_group_reply_rounds) : '3')
        } catch (e) {
          console.error('重新加载设置失败:', e)
        }
      }} />

      <FeedbackModal show={showFeedback} onClose={() => setShowFeedback(false)} />

      <InspectModal show={showInspect} text={inspectText} onClose={() => setShowInspect(false)} />

      <PromptManagementModal show={showPromptManagement} onClose={() => setShowPromptManagement(false)} />
              </div>
  )
}

// 主App组件，包装所有Provider
function App() {
                  return (
    <AuthProvider>
      <CharacterProvider>
        <GroupProvider>
          <AdminProvider>
            <AppContent />
          </AdminProvider>
        </GroupProvider>
      </CharacterProvider>
    </AuthProvider>
  )
}

export default App

