# ArchiveBot 部署指南

本指南提供多种部署方案，帮助你在不同环境下稳定运行 ArchiveBot。

> **首次使用？** 请先阅读 [快速开始指南](QUICKSTART.md) 了解基本使用。

## 📋 部署方式对比

| 部署方式 | 适用场景 | 优点 | 缺点 | 成本 |
|---------|---------|------|------|------|
| **Docker (推荐)** | 任何环境 | 一键部署、环境隔离、易迁移升级 | 需要学习Docker | 免费 |
| 本地电脑 | 测试、开发 | 简单快速 | 需要电脑一直开机 | 免费 |
| 云服务器 | 长期使用 | 稳定可靠、7×24运行 | 需要基础Linux知识 | ¥10-30/月 |
| 宝塔面板 | 可视化管理 | 图形界面、易操作 | 需要安装宝塔 | 面板免费 |

---

## 🐳 方案一：Docker 部署（推荐）

### 为什么推荐 Docker？

- ✅ **一键部署**：无需手动配置 Python 环境
- ✅ **环境隔离**：不污染系统环境，卸载干净
- ✅ **易于升级**：一条命令更新到最新版
- ✅ **跨平台**：Windows/macOS/Linux 统一部署方式
- ✅ **数据持久化**：数据库和配置自动保存到宿主机

### 前置要求

安装 Docker 和 Docker Compose：

