# 推送和部署指南

## ✅ 项目清理已完成

项目已经完成清理，准备推送到GitHub并部署到生产环境。

## 📊 清理统计

- **删除文件**: 18个临时文档和测试脚本
- **归档文档**: 10个开发过程文档
- **新增文件**: 3个核心文档（部署指南、连接池快速修复、清理总结）
- **代码优化**: 修复连接池泄漏bug，优化连接池配置
- **净减少**: 8152行 - 914行 = 7238行代码和文档

## 🔍 推送前最后检查

### 1. 检查Git状态
```bash
cd /home/changan/MyProject/FastNPC
git status
```

✅ 应该显示：`Your branch is ahead of 'origin/main' by 23 commits.`

### 2. 确认敏感文件已排除
```bash
# 检查.env文件状态
git ls-files | grep "\.env$"

# 应该返回空（.env不在git追踪中）
```

✅ `.env` 文件已在 .gitignore 中

### 3. 确认用户数据已排除
```bash
# 检查是否有用户数据被追踪
git ls-files | grep -E "(Avatars/|Feedbacks/|Characters/|\.db$|\.log$)"

# 应该返回空
```

✅ 用户数据目录已在 .gitignore 中

### 4. 查看待推送的提交
```bash
git log origin/main..HEAD --oneline
```

## 🚀 推送到GitHub

### 方式一：直接推送（推荐）

```bash
cd /home/changan/MyProject/FastNPC
git push origin main
```

### 方式二：强制推送（如果有冲突）

**⚠️ 警告**: 只有在确定需要覆盖远程历史时才使用！

```bash
git push origin main --force
```

### 方式三：推送并设置上游分支

```bash
git push -u origin main
```

## 📦 部署到生产服务器

### 前置准备

1. **确保服务器满足要求**
   - Ubuntu 20.04+ 或 CentOS 7+
   - Python 3.10+
   - PostgreSQL 13+
   - Redis 6+
   - Node.js 18+
   - 至少4GB内存

2. **准备部署账号**
   ```bash
   # 在服务器上创建部署用户
   sudo adduser fastnpc
   sudo usermod -aG sudo fastnpc
   ```

### 部署步骤

#### 1. 克隆项目到服务器

```bash
# SSH到服务器
ssh your_user@your_server_ip

# 切换到部署用户
sudo su - fastnpc

# 克隆项目
git clone https://github.com/YOUR_USERNAME/FastNPC.git
cd FastNPC
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑环境变量
nano .env
```

**必须配置的关键变量**：
```bash
# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx

# 数据库（PostgreSQL）
USE_POSTGRESQL=true
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fastnpc
POSTGRES_USER=fastnpc
POSTGRES_PASSWORD=使用强密码

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 连接池（已优化）
DB_POOL_MIN_CONN=10
DB_POOL_MAX_CONN=50

# 提示词数据库
USE_DB_PROMPTS=true
```

#### 3. 安装数据库

##### PostgreSQL
```bash
# 安装PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# 创建数据库和用户
sudo -u postgres psql
```

在PostgreSQL中执行：
```sql
CREATE DATABASE fastnpc;
CREATE USER fastnpc WITH PASSWORD '你的强密码';
ALTER DATABASE fastnpc OWNER TO fastnpc;
GRANT ALL PRIVILEGES ON DATABASE fastnpc TO fastnpc;
\q
```

##### Redis
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 验证Redis运行
redis-cli ping
# 应该返回: PONG
```

#### 4. 安装Python依赖

```bash
cd /home/fastnpc/FastNPC

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. 初始化数据库

```bash
# 激活虚拟环境
source venv/bin/activate

# 初始化数据库结构
python -c "from fastnpc.api.auth.db_init import init_db; init_db()"

# 初始化提示词
python fastnpc/scripts/init_prompts.py
python fastnpc/scripts/init_evaluation_prompts.py

# 验证数据库
python fastnpc/scripts/monitor_pool.py --mode status
```

#### 6. 构建前端

```bash
cd web/fastnpc-web

# 安装依赖
npm install

# 构建生产版本
npm run build

cd ../..
```

#### 7. 配置Systemd服务

```bash
# 编辑服务文件，更新路径
sudo nano fastnpc.service
```

确保以下路径正确：
```ini
WorkingDirectory=/home/fastnpc/FastNPC
ExecStart=/home/fastnpc/FastNPC/venv/bin/gunicorn
User=fastnpc
Group=fastnpc
```

