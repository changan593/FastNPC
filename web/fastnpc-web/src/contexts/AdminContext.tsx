import { createContext, useContext, useState, ReactNode } from 'react'
import type { AdminUser, AdminCharacter, GroupItem, GroupMessage, Message, Feedback } from '../types'
import { useAuth } from './AuthContext'

interface AdminContextType {
  adminView: boolean
  setAdminView: (view: boolean) => void
  adminUsers: AdminUser[]
  setAdminUsers: (users: AdminUser[]) => void
  adminSelectedUser: AdminUser | null
  setAdminSelectedUser: (user: AdminUser | null) => void
  adminUserChars: AdminCharacter[]
  setAdminUserChars: (chars: AdminCharacter[]) => void
  adminSelectedChar: AdminCharacter | null
  setAdminSelectedChar: (char: AdminCharacter | null) => void
  adminMessages: Message[]
  setAdminMessages: (msgs: Message[]) => void
  adminTab: 'users' | 'characters' | 'groups' | 'feedbacks' | 'detail'
  setAdminTab: (tab: 'users' | 'characters' | 'groups' | 'feedbacks' | 'detail') => void
  adminSearchQuery: string
  setAdminSearchQuery: (query: string) => void
  
  // 管理员查看群聊
  adminUserGroups: GroupItem[]
  setAdminUserGroups: (groups: GroupItem[]) => void
  adminSelectedGroup: any | null
  setAdminSelectedGroup: (group: any) => void
  adminGroupMessages: GroupMessage[]
  setAdminGroupMessages: (msgs: GroupMessage[]) => void
  
  // 管理员反馈
  adminFeedbacks: Feedback[]
  setAdminFeedbacks: (feedbacks: Feedback[]) => void
  adminSelectedFeedback: Feedback | null
  setAdminSelectedFeedback: (feedback: Feedback | null) => void
  feedbackReply: string
  setFeedbackReply: (reply: string) => void
  feedbackStatus: 'pending' | 'in_progress' | 'resolved' | 'rejected'
  setFeedbackStatus: (status: 'pending' | 'in_progress' | 'resolved' | 'rejected') => void
  
  // inspect modal
  showInspect: boolean
  setShowInspect: (show: boolean) => void
  inspectText: string
  setInspectText: (text: string) => void
  
  // 方法
  openAdmin: () => Promise<void>
  loadAdminUser: (uid: number) => Promise<void>
  loadAdminUserGroups: (uid: number) => Promise<void>
  loadAdminGroup: (groupId: number) => Promise<void>
  loadAdminFeedbacks: () => Promise<void>
  loadAdminFeedback: (feedbackId: number) => Promise<void>
  updateFeedbackStatus: (feedbackId: number) => Promise<void>
  deleteFeedback: (feedbackId: number) => Promise<void>
  loadAdminChar: (uid: number, cid: number) => Promise<void>
  cleanupAdminUserChars: (uid: number) => Promise<void>
  refreshAdminData: () => Promise<void>
}

const AdminContext = createContext<AdminContextType | undefined>(undefined)

export function AdminProvider({ children }: { children: ReactNode }) {
  const { api } = useAuth()
  
  const [adminView, setAdminView] = useState(false)
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [adminSelectedUser, setAdminSelectedUser] = useState<AdminUser|null>(null)
  const [adminUserChars, setAdminUserChars] = useState<AdminCharacter[]>([])
  const [adminSelectedChar, setAdminSelectedChar] = useState<AdminCharacter|null>(null)
  const [adminMessages, setAdminMessages] = useState<Message[]>([])
  const [adminTab, setAdminTab] = useState<'users'|'characters'|'groups'|'feedbacks'|'detail'>('users')
  const [adminSearchQuery, setAdminSearchQuery] = useState('')
  
  // 管理员查看群聊
  const [adminUserGroups, setAdminUserGroups] = useState<GroupItem[]>([])
  const [adminSelectedGroup, setAdminSelectedGroup] = useState<any|null>(null)
  const [adminGroupMessages, setAdminGroupMessages] = useState<GroupMessage[]>([])
  
  // 管理员反馈
  const [adminFeedbacks, setAdminFeedbacks] = useState<Feedback[]>([])
  const [adminSelectedFeedback, setAdminSelectedFeedback] = useState<Feedback|null>(null)
  const [feedbackReply, setFeedbackReply] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState<'pending' | 'in_progress' | 'resolved' | 'rejected'>('pending')
  
  // inspect modal
  const [showInspect, setShowInspect] = useState(false)
  const [inspectText, setInspectText] = useState('')

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
    } catch (e: any) {
      console.error('加载用户角色失败:', e)
      alert(e?.response?.data?.error || '加载用户角色失败')
    }
  }

  async function loadAdminUserGroups(uid: number) {
    try {
      const { data } = await api.get(`/admin/users/${uid}/groups`)
      setAdminSelectedUser(adminUsers.find(u => u.id === uid) || null)
      setAdminUserGroups(data.items || [])
      setAdminSelectedGroup(null)
      setAdminGroupMessages([])
      setAdminTab('groups')
    } catch (e: any) {
      console.error('加载用户群聊失败:', e)
      alert(e?.response?.data?.error || '加载用户群聊失败')
    }
  }

  async function loadAdminGroup(groupId: number) {
    try {
      const { data: detail } = await api.get(`/admin/groups/${groupId}`)
      setAdminSelectedGroup(detail.group)
      const { data: msgs } = await api.get(`/admin/groups/${groupId}/messages`)
      setAdminGroupMessages(msgs.messages || [])
    } catch (e: any) {
      console.error('加载群聊详情失败:', e)
      alert(e?.response?.data?.error || '加载群聊详情失败')
    }
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
    } catch (e: any) {
      console.error('加载角色详情失败:', e)
      alert(e?.response?.data?.error || '加载角色详情失败')
    }
  }

  return (
    <AdminContext.Provider
      value={{
        adminView,
        setAdminView,
        adminUsers,
        setAdminUsers,
        adminSelectedUser,
        setAdminSelectedUser,
        adminUserChars,
        setAdminUserChars,
        adminSelectedChar,
        setAdminSelectedChar,
        adminMessages,
        setAdminMessages,
        adminTab,
        setAdminTab,
        adminSearchQuery,
        setAdminSearchQuery,
        adminUserGroups,
        setAdminUserGroups,
        adminSelectedGroup,
        setAdminSelectedGroup,
        adminGroupMessages,
        setAdminGroupMessages,
        adminFeedbacks,
        setAdminFeedbacks,
        adminSelectedFeedback,
        setAdminSelectedFeedback,
        feedbackReply,
        setFeedbackReply,
        feedbackStatus,
        setFeedbackStatus,
        showInspect,
        setShowInspect,
        inspectText,
        setInspectText,
        openAdmin,
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
      }}
    >
      {children}
    </AdminContext.Provider>
  )
}

export function useAdmin() {
  const context = useContext(AdminContext)
  if (context === undefined) {
    throw new Error('useAdmin must be used within an AdminProvider')
  }
  return context
}

