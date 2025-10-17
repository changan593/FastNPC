import { createContext, useContext, useState, useRef, ReactNode } from 'react'
import type { GroupItem, GroupMessage, MemberBrief } from '../types'
import { useAuth } from './AuthContext'

interface GroupContextType {
  groups: GroupItem[]
  setGroups: (groups: GroupItem[]) => void
  activeGroupId: number | null
  setActiveGroupId: (id: number | null) => void
  groupMessages: GroupMessage[]
  setGroupMessages: (msgs: GroupMessage[]) => void
  groupMemberBriefs: MemberBrief[]
  setGroupMemberBriefs: (briefs: MemberBrief[]) => void
  
  // 创建群聊
  showCreateGroup: boolean
  setShowCreateGroup: (show: boolean) => void
  newGroupName: string
  setNewGroupName: (name: string) => void
  selectedMembers: string[]
  setSelectedMembers: (members: string[]) => void
  
  // 管理群聊
  showManageGroup: boolean
  setShowManageGroup: (show: boolean) => void
  newMemberName: string
  setNewMemberName: (name: string) => void
  
  // 中控状态
  typingStatus: string
  setTypingStatus: (status: string) => void
  characterReplyCountRef: React.MutableRefObject<number>
  userInputTimeout: number | null
  setUserInputTimeout: (timeout: number | null) => void
  characterReplyTimeout: number | null
  setCharacterReplyTimeout: (timeout: number | null) => void
  
  // 方法
  reloadGroupMessages: () => Promise<void>
  loadGroupMemberBriefs: () => Promise<void>
  sendGroupMessage: (input: string, setInput: (v: string) => void, maxGroupReplyRounds: string) => Promise<void>
  triggerModerator: (maxGroupReplyRounds: string) => Promise<void>
  handleUserTyping: () => void
}

const GroupContext = createContext<GroupContextType | undefined>(undefined)

export function GroupProvider({ children }: { children: ReactNode }) {
  const { api } = useAuth()
  
  const [groups, setGroups] = useState<GroupItem[]>([])
  const [activeGroupId, setActiveGroupId] = useState<number|null>(null)
  const [groupMessages, setGroupMessages] = useState<GroupMessage[]>([])
  const [groupMemberBriefs, setGroupMemberBriefs] = useState<MemberBrief[]>([])
  
  // 创建群聊
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [selectedMembers, setSelectedMembers] = useState<string[]>([])
  
  // 管理群聊
  const [showManageGroup, setShowManageGroup] = useState(false)
  const [newMemberName, setNewMemberName] = useState('')
  
  // 中控状态
  const [typingStatus, setTypingStatus] = useState<string>('')
  const characterReplyCountRef = useRef(0)
  const [userInputTimeout, setUserInputTimeout] = useState<number|null>(null)
  const [characterReplyTimeout, setCharacterReplyTimeout] = useState<number|null>(null)

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

  async function sendGroupMessage(input: string, setInput: (v: string) => void, maxGroupReplyRounds: string) {
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
      triggerModerator(maxGroupReplyRounds)
    } catch (e: any) {
      alert(e?.response?.data?.error || '发送失败')
    }
  }

  async function triggerModerator(maxGroupReplyRounds: string) {
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
        triggerModerator(maxGroupReplyRounds)
      }, 3000)
      setCharacterReplyTimeout(timer)
    } catch (e: any) {
      console.error('中控判断失败', e)
      setTypingStatus('')
    }
  }

  return (
    <GroupContext.Provider
      value={{
        groups,
        setGroups,
        activeGroupId,
        setActiveGroupId,
        groupMessages,
        setGroupMessages,
        groupMemberBriefs,
        setGroupMemberBriefs,
        showCreateGroup,
        setShowCreateGroup,
        newGroupName,
        setNewGroupName,
        selectedMembers,
        setSelectedMembers,
        showManageGroup,
        setShowManageGroup,
        newMemberName,
        setNewMemberName,
        typingStatus,
        setTypingStatus,
        characterReplyCountRef,
        userInputTimeout,
        setUserInputTimeout,
        characterReplyTimeout,
        setCharacterReplyTimeout,
        reloadGroupMessages,
        loadGroupMemberBriefs,
        sendGroupMessage,
        triggerModerator,
        handleUserTyping,
      }}
    >
      {children}
    </GroupContext.Provider>
  )
}

export function useGroup() {
  const context = useContext(GroupContext)
  if (context === undefined) {
    throw new Error('useGroup must be used within a GroupProvider')
  }
  return context
}