- **Windows/macOS**：下载 [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**：
  ```bash
  # Ubuntu/Debian
  curl -fsSL https://get.docker.com | sh
  sudo systemctl start docker
  sudo systemctl enable docker
  
  # 安装 Docker Compose（如果没有）
  sudo apt install docker-compose-plugin
  ```

### 快速开始

#### 1. 克隆项目

```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

#### 2. 配置 Bot

**方式一：使用配置文件（推荐）**

```bash
# 复制配置模板
cp config/config.template.yaml config/config.yaml

# 编辑配置文件
nano config/config.yaml  # 或用其他编辑器
```

填写以下必填项：
- `bot.token`: 从 [@BotFather](https://t.me/BotFather) 获取
- `bot.owner_id`: 你的 Telegram ID（[@userinfobot](https://t.me/userinfobot) 查询）
- `storage.telegram.channels.default`: 私有频道 ID
- `ai.api.api_key`: AI API 密钥（可选）

**方式二：使用环境变量（适合CI/CD）**

编辑 `docker-compose.yml`，取消注释并填写环境变量：

```yaml
environment:
  - BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
  - OWNER_ID=123456789
  - CHANNEL_ID=-1001234567890
  - AI_API_KEY=your_api_key_here
```

> 💡 **提示**：环境变量优先级 > 配置文件，可以混合使用

#### 3. 验证配置（推荐）

在启动前验证配置是否正确：

```bash
python verify_docker.py
```

如果看到 `✅ 所有检查通过！` 则可以继续。

#### 4. 启动 Bot

```bash
# 构建并启动（后台运行）
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止运行
docker-compose down
```

### 常用命令

```bash
# 查看运行状态
docker-compose ps

# 查看实时日志
docker-compose logs -f archivebot

# 重启 Bot
docker-compose restart

# 停止 Bot
docker-compose stop

# 完全删除容器（不删除数据）
docker-compose down

# 更新到最新版本
git pull
docker-compose down
docker-compose up -d --build
```

### 数据管理

数据持久化在以下目录（自动挂载到宿主机）：

- `./data/`：数据库、备份、缓存
- `./config/`：配置文件

**备份数据**：

```bash
# 备份整个数据目录
tar -czf archivebot-backup-$(date +%Y%m%d).tar.gz data/ config/

# 或使用 Bot 内置的备份功能（/backup 命令）
```

**恢复数据**：

```bash
# 解压备份
tar -xzf archivebot-backup-20260125.tar.gz

# 重启容器
docker-compose restart
```

### 故障排查

#### 容器无法启动

```bash
# 查看错误日志
docker-compose logs archivebot

# 常见问题：
# 1. config.yaml 不存在 → 检查是否复制了配置文件
# 2. 权限问题 → 检查 data/ 和 config/ 目录权限
# 3. 端口占用 → Bot 不需要端口，通常不会有此问题
```

#### 配置更新后不生效

```bash
# 重启容器
docker-compose restart

# 或重新构建
docker-compose up -d --build
```

#### 查看详细日志

```bash
# 查看最近 100 行日志
docker-compose logs --tail=100 archivebot

# 持续查看日志（Ctrl+C 退出）
docker-compose logs -f archivebot
```

### 安全建议

1. ⚠️ **不要提交敏感信息到 Git**：
   ```bash
   # config.yaml 和真实配置的 docker-compose.yml 已在 .gitignore 中
   # 如果修改了 docker-compose.yml 并填写了真实密钥，不要提交
   ```

2. ✅ **使用环境变量文件**（更安全的方式）：
   ```bash
   # 创建 .env 文件（不提交到 Git）
   echo "BOT_TOKEN=your_token" > .env
   echo "OWNER_ID=123456789" >> .env
   
   # docker-compose.yml 中引用
   env_file:
     - .env
   ```

3. ✅ **定期备份**：使用 Bot 的 `/backup` 命令或手动备份 `data/` 目录

---

## 💻 方案二：本地电脑部署

### Windows

#### 1. 安装 Python

下载并安装 [Python 3.9+](https://www.python.org/downloads/)

安装时勾选 **"Add Python to PATH"**

#### 2. 部署 Bot

```powershell
# 下载项目
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 安装依赖
pip install -r requirements.txt

# 配置Bot（参考快速开始指南）
copy config\config.template.yaml config\config.yaml
notepad config\config.yaml

# 启动
python main.py
```

#### 3. 后台运行（可选）

创建 `start.bat`：

```batch
@echo off
cd /d %~dp0
python main.py
pause
```

双击运行，最小化窗口即可。

### macOS / Linux

```bash
# 下载项目
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 安装依赖
pip3 install -r requirements.txt

# 配置Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml

# 启动
python3 main.py
```

#### 使用 nohup 后台运行

```bash
nohup python3 main.py > data/output.log 2>&1 &

# 查看进程
ps aux | grep main.py

# 停止
kill $(ps aux | grep 'python3 main.py' | grep -v grep | awk '{print $2}')
```

## 🌐 方案三：云服务器部署

### 服务器选择

**推荐配置**：
- CPU: 1核心
- 内存: 1GB+
- 存储: 10GB SSD
- 带宽: 1Mbps+
- 系统: Ubuntu 20.04/22.04 LTS

**服务商推荐**：

| 服务商 | 特点 | 优势 | 适用场景 |
|--------|------|------|----------|
| [衡天云](https://my.htstack.com/aff.php?aff=1197) | 国内服务商，香港/日本线路 | • CN2优化线路，国内速度快<br>• 价格亲民，性价比高<br>• 中文客服，沟通方便<br>• 按月付费，灵活取消 | 国内用户优选 |
| [DMIT](https://www.dmit.io/aff.php?aff=17814) | 美国/香港高端线路 | • CN2 GIA专线，延迟低<br>• 网络稳定性极高<br>• 适合长期使用<br>• 国际带宽充足 | 对速度要求高的用户 |

> 💡 **提示**：选择离你最近的服务器位置，可获得最佳访问速度。推荐香港或日本节点。

### Ubuntu/Debian 部署

#### 1. 连接服务器

```bash
ssh root@your_server_ip
```

#### 2. 系统准备

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y python3 python3-pip git wget curl

# 验证 Python 版本（需要 3.9+）
python3 --version
```

#### 3. 部署 Bot

**推荐使用 Docker 部署**（更简单）：

```bash
# 克隆项目
cd /opt
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 安装 Docker（如果未安装）
curl -fsSL https://get.docker.com | sh
sudo systemctl start docker
sudo systemctl enable docker

# 配置 Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml
# 填入你的Bot Token、User ID、Channel ID

# 启动（使用 Docker）
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

**或使用传统方式部署**：

```bash
# 克隆项目
cd /opt
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 安装依赖
pip3 install -r requirements.txt

# 配置Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml
# 填入你的Bot Token、User ID、Channel ID

# 测试启动
python3 main.py
# 按 Ctrl+C 停止
```

#### 4. 使用 Systemd 守护进程（推荐）

创建服务文件：

```bash
nano /etc/systemd/system/archivebot.service
```

填入以下内容：

```ini
[Unit]
Description=ArchiveBot - Telegram Archive Assistant
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ArchiveBot
ExecStart=/usr/bin/python3 /opt/ArchiveBot/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/ArchiveBot/data/bot.log
StandardError=append:/opt/ArchiveBot/data/error.log

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重新加载配置
systemctl daemon-reload

# 启动服务
systemctl start archivebot

# 设置开机自启
systemctl enable archivebot

# 查看状态
systemctl status archivebot
```

**常用命令**：

```bash
# 重启
systemctl restart archivebot

# 停止
systemctl stop archivebot

# 查看实时日志
journalctl -u archivebot -f

# 查看最近100行日志
journalctl -u archivebot -n 100

# 查看Bot日志文件
tail -f /opt/ArchiveBot/data/bot.log
```

### CentOS/RHEL 部署

```bash
# 更新系统
yum update -y

# 安装依赖
yum install -y python3 python3-pip git

# 其他步骤与 Ubuntu 相同
```

## 🎨 方案三：宝塔面板部署

适合不熟悉命令行的用户，提供可视化管理界面。

### 1. 安装宝塔面板

```bash
# Ubuntu/Debian
wget -O install.sh https://download.bt.cn/install/install-ubuntu_6.0.sh && bash install.sh

# CentOS
yum install -y wget && wget -O install.sh https://download.bt.cn/install/install_6.0.sh && sh install.sh
```

安装完成后记录面板地址、用户名和密码。

### 2. 通过面板部署

#### 2.1 上传项目文件

1. 登录宝塔面板 → **文件** → 创建目录 `/www/wwwroot/ArchiveBot`
2. 进入该目录，上传项目文件（可以直接上传压缩包后解压，或使用终端Git克隆）

**方式一：使用 Git 克隆**（推荐）
```bash
cd /www/wwwroot/ArchiveBot
git clone https://github.com/tealun/ArchiveBot.git .
```

**方式二：上传压缩包**
- 下载项目 ZIP 包
- 在宝塔文件管理器中上传并解压

3. 复制并编辑配置文件：
   ```bash
   cp config/config.template.yaml config/config.yaml
   nano config/config.yaml
   ```

#### 2.2 创建 Python 项目

1. 返回宝塔面板 → 点击左侧 **网站**
2. 点击 **添加站点** → 选择 **Python项目**
3. 填写项目信息：
   - **项目名称**：`ArchiveBot`
   - **Python环境**：选择 Python 3.9 或更高版本（如 3.14.2）
   - **项目路径**：选择 `/www/wwwroot/ArchiveBot`（刚才上传的路径）
   - **启动方式**：选择 **命令行启动**
   - **启动命令**：`python main.py`
   - **环境变量**：选择 **无**
   - **启动用户**：`root`（默认）
   - **开机启动**：勾选"是否设置开机自启动"（推荐）
4. 点击 **保存配置**

#### 2.3 安装依赖

1. 在 **网站** 列表中找到刚创建的 `archivebot` 项目
2. 点击 **设置** → **环境管理**
3. 在"依赖记录文件"输入框中确认路径为：`/www/wwwroot/ArchiveBot/requirements.txt`
4. 点击 **安装** 按钮，宝塔会自动读取并安装所有依赖包
5. 等待安装完成（可以看到所有依赖包及版本号列表）

#### 2.4 启动项目

1. 返回 **网站** 列表
2. 找到 `archivebot` 项目，点击 **启动** 按钮
3. 等待项目启动成功，状态变为"运行中"

#### 2.5 查看状态和日志

- **查看运行状态**：在项目列表中可以看到运行状态（运行中/已停止）
- **查看日志**：点击项目 **设置** → **日志** 查看实时运行日志
- **重启项目**：点击 **重启** 按钮
- **停止项目**：点击 **停止** 按钮

> 💡 **提示**：宝塔会自动为Python项目配置守护进程，重启服务器后会自动启动

<details>
<summary>📝 旧版宝塔面板部署方式（使用PM2/Supervisor）</summary>

如果你的宝塔版本较旧，没有Python项目功能，可以使用以下方式：

**使用 PM2 管理器**：
1. 软件商店安装 **PM2管理器**
2. 添加项目：
   - 项目路径：`/www/wwwroot/ArchiveBot`
   - 启动文件：`main.py`
   - 运行模式：`Python`
3. 点击启动

**使用 Supervisor 管理器**：
1. 软件商店安装 **Supervisor管理器**
2. 添加守护进程：
   - 名称：`archivebot`
   - 启动命令：`/usr/bin/python3 /www/wwwroot/ArchiveBot/main.py`
   - 目录：`/www/wwwroot/ArchiveBot`
3. 启动进程

</details>

### 3. 查看日志

在宝塔面板 → 网站 → ArchiveBot → 设置 → 日志

## 🐳 方案四：Docker 部署

### 使用 Docker Compose（推荐）

#### 1. 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | bash

# 启动 Docker
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
apt install -y docker-compose
```

#### 2. 创建项目目录

```bash
mkdir -p /opt/archivebot
cd /opt/archivebot
```

#### 3. 下载项目

```bash
git clone https://github.com/tealun/ArchiveBot.git .
```

#### 4. 配置

```bash
cp config/config.template.yaml config/config.yaml
nano config/config.yaml
```

#### 5. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  archivebot:
    image: python:3.11-slim
    container_name: archivebot
    restart: unless-stopped
    working_dir: /app
    volumes:
      - ./:/app
      - ./data:/app/data
      - ./config:/app/config
    command: >
      sh -c "pip install --no-cache-dir -r requirements.txt && 
             python main.py"
    environment:
      - TZ=Asia/Shanghai
      - PYTHONUNBUFFERED=1
```

#### 6. 启动容器

```bash
# 启动（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps

# 重启
docker-compose restart

# 停止
docker-compose down
```

### 使用 Dockerfile（高级）

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

构建和运行：

```bash
# 构建镜像
docker build -t archivebot .

# 运行容器
docker run -d \
  --name archivebot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  archivebot
```

## 🔒 安全加固

### 1. 文件权限

```bash
# 保护配置文件
chmod 600 config/config.yaml

# 限制数据目录访问
chmod 700 data/
```

### 2. 防火墙配置

ArchiveBot 不需要对外开放端口，确保只开放 SSH：

```bash
# Ubuntu (ufw)
ufw allow 22/tcp
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
```

### 3. 定期备份

创建备份脚本 `backup.sh`：

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
BOT_DIR="/opt/ArchiveBot"

mkdir -p $BACKUP_DIR

# 备份数据库
cp $BOT_DIR/data/archive.db $BACKUP_DIR/archive_$DATE.db

# 清理30天前的备份
find $BACKUP_DIR -name "archive_*.db" -mtime +30 -delete

echo "Backup completed: archive_$DATE.db"
```

设置定时任务：

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨2点备份
0 2 * * * /opt/ArchiveBot/backup.sh >> /opt/ArchiveBot/backup.log 2>&1
```

## 📊 监控和维护

### 查看运行状态

```bash
# Systemd
systemctl status archivebot

# Docker
docker-compose ps
docker logs archivebot

# 进程
ps aux | grep main.py
```

### 查看日志

```bash
# Bot日志
tail -f data/bot.log

# 系统日志
journalctl -u archivebot -f

# Docker日志
docker-compose logs -f
```

### 更新 Bot

```bash
# 停止服务
systemctl stop archivebot
# 或
docker-compose down

# 拉取最新代码
git pull

# 安装新依赖
pip3 install -r requirements.txt

# 重启服务
systemctl start archivebot
# 或
docker-compose up -d
```

### 性能优化

```bash
# 清理缓存
find data/ -name "*.pyc" -delete
find data/ -name "__pycache__" -delete

# 数据库优化（定期执行）
sqlite3 data/archive.db "VACUUM;"

# 查看数据库大小
ls -lh data/archive.db
```

## 🆘 故障排查

### Bot 无法启动

1. 检查配置文件格式：
```bash
python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
```

2. 检查依赖：
```bash
pip3 install -r requirements.txt --upgrade
```

3. 查看详细错误：
```bash
python3 main.py
```

### 内存占用过高

```bash
# 查看内存使用
free -h

# 重启 Bot
systemctl restart archivebot
```

### 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 清理日志
truncate -s 0 data/bot.log

# 清理旧备份
find data/backups/ -mtime +30 -delete
```

## 📚 相关资源

- [快速开始指南](QUICKSTART.md) - 了解如何使用
- [GitHub Issues](https://github.com/tealun/ArchiveBot/issues) - 报告问题

---

**需要帮助？** 欢迎在 GitHub 提交 Issue！
