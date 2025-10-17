#!/bin/bash
# FastNPC 生产环境启动脚本（2核2G服务器优化）

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FastNPC 生产环境启动${NC}"
echo -e "${GREEN}服务器配置: 2核2G${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: .env 文件不存在${NC}"
    echo "请复制 .env.example 并配置环境变量"
    exit 1
fi

# 加载环境变量
source .env

# 检查必需的环境变量
if [ -z "$FASTNPC_SECRET" ]; then
    echo -e "${RED}错误: FASTNPC_SECRET 未设置${NC}"
    exit 1
fi

# 服务器配置（2核2G优化）
HOST="0.0.0.0"
PORT=8000
WORKERS=2  # 2个worker，充分利用2核CPU

# 日志配置
LOG_DIR="logs"
mkdir -p $LOG_DIR
ACCESS_LOG="$LOG_DIR/access.log"
ERROR_LOG="$LOG_DIR/error.log"

echo -e "${YELLOW}配置信息:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS (2核CPU，每核1个worker)"
echo "  访问日志: $ACCESS_LOG"
echo "  错误日志: $ERROR_LOG"
echo ""

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}"
    echo "正在尝试停止旧进程..."
    pkill -f "uvicorn fastnpc.api.server:app" || true
    sleep 2
fi

# 启动服务器（生产环境配置）
echo -e "${GREEN}启动FastNPC服务器...${NC}"
echo ""

# 使用uvicorn + gunicorn模式（推荐生产环境）
# 如果安装了gunicorn，使用以下命令：
# gunicorn fastnpc.api.server:app \
#     --workers $WORKERS \
#     --worker-class uvicorn.workers.UvicornWorker \
#     --bind $HOST:$PORT \
#     --access-logfile $ACCESS_LOG \
#     --error-logfile $ERROR_LOG \
#     --log-level info \
#     --timeout 300 \
#     --graceful-timeout 30 \
#     --keep-alive 5

# 如果没有gunicorn，使用uvicorn多worker模式：
uvicorn fastnpc.api.server:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level info \
    --access-log \
    --no-server-header \
    --timeout-keep-alive 5 \
    --limit-concurrency 100 \
    --backlog 128

# 注意：uvicorn的多worker模式不支持--reload选项
# 如果需要热重载，使用 start_dev.sh 开发脚本

