<!-- 5af4277a-bbc3-41af-a90a-bbeb3c38ffe7 fa378008-d096-492d-b7e1-b82731fa52f4 -->
# 全面接轨提示词管理系统实施计划

## 一、全面检查并补充遗漏的提示词

### 1. 修复 group_routes.py 中的硬编码提示词

**文件**: `fastnpc/api/routes/group_routes.py` (第753-766行)

**当前问题**: 群聊系统提示仍然硬编码在 `stream_group_chat()` 函数中

**修改方案**:
```python
# 从数据库加载群聊系统提示（或使用 prompt_builder 中已重构的方法）
from fastnpc.prompt_manager import PromptManager, PromptCategory

# 753-766行替换为：
if USE_DB_PROMPTS:
    try:
        prompt_data = PromptManager.get_active_prompt(PromptCategory.GROUP_CHAT_CHARACTER)
        if prompt_data:
            fixed_rules = PromptManager.render_prompt(
                prompt_data['template_content'],
                {"display_name": display_name, "other_members": all_names}
            )
    except Exception as e:
        # 降级到硬编码版本
        fixed_rules = (原有硬编码内容)
else:
    fixed_rules = (原有硬编码内容)
```

### 2. 全面搜索验证

检查以下文件确保无遗漏：
- `fastnpc/chat/prompt_builder.py` ✓ (已重构，有降级版本)
- `fastnpc/pipeline/structure/prompts.py` ✓ (已重构，有降级版本)
- `fastnpc/chat/memory_manager.py` ✓ (已重构，有降级版本)
- `fastnpc/chat/group_moderator.py` ✓ (已重构，有降级版本)
- `fastnpc/api/routes/group_routes.py` ✗ (需要修复)

## 二、添加版本切换功能

### 1. 后端API增强

**文件**: `fastnpc/api/routes/prompt_routes.py`

**新增端点**:
```python
@router.get("/admin/prompts/{id}/versions")
async def get_prompt_versions(
    id: int,
    current_user: dict = Depends(require_admin)
):
    """获取某个提示词的所有版本列表（包括激活状态和评估结果）"""
    # 查询同category、同sub_category的所有版本
    # 关联查询评估结果统计
    # 返回：版本号、创建时间、激活状态、平均评分、测试通过率等
```

### 2. 前端版本切换组件

**新建文件**: `web/fastnpc-web/src/components/PromptVersionSwitcher.tsx`

**组件结构**:
```typescript
interface PromptVersionSwitcherProps {
  promptId: number
  currentVersion: string
  onVersionChange: (versionId: number) => void
}

// 弹窗内容：
// - 版本列表（时间倒序）
// - 每个版本显示：
//   - 版本号 + 激活标识
//   - 创建时间
//   - 提示词内容预览（前200字符）
//   - 测试结果摘要（通过率、平均分）
//   - 操作按钮：[预览] [激活] [对比]
```

**样式**: 
- 卡片式布局
- 激活版本高亮（绿色边框）
- 测试通过率色阶图标（红/黄/绿）

### 3. 修改主界面集成版本切换

**文件**: `web/fastnpc-web/src/components/modals/PromptManagementModal.tsx`

**修改位置**: 第85-93行的 editor-header 区域

```typescript
<div className="editor-header">
  <div>
    <h3>{selectedPrompt.name}</h3>
    <span className="version-badge">
      v{selectedPrompt.version}
      {selectedPrompt.is_active === 1 && <span className="active-tag"> (激活)</span>}
    </span>
  </div>
  <div className="editor-actions">
    {/* 新增：版本切换按钮 */}
    <button 
      onClick={() => setShowVersionSwitcher(true)} 
      className="btn-secondary"
    >
      🔄 切换版本
    </button>
    
    <button onClick={handleSave} className="btn-primary">
      💾 保存
    </button>
    {/* ... 其他按钮 */}
  </div>
</div>

{/* 版本切换弹窗 */}
{showVersionSwitcher && (
  <PromptVersionSwitcher
    promptId={selectedPrompt.id}
    currentVersion={selectedPrompt.version}
    onClose={() => setShowVersionSwitcher(false)}
    onVersionChange={(versionId) => {
      // 加载新版本
      loadPromptVersion(versionId)
      setShowVersionSwitcher(false)
    }}
  />
)}
```

