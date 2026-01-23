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
- 🏷️ **智能标签**：自动打标签，支持手动标签（#tag）+ AI智能标签
- 🔍 **全文搜索**：FTS5 全文搜索引擎，分页展示（10项/页）
- ❤️ **精选收藏**：一键标记精选内容，快速筛选重要资料
- 📝 **笔记系统**：支持独立笔记和关联笔记，记录想法和心得
- ↗️ **快速转发**：一键转发归档内容到频道或其他对话
- 🗑️ **回收站**：误删除内容可恢复，30天自动清理
- 💾 **数据导出**：支持导出 Markdown/JSON 格式
- 🔄 **自动备份**：定期自动备份数据库，保障数据安全
- 🤖 **AI智能增强**：Grok-4智能分析（摘要/关键点/分类/标签）
- 🎯 **提示词工程**：角色扮演 + 上下文 + Few-Shot + 质量约束 + 思维链
- 🌏 **多语言优化**：英语/简体中文/繁体中文（含区域术语）
- 🔗 **链接智能**：自动提取网页标题、描述等元数据
- 💾 **简化存储**：Database → Telegram → Reference（三级策略）
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
git clone https://github.com/tealun/ArchiveBot.git
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

📚 **详细指南**: [快速开始文档](docs/QUICKSTART.md) | [部署指南](docs/DEPLOYMENT.md)

## 📦 存储策略

ArchiveBot 采用简化的三级存储策略，充分利用 Telegram 的免费存储空间：

| 内容类型 | 大小范围 | 存储方式 | 说明 |
|---------|---------|---------|------|
| 文本/链接 | - | SQLite 数据库 | 直接存储，支持全文搜索 |
| 媒体文件 | 0-2GB | Telegram 私有频道 | 永久可靠，file_id 转发 |
| 超大文件 | >2GB | 仅存引用信息 | 不占空间，依赖原消息 |

**核心优势**：
- ✅ 无需下载/上传，直接 file_id 转发
- ✅ 频道消息 file_id 永久有效
- ✅ 支持完整 2GB 限制
- ✅ 简单可靠，无超时风险

## 🎮 使用方法

### 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 初始化 Bot，显示欢迎消息 |
| `/help` | 查看详细帮助信息 |
| `/search <关键词>` | 搜索归档内容 |
| `/tags` | 查看所有标签及统计 |
| `/stats` | 查看归档统计信息 |
| `/note` | 进入笔记模式，为内容添加笔记 |
| `/notes` | 查看所有笔记列表 |
| `/trash` | 查看回收站内容 |
| `/export` | 导出归档数据 |
| `/backup` | 创建数据库备份 |
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
| 语言 | Python 3.14.2 |
| 框架 | python-telegram-bot 21.x |
| 数据库 | SQLite (WAL模式, FTS5, AI字段索引) |
| AI | httpx (Grok-4 via xAI) |
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
│   │   ├── search_engine.py     # 搜索引擎
│   │   ├── note_manager.py      # 笔记管理
│   │   ├── trash_manager.py     # 回收站管理
│   │   ├── export_manager.py    # 数据导出
│   │   ├── backup_manager.py    # 备份管理
│   │   └── review_manager.py    # 内容回顾
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

ArchiveBot 支持云端 AI 服务，可以自动生成内容摘要、提取关键点、智能分类、推荐标签。

### 支持的AI服务

- **Grok-4 (xAI)** - 当前默认，强大的多语言理解能力
- **OpenAI GPT-4/3.5** - 功能强大，效果最好
- **Anthropic Claude** - 性价比高，中文支持好
- **阿里云通义千问** - 国内服务，访问稳定

💡 **轻量级设计**：仅使用 HTTP API 调用，无需安装庞大的 SDK

### AI功能亮点

✅ **智能摘要**：30-100字精简总结  
✅ **关键点提取**：3-5个核心观点  
✅ **智能分类**：自动分类到适合的category  
✅ **精准标签**：5个可搜索的专业标签  
✅ **提示词工程**：角色扮演 + 上下文 + Few-Shot + 质量约束 + 思维链  
✅ **内容语言检测**：自动识别中英文内容  
✅ **智能降级**：根据内容长度调整分析深度  
✅ **多语言优化**：简体/繁体/英文术语区分  

### 搜索增强

✅ **分页展示**：10项/页，左右箭头导航  
✅ **AI解析按钮**：🤖 #2《华尔街之狼…》格式展示  
✅ **快速查看**：点击查看完整AI分析结果  
✅ **直接跳转**：点击标题链接跳转频道消息  

