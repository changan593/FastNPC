# 测试用例CRUD功能实现

## 概述

本文档记录了为测试用例管理添加完整的增删改查（CRUD）功能的实现过程。

## 背景

之前测试用例是通过脚本自动生成的，用户无法手动管理。现在添加了完整的CRUD功能，用户可以：

- ✅ 查看测试用例详情
- ✅ 创建新的测试用例
- ✅ 编辑现有测试用例
- ✅ 删除测试用例
- ✅ 表单验证
- ✅ 确认对话框

## 实施内容

### 1. 后端API扩展

#### 1.1 新增DELETE接口

**文件**: `fastnpc/api/routes/test_case_routes.py`

```python
@router.delete('/admin/test-cases/{id}')
async def delete_test_case(id: int, request: Request):
    """删除测试用例"""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 检查测试用例是否存在
        cur.execute(f"SELECT * FROM test_cases WHERE id = {placeholder}", (id,))
        test_case = cur.fetchone()
        if not test_case:
            return JSONResponse({"error": "测试用例不存在"}, status_code=404)
        
        # 删除相关的测试执行记录
        cur.execute(f"DELETE FROM test_executions WHERE test_case_id = {placeholder}", (id,))
        
        # 删除测试用例
        cur.execute(f"DELETE FROM test_cases WHERE id = {placeholder}", (id,))
        
        conn.commit()
        return {"ok": True, "message": "删除成功"}
    
    except Exception as e:
        print(f"[ERROR] 删除测试用例失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return JSONResponse({"error": f"删除失败: {e}"}, status_code=500)
    
    finally:
        _return_conn(conn)
```

**特性**：
- 删除测试用例前先检查是否存在
- 级联删除相关的测试执行记录
- 完整的错误处理和回滚

#### 1.2 已有的API

现有的API已经支持：
- `POST /admin/test-cases` - 创建测试用例
- `PUT /admin/test-cases/{id}` - 更新测试用例

### 2. 前端状态管理

**文件**: `web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`

#### 2.1 新增状态变量

```typescript
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
```

#### 2.2 核心功能函数

##### 创建测试用例

```typescript
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
```

特性：
- 自动填充当前的测试分类
- 自动填充选中的目标（角色/群聊）

##### 编辑测试用例

```typescript
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
```

特性：
- 自动填充现有测试用例的所有字段
- 智能处理test_content（字符串或对象）

##### 保存测试用例

```typescript
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
```

特性：
- 完整的字段验证
- 智能JSON解析（支持纯文本或JSON）
- 自动刷新列表
- 创建后自动选中新测试用例

##### 删除测试用例

```typescript
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
```

特性：
- 二次确认对话框
- 删除后自动刷新列表
- 清除选中状态

### 3. UI/UX设计

#### 3.1 三种显示模式

测试用例管理界面支持三种模式：

1. **空状态** - 未选择测试用例时
   - 显示提示信息
   - "创建新测试用例"按钮

2. **编辑/创建模式** - 表单编辑器
   - 所有字段可编辑
   - "保存"和"取消"按钮

3. **查看模式** - 只读展示
   - 显示测试用例详情
   - "执行测试"、"编辑"、"删除"、"重置状态"按钮

#### 3.2 表单字段

创建/编辑表单包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 测试用例名称 | 文本 | ✅ | 例如：特朗普-政治话题测试 |
| 描述 | 多行文本 | ❌ | 测试用例的详细描述 |
| 版本 | 文本 | ❌ | 默认1.0.0 |
| 测试分类 | 下拉选择 | ✅ | 单聊/群聊/结构化等 |
| 目标类型 | 下拉选择 | ✅ | character/group |
| 目标ID | 文本 | ✅ | 角色或群聊的ID |
| 测试内容 | 多行文本(JSON) | ✅ | JSON格式的测试数据 |
| 期望行为 | 多行文本 | ❌ | 描述期望的输出 |

#### 3.3 按钮布局

**查看模式（中间区域）**：
```
┌─────────────────────────────────┐
│ 测试用例名称                     │
│ 版本 · 类型 · 创建时间           │
│                                  │
│ [▶️ 执行测试] [✏️ 编辑]         │
│ [🗑️ 删除] [🔄 重置状态]        │
└─────────────────────────────────┘
```

**编辑/创建模式（中间区域）**：
```
┌─────────────────────────────────┐
│ ➕ 创建测试用例 / ✏️ 编辑测试用例│
│                                  │
│ [💾 保存] [✕ 取消]              │
└─────────────────────────────────┘
```

