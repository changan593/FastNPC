# 🎨 角色头像功能 - 更新日志

## 版本信息
- **更新日期**: 2025-10-18
- **版本号**: v1.1.0
- **功能**: 角色头像自动抓取与展示

---

## 📝 更新内容

### ✨ 新增功能

1. **自动抓取头像**
   - 创建角色时自动从百度百科抓取角色图片
   - 支持多种CSS选择器，提高抓取成功率
   - 智能回退机制，优先使用高质量图片

2. **图片智能处理**
   - 自动裁剪为正方形（中心裁剪）
   - 统一调整为256x256像素
   - 转换为JPEG格式优化存储
   - 自动处理透明背景

3. **界面美化**
   - 侧边栏显示40x40圆角正方形头像
   - 头像与角色信息并排显示
   - 无头像时显示默认图标（👤）

4. **数据持久化**
   - 头像URL存储在数据库
   - 头像文件保存在Avatars目录
   - 支持角色复制时头像同步复制

---

## 🔧 技术变更

### 数据库变更
```sql
-- characters 表新增字段
ALTER TABLE characters ADD COLUMN avatar_url TEXT;
```

### 新增文件

#### 后端
- `fastnpc/utils/image_utils.py` - 图片处理工具模块
  - `download_and_crop_avatar()` - 下载、裁剪、保存头像
  - `extract_baike_avatar_url()` - 从HTML提取头像URL

- `migrations/add_avatar_url.sql` - 数据库迁移脚本

- `test_avatar.py` - 头像功能测试脚本

- `AVATAR_FEATURE.md` - 完整功能文档

- `CHANGELOG_AVATAR.md` - 本更新日志

#### 前端
无新增文件，仅修改现有文件

### 修改文件

#### 后端（Python）
| 文件路径 | 修改内容 | 行数 |
|---------|---------|------|
| `requirements.txt` | 添加 Pillow>=10.0.0 依赖 | +1 |
| `fastnpc/api/auth/db_init.py` | 添加 avatar_url 字段到数据库表定义 | +16 |
| `fastnpc/datasources/baike_robust.py` | 添加头像URL提取逻辑 | +35 |
| `fastnpc/api/state.py` | 角色创建时下载并保存头像 | +28 |
| `fastnpc/api/auth/char_data.py` | save/load 函数支持 avatar_url | +15 |
| `fastnpc/api/utils.py` | 角色列表API返回 avatar_url | +5 |
| `fastnpc/api/routes/character_routes.py` | 复制角色时同步复制头像 | +28 |
| `fastnpc/api/server.py` | 挂载 /avatars 静态文件服务 | +8 |

#### 前端（TypeScript/TSX）
| 文件路径 | 修改内容 | 行数 |
|---------|---------|------|
| `web/fastnpc-web/src/types.ts` | CharacterItem 接口添加 avatar_url 字段 | +1 |
| `web/fastnpc-web/src/components/Sidebar.tsx` | 显示圆角正方形头像 | +26 |

---

## 📦 依赖变更

### 新增依赖
```python
Pillow>=10.0.0  # 图片处理库
```

### 安装命令
```bash
pip install Pillow>=10.0.0
```

---

## 🚀 部署步骤

### 1. 更新代码
```bash
cd /home/changan/MyProject/FastNPC
git pull  # 或拉取最新代码
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 数据库迁移（自动）
启动服务时会自动检测并添加 `avatar_url` 字段，无需手动操作。

### 4. 创建头像目录（自动）
服务启动时会自动创建 `Avatars/` 目录，无需手动创建。

### 5. 重启服务
```bash
# 使用启动脚本
./start_dev.sh

