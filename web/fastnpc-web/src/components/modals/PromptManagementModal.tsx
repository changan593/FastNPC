import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { PromptVersionSwitcher } from '../PromptVersionSwitcher'
import type { TestCase, TestConfig, TestExecutionResult, ParsedEvaluationResult } from '../../types'
import './PromptManagementModal.css'

interface Prompt {
  id: number
  category: string
  sub_category?: string
  name: string
  description?: string
  template_content: string
  version: string
  is_active: number
  created_at: number
  updated_at: number
  metadata?: any
}

interface PromptManagementModalProps {
  show: boolean
  onClose: () => void
}

const PROMPT_CATEGORIES = {
  'STRUCTURED_GENERATION': {
    name: '结构化生成',
    subCategories: [
      '基础身份信息',
      '个性与行为设定',
      '背景故事',
      '知识与能力',
      '对话与交互规范',
      '任务/功能性信息',
      '环境与世界观',
      '系统与控制参数',
      '来源'
    ]
  },
  'BRIEF_GENERATION': { name: '简介生成', subCategories: [] },
  'SINGLE_CHAT_SYSTEM': { name: '单聊系统提示', subCategories: [] },
  'SINGLE_CHAT_STM_COMPRESSION': { name: '短期记忆凝练（单聊）', subCategories: [] },
  'GROUP_CHAT_STM_COMPRESSION': { name: '短期记忆凝练（群聊）', subCategories: [] },
  'LTM_INTEGRATION': { name: '长期记忆整合', subCategories: [] },
  'GROUP_MODERATOR': { name: '群聊中控', subCategories: [] },
  'GROUP_CHAT_CHARACTER': { name: '群聊角色发言', subCategories: [] },
  'STRUCTURED_SYSTEM_MESSAGE': { name: '结构化系统消息', subCategories: [] }
}

// 评估提示词分类定义（分级结构）
const EVALUATION_CATEGORIES: Record<string, { name: string; subCategories: string[] }> = {
  'STRUCTURED_GEN_EVALUATORS': { 
    name: '结构化生成评估器', 
    subCategories: [
      'EVALUATOR_BASIC_INFO',
      'EVALUATOR_PERSONALITY', 
      'EVALUATOR_BACKGROUND',
      'EVALUATOR_APPEARANCE',
      'EVALUATOR_BEHAVIOR',
      'EVALUATOR_RELATIONSHIPS',
      'EVALUATOR_SKILLS',
      'EVALUATOR_VALUES',
      'EVALUATOR_EMOTIONS'
    ] 
  },
  'OTHER_EVALUATORS': { 
    name: '其他评估器', 
    subCategories: [
      'EVALUATOR_BRIEF_GEN',
      'EVALUATOR_SINGLE_CHAT',
      'EVALUATOR_GROUP_CHAT',
      'EVALUATOR_STM_COMPRESSION',
      'EVALUATOR_LTM_INTEGRATION',
      'EVALUATOR_GROUP_MODERATOR'
    ] 
  }
}

// 评估器子类别名称映射
const EVALUATOR_SUBCATEGORY_NAMES: Record<string, string> = {
  'EVALUATOR_BASIC_INFO': '基础身份信息评估器',
  'EVALUATOR_PERSONALITY': '性格特征评估器',
  'EVALUATOR_BACKGROUND': '背景经历评估器',
  'EVALUATOR_APPEARANCE': '外貌特征评估器',
  'EVALUATOR_BEHAVIOR': '行为习惯评估器',
  'EVALUATOR_RELATIONSHIPS': '人际关系评估器',
  'EVALUATOR_SKILLS': '技能特长评估器',
  'EVALUATOR_VALUES': '价值观信念评估器',
  'EVALUATOR_EMOTIONS': '情感倾向评估器',
  'EVALUATOR_BRIEF_GEN': '简介生成评估器',
  'EVALUATOR_SINGLE_CHAT': '单聊对话评估器',
  'EVALUATOR_GROUP_CHAT': '群聊对话评估器',
  'EVALUATOR_STM_COMPRESSION': '短期记忆凝练评估器',
  'EVALUATOR_LTM_INTEGRATION': '长期记忆整合评估器',
  'EVALUATOR_GROUP_MODERATOR': '群聊中控评估器'
}

// 测试分类定义
const TEST_CATEGORIES = [
  { id: 'SINGLE_CHAT', name: '单聊测试', icon: '💬' },
  { id: 'GROUP_CHAT', name: '群聊测试', icon: '👥' },
  { id: 'STRUCTURED_GEN', name: '结构化生成', icon: '📋' },
  { id: 'BRIEF_GEN', name: '简介生成', icon: '📝' },
  { id: 'STM_COMPRESSION', name: '短期记忆', icon: '🧠' },
  { id: 'LTM_INTEGRATION', name: '长期记忆', icon: '💾' },
  { id: 'GROUP_MODERATOR', name: '群聊中控', icon: '🎯' }
]