### 4. 版本切换弹窗样式

**新建文件**: `web/fastnpc-web/src/components/PromptVersionSwitcher.css`

**关键样式**:
```css
.version-switcher-modal {
  width: 900px;
  max-height: 80vh;
}

.version-card {
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.2s;
}

.version-card.active {
  border-color: #10b981;
  background: #f0fdf4;
}

.version-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.test-result-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.test-result-badge.high {
  background: #d1fae5;
  color: #065f46;
}

.test-result-badge.medium {
  background: #fef3c7;
  color: #78350f;
}

.test-result-badge.low {
  background: #fee2e2;
  color: #991b1b;
}
```

## 三、完善测试结果展示

### 1. 查询版本评估结果

**文件**: `fastnpc/api/routes/prompt_routes.py`

修改 `get_prompt_versions` 端点，关联查询评估数据：

```python
# 对每个版本，统计：
# - 总测试次数
# - 通过次数
# - 平均通过率
# - 最新测试时间
SELECT 
  pt.id, pt.version, pt.is_active, pt.created_at,
  COUNT(pe.id) as test_count,
  AVG(CASE WHEN pe.auto_metrics->>'overall_passed' = 'true' THEN 1 ELSE 0 END) as pass_rate,
  MAX(pe.created_at) as last_test_time
FROM prompt_templates pt
LEFT JOIN prompt_evaluations pe ON pt.id = pe.prompt_template_id
WHERE pt.category = ? AND pt.sub_category = ?
GROUP BY pt.id
ORDER BY pt.created_at DESC
```

### 2. 前端展示测试结果

在版本卡片中显示：
```typescript
<div className="version-test-summary">
  <span className={`test-result-badge ${getResultClass(version.pass_rate)}`}>
    通过率: {(version.pass_rate * 100).toFixed(0)}%
  </span>
  <span className="test-count">
    测试次数: {version.test_count}
  </span>
  {version.last_test_time && (
    <span className="last-test-time">
      最后测试: {formatDate(version.last_test_time)}
    </span>
  )}
</div>
```

## 四、实施步骤

### 步骤1: 修复遗漏的提示词 (30分钟)
1. 修改 `group_routes.py`，从数据库加载群聊系统提示
2. 测试群聊功能确保正常工作
3. 清除Redis缓存

### 步骤2: 后端API增强 (45分钟)
1. 新增 `GET /admin/prompts/{id}/versions` 端点
2. 查询逻辑包含评估结果统计
3. 测试API返回数据格式

### 步骤3: 前端版本切换组件 (2小时)
1. 创建 `PromptVersionSwitcher.tsx` 组件
2. 创建对应的CSS样式文件
3. 实现版本列表展示
4. 实现激活、预览、对比功能
5. 添加加载状态和错误处理

### 步骤4: 集成到主界面 (30分钟)
1. 修改 `PromptManagementModal.tsx`
2. 添加"切换版本"按钮
3. 集成版本切换弹窗
4. 测试版本切换流程

### 步骤5: 测试验证 (30分钟)
1. 创建多个版本测试版本切换
2. 测试激活功能
3. 验证测试结果显示
4. 检查UI美观性

## 五、关键文件清单

**需要修改的文件**:
1. `fastnpc/api/routes/group_routes.py` - 修复硬编码提示词
2. `fastnpc/api/routes/prompt_routes.py` - 新增版本列表API
3. `web/fastnpc-web/src/components/modals/PromptManagementModal.tsx` - 集成版本切换按钮

**需要新建的文件**:
1. `web/fastnpc-web/src/components/PromptVersionSwitcher.tsx` - 版本切换组件
2. `web/fastnpc-web/src/components/PromptVersionSwitcher.css` - 版本切换样式

**预计总时间**: 约4.5小时


### To-dos

- [ ] 修复 group_routes.py 中硬编码的群聊系统提示词，改为从数据库加载
- [ ] 新增 GET /admin/prompts/{id}/versions API端点，包含评估结果统计
- [ ] 创建 PromptVersionSwitcher.tsx 组件和对应CSS样式
- [ ] 在 PromptManagementModal 中集成版本切换按钮和弹窗
- [ ] 全面测试版本切换功能和提示词加载