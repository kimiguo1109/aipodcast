#!/bin/bash

echo "🛑 停止 EchoCast 后端服务..."

# 方式1: 停止 screen 会话
screen -S echocast -X quit 2>/dev/null && echo "✅ Screen 会话已停止"

# 方式2: 停止 systemd 服务
sudo systemctl stop echocast 2>/dev/null && echo "✅ Systemd 服务已停止"

# 方式3: 杀掉 uvicorn 进程
pkill -f "uvicorn app.main:app" && echo "✅ Uvicorn 进程已停止"

echo ""
echo "✅ 所有后端服务已停止"

