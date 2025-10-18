# 角色头像功能说明

## ✨ 功能概述

FastNPC 现在支持从数据源（如百度百科）自动抓取角色图片作为头像，并在界面中以圆角正方形的形式展示。

## 🎯 功能特性

### 1. 自动抓取头像
- 在创建角色时，系统会自动从百度百科页面抓取角色图片
- 使用CSS选择器 `#side > div.abstractAlbum_jhNeu > img` 等多种选择器提取图片
- 支持多种备用选择器，提高抓取成功率

### 2. 图片处理
- 自动裁剪为正方形（中心裁剪）
- 统一调整为 256x256 像素
- 转换为 JPEG 格式，优化存储空间（quality=85）
- 自动处理透明背景（转换为白色背景）

### 3. 存储与展示
- 头像保存在 `Avatars/` 目录
- 文件命名格式：`user_{用户ID}_{角色名}.jpg`
- 在侧边栏显示为 40x40 像素的圆角正方形
- 如果没有头像，显示默认图标（👤）

## 📂 文件结构

```
FastNPC/
├── Avatars/                          # 头像存储目录（自动创建）
│   ├── user_1_哪吒.jpg
│   └── user_1_孙悟空.jpg
├── fastnpc/
│   ├── utils/
│   │   └── image_utils.py           # 图片处理工具模块 ⭐ 新增
│   ├── datasources/
│   │   └── baike_robust.py          # 百度百科爬虫（已修改，添加头像提取）
│   └── api/
│       ├── server.py                 # 添加了 /avatars 静态文件服务
│       ├── state.py                  # 角色创建流程（添加头像下载逻辑）
│       ├── utils.py                  # 角色列表API（添加avatar_url字段）
│       └── auth/
│           ├── db_init.py            # 数据库表（添加avatar_url字段）
│           └── char_data.py          # 角色数据操作（支持avatar_url）
└── web/fastnpc-web/src/
    ├── types.ts                      # 类型定义（添加avatar_url字段）
    └── components/
        └── Sidebar.tsx               # 侧边栏（显示圆角正方形头像）⭐ 修改
```

## 🔧 技术实现

### 后端

#### 1. 数据库变更
```sql
ALTER TABLE characters ADD COLUMN avatar_url TEXT;
```

#### 2. 图片处理（`fastnpc/utils/image_utils.py`）
```python
download_and_crop_avatar(
    image_url: str,      # 图片URL
    save_dir: str,       # 保存目录
    filename: str,       # 文件名（不含扩展名）
    size: (256, 256),    # 目标尺寸
    timeout: 15          # 下载超时（秒）
) -> Optional[str]       # 返回保存的文件名
```

主要步骤：
1. 下载图片（带 Referer 防反爬）
2. 使用 Pillow 加载图片
3. 处理透明通道（转为白色背景）
4. 中心裁剪为正方形
5. 调整尺寸为 256x256
6. 保存为 JPEG（quality=85）

#### 3. 爬虫集成（`fastnpc/datasources/baike_robust.py`）
在 `_parse_html_content` 函数中添加头像提取逻辑：
```python
# 尝试多种选择器提取头像
avatar_selectors = [
    '#side div.abstractAlbum_jhNeu img',
    'div.abstractAlbum_jhNeu img',
    'div.summary-pic img',
    'div.lemma-summary img',
    '#side img',
]
```

#### 4. 角色创建流程（`fastnpc/api/state.py`）
```python
# 处理头像（如果有）
if raw_data.get('avatar_url'):
    avatar_saved = download_and_crop_avatar(
        image_url=raw_data['avatar_url'],
        save_dir=avatar_dir,
        filename=f"user_{user_id}_{role}",
        size=(256, 256),
        timeout=15
    )
    if avatar_saved:
        avatar_saved_path = f"/avatars/{avatar_saved}"
```

#### 5. API 返回（`fastnpc/api/utils.py`）
角色列表API现在包含 `avatar_url` 字段：
```json
{
  "items": [
    {
      "role": "哪吒",
      "path": "db://characters/123",
      "updated_at": 1234567890,
      "preview": "哪吒，中国古代神话传说人物...",
      "avatar_url": "/avatars/user_1_哪吒.jpg"
    }
  ]
}
```

### 前端

#### 1. 类型定义（`types.ts`）
```typescript
export interface CharacterItem {
  role: string;
  path: string;
  updated_at: number;
  preview?: string;
  avatar_url?: string;  // ⭐ 新增
}
```

#### 2. 侧边栏显示（`Sidebar.tsx`）
```tsx
{item.type === 'character' && item.data.avatar_url ? (
  <div 
    className="avatar" 
    style={{ 
      width: 40, 
      height: 40, 
      borderRadius: 8,  // 圆角正方形
      overflow: 'hidden',
      marginRight: 12,
      flexShrink: 0
    }}
  >
    <img 
      src={item.data.avatar_url} 
      alt={item.name}
      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
    />
  </div>
) : null}
```

## 📦 依赖项

### 新增依赖
在 `requirements.txt` 中添加：
```
Pillow>=10.0.0
```

### 安装依赖
```bash
pip install Pillow>=10.0.0
```

## 🚀 部署步骤

### 1. 更新代码
```bash
git pull
```

### 2. 安装新依赖
```bash
pip install -r requirements.txt
```

### 3. 数据库迁移
系统会在启动时自动检测并添加 `avatar_url` 字段，无需手动操作。

