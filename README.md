# ArchiveBot

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

基于 Telegram Bot 的个人内容归档系统 | Personal Content Archiving System for Telegram

## 📖 项目简介

ArchiveBot 是一个开源的 Telegram Bot，帮助你将 Telegram 中的各类内容（文件、图片、视频、文字、链接等）进行智能分类和归档，打造个人知识库和内容收藏系统。

**核心定位**：个人实例工具，每个人部署自己的 Bot，数据完全私有。

## ✨ 核心特性

- 📦 **智能归档**：自动识别 10+ 种内容类型并分类存储
- 🏷️ **智能标签**：自动打标签，支持手动标签（#tag）
- 🔍 **全文搜索**：FTS5 全文搜索引擎，快速查找已归档的内容
- 🤖 **AI智能总结**：支持OpenAI、Claude、通义千问，自动生成摘要和标签
- 🔗 **链接智能**：自动提取网页标题、描述等元数据
- 💾 **多级存储**：Database → Telegram → Cloud → Reference
- 🌍 **多语言支持**：English | 简体中文 | 繁體中文
- 🔒 **隐私保护**：数据完全私有，单用户模式
- 🛡️ **安全可靠**：SQL 注入防护、敏感信息过滤、线程安全
- ⚡ **高性能**：WAL 模式、索引优化、并发支持

## 🎯 适用场景

- 📝 保存重要消息和对话
- 🖼️ 收藏图片和表情包
- 📄 归档文档和资料
- 🔗 收集有用的链接
- 🎬 保存视频和音频
- 📚 构建个人知识库

## 🚀 快速开始

### 前置要求

- Python 3.9+
- Telegram 账号
- Bot Token（从 @BotFather 获取）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/ArchiveBot.git
cd ArchiveBot
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置 Bot**
```bash
# 复制配置模板
cp config/config.template.yaml config/config.yaml

# 编辑配置文件
nano config/config.yaml
```

**必填配置项**:
- `bot_token`: 从 @BotFather 获取
- `owner_id`: 你的 Telegram User ID（从 @userinfobot 获取）
- `telegram_channel_id`: 私有频道 ID（可选，用于存储文件）

4. **启动 Bot**
```bash
python main.py
```

5. **开始使用**

在 Telegram 中找到你的 Bot，发送 `/start` 开始使用！

📚 **详细指南**: [快速开始文档](QUICKSTART.md) | [部署指南](DEPLOYMENT.md)

## 📦 存储策略

| 内容类型 | 大小范围 | 存储方式 | 说明 |
|---------|---------|---------|------|
| 文本/链接 | - | SQLite 数据库 | 直接存储，支持全文搜索 |
| 小文件 | 0-10MB | Telegram 私有频道 | 永久可靠，不占网盘空间 |
| 中等文件 | 10MB-100MB | 云端网盘 | 占用网盘配额 |
| 大文件 | 100MB-500MB | 云端网盘（需确认） | 占用网盘配额，需用户确认 |
| 超大文件 | 500MB+ | 仅存 file_id | 不占空间，但依赖原消息 |

## 快速开始

### 1. 获取 Bot Token 和你的 ID

```bash
# 1. 找 @BotFather 创建你的 Bot，获取 Token
# 2. 找 @userinfobot 获取你的 Telegram ID
# 3. 创建私有频道，将 Bot 添加为管理员
```

### 2. 配置 Bot

```bash
# 复制配置模板
cp config/config.template.yaml config/config.yaml

# 编辑配置文件，填入：
# - bot.token: 你的 Bot Token
# - bot.owner_id: 你的 Telegram ID
# - storage.telegram.channel_id: 私有频道 ID
```

### 3. 运行 Bot

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

## 🎮 使用方法

### 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 初始化 Bot，显示欢迎消息 |
| `/help` | 查看详细帮助信息 |
| `/search <关键词>` | 搜索归档内容 |
| `/tags` | 查看所有标签及统计 |
| `/stats` | 查看归档统计信息 |
| `/summarize` | AI智能总结（需启用AI功能） |
| `/ai` | 查看AI功能状态 |
| `/language` | 切换界面语言 |

### 归档内容

**直接发送任何内容即可归档！**

```
支持的内容类型：
📝 文本消息
🔗 链接
🖼️ 图片
🎬 视频
📄 文档
🎵 音频
🎤 语音
🎭 贴纸
🎞️ 动画
```

**添加标签**:
```
发送消息时加上 #标签 即可：

这是一条测试消息 #测试 #重要
https://github.com #技术 #开源
```

### 搜索内容

```bash
# 关键词搜索
/search python

# 标签搜索
/search #技术

# 组合搜索
/search #技术 python
```

## 🛠️ 技术架构

### 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.9+ |
| 框架 | python-telegram-bot 21.0 |
| 数据库 | SQLite (WAL模式, FTS5) |
| 配置 | PyYAML |

### 架构设计

```
ArchiveBot/
├── main.py                      # 入口文件
├── src/
│   ├── bot/                     # Bot 层
│   │   ├── commands.py          # 命令处理
│   │   ├── handlers.py          # 消息处理
│   │   └── callbacks.py         # 回调处理
│   ├── core/                    # 核心业务
│   │   ├── analyzer.py          # 内容分析
│   │   ├── tag_manager.py       # 标签管理
│   │   ├── storage_manager.py   # 存储管理
│   │   └── search_engine.py     # 搜索引擎
│   ├── storage/                 # 存储层
│   │   ├── database.py          # 数据库存储
│   │   └── telegram.py          # Telegram存储
│   ├── models/                  # 数据模型
│   │   └── database.py          # 数据库模型
│   ├── utils/                   # 工具模块
│   │   ├── config.py            # 配置管理
│   │   ├── logger.py            # 日志系统
│   │   ├── i18n.py              # 国际化
│   │   ├── validators.py        # 输入验证
│   │   └── db_maintenance.py    # 数据库维护
│   └── locales/                 # 语言文件
│       ├── en.json
│       ├── zh-CN.json
│       └── zh-TW.json
└── config/
    └── config.yaml              # 配置文件
```

