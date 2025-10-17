#!/bin/bash
# 使用Gunicorn启动FastNPC（推荐生产环境）

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FastNPC Gunicorn启动${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查gunicorn是否安装
if ! command -v gunicorn &> /dev/null; then
    echo -e "${RED}错误: gunicorn未安装${NC}"
    echo "请运行: pip install gunicorn"
    exit 1
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: .env 文件不存在${NC}"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 检查端口
PORT=8000
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}"
    echo "正在停止旧进程..."
    pkill -f "gunicorn fastnpc.api.server:app" || true
    sleep 2
fi

# 启动服务器
echo -e "${GREEN}启动Gunicorn服务器...${NC}"
echo ""

gunicorn fastnpc.api.server:app \
    --config gunicorn_conf.py \
    --log-level info

echo -e "${GREEN}服务器已启动${NC}"
echo "访问地址: http://localhost:$PORT"
echo "日志目录: logs/"
echo ""
echo "停止服务器: pkill -f 'gunicorn fastnpc.api.server:app'"

