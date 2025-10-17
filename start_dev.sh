#!/bin/bash
# FastNPC 开发环境启动脚本（支持热重载）

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FastNPC 开发环境启动${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: .env 文件不存在${NC}"
    echo "请复制 .env.example 并配置环境变量"
    exit 1
fi

# 开发环境配置
HOST="0.0.0.0"
PORT=8000

echo -e "${YELLOW}配置信息:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: 1 (开发模式，支持热重载)"
echo "  热重载: 启用"
echo ""

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}"
    echo "正在尝试停止旧进程..."
    pkill -f "uvicorn fastnpc.api.server:app" || true
    sleep 2
fi

# 启动开发服务器（支持热重载）
echo -e "${GREEN}启动FastNPC开发服务器...${NC}"
echo -e "${YELLOW}提示: 文件修改后会自动重载${NC}"
echo ""

uvicorn fastnpc.api.server:app \
    --host $HOST \
    --port $PORT \
    --reload \
    --log-level debug \
    --access-log

