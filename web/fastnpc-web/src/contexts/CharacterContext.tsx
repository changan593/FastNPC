import { createContext, useContext, useState, useRef, ReactNode } from 'react'
import type { CharacterItem, Message, TaskState } from '../types'
import { useAuth } from './AuthContext'

interface CharacterContextType {
  characters: CharacterItem[]
  setCharacters: (chars: CharacterItem[]) => void
  activeRole: string
  setActiveRole: (role: string) => void
  messages: Message[]
  setMessages: (msgs: Message[] | ((prev: Message[]) => Message[])) => void
  input: string
  setInput: (input: string) => void
  typingStatus: string
  setTypingStatus: (status: string) => void
  
  // 创建角色相关
  showCreate: boolean
  setShowCreate: (show: boolean) => void
  newRole: string
  setNewRole: (role: string) => void
  newSource: 'baike' | 'zhwiki'
  setNewSource: (source: 'baike' | 'zhwiki') => void
  newDetail: 'concise' | 'detailed'
  setNewDetail: (detail: 'concise' | 'detailed') => void
  creating: boolean
  setCreating: (creating: boolean) => void
  progress: TaskState | null
  setProgress: (progress: TaskState | null) => void
  createDone: boolean
  setCreateDone: (done: boolean) => void
  exportFacts: boolean
  setExportFacts: (exp: boolean) => void
  exportBullets: boolean
  setExportBullets: (exp: boolean) => void
  exportSummary: boolean
  setExportSummary: (exp: boolean) => void
  exportMd: boolean
  setExportMd: (exp: boolean) => void
  exportCtx: boolean
  setExportCtx: (exp: boolean) => void
  
  // 消歧相关
  showPoly: boolean
  setShowPoly: (show: boolean) => void
  polyOptions: {text: string; href: string}[]
  setPolyOptions: (options: {text: string; href: string}[]) => void
  polyLoading: boolean
  setPolyLoading: (loading: boolean) => void
  polyFilter: string
  setPolyFilter: (filter: string) => void
  polyChoiceIdx: number | null
  setPolyChoiceIdx: (idx: number | null) => void
  polyChoiceHref: string
  setPolyChoiceHref: (href: string) => void
  polyRoute: string
  setPolyRoute: (route: string) => void
  polyReqSeqRef: React.MutableRefObject<number>
  
  // 右键菜单
  menuVisible: boolean
  setMenuVisible: (visible: boolean) => void
  menuPos: { x: number; y: number }
  setMenuPos: (pos: { x: number; y: number }) => void
  menuRole: string
  setMenuRole: (role: string) => void
  
  // 重命名
  renaming: string
  setRenaming: (role: string) => void
  newName: string
  setNewName: (name: string) => void
  
  // 单聊角色简介
  charIntro: string
  setCharIntro: (intro: string) => void
  showManageChar: boolean
  setShowManageChar: (show: boolean) => void
  
  // 方法
  refreshList: () => Promise<void>
  createRole: () => Promise<void>
  renameRole: (oldName: string) => Promise<void>
  deleteRole: (name: string) => Promise<void>
  copyRole: (name: string) => Promise<void>
  send: () => void
  reloadMessages: () => Promise<void>
  loadCharBrief: () => Promise<void>
}

const CharacterContext = createContext<CharacterContextType | undefined>(undefined)

export function CharacterProvider({ children }: { children: ReactNode }) {
  const { api, user } = useAuth()
  
  const [characters, setCharacters] = useState<CharacterItem[]>([])
  const [activeRole, setActiveRole] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [typingStatus, setTypingStatus] = useState<string>('')
  
  // 创建角色相关
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
  
  // 消歧相关
  const [showPoly, setShowPoly] = useState(false)
  const [polyOptions, setPolyOptions] = useState<{text:string, href:string}[]>([])
  const [polyLoading, setPolyLoading] = useState(false)
  const [polyFilter, setPolyFilter] = useState('')
  const [polyChoiceIdx, setPolyChoiceIdx] = useState<number|null>(null)
  const [polyChoiceHref, setPolyChoiceHref] = useState<string>('')
  const [polyRoute, setPolyRoute] = useState<string>('')
  const polyReqSeqRef = useRef<number>(0)
  
  // 右键菜单
  const [menuVisible, setMenuVisible] = useState(false)
  const [menuPos, setMenuPos] = useState<{x:number,y:number}>({x:0,y:0})
  const [menuRole, setMenuRole] = useState<string>('')
  
  // 重命名
  const [renaming, setRenaming] = useState<string>('')
  const [newName, setNewName] = useState<string>('')
  
  // 单聊角色简介
  const [charIntro, setCharIntro] = useState<string>('')
  const [showManageChar, setShowManageChar] = useState(false)

  async function refreshList() {
    const { data } = await api.get('/api/characters')
    setCharacters(data.items || [])
  }

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

  async function createRole() {
    if (!newRole.trim()) return
    // 若为百科/维基且尚未选择具体义项，则先弹出同名选择
    if ((newSource === 'baike' || newSource === 'zhwiki') && polyChoiceIdx == null) {
      // 需要先打开消歧弹窗，不在这里处理
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

  async function copyRole(name: string) {
    try {
      const { data } = await api.post(`/api/characters/${encodeURIComponent(name)}/copy`)
      await refreshList()
      if (data?.new_name) setActiveRole(data.new_name)
    } catch (e:any) { alert(e?.response?.data?.error || '复制失败') }
  }

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

  return (
    <CharacterContext.Provider
      value={{
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
        setNewRole,
        newSource,
        setNewSource,
        newDetail,
        setNewDetail,
        creating,
        setCreating,
        progress,
        setProgress,
        createDone,
        setCreateDone,
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
        showPoly,
        setShowPoly,
        polyOptions,
        setPolyOptions,
        polyLoading,
        setPolyLoading,
        polyFilter,
        setPolyFilter,
        polyChoiceIdx,
        setPolyChoiceIdx,
        polyChoiceHref,
        setPolyChoiceHref,
        polyRoute,
        setPolyRoute,
        polyReqSeqRef,
        menuVisible,
        setMenuVisible,
        menuPos,
        setMenuPos,
        menuRole,
        setMenuRole,
        renaming,
        setRenaming,
        newName,
        setNewName,
        charIntro,
        setCharIntro,
        showManageChar,
        setShowManageChar,
        refreshList,
        createRole,
        renameRole,
        deleteRole,
        copyRole,
        send,
        reloadMessages,
        loadCharBrief,
      }}
    >
      {children}
    </CharacterContext.Provider>
  )
}

export function useCharacter() {
  const context = useContext(CharacterContext)
  if (context === undefined) {
    throw new Error('useCharacter must be used within a CharacterProvider')
  }
  return context
}

