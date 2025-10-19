#!/bin/bash
# FastNPC 数据库管理工具启动脚本
# 使用Docker运行Adminer来管理PostgreSQL数据库

set -e

echo "=================================="
echo "FastNPC Adminer 启动脚本"
echo "=================================="
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未检测到Docker，请先安装Docker"
    echo ""
    echo "安装指引:"
    echo "  Ubuntu/Debian: sudo apt install docker.io"
    echo "  或访问: https://docs.docker.com/engine/install/"
    exit 1
fi

# 检查是否已经有运行中的Adminer容器
if docker ps -a --format '{{.Names}}' | grep -q '^fastnpc-adminer$'; then
    echo "📦 检测到已存在的Adminer容器"
    
    # 检查容器状态
    if docker ps --format '{{.Names}}' | grep -q '^fastnpc-adminer$'; then
        echo "✅ Adminer容器已在运行中"
    else
        echo "🔄 启动已存在的Adminer容器..."
        docker start fastnpc-adminer
        echo "✅ Adminer容器已启动"
    fi
else
    echo "🚀 创建并启动新的Adminer容器..."
    docker run -d \
      --name fastnpc-adminer \
      --network host \
      -p 8080:8080 \
      adminer:latest
    
    echo "✅ Adminer容器已创建并启动"
fi

echo ""
echo "=================================="
echo "✨ Adminer 已成功启动！"
echo "=================================="
echo ""
echo "📍 访问地址:"
echo "   http://localhost:8080/"
echo ""
echo "🔐 登录信息:"
echo "   系统: PostgreSQL"
echo "   服务器: localhost (或 127.0.0.1)"
echo "   用户名: fastnpc"
echo "   密码: (查看 fastnpc/config.py 中的 PG_PASSWORD)"
echo "   数据库: fastnpc"
echo ""
echo "🎯 快速访问链接（需先填写密码）:"
echo "   http://localhost:8080/?pgsql=localhost&username=fastnpc&db=fastnpc&ns=public&select=characters"
echo ""
echo "💡 常用命令:"
echo "   停止: docker stop fastnpc-adminer"
echo "   启动: docker start fastnpc-adminer"
echo "   删除: docker rm -f fastnpc-adminer"
echo "   查看日志: docker logs fastnpc-adminer"
echo ""
echo "📚 详细文档: docs/DATABASE_MANAGEMENT.md"
echo ""

# 等待容器完全启动
echo "⏳ 等待Adminer启动完成..."
sleep 3

# 检查Adminer是否可访问
if command -v curl &> /dev/null; then
    if curl -s http://localhost:8080 > /dev/null; then
        echo "✅ Adminer运行正常！"
        echo ""
        
        # 尝试在浏览器中打开
        if command -v xdg-open &> /dev/null; then
            echo "🌐 正在浏览器中打开..."
            xdg-open http://localhost:8080 2>/dev/null || true
        elif command -v open &> /dev/null; then
            echo "🌐 正在浏览器中打开..."
            open http://localhost:8080 2>/dev/null || true
        else
            echo "💻 请手动在浏览器中打开: http://localhost:8080"
        fi
    else
        echo "⚠️  警告: 无法访问Adminer，请检查容器状态"
        echo "   运行 'docker logs fastnpc-adminer' 查看日志"
    fi
else
    echo "💻 请在浏览器中打开: http://localhost:8080"
fi

echo ""
echo "按 Ctrl+C 退出此脚本（容器将继续在后台运行）"