# 或直接运行
uvicorn fastnpc.api.server:app --reload --host 0.0.0.0 --port 8000
```

### 6. 测试功能
```bash
# 运行测试脚本
python test_avatar.py
```

### 7. 前端重新构建（可选）
如果前端代码有更新：
```bash
cd web/fastnpc-web
npm install
npm run build
```

---

## 🧪 测试清单

运行测试脚本：
```bash
python test_avatar.py
```

手动测试：
- [ ] 创建新角色，确认头像正确抓取和显示
- [ ] 复制角色，确认头像一起复制
- [ ] 重命名角色，确认头像保持不变
- [ ] 删除角色后，前端不再显示该头像
- [ ] 没有头像的角色显示默认图标（👤）
- [ ] 头像显示为圆角正方形
- [ ] 侧边栏布局正常，头像不遮挡文字

---

## 📊 性能影响

### 存储空间
- 每个头像约 10-50KB
- 1000个角色约占用 10-50MB

### 创建角色时间
- 增加约 2-5 秒（图片下载和处理）
- 异步处理，不阻塞主流程
- 下载失败不影响角色创建

### API响应时间
- 角色列表API增加 avatar_url 字段（~50字节）
- 静态文件服务（/avatars）不影响API性能

---

## 🔍 常见问题

### Q1: 为什么有些角色没有头像？
**A**: 可能原因：
- 百度百科页面没有图片
- 图片下载失败（网络问题）
- 页面结构变化导致选择器失效

**解决方法**：
- 查看后端日志确认错误原因
- 检查 Avatars/ 目录是否有文件
- 可以手动添加头像文件

### Q2: 如何手动添加或替换头像？
**A**: 
1. 准备一张图片（任意尺寸）
2. 重命名为 `user_{用户ID}_{角色名}.jpg`
3. 放入 `Avatars/` 目录
4. 刷新前端页面

### Q3: 头像显示模糊怎么办？
**A**: 
- 系统自动处理为 256x256，显示40x40，不应模糊
- 如果模糊，可能是原图质量差
- 手动替换更高清的图片

### Q4: Pillow 安装失败？
**A**: 
可能缺少系统依赖，先安装：
```bash
# Ubuntu/Debian
sudo apt-get install libjpeg-dev libpng-dev

# CentOS/RHEL
sudo yum install libjpeg-devel libpng-devel

# macOS
brew install libjpeg libpng
```

### Q5: 已有角色如何添加头像？
**A**: 
需要重新创建角色，或手动添加头像文件到 Avatars/ 目录。

---

## 🔐 安全性

### 文件安全
- 文件名固定格式，防止路径遍历
- 统一转换为JPEG格式
- 文件大小控制（256x256）

### 网络安全
- 下载超时限制（15秒）
- 仅从可信数据源下载
- 静态文件服务仅限 /avatars 目录

---

## 🐛 已知问题

无已知问题。

---

## 🎯 未来计划

### v1.2.0（计划）
- [ ] 手动上传自定义头像
- [ ] 头像编辑功能（裁剪、旋转）
- [ ] 多尺寸头像支持

### v1.3.0（计划）
- [ ] OSS 存储支持（阿里云、腾讯云）
- [ ] CDN 加速
- [ ] 智能人脸识别裁剪

### v2.0.0（计划）
- [ ] 头像动画支持
- [ ] 头像框架/装饰
- [ ] 头像成就系统

---

## 📚 相关文档

- [AVATAR_FEATURE.md](./AVATAR_FEATURE.md) - 完整功能文档
- [migrations/add_avatar_url.sql](./migrations/add_avatar_url.sql) - 数据库迁移脚本
- [test_avatar.py](./test_avatar.py) - 测试脚本

---

## 👥 贡献者

- **开发**: FastNPC Team
- **测试**: [待补充]
- **设计**: [待补充]

---

## 📞 支持

如有问题，请：
1. 查看 [AVATAR_FEATURE.md](./AVATAR_FEATURE.md) 详细文档
2. 运行 `python test_avatar.py` 诊断问题
3. 查看后端日志（`fastnpc/api/server.py` 输出）
4. 提交 Issue 或 Pull Request

---

**版本**: v1.1.0  
**更新日期**: 2025-10-18  
**状态**: ✅ 已发布