如果需要手动迁移，可以执行：
```bash
# PostgreSQL
psql -U your_user -d your_db -f migrations/add_avatar_url.sql

# SQLite
sqlite3 your_database.db < migrations/add_avatar_url.sql
```

### 4. 重启服务
```bash
# 如果使用 start_dev.sh
./start_dev.sh

# 或者直接运行
python -m fastnpc.api.server
```

### 5. 前端重新构建（如果修改了前端代码）
```bash
cd web/fastnpc-web
npm install
npm run build
```

## 🎨 样式说明

### 头像显示样式
- **尺寸**: 40x40 像素（侧边栏）
- **形状**: 圆角正方形（`borderRadius: 8px`）
- **对齐**: 左对齐，右侧显示角色名称和时间
- **回退**: 如果没有头像，显示 👤 图标

### 支持的图片格式
- 输入：JPEG, PNG, GIF, WebP 等（Pillow 支持的格式）
- 输出：JPEG（统一格式，体积优化）
- 透明背景自动转换为白色背景

## 🔍 故障排查

### 1. 头像未显示
**可能原因**：
- 百度百科页面没有图片
- 图片下载失败（网络问题）
- 图片URL提取失败（页面结构变化）

**解决方法**：
- 查看后端日志，确认是否有图片URL提取成功的日志
- 检查 `Avatars/` 目录是否有对应文件
- 如果是网络问题，可以手动下载图片并放到 `Avatars/` 目录

### 2. 头像显示模糊
**原因**：原始图片分辨率较低

**解决方法**：
- 目标尺寸设置为 256x256，足够清晰
- 可以手动替换更高清的图片

### 3. Pillow 安装失败
**可能原因**：缺少系统依赖

**解决方法**：
```bash
# Ubuntu/Debian
sudo apt-get install libjpeg-dev libpng-dev

# CentOS/RHEL
sudo yum install libjpeg-devel libpng-devel

# macOS
brew install libjpeg libpng
```

### 4. 头像文件占用空间过大
**解决方法**：
- 系统已自动优化（JPEG quality=85）
- 每个头像约 10-50KB
- 定期清理不再使用的头像文件

## 📊 性能影响

### 存储空间
- 每个头像约 10-50KB
- 1000个角色约占用 10-50MB

### 网络带宽
- 首次加载头像时需要下载
- 浏览器会自动缓存
- 建议配置 CDN 加速

### 创建角色时间
- 增加约 2-5 秒（图片下载和处理）
- 异步处理，不阻塞主流程
- 如果下载失败，不影响角色创建

## 🔐 安全考虑

### 1. 文件命名
- 使用固定格式：`user_{user_id}_{role}.jpg`
- 防止路径遍历攻击

### 2. 文件大小限制
- 下载超时：15秒
- 目标尺寸固定：256x256
- 格式统一：JPEG

### 3. 静态文件服务
- 使用 FastAPI 的 StaticFiles
- 仅允许访问 `/avatars/` 目录
- 不允许目录列表

## 📝 未来优化方向

### 1. 手动上传头像
- 允许用户手动上传自定义头像
- 添加头像编辑功能（裁剪、旋转）

### 2. CDN 加速
- 将头像上传到 OSS（如阿里云、腾讯云）
- 使用 CDN 加速访问

### 3. 智能裁剪
- 使用人脸识别自动定位裁剪区域
- 提高头像质量

### 4. 多尺寸支持
- 生成多种尺寸的缩略图
- 响应式加载（移动端加载小尺寸）

### 5. 缓存优化
- 使用 Redis 缓存头像URL
- 减少数据库查询

## ✅ 测试清单

- [ ] 创建新角色时，头像自动抓取并显示
- [ ] 复制角色时，头像一起复制
- [ ] 重命名角色时，头像保持不变
- [ ] 删除角色时，头像文件是否需要清理（待定）
- [ ] 没有头像的角色显示默认图标
- [ ] 头像显示为圆角正方形
- [ ] 头像在不同分辨率下显示正常
- [ ] 侧边栏头像大小适中，不遮挡文字
- [ ] 数据库迁移成功添加 avatar_url 字段
- [ ] Avatars 目录权限正确，可读写

## 📚 相关文件

### 后端
- `fastnpc/utils/image_utils.py` - 图片处理工具 ⭐ 新增
- `fastnpc/datasources/baike_robust.py` - 头像URL提取
- `fastnpc/api/state.py` - 角色创建流程
- `fastnpc/api/server.py` - 静态文件服务
- `fastnpc/api/utils.py` - 角色列表API
- `fastnpc/api/auth/db_init.py` - 数据库表定义
- `fastnpc/api/auth/char_data.py` - 角色数据操作
- `fastnpc/api/routes/character_routes.py` - 角色复制功能

### 前端
- `web/fastnpc-web/src/types.ts` - 类型定义
- `web/fastnpc-web/src/components/Sidebar.tsx` - 头像显示 ⭐ 修改

### 配置
- `requirements.txt` - 添加 Pillow 依赖
- `migrations/add_avatar_url.sql` - 数据库迁移脚本 ⭐ 新增

## 💡 使用提示

1. **首次部署**：记得安装 Pillow 依赖并重启服务
2. **已有角色**：需要重新创建才会有头像，或手动添加头像文件
3. **百度百科**：如果页面结构变化，可能需要更新选择器
4. **网络问题**：可以在 `image_utils.py` 中配置代理
5. **头像替换**：直接替换 `Avatars/` 目录中的文件即可（需清除缓存）

---

**开发日期**: 2025-10-18  
**版本**: 1.0.0  
**负责人**: FastNPC Team

