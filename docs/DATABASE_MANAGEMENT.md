# 数据库管理工具使用指南

## 🎯 使用Adminer访问PostgreSQL数据库

### 方法一：Docker方式（推荐）

#### 1. 启动Adminer容器

```bash
docker run -d \
  --name fastnpc-adminer \
  --network host \
  -p 8080:8080 \
  adminer:latest
```

#### 2. 访问Web界面

在浏览器中打开：
```
http://localhost:8080/
```

#### 3. 填写连接信息

在Adminer登录界面填写：

- **系统**: PostgreSQL
- **服务器**: `localhost` 或 `127.0.0.1`
- **用户名**: `fastnpc`
- **密码**: 您的数据库密码（参考 `fastnpc/config.py` 中的 `PG_PASSWORD`）
- **数据库**: `fastnpc`

#### 4. 直接访问（URL方式）

也可以通过URL直接携带参数访问：

```
http://localhost:8080/?pgsql=localhost&username=fastnpc&db=fastnpc&ns=public&select=characters
```

参数说明：
- `pgsql=localhost` - PostgreSQL服务器地址
- `username=fastnpc` - 用户名
- `db=fastnpc` - 数据库名
- `ns=public` - Schema（通常是public）
- `select=characters` - 直接打开characters表

#### 5. 停止和删除容器

```bash
# 停止容器
docker stop fastnpc-adminer

# 删除容器
docker rm fastnpc-adminer
```

---

### 方法二：独立安装Adminer

#### 1. 下载Adminer

```bash
cd /tmp
wget https://github.com/vrana/adminer/releases/download/v4.8.1/adminer-4.8.1.php
```

#### 2. 使用PHP内置服务器运行

```bash
php -S localhost:8080 adminer-4.8.1.php
```

#### 3. 访问

浏览器打开：`http://localhost:8080/adminer-4.8.1.php`

---

### 方法三：使用pgAdmin（推荐用于复杂操作）

#### 1. 安装pgAdmin

##### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install pgadmin4
```

##### Docker方式:
```bash
docker run -d \
  --name pgadmin \
  -p 5050:80 \
  -e "PGADMIN_DEFAULT_EMAIL=admin@fastnpc.local" \
  -e "PGADMIN_DEFAULT_PASSWORD=admin" \
  dpage/pgadmin4:latest
```

#### 2. 访问pgAdmin

- Docker方式：`http://localhost:5050`
- 桌面版：从应用菜单启动

#### 3. 添加服务器连接

1. 右键点击 "Servers" → "Register" → "Server"
2. 填写连接信息：
   - **Name**: FastNPC Database
   - **Host**: localhost
   - **Port**: 5432
   - **Username**: fastnpc
   - **Password**: （您的数据库密码）
   - **Database**: fastnpc

---

## 🔍 常用查询

### 查看所有角色

```sql
SELECT id, name, created_by, created_at, is_test_case 
FROM characters 
ORDER BY created_at DESC;
```

### 查看所有群聊

```sql
SELECT gc.id, gc.group_name, gc.created_by, gc.is_test_case,
       COUNT(gm.character_id) as member_count
FROM group_chats gc
LEFT JOIN group_members gm ON gc.id = gm.group_chat_id
GROUP BY gc.id
ORDER BY gc.created_at DESC;
```

### 查看提示词版本

```sql
SELECT category, sub_category, version, is_active, 
       LENGTH(template_content) as content_length,
       created_at
FROM prompt_templates
WHERE category = 'SYSTEM_PROMPT'
ORDER BY created_at DESC;
```

### 查看测试用例

```sql
SELECT id, category, target_type, target_id, name, 
       version, is_active, created_at
FROM test_cases
ORDER BY created_at DESC;
```

### 查看用户信息

```sql
SELECT id, username, email, is_admin, created_at 
FROM users 
ORDER BY created_at;
```

---

## 📊 数据库性能监控

### 查看表大小

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 查看索引使用情况

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

### 查看慢查询

```sql
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

---

## 🔐 安全提示

1. **生产环境**: 不要在生产环境暴露Adminer到公网
2. **访问控制**: 使用防火墙限制只能从本地访问8080端口
3. **强密码**: 确保数据库使用强密码
4. **定期备份**: 定期备份数据库

### 创建数据库备份

```bash
# 使用pg_dump备份
pg_dump -h localhost -U fastnpc -d fastnpc > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
psql -h localhost -U fastnpc -d fastnpc < backup_20251019_120000.sql
```

---

## 📝 配置文件位置

FastNPC数据库配置位于：`fastnpc/config.py`

关键配置项：
- `USE_POSTGRESQL` - 是否使用PostgreSQL（True）或SQLite（False）
- `PG_HOST` - PostgreSQL服务器地址
- `PG_PORT` - PostgreSQL端口（默认5432）
- `PG_USER` - 数据库用户名
- `PG_PASSWORD` - 数据库密码
- `PG_DATABASE` - 数据库名称

---

## 🆘 常见问题

### Q1: 无法连接到数据库

**检查项**:
1. PostgreSQL服务是否运行: `sudo systemctl status postgresql`
2. 端口是否开放: `sudo netstat -tlnp | grep 5432`
3. 配置文件中的密码是否正确
4. 用户权限是否足够

### Q2: Adminer显示"Extension not available"

**解决方案**:
```bash
# 安装PostgreSQL扩展
sudo apt install php-pgsql
```

### Q3: 权限被拒绝

**解决方案**:
检查PostgreSQL的 `pg_hba.conf` 文件，确保允许本地连接：
```
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
```

然后重启PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## 🎨 Adminer主题和插件

Adminer支持自定义主题和插件，提升使用体验。

### 安装美化主题

1. 下载主题：https://www.adminer.org/en/extension/
2. 将主题文件放在与adminer.php同目录
3. 访问时自动应用

### 常用插件

- **Dump Zip** - 导出为ZIP压缩包
- **Login IP** - 记住服务器IP
- **Pretty JSON** - 美化显示JSON数据
- **Tables Filter** - 表过滤功能