**右侧面板**：
```
┌─────────────────────────────────┐
│ 📋 测试用例列表     [➕ 新建]   │
└─────────────────────────────────┘
```

### 4. 用户流程

#### 4.1 创建新测试用例

1. 在左侧选择测试分类（例如：单聊测试）
2. 在左侧选择测试目标（例如：特朗普）
3. 点击右侧面板的"➕ 新建"按钮
4. 填写表单（自动填充了分类和目标）
5. 点击"💾 保存"
6. 测试用例创建成功，自动刷新列表

#### 4.2 编辑测试用例

1. 在右侧列表中选择要编辑的测试用例
2. 点击中间区域的"✏️ 编辑"按钮
3. 修改表单字段
4. 点击"💾 保存"
5. 测试用例更新成功

#### 4.3 删除测试用例

1. 在右侧列表中选择要删除的测试用例
2. 点击中间区域的"🗑️ 删除"按钮
3. 确认删除操作
4. 测试用例删除成功，列表自动刷新

### 5. 表单验证

实施了以下验证规则：

- **测试用例名称**：不能为空
- **目标ID**：不能为空
- **测试内容**：不能为空
- **测试内容格式**：尝试解析为JSON，失败则自动包装为`{messages: [...]}`

### 6. 错误处理

- ✅ 网络请求错误处理
- ✅ JSON解析错误处理
- ✅ 数据库操作错误处理
- ✅ 用户友好的错误提示
- ✅ 事务回滚（后端）

### 7. 类型安全

使用TypeScript确保类型安全：

```typescript
// 编辑表单数据类型
interface EditFormData {
  name: string
  description: string
  version: string
  category: string
  prompt_category: string
  prompt_sub_category: string
  target_type: 'character' | 'group'
  target_id: string
  test_content: string
  expected_behavior: string
}
```

### 8. 性能优化

- ✅ 自动刷新列表（避免手动刷新）
- ✅ 创建后自动选中新测试用例
- ✅ 智能JSON格式化（仅在编辑时）
- ✅ 条件渲染（避免不必要的DOM更新）

## 使用示例

### 示例1：创建单聊测试用例

```json
{
  "name": "特朗普-政治话题测试",
  "description": "测试特朗普对政治话题的回应",
  "category": "SINGLE_CHAT",
  "target_type": "character",
  "target_id": "trump-001",
  "test_content": {
    "messages": [
      "你对当前的国际局势有什么看法？",
      "你认为经济政策应该如何调整？"
    ]
  },
  "expected_behavior": "应该表现出强硬、自信的态度，并提供具体的政策建议"
}
```

### 示例2：创建群聊测试用例

```json
{
  "name": "政治局-外交讨论",
  "description": "测试政治局群聊中关于国际外交的讨论",
  "category": "GROUP_CHAT",
  "target_type": "group",
  "target_id": "politics-group",
  "test_content": {
    "user_message": "大家认为当前的中美关系应该如何发展？",
    "expected_rounds": 5
  },
  "expected_behavior": "各角色应该从不同角度表达观点，展现多样性"
}
```

## 技术亮点

1. **三模式UI切换**：空状态/编辑/查看，流畅切换
2. **智能表单填充**：根据上下文自动填充字段
3. **JSON智能解析**：支持直接输入文本或JSON
4. **完整的验证**：前后端双重验证
5. **友好的确认**：删除操作二次确认
6. **自动刷新**：操作后自动更新列表
7. **类型安全**：TypeScript完整类型定义

## 后续改进建议

1. **批量操作**：支持批量删除测试用例
2. **导入/导出**：支持JSON格式批量导入导出
3. **测试用例模板**：提供常用测试用例模板
4. **复制测试用例**：快速复制现有测试用例
5. **测试用例标签**：添加标签系统便于分类
6. **搜索过滤**：测试用例列表搜索和过滤
7. **版本对比**：支持测试用例版本对比

## 相关文件

- 后端API：`fastnpc/api/routes/test_case_routes.py`
- 前端组件：`web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`
- 样式文件：`web/fastnpc-web/src/components/modals/PromptManagementModal.css`
- 类型定义：`web/fastnpc-web/src/types.ts`

## 测试清单

- [x] 创建测试用例（字段完整）
- [x] 创建测试用例（字段部分填写）
- [x] 编辑测试用例
- [x] 删除测试用例（带确认）
- [x] 表单验证（必填字段）
- [x] JSON解析（有效JSON）
- [x] JSON解析（纯文本）
- [x] 取消编辑/创建
- [x] 创建后自动选中
- [x] 列表自动刷新
- [x] 错误处理

## 更新日期

2025-10-19

