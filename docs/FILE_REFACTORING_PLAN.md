# 大文件拆分优化计划

## 📋 概述

本文档详细说明如何拆分项目中过大的文件，以提升代码可维护性和开发效率。

---

## 🎯 优先级1: 拆分 `group_routes.py` (1114行)

### 当前问题
- 单文件过大，包含群聊相关的所有功能
- 混合了CRUD、消息管理、记忆管理、中控等多种职责
- 难以快速定位和修改特定功能

### 拆分方案

#### 目标结构

```
fastnpc/api/routes/
├── group/
│   ├── __init__.py           # 导出所有路由
│   ├── group_basic.py        # 基础CRUD (~300行)
│   ├── group_chat.py         # 聊天和消息 (~400行)
│   ├── group_memory.py       # 记忆管理 (~300行)
│   └── group_moderator.py    # 中控相关 (~100行)
└── group_routes.py           # 保留作为兼容层（可选）
```

#### 文件划分

##### 1. `group/group_basic.py` - 基础CRUD操作

**包含的路由**:
- `POST /groups` - 创建群聊
- `GET /groups` - 列出群聊
- `GET /groups/{group_id}` - 获取群聊详情
- `PUT /groups/{group_id}` - 更新群聊
- `DELETE /groups/{group_id}` - 删除群聊
- `POST /groups/{group_id}/members` - 添加成员
- `DELETE /groups/{group_id}/members/{character_id}` - 移除成员
- `GET /groups/{group_id}/members` - 获取成员列表

**预计行数**: ~300行

##### 2. `group/group_chat.py` - 聊天和消息功能

**包含的路由**:
- `POST /groups/{group_id}/chat` - 发送群聊消息
- `GET /groups/{group_id}/messages` - 获取消息历史
- `DELETE /groups/{group_id}/messages` - 清空消息
- `POST /groups/{group_id}/regenerate` - 重新生成回复
- `GET /groups/{group_id}/chat-context` - 获取聊天上下文

**预计行数**: ~400行

##### 3. `group/group_memory.py` - 记忆管理

**包含的路由**:
- `GET /groups/{group_id}/memories` - 获取群聊记忆
- `POST /groups/{group_id}/memories/compress` - 压缩短期记忆
- `POST /groups/{group_id}/memories/integrate` - 整合长期记忆
- `DELETE /groups/{group_id}/memories` - 清空记忆
- `GET /groups/{group_id}/memory-stats` - 记忆统计

**预计行数**: ~300行

##### 4. `group/group_moderator.py` - 中控相关

**包含的路由**:
- `POST /groups/{group_id}/select-speaker` - 选择发言者
- `GET /groups/{group_id}/moderator-status` - 中控状态
- `POST /groups/{group_id}/moderator/reset` - 重置中控

**预计行数**: ~100行

#### 实施步骤

**步骤1**: 创建目录和基础文件
```bash
mkdir -p fastnpc/api/routes/group
touch fastnpc/api/routes/group/__init__.py
touch fastnpc/api/routes/group/group_basic.py
touch fastnpc/api/routes/group/group_chat.py
touch fastnpc/api/routes/group/group_memory.py
touch fastnpc/api/routes/group/group_moderator.py
```

**步骤2**: 提取共享依赖和辅助函数
- 将共享的import语句移到各文件顶部
- 提取共享的辅助函数到 `group_utils.py`

**步骤3**: 分割代码
- 按功能模块复制路由到对应文件
- 确保每个文件都有必要的导入

**步骤4**: 创建统一导出
在 `group/__init__.py` 中：
```python
from fastapi import APIRouter
from .group_basic import router as basic_router
from .group_chat import router as chat_router
from .group_memory import router as memory_router
from .group_moderator import router as moderator_router

router = APIRouter(prefix="/groups", tags=["groups"])
router.include_router(basic_router)
router.include_router(chat_router)
router.include_router(memory_router)
router.include_router(moderator_router)
```

**步骤5**: 更新主路由注册
在 `fastnpc/api/main.py` 或相关文件中更新：
```python
# 旧的
from fastnpc.api.routes import group_routes
app.include_router(group_routes.router)

# 新的
from fastnpc.api.routes.group import router as group_router
app.include_router(group_router)
```

**步骤6**: 测试验证
- 运行所有群聊相关的API测试
- 确保所有路由正常工作
- 检查没有遗漏的功能

**步骤7**: 清理
- 备份原 `group_routes.py`
- 删除或重命名为 `group_routes.py.backup`

---

## 🎯 优先级2: 拆分 `PromptManagementModal.tsx` (1256行)

### 当前问题
- React组件过大，包含提示词、评估、测试用例三大功能
- 状态管理复杂，难以理解和维护
- 单个文件修改容易引入bug

### 拆分方案

#### 目标结构

```
web/fastnpc-web/src/components/prompts/
├── PromptManagementModal.tsx       # 主容器 (~200行)
├── PromptManagementModal.css       # 保留共享样式
├── PromptEditor.tsx                # 提示词编辑器 (~300行)
├── PromptTestPanel.tsx             # 测试面板 (~250行)
├── EvaluationPromptTab.tsx         # 评估提示词标签页 (~300行)
├── TestCaseTab.tsx                 # 测试用例标签页 (~300行)
├── TestConfigEditor.tsx            # 测试配置编辑器 (~150行)
└── types.ts                        # 共享类型定义
```

#### 组件划分

##### 1. `PromptManagementModal.tsx` - 主容器组件

**职责**:
- 管理标签页切换状态
- 协调子组件通信
- 提供整体布局

