# ArchiveBot 快速开始指南

5分钟完成部署，开始使用你的个人归档助手！

## 📋 准备工作

你需要准备：
- Python 3.9+ 环境
- Telegram 账号
- 5分钟时间 ⏰

## 🚀 三步快速部署

### 第一步：获取必要信息

#### 1.1 创建你的 Bot
1. 在 Telegram 找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新 Bot
3. 输入 Bot 名称（如：`My Archive Bot`）
4. 输入 Bot 用户名（必须以 bot 结尾，如：`myarchive_bot`）
5. **保存** BotFather 返回的 Token（类似：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

#### 1.2 获取你的 Telegram ID
1. 在 Telegram 找到 [@userinfobot](https://t.me/userinfobot)
2. 点击 **Start** 或发送任意消息
3. **保存** 返回的数字 ID（如：`123456789`）

#### 1.3 创建私有频道（存储媒体文件）
1. 创建新频道（设置为**私有**）
2. 频道名称随意（如：`My Archive Storage`）
3. 将你的 Bot 添加为**管理员**（搜索你的 Bot 用户名）
4. 赋予 Bot **发送消息**权限
5. 在频道发送任意消息，然后转发给 [@userinfobot](https://t.me/userinfobot)
6. **保存** 返回的频道 ID（负数，类似：`-1001234567890`）

### 第二步：安装配置

#### 2.1 克隆项目
```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

#### 2.2 安装依赖
```bash
pip install -r requirements.txt
```

#### 2.3 配置 Bot
```bash
# 复制配置模板
cp config/config.template.yaml config/config.yaml

# 编辑配置（Windows 用 notepad，Mac/Linux 用 nano）
notepad config/config.yaml  # Windows
nano config/config.yaml     # Mac/Linux
```

**填入第一步获取的信息**：
```yaml
bot:
  token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # 你的 Bot Token
  owner_id: 123456789                              # 你的 Telegram ID
  language: "zh-CN"                                # 界面语言

storage:
  telegram:
    channel_id: -1001234567890  # 你的频道 ID（必填）

# AI 功能（可选）
ai:
  enabled: false  # 暂时不启用，后续可配置
```

💡 **提示**：只需填写 `bot_token`、`owner_id` 和 `channel_id` 三项即可，其他保持默认。

### 第三步：启动使用

```bash
python main.py
```

看到以下信息表示启动成功：
```
Bot is ready! Starting polling...
```

## 🎮 开始使用

### 1. 初始化 Bot
在 Telegram 中找到你的 Bot，点击 **Start** 或发送 `/start`

### 2. 发送内容归档

**直接发送任何内容即可自动归档！**

支持的内容类型：
- 📝 文本消息
- 🔗 链接（自动提取标题）
- 🖼️ 图片
- 🎬 视频
- 📄 文档  
- 🎵 音频
- 🎤 语音消息
- 🎭 贴纸/动图

### 3. 添加标签

发送内容时加上 `#标签` 即可：
```
这是一篇关于 Python 的文章 #Python #编程 #学习
https://github.com #技术 #开源
```

### 4. 搜索归档

```
/search Python        # 关键词搜索
/search #Python       # 标签搜索
/search #Python 教程   # 组合搜索
```

## 📱 常用命令

| 命令 | 功能 |
|------|------|
| `/start` | 显示欢迎信息 |
| `/help` | 查看帮助 |
| `/search <关键词>` | 搜索归档内容 |
| `/tags` | 查看所有标签及统计 |
| `/stats` | 查看归档统计信息 |
| `/language` | 切换界面语言 |

## 🌍 多语言支持

支持三种语言：
- 🇬🇧 **English** (en)
- 🇨🇳 **简体中文** (zh-CN)
- 🇹🇼 **繁體中文** (zh-TW)

使用 `/language` 命令切换。

## 🔧 常见问题

### Q1: Bot 无法启动？
**检查清单**：
- ✅ Bot Token 是否正确填写
- ✅ owner_id 是否正确填写
- ✅ channel_id 是否正确填写
- ✅ Bot 是否已添加到频道且有管理员权限
- ✅ Python 版本是否 3.9+

**查看日志**：
```bash
# Windows
type data\bot.log

# Mac/Linux
cat data/bot.log
```

### Q2: Bot 不响应消息？
确认你的 Telegram ID 与配置文件中的 `owner_id` 完全一致。

### Q3: 频道 ID 怎么获取？
1. 在频道发送任意消息
2. 将消息转发给 [@userinfobot](https://t.me/userinfobot)
3. Bot 会返回频道信息，其中包含 ID

### Q4: 如何重置数据库？
```bash
# 停止 Bot（Ctrl+C）
# 删除数据库文件
rm data/archive.db  # Mac/Linux
del data\archive.db # Windows
# 重新启动 Bot
python main.py
```

## 🎯 下一步

### 启用 AI 功能（可选）
如需自动摘要和智能标签，请参考：
📖 [AI 功能配置指南](docs/AI_SETUP.md)

### 生产环境部署
如需长期稳定运行，请参考：
🚀 [部署指南](DEPLOYMENT.md)

### 了解技术细节
如有兴趣了解系统架构，请参考：
🏗️ [架构设计文档](docs/ARCHITECTURE.md)

---

**🎉 恭喜！你已成功部署 ArchiveBot**

开始享受你的个人知识归档系统吧！