## 🤖 AI功能（可选）

ArchiveBot支持AI智能总结功能，可以自动生成内容摘要、提取关键点、推荐标签。
🤖 [AI功能配置](docs/AI_SETUP.md) - AI智能总结设置指南
- 🔗 [链接智能处理](docs/LINK_INTELLIGENCE.md) - 网页元数据提取
- 📝 [日志系统](docs/LOGGING.md) - 日志查看和管理
- 
### 支持的AI服务

- **OpenAI GPT-4/3.5** - 功能强大，效果最好
- **Anthropic Claude** - 性价比高，中文支持好
- **阿里云通义千问** - 国内服务，访问稳定

### 快速启用

1. **安装AI依赖**
```bash
# 根据选择的服务安装
pip install openai          # OpenAI
pip install anthropic       # Claude
pip install dashscope       # 通义千问

# 或全部安装
pip install -r requirements-ai.txt
```

2. **配置API密钥**

编辑 `config/config.yaml`:
```yaml
ai:
  enabled: true
  api:
    provider: openai  # 或 claude, qwen
    api_key: 'your-api-key-here'
    model: gpt-4-turbo
```

3. **使用AI功能**
```bash
# 查看AI状态
/ai

# 生成摘要（回复归档消息）
/summarize
```

📖 **详细配置**: 参见 [AI功能配置指南](docs/AI_SETUP.md)

## 📚 文档

- 📖 [快速开始](QUICKSTART.md) - 5分钟快速上手
- 🏗️ [架构设计](docs/ARCHITECTURE.md) - 系统架构详解
- 💻 [开发指南](docs/DEVELOPMENT.md) - 开发流程和规范
- 🚀 [部署指南](DEPLOYMENT.md) - 生产环境部署
- 🔒 [安全清单](SECURITY.md) - 安全最佳实践
- 🧪 [测试清单](TESTING.md) - 完整测试指南
- 📊 [MVP 报告](MVP_REPORT.md) - 第一阶段完成报告

## 🔒 安全特性

- ✅ **SQL 注入防护** - 参数化查询 + ESCAPE 转义
- ✅ **输入验证** - 所有输入经过严格验证和清理
- ✅ **敏感信息过滤** - 日志自动过滤 token 和 ID
- ✅ **线程安全** - RLock + WAL 模式
- ✅ **身份验证** - owner_only 装饰器保护
- ✅ **错误处理** - 完善的异常处理和恢复机制

## 🎯 开发状态

- ✅ **MVP 第一阶段** - 已完成
- 🚧 **第二阶段** - 计划中
  - 云盘集成（Google Drive, 阿里云盘）
  - 数据导出功能
  - Web 管理界面
  - 定时备份

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/yourusername/ArchiveBot.git

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试
python test_bot.py
```

## 📄 许可证

本项目采用 [MIT License](LICENSE)

## 🙏 致谢

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 优秀的 Telegram Bot 框架
- [SQLite](https://www.sqlite.org/) - 可靠的嵌入式数据库

## 📧 联系方式

- GitHub Issues: [提交问题](https://github.com/yourusername/ArchiveBot/issues)
- Email: your.email@example.com

---

**免责声明**: 本项目仅供学习和个人使用，请遵守 Telegram 服务条款。

⭐ 如果这个项目对你有帮助，请给个星标！

- **语言**：Python 3.9+
- **Bot 框架**：python-telegram-bot
- **数据库**：SQLite
- **网盘 SDK**：各网盘官方 SDK
- **AI 能力**：可选集成 GPT/Claude 进行内容分析

## 路线图

### MVP (v0.1) - 2-3周
- [x] 基础 Bot 框架
- [x] 所有者身份验证
- [x] 文本/链接归档
- [x] Telegram 频道存储
- [ ] 简单搜索功能

### v1.0 - 1-2个月
**存储与管理**：
- [ ] Google Drive / 阿里云盘集成
- [ ] 智能去重
- [ ] 增量备份

**用户体验**：
- [ ] 快速笔记和批注
- [ ] 批量操作
- [ ] 快捷命令和别名
- [ ] 回顾和统计

### v1.5 - 2-3个月
**AI 赋能**：
- [ ] 智能摘要生成
- [ ] OCR 和内容提取
- [ ] 自动分类和整理
- [ ] 翻译功能

**数据增强**：
- [ ] 关联和引用系统
- [ ] 版本管理
- [ ] 高级筛选和视图
- [ ] 数据分析面板

### v2.0 - 长期迭代
**知识管理**：
- [ ] 智能问答（RAG）
- [ ] 知识图谱
- [ ] 归档模板
- [ ] 时光机

**集成扩展**：
- [ ] Web 管理界面
- [ ] 浏览器扩展
- [ ] RSS 订阅
- [ ] 社交媒体同步

**高级功能**：
- [ ] 内容监控
- [ ] 游戏化
- [ ] 加密功能

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 开源协议

MIT License

## 免责声明

本项目仅供个人合法内容归档使用。用户对其存储内容负完全责任。
