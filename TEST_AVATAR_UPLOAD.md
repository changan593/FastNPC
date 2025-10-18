# ✅ 头像上传功能测试清单

## 快速测试

### 1️⃣ 访问角色配置页面

```bash
# 方式1: 从React前端
http://localhost:5173/
→ 右键点击角色 → 管理 → 打开角色配置页面

# 方式2: 直接访问
http://localhost:8000/structured/view?role=孙悟空202510181802
```

### 2️⃣ 测试上传

- [ ] 点击头像区域，选择图片上传
- [ ] 拖拽图片到头像区域上传
- [ ] 上传JPG图片
- [ ] 上传PNG图片（测试透明背景处理）
- [ ] 上传非正方形图片（测试自动裁剪）

### 3️⃣ 测试显示

- [ ] 上传成功后，头像立即显示
- [ ] 关闭页面，从侧边栏看到新头像
- [ ] 刷新页面，头像依然显示

### 4️⃣ 测试删除

- [ ] 点击"删除"按钮
- [ ] 确认删除对话框
- [ ] 头像恢复为默认图标（👤）
- [ ] 侧边栏也恢复默认图标

### 5️⃣ 测试边界情况

- [ ] 上传超大文件（>10MB），应该提示错误
- [ ] 上传非图片文件，应该提示错误
- [ ] 快速连续上传，应该正常处理

### 6️⃣ 测试缓存

- [ ] 上传头像后，强制刷新浏览器（Ctrl+Shift+R）
- [ ] 应该显示新头像（不是旧的）

---

## 📋 测试结果

### 预期行为

#### 上传成功
```
✅ 状态显示: "上传中..." → "上传成功！"
✅ 头像立即更新
✅ "删除"按钮出现
✅ 文件保存在 Avatars/ 目录
✅ 数据库 avatar_url 字段更新
```

#### 删除成功
```
✅ 状态显示: "删除中..." → "已删除"
✅ 显示默认图标（👤）
✅ "删除"按钮隐藏
✅ 文件从 Avatars/ 目录删除
✅ 数据库 avatar_url 字段清空
```

---

## 🐛 如何调试

### 后端日志
```bash
tail -f /home/changan/MyProject/FastNPC/server.log
```

### 浏览器控制台
按 F12 → Console 标签，查看JavaScript错误

### 网络请求
按 F12 → Network 标签，筛选：
- `avatar` - 查看上传/删除请求
- `jpg` - 查看图片加载

### 数据库检查
```bash
PGPASSWORD=fastnpc123 psql -h localhost -U fastnpc -d fastnpc -c \
  "SELECT name, avatar_url FROM characters WHERE name LIKE '%孙悟空%';"
```

### 文件系统检查
```bash
ls -lh /home/changan/MyProject/FastNPC/Avatars/
```

---

## 🎯 已知功能

- ✅ 自动裁剪为正方形
- ✅ 自动缩放到256x256
- ✅ 支持拖拽上传
- ✅ 支持点击上传
- ✅ 实时预览
- ✅ 文件类型验证
- ✅ 文件大小验证
- ✅ 透明背景转换
- ✅ JPEG优化
- ✅ 数据库同步
- ✅ 缓存清除
- ✅ 错误提示

---

## 📞 遇到问题？

### 问题1: 上传失败
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 检查Avatars目录权限
ls -la /home/changan/MyProject/FastNPC/Avatars/

# 查看错误日志
tail -50 /home/changan/MyProject/FastNPC/server.log
```

### 问题2: 图片不显示
```bash
# 检查图片是否存在
ls /home/changan/MyProject/FastNPC/Avatars/*.jpg

# 检查数据库
PGPASSWORD=fastnpc123 psql -h localhost -U fastnpc -d fastnpc -c \
  "SELECT name, avatar_url FROM characters LIMIT 5;"

# 测试图片访问
curl -I http://localhost:8000/avatars/user_5_角色名.jpg
```

### 问题3: 侧边栏不更新
```bash
# 清除浏览器缓存
Ctrl+Shift+Delete → 清除缓存

# 强制刷新
Ctrl+Shift+R

# 清除Redis缓存
redis-cli -h localhost -p 6379 FLUSHALL
```

---

**状态**: ✅ 所有功能已实现  
**测试**: 📋 待用户测试  
**文档**: 📚 已完成

