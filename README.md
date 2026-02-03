<div align="center">

# ArchiveBot

**✨ Version 1.0 | 正式发布版**

**🌍 Read this in other languages / 其他語言版本**

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

---

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

</div>

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
- 💬 **AI智能对话**：自然语言交互，智能识别意图并直接返回资源文件
- 🌏 **多语言支持**：6种语言（英语/简体中文/繁体中文/日语/韩语/西班牙语）
- 🔗 **链接智能提取**：自动提取网页标题、描述、作者、关键信息等元数据，便于后续搜索和管理
- 💾 **简化存储**：本地存储小数据 → 频道存储大文件 → 仅引用超大文件（三级策略）
- 🔒 **隐私保护**：数据完全私有，单用户模式
- 🛡️ **安全可靠**：SQL 注入防护、敏感信息过滤、线程安全
- ⚡ **高性能**：WAL 模式、索引优化、并发支持

## 🎯 适用场景

- 📝 保存重要消息和对话
- 🖼️ 收藏图片和电子书
- 📄 归档文档和资料
- 🔗 收集有用的链接
- 🎬 保存视频和音频
- 📚 构建个人知识库

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

**最简单的部署方式，无需配置 Python 环境**

#### 前置要求

- 安装 [Docker](https://www.docker.com/get-started) 和 Docker Compose
- Telegram 账号
- Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）

#### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 2. 配置 Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # 填写 bot_token, owner_id, channel_id

# 3. 验证配置（可选但推荐）
python verify_docker.py

# 4. 启动（一键部署）
docker-compose up -d --build

# 5. 查看日志
docker-compose logs -f
```

**完成！** 去 Telegram 中找到你的 Bot，发送 `/start` 开始使用。

#### 常用命令

```bash
docker-compose restart          # 重启
docker-compose logs -f          # 查看日志
docker-compose down             # 停止
git pull && docker-compose up -d --build  # 更新到最新版
```

#### 配置方式

**方式一：配置文件（推荐）**
- 编辑 `config/config.yaml`
- 所有配置写在文件中

**方式二：环境变量（适合 CI/CD）**
- 编辑 `docker-compose.yml` 中的 environment 部分
- 优先级：环境变量 > 配置文件

---

### 方式二：传统部署

#### 前置要求

- Python 3.9+
- Telegram 账号
- Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）

#### 安装步骤

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

- `bot_token`: 从 [@BotFather](https://t.me/BotFather) 获取
- `owner_id`: 你的 Telegram User ID（从 [@userinfobot](https://t.me/userinfobot) 获取）
- `storage.telegram.channels.default`: 默认私有频道 ID（用于存储文件，支持多频道分类存储）

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
| --------- | --------- | --------- | ------ |
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

| 命令 | 短命令 | 说明 |
| ------ | ------ | ------ |
| `/start` | - | 初始化 Bot，显示欢迎消息 |
| `/help` | - | 查看详细帮助信息 |
| `/search <关键词>` | `/s` | 搜索归档内容 |
| `/note` | `/n` | 添加笔记 |
| `/notes` | - | 查看所有笔记列表 |
| `/tags` | `/t` | 查看所有标签及统计 |
| `/stats` | `/st` | 查看归档统计信息 |
| `/setting` | `/set` | 系统配置 |
| `/review` | - | 活动回顾与统计（周/月/年） |
| `/rand` | `/r` | 随机查看历史归档 |
| `/trash` | - | 查看回收站内容 |
| `/export` | - | 导出归档数据 |
| `/backup` | - | 创建数据库备份 |
| `/ai` | - | 查看AI功能状态 |
| `/language` | `/la` | 切换界面语言 |
| `/restart` | - | 重启系统 |
| `/cancel` | - | 取消当前操作 |

### 归档内容

**直接发送任何内容即可归档！**

```text
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

```text
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
| ------ | ------ |
| 语言 | Python 3.14.2 |
| 框架 | python-telegram-bot 21.x |
| 数据库 | SQLite (WAL模式, FTS5, AI字段索引) |
| AI | httpx (Grok-4 via xAI) |
| 配置 | PyYAML |

### 架构设计

```text
ArchiveBot/
├── main.py                      # 入口文件
├── src/
│   ├── bot/                     # Bot 层
│   │   ├── commands.py          # 旧命令处理
│   │   ├── handlers.py          # 旧消息处理
│   │   ├── message_handlers.py  # 主消息处理
│   │   ├── message_aggregator.py # 消息聚合器
│   │   ├── callback_router.py   # 回调路由
│   │   ├── unknown_command.py   # 未知命令处理
│   │   ├── commands/            # 命令模块
│   │   ├── handlers/            # 处理器模块
│   │   └── callbacks/           # 回调处理器
│   ├── core/                    # 核心业务
│   │   ├── analyzer.py          # 内容分析
│   │   ├── tag_manager.py       # 标签管理
│   │   ├── storage_manager.py   # 存储管理
│   │   ├── search_engine.py     # 搜索引擎
│   │   ├── note_manager.py      # 笔记管理
│   │   ├── trash_manager.py     # 回收站管理
│   │   ├── export_manager.py    # 数据导出
│   │   ├── backup_manager.py    # 备份管理
│   │   ├── review_manager.py    # 内容回顾
│   │   ├── ai_session.py        # AI会话管理
│   │   ├── ai_cache.py          # AI缓存基类
│   │   └── ai_data_cache.py     # AI数据缓存
│   ├── ai/                      # AI 功能
│   │   ├── summarizer.py        # AI摘要生成
│   │   ├── chat_router.py       # 智能对话路由
│   │   ├── fallback.py          # AI降级策略
│   │   ├── knowledge_base.py    # 知识库
│   │   ├── request_queue.py     # 请求队列
│   │   ├── response_optimizer.py # 响应优化器
│   │   ├── prompts/             # 提示词模板
│   │   ├── functions/           # 函数调用
│   │   ├── operations/          # AI操作
│   │   └── providers/           # AI提供商配置
│   ├── storage/                 # 存储层
│   │   ├── base.py              # 存储基类
│   │   ├── database.py          # 数据库存储
│   │   └── telegram.py          # Telegram存储
│   ├── models/                  # 数据模型
│   │   └── database.py          # 数据库模型
│   ├── utils/                   # 工具模块
│   │   ├── config.py            # 配置管理
│   │   ├── logger.py            # 日志系统
│   │   ├── i18n.py              # 国际化
│   │   ├── language_context.py  # 语言上下文
│   │   ├── message_builder.py   # 消息构建框架
│   │   ├── validators.py        # 输入验证
│   │   ├── helpers.py           # 辅助函数
│   │   ├── constants.py         # 常量定义
│   │   ├── file_handler.py      # 文件处理
│   │   ├── link_extractor.py    # 链接元数据提取
│   │   ├── note_storage_helper.py # 笔记存储助手
│   │   ├── auto_installer.py    # 自动安装器
│   │   ├── db_maintenance.py    # 数据库维护
│   │   └── formatters/          # 消息格式化器
│   └── locales/                 # 语言文件
│       ├── en.json              # 英语
│       ├── zh-CN.json           # 简体中文
│       ├── zh-TW.json           # 繁体中文
│       ├── ja.json              # 日语
│       ├── ko.json              # 韩语
│       └── es.json              # 西班牙语
└── config/
    └── config.yaml              # 配置文件
```

## 🤖 AI功能（可选）

ArchiveBot 支持云端 AI 服务，可以**自动**生成内容摘要、提取关键点、智能分类、推荐标签，大幅提升内容管理效率。

### 支持的AI服务

| 提供商 | 模型 | 特点 | 推荐场景 |
| -------- | ------ | ------ | ---------- |
| **xAI** | Grok-4 | 多语言理解强，速度快 | 默认推荐 |
| **OpenAI** | GPT-4/GPT-3.5 | 功能最强，效果最好 | 预算充足 |
| **Anthropic** | Claude 3.5 | 性价比高，中文好 | 成本敏感 |
| **阿里云** | 通义千问 | 国内服务，访问稳定 | 国内用户 |

💡 **轻量级设计**：仅使用 HTTP API 调用，无需安装庞大的 SDK

### AI功能亮点

✅ **智能摘要**：自动生成30-100字精简总结  
✅ **关键点提取**：提炼3-5个核心观点  
✅ **智能分类**：自动归类到合适的category  
✅ **精准标签**：生成5个可搜索的专业标签  
✅ **智能对话**：自然语言交互，自动识别意图和语言  
✅ **提示词工程**：角色扮演 + Few-Shot + 思维链优化  
✅ **语言检测**：自动识别中/英文内容  
✅ **智能降级**：根据内容长度调整分析深度  
✅ **多语言优化**：简体/繁体/英文术语自适应  

### 搜索增强

✅ **分页展示**：10项/页，左右箭头导航  
✅ **AI解析按钮**：🤖 格式展示，一键查看AI分析  
✅ **快速查看**：点击查看完整AI摘要/标签/分类  
✅ **直接跳转**：点击标题链接跳转频道消息  

### ⚠️ 不启用AI的影响

如果选择不启用AI功能，以下功能将**不可用**：

❌ **自动摘要生成** - 无法自动生成内容摘要  
❌ **AI智能标签** - 无法自动生成AI推荐标签  
❌ **智能分类** - 无法自动分类内容  
❌ **关键点提取** - 无法提取内容关键观点  
❌ **智能对话** - 无法使用自然语言交互  
❌ **搜索AI解析** - 搜索结果无🤖按钮和AI信息  

**✅ 不受影响的核心功能：**

✅ 内容归档存储  
✅ 手动标签（#tag）  
✅ 全文搜索（FTS5）  
✅ 笔记系统  
✅ 回收站  
✅ 数据导出/备份  
✅ 所有命令正常使用  

> 💡 **建议**：即使不启用AI，ArchiveBot的核心归档和搜索功能依然完整可用。可以先使用基础功能，后续需要时再启用AI。

### 快速启用 AI

1. **配置API密钥**

编辑 `config/config.yaml`:

```yaml
ai:
  enabled: true              # 启用AI功能
  auto_summarize: true       # 自动生成摘要
  auto_generate_tags: true   # 自动生成AI标签
  api:
    provider: xai            # 提供商: xai/openai/anthropic/qwen
    api_key: 'xai-xxx'       # API密钥
    base_url: 'https://api.x.ai/v1'  # API端点
    model: grok-4-1-fast-non-reasoning  # 生成回复的快速模型
    reasoning_model: grok-4-1-fast-reasoning  # 意图分析的推理模型
    max_tokens: 1000         # 最大token数
    timeout: 30              # 请求超时（秒）
```

**其他提供商配置示例：**

<details>
<summary>OpenAI GPT-4</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: openai
    api_key: 'sk-xxx'
    base_url: 'https://api.openai.com/v1'
    model: gpt-4-turbo       # 生成回复的模型
    reasoning_model: gpt-4-turbo  # 意图分析的推理模型
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>Anthropic Claude</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: anthropic
    api_key: 'sk-ant-xxx'
    base_url: 'https://api.anthropic.com/v1'
    model: claude-3-5-sonnet-20241022  # 生成回复的模型
    reasoning_model: claude-3-5-sonnet-20241022  # 意图分析的推理模型
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>阿里云通义千问</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: qwen
    api_key: 'sk-xxx'
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: qwen-plus         # 生成回复的模型
    reasoning_model: qwen-plus  # 意图分析的推理模型
    max_tokens: 1000
    timeout: 30
```

</details>

1. **重启Bot**

```bash
python main.py
```

1. **验证AI状态**

```bash
# 在 Telegram 中向 Bot 发送以下命令
/ai
```

1. **开始使用AI功能**

向Bot发送任何内容（文本/链接/图片/文档等），AI会自动在后台进行分析。使用 `/search` 搜索时，有AI分析的内容会显示🤖按钮，点击可查看完整AI分析结果（摘要/关键点/标签/分类）。

## 📚 文档

- 📖 [快速开始](docs/QUICKSTART.md) - 5分钟快速上手
- 🚀 [部署指南](docs/DEPLOYMENT.md) - 生产环境部署
- 🤖 [如何应用 AI PR](docs/HOW_TO_APPLY_AI_PR.md) - AI 助手 Pull Request 应用指南
- 🛠️ [开发指南](docs/DEVELOPMENT.md) - 开发环境配置和贡献指南
- 📐 [架构说明](docs/ARCHITECTURE.md) - 系统架构和设计理念

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
  - ✅ 智能意图识别和自然语言交互
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

- ✅ 用户体验优化
  - ✅ 命令别名支持（/s = /search, /t = /tags, /st = /stats, /la = /language）
  - ✅ 自动去重检测（文件MD5检测，防止重复归档）
- ✅ 内容回顾功能
  - ✅ 活动统计报告（周/月/年趋势、热门标签、每日活动）
  - ✅ 随机回顾展示（统计报告中自动包含随机历史内容）
  - ✅ `/review` 命令（按钮选择期间）
  - ✅ `/rand` 独立随机回看命令（可配置数量，快速查看历史归档）
- ✅ AI功能增强
  - ✅ 智能识别敏感内容存档指定频道
  - ✅ AI参考内容排除指定存档频道
  - ✅ AI参考内容排除指定标签与分类
- ✅ 存档功能增强
  - ✅ 根据转发来源指定存档频道
  - ✅ 个人直接发送文档指定存档频道
  - ✅ 根据标签指定存档频道

### 📝 第四阶段 (未来规划)

- 🔄 批量操作（底层API已完成，UI待开发）
  - 🚧 批量标签替换 API（replace_tag）
  - 🚧 批量标签移除 API
  - 🚧 批量操作用户界面（命令/按钮）
  - 🚧 批量删除/恢复
  - 🚧 批量导出
- 🚧 高级搜索
  - 🚧 组合筛选
  - 🚧 时间范围
  - 🚧 内容类型筛选
- 🔮 **AI功能增强**
  - 🚧 语音转文字（Whisper API）
  - 🚧 OCR图片文字识别
  - 🚧 智能内容相似度分析
- 🔮 **扩展功能**
  - 🚧 Web管理界面
  - 🚧 RESTful API接口
  - 🚧 云存储集成（Google Drive/阿里云盘）
  - 🚧 增强型URL内容反爬获取
- 🔮 **性能优化**
  - 🚧 缓存机制优化
  - 🚧 异步处理增强
  - 🚧 批量操作优化

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT License](LICENSE)

