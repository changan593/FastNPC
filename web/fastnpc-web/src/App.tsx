import { useEffect, useState, useRef } from 'react'
import './App.css'
import axios from 'axios'
import type { CharacterItem, Message, TaskState, AdminUser, AdminCharacter, GroupItem, GroupMessage, MemberBrief, Feedback } from './types'

function App() {
  const [characters, setCharacters] = useState<CharacterItem[]>([])
  const [activeRole, setActiveRole] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newRole, setNewRole] = useState('')
  const [newSource, setNewSource] = useState<'baike'|'zhwiki'>('baike')
  const [newDetail, setNewDetail] = useState<'concise'|'detailed'>('concise')
  const [creating, setCreating] = useState(false)
  const [progress, setProgress] = useState<TaskState|null>(null)
  const [createDone, setCreateDone] = useState(false)
  const [exportFacts, setExportFacts] = useState(false)
  const [exportBullets, setExportBullets] = useState(false)
  const [exportSummary, setExportSummary] = useState(false)
  const [exportMd, setExportMd] = useState(false)
  const [exportCtx, setExportCtx] = useState(false)
  const [user, setUser] = useState<{id:number, username:string, is_admin?: number}|null>(null)
  const [authMode, setAuthMode] = useState<'login'|'register'>('login')
  const [authForm, setAuthForm] = useState({ username: '', password: '' })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [showTerms, setShowTerms] = useState(false)
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<'updated'|'alpha'>('updated')
  const [renaming, setRenaming] = useState<string>('')
  const [newName, setNewName] = useState<string>('')
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [adminView, setAdminView] = useState(false)
  const [adminSelectedUser, setAdminSelectedUser] = useState<AdminUser|null>(null)
  const [adminUserChars, setAdminUserChars] = useState<AdminCharacter[]>([])
  const [adminSelectedChar, setAdminSelectedChar] = useState<AdminCharacter|null>(null)
  const [adminMessages, setAdminMessages] = useState<Message[]>([])
  const [adminTab, setAdminTab] = useState<'users'|'characters'|'groups'|'feedbacks'|'detail'>('users')
  const [adminSearchQuery, setAdminSearchQuery] = useState('')
  // 管理员查看群聊相关状态
  const [adminUserGroups, setAdminUserGroups] = useState<GroupItem[]>([])
  const [adminSelectedGroup, setAdminSelectedGroup] = useState<any|null>(null)
  const [adminGroupMessages, setAdminGroupMessages] = useState<GroupMessage[]>([])
  // 管理员查看反馈相关状态
  const [adminFeedbacks, setAdminFeedbacks] = useState<Feedback[]>([])
  const [adminSelectedFeedback, setAdminSelectedFeedback] = useState<Feedback|null>(null)
  const [feedbackReply, setFeedbackReply] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState<'pending' | 'in_progress' | 'resolved' | 'rejected'>('pending')
  // inspect modal
  const [showInspect, setShowInspect] = useState(false)
  const [inspectText, setInspectText] = useState('')
  // 右键菜单
  const [menuVisible, setMenuVisible] = useState(false)
  const [menuPos, setMenuPos] = useState<{x:number,y:number}>({x:0,y:0})
  const [menuRole, setMenuRole] = useState<string>('')
  // chat body ref for auto-scroll
  const chatBodyRef = useRef<HTMLDivElement|null>(null)
  // user settings
  const allowedModels = [
    'z-ai/glm-4-32b',
    'z-ai/glm-4.5-air:free',
    'deepseek/deepseek-chat-v3.1:free',
    'tencent/hunyuan-a13b-instruct:free',
  ] as const
  const [showSettings, setShowSettings] = useState(false)
  const [defaultModel, setDefaultModel] = useState<string>('')
  const [ctxMaxChat, setCtxMaxChat] = useState<string>('')
  const [ctxMaxStm, setCtxMaxStm] = useState<string>('')
  const [ctxMaxLtm, setCtxMaxLtm] = useState<string>('')
  const [oldPwd, setOldPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [deletePwd, setDeletePwd] = useState('')
  const [userProfile, setUserProfile] = useState<string>('')
  const [maxGroupReplyRounds, setMaxGroupReplyRounds] = useState<string>('3')

  // 群聊相关状态
  const [groups, setGroups] = useState<GroupItem[]>([])
  const [activeGroupId, setActiveGroupId] = useState<number|null>(null)
  const [groupMessages, setGroupMessages] = useState<GroupMessage[]>([])
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [selectedMembers, setSelectedMembers] = useState<string[]>([])
  const [groupMemberBriefs, setGroupMemberBriefs] = useState<MemberBrief[]>([])
  const [showManageGroup, setShowManageGroup] = useState(false)
  const [newMemberName, setNewMemberName] = useState('')

  // 单聊相关状态
  const [showManageChar, setShowManageChar] = useState(false)
  const [charIntro, setCharIntro] = useState<string>('')

  // 反馈相关状态
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackTitle, setFeedbackTitle] = useState('')
  const [feedbackContent, setFeedbackContent] = useState('')
  const [feedbackAttachments, setFeedbackAttachments] = useState<string[]>([])
  const [feedbackUploading, setFeedbackUploading] = useState(false)
  const [feedbackTab, setFeedbackTab] = useState<'submit' | 'history'>('submit')
  const [myFeedbacks, setMyFeedbacks] = useState<Feedback[]>([])
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null)

  // 移动端相关状态
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)

  // 中控相关状态
  const [typingStatus, setTypingStatus] = useState<string>('')
  const characterReplyCountRef = useRef(0)  // 使用 useRef 避免闭包问题
  const [userInputTimeout, setUserInputTimeout] = useState<number|null>(null)
  const [characterReplyTimeout, setCharacterReplyTimeout] = useState<number|null>(null)

  // 统一视图状态（角色/群聊）
  const [activeType, setActiveType] = useState<'character'|'group'>('character')

  // 左下角按钮（不再需要状态管理）
  
  // 跟踪前一个活动的角色/群聊，用于离开时压缩记忆
  const prevActiveRoleRef = useRef<string>('')
  const prevActiveGroupRef = useRef<number | null>(null)

  // baike 同名消歧（方案A）
  const [showPoly, setShowPoly] = useState(false)
  const [polyOptions, setPolyOptions] = useState<{text:string, href:string}[]>([])
  const [polyLoading, setPolyLoading] = useState(false)
  const [polyFilter, setPolyFilter] = useState('')
  const [polyChoiceIdx, setPolyChoiceIdx] = useState<number|null>(null)
  const [polyChoiceHref, setPolyChoiceHref] = useState<string>('')
  const [polyRoute, setPolyRoute] = useState<string>('')
  // 防抖/竞态：只接受最后一次请求结果
  const polyReqSeqRef = useRef<number>(0)

  // 打开创建或切换数据源时，重置义项选择，避免上次选择残留导致跳过弹窗
  useEffect(() => {
    if (showCreate) {
      setPolyChoiceIdx(null)
      setPolyChoiceHref('')
      setPolyOptions([])
      setPolyFilter('')
    }
  }, [showCreate])
  useEffect(() => {
    if (newSource === 'baike') {
      setPolyChoiceIdx(null)
      setPolyChoiceHref('')
    }
  }, [newSource])

  const api = axios.create({ withCredentials: true })
  async function reloadMessages() {
    if (!activeRole) return
    try {
      const { data } = await api.get(`/api/chat/${activeRole}/messages`)
      setMessages(data.messages || [])
    } catch {}
  }

  async function loadCharBrief() {
    if (!activeRole) return
    try {
      const { data } = await api.get(`/api/characters/${encodeURIComponent(activeRole)}/structured`)
      const base = data['基础身份信息'] || {}
      const intro = base['人物简介'] || ''
      setCharIntro(intro)
    } catch(e) {
      console.error('加载角色简介失败:', e)
      setCharIntro('')
    }
  }
  // const backendBase = (import.meta as any).env?.VITE_BACKEND || `${window.location.protocol}//${window.location.hostname}:8000`

  // load characters and groups
  useEffect(() => {
    (async () => {
      try {
        const me = await api.get('/auth/me')
        setUser(me.data)
        
        // 加载角色和群聊
        const [chars, grps] = await Promise.all([
          api.get('/api/characters'),
          api.get('/api/groups')
        ])
        
        setCharacters(chars.data.items || [])
        setGroups(grps.data.items || [])
        
        // 如果是管理员，加载管理员数据
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
      } catch (e:any) {
        // 未登录（401）或其他错误，清空所有状态，显示登录界面
        if (e?.response?.status === 401) {
          setUser(null)
          setCharacters([])
          setGroups([])
          setMessages([])
          setGroupMessages([])
          setActiveRole('')
          setActiveGroupId(null)
          setAdminUsers([])
          setAdminView(false)
          setAdminSelectedUser(null)
          setAdminUserChars([])
          setAdminSelectedChar(null)
          setAdminMessages([])
        }
      }
    })()
  }, [])

  // load messages when role changes
  useEffect(() => {
    (async () => {
      if (!activeRole) return
      try {
        const { data } = await api.get(`/api/chat/${activeRole}/messages`)
        setMessages(data.messages || [])
      } catch (e:any) {
        if (e?.response?.status === 401) setUser(null)
      }
    })()
  }, [activeRole])

  useEffect(() => {
    const hide = () => setMenuVisible(false)
    window.addEventListener('click', hide)
    return () => { window.removeEventListener('click', hide) }
  }, [])

  // 自动滚动到聊天底部（单聊）
  useEffect(() => {
    try {
      const el = chatBodyRef.current
      if (!el) return
      el.scrollTop = el.scrollHeight
    } catch {}
  }, [messages, adminView])

  // 自动滚动到聊天底部（群聊）
  useEffect(() => {
    try {
      const el = chatBodyRef.current
      if (!el || activeType !== 'group') return
      el.scrollTop = el.scrollHeight
    } catch {}
  }, [groupMessages, activeType])

  function send() {
    if (!activeRole || !input.trim()) return
    const content = input.trim()
    setInput('')
    setTypingStatus('发送中...')
    // 先推入用户消息与占位的助手气泡
    setMessages(m => [...m, { role: 'user', content }, { role: 'assistant', content: '' }])
    try {
      const es = new EventSource(`/api/chat/${encodeURIComponent(activeRole)}/stream?content=${encodeURIComponent(content)}${(user?.is_admin===1 && exportCtx)?'&export_ctx=1':''}`)
      let acc = ''
      es.onmessage = (e) => {
        if (!acc) setTypingStatus(`${activeRole} 回复中...`)
        acc += e.data
        setMessages(m => {
          if (!m.length) return m
          const copy = m.slice()
          // 更新最后一个助手气泡（流式）
          copy[copy.length - 1] = { role: 'assistant', content: acc }
          return copy
        })
      }
      es.onerror = async () => {
        // 大多数浏览器在服务器正常结束 SSE 时也会触发 onerror。
        // 若已收到流式内容(acc 有值)，则仅关闭连接，不做回退。
        try { es.close() } catch {}
        setTypingStatus('')
        if (acc && acc.trim()) { await reloadMessages(); return }
        // 未收到任何流数据，才回退到非流式接口
        try {
          const payload: any = { content }
          if (user?.is_admin === 1 && exportCtx) payload.export_ctx = true
          const { data } = await api.post(`/api/chat/${encodeURIComponent(activeRole)}/messages`, payload)
          const reply: string = (data && data.reply) ? data.reply : (typeof data === 'string' ? data : '')
          setMessages(m => {
            if (!m.length) return m
            const copy = m.slice()
            // 仅当最后一个助手气泡仍为空时才写入回退结果
            const last = copy[copy.length - 1]
            if (last.role === 'assistant' && !last.content) {
              copy[copy.length - 1] = { role: 'assistant', content: reply || '（无回复）' }
            }
            return copy
          })
          await reloadMessages()
        } catch (e:any) {
          setMessages(m => {
            if (!m.length) return m
            const copy = m.slice()
            const last = copy[copy.length - 1]
            if (last.role === 'assistant' && !last.content) {
              copy[copy.length - 1] = { role: 'assistant', content: `错误: ${e?.response?.data?.error || e?.message || e}` }
            }
            return copy
          })
        }
      }
    } catch (e:any) {
      setTypingStatus('')
      setMessages(m => [...m, { role: 'assistant', content: `错误: ${e?.message||e}` }])
    }
  }

  async function doLogin() {
    try {
      const { data } = await api.post('/auth/login', authForm)
      
      // 立即清空表单（安全）
      setAuthForm({ username: '', password: '' })
      
      setUser(data.user)
      
      // 完整加载新账号的所有数据
      const [chars, grps] = await Promise.all([
        api.get('/api/characters'),
        api.get('/api/groups')
      ])
      
      setCharacters(chars.data.items || [])
      setGroups(grps.data.items || [])
      
      // 如果是管理员，加载管理员数据
      if (data.user?.is_admin === 1) {
        try {
          const { data: adminData } = await api.get('/admin/users')
          if (adminData?.items) setAdminUsers(adminData.items)
        } catch {}
      }
      
      // 设置默认选中
      if (chars.data.items?.length) {
        setActiveRole(chars.data.items[0].role)
        setActiveType('character')
      }
    } catch (e:any) {
      alert(e?.response?.data?.error || '登录失败')
    }
  }

  async function doRegister() {
    // 检查是否同意用户协议
    if (!agreedToTerms) {
      alert('请先阅读并同意用户协议')
      return
    }
    
    try {
      const { data } = await api.post('/auth/register', authForm)
      
      // 立即清空表单（安全）
      setAuthForm({ username: '', password: '' })
      setAgreedToTerms(false)
      
      setUser(data.user)
      
      // 完整加载新账号的所有数据
      const [chars, grps] = await Promise.all([
        api.get('/api/characters'),
        api.get('/api/groups')
      ])
      
      setCharacters(chars.data.items || [])
      setGroups(grps.data.items || [])
      
      // 新用户通常没有角色，不强制设置默认选中
    } catch (e:any) {
      alert(e?.response?.data?.error || '注册失败')
    }
  }

  async function doLogout() {
    try { await api.post('/auth/logout') } catch {}
    
    // 清空所有用户数据和状态
    setUser(null)
    setCharacters([])
    setGroups([])
    setMessages([])
    setGroupMessages([])
    setActiveRole('')
    setActiveGroupId(null)
    setActiveType('character')
    
    // 清空管理员数据
    setAdminUsers([])
    setAdminView(false)
    setAdminSelectedUser(null)
    setAdminUserChars([])
    setAdminSelectedChar(null)
    setAdminMessages([])
    setAdminTab('users')
    
    // 清空表单（安全）
    setAuthForm({ username: '', password: '' })
  }

  async function refreshList() {
    const { data } = await api.get('/api/characters')
    setCharacters(data.items || [])
  }

  async function openAdmin() {
    setAdminView(true)
    try {
      const { data } = await api.get('/admin/users')
      setAdminUsers(data.items || [])
    } catch {}
  }

  async function loadAdminUser(uid: number) {
    try {
      const { data } = await api.get(`/admin/users/${uid}/characters`)
      setAdminSelectedUser(adminUsers.find(u => u.id === uid) || null)
      setAdminUserChars(data.items || [])
      setAdminSelectedChar(null)
      setAdminMessages([])
      setAdminTab('characters')
    } catch {}
  }

  async function loadAdminUserGroups(uid: number) {
    try {
      const { data } = await api.get(`/admin/users/${uid}/groups`)
      setAdminSelectedUser(adminUsers.find(u => u.id === uid) || null)
      setAdminUserGroups(data.items || [])
      setAdminSelectedGroup(null)
      setAdminGroupMessages([])
      setAdminTab('groups')
    } catch {}
  }

  async function loadAdminGroup(groupId: number) {
    try {
      const { data: detail } = await api.get(`/admin/groups/${groupId}`)
      setAdminSelectedGroup(detail.group)
      const { data: msgs } = await api.get(`/admin/groups/${groupId}/messages`)
      setAdminGroupMessages(msgs.messages || [])
    } catch {}
  }

  async function loadAdminFeedbacks() {
    try {
      const { data } = await api.get('/admin/feedbacks')
      setAdminFeedbacks(data.items || [])
      setAdminTab('feedbacks')
    } catch {}
  }

  async function loadAdminFeedback(feedbackId: number) {
    try {
      const { data } = await api.get(`/admin/feedbacks/${feedbackId}`)
      setAdminSelectedFeedback(data.feedback)
      setFeedbackReply(data.feedback.admin_reply || '')
      setFeedbackStatus(data.feedback.status)
    } catch {}
  }

  async function updateFeedbackStatus(feedbackId: number) {
    try {
      await api.put(`/admin/feedbacks/${feedbackId}`, {
        status: feedbackStatus,
        admin_reply: feedbackReply
      })
      alert('更新成功')
      await loadAdminFeedbacks()
      setAdminSelectedFeedback(null)
    } catch (e: any) {
      alert(e?.response?.data?.error || '更新失败')
    }
  }

  async function deleteFeedback(feedbackId: number) {
    if (!confirm('确定要删除这条反馈吗？')) return
    try {
      await api.delete(`/admin/feedbacks/${feedbackId}`)
      alert('删除成功')
      await loadAdminFeedbacks()
      setAdminSelectedFeedback(null)
    } catch (e: any) {
      alert(e?.response?.data?.error || '删除失败')
    }
  }

  async function cleanupAdminUserChars(uid: number) {
    if (!confirm('确定要清理数据库中文件已不存在的角色记录吗？')) return
    try {
      const { data } = await api.post(`/admin/users/${uid}/characters/cleanup`)
      alert(`清理完成！删除了 ${data.deleted_count} 个无效角色记录：\n${data.deleted_names.join('\n')}`)
      // 重新加载角色列表
      await loadAdminUser(uid)
    } catch (e: any) {
      alert(e?.response?.data?.error || '清理失败')
    }
  }

  async function refreshAdminData() {
    try {
      const { data } = await api.get('/admin/users')
      if (data?.items) setAdminUsers(data.items)
      alert('数据已刷新')
    } catch (e: any) {
      alert(e?.response?.data?.error || '刷新失败')
    }
  }

  async function loadAdminChar(uid: number, cid: number) {
    try {
      const { data: detail } = await api.get(`/admin/users/${uid}/characters/${cid}`)
      setAdminSelectedChar(detail.character)
      const { data: msgs } = await api.get(`/admin/users/${uid}/characters/${cid}/messages`)
      setAdminMessages(msgs.messages || [])
      setAdminTab('detail')
    } catch {}
  }

  async function renameRole(oldName: string) {
    if (!newName.trim()) return
    try {
      await api.put(`/api/characters/${encodeURIComponent(oldName)}/rename`, { new_name: newName.trim() })
      setRenaming(''); setNewName('')
      await refreshList()
      if (activeRole === oldName) setActiveRole(newName.trim())
    } catch (e:any) { alert(e?.response?.data?.error || '重命名失败') }
  }

  async function deleteRole(name: string) {
    if (!confirm(`确定删除角色「${name}」及其消息吗？`)) return
    try {
      await api.delete(`/api/characters/${encodeURIComponent(name)}`)
      await refreshList()
      if (activeRole === name) setActiveRole(characters[0]?.role || '')
    } catch (e:any) { alert(e?.response?.data?.error || '删除失败') }
  }

  // 反馈相关函数
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
        attachments
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

  async function copyRole(name: string) {
    try {
      const { data } = await api.post(`/api/characters/${encodeURIComponent(name)}/copy`)
      await refreshList()
      if (data?.new_name) setActiveRole(data.new_name)
    } catch (e:any) { alert(e?.response?.data?.error || '复制失败') }
  }

  async function createRole() {
    if (!newRole.trim()) return
    // 若为百科/维基且尚未选择具体义项，则先弹出同名选择
    if ((newSource === 'baike' || newSource === 'zhwiki') && polyChoiceIdx == null) {
      await openPolyModal()
      return
    }
    setCreating(true)
    setCreateDone(false)
    try {
      const fmt = (()=>{ const d=new Date(); const pad=(n:number)=>String(n).padStart(2,'0'); return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}` })()
      const roleWithTs = `${newRole.trim()}${fmt}`
      const payload: any = { role: roleWithTs, source: newSource, detail: newDetail, export_facts: exportFacts, export_bullets: exportBullets, export_summary: exportSummary, export_md: exportMd }
      if (newSource === 'baike' || newSource === 'zhwiki') {
        if (polyChoiceIdx != null) payload.choice_index = polyChoiceIdx
        if (polyFilter && polyFilter.trim()) payload.filter_text = polyFilter.trim()
        if (newSource === 'baike' && polyChoiceHref) payload.chosen_href = polyChoiceHref
      }
      const { data } = await api.post('/api/characters', payload)
      const taskId = data.task_id
      // poll
      let done = false
      while (!done) {
        const { data: t } = await api.get(`/api/tasks/${taskId}`)
        setProgress(t)
        if (t.status === 'done') {
          done = true
          break
        }
        if (t.status === 'error' || t.status === 'not_found') break
        await new Promise(r => setTimeout(r, 1200))
      }
      // refresh list
      const { data: list } = await api.get('/api/characters')
      setCharacters(list.items || [])
      setActiveRole(roleWithTs)
      setCreateDone(true)
    } catch (e) {
      console.error(e)
    } finally {
      setCreating(false)
    }
  }

  async function openPolyModal() {
    if (!newRole.trim()) { alert('请先填写角色名'); return }
    // 显示“预抓取候选”的进度
    setProgress({
      role: newRole.trim(), source: 'baike', model: '', user_id: 0, detail: 'detailed',
      progress: 10, status: 'running', message: '正在从 baike 抓取候选…', raw_path: '', structured_path: '', started_at: Date.now()/1000
    } as any)
    setShowPoly(true)
    setPolyLoading(true)
    const seq = Date.now()
    polyReqSeqRef.current = seq
    const endpoint = (newSource === 'zhwiki') ? '/api/zhwiki/polysemant' : '/api/baike/polysemant'
    const limit = (newSource === 'zhwiki') ? 80 : 200
    const normalize = (arr:any[]) => (arr||[]).map((it:any)=>({ text: it.text||it.title||'', href: it.href||'', snippet: (it.snippet||'').replace(/<[^>]+>/g,'') }))
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
    } catch (e:any) {
      console.error(e)
      alert(e?.response?.data?.error || '获取候选失败')
    } finally {
      if (polyReqSeqRef.current === seq) setPolyLoading(false)
    }
  }

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
        setOldPwd(''); setNewPwd('')
      }
      alert('已保存')
      setShowSettings(false)
    } catch (e:any) {
      alert(e?.response?.data?.error || '保存失败')
    }
  }

  async function deleteAccount() {
    if (!deletePwd.trim()) { alert('请输入密码确认'); return }
    if (!confirm('确定注销账户吗？该操作不可恢复，将删除你的所有角色与消息。')) return
    try {
      const { data } = await api.post('/api/me/delete', { password: deletePwd })
      if (data?.ok) {
        alert('账户已注销')
        setShowSettings(false)
        await doLogout()
      }
    } catch (e:any) {
      alert(e?.response?.data?.error || '注销失败')
    }
  }

  // 群聊相关函数
  async function reloadGroupMessages() {
    if (!activeGroupId) return
    try {
      const { data } = await api.get(`/api/groups/${activeGroupId}/messages`)
      setGroupMessages(data.messages || [])
    } catch {}
  }

  async function loadGroupMemberBriefs() {
    if (!activeGroupId) return
    try {
      const { data } = await api.get(`/api/groups/${activeGroupId}/members/briefs`)
      setGroupMemberBriefs(data.members || [])
    } catch {}
  }

  function handleUserTyping() {
    setTypingStatus('用户输入中')
    
    // 只清除角色回复的等待计时器，阻止角色在用户输入时发言
    if (characterReplyTimeout) {
      window.clearTimeout(characterReplyTimeout)
      setCharacterReplyTimeout(null)
    }
    // 注意：不重置 characterReplyCountRef，不设置新定时器
    // 只有用户真正发送消息后，才会重置计数器并触发中控
  }

  async function sendGroupMessage() {
    if (!input.trim() || !activeGroupId) return
    const content = input.trim()
    setInput('')
    
    // 清除角色回复等待计时器（如果有的话）
    if (characterReplyTimeout) {
      window.clearTimeout(characterReplyTimeout)
      setCharacterReplyTimeout(null)
    }
    
    console.log(`[DEBUG] 用户发言，重置计数器: ${characterReplyCountRef.current} -> 0`)
    setTypingStatus('')
    characterReplyCountRef.current = 0
    
    try {
      await api.post(`/api/groups/${activeGroupId}/messages`, { content })
      await reloadGroupMessages()
      triggerModerator()
    } catch (e: any) {
      alert(e?.response?.data?.error || '发送失败')
    }
  }

  async function triggerModerator() {
    if (!activeGroupId) return
    const maxRounds = Number(maxGroupReplyRounds) || 3
    
    console.log(`[DEBUG] triggerModerator: characterReplyCount=${characterReplyCountRef.current}, maxRounds=${maxRounds}`)
    
    // 达到最大连续回复次数，必须等待用户发言
    if (characterReplyCountRef.current >= maxRounds) {
      console.log(`[INFO] 已达到最大回复轮数 (${characterReplyCountRef.current}/${maxRounds})，等待用户发言`)
      setTypingStatus('等待用户发言...')
      // 不再自动继续，必须等待用户真正发言
      return
    }
    
    try {
      const { data } = await api.post(`/api/groups/${activeGroupId}/judge-next`)
      const nextSpeaker = data.next_speaker
      const confidence = data.confidence
      const moderatorPrompt = data.moderator_prompt
      const moderatorResponse = data.moderator_response
      
      if (!nextSpeaker || confidence < 0.3) {
        setTypingStatus('等待用户发言...')
        return
      }
      
      setTypingStatus(`${nextSpeaker} 输入中...`)
      
      // 流式接收群聊角色回复
      const token = localStorage.getItem('token')
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/groups/${activeGroupId}/generate-reply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          character_name: nextSpeaker,
          moderator_prompt: moderatorPrompt,
          moderator_response: moderatorResponse
        })
      })
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let streamContent = ''
      
      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            
            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n')
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  if (data.content) {
                    streamContent += data.content
                    // 实时更新群聊消息（可选）
                  } else if (data.done) {
                    // 流式完成
                  } else if (data.error) {
                    console.error('流式错误:', data.error)
                  }
                } catch (e) {
                  // 忽略JSON解析错误
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }
      }
      
      await reloadGroupMessages()
      characterReplyCountRef.current += 1
      const newCount = characterReplyCountRef.current
      console.log(`[DEBUG] 角色回复完成，计数器: ${newCount - 1} -> ${newCount}`)
      setTypingStatus('')
      
      // 检查是否已达到最大连续回复次数
      const maxRounds = Number(maxGroupReplyRounds) || 3
      if (newCount >= maxRounds) {
        // 已达到最大次数，显示等待用户发言，不再触发中控
        console.log(`[INFO] 角色回复完成后检查：已达到最大轮数 (${newCount}/${maxRounds})`)
        setTypingStatus('等待用户发言...')
        return
      }
      
      console.log(`[DEBUG] 角色回复完成，未达到最大轮数 (${newCount}/${maxRounds})，3秒后继续`)
      
      // 角色发言后，等待3秒看用户是否输入
      // 如果用户开始输入，handleUserTyping会清除这个计时器
      // 如果用户没有输入，3秒后继续触发中控
      const timer = window.setTimeout(() => {
        triggerModerator()
      }, 3000)
      setCharacterReplyTimeout(timer)
    } catch (e: any) {
      console.error('中控判断失败', e)
      setTypingStatus('')
    }
  }

  // 监听角色/群聊切换，处理离开会话时的记忆压缩
  useEffect(() => {
    console.log(`[DEBUG] useEffect触发 - activeType=${activeType}, activeGroupId=${activeGroupId}, activeRole=${activeRole}`)
    
    // 离开上一个单聊时压缩记忆
    if (prevActiveRoleRef.current && prevActiveRoleRef.current !== activeRole) {
      console.log(`[INFO] 切换单聊，压缩记忆: ${prevActiveRoleRef.current}`)
      api.post(`/api/chat/${prevActiveRoleRef.current}/compress-all`).catch(() => {
        console.log(`[INFO] 压缩单聊记忆: ${prevActiveRoleRef.current}`)
      })
    }
    
    // 离开上一个群聊时压缩记忆
    if (prevActiveGroupRef.current && prevActiveGroupRef.current !== activeGroupId) {
      console.log(`[INFO] 切换群聊，压缩记忆: ${prevActiveGroupRef.current}`)
      api.post(`/api/groups/${prevActiveGroupRef.current}/compress-memories`).catch(() => {
        console.log(`[INFO] 压缩群聊记忆: ${prevActiveGroupRef.current}`)
      })
    }
    
    // 更新当前活动的角色/群聊
    prevActiveRoleRef.current = activeRole || ''
    prevActiveGroupRef.current = activeGroupId
    
    // 切换时清除所有计时器
    if (userInputTimeout) {
      window.clearTimeout(userInputTimeout)
      setUserInputTimeout(null)
    }
    if (characterReplyTimeout) {
      window.clearTimeout(characterReplyTimeout)
      setCharacterReplyTimeout(null)
    }
    console.log(`[DEBUG] useEffect: 重置状态和计数器`)
    setTypingStatus('')
    characterReplyCountRef.current = 0
    
    if (activeType === 'group' && activeGroupId) {
      reloadGroupMessages()
      loadGroupMemberBriefs()
    } else if (activeType === 'character' && activeRole) {
      reloadMessages()
      loadCharBrief()
    }
  }, [activeType, activeGroupId, activeRole])

  if (!user) {
    return (
      <>
      <div className="auth-wrap">
        <div className="auth-background-text">FastNPC</div>
        <div className="auth-card">
          <h2>{authMode === 'login' ? '登录' : '注册'}</h2>
          <label>用户名
            <input value={authForm.username} onChange={e=>setAuthForm({...authForm, username:e.target.value})} placeholder="用户名" />
          </label>
          <label>密码
            <input type="password" value={authForm.password} onChange={e=>setAuthForm({...authForm, password:e.target.value})} placeholder="密码" />
          </label>
          {authMode === 'register' && (
            <div className="terms-agreement">
              <label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}>
                <input 
                  type="checkbox" 
                  checked={agreedToTerms}
                  onChange={e => setAgreedToTerms(e.target.checked)}
                  style={{cursor: 'pointer'}}
                />
                <span style={{fontSize: '14px', color: '#6b7280'}}>
                  我已阅读并同意
                  <a 
                    href="#" 
                    onClick={(e) => { e.preventDefault(); setShowTerms(true); }}
                    style={{color: '#667eea', textDecoration: 'none', marginLeft: '4px', marginRight: '4px'}}
                  >
                    《用户服务协议》
                  </a>
                </span>
              </label>
            </div>
          )}
          <div className="actions">
            {authMode === 'login' ? (
              <>
                <button onClick={doLogin} className="primary">登录</button>
                <button onClick={()=>setAuthMode('register')}>没有账号？去注册</button>
              </>
            ) : (
              <>
                <button onClick={doRegister} className="primary">注册并登录</button>
                <button onClick={()=>setAuthMode('login')}>已有账号？去登录</button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 用户协议模态框 */}
      {showTerms && (
        <div className="modal" onClick={() => setShowTerms(false)}>
          <div className="dialog" style={{maxWidth: '800px', maxHeight: '80vh', display: 'flex', flexDirection: 'column'}} onClick={e => e.stopPropagation()}>
            <div className="feedback-header">
              <h3>📜 用户服务协议</h3>
              <button className="close-btn" onClick={() => setShowTerms(false)}>×</button>
            </div>
            <div style={{flex: 1, overflow: 'auto', padding: '20px', fontSize: '14px', lineHeight: '1.8'}}>
              <div style={{whiteSpace: 'pre-wrap', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#374151'}}>
                <h2 style={{fontSize: '20px', fontWeight: 'bold', marginBottom: '16px'}}>FastNPC 用户服务协议</h2>
                <p style={{fontSize: '12px', color: '#6b7280', marginBottom: '24px'}}>最后更新时间：2025年1月17日</p>
                
                <p style={{marginBottom: '16px'}}>欢迎使用 FastNPC！本服务协议（以下简称"本协议"）是您与 FastNPC 项目（以下简称"我们"或"本服务"）之间的法律协议。</p>
                
                <p style={{fontWeight: 'bold', marginBottom: '16px', color: '#dc2626'}}>⚠️ 重要提示：使用本服务即表示您同意本协议的所有条款。如果您不同意本协议的任何部分，请勿使用本服务。</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>1. 服务使用</h3>
                <p style={{marginBottom: '8px'}}>• 您必须年满 13 周岁才能使用本服务</p>
                <p style={{marginBottom: '8px'}}>• 您同意提供真实、准确的注册信息</p>
                <p style={{marginBottom: '16px'}}>• 您有责任维护账户密码的安全性</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>2. 禁止行为</h3>
                <p style={{marginBottom: '8px'}}>在使用本服务时，禁止以下行为：</p>
                <p style={{marginBottom: '8px'}}>• 发布侵犯他人知识产权的内容</p>
                <p style={{marginBottom: '8px'}}>• 发布威胁、骚扰、诽谤他人的内容</p>
                <p style={{marginBottom: '8px'}}>• 发布暴力、色情、淫秽内容</p>
                <p style={{marginBottom: '8px'}}>• 试图破解、反向工程本服务</p>
                <p style={{marginBottom: '16px'}}>• 从事任何非法活动</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>3. AI 内容免责</h3>
                <p style={{marginBottom: '8px'}}>• AI 生成的内容可能不准确，仅供娱乐参考</p>
                <p style={{marginBottom: '8px'}}>• 不要依赖 AI 内容做重要决策</p>
                <p style={{marginBottom: '16px'}}>• 您对使用 AI 生成内容的后果负全部责任</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>4. 知识产权与内容所有权</h3>
                <p style={{fontWeight: 'bold', marginBottom: '12px', color: '#059669'}}>✅ 重要：您创建的所有角色和内容的版权归您所有</p>
                <p style={{marginBottom: '8px'}}>• 您创建的 AI 角色、对话记录等，所有权完全归您</p>
                <p style={{marginBottom: '8px'}}>• 我们有权删除违规内容，无需事先通知</p>
                <p style={{marginBottom: '8px', color: '#dc2626'}}>⚠️ 我们不对数据丢失、误删承担责任</p>
                <p style={{marginBottom: '16px'}}>• 建议您定期备份重要数据</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>5. 隐私保护</h3>
                <p style={{marginBottom: '8px'}}>• 我们收集必要的注册和使用数据</p>
                <p style={{marginBottom: '8px'}}>• 我们不会出售您的个人信息</p>
                <p style={{marginBottom: '16px'}}>• 我们采取合理措施保护您的数据安全</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>6. 免责声明</h3>
                <p style={{marginBottom: '8px'}}>• 本服务按"现状"提供，不保证无错误</p>
                <p style={{marginBottom: '8px', fontWeight: 'bold', color: '#dc2626'}}>• 我们不对数据丢失、损坏、误删承担任何责任</p>
                <p style={{marginBottom: '8px'}}>• 我们不对服务中断或 AI 内容准确性负责</p>
                <p style={{marginBottom: '16px', background: '#fef3c7', padding: '8px', borderRadius: '4px', color: '#92400e'}}>💡 本服务为免费服务，不承担任何赔偿责任</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>7. 服务变更与终止</h3>
                <p style={{marginBottom: '8px'}}>• 我们可能随时修改、暂停或终止服务</p>
                <p style={{marginBottom: '8px'}}>• 我们保留暂停或终止违规账户的权利</p>
                <p style={{marginBottom: '16px'}}>• 账户终止后，您的数据可能被删除</p>
                
                <h3 style={{fontSize: '16px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px'}}>8. 联系我们</h3>
                <p style={{marginBottom: '8px'}}>如对本协议有疑问，请通过以下方式联系：</p>
                <p style={{marginBottom: '8px'}}>• 使用应用内的"我要反馈"功能</p>
                <p style={{marginBottom: '16px'}}>• GitHub: https://github.com/changan593/FastNPC</p>
                
                <p style={{fontWeight: 'bold', marginTop: '32px', padding: '16px', background: '#fef3c7', borderRadius: '8px', color: '#92400e'}}>
                  ⚠️ 再次提醒：使用本服务即表示您已阅读、理解并同意本协议的所有条款。
                </p>
                
                <p style={{marginTop: '24px', fontSize: '12px', color: '#6b7280', textAlign: 'center'}}>
                  FastNPC 是一个开源项目，遵循 MIT 许可证
                </p>
              </div>
            </div>
            <div className="feedback-actions">
              <button className="btn-primary" onClick={() => { setShowTerms(false); setAgreedToTerms(true); }}>我已阅读并同意</button>
              <button className="btn-secondary" onClick={() => setShowTerms(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
      </>
    )
  }

  return (
    <div className={`layout ${showMobileSidebar ? 'mobile-sidebar-open' : ''}`}>
      <div className="mobile-overlay" onClick={() => setShowMobileSidebar(false)}></div>
      <aside className="sidebar">
        <div className="sidebar-head">
          <div className="app-logo">FastNPC</div>
          <h2>角色/群聊</h2>
        </div>
        <div className="search">
          <input placeholder="搜索" value={q} onChange={e=>setQ(e.target.value)} />
          <select value={sort} onChange={e=>setSort(e.target.value as any)}>
            <option value="updated">最近更新</option>
            <option value="alpha">按名称</option>
          </select>
        </div>
        <ul className="role-list">
          {(() => {
            const allItems = [
              ...characters.map(c => ({ 
                type: 'character' as const, 
                data: c, 
                updated_at: c.updated_at,
                name: c.role
              })),
              ...groups.map(g => ({ 
                type: 'group' as const, 
                data: g, 
                updated_at: g.updated_at,
                name: g.name
              }))
            ]
            
            return allItems
              .filter(item => !q || item.name.includes(q))
              .sort((a, b) => sort === 'alpha' ? a.name.localeCompare(b.name) : (b.updated_at - a.updated_at))
              .map(item => (
                <li key={`${item.type}-${item.type === 'character' ? item.data.role : item.data.id}`}
                    className={
                      (item.type === 'character' && activeType === 'character' && item.data.role === activeRole) ||
                      (item.type === 'group' && activeType === 'group' && item.data.id === activeGroupId)
                        ? 'active' : ''
                    }
                    onContextMenu={(e)=>{
                      if (item.type === 'character') {
                        e.preventDefault();
                        setMenuRole(item.data.role); setMenuPos({x:e.clientX, y:e.clientY}); setMenuVisible(true)
                      }
                    }}>
                  <div className="row" onClick={() => {
                    if (item.type === 'character') {
                      setActiveType('character')
                      setActiveRole(item.data.role)
                      setActiveGroupId(null)
                    } else {
                      setActiveType('group')
                      setActiveGroupId(item.data.id)
                      setActiveRole('')
                    }
                  }}>
                    <div className="name">
                      <span>{item.type === 'character' ? '👤 ' : '💬 '}</span>
                      {item.name}
                    </div>
                    <div className="time">{new Date(item.updated_at*1000).toLocaleDateString()}</div>
                  </div>
                  {item.type === 'character' && item.data.preview ? (
                    <div className="muted" title={item.data.preview}
                      style={{
                        margin:'4px 0 0', fontSize:12, lineHeight:1.4,
                        display: '-webkit-box', WebkitLineClamp: 2 as any, WebkitBoxOrient: 'vertical' as any,
                        overflow: 'hidden', textOverflow: 'ellipsis'
                      }}>
                      {item.data.preview}
                    </div>
                  ) : null}
                  {item.type === 'character' && (
                    <div className="ops">
                      {renaming===item.data.role ? (
                        <>
                          <input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="新名称" />
                          <button onClick={()=>renameRole(item.data.role)} className="primary">确定</button>
                          <button onClick={()=>{setRenaming(''); setNewName('')}}>取消</button>
                        </>
                      ) : null}
                    </div>
                  )}
                </li>
              ))
          })()}
        </ul>
        <div className="fab-container">
          <div className="fab-hint">新建</div>
          <div className="fab-buttons">
            <button className="fab" aria-label="创建角色" title="创建角色" onClick={() => setShowCreate(true)}>
              📝 角色
            </button>
            <button className="fab" aria-label="创建群聊" title="创建群聊" onClick={() => setShowCreateGroup(true)}>
              💬 群聊
            </button>
          </div>
        </div>
      </aside>
      {activeType === 'group' && activeGroupId && !adminView ? (
        <main className="chat">
          <header className="chat-head">
            <button 
              className="mobile-menu-btn" 
              onClick={() => setShowMobileSidebar(true)}
              style={{ display: 'none' }}
            >
              ☰
            </button>
            <div className="title">
              {groups.find(g => g.id === activeGroupId)?.name || '群聊'}
              <span style={{fontSize:12, color:'var(--muted)', marginLeft:8}}>
                ({groupMemberBriefs.length} 成员)
              </span>
            </div>
            <div style={{display:'flex', alignItems:'center', gap:8}}>
              <span className="muted">{user.username}</span>
              <button className={`settings ${showSettings? 'active':''}`} onClick={()=>{ if (showSettings) { setShowSettings(false) } else { loadSettings(); setShowSettings(true) } }}>设置</button>
              {user?.is_admin === 1 && (
                <button className={`settings ${adminView? 'active':''}`} onClick={()=>{ if (adminView) { setAdminView(false) } else { openAdmin() } }}>管理员</button>
              )}
              <button className="settings" onClick={doLogout}>退出</button>
            </div>
          </header>
          <div className="chat-body" ref={chatBodyRef}>
            {groupMessages.map((msg, idx) => {
              const text = String(msg.content || '')
              // 将消息按句号和感叹号分段
              const parts = text ? (text.match(/[^。！]+[。！]|[^。！]+/g) || ['']) : ['']
              return (
                <div key={idx} className={`group-msg-item ${msg.sender_type}`}>
                  <div className="avatar">
                    {msg.sender_type === 'user' ? '👤' : '🎭'}
                  </div>
                  <div className="msg-right">
                    <div className="sender-name">{msg.sender_name}</div>
                    {parts.map((s, j) => (
                      <div key={j} className="bubble">{s}</div>
                    ))}
                    {(user?.is_admin===1 && msg.id) ? (
                      <button className="view-btn" onClick={async ()=>{
                        try{
                          const { data } = await api.get(`/admin/groups/${activeGroupId}/messages/${msg.id}/prompt`)
                          const pretty = JSON.stringify({
                            sender: data.sender_name,
                            system_prompt: data.system_prompt,
                            user_content: data.user_content,
                            moderator_prompt: data.moderator_prompt,
                            moderator_response: data.moderator_response
                          }, null, 2)
                          setInspectText(pretty)
                          setShowInspect(true)
                        }catch(e:any){
                          alert(e?.response?.data?.error || '获取失败')
                        }
                      }}>查看</button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
          {typingStatus && (
            <div className="status-bar">
              <span>{typingStatus}</span>
            </div>
          )}
          <footer className="chat-input">
            <input 
              value={input} 
              onChange={e => { setInput(e.target.value); handleUserTyping(); }}
              onKeyPress={e => e.key === 'Enter' && sendGroupMessage()}
              placeholder="输入消息..." 
            />
            <button onClick={sendGroupMessage}>发送</button>
          </footer>
        </main>
      ) : (
        <main className="chat">
          <header className="chat-head">
            <button 
              className="mobile-menu-btn" 
              onClick={() => setShowMobileSidebar(true)}
              style={{ display: 'none' }}
            >
              ☰
            </button>
            <div className="title">{activeRole || '选择一个角色开始聊天'}</div>
            <div style={{display:'flex', alignItems:'center', gap:8}}>
              <span className="muted">{user.username}</span>
              <button className={`settings ${showSettings? 'active':''}`} onClick={()=>{ if (showSettings) { setShowSettings(false) } else { loadSettings(); setShowSettings(true) } }}>设置</button>
              {user?.is_admin === 1 && (
                <button className={`settings ${adminView? 'active':''}`} onClick={()=>{ if (adminView) { setAdminView(false) } else { openAdmin() } }}>管理员</button>
              )}
              <button className="settings" onClick={doLogout}>退出</button>
            </div>
          </header>
        <div className="chat-body" ref={chatBodyRef}>
          {adminView ? (
            <div className="admin-page">
              <div className="admin-header">
                <div className="admin-tabs">
                  <button 
                    className={adminTab === 'users' ? 'active' : ''} 
                    onClick={() => { setAdminTab('users'); setAdminSelectedUser(null); setAdminUserChars([]); setAdminSelectedChar(null); }}
                  >
                    用户列表
                  </button>
                  <button 
                    className={adminTab === 'characters' ? 'active' : ''} 
                    onClick={() => setAdminTab('characters')}
                    disabled={!adminSelectedUser}
                  >
                    角色列表 {adminSelectedUser ? `(${adminSelectedUser.username})` : ''}
                  </button>
                  <button 
                    className={adminTab === 'groups' ? 'active' : ''} 
                    onClick={() => setAdminTab('groups')}
                    disabled={!adminSelectedUser}
                  >
                    群聊列表 {adminSelectedUser ? `(${adminSelectedUser.username})` : ''}
                  </button>
                  <button 
                    className={adminTab === 'feedbacks' ? 'active' : ''} 
                    onClick={() => loadAdminFeedbacks()}
                  >
                    用户反馈
                  </button>
                  <button 
                    className={adminTab === 'detail' ? 'active' : ''} 
                    onClick={() => setAdminTab('detail')}
                    disabled={!adminSelectedChar}
                  >
                    详情 {adminSelectedChar ? `(${adminSelectedChar.name})` : ''}
                  </button>
                </div>
                <div className="admin-actions">
                  <input 
                    type="text" 
                    placeholder="搜索..." 
                    value={adminSearchQuery}
                    onChange={e => setAdminSearchQuery(e.target.value)}
                    className="admin-search"
                  />
                  <button onClick={refreshAdminData} className="settings">刷新数据</button>
                  {adminTab === 'characters' && adminSelectedUser && (
                    <button onClick={() => cleanupAdminUserChars(adminSelectedUser.id)} className="settings">清理无效角色</button>
                  )}
                </div>
              </div>

              {adminTab === 'users' && (
                <div className="admin-content">
                  {/* 桌面端表格 */}
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
                          <td>{u.username} {u.is_admin ? <span className="badge">管理员</span> : ''}</td>
                          <td>{new Date(u.created_at * 1000).toLocaleString()}</td>
                          <td>-</td>
                          <td>
                            <button onClick={() => loadAdminUser(u.id)} className="btn-link">查看角色</button>
                            {' | '}
                            <button onClick={() => loadAdminUserGroups(u.id)} className="btn-link">查看群聊</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* 移动端卡片 */}
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
                  
                  {/* 桌面端表格 */}
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
                          <td><span className="muted">{c.model || '-'}</span></td>
                          <td><span className="muted">{c.source || '-'}</span></td>
                          <td>{new Date(c.updated_at * 1000).toLocaleString()}</td>
                          <td>
                            <button onClick={() => loadAdminChar(adminSelectedUser.id, c.id)} className="btn-link">查看详情</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* 移动端卡片 */}
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
                  
                  {/* 桌面端表格 */}
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
                          <td><span className="muted">{g.member_count || 0} 人</span></td>
                          <td>{new Date(g.created_at * 1000).toLocaleString()}</td>
                          <td>{new Date(g.updated_at * 1000).toLocaleString()}</td>
                          <td>
                            <button onClick={() => loadAdminGroup(g.id)} className="btn-link">查看详情</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* 移动端卡片 */}
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
                  
                  {/* 群聊详情 */}
                  {adminSelectedGroup && (
                    <div className="admin-detail-page" style={{marginTop: '2rem'}}>
                      <div className="admin-detail-header">
                        <h3>{adminSelectedGroup.name}</h3>
                        <div className="muted">ID: #{adminSelectedGroup.id}</div>
                      </div>
                      
                      <div className="admin-detail-section">
                        <h4>成员列表 ({adminSelectedGroup.members?.length || 0} 人)</h4>
                        <div className="member-list">
                          {adminSelectedGroup.members?.map((member: any, idx: number) => (
                            <div key={idx} className="member-item">
                              <div className="member-avatar">
                                {member.is_moderator ? '🎭' : '👤'}
                              </div>
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
                            const msgType = m.sender_type === 'user' ? 'user-msg' : 
                                          m.sender_type === 'moderator' ? 'moderator-msg' : 
                                          'character-msg'
                            const avatar = m.sender_type === 'user' ? '👤' :
                                         m.sender_type === 'moderator' ? '🎭' :
                                         '🤖'
                            // 显示具体的名字，而不是类型
                            const displayName = m.sender_name || (m.sender_type === 'user' ? (adminSelectedUser?.username || '用户') : '未知')
                            const badgeText = m.sender_type === 'user' ? '用户' :
                                            m.sender_type === 'moderator' ? '主持人' :
                                            '角色'
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
                      <pre className="json-view">
                        {adminSelectedChar.structured_json || '（无）'}
                      </pre>
                    </div>

                    <div className="admin-detail-section">
                      <h4>聊天记录 ({adminMessages.length} 条)</h4>
                      <div className="admin-msgs">
                        {adminMessages.map((m, i) => {
                          const mid = (m as any).id as number | undefined
                          const canInspect = (user?.is_admin === 1) && m.role === 'user' && adminSelectedUser && adminSelectedChar
                          const msgType = m.role === 'user' ? 'user-msg' : 'character-msg'
                          const avatar = m.role === 'user' ? '👤' : '🤖'
                          const senderName = m.role === 'user' ? (adminSelectedUser?.username || '用户') : adminSelectedChar.name
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
                                          params: { uid: adminSelectedUser!.id, cid: adminSelectedChar!.id, msg_id: mid, role: adminSelectedChar!.name }
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
                      {/* 桌面端表格 */}
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
                                <button onClick={() => loadAdminFeedback(f.id)} className="btn-link">查看详情</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {/* 移动端卡片 */}
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
                          <button onClick={() => setAdminSelectedFeedback(null)} className="settings">返回列表</button>
                        </div>
                      </div>
                      
                      <div className="admin-detail-section">
                        <div style={{display: 'flex', gap: '16px', marginBottom: '16px'}}>
                          <div><strong>反馈ID:</strong> #{adminSelectedFeedback.id}</div>
                          <div><strong>用户:</strong> {adminSelectedFeedback.username}</div>
                          <div><strong>提交时间:</strong> {new Date(adminSelectedFeedback.created_at * 1000).toLocaleString()}</div>
                        </div>
                        
                        <h4>反馈内容</h4>
                        <div className="feedback-content">
                          {adminSelectedFeedback.content}
                        </div>
                        
                        {adminSelectedFeedback.attachments && JSON.parse(adminSelectedFeedback.attachments).length > 0 && (
                          <div style={{marginTop: '16px'}}>
                            <h4>附件图片</h4>
                            <div style={{display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '12px'}}>
                              {JSON.parse(adminSelectedFeedback.attachments).map((url: string, idx: number) => (
                                <a key={idx} href={url} target="_blank" rel="noreferrer">
                                  <img src={url} alt="" style={{width: '150px', height: '150px', objectFit: 'cover', borderRadius: '8px', border: '1px solid var(--border)'}} />
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
                            style={{width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '8px', resize: 'vertical'}}
                          />
                        </label>
                        <div style={{display: 'flex', gap: '8px', marginTop: '12px'}}>
                          <button className="primary" onClick={() => updateFeedbackStatus(adminSelectedFeedback.id)}>保存更新</button>
                          <button onClick={() => deleteFeedback(adminSelectedFeedback.id)} style={{background: '#ef4444', color: 'white'}}>删除反馈</button>
                        </div>
                        {adminSelectedFeedback.admin_reply && (
                          <div style={{marginTop: '16px', padding: '12px', background: '#f3f4f6', borderRadius: '8px'}}>
                            <strong>当前回复:</strong>
                            <div style={{marginTop: '8px'}}>{adminSelectedFeedback.admin_reply}</div>
                            <div style={{marginTop: '8px', fontSize: '12px', color: '#6b7280'}}>
                              更新时间: {new Date(adminSelectedFeedback.updated_at * 1000).toLocaleString()}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            messages.map((m,i) => {
              const text = String(m.content || '')
              // 将消息按句号和感叹号分段
              const parts = text ? (text.match(/[^。！]+[。！]|[^。！]+/g) || ['']) : ['']
              const senderType = m.role === 'user' ? 'user' : 'character'
              const senderName = m.role === 'user' ? (user?.username || 'User') : activeRole
              
              return (
                <div key={i} className={`group-msg-item ${senderType}`}>
                  <div className="avatar">
                    {m.role === 'user' ? '👤' : '🎭'}
                  </div>
                  <div className="msg-right">
                    <div className="sender-name">{senderName}</div>
                    {parts.map((s, j) => (
                      <div key={j} className="bubble">{s}</div>
                    ))}
                    {(user?.is_admin===1 && m.role==='user' && (m as any).id) ? (
                      <button className="view-btn" onClick={async ()=>{
                        try{
                          const { data } = await api.get('/admin/chat/compiled', { 
                            params: { 
                              msg_id: (m as any).id, 
                              role: activeRole,
                              uid: user.id,
                              cid: 0  // 使用role自动查找
                            } 
                          })
                          const pretty = JSON.stringify(data, null, 2)
                          setInspectText(pretty)
                          setShowInspect(true)
                        }catch(e:any){
                          alert(e?.response?.data?.error || '获取失败')
                        }
                      }}>查看</button>
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
            onChange={e => { setInput(e.target.value); if (e.target.value) setTypingStatus('用户输入中...'); else setTypingStatus(''); }}
            placeholder="和角色聊天..." 
            onKeyDown={e=>{ if(e.key==='Enter') send() }} 
          />
          <button onClick={send}>发送</button>
        </footer>
        </main>
      )}

      {/* 群聊右侧简介栏 */}
      {activeType === 'group' && activeGroupId && !adminView && (
        <aside className="group-info-panel">
          <div className="info-header">
            <h3>成员简介</h3>
            <button className="manage-btn" onClick={() => setShowManageGroup(true)}>管理</button>
          </div>
          <div className="info-content">
            {groupMemberBriefs.map((member, idx) => (
              <div key={idx} className="member-brief">
                <div className="member-name">
                  {member.type === 'user' ? '👤' : '🎭'} {member.name}
                </div>
                <div className="member-intro">
                  {member.brief || '暂无简介'}
                </div>
              </div>
            ))}
          </div>
          {/* 反馈按钮（非管理员） */}
          {user && user.is_admin !== 1 && (
            <div style={{padding: '16px', borderTop: '1px solid var(--border)'}}>
              <button 
                className="feedback-btn-sidebar"
                onClick={() => {
                  setShowFeedback(true)
                  setFeedbackTab('submit')
                  loadMyFeedbacks()
                }}
              >
                💬 我要反馈
              </button>
            </div>
          )}
        </aside>
      )}

      {/* 单聊右侧简介栏 */}
      {activeType === 'character' && activeRole && !adminView && (
        <aside className="group-info-panel">
          <div className="info-header">
            <h3>角色简介</h3>
            <button className="manage-btn" onClick={() => setShowManageChar(true)}>管理</button>
          </div>
          <div className="info-content">
            <div className="member-brief">
              <div className="member-name">
                🎭 {activeRole}
              </div>
              {charIntro ? (
                <div className="member-intro" style={{
                  lineHeight: 1.6, 
                  whiteSpace: 'pre-wrap',
                  display: 'block',
                  WebkitLineClamp: 'unset',
                  WebkitBoxOrient: 'unset' as any,
                  overflow: 'visible'
                }}>
                  {charIntro}
                </div>
              ) : (
                <div className="member-intro">暂无简介</div>
              )}
            </div>
          </div>
          {/* 反馈按钮（非管理员） */}
          {user && user.is_admin !== 1 && (
            <div style={{padding: '16px', borderTop: '1px solid var(--border)'}}>
              <button 
                className="feedback-btn-sidebar"
                onClick={() => {
                  setShowFeedback(true)
                  setFeedbackTab('submit')
                  loadMyFeedbacks()
                }}
              >
                💬 我要反馈
              </button>
            </div>
          )}
        </aside>
      )}

      {showManageGroup && (
        <div className="modal" onClick={() => setShowManageGroup(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>管理群成员</h3>
            <div style={{marginBottom: 16}}>
              <h4 style={{marginBottom: 8}}>当前成员</h4>
              <div style={{maxHeight: 200, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, padding: 8}}>
                {groupMemberBriefs.map((member, idx) => (
                  <div key={idx} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', borderBottom: idx < groupMemberBriefs.length - 1 ? '1px solid #f3f4f6' : 'none'}}>
                    <span>
                      {member.type === 'user' ? '👤' : '🎭'} {member.name}
                    </span>
                    {member.type === 'character' && (
                      <button 
                        style={{fontSize: 12, padding: '2px 8px', background: '#ef4444', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer'}}
                        onClick={async () => {
                          if (!confirm(`确定移除 ${member.name}？`)) return
                          try {
                            await api.delete(`/api/groups/${activeGroupId}/members/${member.name}`)
                            await loadGroupMemberBriefs()
                          } catch (e: any) {
                            alert(e?.response?.data?.error || '移除失败')
                          }
                        }}
                      >
                        移除
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <div style={{marginBottom: 16}}>
              <h4 style={{marginBottom: 8}}>添加新成员</h4>
              <div style={{display: 'flex', gap: 8}}>
                <select 
                  value={newMemberName} 
                  onChange={e => setNewMemberName(e.target.value)}
                  style={{flex: 1, padding: '8px', border: '1px solid #e5e7eb', borderRadius: 8}}
                >
                  <option value="">选择角色</option>
                  {characters
                    .filter(c => !groupMemberBriefs.some(m => m.name === c.role))
                    .map(c => (
                      <option key={c.role} value={c.role}>{c.role}</option>
                    ))
                  }
                </select>
                <button 
                  onClick={async () => {
                    if (!newMemberName) {
                      alert('请选择角色')
                      return
                    }
                    try {
                      await api.post(`/api/groups/${activeGroupId}/members`, {
                        member_name: newMemberName
                      })
                      await loadGroupMemberBriefs()
                      setNewMemberName('')
                    } catch (e: any) {
                      alert(e?.response?.data?.error || '添加失败')
                    }
                  }}
                  style={{padding: '8px 16px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer'}}
                >
                  添加
                </button>
              </div>
            </div>
            <div className="actions" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <button 
                onClick={async () => {
                  if (!confirm('确定删除该群聊？删除后无法恢复！')) return
                  try {
                    await api.delete(`/api/groups/${activeGroupId}`)
                    // 刷新群聊列表
                    const { data } = await api.get('/api/groups')
                    setGroups(data.items || [])
                    // 关闭弹窗
                    setShowManageGroup(false)
                    // 切换到角色列表的第一个角色
                    setActiveType('character')
                    setActiveGroupId(null)
                    if (characters.length > 0) {
                      setActiveRole(characters[0].role)
                    }
                  } catch (e: any) {
                    alert(e?.response?.data?.error || '删除失败')
                  }
                }}
                style={{background: '#ef4444', color: 'white'}}
              >
                删除群聊
              </button>
              <button onClick={() => setShowManageGroup(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* 单聊管理弹窗 */}
      {showManageChar && (
        <div className="modal" onClick={() => setShowManageChar(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>管理角色</h3>
            <div style={{marginBottom: 16}}>
              <h4 style={{marginBottom: 8}}>角色配置</h4>
              <div style={{padding: 12, border: '1px solid #e5e7eb', borderRadius: 8}}>
                <a
                  href={`/structured/view?role=${encodeURIComponent(activeRole)}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'block',
                    padding: '10px 16px',
                    background: '#3b82f6',
                    color: 'white',
                    textAlign: 'center',
                    borderRadius: 8,
                    textDecoration: 'none',
                    fontSize: 14
                  }}
                >
                  🔧 打开角色配置页面
                </a>
                <div style={{marginTop: 12, fontSize: 12, color: '#666', lineHeight: 1.6}}>
                  在配置页面可以查看和编辑角色的详细信息、性格设定、记忆等内容
                </div>
              </div>
            </div>
            <div className="actions" style={{display: 'flex', justifyContent: 'flex-end'}}>
              <button onClick={() => setShowManageChar(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {showCreateGroup && (
        <div className="modal" onClick={() => setShowCreateGroup(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>创建群聊</h3>
            <label>
              群聊名称
              <input value={newGroupName} onChange={e => setNewGroupName(e.target.value)} placeholder="输入群聊名称" />
            </label>
            <label>
              选择成员（角色）
              <div style={{maxHeight: 200, overflowY: 'auto', border: '1px solid #ccc', padding: 8}}>
                {characters.map(c => (
                  <label key={c.role} style={{display: 'block'}}>
                    <input type="checkbox" checked={selectedMembers.includes(c.role)}
                      onChange={e => {
                        if (e.target.checked) {
                          setSelectedMembers([...selectedMembers, c.role])
                        } else {
                          setSelectedMembers(selectedMembers.filter(m => m !== c.role))
                        }
                      }}
                    />
                    {c.role}
                  </label>
                ))}
              </div>
            </label>
            <div className="actions">
              <button onClick={async () => {
                if (!newGroupName.trim()) { alert('请输入群聊名称'); return }
                if (selectedMembers.length === 0) { alert('请至少选择一个角色'); return }
                try {
                  const { data } = await api.post('/api/groups', {
                    name: newGroupName.trim(),
                    members: selectedMembers
                  })
                  const grps = await api.get('/api/groups')
                  setGroups(grps.data.items || [])
                  setActiveType('group')
                  setActiveGroupId(data.group_id)
                  setActiveRole('')
                  setShowCreateGroup(false)
                  setNewGroupName('')
                  setSelectedMembers([])
                } catch (e: any) {
                  alert(e?.response?.data?.error || '创建失败')
                }
              }}>创建</button>
              <button onClick={() => setShowCreateGroup(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="modal">
          <div className="dialog">
            <h3>新建角色</h3>
            <label>角色名
              <input value={newRole} onChange={e=>setNewRole(e.target.value)} placeholder="输入角色名" />
            </label>
            <label>数据源
              <select value={newSource} onChange={e=>setNewSource(e.target.value as any)}>
                <option value="baike">百度百科 (baike)</option>
                <option value="zhwiki">中文维基 (zhwiki)</option>
              </select>
            </label>
            {/* 义项选择入口已改为“点击创建时自动弹窗”，此处不再显示 */}
            <label>结构化程度
              <select value={newDetail} onChange={e=>setNewDetail(e.target.value as any)}>
                <option value="concise">简洁（仅核心八类与默认安全限制、基本任务与对话意图）</option>
                <option value="detailed">细化（含经历/关系网络/知识领域/世界观/时间线/社会规则/外部资源/行为约束/著名故事/组织/安全限制）</option>
              </select>
            </label>
            {(user?.is_admin === 1) && (
              <details style={{margin:'6px 0'}}>
                <summary style={{cursor:'pointer', color:'#374151'}}>管理员测试选项（导出中间产物）</summary>
                <div className="opt-grid">
                  <label className="opt-chip" title="导出模型分块事实抽取（mapreduce策略下）">
                    <input type="checkbox" checked={exportFacts} onChange={e=>setExportFacts(e.target.checked)} />
                    <div className="chip">
                      <span className="title">导出事实</span>
                      <span className="suffix">facts_*.json</span>
                    </div>
                  </label>
                  <label className="opt-chip" title="导出要点文本（旧版 bullets）">
                    <input type="checkbox" checked={exportBullets} onChange={e=>setExportBullets(e.target.checked)} />
                    <div className="chip">
                      <span className="title">导出要点</span>
                      <span className="suffix">bullets_*.txt</span>
                    </div>
                  </label>
                  <label className="opt-chip" title="导出全局详细摘要（global 策略）">
                    <input type="checkbox" checked={exportSummary} onChange={e=>setExportSummary(e.target.checked)} />
                    <div className="chip">
                      <span className="title">导出摘要</span>
                      <span className="suffix">summary_*.txt</span>
                    </div>
                  </label>
                  <label className="opt-chip" title="导出 JSON→Markdown 的中间结果">
                    <input type="checkbox" checked={exportMd} onChange={e=>setExportMd(e.target.checked)} />
                    <div className="chip">
                      <span className="title">导出 Markdown</span>
                      <span className="suffix">md_*.md</span>
                    </div>
                  </label>
                  <label className="opt-chip" title="导出每次请求发送到模型前的上下文（含来源标注）">
                    <input type="checkbox" checked={exportCtx} onChange={e=>setExportCtx(e.target.checked)} />
                    <div className="chip">
                      <span className="title">导出请求上下文</span>
                      <span className="suffix">ctx_*.json</span>
                    </div>
                  </label>
                </div>
              </details>
            )}
            {creating && !progress && (
              <div style={{marginTop: 12, padding: '10px 12px', background: '#f3f4f6', borderRadius: 6, color: '#6b7280', fontSize: 14}}>
                ⏱️ 预计创建时间约 2 分钟，请耐心等待...
              </div>
            )}
            {progress && (
              <div className="progress">
                <div>
                  {progress.message} ({progress.progress ?? 0}%)
                  {typeof progress.elapsed_sec === 'number' && (
                    <span style={{marginLeft:8, color:'#6b7280'}}>用时 {(() => {
                      const sec = Math.max(0, progress.elapsed_sec||0);
                      const h = Math.floor(sec/3600), m = Math.floor((sec%3600)/60), s = sec%60;
                      return h ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
                    })()}</span>
                  )}
                </div>
                <progress value={progress.progress || 0} max={100}></progress>
              </div>
            )}
            <div className="actions">
              <button onClick={()=>{ setShowCreate(false); setProgress(null); setCreateDone(false); setCreating(false); setNewRole(''); }}>取消</button>
              {createDone ? (
                <button className="primary" onClick={()=>{ setShowCreate(false); setProgress(null); setCreateDone(false); setNewRole(''); }}>完成</button>
              ) : (
                <button onClick={createRole} className="primary" disabled={creating}>{creating ? '创建中...' : '创建'}</button>
              )}
            </div>
          </div>
        </div>
      )}
      {showInspect && (
        <div className="modal" onClick={()=>setShowInspect(false)}>
          <div className="dialog" onClick={e=>e.stopPropagation()} style={{width:'80vw', maxWidth: '1200px', height:'70vh', display:'flex', flexDirection:'column'}}>
            <h3>最终发送内容</h3>
            <pre className="json-view" style={{flex:1, overflow:'auto', whiteSpace:'pre-wrap', wordBreak:'break-word'}}>{inspectText}</pre>
            <div className="actions">
              <button onClick={()=>{ navigator.clipboard?.writeText(inspectText).catch(()=>{}); }}>复制</button>
              <button className="primary" onClick={()=>setShowInspect(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <div className="modal">
          <div className="dialog">
            <h3>用户设置</h3>
            <label>默认模型
              <select value={defaultModel} onChange={e=>setDefaultModel(e.target.value)}>
                <option value="">（使用系统/环境默认）</option>
                {allowedModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
            <label>上下文预算（字符）
              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
                <input type="number" min={0} placeholder="会话记忆（默认 3000）" value={ctxMaxChat} onChange={e=>setCtxMaxChat(e.target.value)} />
                <input type="number" min={0} placeholder="短期记忆（默认 3000）" value={ctxMaxStm} onChange={e=>setCtxMaxStm(e.target.value)} />
                <input type="number" min={0} placeholder="长期记忆（默认 4000）" value={ctxMaxLtm} onChange={e=>setCtxMaxLtm(e.target.value)} />
              </div>
            </label>
            <label>个人简介（用于群聊）
              <textarea 
                value={userProfile} 
                onChange={e => setUserProfile(e.target.value)} 
                placeholder="简单介绍自己，用于群聊中其他角色了解你"
                rows={3}
                style={{width:'100%', padding:'10px', border:'1px solid var(--border)', borderRadius:'8px', boxSizing:'border-box', resize:'vertical'}}
              />
            </label>
            <label>群聊最大角色回复轮数（默认3）
              <input 
                type="number" 
                min={1} 
                max={10} 
                value={maxGroupReplyRounds} 
                onChange={e => setMaxGroupReplyRounds(e.target.value)} 
                placeholder="默认3"
              />
              <div style={{fontSize:12, color:'#6b7280', marginTop:4}}>
                角色连续发言达到此轮数后，将等待用户输入
              </div>
            </label>
            {/* 模型回退顺序由系统随机，不提供手动设置 */}
            <label>修改密码
              <input type="password" placeholder="原密码" value={oldPwd} onChange={e=>setOldPwd(e.target.value)} />
              <input type="password" placeholder="新密码（≥6位）" value={newPwd} onChange={e=>setNewPwd(e.target.value)} />
            </label>
            <label>注销账户（请输入当前密码以确认）
              <input type="password" placeholder="当前密码" value={deletePwd} onChange={e=>setDeletePwd(e.target.value)} />
              <button style={{marginTop:8}} onClick={deleteAccount}>确认注销</button>
            </label>
            <div className="actions">
              <button onClick={()=>setShowSettings(false)}>关闭</button>
              <button className="primary" onClick={saveSettings}>保存</button>
            </div>
          </div>
        </div>
      )}
      {menuVisible && menuRole && (
        <div style={{position:'fixed', left:menuPos.x, top:menuPos.y, zIndex:1000, background:'#fff', border:'1px solid #e5e7eb', boxShadow:'0 4px 12px rgba(0,0,0,0.08)', borderRadius:8, overflow:'hidden'}}>
          <button style={{display:'block', width:160, textAlign:'left', padding:'8px 12px'}} onClick={()=>{ setRenaming(menuRole); setNewName(menuRole); setMenuVisible(false) }}>重命名</button>
          <button style={{display:'block', width:160, textAlign:'left', padding:'8px 12px'}} onClick={()=>{ copyRole(menuRole); setMenuVisible(false) }}>复制</button>
          <button style={{display:'block', width:160, textAlign:'left', padding:'8px 12px', color:'#b91c1c'}} onClick={()=>{ deleteRole(menuRole); setMenuVisible(false) }}>删除</button>
        </div>
      )}
      {showPoly && (
        <div className="modal" style={{alignItems:'center', justifyContent:'center'}}>
          <div className="dialog" style={{width: '80vw', maxWidth: '1200px', height: '70vh', display:'flex', flexDirection:'column'}}>
            <h3>选择同名词条</h3>
            <div style={{display:'flex', gap:8, alignItems:'center', padding: '8px 0'}}>
              <span style={{fontSize: 16, fontWeight: 500}}>🎭 {newRole}</span>
              <span className="muted">{polyLoading? '加载中…' : `共 ${polyOptions.length} 项`}</span>
              {polyRoute ? (
                <span className="muted" style={{marginLeft:8}}>来源: {polyRoute}</span>
              ) : null}
            </div>
            <div style={{flex:1, overflow:'auto', marginTop: 8}}>
              {/* 多列卡片布局：点击文本块即可选择，选中高亮 */}
              <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(300px, 1fr))', gap:12}}>
                {polyOptions.map((it:any, idx:number) => {
                  const selected = polyChoiceIdx===idx
                  return (
                    <div key={idx} onClick={()=>{ setPolyChoiceIdx(idx); setPolyChoiceHref(it.href) }}
                      style={{
                        border:'1px solid',
                        borderColor: selected ? '#2563eb' : '#e5e7eb',
                        background: selected ? 'rgba(37,99,235,0.06)' : 'white',
                        borderRadius:8, padding:12, cursor:'pointer',
                        transition:'border-color .15s ease, background .15s ease'
                      }}>
                      <div style={{fontWeight:600, lineHeight:1.5, wordBreak:'break-word', whiteSpace:'normal'}}>{it.text}</div>
                      {it.snippet ? (
                        <div className="muted" style={{marginTop:4, fontSize:12, lineHeight:1.5, wordBreak:'break-word'}}>{it.snippet}</div>
                      ) : null}
                      {it.href ? (
                        <div className="muted" style={{marginTop:6, fontSize:12, wordBreak:'break-all'}}>
                          <a href={it.href} target="_blank" rel="noreferrer">{it.href}</a>
                        </div>
                      ) : null}
                    </div>
                  )})}
              </div>
            </div>
            <div className="actions">
              <button onClick={()=>{ setShowPoly(false); setPolyLoading(false); setProgress(null); }}>取消</button>
              <button className="primary" onClick={()=>{ setShowPoly(false); createRole(); }} disabled={polyChoiceIdx === null}>选择</button>
            </div>
          </div>
        </div>
      )}

      {/* 反馈弹窗 */}
      {showFeedback && (
        <div className="modal" onClick={() => {
          setShowFeedback(false)
          setFeedbackTitle('')
          setFeedbackContent('')
          setFeedbackAttachments([])
          setSelectedFeedback(null)
        }}>
          <div className="dialog feedback-dialog" onClick={e => e.stopPropagation()}>
            <div className="feedback-header">
              <h3>💬 用户反馈</h3>
              <button className="close-btn" onClick={() => {
                setShowFeedback(false)
                setFeedbackTitle('')
                setFeedbackContent('')
                setFeedbackAttachments([])
                setSelectedFeedback(null)
              }}>×</button>
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
              <button 
                className={feedbackTab === 'history' ? 'active' : ''}
                onClick={() => setFeedbackTab('history')}
              >
                📋 我的反馈 {myFeedbacks.length > 0 && `(${myFeedbacks.length})`}
              </button>
            </div>

            {feedbackTab === 'submit' ? (
              <div className="feedback-content">
            <label>
              标题
              <input 
                type="text" 
                value={feedbackTitle}
                onChange={e => setFeedbackTitle(e.target.value)}
                placeholder="请简要描述问题"
              />
            </label>
            <label>
              详细内容
              <textarea 
                value={feedbackContent}
                onChange={e => setFeedbackContent(e.target.value)}
                placeholder="请详细描述您遇到的问题或建议"
                rows={6}
                style={{width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '8px', resize: 'vertical'}}
              />
            </label>
            <label>
              上传图片（可选）
              <input 
                type="file" 
                accept="image/*"
                onChange={handleFeedbackImageUpload}
                disabled={feedbackUploading}
              />
              {feedbackUploading && <div style={{marginTop: '8px', color: '#6b7280'}}>上传中...</div>}
            </label>
            {feedbackAttachments.length > 0 && (
              <div style={{marginTop: '12px'}}>
                <div style={{fontSize: '14px', fontWeight: 600, marginBottom: '8px'}}>已上传的图片：</div>
                <div style={{display: 'flex', flexWrap: 'wrap', gap: '12px'}}>
                  {feedbackAttachments.map((url, idx) => (
                    <div key={idx} style={{position: 'relative'}}>
                      <img 
                        src={url} 
                        alt={`附件${idx + 1}`} 
                        style={{
                          width: '120px', 
                          height: '120px', 
                          objectFit: 'cover', 
                          borderRadius: '8px', 
                          border: '2px solid var(--border)',
                          cursor: 'pointer'
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
                          boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
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
              <button onClick={() => {
                setShowFeedback(false)
                setFeedbackTitle('')
                setFeedbackContent('')
                setFeedbackAttachments([])
              }} className="btn-secondary">取消</button>
              <button className="btn-primary" onClick={submitFeedback}>✅ 提交反馈</button>
            </div>
              </div>
            ) : (
              <div className="feedback-content">
                {!selectedFeedback ? (
                  <>
                    {myFeedbacks.length === 0 ? (
                      <div className="empty-state">
                        <div style={{fontSize: '48px', marginBottom: '16px'}}>📭</div>
                        <p style={{color: '#6b7280'}}>暂无反馈记录</p>
                      </div>
                    ) : (
                      <div className="feedback-list">
                        {myFeedbacks.map(fb => (
                          <div key={fb.id} className="feedback-item" onClick={() => setSelectedFeedback(fb)}>
                            <div className="feedback-item-header">
                              <h4>{fb.title}</h4>
                              <span className={`feedback-status ${fb.status}`}>
                                {fb.status === 'pending' ? '⏳ 待处理' : 
                                 fb.status === 'in_progress' ? '🔄 处理中' : 
                                 fb.status === 'resolved' ? '✅ 已解决' : '❌ 已拒绝'}
                              </span>
                            </div>
                            <p className="feedback-item-content">{fb.content}</p>
                            <div className="feedback-item-footer">
                              <span className="feedback-item-time">
                                {new Date(fb.created_at * 1000).toLocaleString()}
                              </span>
                              {fb.admin_reply && <span className="has-reply">💬 有回复</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="feedback-detail">
                    <button onClick={() => setSelectedFeedback(null)} className="back-btn">← 返回列表</button>
                    
                    <div className="feedback-detail-header">
                      <h3>{selectedFeedback.title}</h3>
                      <span className={`feedback-status ${selectedFeedback.status}`}>
                        {selectedFeedback.status === 'pending' ? '⏳ 待处理' : 
                         selectedFeedback.status === 'in_progress' ? '🔄 处理中' : 
                         selectedFeedback.status === 'resolved' ? '✅ 已解决' : '❌ 已拒绝'}
                      </span>
                    </div>
                    
                    <div className="feedback-detail-section">
                      <label>反馈内容</label>
                      <div className="feedback-text">{selectedFeedback.content}</div>
                    </div>
                    
                    {selectedFeedback.attachments && JSON.parse(selectedFeedback.attachments).length > 0 && (
                      <div className="feedback-detail-section">
                        <label>附件图片</label>
                        <div style={{display: 'flex', flexWrap: 'wrap', gap: '12px'}}>
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
                                  border: '1px solid var(--border)'
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
                        <div className="admin-reply-box">
                          {selectedFeedback.admin_reply}
                        </div>
                        <div className="reply-time">
                          回复时间: {new Date(selectedFeedback.updated_at * 1000).toLocaleString()}
                        </div>
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
      )}
      </div>
  )
}

export default App
