# FastNPC PostgreSQL 迁移验证指南

## 📊 自动化测试结果

✅ **成功率: 100%** (7/7项测试通过)

### 已验证项目：
1. ✅ PostgreSQL 数据库连接
2. ✅ 20个数据库表结构完整
3. ✅ 角色数据完整性（百科全文、结构化数据）
4. ✅ 角色数据加载功能
5. ✅ 消息存储（单聊8条、群聊1个、群聊消息3条）
6. ✅ 用户系统（2个用户、1个管理员）
7. ✅ 反馈系统（1条反馈）

## 🧪 前端功能验证清单

### 1. 用户认证功能 (5分钟)

**测试目标**: 验证用户注册、登录、登出功能

#### 步骤：
1. 打开浏览器访问 `http://localhost:8000`
2. **注册新用户**：
   - 点击"注册"按钮
   - 输入用户名（如 `testuser`）和密码
   - 验证注册成功并自动登录
3. **登出**：点击右上角用户名 → 登出
4. **登录**：使用刚才的用户名和密码登录
5. **验证**：检查是否能正常进入主界面

#### 预期结果：
- ✅ 注册成功
- ✅ 登录成功
- ✅ 登出成功
- ✅ 用户状态正确显示

---

### 2. 角色管理功能 (10分钟)

**测试目标**: 验证角色列表、详情、创建功能

#### 步骤：
1. **查看角色列表**：
   - 登录后查看左侧角色列表
   - 应该看到：赵云202510171433、司马迁202510171439 等
2. **查看角色详情**：
   - 点击"赵云"
   - 查看右侧显示的角色简介、性格特质等信息
3. **创建新角色**：
   - 点击"创建角色"按钮
   - 输入角色名（如 `诸葛亮`）
   - 选择数据源：百度百科
   - 点击提交，等待创建完成（约30-60秒）
4. **验证新角色**：
   - 检查角色列表中是否出现"诸葛亮"
   - 点击查看详情，确认数据完整

#### 预期结果：
- ✅ 角色列表正确显示
- ✅ 角色详情正确加载（从数据库）
- ✅ 新角色创建成功
- ✅ 百科数据完整（可运行 `python test_postgresql_migration.py` 再次验证）

---

### 3. 单角色对话功能 (10分钟)

**测试目标**: 验证从数据库加载角色数据进行对话

#### 步骤：
1. **开始对话**：
   - 选择"赵云"角色
   - 点击"开始对话"按钮
2. **发送消息**：
   - 输入: `你好，赵云！请介绍一下你自己`
   - 等待AI回复
3. **验证角色设定**：
   - 检查赵云的回复是否符合人物设定
   - 应该体现出忠诚、谨慎、勇敢等特质
4. **继续对话**：
   - 输入: `你和刘备的关系怎么样？`
   - 验证回复是否提及历史关系
5. **查看对话历史**：
   - 刷新页面，重新选择赵云
   - 验证之前的对话是否保存

#### 预期结果：
- ✅ 角色能正常响应
- ✅ 回复符合角色设定（性格、背景、关系等）
- ✅ 对话历史正确保存和加载
- ✅ 消息保存到 `messages` 表

---

### 4. 记忆压缩功能 (15分钟)

**测试目标**: 验证短期记忆和长期记忆的数据库保存

#### 步骤：
1. **触发记忆压缩**：
   - 与赵云对话，连续发送10条以上消息
   - 等待系统自动触发记忆压缩（通常在20条消息后）
2. **验证数据库记录**：
   ```bash
   python3 -c "
   from fastnpc.api.auth import _get_conn
   conn = _get_conn()
   cur = conn.cursor()
   cur.execute('SELECT COUNT(*) FROM character_memories WHERE character_id=7')
   print(f'记忆条数: {cur.fetchone()[0]}')
   conn.close()
   "
   ```
3. **检查记忆类型**：
   - 短期记忆应该有多条
   - 长期记忆可能需要更多对话才会生成

#### 预期结果：
- ✅ 消息超过阈值后触发压缩
- ✅ 短期记忆保存到 `character_memories` 表
- ✅ 长期记忆正确生成和保存
- ✅ `messages.compressed` 字段标记为1

---

### 5. 群聊功能 (15分钟)

**测试目标**: 验证群聊创建和多角色对话

#### 步骤：
1. **创建群聊**：
   - 点击"创建群聊"按钮
   - 输入群聊名称: `三国群聊`
   - 选择角色: 赵云、诸葛亮（如果已创建）
   - 点击创建
2. **发送消息**：
   - 输入: `大家好，我想听听你们对三国时期的看法`
   - 等待角色轮流回复
3. **观察互动**：
   - 角色应该根据各自性格和背景回复
   - 可能会相互提及
4. **验证数据**：
   - 检查群聊列表是否显示新群聊
   - 检查消息是否正确保存

#### 预期结果：
- ✅ 群聊创建成功
- ✅ 多个角色轮流发言
- ✅ 角色互动合理
- ✅ 群聊消息保存到 `group_messages` 表

---

### 6. 管理员功能 (10分钟)

**测试目标**: 验证管理员查看用户、角色、群聊等功能

#### 前提：
- 使用管理员账号登录（is_admin=1）

#### 步骤：
1. **查看用户列表**：
   - 点击"管理"→"用户管理"
   - 应该看到所有注册用户
2. **查看角色列表**：
   - 点击"管理"→"角色管理"
   - 应该看到所有用户创建的角色
   - 点击某个角色查看详细信息
3. **查看群聊**：
   - 点击"管理"→"群聊管理"
   - 应该看到所有群聊和消息
4. **查看反馈**：
   - 点击"管理"→"反馈管理"
   - 应该看到用户提交的反馈

