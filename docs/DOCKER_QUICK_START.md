# 🐳 Docker 一键部署指南（零基础版）

**ArchiveBot v1.0 官方发布版**

本指南将引导你在 5 分钟内完成 ArchiveBot 的 Docker 部署，无需任何编程基础。

---

## 第一步：安装 Docker

### Windows 用户
1. 下载 Docker Desktop：https://www.docker.com/products/docker-desktop/
2. 双击安装包，按提示安装
3. 重启电脑
4. 打开 Docker Desktop，等待启动完成（右下角图标变绿）

### macOS 用户
1. 下载 Docker Desktop：https://www.docker.com/products/docker-desktop/
2. 拖动到应用程序文件夹
3. 打开 Docker Desktop，等待启动完成（顶部菜单栏图标变亮）

### Linux 用户（Ubuntu/Debian）
```bash
# 一键安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（可选，避免每次 sudo）
sudo usermod -aG docker $USER
newgrp docker
```

**验证安装**：
```bash
docker --version
docker compose version
```
看到版本号即表示安装成功（Docker Compose 2.x+ 使用 `docker compose`，旧版使用 `docker-compose`）。

---

## 第二步：下载 ArchiveBot

```bash
# 克隆项目（v1.0 正式版）
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 可选：切换到稳定版本
git checkout v1.0
```

---

## 第三步：配置 Bot

### 3.1 获取必需信息

1. **Bot Token**：
   - 打开 Telegram，搜索 [@BotFather](https://t.me/BotFather)
   - 发送 `/newbot` 创建新 Bot
   - 按提示设置名称和用户名
   - **复制获得的 Token**（格式：`123456:ABC-DEF...`）

2. **你的 User ID**：
   - 搜索 [@userinfobot](https://t.me/userinfobot)
   - 发送任意消息
   - **记下你的 ID**（纯数字，如：`123456789`）

3. **私有频道 ID**：
   - 创建一个新频道（设为私有）
   - 把 Bot 添加为频道管理员（需要发送消息权限）
   - 在频道中转发一条消息到 [@userinfobot](https://t.me/userinfobot)
   - **记下频道 ID**（格式：`-100xxxxxxxxx`）

### 3.2 填写配置文件

**选择你的语言版本**：
- 简体中文：`config/config.template.yaml`
- English: `config/config.template.en.yaml`
- 其他语言：查看 `config/` 目录

```bash
# 复制配置模板（选择你的语言）
cp config/config.template.yaml config/config.yaml

# Windows 用户用记事本编辑：
notepad config/config.yaml

# macOS/Linux 用户：
nano config/config.yaml
```

**只需要修改这三个地方**：

```yaml
bot:
  token: "你的Bot Token"        # ← 改这里
  owner_id: 你的User ID          # ← 改这里（数字，不加引号）

storage:
  telegram:
    channels:
      default: -100你的频道ID    # ← 改这里（负数，不加引号）
```

保存文件（Ctrl+S 或 Cmd+S）。

### 3.3 验证配置（推荐）

运行配置验证工具，确保配置正确：

```bash
python verify_docker.py
```

如果看到 ✅，说明配置正确！

---

## 第四步：启动 Bot

```bash
# 一键构建并启动
docker compose up -d --build

# 查看启动日志
docker compose logs -f
```

**看到以下输出表示成功**：
```
INFO - Bot started successfully
INFO - Bot username: @YourBotName
```

按 `Ctrl+C` 退出日志查看（Bot 会继续在后台运行）。

---

## 第五步：开始使用

1. 在 Telegram 中找到你的 Bot
2. 发送 `/start` 命令
3. 开始归档你的内容！

🎉 **恭喜！你的 ArchiveBot 已经运行起来了！**

---

## 常用命令

```bash
# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启 Bot
docker compose restart

# 停止 Bot
docker compose down

# 更新到最新版
git pull && docker compose up -d --build

# 进入容器（调试用）
docker compose exec archivebot sh
```

---

## 第四步：配置数据目录权限（重要）

由于 Docker 容器以非 root 用户（uid 1000）运行，需要确保数据目录权限正确。

### Linux/macOS 用户：
```bash
# 确保 data 目录存在并设置权限
mkdir -p data
chmod 755 data
```

如果启动后遇到权限错误，执行：
```bash
sudo chown -R 1000:1000 data/
```

### Windows 用户：
通常无需额外配置，Docker Desktop 会自动处理权限映射。

---

## 第五步：启动 Bot

**一条命令搞定**：

```bash
docker-compose up -d --build
```

等待 1-3 分钟（首次构建镜像需要下载依赖）。

看到这个表示成功：
```
✓ Container archivebot  Started
```

---

## 第六步：测试 Bot

1. 打开 Telegram，找到你的 Bot
2. 发送 `/start`
3. 看到欢迎消息即表示成功！

---

## 常用命令

```bash
# 查看运行状态
docker-compose ps

# 查看日志（实时）
docker-compose logs -f

# 重启 Bot
docker-compose restart

# 停止 Bot
docker-compose stop

# 停止并删除容器（不删除数据）
docker-compose down

# 更新到最新版本
git pull
docker-compose down
docker-compose up -d --build
```

---

## 故障排查

### 问题 1：容器无法启动

**查看错误日志**：
```bash
docker-compose logs archivebot
```

**常见原因**：
- `config.yaml` 未正确填写 → 重新编辑配置文件
- Bot Token 错误 → 检查是否完整复制
- 频道 ID 错误 → 确认是负数格式 `-100xxxxxxx`

### 问题 2：Bot 不回复消息

**检查**：
1. Bot 是否已启动：`docker-compose ps`
2. 查看日志：`docker-compose logs -f`
3. 确认你的 User ID 是否正确
4. 确认 Bot 已添加到频道并设为管理员

### 问题 3：修改配置后不生效

```bash
# 重启容器
docker-compose restart

# 或重新构建
docker-compose down
docker-compose up -d --build
```

---

## 数据备份

**你的所有数据在这里**：
- `./data/` - 数据库、备份文件
- `./config/config.yaml` - 配置文件

**备份方法**：
```bash
# Windows PowerShell
Compress-Archive -Path data, config -DestinationPath backup.zip

# macOS/Linux
tar -czf backup.tar.gz data/ config/config.yaml
```

---

## 完全卸载

```bash
# 停止并删除容器
docker-compose down

# 删除镜像（可选）
docker rmi archivebot-archivebot

# 删除项目文件夹
cd ..
rm -rf ArchiveBot  # Linux/macOS
# 或手动删除文件夹（Windows）
```

---

## 需要帮助？

- 📖 详细文档：[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 🐛 问题反馈：https://github.com/tealun/ArchiveBot/issues
- 💬 配置问题：先运行 `python verify_docker.py` 检查配置

---

**🎉 恭喜！你已成功部署 ArchiveBot！**

现在可以：
- 转发消息到 Bot 进行归档
- 使用 `/search` 搜索内容
- 使用 `/tags` 管理标签
- 使用 `/help` 查看所有命令
