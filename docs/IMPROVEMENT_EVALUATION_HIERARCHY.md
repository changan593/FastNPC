# 评估提示词分级布局改进

## 概述

将评估提示词标签页的侧边栏从平铺结构改为分级结构，与功能提示词保持一致的UI风格。

## 改进前

评估提示词侧边栏是平铺的，所有15个评估器都在同一层级：

```
评估器分类
├─ 📋 基础身份信息评估器
├─ 🎭 性格特征评估器
├─ 📖 背景经历评估器
├─ 👤 外貌特征评估器
├─ 🚶 行为习惯评估器
├─ 🤝 人际关系评估器
├─ 🎯 技能特长评估器
├─ 💭 价值观信念评估器
├─ ❤️ 情感倾向评估器
├─ 📝 简介生成评估器
├─ 💬 单聊对话评估器
├─ 👥 群聊对话评估器
├─ 🧠 短期记忆凝练评估器
├─ 💾 长期记忆整合评估器
└─ 🎮 群聊中控评估器
```

**问题**：
- 列表过长，不易浏览
- 没有层次感，难以区分不同类型的评估器
- 与功能提示词的分级布局不一致

## 改进后

采用两级分类结构：

```
评估器分类
┌─ 结构化生成评估器
│  ├─ 基础身份信息评估器
│  ├─ 性格特征评估器
│  ├─ 背景经历评估器
│  ├─ 外貌特征评估器
│  ├─ 行为习惯评估器
│  ├─ 人际关系评估器
│  ├─ 技能特长评估器
│  ├─ 价值观信念评估器
│  └─ 情感倾向评估器
│
└─ 其他评估器
   ├─ 简介生成评估器
   ├─ 单聊对话评估器
   ├─ 群聊对话评估器
   ├─ 短期记忆凝练评估器
   ├─ 长期记忆整合评估器
   └─ 群聊中控评估器
```

**优势**：
- 层次清晰，9个结构化生成评估器分组在一起
- 与功能提示词的布局风格保持一致
- 易于导航和查找

## 实施细节

### 1. 数据结构调整

**文件**: `web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`

#### 1.1 定义分级类别

```typescript
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
```

#### 1.2 定义子类别名称映射

```typescript
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
```

### 2. UI渲染调整

修改评估提示词标签页的侧边栏渲染逻辑：

```typescript
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
```

### 3. 样式复用

使用了现有的CSS类：
- `.category-parent`: 父类别样式（灰色背景，不可点击）
- `.category-child`: 子类别样式（可点击，支持hover和active状态）
- `.category-tree`: 分类树容器

这些样式已在功能提示词标签页中定义，确保了视觉一致性。

## 用户体验改进

### 改进前
- 用户需要在15个评估器中逐一查找
- 没有明确的分组指示
- 视觉上较为单调

### 改进后
- 一眼就能看出两大类评估器
- 9个结构化生成评估器集中管理
- 与功能提示词的交互体验一致
- 更符合用户的心智模型

## 相关文件

- 前端组件：`web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`
- 样式文件：`web/fastnpc-web/src/components/modals/PromptManagementModal.css`（复用现有样式）
- 相关文档：`docs/EVALUATOR_STRUCTURED_CATEGORIES.md`

## 截图对比

### 改进前
```
评估器分类
  基础身份信息评估器
  性格特征评估器
  背景经历评估器
  外貌特征评估器
  行为习惯评估器
  人际关系评估器
  技能特长评估器
  价值观信念评估器
  情感倾向评估器
  简介生成评估器
  单聊对话评估器
  群聊对话评估器
  短期记忆凝练评估器
  长期记忆整合评估器
  群聊中控评估器
```

### 改进后
```
评估器分类
  结构化生成评估器
    基础身份信息评估器
    性格特征评估器
    背景经历评估器
    外貌特征评估器
    行为习惯评估器
    人际关系评估器
    技能特长评估器
    价值观信念评估器
    情感倾向评估器
  其他评估器
    简介生成评估器
    单聊对话评估器
    群聊对话评估器
    短期记忆凝练评估器
    长期记忆整合评估器
    群聊中控评估器
```

## 技术细节

### 分类逻辑

- **父类别**：仅作为分组标识，不可点击
- **子类别**：可点击，点击后加载对应的评估器提示词
- **状态管理**：`selectedCategory` 保存的是子类别的key（如 `EVALUATOR_BASIC_INFO`）

### 兼容性

- 保持了与后端数据库的兼容性
- 评估器的 `category` 字段仍然是子类别的key
- 不需要修改数据库结构或后端API

### 可扩展性

如果未来需要添加新的评估器类型，可以轻松扩展：

```typescript
const EVALUATION_CATEGORIES = {
  'STRUCTURED_GEN_EVALUATORS': { ... },
  'OTHER_EVALUATORS': { ... },
  'NEW_CATEGORY': {  // 新增类别
    name: '新类别名称',
    subCategories: ['EVALUATOR_XXX', 'EVALUATOR_YYY']
  }
}
```

## 构建结果

```
✓ 109 modules transformed.
✓ built in 749ms
```

构建成功，无错误。

## 更新日期

2025-10-19

