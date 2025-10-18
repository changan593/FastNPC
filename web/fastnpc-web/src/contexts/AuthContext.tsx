import { createContext, useContext, useState, type ReactNode } from 'react'
import axios from 'axios'

interface User {
  id: number
  username: string
  is_admin?: number
  avatar_url?: string
}

interface AuthContextType {
  user: User | null
  setUser: (user: User | null) => void
  authMode: 'login' | 'register'
  setAuthMode: (mode: 'login' | 'register') => void
  authForm: { username: string; password: string }
  setAuthForm: (form: { username: string; password: string }) => void
  agreedToTerms: boolean
  setAgreedToTerms: (agreed: boolean) => void
  showTerms: boolean
  setShowTerms: (show: boolean) => void
  doLogin: () => Promise<void>
  doRegister: () => Promise<void>
  doLogout: () => Promise<void>
  api: ReturnType<typeof axios.create>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authForm, setAuthForm] = useState({ username: '', password: '' })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [showTerms, setShowTerms] = useState(false)

  const api = axios.create({ withCredentials: true })

  async function doLogin() {
    try {
      const { data } = await api.post('/auth/login', authForm)
      
      // 立即清空表单（安全）
      setAuthForm({ username: '', password: '' })
      
      setUser(data.user)
      
      // 返回用户数据，以便App.tsx加载角色和群聊
      return data.user
    } catch (e: any) {
      alert(e?.response?.data?.error || '登录失败')
      throw e
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
      
      // 返回用户数据
      return data.user
    } catch (e: any) {
      alert(e?.response?.data?.error || '注册失败')
      throw e
    }
  }

  async function doLogout() {
    try { await api.post('/auth/logout') } catch {}
    
    // 清空用户数据
    setUser(null)
    
    // 清空表单（安全）
    setAuthForm({ username: '', password: '' })
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        authMode,
        setAuthMode,
        authForm,
        setAuthForm,
        agreedToTerms,
        setAgreedToTerms,
        showTerms,
        setShowTerms,
        doLogin,
        doRegister,
        doLogout,
        api,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

