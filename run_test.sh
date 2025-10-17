#!/bin/bash
# 并发测试脚本

echo "================================"
echo "FastNPC 并发性能测试"
echo "================================"
echo ""
echo "步骤1: 启动服务器（单进程模式）"
echo "步骤2: 在另一个终端运行: python test_concurrency.py"
echo ""
echo "正在启动服务器..."
echo ""

cd /home/changan/MyProject/FastNPC
source .venv/bin/activate || true
python -m fastnpc
