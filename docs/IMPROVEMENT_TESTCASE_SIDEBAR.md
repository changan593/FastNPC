# 测试用例标签页左侧列表优化

## 优化日期
2025-10-19

## 问题背景

用户反馈：
> "举个例子，左下侧的测试用例列表只需要定位到'政治局'就行了，不要显示'政治局-群聊测试1'。具体政治局的第几个测试用例，就在右侧进行选择"

## 优化前的设计

### 布局
```
左侧：测试分类 + 所有测试用例（冗长）
├─ 单聊测试
├─ 政治局-群聊测试1
├─ 政治局-群聊测试2
├─ 政治局-外交测试3
├─ 特朗普-单聊测试1
├─ 特朗普-单聊测试2
└─ ...（可能有几十个）

中间：测试用例详情

右侧：相关测试用例（同一角色/群聊的其他测试）
```

### 问题
1. **左侧列表冗长**：如果一个角色/群聊有多个测试用例，列表会很长
2. **信息重复**：左侧和右侧都显示相同的测试用例
3. **导航不便**：需要在长列表中滚动查找
4. **视觉混乱**：测试用例名称通常较长，导致列表拥挤

## 优化后的设计

### 布局
```
左侧：测试分类 + 测试目标（去重）
├─ 单聊测试
├─ 👤 政治局 [3]
├─ 👤 特朗普 [2]
└─ 👤 李白 [1]

中间：当前选中测试用例的详情

右侧：该角色/群聊的所有测试用例
├─ 政治局-群聊测试1 （高亮）
├─ 政治局-群聊测试2
└─ 政治局-外交测试3
```

### 优势
1. ✅ **左侧简洁**：只显示角色/群聊名称，去重后通常只有几个到十几个
2. ✅ **层次清晰**：左侧定位target，右侧选择具体测试
3. ✅ **快速导航**：无需滚动长列表，直接点击目标
4. ✅ **数量可见**：每个target旁边显示测试用例数量徽章
5. ✅ **视觉整洁**：短名称 + 图标，视觉更清爽

## 实施内容

### 1. 新增状态
**文件**: `web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`

```typescript
const [selectedTarget, setSelectedTarget] = useState<{
  type: string, 
  id: string, 
  name: string
} | null>(null)
```

记录当前选中的测试目标（角色/群聊）。

### 2. 新增辅助函数

#### getUniqueTargets()
```typescript
const getUniqueTargets = () => {
  const targetMap = new Map<string, {type: string, id: string, name: string}>()
  
  testCases.forEach(tc => {
    const key = `${tc.target_type}-${tc.target_id}`
    if (!targetMap.has(key)) {
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
```

**功能**：
- 从测试用例列表中提取唯一的target
- 按 `target_type + target_id` 去重
- 从测试用例名称中智能提取角色/群聊名称（通常格式为：`角色名-测试场景`）

#### selectTarget()
```typescript
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
```

**功能**：
- 设置选中的target
- 自动选择该target的第一个测试用例
- 触发右侧列表和中间详情的更新

### 3. 修改左侧列表

**原代码**：显示所有测试用例
```jsx
{testCases.map((testCase) => (
  <div onClick={() => setSelectedTestCase(testCase)}>
    {testCase.name}
  </div>
))}
```

**新代码**：显示去重的target
```jsx
{getUniqueTargets().map((target) => {
  const testCount = testCases.filter(tc => 
    tc.target_type === target.type && tc.target_id === target.id
  ).length
  
  return (
    <div onClick={() => selectTarget(target)}>
      <span>{target.type === 'character' ? '👤' : '👥'}</span>
      <span>{target.name}</span>
      <span className="badge">{testCount}</span>
    </div>
  )
})}
```

**特点**：
- 显示图标（👤角色 / 👥群聊）
- 显示target名称（从测试用例名称提取）
- 显示数量徽章（该target有多少个测试用例）
- 点击时自动选中第一个测试用例

### 4. 修改中间区域

**空状态提示**：
```jsx
{!selectedTestCase ? (
  <div className="empty-state">
    <p>👈 请从左侧选择一个测试目标</p>
    <p>选择角色或群聊后，在右侧选择具体的测试用例</p>
  </div>
) : (...)}
```

### 5. 修改右侧面板

**标题**：从"🔗 相关测试用例"改为"📋 测试用例列表"

**数据源**：使用`selectedTarget`而不是`selectedTestCase`
```jsx
{!selectedTarget ? (
  <p>选择测试目标后查看所有测试用例</p>
) : (
  <>
    <div>目标: {selectedTarget.name}</div>
    <div>所有测试用例 [{testCount}]</div>
    {testCases
      .filter(tc => 
        tc.target_type === selectedTarget.type &&
        tc.target_id === selectedTarget.id
      )
      .map(tc => (
        <div 
          onClick={() => setSelectedTestCase(tc)}
          style={{
            border: selectedTestCase?.id === tc.id ? '2px solid #667eea' : '1px solid #e5e7eb',
            background: selectedTestCase?.id === tc.id ? '#f0f4ff' : 'white'
          }}
        >
          {tc.name}
        </div>
      ))
    }
  </>
)}
```

