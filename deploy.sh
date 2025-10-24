#!/bin/bash

echo "🚀 部署 EchoCast 后端服务..."

# 检查并安装依赖
cd /root/usr/podcast_web/backend
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

echo "📦 安装/更新依赖..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 找到 uvicorn 的实际路径
UVICORN_PATH=$(which uvicorn)
PYTHON_PATH=$(which python3)

echo "✅ Python 路径: $PYTHON_PATH"
echo "✅ Uvicorn 路径: $UVICORN_PATH"

# 创建 systemd 服务文件
echo "📝 创建 systemd 服务..."
sudo tee /etc/systemd/system/echocast.service > /dev/null << EOF
[Unit]
Description=EchoCast Podcast API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/usr/podcast_web/backend
Environment="PATH=$PATH:/root/usr/podcast_web/backend/venv/bin"
ExecStart=/root/usr/podcast_web/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 18188
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重载 systemd 并启动服务
echo "🔄 重载 systemd..."
sudo systemctl daemon-reload

echo "🟢 启动服务..."
sudo systemctl restart echocast

echo "⚙️  设置开机自启..."
sudo systemctl enable echocast

# 等待服务启动
sleep 3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 部署完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 服务管理命令："
echo "  查看状态: sudo systemctl status echocast"
echo "  查看日志: sudo journalctl -u echocast -f"
echo "  停止服务: sudo systemctl stop echocast"
echo "  重启服务: sudo systemctl restart echocast"
echo "  禁用服务: sudo systemctl disable echocast"
echo ""
echo "🌐 API 地址: http://$(curl -s ifconfig.me):18188"
echo "📖 API 文档: http://$(curl -s ifconfig.me):18188/docs"
echo ""

# 显示服务状态
sudo systemctl status echocast --no-pager