## 🙏 致谢

### 特别感谢

- **[@WangPanBOT](https://t.me/WangPanBOT)** - Telegram 网盘机器人项目，作为本项目的灵感来源，展示了 Telegram Bot 在个人内容管理方面的巨大潜力

### 开源项目

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 优秀的 Telegram Bot 框架，强大而易用
- [SQLite](https://www.sqlite.org/) - 可靠的嵌入式数据库，轻量且高效

### AI 服务提供商

- [xAI](https://x.ai/) - Grok-4 快速推理模型
- [OpenAI](https://openai.com/) - GPT 系列模型
- [Anthropic](https://anthropic.com/) - Claude 系列模型
- [阿里云](https://www.aliyun.com/) - 通义千问模型

## 📧 联系方式

- **GitHub Issues**: [提交问题](https://github.com/tealun/ArchiveBot/issues)
- **X (Twitter)**: [@TealunDu](https://x.com/TealunDu)
- **Email**: <tealun@gmail.com>

### 交流群组

- **中文交流群**: [@ArchiveBotCN](https://t.me/joinchat/3753827356)
- **English Group**: [@ArchiveBotEN](https://t.me/joinchat/3877196244)

---

## ⚠️ 免责声明

### 使用须知

1. **个人使用**：本项目仅供学习研究和个人使用，不得用于商业用途或违法活动
2. **服务条款**：使用本项目时请严格遵守 [Telegram 服务条款](https://telegram.org/tos)和相关 API 使用政策
3. **内容责任**：用户对通过 Bot 归档的所有内容负全部责任，开发者不对用户存储的内容承担任何责任
4. **数据安全**：本项目为本地部署工具，数据存储在用户自己的环境中。请妥善保管配置文件和数据库，防止敏感信息泄露

### 第三方服务

1. **AI 服务**：使用 AI 功能时，您的内容会发送至第三方 AI 服务商（xAI/OpenAI/Anthropic/阿里云）。请确保遵守这些服务商的使用条款和隐私政策
2. **API 使用**：用户需自行申请并合法使用各项第三方服务的 API 密钥，因 API 滥用产生的后果由用户自行承担

### 知识产权与隐私

1. **版权保护**：请勿使用本项目归档受版权保护的内容，或侵犯他人知识产权的材料
2. **隐私尊重**：请勿未经授权归档他人的私密信息或对话内容
3. **开源协议**：本项目采用 MIT License，但不包含任何担保或保证

### 无担保声明

1. **按原样提供**：本软件按"原样"提供，不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性
2. **风险自负**：使用本项目产生的任何直接或间接损失（包括但不限于数据丢失、服务中断、业务损失等），开发者概不负责
3. **安全风险**：虽然项目采取了安全措施，但任何软件都可能存在未知漏洞。用户应自行评估安全风险

### 法律合规

1. **地区法律**：请确保在您所在地区使用本项目符合当地法律法规
2. **禁止违法**：严禁使用本项目从事任何违法违规活动，包括但不限于传播违法信息、侵犯隐私、网络攻击等

---
