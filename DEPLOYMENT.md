# ArchiveBot 部署指南

本指南帮助你在不同环境下部署 ArchiveBot，实现7×24小时稳定运行。

> **快速开始**：如果你是第一次使用，请先阅读 [快速开始指南](QUICKSTART.md)

## 📋 部署方式对比

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| 本地直接运行 | 测试、开发 | 简单快速 | 需要电脑一直开机 |
| 后台进程 | 个人VPS | 持续运行 | 需要手动管理 |
| Systemd服务 | Linux VPS | 开机自启、自动重启 | 仅Linux |
| Docker | 生产环境 | 隔离环境、易迁移 | 需要学习Docker |
| 云服务器 | 长期使用 | 稳定可靠 | 有一定成本 |

## 🖥️ 方案一：本地直接运行

**适合**：测试使用，短期运行

### 步骤

1. 完成 [快速开始指南](QUICKSTART.md) 的配置
2. 运行 Bot：
```bash
python main.py
```

3. 保持终端窗口打开

**优点**：立即可用  
**缺点**：关闭终端或电脑就停止运行

## 🌐 方案二：云服务器部署（推荐）

**适合**：长期使用，7×24小时运行

### 选择云服务器

推荐配置：
- **CPU**: 1核心
- **内存**: 512MB - 1GB  
- **存储**: 10GB
- **带宽**: 1Mbps
- **系统**: Ubuntu 20.04/22.04

常见服务商：
- 阿里云（国内）
- 腾讯云（国内）
- AWS（国际）
- DigitalOcean（国际）

💰 **成本**：约 ¥10-30/月

### 部署步骤

#### 1. 连接到服务器

```bash
# 使用 SSH 连接（替换为你的服务器 IP）
ssh root@your_server_ip
```

#### 2. 安装依赖

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Python 和 Git
apt install -y python3 python3-pip git

# 验证安装
python3 --version  # 应显示 3.9+
```

#### 3. 部署 Bot

```bash
# 克隆项目
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 安装Python依赖
pip3 install -r requirements.txt

# 配置Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # 填入你的配置
```

#### 4. 使用 Screen 后台运行（简单方式）

```bash
# 安装 screen
apt install -y screen

# 创建新会话
screen -S archivebot

# 启动 Bot
python3 main.py

# 按 Ctrl+A 然后按 D 离开会话（Bot继续运行）

# 重新进入会话查看
screen -r archivebot

# 终止 Bot
screen -X -S archivebot quit
```

#### 5. 使用 Systemd 服务（推荐方式）

```bash
# 创建服务文件
nano /etc/systemd/system/archivebot.service
```

**填入以下内容**（替换路径）：
```ini
```bash
# 测试配置
python -c "from src.utils.config import get_config; print(get_config())"

# 测试数据库
python -c "from src.models.database import init_database; db = init_database('data/test.db'); print('OK'); db.close()"

# 启动 bot（测试模式）
python main.py
```

## 🚀 启动 Bot

### 直接启动
```bash
python main.py
```

### 后台运行（Linux/Mac）
```bash
# 使用 nohup
nohup python main.py > data/output.log 2>&1 &

# 查看日志
tail -f data/bot.log

# 停止 bot
ps aux | grep main.py
```ini
[Unit]
Description=ArchiveBot - Personal Telegram Archive Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ArchiveBot
ExecStart=/usr/bin/python3 /root/ArchiveBot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启动服务**：
```bash
# 重新加载配置
systemctl daemon-reload

# 启动服务
systemctl start archivebot

# 设置开机自启
systemctl enable archivebot

# 查看状态
systemctl status archivebot

# 查看日志
journalctl -u archivebot -f
```

**常用命令**：
```bash
# 重启
systemctl restart archivebot

# 停止
systemctl stop archivebot

# 查看日志（最近100行）
journalctl -u archivebot -n 100
```

## 🐳 方案三：Docker 部署（高级）

**适合**：熟悉 Docker 的用户，需要环境隔离

### 使用 Docker Compose（推荐）

1. 创建 `docker-compose.yml`：
```yaml
version: '3.8'

services:
  archivebot:
    image: python:3.9-slim
    container_name: archivebot
    restart: unless-stopped
    working_dir: /app
    volumes:
      - ./:/app
      - ./data:/app/data
    command: >
      sh -c "pip install -r requirements.txt && python main.py"
    environment:
      - TZ=Asia/Shanghai
```

2. 启动：
```bash
# 启动容器（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

## 🔒 安全建议

### 1. 保护配置文件
```bash
# Linux/Mac
chmod 600 config/config.yaml

# Windows: 右键 → 属性 → 安全 → 限制访问权限
```

### 2. 防火墙配置
ArchiveBot 不需要开放端口，确保防火墙关闭所有入站端口。

### 3. 定期备份
```bash
# 备份脚本示例
#!/bin/bash