#### 预期结果：
- ✅ 所有管理功能正常显示
- ✅ 数据从数据库正确加载
- ✅ 详细信息完整展示

---

### 7. 反馈功能 (5分钟)

**测试目标**: 验证用户反馈提交和查看

#### 步骤：
1. **提交反馈**（非管理员用户）：
   - 点击角色简介下方的"我要反馈"按钮
   - 输入反馈内容
   - 可选：上传图片附件
   - 点击提交
2. **查看反馈历史**：
   - 点击"查看历史"
   - 验证提交的反馈出现在列表中
3. **管理员回复**（管理员账号）：
   - 切换到管理员账号
   - 查看反馈列表
   - 对某个反馈进行回复
4. **用户查看回复**：
   - 切回普通用户
   - 查看反馈历史，验证管理员回复

#### 预期结果：
- ✅ 反馈提交成功
- ✅ 反馈保存到 `feedbacks` 表
- ✅ 图片附件正确上传
- ✅ 管理员回复成功显示

---

### 8. 角色删除功能 (5分钟)

**测试目标**: 验证级联删除功能

#### 步骤：
1. **删除角色**：
   - 选择一个测试角色（如刚创建的"诸葛亮"）
   - 点击"删除"按钮
   - 确认删除
2. **验证级联删除**：
   ```bash
   python3 -c "
   from fastnpc.api.auth import _get_conn
   conn = _get_conn()
   cur = conn.cursor()
   
   # 假设诸葛亮的ID是9
   char_id = 9
   
   tables = ['character_basic_info', 'character_experiences', 'character_relationships', 'messages']
   for table in tables:
       cur.execute(f'SELECT COUNT(*) FROM {table} WHERE character_id=%s', (char_id,))
       count = cur.fetchone()[0]
       print(f'{table}: {count} 条记录（应该为0）')
   
   conn.close()
   "
   ```

#### 预期结果：
- ✅ 角色从列表中消失
- ✅ 所有关联数据被级联删除
- ✅ 不影响其他角色

---

## 📋 快速验证命令

### 运行自动化测试：
```bash
cd /home/changan/MyProject/FastNPC
source .venv/bin/activate
python test_postgresql_migration.py
```

### 查看数据库状态：
```bash
PGPASSWORD=fastnpc123 psql -h localhost -U fastnpc -d fastnpc -c "
SELECT 
    '角色总数' as 项目, COUNT(*)::text as 数量 
FROM characters
UNION ALL
SELECT 
    '有百科内容的角色', COUNT(*)::text 
FROM characters WHERE baike_content IS NOT NULL AND LENGTH(baike_content) > 100
UNION ALL
SELECT 
    '消息总数', COUNT(*)::text 
FROM messages
UNION ALL
SELECT 
    '群聊总数', COUNT(*)::text 
FROM group_chats
UNION ALL
SELECT 
    '用户总数', COUNT(*)::text 
FROM users
UNION ALL
SELECT 
    '反馈总数', COUNT(*)::text 
FROM feedbacks;
"
```

### 查看具体角色数据：
```bash
python3 -c "
from fastnpc.api.auth import _get_conn, load_character_full_data, load_character_memories
import json

conn = _get_conn()
cur = conn.cursor()

# 查询赵云
cur.execute('SELECT id, name FROM characters WHERE name LIKE %s', ('%赵云%',))
row = cur.fetchone()
char_id, name = row[0], row[1]

print(f'角色: {name} (ID: {char_id})')
print('=' * 60)

# 加载完整数据
data = load_character_full_data(char_id)
if data:
    print(f'基础信息: {\"✅\" if \"基础身份信息\" in data else \"❌\"}')
    print(f'知识能力: {\"✅\" if \"知识与能力\" in data else \"❌\"}')
    print(f'性格行为: {\"✅\" if \"个性与行为设定\" in data else \"❌\"}')

# 加载记忆
memories = load_character_memories(char_id)
if memories:
    stm = len(memories.get('short_term_memory', []))
    ltm = len(memories.get('long_term_memory', []))
    print(f'短期记忆: {stm} 条')
    print(f'长期记忆: {ltm} 条')

conn.close()
"
```

---

## ✅ 验证完成标准

### 核心功能（必须通过）：
- [x] 数据库连接正常
- [x] 所有表结构完整
- [x] 角色创建和数据保存
- [ ] 单角色对话功能
- [ ] 对话历史保存和加载
- [ ] 群聊功能

### 扩展功能（建议通过）：
- [ ] 记忆压缩功能
- [ ] 管理员查看功能
- [ ] 反馈功能
- [ ] 级联删除功能

---

## 🐛 常见问题

### 问题1: 对话无法开始
**原因**: 角色数据未正确从数据库加载

**解决**:
```bash
# 检查角色数据
python3 -c "
from fastnpc.api.auth import load_character_full_data
data = load_character_full_data(7)  # 赵云的ID
print('数据加载:', '成功' if data else '失败')
"
```

### 问题2: 记忆未保存到数据库
**原因**: 记忆压缩阈值未达到

**解决**: 发送更多消息（>20条）触发自动压缩

### 问题3: 群聊角色不发言
**原因**: 角色数据加载失败

**解决**: 检查 `fastnpc/core/group_chat.py` 中的角色加载逻辑

---

## 📞 需要帮助？

如果遇到问题：
1. 先运行 `python test_postgresql_migration.py` 查看自动化测试结果
2. 查看服务器日志: `tail -100 server.log`
3. 检查PostgreSQL日志: `sudo tail -100 /var/log/postgresql/postgresql-16-main.log`

---

**最后更新**: 2025-10-17
**版本**: PostgreSQL Migration v1.0