export function PromptManagementModal({ show, onClose }: PromptManagementModalProps) {
  const { api } = useAuth()
  
  // 标签页状态
  const [activeTab, setActiveTab] = useState<'prompts' | 'testcases' | 'evaluation' | 'execution'>('prompts')
  
  // 提示词相关状态
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [promptTestCases, setPromptTestCases] = useState<TestCase[]>([])
  const [, setLoading] = useState(false)
  
  // 选择状态
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedSubCategory, setSelectedSubCategory] = useState<string>('')
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null)
  
  // 编辑状态
  const [editedContent, setEditedContent] = useState('')
  const [editedDescription, setEditedDescription] = useState('')
  
  // 版本切换状态
  const [showVersionSwitcher, setShowVersionSwitcher] = useState(false)
  
  // 测试用例相关状态
  const [testCategory, setTestCategory] = useState<string>('SINGLE_CHAT')
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null)
  const [selectedTarget, setSelectedTarget] = useState<{type: string, id: string, name: string} | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  
  // 测试用例编辑/创建状态
  const [isEditing, setIsEditing] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [editFormData, setEditFormData] = useState({
    name: '',
    description: '',
    version: '1.0.0',
    category: 'SINGLE_CHAT',
    prompt_category: '',
    prompt_sub_category: '',
    target_type: 'character',
    target_id: '',
    test_content: '',
    expected_behavior: ''
  })
  
  // 测试配置编辑状态
  const [editingConfig, setEditingConfig] = useState(false)
  const [configCtxMaxChat, setConfigCtxMaxChat] = useState('')
  const [configCtxMaxStm, setConfigCtxMaxStm] = useState('')
  const [configCtxMaxLtm, setConfigCtxMaxLtm] = useState('')
  const [configMaxGroupRounds, setConfigMaxGroupRounds] = useState('')
  const [configTemperature, setConfigTemperature] = useState('')
  const [configMaxTokens, setConfigMaxTokens] = useState('')
  const [configModel, setConfigModel] = useState('')

  // 测试执行标签页状态
  const [executionMode, setExecutionMode] = useState<'single' | 'batch' | 'category'>('single')
  const [testConfigs, setTestConfigs] = useState<TestConfig[]>([])
  const [selectedTestCases, setSelectedTestCases] = useState<number[]>([])
  const [availableTestCases, setAvailableTestCases] = useState<TestCase[]>([])
  const [selectedCategoryForExecution, setSelectedCategoryForExecution] = useState<string>('SINGLE_CHAT')
  const [executionResults, setExecutionResults] = useState<TestExecutionResult[]>([])
  const [isExecuting, setIsExecuting] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)
  const [resultDisplayModes, setResultDisplayModes] = useState<Record<number, 'raw' | 'structured'>>({}) // 存储每个结果的显示模式

  useEffect(() => {
    if (show) {
      loadPrompts()
      loadPromptTestCases()
      
      // 如果是测试用例标签页，加载测试用例
      if (activeTab === 'testcases') {
        loadTestCases(testCategory)
      }
      
      // 如果是执行标签页，加载可用的测试用例
      if (activeTab === 'execution') {
        loadAvailableTestCases()
      }
    }
  }, [show, activeTab, testCategory, selectedCategoryForExecution])
  
  // 加载测试配置
  useEffect(() => {
    if (selectedTestCase) {
      loadTestConfig(selectedTestCase)
    }
  }, [selectedTestCase])
  
  // 加载测试配置到编辑状态
  function loadTestConfig(testCase: TestCase) {
    const config = testCase.test_config || {}
    setConfigCtxMaxChat(config.ctx_max_chat?.toString() || '')
    setConfigCtxMaxStm(config.ctx_max_stm?.toString() || '')
    setConfigCtxMaxLtm(config.ctx_max_ltm?.toString() || '')
    setConfigMaxGroupRounds(config.max_group_reply_rounds?.toString() || '')
    setConfigTemperature(config.temperature?.toString() || '')
    setConfigMaxTokens(config.max_tokens?.toString() || '')
    setConfigModel(config.model || '')
    setEditingConfig(false)
  }

  useEffect(() => {
    if (selectedPrompt) {
      setEditedContent(selectedPrompt.template_content)
      setEditedDescription(selectedPrompt.description || '')
    }
  }, [selectedPrompt])

  async function loadPrompts() {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/prompts?include_inactive=true')
      setPrompts(data.items || [])
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载提示词失败')
    } finally {
      setLoading(false)
    }
  }

  async function loadPromptTestCases() {
    try {
      const { data } = await api.get('/admin/prompts/test-cases')
      setPromptTestCases(data.items || [])
    } catch (e: any) {
      console.error('加载提示词测试用例失败:', e)
    }
  }
  
  // 加载测试用例（按分类）
  async function loadTestCases(category: string) {
    setTestLoading(true)
    try {
      const response = await fetch(`/admin/test-cases?category=${category}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setTestCases(data.items || [])
        // 自动选中第一个测试用例
        if (data.items && data.items.length > 0) {
          setSelectedTestCase(data.items[0])
        } else {
          setSelectedTestCase(null)
        }
      } else {
        console.error('加载测试用例失败:', await response.text())
        setTestCases([])
        setSelectedTestCase(null)
      }
    } catch (error) {
      console.error('加载测试用例失败:', error)
      setTestCases([])
      setSelectedTestCase(null)
    } finally {
      setTestLoading(false)
    }
  }
  

  function selectPrompt(category: string, subCategory?: string) {
    setSelectedCategory(category)
    setSelectedSubCategory(subCategory || '')
    
    // 查找对应的激活提示词
    const prompt = prompts.find(p => 
      p.category === category && 
      (subCategory ? p.sub_category === subCategory : !p.sub_category) &&
      p.is_active === 1
    )
    
    setSelectedPrompt(prompt || null)
  }

  async function handleSave() {
    if (!selectedPrompt) return
    
    if (!confirm('确定保存修改吗？这将创建一个新版本。')) return
    
    try {
      // 更新提示词
      await api.put(`/admin/prompts/${selectedPrompt.id}`, {
        template_content: editedContent,
        description: editedDescription,
        create_history: true
      })
      
      alert('保存成功')
      await loadPrompts()
    } catch (e: any) {
      alert(e?.response?.data?.error || '保存失败')
    }
  }

  async function handleActivate() {
    if (!selectedPrompt) return
    
    if (!confirm('确定激活此版本吗？')) return
    
    try {
      await api.post(`/admin/prompts/${selectedPrompt.id}/activate`)
      alert('激活成功')
      await loadPrompts()
    } catch (e: any) {
      alert(e?.response?.data?.error || '激活失败')
    }
  }

  async function handleDuplicate() {
    if (!selectedPrompt) return
    
    const newVersion = prompt('请输入新版本号:', '2.0.0')
    if (!newVersion) return
    
    try {
      const { data } = await api.post(`/admin/prompts/${selectedPrompt.id}/duplicate`, {
        new_version: newVersion
      })
      
      alert(`已复制为新版本 (ID: ${data.new_prompt_id})`)
      await loadPrompts()
    } catch (e: any) {
      alert(e?.response?.data?.error || '复制失败')
    }
  }

  async function loadPromptVersion(versionId: number) {
    try {
      const { data } = await api.get(`/admin/prompts/${versionId}`)
      setSelectedPrompt(data)
      setEditedContent(data.template_content)
      setEditedDescription(data.description || '')
      await loadPrompts() // 刷新列表以更新激活状态
    } catch (e: any) {
      alert(e?.response?.data?.error || '加载版本失败')
    }
  }
  
  // 执行测试用例
  async function handleExecuteTest() {
    if (!selectedTestCase) return
    
    setExecuting(true)
    try {
      const response = await fetch(`/admin/test-cases/${selectedTestCase.id}/execute`, {
        method: 'POST',
        credentials: 'include'
      })
      if (response.ok) {
        const result = await response.json()
        alert(`测试执行完成！\n通过: ${result.passed ? '是' : '否'}\n评分: ${result.score || 'N/A'}`)
      } else {
        const error = await response.text()
        alert(`测试执行失败: ${error}`)
      }
    } catch (error) {
      console.error('测试执行失败:', error)
      alert(`测试执行失败: ${error}`)
    } finally {
      setExecuting(false)
    }
  }
  
  // 重置测试状态
  async function handleResetState() {
    if (!selectedTestCase) return
    
    const confirmMsg = `确定要重置 "${selectedTestCase.name}" 的状态吗？\n这将清空所有对话历史和记忆。`
    if (!confirm(confirmMsg)) return
    
    try {
      const targetType = selectedTestCase.target_type.toLowerCase()
      const targetId = selectedTestCase.target_id
      const endpoint = targetType === 'character' 
        ? `/admin/test-cases/reset-character/${targetId}`
        : `/admin/test-cases/reset-group/${targetId}`
      
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'include'
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`状态重置成功！\n清理项: ${result.reset_count || 0}`)
      } else {
        const error = await response.text()
        alert(`状态重置失败: ${error}`)
      }
    } catch (error) {
      console.error('状态重置失败:', error)
      alert(`状态重置失败: ${error}`)
    }
  }
  
  // 保存测试配置
  async function handleSaveConfig() {
    if (!selectedTestCase) return
    
    try {
      const newConfig: any = {}
      
      // 只保存已填写的配置项
      if (configCtxMaxChat) newConfig.ctx_max_chat = Number(configCtxMaxChat)
      if (configCtxMaxStm) newConfig.ctx_max_stm = Number(configCtxMaxStm)
      if (configCtxMaxLtm) newConfig.ctx_max_ltm = Number(configCtxMaxLtm)
      if (configMaxGroupRounds) newConfig.max_group_reply_rounds = Number(configMaxGroupRounds)
      if (configTemperature) newConfig.temperature = Number(configTemperature)
      if (configMaxTokens) newConfig.max_tokens = Number(configMaxTokens)
      if (configModel) newConfig.model = configModel
      
      const response = await fetch(`/admin/test-cases/${selectedTestCase.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          test_config: newConfig
        })
      })
      
      if (response.ok) {
        alert('测试配置已保存！')
        setEditingConfig(false)
        // 重新加载测试用例以获取最新数据
        await loadTestCases(testCategory)
        // 更新选中的测试用例
        const updatedCase = testCases.find(tc => tc.id === selectedTestCase.id)
        if (updatedCase) {
          setSelectedTestCase(updatedCase)
        }
      } else {
        const error = await response.text()
        alert(`保存配置失败: ${error}`)
      }
    } catch (error) {
      console.error('保存配置失败:', error)
      alert(`保存配置失败: ${error}`)
    }
  }
  
  // 取消编辑测试配置
  function handleCancelConfigEdit() {
    if (selectedTestCase) {
      loadTestConfig(selectedTestCase)
    }
    setEditingConfig(false)
  }
  
  // ===== 测试用例CRUD操作 =====
  
  // 开始创建新测试用例
  function handleStartCreate() {
    setIsCreating(true)
    setIsEditing(false)
    setEditFormData({
      name: '',
      description: '',
      version: '1.0.0',
      category: testCategory,
      prompt_category: '',
      prompt_sub_category: '',
      target_type: selectedTarget?.type || 'character',
      target_id: selectedTarget?.id || '',
      test_content: '',
      expected_behavior: ''
    })
  }
  
  // 开始编辑测试用例
  function handleStartEdit() {
    if (!selectedTestCase) return
    
    setIsEditing(true)
    setIsCreating(false)
    setEditFormData({
      name: selectedTestCase.name,
      description: selectedTestCase.description || '',
      version: selectedTestCase.version,
      category: selectedTestCase.category,
      prompt_category: selectedTestCase.prompt_category || '',
      prompt_sub_category: selectedTestCase.prompt_sub_category || '',
      target_type: selectedTestCase.target_type,
      target_id: selectedTestCase.target_id,
      test_content: typeof selectedTestCase.test_content === 'string' 
        ? selectedTestCase.test_content 
        : JSON.stringify(selectedTestCase.test_content, null, 2),
      expected_behavior: selectedTestCase.expected_behavior || ''
    })
  }
  
  // 保存测试用例（创建或更新）
  async function handleSaveTestCase() {
    try {
      // 验证必填字段
      if (!editFormData.name.trim()) {
        alert('请输入测试用例名称')
        return
      }
      if (!editFormData.target_id.trim()) {
        alert('请输入目标ID')
        return
      }
      if (!editFormData.test_content.trim()) {
        alert('请输入测试内容')
        return
      }
      
      // 解析测试内容为JSON
      let parsedTestContent
      try {
        parsedTestContent = JSON.parse(editFormData.test_content)
      } catch {
        parsedTestContent = { messages: [editFormData.test_content] }
      }
      
      const payload = {
        name: editFormData.name.trim(),
        description: editFormData.description.trim(),
        version: editFormData.version,
        category: editFormData.category,
        prompt_category: editFormData.prompt_category || undefined,
        prompt_sub_category: editFormData.prompt_sub_category || undefined,
        target_type: editFormData.target_type,
        target_id: editFormData.target_id.trim(),
        test_content: parsedTestContent,
        expected_behavior: editFormData.expected_behavior.trim() || undefined
      }
      
      let response
      if (isCreating) {
        // 创建新测试用例
        response = await fetch('/admin/test-cases', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        })
      } else if (isEditing && selectedTestCase) {
        // 更新现有测试用例
        response = await fetch(`/admin/test-cases/${selectedTestCase.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        })
      }
      
      if (response && response.ok) {
        const result = await response.json()
        alert(isCreating ? '测试用例已创建！' : '测试用例已更新！')
        
        // 重新加载测试用例列表
        await loadTestCases(testCategory)
        
        // 如果是创建，选择新创建的测试用例
        if (isCreating && result.test_case_id) {
          const newCase = testCases.find(tc => tc.id === result.test_case_id)
          if (newCase) {
            setSelectedTestCase(newCase)
          }
        }
        
        // 关闭编辑模式
        setIsCreating(false)
        setIsEditing(false)
      } else {
        const error = response ? await response.text() : '未知错误'
        alert(`保存失败: ${error}`)
      }
    } catch (error) {
      console.error('保存测试用例失败:', error)
      alert(`保存失败: ${error}`)
    }
  }
  
  // 取消编辑/创建
  function handleCancelEdit() {
    setIsCreating(false)
    setIsEditing(false)
  }
  
  // 删除测试用例
  async function handleDeleteTestCase() {
    if (!selectedTestCase) return
    
    const confirmMsg = `确定要删除测试用例 "${selectedTestCase.name}" 吗？\n此操作不可恢复！`
    if (!confirm(confirmMsg)) return
    
    try {
      const response = await fetch(`/admin/test-cases/${selectedTestCase.id}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      
      if (response.ok) {
        alert('测试用例已删除！')
        
        // 清除选中状态
        setSelectedTestCase(null)
        
        // 重新加载测试用例列表
        await loadTestCases(testCategory)
      } else {
        const error = await response.text()
        alert(`删除失败: ${error}`)
      }
    } catch (error) {
      console.error('删除测试用例失败:', error)
      alert(`删除失败: ${error}`)
    }
  }
  
  // 格式化工具函数
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('zh-CN')
  }
  
  const formatDuration = (ms?: number) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }
  
  // 获取去重的target列表
  const getUniqueTargets = () => {
    const targetMap = new Map<string, {type: string, id: string, name: string}>()
    
    testCases.forEach(tc => {
      const key = `${tc.target_type}-${tc.target_id}`
      if (!targetMap.has(key)) {
        // 从测试用例名称中提取角色/群聊名称
        const name = tc.name.split('-')[0] || tc.name
        targetMap.set(key, {
          type: tc.target_type,
          id: tc.target_id,
          name: name
        })
      }
    })
    
    return Array.from(targetMap.values())
  }
  
  // 选择target
  const selectTarget = (target: {type: string, id: string, name: string}) => {
    setSelectedTarget(target)
    
    // 自动选中该target的第一个测试用例
    const firstTestCase = testCases.find(
      tc => tc.target_type === target.type && tc.target_id === target.id
    )
    if (firstTestCase) {
      setSelectedTestCase(firstTestCase)
    }
  }

  // ========== 测试执行标签页相关函数 ==========
  
  // 加载可用的测试用例
  async function loadAvailableTestCases() {
    try {
      let url = '/admin/test-cases?include_inactive=false'
      if (executionMode === 'category') {
        url += `&category=${selectedCategoryForExecution}`
      }
      
      const response = await fetch(url, { credentials: 'include' })
      if (response.ok) {
        const data = await response.json()
        setAvailableTestCases(data.items || [])
      }
    } catch (error) {
      console.error('加载测试用例失败:', error)
    }
  }
  
  // 添加测试用例到配置表格
  function addTestCaseToConfig(testCase: TestCase) {
    // 检查是否已存在
    if (testConfigs.some(c => c.testCaseId === testCase.id)) {
      alert('该测试用例已添加')
      return
    }
    
    const newConfig: TestConfig = {
      id: `config-${Date.now()}-${Math.random()}`,
      testCaseId: testCase.id,
      testCaseName: testCase.name,
      testCaseCategory: testCase.category,
      promptCategory: testCase.prompt_category || '',
      promptSubCategory: testCase.prompt_sub_category,
      selectedPromptVersion: undefined,
      selectedEvaluatorVersion: undefined,
      status: 'pending'
    }
    
    setTestConfigs([...testConfigs, newConfig])
  }
  
  // 移除测试配置
  function removeTestConfig(configId: string) {
    setTestConfigs(testConfigs.filter(c => c.id !== configId))
  }
  
  // 更新测试配置的提示词版本
  function updateConfigPromptVersion(configId: string, promptId: number) {
    setTestConfigs(testConfigs.map(c => 
      c.id === configId ? { ...c, selectedPromptVersion: promptId } : c
    ))
  }
  
  // 更新测试配置的评估器版本
  function updateConfigEvaluatorVersion(configId: string, evaluatorId: number) {
    setTestConfigs(testConfigs.map(c => 
      c.id === configId ? { ...c, selectedEvaluatorVersion: evaluatorId } : c
    ))
  }
  
  // 获取某个配置可选的提示词版本
  function getAvailablePromptVersions(config: TestConfig) {
    return prompts.filter(p => 
      p.category === config.promptCategory && 
      (!config.promptSubCategory || p.sub_category === config.promptSubCategory)
    )
  }
  
  // 获取某个配置可选的评估器版本
  function getAvailableEvaluatorVersions(config: TestConfig) {
    // 根据提示词类别映射到评估器类别
    let evaluatorCategory = ''
    
    // 结构化生成需要根据子类别细化
    if (config.promptCategory === 'STRUCTURED_GEN' && config.promptSubCategory) {
      const structuredEvaluatorMap: Record<string, string> = {
        '基础身份信息': 'EVALUATOR_BASIC_INFO',
        '性格特征': 'EVALUATOR_PERSONALITY',
        '背景经历': 'EVALUATOR_BACKGROUND',
        '外貌特征': 'EVALUATOR_APPEARANCE',
        '行为习惯': 'EVALUATOR_BEHAVIOR',
        '人际关系': 'EVALUATOR_RELATIONSHIPS',
        '技能特长': 'EVALUATOR_SKILLS',
        '价值观信念': 'EVALUATOR_VALUES',
        '情感倾向': 'EVALUATOR_EMOTIONS'
      }
      evaluatorCategory = structuredEvaluatorMap[config.promptSubCategory] || ''
    } else {
      // 其他类别的映射
      const evaluatorCategoryMap: Record<string, string> = {
        'SINGLE_CHAT_SYSTEM': 'EVALUATOR_SINGLE_CHAT',
        'GROUP_CHAT_CHARACTER': 'EVALUATOR_GROUP_CHAT',
        'BRIEF_GEN': 'EVALUATOR_BRIEF_GEN',
        'SINGLE_CHAT_STM_COMPRESSION': 'EVALUATOR_STM_COMPRESSION',
        'GROUP_CHAT_STM_COMPRESSION': 'EVALUATOR_STM_COMPRESSION',
        'LTM_INTEGRATION': 'EVALUATOR_LTM_INTEGRATION',
        'GROUP_MODERATOR': 'EVALUATOR_GROUP_MODERATOR'
      }
      evaluatorCategory = evaluatorCategoryMap[config.promptCategory] || ''
    }
    
    if (!evaluatorCategory) return []
    
    return prompts.filter(p => p.category === evaluatorCategory)
  }
  
  // 运行测试
  async function handleRunTests() {
    // 验证所有配置都已选择版本
    for (const config of testConfigs) {
      if (!config.selectedPromptVersion) {
        alert(`请为测试用例"${config.testCaseName}"选择提示词版本`)
        return
      }
      if (!config.selectedEvaluatorVersion) {
        alert(`请为测试用例"${config.testCaseName}"选择评估器版本`)
        return
      }
    }
    
    if (testConfigs.length === 0) {
      alert('请先添加测试用例')
      return
    }
    
    setIsExecuting(true)
    setExecutionResults([])
    
    // 更新所有配置状态为running
    setTestConfigs(testConfigs.map(c => ({ ...c, status: 'running' })))
    
    try {
      // 构建批量执行请求
      const executions = testConfigs.map(config => ({
        test_case_id: config.testCaseId,
        prompt_template_id: config.selectedPromptVersion!,
        evaluator_prompt_id: config.selectedEvaluatorVersion!
      }))
      
      const response = await fetch('/admin/test-cases/batch-execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ executions })
      })
      
      if (!response.ok) {
        throw new Error('执行失败')
      }
      
      const data = await response.json()
      
      // 处理结果
      const results: TestExecutionResult[] = data.results.map((r: any) => ({
        ...r,
        testCaseName: testConfigs.find(c => c.testCaseId === r.test_case_id)?.testCaseName
      }))
      
      setExecutionResults(results)
      
      // 更新配置状态
      setTestConfigs(testConfigs.map(config => {
        const result = results.find(r => r.test_case_id === config.testCaseId)
        return {
          ...config,
          status: result?.success ? 'completed' : 'error'
        }
      }))
      
    } catch (error) {
      console.error('执行测试失败:', error)
      alert('执行测试失败: ' + (error instanceof Error ? error.message : String(error)))
      setTestConfigs(testConfigs.map(c => ({ ...c, status: 'error' })))
    } finally {
      setIsExecuting(false)
    }
  }
  
  // 恢复测试环境
  async function handleRestoreTestEnvironment() {
    if (testConfigs.length === 0) {
      alert('没有需要恢复的测试环境')
      return
    }
    
    if (!confirm('确定要清除所有相关角色和群聊的记忆和消息吗？此操作不可恢复。')) {
      return
    }
    
    setIsRestoring(true)
    
    try {
      // 收集所有需要恢复的target
      const targets = new Map<string, Set<number>>()
      
      for (const config of testConfigs) {
        const response = await fetch(`/admin/test-cases/${config.testCaseId}`, {
          credentials: 'include'
        })
        if (response.ok) {
          const testCase = await response.json()
          const targetType = testCase.target_type
          const targetId = parseInt(testCase.target_id)
          
          if (!targets.has(targetType)) {
            targets.set(targetType, new Set())
          }
          targets.get(targetType)!.add(targetId)
        }
      }
      
      // 批量恢复
      let successCount = 0
      let failCount = 0
      
      for (const [type, ids] of targets) {
        for (const id of ids) {
          try {
            let url = ''
            if (type === 'character') {
              url = `/admin/test-cases/reset-character/${id}`
            } else if (type === 'group') {
              url = `/admin/test-cases/reset-group/${id}`
            } else {
              continue
            }
            
            const response = await fetch(url, {
              method: 'POST',
              credentials: 'include'
            })
            
            if (response.ok) {
              successCount++
            } else {
              failCount++
            }
          } catch (error) {
            failCount++
          }
        }
      }
      
      alert(`恢复完成！成功: ${successCount}, 失败: ${failCount}`)
      
    } catch (error) {
      console.error('恢复测试环境失败:', error)
      alert('恢复测试环境失败: ' + (error instanceof Error ? error.message : String(error)))
    } finally {
      setIsRestoring(false)
    }
  }
  
  // 解析评估结果
  function parseEvaluationResult(result: any): ParsedEvaluationResult {
    if (!result) return { raw: '无评估结果' }
    
    try {
      // 尝试提取常见字段（支持中英文）
      return {
        score: result.score || result.总分 || result.评分 || undefined,
        strengths: result.strengths || result.优点 || result.亮点 || [],
        weaknesses: result.weaknesses || result.缺点 || result.不足 || [],
        suggestions: result.suggestions || result.建议 || result.改进建议 || [],
        details: result.details || result.详细评分 || result.详情 || {},
        raw: JSON.stringify(result, null, 2)
      }
    } catch (error) {
      return { raw: String(result) }
    }
  }

  if (!show) return null

  return (
    <div className="modal prompt-management-modal">
      <div className="dialog" style={{ width: '95vw', height: '90vh', maxWidth: 'none' }}>
        <div className="prompt-management-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <h2>🎯 提示词与测试管理</h2>
            <div className="tab-buttons">
              <button 
                className={`tab-btn ${activeTab === 'prompts' ? 'active' : ''}`}
                onClick={() => setActiveTab('prompts')}
              >
                🎯 功能提示词
              </button>
              <button 
                className={`tab-btn ${activeTab === 'testcases' ? 'active' : ''}`}
                onClick={() => setActiveTab('testcases')}
              >
                🧪 测试用例
              </button>
              <button 
                className={`tab-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
                onClick={() => setActiveTab('evaluation')}
              >
                ⭐ 评估提示词
              </button>
              <button 
                className={`tab-btn ${activeTab === 'execution' ? 'active' : ''}`}
                onClick={() => setActiveTab('execution')}
              >
                ▶️ 测试执行
              </button>
            </div>
          </div>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="prompt-management-body">{activeTab === 'prompts' ? (
          // ========== 提示词管理界面 ==========
          <>
          {/* 左侧：分类树 */}
          <div className="category-sidebar">
            <h3>提示词分类</h3>
            <div className="category-tree">
              {Object.entries(PROMPT_CATEGORIES).map(([key, config]) => (
                <div key={key} className="category-group">
                  <div className="category-parent">{config.name}</div>
                  {config.subCategories.length > 0 ? (
                    <div className="category-children">
                      {config.subCategories.map(sub => {
                        const isActive = selectedCategory === key && selectedSubCategory === sub
                        return (
                          <div
                            key={sub}
                            className={`category-child ${isActive ? 'active' : ''}`}
                            onClick={() => selectPrompt(key, sub)}
                          >
                            {sub}
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div
                      className={`category-child ${selectedCategory === key ? 'active' : ''}`}
                      onClick={() => selectPrompt(key)}
                      style={{ marginLeft: 0 }}
                    >
                      点击查看
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 中间：编辑器 */}
          <div className="editor-area">
            {selectedPrompt ? (
              <>
                <div className="editor-header">
                  <div>
                    <h3>{selectedPrompt.name}</h3>
                    <span className="version-badge">
                      v{selectedPrompt.version}
                      {selectedPrompt.is_active === 1 && <span className="active-tag"> (激活)</span>}
                    </span>
                  </div>
                  <div className="editor-actions">
                    <button 
                      onClick={() => setShowVersionSwitcher(true)} 
                      className="btn-secondary"
                      title="查看和切换版本"
                    >
                      🔄 切换版本
                    </button>
                    <button onClick={handleSave} className="btn-primary">
                      💾 保存
                    </button>
                    {selectedPrompt.is_active !== 1 && (
                      <button onClick={handleActivate} className="btn-success">
                        ✓ 激活此版本
                      </button>
                    )}
                    <button onClick={handleDuplicate}>
                      📋 复制为新版本
                    </button>
                  </div>
                </div>

                <div className="editor-fields">
                  <label>
                    描述
                    <input
                      type="text"
                      value={editedDescription}
                      onChange={(e) => setEditedDescription(e.target.value)}
                      placeholder="提示词描述..."
                    />
                  </label>

                  <label>
                    提示词内容
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      rows={20}
                      placeholder="输入提示词内容，支持 {变量} 占位符..."
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                    />
                  </label>

                  {selectedPrompt.metadata?.variables && (
                    <div className="variables-info">
                      <strong>可用变量：</strong>
                      {selectedPrompt.metadata.variables.map((v: string) => (
                        <code key={v}>{`{${v}}`}</code>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>👈 请从左侧选择一个提示词分类</p>
              </div>
            )}
          </div>

          {/* 右侧：提示词信息 */}
          <div className="test-panel">
            <h3>提示词信息</h3>
            
            {selectedPrompt ? (
              <>
                <div className="prompt-info">
                  <div className="info-section">
                    <h4>📋 基本信息</h4>
                    <div className="info-item">
                      <strong>类别：</strong>
                      <span>{selectedPrompt.category}</span>
                    </div>
                    {selectedPrompt.sub_category && (
                      <div className="info-item">
                        <strong>子类别：</strong>
                        <span>{selectedPrompt.sub_category}</span>
                      </div>
                    )}
                    <div className="info-item">
                      <strong>版本：</strong>
                      <span>v{selectedPrompt.version}</span>
                    </div>
                    <div className="info-item">
                      <strong>状态：</strong>
                      <span className={selectedPrompt.is_active === 1 ? 'status-active' : 'status-inactive'}>
                        {selectedPrompt.is_active === 1 ? '✓ 已激活' : '○ 未激活'}
                      </span>
                    </div>
                    <div className="info-item">
                      <strong>创建时间：</strong>
                      <span>{new Date(selectedPrompt.created_at * 1000).toLocaleString('zh-CN')}</span>
                    </div>
                </div>

                  <div className="info-section">
                    <h4>🔧 使用说明</h4>
                    <p style={{ fontSize: '13px', lineHeight: '1.6', color: '#6b7280' }}>
                      {selectedPrompt.is_active === 1 
                        ? '此版本当前处于激活状态，系统将使用此提示词。' 
                        : '此版本未激活，可以点击"激活此版本"按钮来启用。'
                      }
                    </p>
                    <p style={{ fontSize: '13px', lineHeight: '1.6', color: '#6b7280' }}>
                      • 点击"保存"创建新版本<br/>
                      • 点击"复制为新版本"创建副本<br/>
                      • 点击"切换版本"查看历史版本
                    </p>
                          </div>

                  {/* 相关测试用例 */}
                  <div className="info-section">
                    <h4>🧪 相关测试用例</h4>
                    {promptTestCases.filter(tc => 
                      tc.prompt_category === selectedPrompt.category &&
                      (!tc.prompt_sub_category || tc.prompt_sub_category === selectedPrompt.sub_category)
                    ).length > 0 ? (
                      <div className="related-test-cases">
                        {promptTestCases
                          .filter(tc => 
                            tc.prompt_category === selectedPrompt.category &&
                            (!tc.prompt_sub_category || tc.prompt_sub_category === selectedPrompt.sub_category)
                          )
                          .map(tc => (
                            <div key={tc.id} className="test-case-item">
                              <strong>{tc.name}</strong>
                              {tc.description && <p>{tc.description}</p>}
                            </div>
                          ))
                        }
                        <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '12px' }}>
                          💡 前往"测试执行"标签页运行这些测试
                        </p>
                      </div>
                    ) : (
                      <p style={{ fontSize: '13px', color: '#9ca3af' }}>
                        暂无相关测试用例
                      </p>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>选择提示词后查看详情</p>
              </div>
            )}
          </div>
          </>
        ) : activeTab === 'evaluation' ? (
          // ========== 评估提示词管理界面 ==========
          <>
          {/* 左侧：评估器分类 */}
          <div className="category-sidebar">
            <h3>评估器分类</h3>
            <div className="category-tree">
              {Object.entries(EVALUATION_CATEGORIES).map(([parentKey, parentConfig]) => (
                <div key={parentKey}>
                  {/* 父类别 */}
                  <div className="category-parent">
                    {parentConfig.name}
                  </div>
                  
                  {/* 子类别 */}
                  {parentConfig.subCategories.map(childKey => (
                    <div
                      key={childKey}
                      className={`category-child ${selectedCategory === childKey ? 'active' : ''}`}
                      onClick={() => selectPrompt(childKey)}
                    >
                      {EVALUATOR_SUBCATEGORY_NAMES[childKey]}
                          </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
          
          {/* 中间：评估器内容编辑 */}
          <div className="editor-area">
            {selectedPrompt ? (
              <>
                <div className="editor-header">
                  <div>
                    <h3>{selectedPrompt.name}</h3>
                    <div className="version-badge">
                      <span>v{selectedPrompt.version}</span>
                      {selectedPrompt.is_active === 1 && <span className="active-tag">● Active</span>}
                          </div>
                  </div>
                  <div className="editor-actions">
                    <button onClick={() => setShowVersionSwitcher(true)} className="btn-secondary">
                      📋 版本历史
                    </button>
                    <button onClick={handleSave} className="btn-primary">
                      💾 保存新版本
                    </button>
                    <button onClick={handleActivate} disabled={selectedPrompt.is_active === 1} className="btn-success">
                      ✓ 激活此版本
                    </button>
                    <button onClick={handleDuplicate} className="btn-secondary">
                      📑 复制
                    </button>
                  </div>
                </div>

                <div className="editor-fields">
                  <label>
                    描述
                    <input
                      type="text"
                      value={editedDescription}
                      onChange={(e) => setEditedDescription(e.target.value)}
                      placeholder="评估器描述..."
                    />
                  </label>

                  <label>
                    评估提示词内容
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      rows={20}
                      placeholder="输入评估提示词内容..."
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                    />
                  </label>

                  {selectedPrompt.metadata?.variables && selectedPrompt.metadata.variables.length > 0 && (
                    <div className="variables-info">
                      <strong>可用变量：</strong>
                      {selectedPrompt.metadata.variables.map((v: string) => (
                        <code key={v}>{`{${v}}`}</code>
                      ))}
                    </div>
                  )}

                  {selectedPrompt.metadata?.scoring_range && (
                    <div style={{ padding: '12px', background: '#e0f2fe', borderRadius: '8px', fontSize: '13px' }}>
                      <strong>评分范围：</strong> {selectedPrompt.metadata.scoring_range}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>👈 请从左侧选择一个评估器</p>
              </div>
            )}
          </div>

          {/* 右侧：评估器信息面板 */}
          <div className="test-panel">
            <h3>评估器信息</h3>
            
            {selectedPrompt ? (
              <>
                <div style={{ fontSize: '13px', lineHeight: 1.8 }}>
                  <div style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', color: '#374151' }}>
                      用途说明
                    </strong>
                    <p style={{ margin: 0, color: '#6b7280' }}>
                      {selectedPrompt.description || '暂无描述'}
                    </p>
                  </div>

                  <div style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', color: '#374151' }}>
                      版本信息
                    </strong>
                    <p style={{ margin: '4px 0', color: '#6b7280' }}>
                      当前版本: v{selectedPrompt.version}
                    </p>
                    <p style={{ margin: '4px 0', color: '#6b7280' }}>
                      状态: {selectedPrompt.is_active === 1 ? '✓ 已激活' : '未激活'}
                    </p>
                    <p style={{ margin: '4px 0', color: '#6b7280' }}>
                      更新时间: {new Date(selectedPrompt.updated_at * 1000).toLocaleString('zh-CN')}
                    </p>
                  </div>

                  <div style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', color: '#374151' }}>
                      输出格式
                    </strong>
                    <p style={{ margin: 0, color: '#6b7280' }}>
                      {selectedPrompt.metadata?.output_format === 'json' ? 'JSON 格式' : '文本格式'}
                    </p>
                  </div>

                  <div style={{ padding: '12px', background: '#fef3c7', borderRadius: '8px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px', fontSize: '12px' }}>
                      💡 使用提示
                    </strong>
                    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px', color: '#78350f' }}>
                      <li>评估器用于自动评价LLM输出质量</li>
                      <li>修改评估标准会影响测试结果</li>
                      <li>建议保持评分体系的一致性</li>
                      <li>可以通过版本管理对比不同评估策略</li>
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>选择评估器后查看详情</p>
              </div>
            )}
          </div>
          </>
        ) : activeTab === 'testcases' ? (
          // ========== 测试用例管理界面 ==========
          <>
          {/* 左侧：分类和测试用例列表 */}
          <div className="category-sidebar">
            {/* 测试分类 */}
            <div>
              <h3>测试分类</h3>
              <div className="category-tree">
                {TEST_CATEGORIES.map((category) => (
                  <div
                    key={category.id}
                    className={`category-child ${testCategory === category.id ? 'active' : ''}`}
                    onClick={() => setTestCategory(category.id)}
                    style={{ marginLeft: 0 }}
                  >
                    <span style={{ marginRight: '8px' }}>{category.icon}</span>
                    {category.name}
                  </div>
                ))}
              </div>
            </div>

            {/* 测试目标列表（角色/群聊） */}
            <div className="test-cases-section" style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #e5e7eb' }}>
              <h3>测试目标</h3>
              <div className="category-tree">
                {testLoading ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>加载中...</div>
                ) : testCases.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#999', fontSize: '13px' }}>
                    暂无测试用例
                  </div>
                ) : (
                  getUniqueTargets().map((target) => {
                    const isActive = selectedTarget?.type === target.type && selectedTarget?.id === target.id
                    const testCount = testCases.filter(tc => 
                      tc.target_type === target.type && tc.target_id === target.id
                    ).length
                      
                      return (
                      <div
                        key={`${target.type}-${target.id}`}
                        className={`category-child ${isActive ? 'active' : ''}`}
                        onClick={() => selectTarget(target)}
                        style={{ 
                          marginLeft: 0, 
                          display: 'flex', 
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{target.type === 'character' ? '👤' : '👥'}</span>
                          <span style={{ fontWeight: 500 }}>{target.name}</span>
                        </div>
                        <span style={{ 
                          fontSize: '11px', 
                          background: isActive ? 'rgba(255,255,255,0.3)' : '#e5e7eb',
                          color: isActive ? 'white' : '#6b7280',
                          padding: '2px 8px', 
                          borderRadius: '12px',
                          fontWeight: 600
                        }}>
                          {testCount}
                            </span>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
                          </div>
                          
          {/* 中间：测试用例详情/编辑 */}
          <div className="editor-area">
            {!selectedTestCase && !isCreating ? (
              <div className="empty-state">
                <p>👈 请从左侧选择一个测试目标</p>
                <p style={{ fontSize: '13px', color: '#9ca3af', marginTop: '8px' }}>
                  选择角色或群聊后，在右侧选择具体的测试用例
                </p>
                <button 
                  onClick={handleStartCreate}
                  className="btn-primary"
                  style={{ marginTop: '20px' }}
                >
                  ➕ 创建新测试用例
                </button>
              </div>
            ) : isEditing || isCreating ? (
              <>
                {/* 编辑/创建表单 */}
                <div className="editor-header">
                  <h3>{isCreating ? '➕ 创建测试用例' : '✏️ 编辑测试用例'}</h3>
                  <div className="editor-actions">
                    <button onClick={handleSaveTestCase} className="btn-primary">
                      💾 保存
                    </button>
                    <button onClick={handleCancelEdit} className="btn-secondary">
                      ✕ 取消
                    </button>
                  </div>
                </div>
                
                <div className="editor-fields" style={{ overflowY: 'auto' }}>
                  <label>
                    测试用例名称 *
                    <input
                      type="text"
                      value={editFormData.name}
                      onChange={(e) => setEditFormData({...editFormData, name: e.target.value})}
                      placeholder="例如：特朗普-政治话题测试"
                    />
                  </label>
                  
                  <label>
                    描述
                    <textarea
                      value={editFormData.description}
                      onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                      rows={3}
                      placeholder="测试用例的描述..."
                    />
                  </label>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <label>
                      版本
                      <input
                        type="text"
                        value={editFormData.version}
                        onChange={(e) => setEditFormData({...editFormData, version: e.target.value})}
                        placeholder="1.0.0"
                      />
                    </label>
                    
                    <label>
                      测试分类 *
                      <select
                        value={editFormData.category}
                        onChange={(e) => setEditFormData({...editFormData, category: e.target.value})}
                      >
                        {TEST_CATEGORIES.map(cat => (
                          <option key={cat.id} value={cat.id}>{cat.name}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <label>
                      目标类型 *
                      <select
                        value={editFormData.target_type}
                        onChange={(e) => setEditFormData({...editFormData, target_type: e.target.value})}
                      >
                        <option value="character">角色 (character)</option>
                        <option value="group">群聊 (group)</option>
                      </select>
                    </label>
                    
                    <label>
                      目标ID *
                      <input
                        type="text"
                        value={editFormData.target_id}
                        onChange={(e) => setEditFormData({...editFormData, target_id: e.target.value})}
                        placeholder="角色或群聊的ID"
                      />
                    </label>
                  </div>
                  
                  <label>
                    测试内容 * (JSON格式)
                    <textarea
                      value={editFormData.test_content}
                      onChange={(e) => setEditFormData({...editFormData, test_content: e.target.value})}
                      rows={8}
                      placeholder='{"messages": ["你好", "你觉得..."]}'
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                    />
                  </label>
                  
                  <label>
                    期望行为
                    <textarea
                      value={editFormData.expected_behavior}
                      onChange={(e) => setEditFormData({...editFormData, expected_behavior: e.target.value})}
                      rows={3}
                      placeholder="描述期望的输出或行为..."
                    />
                  </label>
                </div>
              </>
            ) : selectedTestCase ? (
              <>
                {/* 查看模式 */}
                <div className="editor-header">
                  <div>
                    <h3>{selectedTestCase.name}</h3>
                    <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                      版本 {selectedTestCase.version} · {selectedTestCase.target_type} · 
                      创建于 {formatTimestamp(selectedTestCase.created_at)}
                    </div>
                  </div>
                  <div className="editor-actions">
                    <button
                      className="btn-primary"
                      onClick={handleExecuteTest}
                      disabled={executing}
                    >
                      {executing ? '⏳ 执行中...' : '▶️ 执行测试'}
                    </button>
                    <button 
                      onClick={handleStartEdit}
                      className="btn-secondary"
                    >
                      ✏️ 编辑
                    </button>
                    <button 
                      onClick={handleDeleteTestCase}
                      style={{ background: '#ef4444', color: 'white' }}
                    >
                      🗑️ 删除
                    </button>
                    <button 
                      onClick={handleResetState}
                      style={{ background: '#f59e0b', color: 'white' }}
                    >
                      🔄 重置状态
                    </button>
                  </div>
                </div>

                <div className="editor-fields" style={{ overflowY: 'auto' }}>
                  {/* 测试描述 */}
                  {selectedTestCase.description && (
                    <div style={{ marginBottom: '20px' }}>
                      <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>描述</label>
                      <p style={{ margin: 0, lineHeight: 1.6 }}>{selectedTestCase.description}</p>
                            </div>
                          )}
                          
                  {/* 目标信息 */}
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>目标信息</label>
                    <p style={{ margin: '4px 0' }}>类型: {selectedTestCase.target_type}</p>
                    <p style={{ margin: '4px 0' }}>ID: {selectedTestCase.target_id}</p>
                          </div>

                  {/* 测试内容 */}
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>测试内容</label>
                    <pre style={{ 
                      background: '#f5f5f5', 
                      padding: '12px', 
                      borderRadius: '8px', 
                      fontSize: '13px', 
                      overflow: 'auto',
                      maxHeight: '200px',
                      border: '1px solid #e0e0e0'
                    }}>
                      {JSON.stringify(selectedTestCase.test_content, null, 2)}
                    </pre>
                  </div>

                  {/* 期望行为 */}
                  {selectedTestCase.expected_behavior && (
                    <div style={{ marginBottom: '20px' }}>
                      <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>期望行为</label>
                      <p style={{ margin: 0, lineHeight: 1.6 }}>{selectedTestCase.expected_behavior}</p>
                            </div>
                          )}
                          
                  {/* 测试配置 */}
                  <div style={{ marginBottom: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <label style={{ fontWeight: 600, margin: 0 }}>测试配置</label>
                      {!editingConfig ? (
                        <button 
                          onClick={() => setEditingConfig(true)}
                          style={{ fontSize: '13px', padding: '4px 12px' }}
                        >
                          ⚙️ 编辑配置
                        </button>
                      ) : (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            onClick={handleSaveConfig}
                            className="btn-primary"
                            style={{ fontSize: '13px', padding: '4px 12px' }}
                          >
                            💾 保存
                          </button>
                          <button 
                            onClick={handleCancelConfigEdit}
                            style={{ fontSize: '13px', padding: '4px 12px' }}
                          >
                            ❌ 取消
                          </button>
                        </div>
                          )}
                        </div>
                    
                    {!editingConfig ? (
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: '12px', 
                        borderRadius: '8px', 
                        fontSize: '13px', 
                        overflow: 'auto',
                        maxHeight: '200px',
                        border: '1px solid #e0e0e0'
                      }}>
                        {selectedTestCase.test_config ? JSON.stringify(selectedTestCase.test_config, null, 2) : '{}'}
                      </pre>
                    ) : (
                      <div style={{ 
                        background: '#f5f5f5', 
                        padding: '16px', 
                        borderRadius: '8px',
                        border: '1px solid #e0e0e0'
                      }}>
                        {/* 记忆预算配置 */}
                        <div style={{ marginBottom: '16px' }}>
                          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                            记忆预算（字符数）
                          </label>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                            <input
                              type="number"
                              placeholder="会话记忆"
                              value={configCtxMaxChat}
                              onChange={e => setConfigCtxMaxChat(e.target.value)}
                              min="50"
                              max="5000"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                            <input
                              type="number"
                              placeholder="短期记忆"
                              value={configCtxMaxStm}
                              onChange={e => setConfigCtxMaxStm(e.target.value)}
                              min="50"
                              max="5000"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                            <input
                              type="number"
                              placeholder="长期记忆"
                              value={configCtxMaxLtm}
                              onChange={e => setConfigCtxMaxLtm(e.target.value)}
                              min="50"
                              max="5000"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                          </div>
                        </div>
                        
                        {/* 群聊配置 */}
                        <div style={{ marginBottom: '16px' }}>
                          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                            群聊轮次
                          </label>
                          <input
                            type="number"
                            placeholder="最大回复轮数（3-10）"
                            value={configMaxGroupRounds}
                            onChange={e => setConfigMaxGroupRounds(e.target.value)}
                            min="3"
                            max="10"
                            style={{ fontSize: '13px', padding: '6px 10px', width: '100%' }}
                          />
                        </div>
                        
                        {/* LLM 参数配置 */}
                        <div>
                          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                            LLM 参数
                          </label>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                            <input
                              type="number"
                              placeholder="Temperature (0-2)"
                              value={configTemperature}
                              onChange={e => setConfigTemperature(e.target.value)}
                              min="0"
                              max="2"
                              step="0.1"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                            <input
                              type="number"
                              placeholder="Max Tokens"
                              value={configMaxTokens}
                              onChange={e => setConfigMaxTokens(e.target.value)}
                              min="100"
                              max="4096"
                              style={{ fontSize: '13px', padding: '6px 10px' }}
                            />
                          </div>
                          <select
                            value={configModel}
                            onChange={e => setConfigModel(e.target.value)}
                            style={{ fontSize: '13px', padding: '6px 10px', width: '100%' }}
                          >
                            <option value="">（使用默认模型）</option>
                            <option value="z-ai/glm-4-32b">z-ai/glm-4-32b</option>
                            <option value="z-ai/glm-4.5-air:free">z-ai/glm-4.5-air:free</option>
                            <option value="deepseek/deepseek-chat-v3.1:free">deepseek/deepseek-chat-v3.1:free</option>
                            <option value="tencent/hunyuan-a13b-instruct:free">tencent/hunyuan-a13b-instruct:free</option>
                          </select>
                        </div>
                        
                        <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '12px' }}>
                          💡 留空表示使用全局默认值
                        </div>
                  </div>
                )}
                  </div>
                </div>
              </>
            ) : null}
          </div>

          {/* 右侧：测试用例列表 */}
          <div className="test-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0 }}>📋 测试用例列表</h3>
              {selectedTarget && (
                <button
                  onClick={handleStartCreate}
                  className="btn-primary"
                  style={{ padding: '6px 12px', fontSize: '13px' }}
                >
                  ➕ 新建
                </button>
              )}
            </div>
            
            {!selectedTarget ? (
              <div className="empty-state">
                <p>选择测试目标后查看所有测试用例</p>
              </div>
            ) : (
              <>
                {/* 目标信息卡片 */}
                <div style={{
                  padding: '12px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: '8px',
                  marginBottom: '16px',
                  color: 'white'
                }}>
                  <div style={{ 
                    fontSize: '12px', 
                    opacity: 0.9,
                    marginBottom: '4px',
                    fontWeight: 500
                  }}>
                    {selectedTarget.type === 'character' ? '👤 测试角色' : '👥 测试群聊'}
                  </div>
                  <div style={{ 
                    fontSize: '16px', 
                    fontWeight: 600,
                    marginBottom: '4px'
                  }}>
                    {selectedTarget.name}
                  </div>
                  <div style={{ 
                    fontSize: '11px', 
                    opacity: 0.8,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <span>ID: {selectedTarget.id}</span>
                    <span>•</span>
                    <span>{testCategory}</span>
                  </div>
                </div>

                {/* 测试用例列表 */}
                <div className="related-test-cases">
                  <div style={{ 
                    fontSize: '13px', 
                    fontWeight: 600, 
                    marginBottom: '12px',
                    color: '#374151',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <span>所有测试用例</span>
                    <span style={{
                      background: '#e0e7ff',
                      color: '#4f46e5',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: 600
                    }}>
                      {testCases.filter(tc => 
                        tc.target_type === selectedTarget.type &&
                        tc.target_id === selectedTarget.id
                      ).length}
                    </span>
                  </div>
                  
                  {testCases
                    .filter(tc => 
                      tc.target_type === selectedTarget.type &&
                      tc.target_id === selectedTarget.id
                    )
                    .length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {testCases
                          .filter(tc => 
                            tc.target_type === selectedTarget.type &&
                            tc.target_id === selectedTarget.id
                    )
                    .map(tc => (
                            <div 
                              key={tc.id}
                              onClick={() => setSelectedTestCase(tc)}
                              style={{
                                padding: '12px',
                                border: selectedTestCase?.id === tc.id ? '2px solid #667eea' : '1px solid #e5e7eb',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                background: selectedTestCase?.id === tc.id ? '#f0f4ff' : 'white',
                                transition: 'all 0.2s',
                                boxShadow: selectedTestCase?.id === tc.id ? '0 4px 8px rgba(102, 126, 234, 0.2)' : '0 1px 2px rgba(0,0,0,0.05)'
                              }}
                              onMouseEnter={(e) => {
                                if (selectedTestCase?.id !== tc.id) {
                                  e.currentTarget.style.borderColor = '#667eea'
                                  e.currentTarget.style.boxShadow = '0 4px 6px rgba(102, 126, 234, 0.15)'
                                  e.currentTarget.style.transform = 'translateY(-2px)'
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (selectedTestCase?.id !== tc.id) {
                                  e.currentTarget.style.borderColor = '#e5e7eb'
                                  e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)'
                                  e.currentTarget.style.transform = 'translateY(0)'
                                }
                              }}
                            >
                              <div style={{ 
                                fontWeight: 600, 
                                marginBottom: '6px',
                                color: '#111827',
                                fontSize: '14px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                              }}>
                                <span>{tc.name}</span>
                                {tc.is_active === 1 && (
                                  <span style={{
                                    background: '#10b981',
                                    color: 'white',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    fontSize: '10px',
                                    fontWeight: 600
                                  }}>
                                    激活
                                  </span>
                                )}
                              </div>
                              {tc.description && (
                                <div style={{ 
                                  fontSize: '12px', 
                                  color: '#6b7280',
                                  lineHeight: '1.5',
                                  marginBottom: '8px'
                                }}>
                                  {tc.description}
                                </div>
                              )}
                              <div style={{
                                display: 'flex',
                                gap: '8px',
                                fontSize: '11px',
                                color: '#9ca3af'
                              }}>
                                <span>v{tc.version}</span>
                                <span>•</span>
                                <span>{new Date(tc.created_at * 1000).toLocaleDateString('zh-CN')}</span>
                              </div>
                      </div>
                    ))
                  }
                      </div>
                    ) : (
                      <div style={{ 
                        textAlign: 'center', 
                        padding: '40px 20px',
                        background: '#f9fafb',
                        borderRadius: '8px',
                        border: '1px dashed #d1d5db'
                      }}>
                        <div style={{ fontSize: '32px', marginBottom: '12px' }}>📝</div>
                        <p style={{ margin: '0 0 8px 0', color: '#6b7280', fontSize: '14px' }}>
                          该{selectedTarget.type === 'character' ? '角色' : '群聊'}暂无测试用例
                        </p>
                        <p style={{ 
                          margin: 0, 
                          fontSize: '12px', 
                          color: '#9ca3af',
                          lineHeight: '1.6'
                        }}>
                          您可以在主界面为这个{selectedTarget.type === 'character' ? '角色' : '群聊'}<br/>
                          创建多个测试场景来全面验证功能
                        </p>
                      </div>
                    )
                  }
                </div>

                {/* 提示信息 */}
                <div style={{
                  marginTop: '16px',
                  padding: '12px',
                  background: '#f0f9ff',
                  borderRadius: '8px',
                  border: '1px solid #bae6fd'
                }}>
                  <div style={{ 
                    fontSize: '12px', 
                    color: '#0369a1',
                    lineHeight: '1.6'
                  }}>
                    💡 <strong>使用说明：</strong><br/>
                    • 点击测试用例卡片可查看和编辑详情<br/>
                    • 当前选中的测试用例会高亮显示<br/>
                    • 前往"测试执行"标签页运行测试并查看执行历史
                  </div>
                </div>
              </>
            )}
          </div>
          </>
        ) : activeTab === 'execution' ? (
          // ========== 测试执行标签页 ==========
          <div className="test-execution-tab">
            {/* 上部：测试配置区 */}
            <div className="test-config-section">
              {/* 模式选择 */}
              <div className="execution-mode-selector">
                <button 
                  className={`mode-btn ${executionMode === 'single' ? 'active' : ''}`}
                  onClick={() => setExecutionMode('single')}
                >
                  单个测试
                </button>
                <button 
                  className={`mode-btn ${executionMode === 'batch' ? 'active' : ''}`}
                  onClick={() => setExecutionMode('batch')}
                >
                  批量测试
                </button>
                <button 
                  className={`mode-btn ${executionMode === 'category' ? 'active' : ''}`}
                  onClick={() => setExecutionMode('category')}
                >
                  按类别测试
                </button>
              </div>

              {/* 测试用例选择区 */}
              <div className="test-case-selector">
                {executionMode === 'single' && (
                  <>
                    <label>选择测试用例</label>
                    <select 
                      onChange={(e) => {
                        const testCase = availableTestCases.find(tc => tc.id === parseInt(e.target.value))
                        if (testCase) addTestCaseToConfig(testCase)
                      }}
                      value=""
                    >
                      <option value="">-- 请选择测试用例 --</option>
                      {availableTestCases.map(tc => (
                        <option key={tc.id} value={tc.id}>
                          {tc.name} ({tc.category})
                        </option>
                      ))}
                    </select>
                  </>
                )}

                {executionMode === 'batch' && (
                  <>
                    <label>选择测试用例（可多选）</label>
                    <div className="test-case-list">
                      {availableTestCases.map(tc => (
                        <label key={tc.id} className="test-case-checkbox">
                          <input
                            type="checkbox"
                            checked={selectedTestCases.includes(tc.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedTestCases([...selectedTestCases, tc.id])
                              } else {
                                setSelectedTestCases(selectedTestCases.filter(id => id !== tc.id))
                              }
                            }}
                          />
                          {tc.name} ({tc.category})
                        </label>
                              ))}
                            </div>
                    <button 
                      className="add-to-test-btn"
                      onClick={() => {
                        availableTestCases
                          .filter(tc => selectedTestCases.includes(tc.id))
                          .forEach(tc => addTestCaseToConfig(tc))
                        setSelectedTestCases([])
                      }}
                    >
                      ➕ 添加选中的测试用例
                    </button>
                  </>
                )}

                {executionMode === 'category' && (
                  <>
                    <label>选择测试类别</label>
                    <select 
                      value={selectedCategoryForExecution}
                      onChange={(e) => {
                        setSelectedCategoryForExecution(e.target.value)
                        setTestConfigs([]) // 清空现有配置
                      }}
                    >
                      {TEST_CATEGORIES.map(cat => (
                        <option key={cat.id} value={cat.id}>
                          {cat.icon} {cat.name}
                        </option>
                      ))}
                    </select>
                    <button 
                      className="add-to-test-btn"
                      style={{ marginTop: '8px' }}
                      onClick={() => {
                        availableTestCases.forEach(tc => addTestCaseToConfig(tc))
                      }}
                    >
                      ➕ 添加该类别所有测试用例
                    </button>
                  </>
                          )}
                        </div>

              {/* 测试配置表格 */}
              {testConfigs.length > 0 && (
                <table className="test-config-table">
                  <thead>
                    <tr>
                      <th>测试用例</th>
                      <th>提示词版本</th>
                      <th>评估器版本</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {testConfigs.map(config => (
                      <tr key={config.id}>
                        <td>{config.testCaseName}</td>
                        <td>
                          <select 
                            className="version-selector"
                            value={config.selectedPromptVersion || ''}
                            onChange={(e) => updateConfigPromptVersion(config.id, parseInt(e.target.value))}
                          >
                            <option value="">-- 选择版本 --</option>
                            {getAvailablePromptVersions(config).map(p => (
                              <option key={p.id} value={p.id}>
                                v{p.version} {p.is_active ? '(激活)' : ''}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <select 
                            className="version-selector"
                            value={config.selectedEvaluatorVersion || ''}
                            onChange={(e) => updateConfigEvaluatorVersion(config.id, parseInt(e.target.value))}
                          >
                            <option value="">-- 选择评估器 --</option>
                            {getAvailableEvaluatorVersions(config).map(p => (
                              <option key={p.id} value={p.id}>
                                v{p.version} {p.is_active ? '(激活)' : ''}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <span className={`config-status ${config.status}`}>
                            {config.status === 'pending' && '⏳ 待执行'}
                            {config.status === 'running' && '🔄 执行中'}
                            {config.status === 'completed' && '✅ 完成'}
                            {config.status === 'error' && '❌ 失败'}
                          </span>
                        </td>
                        <td>
                          <button 
                            className="remove-config-btn"
                            onClick={() => removeTestConfig(config.id)}
                            disabled={isExecuting}
                          >
                            移除
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {/* 测试操作按钮 */}
              <div className="test-actions">
                <button 
                  className="test-action-btn run-test-btn"
                  onClick={handleRunTests}
                  disabled={isExecuting || testConfigs.length === 0}
                >
                  {isExecuting ? '⏳ 执行中...' : '▶️ 运行测试'}
                </button>
                <button 
                  className="test-action-btn restore-btn"
                  onClick={handleRestoreTestEnvironment}
                  disabled={isRestoring || testConfigs.length === 0}
                >
                  {isRestoring ? '⏳ 恢复中...' : '🔄 恢复测试环境'}
                </button>
                  </div>
            </div>

            {/* 下部：测试结果展示区 */}
            <div className="test-results-section">
              <h3 style={{ marginTop: 0, marginBottom: '16px' }}>测试结果</h3>
              
              {executionResults.length === 0 ? (
                <div className="no-results">
                  <div className="no-results-icon">📊</div>
                  <p className="no-results-text">
                    {isExecuting ? '测试执行中，请稍候...' : '配置测试用例并点击"运行测试"开始执行'}
                  </p>
                </div>
              ) : (
                executionResults.map((result, index) => {
                  const displayMode = resultDisplayModes[index] || 'raw'
                  const parsed = parseEvaluationResult(result.evaluation_result)
                  
                  return (
                    <div key={index} className={`result-card ${result.success ? 'success' : 'error'}`}>
                      <div className="result-header">
                        <h4>
                          {result.success ? '✅' : '❌'} {result.testCaseName || `测试用例 #${result.test_case_id}`}
                        </h4>
                        <div className="result-meta">
                          {result.score !== undefined && (
                            <span className="result-score">{result.score}/100</span>
                          )}
                          <span>{formatDuration(result.duration_ms)}</span>
                          <span>{formatTimestamp(result.execution_time)}</span>
                        </div>
                      </div>

                      {result.error && (
                        <div style={{ 
                          padding: '12px', 
                          background: '#fee2e2', 
                          borderRadius: '4px', 
                          color: '#991b1b',
                          marginBottom: '12px'
                        }}>
                          <strong>错误:</strong> {result.error}
              </div>
            )}

                      {result.success && result.evaluation_feedback && (
                        <>
                          <div className="result-tabs">
                            <button 
                              className={`result-tab-btn ${displayMode === 'raw' ? 'active' : ''}`}
                              onClick={() => setResultDisplayModes({...resultDisplayModes, [index]: 'raw'})}
                            >
                              📝 原始评估
                            </button>
                            <button 
                              className={`result-tab-btn ${displayMode === 'structured' ? 'active' : ''}`}
                              onClick={() => setResultDisplayModes({...resultDisplayModes, [index]: 'structured'})}
                            >
                              📊 结构化解析
                            </button>
          </div>

                          <div className="result-content">
                            {displayMode === 'raw' ? (
                              <pre className="raw-text">{result.evaluation_feedback}</pre>
                            ) : (
                              <div className="structured-result">
                                {parsed.score !== undefined && (
                                  <div className="result-field">
                                    <div className="result-field-label">评分</div>
                                    <div className="result-field-content">{parsed.score} / 100</div>
              </div>
            )}
                                
                                {parsed.strengths && parsed.strengths.length > 0 && (
                                  <div className="result-field">
                                    <div className="result-field-label">✅ 优点</div>
                                    <div className="result-field-content">
                                      <ul>
                                        {parsed.strengths.map((s, i) => <li key={i}>{s}</li>)}
                                      </ul>
          </div>
                                  </div>
                                )}
                                
                                {parsed.weaknesses && parsed.weaknesses.length > 0 && (
                                  <div className="result-field">
                                    <div className="result-field-label">⚠️ 缺点</div>
                                    <div className="result-field-content">
                                      <ul>
                                        {parsed.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                                      </ul>
                                    </div>
                                  </div>
                                )}
                                
                                {parsed.suggestions && parsed.suggestions.length > 0 && (
                                  <div className="result-field">
                                    <div className="result-field-label">💡 建议</div>
                                    <div className="result-field-content">
                                      <ul>
                                        {parsed.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                                      </ul>
                                    </div>
                                  </div>
                                )}
                                
                                {Object.keys(parsed.details || {}).length > 0 && (
                                  <div className="result-field">
                                    <div className="result-field-label">📋 详细信息</div>
                                    <div className="result-field-content">
                                      <pre style={{ margin: 0, fontSize: '12px' }}>
                                        {JSON.stringify(parsed.details, null, 2)}
                                      </pre>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        ) : null}
        </div>

        {/* 版本切换弹窗 */}
        {showVersionSwitcher && selectedPrompt && (
          <PromptVersionSwitcher
            promptId={selectedPrompt.id}
            currentVersion={selectedPrompt.version}
            onClose={() => setShowVersionSwitcher(false)}
            onVersionChange={(versionId) => {
              loadPromptVersion(versionId)
              setShowVersionSwitcher(false)
            }}
          />
        )}
      </div>
    </div>
  )
}