### 快速启用

1. **配置API密钥**

编辑 `config/config.yaml`:
```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: openai  # 支持 openai, claude, qwen
    api_key: 'xai-xxx'  # xAI API Key for Grok-4
    base_url: 'https://api.x.ai/v1'  # xAI endpoint
    model: grok-beta  # Grok-4 model
    max_tokens: 1000
    timeout: 30
```

2. **重启Bot**
```bash
python main.py
```

3. **使用AI功能**
```bash
# 查看AI状态
/ai

# 生成摘要（回复归档消息）
/summarize
```

## 📚 文档

- 📖 [快速开始](docs/QUICKSTART.md) - 5分钟快速上手
- 🚀 [部署指南](docs/DEPLOYMENT.md) - 生产环境部署

## 🔒 安全特性

- ✅ **SQL 注入防护** - 参数化查询 + ESCAPE 转义
- ✅ **输入验证** - 所有输入经过严格验证和清理
- ✅ **敏感信息过滤** - 日志自动过滤 token 和 ID
- ✅ **线程安全** - RLock + WAL 模式
- ✅ **身份验证** - owner_only 装饰器保护
- ✅ **错误处理** - 完善的异常处理和恢复机制

## 🎯 开发路线图

### ✅ 第一阶段 (已完成)
- ✅ 基础 Bot 框架和命令系统
- ✅ 智能内容分析和归档
- ✅ 全文搜索引擎 (FTS5)
- ✅ 多语言支持 (en/zh-CN/zh-TW/zh-HK/zh-MO)
- ✅ AI智能增强 (Grok-4)
  - ✅ 智能摘要/关键点/分类/标签
  - ✅ 提示词工程优化
  - ✅ 内容语言检测
  - ✅ 智能降级策略
  - ✅ 多语言术语优化
- ✅ 搜索体验优化
  - ✅ 分页展示 (10项/页)
  - ✅ AI解析按钮
  - ✅ 导航优化
- ✅ 简化的 Telegram 存储策略

### ✅ 第二阶段 (已完成)
- ✅ 笔记和批注系统
  - ✅ 独立笔记和关联笔记
  - ✅ 笔记模式快速添加
  - ✅ 笔记列表展示
  - ✅ 笔记状态显示 (📝/📝✓)
- ✅ 精选收藏功能
  - ✅ 一键标记精选 (🤍/❤️)
  - ✅ 精选筛选查询
  - ✅ 精选状态显示
- ✅ 快速操作按钮
  - ✅ 转发功能 (↗️)
  - ✅ 每条记录操作按钮
  - ✅ 归档成功消息操作按钮
- ✅ 回收站系统
  - ✅ 软删除机制
  - ✅ 内容恢复
  - ✅ 定期清理
- ✅ 数据导出功能 (Markdown/JSON/CSV)
- ✅ 自动备份系统
  - ✅ 定时备份调度（每小时检查）
  - ✅ 备份文件管理
  - ✅ 备份恢复
  - ✅ 可配置备份间隔

### ✅ 第三阶段 (已完成)
- ✅ 内容回顾功能
  - ✅ 随机回顾（get_random_archive）
  - ✅ 活动概要（get_activity_summary）
  - ✅ 命令对接（/review）
  - ✅ 期间选择（周/月/年）
- 🔄 批量操作（部分完成）
  - ✅ 批量标签移除（remove_tag_from_all）
  - ✅ 批量标签替换（replace_tag）
  - 🚧 批量操作UI界面
  - 🚧 批量删除/恢复
  - 🚧 批量导出
- 🚧 高级搜索
  - 🚧 组合筛选
  - 🚧 时间范围
  - 🚧 内容类型筛选

### 📝 第四阶段 (未来规划)
- 🔮 AI功能增强
  - 语音转文字（Whisper API）
  - OCR图片文字识别
  - 智能内容相似度分析
  - 自动去重检测
- 🔮 用户体验优化
  - 命令别名支持
  - 智能意图识别
  - 配置向导
  - 快捷键支持
- 🔮 扩展功能
  - Web管理界面
  - RESTful API接口
  - 云存储集成（Google Drive/阿里云盘）
  - 跨设备同步
- 🔮 性能优化
  - 缓存机制
  - 异步处理
  - 批量操作优化

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/tealun/ArchiveBot.git

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

- GitHub Issues: [提交问题](https://github.com/tealun/ArchiveBot/issues)

---

**免责声明**: 本项目仅供学习和个人使用，请遵守 Telegram 服务条款。

⭐ 如果这个项目对你有帮助，请给个星标！