安装服务：
```bash
sudo cp fastnpc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fastnpc
sudo systemctl start fastnpc
```

检查服务状态：
```bash
sudo systemctl status fastnpc
sudo journalctl -u fastnpc -f
```

#### 8. 配置Nginx反向代理

```bash
sudo apt install nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/fastnpc
```

配置内容：
```nginx
server {
    listen 80;
    server_name your_domain.com;  # 改为你的域名

    # 前端静态文件
    location / {
        root /home/fastnpc/FastNPC/web/fastnpc-web/dist;
        try_files $uri $uri/ /index.html;
        
        # 缓存静态资源
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }

    location /admin {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 文件上传大小限制
    client_max_body_size 10M;
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/fastnpc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 9. 配置SSL（推荐）

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your_domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

#### 10. 创建管理员账号

```bash
cd /home/fastnpc/FastNPC
source venv/bin/activate
python
```

在Python交互式环境中：
```python
from fastnpc.api.auth import register_user
register_user("admin", "你的强密码", is_admin=True)
exit()
```

#### 11. 配置防火墙

```bash
# 允许HTTP、HTTPS和SSH
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

#### 12. 设置定时备份

```bash
# 创建备份脚本
sudo nano /home/fastnpc/backup.sh
```

备份脚本内容：
```bash
#!/bin/bash
BACKUP_DIR="/home/fastnpc/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份PostgreSQL
pg_dump -U fastnpc fastnpc > $BACKUP_DIR/db_$DATE.sql

# 备份用户数据
tar -czf $BACKUP_DIR/avatars_$DATE.tar.gz -C /home/fastnpc/FastNPC Avatars Feedbacks

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

设置权限和定时任务：
```bash
chmod +x /home/fastnpc/backup.sh

# 添加到crontab（每天凌晨2点备份）
crontab -e
# 添加这行：
# 0 2 * * * /home/fastnpc/backup.sh >> /home/fastnpc/backup.log 2>&1
```

## ✅ 部署验证

### 1. 检查服务状态
```bash
sudo systemctl status fastnpc
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

### 2. 测试API
```bash
curl http://localhost:8000/api/health
curl https://your_domain.com/api/health
```

### 3. 测试前端
在浏览器访问：`https://your_domain.com`

### 4. 测试连接池
```bash
cd /home/fastnpc/FastNPC
source venv/bin/activate
python fastnpc/scripts/monitor_pool.py --mode status
```

### 5. 查看日志
```bash
# 应用日志
sudo journalctl -u fastnpc -f

# Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 📊 监控和维护

### 日常监控命令

```bash
# 检查服务状态
sudo systemctl status fastnpc

# 查看实时日志
sudo journalctl -u fastnpc -f

# 监控连接池
cd /home/fastnpc/FastNPC && source venv/bin/activate
python fastnpc/scripts/monitor_pool.py --mode monitor

# 检查数据库连接
psql -U fastnpc -d fastnpc -c "SELECT COUNT(*) FROM characters;"

# 检查Redis
redis-cli info stats
```

### 更新部署

```bash
cd /home/fastnpc/FastNPC
git pull origin main

# 更新依赖
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

## 🔧 故障排除

### 服务无法启动
```bash
# 查看详细日志
sudo journalctl -u fastnpc -n 100 --no-pager

# 检查配置文件
nano /etc/systemd/system/fastnpc.service

# 手动运行测试
source venv/bin/activate
gunicorn -c gunicorn_conf.py
```

### 连接池耗尽
参考 `docs/CONNECTION_POOL_QUICK_FIX.md`

### 数据库连接失败
```bash
# 检查PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"

# 测试连接
psql -U fastnpc -d fastnpc -h localhost
```

## 📞 支持

- 部署指南: `DEPLOYMENT.md`
- 连接池问题: `docs/CONNECTION_POOL_QUICK_FIX.md`
- 数据库管理: `docs/DATABASE_MANAGEMENT.md`
- 测试系统: `docs/TEST_SYSTEM_GUIDE.md`

## 🎉 完成！

部署完成后，您的FastNPC应用应该可以通过以下方式访问：

- **前端**: https://your_domain.com
- **API**: https://your_domain.com/api
- **管理后台**: https://your_domain.com (登录后点击管理员图标)

记得定期：
- 检查日志
- 监控连接池状态
- 备份数据库
- 更新依赖包

