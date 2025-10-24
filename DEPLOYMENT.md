# 部署指南

## 三种运行方式

### 🟢 方案 1：Systemd 服务（推荐生产环境）

**优点**：开机自启、自动重启、日志管理

```bash
# 一键部署
./deploy.sh

# 管理命令
sudo systemctl status echocast    # 查看状态
sudo systemctl restart echocast   # 重启服务
sudo systemctl stop echocast      # 停止服务
sudo journalctl -u echocast -f    # 查看实时日志
```

---

### 🔵 方案 2：Screen 会话（推荐开发/测试）

**优点**：简单快速、可随时查看

```bash
# 启动服务
./run_backend.sh

# 查看运行中的会话
screen -ls

# 进入会话（查看日志）
screen -r echocast

# 退出会话（保持运行）
Ctrl+A, 然后按 D

# 停止服务
./stop_backend.sh
```

---

### 🟡 方案 3：直接运行（临时测试）

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**注意**：退出终端后服务会停止

---

## 快速命令

```bash
# 停止所有后端服务
./stop_backend.sh

# 使用 systemd 启动（推荐）
./deploy.sh

# 或使用 screen 启动
./run_backend.sh
```

---

## 访问地址

- **API**: http://your-ec2-ip:8000
- **文档**: http://your-ec2-ip:8000/docs
- **ReDoc**: http://your-ec2-ip:8000/redoc

---

## 防火墙设置

确保 EC2 安全组开放 8000 端口：

```bash
# 检查端口
sudo netstat -tlnp | grep 8000

# 或者
sudo ss -tlnp | grep 8000
```

