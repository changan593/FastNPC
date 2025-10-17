<!-- 2d3676c2-00b4-4b82-ad76-472346bdd4ff e9ebcad1-6249-49fb-af2f-15bea2f9965d -->
# CSS 模块化重构方案

## 概述

将单一的 App.css (1538行) 拆分为按功能组织的模块化CSS文件，同时清理未使用的样式规则。

## 文件结构

```
src/styles/
├── index.css          # 全局样式 + CSS变量 (~50行)
├── auth.css           # 认证相关样式 (~120行)
├── layout.css         # 布局组件样式 (~200行)
├── modal.css          # 模态框基础样式 (~150行)
├── admin.css          # 管理员面板样式 (~450行)
├── feedback.css       # 反馈系统样式 (~320行)
├── group.css          # 群聊相关样式 (~280行)
└── responsive.css     # 移动端响应式 (~350行)
```

## 实施步骤

### 1. 创建 styles 目录结构

- 创建 `src/styles/` 目录

### 2. 拆分并创建各模块CSS文件

**index.css** - 全局入口

- CSS变量定义 (:root)
- 基础HTML/body样式
- 通用工具类 (badge, muted, btn-link等)
- 导入所有其他CSS模块

**auth.css** - 认证模块

- .auth-wrap, .auth-card
- .auth-background-text
- .terms-agreement
- 登录/注册表单样式

**layout.css** - 布局组件

- .layout 网格布局
- .sidebar 及其子元素
- .chat, .chat-head, .chat-body, .chat-input
- .search
- .role-list
- .fab-container

**modal.css** - 模态框基础

- .modal, .dialog
- .dialog 内的通用元素 (label, input, select, actions)
- .progress
- .opt-grid, .opt-chip (导出选项)
- .modal-content

**admin.css** - 管理员面板

- .admin-page, .admin-header, .admin-tabs
- .admin-content, .admin-table
- .admin-detail-page, .admin-detail-section
- .admin-group-msg, .admin-msgs
- .json-view
- .member-list, .member-item
- .admin-inspect-btn
- .admin-card (移动端卡片)

**feedback.css** - 反馈系统

- .feedback-dialog, .feedback-header
- .feedback-tabs, .feedback-content
- .feedback-list, .feedback-item
- .feedback-detail, .feedback-detail-section
- .feedback-status
- .admin-reply-section
- .feedback-btn-sidebar

**group.css** - 群聊功能

- .group-info-panel
- .group-msg-item
- .member-brief
- .status-bar
- 群聊相关的头像和气泡样式

**responsive.css** - 移动端适配

- @media (max-width: 768px) 内的所有规则
- 移动端布局调整
- .mobile-menu-btn, .mobile-overlay
- 移动端卡片视图

### 3. 更新主入口文件

- 修改 `src/main.tsx`，导入 `styles/index.css` 而不是 `App.css`

### 4. 清理未使用样式

- 删除 .logo, .card, .read-the-docs 等示例样式
- 删除 @keyframes logo-spin

### 5. 删除旧文件

- 删除 `src/App.css`
- 删除 `src/App.tsx.backup`
- 删除 `src/App.new.tsx` (如果存在)

### 6. 验证

- 启动开发服务器，确保所有样式正常加载
- 检查各个页面和组件的样式是否完整
- 测试响应式布局

## 注意事项

1. CSS变量保持在 index.css 顶部，确保全局可用
2. 模块间如有样式依赖，通过CSS变量解决
3. 保持所有类名不变，确保不影响现有组件
4. import顺序：index.css 最先，其他按功能加载
5. 每个文件顶部添加注释说明其用途

### To-dos

- [ ] 创建 src/styles/ 目录和8个CSS文件
- [ ] 拆分并迁移 auth.css 样式
- [ ] 拆分并迁移 layout.css 样式
- [ ] 拆分并迁移 modal.css 样式
- [ ] 拆分并迁移 admin.css 样式
- [ ] 拆分并迁移 feedback.css 样式
- [ ] 拆分并迁移 group.css 样式
- [ ] 拆分并迁移 responsive.css 样式
- [ ] 创建 index.css 作为总入口，导入所有模块
- [ ] 更新 main.tsx 的CSS导入路径
- [ ] 删除旧文件 (App.css, App.tsx.backup, App.new.tsx)
- [ ] 验证样式完整性和响应式布局