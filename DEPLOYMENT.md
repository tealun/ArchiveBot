# ArchiveBot 部署指南

## 📋 部署前检查清单

### 1. 环境准备
- [ ] Python 3.9 或更高版本已安装
- [ ] pip 已安装并更新到最新版本
- [ ] Git 已安装（可选，用于版本控制）

### 2. 配置文件
- [ ] 复制 `config/config.template.yaml` 到 `config/config.yaml`
- [ ] 修改 `bot_token`（从 @BotFather 获取）
- [ ] 修改 `owner_id`（你的 Telegram user ID）
- [ ] 修改 `storage.telegram_channel_id`（私有频道 ID）
- [ ] 检查其他配置项是否符合需求

### 3. 依赖安装
```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 目录权限
```bash
# 创建数据目录
mkdir -p data

# 设置权限（Linux/Mac）
chmod 700 data
chmod 600 config/config.yaml

# Windows 上右键 → 属性 → 安全 → 编辑权限
```

### 5. Telegram 设置
- [ ] 创建私有频道
- [ ] 添加 bot 为频道管理员
- [ ] 获取频道 ID（使用 @userinfobot 或发送消息到频道）
- [ ] 确认 bot 有发送消息权限

### 6. 测试运行
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
kill <PID>
```

### 使用 systemd（Linux 推荐）
创建服务文件 `/etc/systemd/system/archivebot.service`:

```ini
[Unit]
Description=ArchiveBot Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/ArchiveBot
ExecStart=/path/to/venv/bin/python /path/to/ArchiveBot/main.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/path/to/ArchiveBot/data/output.log
StandardError=append:/path/to/ArchiveBot/data/error.log

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable archivebot

# 启动服务
sudo systemctl start archivebot

# 查看状态
sudo systemctl status archivebot

# 查看日志
sudo journalctl -u archivebot -f
```

### 使用 Docker（推荐生产环境）
创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p data

# 运行
CMD ["python", "main.py"]
```

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  archivebot:
    build: .
    container_name: archivebot
    restart: unless-stopped
    volumes:
      - ./config:/app/config:ro
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
```

运行：
```bash
# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down
```

## 🔒 安全加固

### 1. 文件权限
```bash
# Linux/Mac
chmod 600 config/config.yaml
chmod 700 data
chmod 600 data/*.db

# 或者使用更严格的权限
chown -R your_user:your_group .
chmod -R go-rwx config data
```

### 2. 防火墙配置
```bash
# 如果运行在 VPS 上，只开放必要端口
# Bot 不需要开放端口（使用 Telegram 轮询）

# UFW（Ubuntu）
sudo ufw enable
sudo ufw default deny incoming
sudo ufw allow ssh
```

### 3. 定期备份
添加到 crontab (`crontab -e`):

```bash
# 每天凌晨 2 点备份数据库
0 2 * * * cd /path/to/ArchiveBot && python -c "from src.utils.db_maintenance import backup_database; backup_database('data/archive.db')" >> data/backup.log 2>&1

# 每周日凌晨 3 点优化数据库
0 3 * * 0 cd /path/to/ArchiveBot && python -c "from src.utils.db_maintenance import optimize_database; optimize_database('data/archive.db')" >> data/maintenance.log 2>&1
```

### 4. 日志轮转
创建 `/etc/logrotate.d/archivebot`:

```
/path/to/ArchiveBot/data/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 your_user your_group
}
```

## 📊 监控和维护

### 健康检查
```bash
# 检查 bot 是否运行
ps aux | grep main.py

# 检查数据库大小
du -h data/archive.db

# 检查日志
tail -n 50 data/bot.log
```

### 性能监控
```python
# 创建监控脚本 monitor.py
import psutil
import os

def check_bot():
    # 检查进程
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if 'main.py' in ' '.join(proc.info['cmdline']):
            # 获取内存和 CPU
            mem = proc.memory_info().rss / 1024 / 1024  # MB
            cpu = proc.cpu_percent(interval=1)
            print(f"Bot PID: {proc.info['pid']}")
            print(f"Memory: {mem:.2f} MB")
            print(f"CPU: {cpu:.1f}%")
            return True
    print("Bot not running!")
    return False

if __name__ == "__main__":
    check_bot()
```

### 数据库维护
```bash
# 检查数据库完整性
python -c "from src.utils.db_maintenance import verify_database; verify_database('data/archive.db')"

# 优化数据库
python -c "from src.utils.db_maintenance import optimize_database; optimize_database('data/archive.db')"

# 备份数据库
python -c "from src.utils.db_maintenance import backup_database; backup_database('data/archive.db')"

# 清理旧备份（保留最近 7 个）
python -c "from src.utils.db_maintenance import cleanup_old_backups; cleanup_old_backups('data/backups', 7)"
```

## 🔧 故障排除

### Bot 无法启动
1. 检查配置文件是否正确
2. 检查 bot token 是否有效
3. 检查网络连接
4. 查看日志文件 `data/bot.log`

### 无法发送消息到频道
1. 确认频道是私有的
2. 确认 bot 是频道管理员
3. 确认频道 ID 正确（负数，如 -1001234567890）
4. 测试手动发送消息

### 数据库错误
1. 检查数据库文件权限
2. 运行完整性检查
3. 从备份恢复
4. 检查磁盘空间

### 性能问题
1. 优化数据库（VACUUM）
2. 清理旧日志
3. 检查磁盘 I/O
4. 考虑升级服务器

## 📚 常用命令

```bash
# 启动
python main.py

# 停止（Ctrl+C 或）
kill -SIGTERM <PID>

# 重启
kill -SIGTERM <PID> && python main.py

# 查看日志
tail -f data/bot.log

# 备份
python -c "from src.utils.db_maintenance import backup_database; backup_database('data/archive.db')"

# 优化
python -c "from src.utils.db_maintenance import optimize_database; optimize_database('data/archive.db')"

# 检查
python -c "from src.utils.db_maintenance import verify_database; verify_database('data/archive.db')"
```

## 🎯 生产环境建议

1. **使用 Docker** - 隔离环境，易于部署
2. **启用 systemd** - 自动重启，开机启动
3. **配置日志轮转** - 避免日志文件过大
4. **定期备份** - 数据安全第一
5. **监控运行状态** - 及时发现问题
6. **限制文件权限** - 防止未授权访问
7. **使用 HTTPS 代理** - 如果需要（Telegram API 已经是 HTTPS）
8. **定期更新依赖** - 修复安全漏洞

## ✅ 部署完成检查

部署完成后，测试以下功能：

- [ ] Bot 启动成功
- [ ] /start 命令响应
- [ ] 发送文本消息归档
- [ ] 发送图片归档
- [ ] 标签自动生成
- [ ] 手动添加标签（#test）
- [ ] /search 搜索功能
- [ ] /tags 查看标签
- [ ] /stats 查看统计
- [ ] /language 切换语言（英文、简体中文、繁体中文）
- [ ] 非授权用户被拒绝
- [ ] 日志正常记录
- [ ] 数据库正常写入
- [ ] Telegram 频道正常存储

全部通过后，Bot 即可正式使用！🎉