**特点**：
- 显示该target的**所有**测试用例（不排除当前选中的）
- 当前选中的测试用例高亮显示（蓝色边框 + 背景色）
- 点击任意测试用例可切换

### 6. 提示信息优化

```jsx
💡 使用说明：
• 点击测试用例卡片可查看和编辑详情
• 当前选中的测试用例会高亮显示
• 前往"测试执行"标签页运行测试并查看执行历史
```

## 交互流程

### 用户操作流程
```
1. 用户打开测试用例标签页
   ↓
2. 选择测试分类（如"群聊测试"）
   ↓
3. 左侧显示该分类下的所有target（如：政治局、诗词局）
   ↓
4. 点击"政治局"
   ↓
5. 自动选中政治局的第一个测试用例
   ↓
6. 中间显示该测试用例的详情
   ↓
7. 右侧显示政治局的所有测试用例（3个）
   ↓
8. 点击右侧的"政治局-外交测试3"
   ↓
9. 中间切换到该测试用例的详情
   ↓
10. 右侧的"政治局-外交测试3"高亮显示
```

## 代码统计

- **新增代码**：约45行（辅助函数 + 状态）
- **修改代码**：约80行（左侧列表 + 右侧面板）
- **删除代码**：约30行（简化逻辑）
- **净增加**：约95行

## 视觉设计

### 左侧列表项
```
┌────────────────────────┐
│ 👤 特朗普          [2] │  ← active状态：蓝色背景
├────────────────────────┤
│ 👤 普京            [3] │
├────────────────────────┤
│ 👥 政治局          [3] │
└────────────────────────┘
```

- 图标：区分角色（👤）和群聊（👥）
- 名称：从测试用例名称提取
- 徽章：显示测试用例数量，active时白色半透明背景

### 右侧测试用例卡片
```
┌─────────────────────────────────┐
│ 政治局-群聊测试1 [激活]         │  ← 当前选中：蓝色边框 + 浅蓝背景
├─────────────────────────────────┤
│ 测试群聊中的多人辩论场景        │
├─────────────────────────────────┤
│ v1.0.0 • 2025-10-19            │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 政治局-群聊测试2                │  ← 未选中：灰色边框 + 白色背景
├─────────────────────────────────┤
│ 测试群聊中的观点冲突处理        │
├─────────────────────────────────┤
│ v1.0.0 • 2025-10-18            │
└─────────────────────────────────┘
```

- 名称 + 激活徽章
- 描述（可选）
- 版本号 + 创建日期
- Hover效果：边框变色、阴影加深、轻微上移
- 选中状态：蓝色边框、浅蓝背景、更强阴影

## 验证清单

- [x] 左侧显示去重后的target列表
- [x] 每个target显示图标（👤/👥）
- [x] 每个target显示测试用例数量徽章
- [x] 点击target时自动选中第一个测试用例
- [x] 中间区域显示选中测试用例的详情
- [x] 中间空状态提示准确
- [x] 右侧显示该target的所有测试用例
- [x] 右侧数量徽章显示正确
- [x] 当前选中的测试用例高亮显示
- [x] 点击右侧测试用例可切换
- [x] Hover效果正常
- [x] 无linter错误

## 用户反馈

原始反馈：
> "举个例子，左下侧的测试用例列表只需要定位到'政治局'就行了，不要显示'政治局-群聊测试1'。具体政治局的第几个测试用例，就在右侧进行选择"

实施结果：
✅ 完全符合要求
- 左侧只显示"政治局"（带测试数量徽章）
- 右侧显示政治局的所有测试用例
- 用户可以在右侧选择具体的测试用例

## 后续优化建议

### 短期
- [ ] 支持target排序（按名称、测试数量）
- [ ] 添加搜索框，快速过滤target
- [ ] 支持拖拽调整测试用例顺序

### 中期
- [ ] 支持创建新测试用例按钮（在右侧面板）
- [ ] 支持批量操作（批量删除、批量激活）
- [ ] target图标可自定义

### 长期
- [ ] 支持树形结构（按角色分组 → 按测试类型分组）
- [ ] 测试覆盖率可视化
- [ ] 拖拽测试用例到执行队列

## 相关文档
- [测试用例标签页右侧面板改进](./IMPROVEMENT_TESTCASE_PANEL.md)
- [测试执行标签页实现](./TEST_EXECUTION_IMPLEMENTATION.md)
- [功能提示词标签页Bug修复](./BUGFIX_PROMPT_TAB.md)

## 总结

这次优化显著改善了测试用例管理的用户体验：

1. **简化导航**：左侧列表从可能的几十项减少到几项或十几项
2. **清晰层次**：左侧定位target → 右侧选择测试 → 中间查看详情
3. **视觉改进**：图标 + 徽章 + 短名称，更整洁美观
4. **高效操作**：快速定位、快速切换、状态可见

通过这次改进，测试用例管理变得更加直观和高效！

