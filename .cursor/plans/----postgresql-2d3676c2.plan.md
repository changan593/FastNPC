<!-- 2d3676c2-00b4-4b82-ad76-472346bdd4ff 7fe36afe-af04-4a5d-8360-d4ccf87e8067 -->
# App.tsx 模块化拆分方案

## 目标
将 2598 行的 App.tsx 拆分为可维护的模块，预计减少至 ~500 行主文件

## 拆分策略

### 阶段 1: 创建 Context 层（状态管理）

创建 4 个 Context 文件来管理全局状态：

**1. `web/fastnpc-web/src/contexts/AuthContext.tsx`**
- 管理：user, authMode, authForm, agreedToTerms, showTerms
- 方法：doLogin, doRegister, doLogout
- 约 150 行

**2. `web/fastnpc-web/src/contexts/CharacterContext.tsx`**
- 管理：characters, activeRole, messages, creating, progress 等角色相关状态
- 方法：createRole, deleteRole, renameRole, copyRole, refreshList
- 约 200 行

**3. `web/fastnpc-web/src/contexts/GroupContext.tsx`**
- 管理：groups, activeGroupId, groupMessages, groupMemberBriefs 等群聊状态
- 方法：sendGroupMessage, loadGroupMemberBriefs, triggerModerator
- 约 200 行

**4. `web/fastnpc-web/src/contexts/AdminContext.tsx`**
- 管理：adminView, adminUsers, adminSelectedUser, adminTab 等管理员状态
- 方法：loadAdminUser, loadAdminChar, updateFeedbackStatus 等
- 约 250 行

### 阶段 2: 提取大型组件

**1. `web/fastnpc-web/src/components/AuthView.tsx`** (约 200 行)
- 包含登录/注册表单
- 用户协议模态框
- 从 App.tsx lines 962-1093 提取

**2. `web/fastnpc-web/src/components/admin/AdminPanel.tsx`** (约 600 行)
- 完整的管理员面板
- 包含 4 个子标签页视图
- 从 App.tsx lines 1296-1817 提取

**3. `web/fastnpc-web/src/components/admin/`** (子组件)
- `AdminUsersTab.tsx` - 用户列表视图
- `AdminCharactersTab.tsx` - 角色列表视图
- `AdminGroupsTab.tsx` - 群聊列表视图
- `AdminFeedbacksTab.tsx` - 反馈列表视图
- `AdminDetailView.tsx` - 详情视图
- 每个约 100-150 行

**4. `web/fastnpc-web/src/components/FeedbackModal.tsx`** (约 350 行)
- 用户反馈提交和历史
- 从 App.tsx lines 2367-2592 提取

### 阶段 3: 提取模态框组件

创建 `web/fastnpc-web/src/components/modals/` 目录：

**1. `CreateCharacterModal.tsx`** (约 150 行)
- 角色创建表单
- 从 App.tsx lines 2153-2245 提取

**2. `CreateGroupModal.tsx`** (约 80 行)
- 群聊创建表单
- 从 App.tsx lines 2099-2151 提取

**3. `SettingsModal.tsx`** (约 120 行)
- 用户设置界面
- 从 App.tsx lines 2259-2313 提取

**4. `PolysemantModal.tsx`** (约 80 行)
- 消歧选择界面
- 从 App.tsx lines 2321-2365 提取

**5. `InspectModal.tsx`** (约 30 行)
- 调试查看弹窗
- 从 App.tsx lines 2246-2257 提取

### 阶段 4: 提取布局组件

**1. `web/fastnpc-web/src/components/Sidebar.tsx`** (约 150 行)
- 左侧角色/群聊列表
- 搜索和排序
- 从 App.tsx lines 1098-1196 提取

**2. `web/fastnpc-web/src/components/ChatMain.tsx`** (约 200 行)
- 聊天主界面（单聊和群聊视图）
- 消息列表和输入框
- 从 App.tsx lines 1197-1875 提取

**3. `web/fastnpc-web/src/components/InfoPanel.tsx`** (约 120 行)
- 右侧信息面板
- 统一处理单聊和群聊的简介显示
- 从 App.tsx lines 1879-1959 提取

### 阶段 5: 提取自定义 Hooks

创建 `web/fastnpc-web/src/hooks/` 目录：

**1. `useCharacterOperations.ts`** (约 100 行)
- 封装角色 CRUD 操作
- 包含 renameRole, deleteRole, copyRole

**2. `useGroupOperations.ts`** (约 80 行)
- 封装群聊操作
- 包含成员管理、消息发送

**3. `usePolysemant.ts`** (约 80 行)
- 封装消歧逻辑
- 包含 openPolyModal 等

### 阶段 6: 重构 App.tsx

**最终的 App.tsx** (约 400-500 行)
- 导入所有 Context Providers
- 导入主要布局组件
- 组合各个模块
- 处理路由逻辑和全局状态初始化

## 文件结构

```
web/fastnpc-web/src/
├── App.tsx (重构后 ~500 行)
├── contexts/
│   ├── AuthContext.tsx
│   ├── CharacterContext.tsx
│   ├── GroupContext.tsx
│   └── AdminContext.tsx
├── components/
│   ├── AuthView.tsx
│   ├── Sidebar.tsx
│   ├── ChatMain.tsx
│   ├── InfoPanel.tsx
│   ├── FeedbackModal.tsx
│   ├── admin/
│   │   ├── AdminPanel.tsx
│   │   ├── AdminUsersTab.tsx
│   │   ├── AdminCharactersTab.tsx
│   │   ├── AdminGroupsTab.tsx
│   │   ├── AdminFeedbacksTab.tsx
│   │   └── AdminDetailView.tsx
│   └── modals/
│       ├── CreateCharacterModal.tsx
│       ├── CreateGroupModal.tsx
│       ├── SettingsModal.tsx
│       ├── PolysemantModal.tsx
│       └── InspectModal.tsx
└── hooks/
    ├── useCharacterOperations.ts
    ├── useGroupOperations.ts
    └── usePolysemant.ts
```

## 实施顺序

1. 创建 Context 文件（保留 App.tsx 原状态，先建立新结构）
2. 提取认证视图组件（最独立）
3. 提取管理员面板（最大模块）
4. 提取反馈模态框
5. 提取其他模态框组件
6. 提取布局组件（Sidebar, ChatMain, InfoPanel）
7. 提取自定义 hooks
8. 重构 App.tsx，整合所有模块
9. 测试所有功能确保无破坏性变更

## 注意事项

- 保持所有现有功能不变
- Context 之间通过 props 或组合 Context 共享状态
- 保留原有的 axios 实例配置
- 保持 CSS 类名不变
- 确保所有事件处理器正确传递


### To-dos

- [ ] 创建 4 个 Context 文件 (AuthContext, CharacterContext, GroupContext, AdminContext)
- [ ] 提取认证视图组件 (AuthView.tsx)
- [ ] 提取管理员面板及其子组件 (AdminPanel + 5 个子组件)
- [ ] 提取反馈模态框组件 (FeedbackModal.tsx)
- [ ] 提取其他模态框组件 (5 个 modal 组件)
- [ ] 提取布局组件 (Sidebar, ChatMain, InfoPanel)
- [ ] 提取自定义 hooks (3 个操作 hooks)
- [ ] 重构 App.tsx 整合所有模块
- [ ] 全面测试所有功能（登录、角色创建、群聊、管理员、反馈等）