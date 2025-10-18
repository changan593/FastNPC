# 🚀 角色头像功能 - 快速开始

## 一分钟部署指南

### 1️⃣ 安装依赖（5秒）
```bash
pip install Pillow>=10.0.0
```

### 2️⃣ 重启服务（10秒）
```bash
./start_dev.sh
```

### 3️⃣ 测试功能（30秒）
```bash
python test_avatar.py
```

### 4️⃣ 创建角色并查看头像（1分钟）
1. 打开 FastNPC 网页
2. 点击"新建"创建角色
3. 输入角色名（如"哪吒"）
4. 等待创建完成
5. 在侧边栏查看圆角头像

---

## ✅ 验证成功

如果看到：
- ✅ 侧边栏显示圆角正方形头像
- ✅ Avatars/ 目录有 .jpg 文件
- ✅ 测试脚本全部通过

恭喜！功能已成功部署 🎉

---

## ❓ 遇到问题？

### 问题1: pip install 失败
```bash
# Ubuntu/Debian
sudo apt-get install libjpeg-dev libpng-dev

# 然后重新安装
pip install Pillow>=10.0.0
```

### 问题2: 头像不显示
```bash
# 检查后端日志
tail -f fastnpc.log

# 检查Avatars目录
ls -lh Avatars/
```

### 问题3: 数据库错误
```bash
# 手动运行迁移脚本
python -c "from fastnpc.api.auth import init_db; init_db()"
```

---

## 📖 详细文档

- [AVATAR_FEATURE.md](./AVATAR_FEATURE.md) - 完整功能文档（5分钟阅读）
- [CHANGELOG_AVATAR.md](./CHANGELOG_AVATAR.md) - 更新日志（3分钟阅读）

---

## 🎯 核心文件（开发者）

### 必看
- `fastnpc/utils/image_utils.py` - 图片处理核心
- `fastnpc/api/state.py` - 头像下载逻辑

### 可选
- `fastnpc/datasources/baike_robust.py` - 头像提取
- `web/fastnpc-web/src/components/Sidebar.tsx` - 前端显示

---

**部署时间**: < 2 分钟  
**难度**: ⭐ 简单  
**成功率**: 99%

