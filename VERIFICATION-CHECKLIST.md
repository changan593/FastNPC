# 测试管理系统验证清单

## ✅ 前端验证清单

### 1. 构建状态
- [x] 前端构建成功（✓ built in 773ms）
- [ ] 浏览器能访问页面
- [ ] 没有 JavaScript 控制台错误

### 2. 侧边栏功能
- [ ] 角色列表正常显示
- [ ] 群聊列表正常显示
- [ ] 测试用例有 ⭐ 星标显示（如果已标记）
- [ ] 星标有 hover 提示"测试用例"

### 3. 管理面板
- [ ] 能进入管理员界面
- [ ] 看到"🔧 提示词管理"按钮
- [ ] 看到"🧪 测试管理"按钮（新增）
- [ ] 测试管理按钮有粉红色渐变

### 4. 测试管理模态框
- [ ] 点击按钮能打开模态框
- [ ] 模态框标题显示"🧪 测试用例管理"
- [ ] 三栏布局正常显示
- [ ] 左栏显示7个测试分类：
  - [ ] 💬 单聊测试
  - [ ] 👥 群聊测试
  - [ ] 📋 结构化生成
  - [ ] 📝 简介生成
  - [ ] 🧠 短期记忆
  - [ ] 💾 长期记忆
  - [ ] 🎯 群聊中控

### 5. 交互功能
- [ ] 点击不同分类能切换
- [ ] 选中分类高亮显示
- [ ] 中栏显示"暂无测试用例"提示（如果还没创建）
- [ ] 右栏显示空状态提示

### 6. 样式和动画
- [ ] 渐变色背景显示正常
- [ ] 鼠标悬停有交互效果
- [ ] 滚动条样式正常
- [ ] 响应式布局正常

## 🔧 后端验证清单

### API 端点测试

#### 1. 测试用例列表
```bash
curl -X GET "http://localhost:8000/admin/test-cases?category=SINGLE_CHAT" \
  --cookie "session=你的cookie"
```
预期：返回测试用例列表（可能为空）

#### 2. 星标切换（角色）
```bash
curl -X POST "http://localhost:8000/api/characters/李白/toggle-test-marker" \
  --cookie "session=你的cookie"
```
预期：返回 `{"ok": true, "is_test_case": true}`

#### 3. 星标切换（群聊）
```bash
curl -X POST "http://localhost:8000/api/groups/1/toggle-test-marker" \
  --cookie "session=你的cookie"
```
预期：返回 `{"ok": true, "is_test_case": true}`

#### 4. 测试执行历史
```bash
curl -X GET "http://localhost:8000/admin/test-reports?test_case_id=1" \
  --cookie "session=你的cookie"
```
预期：返回执行历史列表

## 📊 数据库验证

### 检查表结构
```bash
docker exec -it fastnpc-postgres psql -U fastnpc_user -d fastnpc
```

然后在 psql 中执行：

```sql
-- 1. 检查 group_chats 表是否有 is_test_case 字段
\d group_chats

-- 2. 检查 test_cases 表是否存在
\d test_cases

-- 3. 检查 test_executions 表是否存在
\d test_executions

-- 4. 检查评估提示词是否已创建
SELECT id, name, category, version 
FROM prompt_templates 
WHERE category LIKE 'EVALUATOR_%'
ORDER BY category;

-- 5. 检查是否有测试用例数据
SELECT COUNT(*) as test_case_count FROM test_cases;
```

## 🧪 功能测试流程

### 完整测试流程（当有测试数据后）

1. **标记测试用例**
   - 在角色列表中选择一个角色
   - 调用 toggle-test-marker API
   - 刷新页面，验证星标显示

2. **创建测试用例**（通过 API 或脚本）
   ```python
   # 运行测试数据生成脚本
   python fastnpc/scripts/generate_initial_test_cases.py
   ```

3. **查看测试用例**
   - 打开测试管理界面
   - 选择"单聊测试"分类
   - 中栏应显示测试用例列表
   - 点击一个测试用例
   - 右栏显示详细信息

4. **执行测试**
   - 在详情面板点击"执行测试"
   - 等待执行完成（会有"执行中..."提示）
   - 查看执行结果（通过/失败、评分、反馈）

5. **重置状态**
   - 点击"重置状态"按钮
   - 确认对话框
   - 验证状态已清空

6. **查看执行历史**
   - 在详情面板向下滚动
   - 查看"执行历史"部分
   - 展开详细信息查看 LLM 响应

## 🐛 常见问题排查

### 问题1: 测试管理按钮不显示
- 检查是否是管理员账号登录
- 检查前端构建是否成功
- 查看浏览器控制台是否有错误
- 清除浏览器缓存后刷新

### 问题2: 打开模态框报错
- 检查后端是否正常运行
- 查看 backend.log 日志
- 验证 API 端点是否可访问

### 问题3: 测试用例列表为空
- 这是正常的，因为还没生成测试数据
- 需要运行数据生成脚本（阶段三的任务）

### 问题4: 执行测试失败
- 检查评估提示词是否已创建
- 验证目标角色/群聊是否存在
- 查看后端日志获取详细错误

## 📝 下一步任务

当前已完成：
- ✅ 阶段一：数据库设计与迁移
- ✅ 阶段二：后端 API 开发
- ✅ 阶段三：测试数据生成（评估提示词）
- ✅ 阶段四：前端界面开发

待完成：
- ⏳ 阶段三：生成实际测试用例（50个角色 + 11个群聊）
- ⏳ 阶段五：测试执行引擎（实现真正的测试执行逻辑）
- ⏳ 阶段六：集成与测试

## 🚀 快速验证命令

```bash
# 1. 检查后端是否运行
curl http://localhost:8000/health

# 2. 检查前端是否正常
curl http://localhost:8000/ | head -20

# 3. 检查数据库连接
docker exec -it fastnpc-postgres psql -U fastnpc_user -d fastnpc -c "SELECT COUNT(*) FROM prompt_templates;"

# 4. 查看后端日志
tail -f /home/changan/MyProject/FastNPC/backend.log
```