**代码示例**:
```typescript
export function PromptManagementModal({ show, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'prompts' | 'evaluation' | 'tests'>('prompts')

  return (
    <div className="prompt-management-modal">
      <div className="modal-header">
        <div className="tab-buttons">
          <button onClick={() => setActiveTab('prompts')}>🎯 提示词</button>
          <button onClick={() => setActiveTab('evaluation')}>⭐ 评估</button>
          <button onClick={() => setActiveTab('tests')}>🧪 测试用例</button>
        </div>
      </div>
      
      <div className="modal-body">
        {activeTab === 'prompts' && <PromptEditor />}
        {activeTab === 'evaluation' && <EvaluationPromptTab />}
        {activeTab === 'tests' && <TestCaseTab />}
      </div>
    </div>
  )
}
```

**预计行数**: ~200行

##### 2. `PromptEditor.tsx` - 提示词编辑器

**职责**:
- 提示词分类选择
- 提示词内容编辑
- 版本管理
- 保存、激活、复制操作

**状态管理**:
```typescript
interface PromptEditorState {
  categories: string[]
  selectedCategory: string
  prompts: Prompt[]
  selectedPrompt: Prompt | null
  editingContent: string
  editingDescription: string
  // ...
}
```

**预计行数**: ~300行

##### 3. `PromptTestPanel.tsx` - 测试面板

**职责**:
- 显示测试结果
- 执行测试
- 查看测试历史

**预计行数**: ~250行

##### 4. `EvaluationPromptTab.tsx` - 评估提示词标签页

**职责**:
- 评估器分类管理
- 评估提示词编辑
- 评估器信息展示

**预计行数**: ~300行

##### 5. `TestCaseTab.tsx` - 测试用例标签页

**职责**:
- 测试用例列表
- 测试用例详情
- 测试执行和结果展示

**包含子组件**: `TestConfigEditor`

**预计行数**: ~300行

##### 6. `TestConfigEditor.tsx` - 测试配置编辑器

**职责**:
- 测试参数配置
- 表单验证
- 配置保存

**预计行数**: ~150行

##### 7. `types.ts` - 共享类型定义

**包含类型**:
```typescript
export interface Prompt { /* ... */ }
export interface TestCase { /* ... */ }
export interface TestExecution { /* ... */ }
export interface EvaluationPrompt { /* ... */ }
// ...
```

#### 实施步骤

**步骤1**: 创建目录结构
```bash
mkdir -p web/fastnpc-web/src/components/prompts
```

**步骤2**: 提取类型定义
- 创建 `types.ts`
- 移动所有interface定义

**步骤3**: 创建子组件骨架
- 创建各子组件文件
- 定义Props接口
- 实现基本结构

**步骤4**: 迁移状态管理
- 识别每个组件需要的状态
- 使用Context API共享必要的状态
- 或使用props drilling（较简单）

**步骤5**: 迁移功能代码
- 逐个迁移函数和逻辑
- 保持API调用一致
- 确保事件处理正确

**步骤6**: 样式调整
- 拆分CSS或使用CSS Modules
- 确保样式隔离

**步骤7**: 测试验证
- 逐个功能测试
- 检查所有交互是否正常
- 验证数据流

**步骤8**: 清理
- 删除旧的大文件
- 更新导入语句

#### Context API方案（推荐）

为了更好的状态管理，建议使用Context:

```typescript
// PromptManagementContext.tsx
interface PromptManagementContextType {
  prompts: Prompt[]
  selectedPrompt: Prompt | null
  setSelectedPrompt: (prompt: Prompt | null) => void
  savePrompt: (data: Partial<Prompt>) => Promise<void>
  // ...
}

export const PromptManagementContext = createContext<PromptManagementContextType>(null!)

export function PromptManagementProvider({ children }: { children: ReactNode }) {
  // 状态和逻辑
  return (
    <PromptManagementContext.Provider value={value}>
      {children}
    </PromptManagementContext.Provider>
  )
}

// 使用
export function PromptManagementModal({ show, onClose }: Props) {
  return (
    <PromptManagementProvider>
      {/* 子组件 */}
    </PromptManagementProvider>
  )
}
```

---

## 📅 实施时间表

### 短期（1-2周）
- ✅ 删除冗余脚本文件（已完成）
- ⏳ 拆分 `group_routes.py`
- ⏳ 提取 `PromptEditor` 组件

### 中期（3-4周）
- ⏳ 完成 `PromptManagementModal` 全部拆分
- ⏳ 添加单元测试
- ⏳ 更新文档

### 长期（持续）
- ⏳ 识别其他可优化的大文件
- ⏳ 建立代码规范（文件大小限制）
- ⏳ 定期代码审查

---

## 🎯 成功标准

### 代码质量
- ✅ 单个文件不超过500行（特殊情况除外）
- ✅ 每个函数/组件职责单一
- ✅ 良好的类型定义和注释

### 可维护性
- ✅ 新开发者能快速找到相关代码
- ✅ 修改一个功能不影响其他功能
- ✅ 易于编写单元测试

### 性能
- ✅ 不影响运行时性能
- ✅ 改善代码编辑器性能（大文件加载慢）
- ✅ 提升开发效率

---

## ⚠️ 注意事项

1. **向后兼容**: 确保拆分后API接口保持不变
2. **渐进式重构**: 一次拆分一个文件，充分测试后再继续
3. **备份**: 拆分前备份原文件
4. **团队沟通**: 拆分可能影响其他开发者，需提前沟通
5. **文档更新**: 拆分后及时更新相关文档

---

## 📚 参考资源

### 代码组织最佳实践
- React组件设计模式
- FastAPI项目结构规范
- Python模块化设计

### 工具
- **ESLint**: 前端代码规范检查
- **Pylint**: Python代码质量检查
- **SonarQube**: 代码质量分析


