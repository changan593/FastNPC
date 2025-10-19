# FastNPC 部署指南

## 前置要求

### 服务器环境
- Ubuntu 20.04+ 或 CentOS 7+
- Python 3.10+
- PostgreSQL 13+ 或 SQLite
- Redis 6+
- Node.js 18+
- Nginx (可选，用于反向代理)

### 最小配置
- CPU: 2核
- 内存: 4GB
- 硬盘: 20GB

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/FastNPC.git
cd FastNPC
```

### 2. 配置环境变量

```bash
cp env.example .env
nano .env
```

**必须配置的变量**：
```bash
# OpenRouter API密钥
OPENROUTER_API_KEY=your_api_key_here

# 数据库配置（PostgreSQL）
USE_POSTGRESQL=true
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fastnpc
POSTGRES_USER=fastnpc
POSTGRES_PASSWORD=your_strong_password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 连接池配置（可选，已优化）
DB_POOL_MIN_CONN=10
DB_POOL_MAX_CONN=50
```

### 3. 安装数据库

#### PostgreSQL (推荐)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib

# 创建数据库和用户
sudo -u postgres psql
```

在PostgreSQL中执行：
```sql
CREATE DATABASE fastnpc;
CREATE USER fastnpc WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE fastnpc TO fastnpc;
\q
```

#### Redis
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 4. 安装Python依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 5. 初始化数据库

```bash
# 初始化数据库结构
python -c "from fastnpc.api.auth.db_init import init_db; init_db()"

# 初始化提示词（可选但推荐）
python fastnpc/scripts/init_prompts.py
python fastnpc/scripts/init_evaluation_prompts.py
```

### 6. 构建前端

```bash
cd web/fastnpc-web
npm install
npm run build
cd ../..
```

### 7. 配置systemd服务

```bash
# 复制服务文件
sudo cp fastnpc.service /etc/systemd/system/
sudo nano /etc/systemd/system/fastnpc.service

# 修改以下路径为实际路径：
# - WorkingDirectory
# - ExecStart (venv路径)
# - User

# 重载并启动服务
sudo systemctl daemon-reload
sudo systemctl enable fastnpc
sudo systemctl start fastnpc
```

### 8. 配置Nginx（可选）

创建 `/etc/nginx/sites-available/fastnpc`：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    # 前端静态文件
    location / {
        root /path/to/FastNPC/web/fastnpc-web/dist;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /admin {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket支持（如果需要）
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/fastnpc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. 创建管理员账号

```bash
# 启动Python shell
python

# 执行以下代码
from fastnpc.api.auth import register_user
register_user("admin", "your_secure_password", is_admin=True)
exit()
```

### 10. 验证部署

```bash
# 检查服务状态
sudo systemctl status fastnpc

# 查看日志
sudo journalctl -u fastnpc -f

# 测试API
curl http://localhost:8000/api/health
```

访问 `http://your_domain.com` 应该看到前端界面。

## 常用命令

### 服务管理
```bash
# 启动服务
sudo systemctl start fastnpc

# 停止服务
sudo systemctl stop fastnpc

# 重启服务
sudo systemctl restart fastnpc

# 查看状态
sudo systemctl status fastnpc

# 查看日志
sudo journalctl -u fastnpc -f
```

### 数据库管理
```bash
# 备份数据库
pg_dump -U fastnpc fastnpc > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -U fastnpc fastnpc < backup_20231019.sql

# 查看连接池状态
python fastnpc/scripts/monitor_pool.py --mode status
```

### 更新部署
```bash
# 拉取最新代码
git pull origin main

# 更新Python依赖
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 重新构建前端
cd web/fastnpc-web
npm install
npm run build
cd ../..

# 重启服务
sudo systemctl restart fastnpc
```

## 故障排除

### 连接池耗尽
查看 `docs/CONNECTION_POOL_QUICK_FIX.md`

### 数据库连接失败
1. 检查PostgreSQL是否运行：`sudo systemctl status postgresql`
2. 检查连接配置：`.env` 文件中的数据库配置
3. 检查防火墙：`sudo ufw status`

### Redis连接失败
1. 检查Redis状态：`sudo systemctl status redis-server`
2. 测试连接：`redis-cli ping`

### 前端无法访问API
1. 检查Nginx配置
2. 检查FastNPC服务状态
3. 查看日志：`sudo journalctl -u fastnpc -f`

### OpenRouter API错误
1. 检查API密钥是否正确
2. 检查账户余额
3. 查看错误日志

## 性能优化

### 数据库优化
```sql
-- 创建索引（如果未自动创建）
CREATE INDEX IF NOT EXISTS idx_characters_user_id ON characters(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_character_id ON messages(character_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category);
```

### Redis优化
```bash
# /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Gunicorn优化
修改 `gunicorn_conf.py`：
```python
workers = 4  # CPU核心数 * 2 + 1
worker_class = 'uvicorn.workers.UvicornWorker'
timeout = 120
keepalive = 5
```

## 安全建议

1. **使用HTTPS**
   - 配置Let's Encrypt SSL证书
   - `sudo certbot --nginx -d your_domain.com`

2. **防火墙配置**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **定期备份**
   - 设置cron定时备份数据库
   - 备份用户上传的头像和数据

4. **监控**
   - 使用 `fastnpc/scripts/monitor_pool.py` 监控连接池
   - 设置日志轮转
   - 配置告警通知

## 开发环境部署

简化的开发环境部署：

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd web/fastnpc-web && npm install && cd ../..

# 2. 配置 .env（使用SQLite）
cp env.example .env
# 修改 USE_POSTGRESQL=false

# 3. 初始化数据库
python -c "from fastnpc.api.auth.db_init import init_db; init_db()"

# 4. 启动开发服务器
./start_dev.sh
```

前端开发服务器会自动代理API请求到后端。

## 文档

- 数据库管理：`docs/DATABASE_MANAGEMENT.md`
- 连接池问题：`docs/CONNECTION_POOL_QUICK_FIX.md`
- 测试系统：`docs/TEST_SYSTEM_GUIDE.md`
- 提示词管理：`docs/prompt-management-guide.md`
- 快速开始：`docs/QUICK_START_PROMPTS.md`

## 技术支持

如有问题，请查看：
1. 项目文档（docs目录）
2. GitHub Issues
3. 日志文件：`sudo journalctl -u fastnpc -f`

## 更新日期

2025-10-19

