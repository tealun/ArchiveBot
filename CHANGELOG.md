# Changelog

All notable changes to ArchiveBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-31

### 🎉 正式发布 / Official Release

ArchiveBot v1.0 正式发布！这是第一个生产就绪版本，包含完整的核心功能和稳定的架构。

**ArchiveBot v1.0 is officially released!** This is the first production-ready version with complete core features and stable architecture.

---

### ✨ 核心功能 / Core Features

#### 智能归档 / Smart Archiving
- 📦 支持 11 种内容类型：文本、链接、图片、视频、文档、电子书、音频、语音、动画、贴纸、联系人、位置
- 🤖 AI 智能分析（Grok-4）：自动生成摘要、提取关键点、智能分类、推荐标签
- 🏷️ 自动标签系统：内容类型标签 + 手动标签（#tag）+ AI 智能标签
- 💾 三级存储策略：数据库（文本/链接）→ Telegram 频道（媒体文件 0-2GB）→ 仅引用（>2GB）

#### 搜索与检索 / Search & Retrieval
- 🔍 FTS5 全文搜索引擎，支持中文分词和模糊匹配
- 📄 分页展示（10项/页），智能导航按钮
- 🏷️ 标签筛选，支持多标签组合
- 📊 高级统计：归档总数、标签数、存储容量、最后归档时间

#### AI 对话与交互 / AI Chat & Interaction
- 💬 AI 智能对话：自然语言交互，理解用户意图
- 🎯 Function Calling 架构：执行系统命令（search/tags/notes/review）
- 📚 知识库查询：智能搜索归档内容，直接返回资源文件
- 🚫 严格约束：禁止虚构内容，基于真实数据回答

#### 笔记管理 / Notes Management
- 📝 关联笔记：为归档添加笔记，支持全文搜索
- 📋 独立笔记：快速记录想法，不依赖归档
- 🔍 笔记搜索：按关键词搜索所有笔记
- 🤖 AI 精炼：智能优化笔记内容，提取核心要点

#### 数据管理 / Data Management
- 🗑️ 回收站：软删除机制，30天内可恢复
- 💾 导出功能：支持 JSON/HTML/Markdown 格式
- 🔄 备份管理：手动备份 + 自动备份调度（可配置）
- ❤️ 精选收藏：一键标记重要内容，快速筛选
- ↗️ 快速转发：一键转发归档到频道或对话

#### 回顾与统计 / Review & Statistics
- 🎲 随机回顾：随机展示 N 条归档，重温旧内容
- 📊 活动概要：按周/月/季度/年统计归档活动
- 📈 内容分布：各类型内容数量统计
- 🏷️ 标签分析：最常用标签、标签云

#### 国际化 / Internationalization
- 🌏 **6 种语言支持**：英语、简体中文、繁体中文、日语、韩语、西班牙语
- 🔄 语言切换：`/language` 命令即时切换界面语言
- 📝 内容语言自适应：AI 自动识别内容语言，使用对应语言生成分析结果
- 🗂️ 多语言配置模板：提供 6 种语言的配置文件和环境变量示例

#### 网页存档 / Web Archiving
- 🌐 智能网页提取：自动识别 URL，提取标题、描述、作者、发布日期
- 🎨 内容优化：移除广告和导航栏，保留核心内容
- 📊 元数据提取：网页标题、描述、关键信息智能分析

---

### 🏗️ 技术架构 / Technical Architecture

#### 框架与存储 / Framework & Storage
- 🐍 Python 3.9+，基于 python-telegram-bot 21.x
- 💾 SQLite 数据库（WAL 模式 + FTS5 全文搜索 + AI 字段索引）
- 📦 模块化设计：Bot 层、业务逻辑层、AI 层、存储层清晰分离
- 🔄 消息聚合框架：批量转发自动聚合处理

#### AI 集成 / AI Integration
- 🤖 轻量 httpx 调用（2MB vs 150MB SDK）
- 🎯 Grok-4 API 支持：Fast 和 Reasoning 双模型
- 📝 提示词工程：内容语言自适应、区域术语优化
- 🚀 AI 数据缓存：7天 TTL，减少重复调用

#### 消息构建框架 / Message Builder Framework
- 📋 统一列表格式：搜索结果/标签列表/AI 资源回复复用同一框架
- 📱 资源发送：直接返回媒体文件（图片/视频/文档）
- 🔗 智能跳转：点击结果可跳转到频道原消息
- 🎨 格式优化：Markdown 支持，表情符号增强可读性

#### 部署与运维 / Deployment & Operations
- 🐳 Docker 支持：一键部署，零配置
- ⚙️ 灵活配置：YAML 配置文件 + 环境变量双重支持
- 📊 健康检查：Docker healthcheck 自动重启
- 🔒 安全设计：单用户模式、owner_only 装饰器、SQL 注入防护

---

### 📦 依赖管理 / Dependencies

**核心依赖**（已锁定版本）：
- python-telegram-bot==20.7 (Telegram Bot 框架)
- PyYAML==6.0.2 (配置管理)
- python-dotenv==1.0.0 (环境变量)
- httpx==0.25.2 (AI API 调用)
- beautifulsoup4==4.12.3 (网页解析)
- lxml==6.0.2 (XML/HTML 处理)
- trafilatura==2.0.0 (网页内容提取)
- readability-lxml==0.8.4.1 (可读性优化)

---

### 📝 系统命令 / System Commands

| 命令 | 说明 | Command | Description |
|------|------|---------|-------------|
| `/start` | 初始化机器人 | `/start` | Initialize bot |
| `/help` | 查看帮助 | `/help` | View help |
| `/search` `/s` | 搜索归档 | `/search` `/s` | Search archives |
| `/tags` `/t` | 查看标签 | `/tags` `/t` | View tags |
| `/stats` `/st` | 统计信息 | `/stats` `/st` | Statistics |
| `/notes` | 笔记列表 | `/notes` | Notes list |
| `/note` `/n` | 添加笔记 | `/note` `/n` | Add note |
| `/review` | 活动回顾 | `/review` | Activity review |
| `/rand` `/r` | 随机回顾 | `/rand` `/r` | Random review |
| `/trash` | 回收站 | `/trash` | Trash bin |
| `/export` | 导出数据 | `/export` | Export data |
| `/backup` | 备份管理 | `/backup` | Backup management |
| `/ai` | AI 状态 | `/ai` | AI status |
| `/language` `/la` | 切换语言 | `/language` `/la` | Switch language |
| `/setting` `/set` | 系统配置 | `/setting` `/set` | System settings |

---

### 🎯 使用场景 / Use Cases

- 📚 **知识管理**：保存文章、电子书、学习资料
- 🔗 **链接收藏**：收集有用的网站、工具、资源
- 💼 **工作资料**：归档项目文档、会议记录、代码片段
- 🎬 **媒体收藏**：保存图片、视频、音频、GIF
- 📝 **笔记记录**：快速记录想法、待办事项、灵感
- 🗂️ **信息整理**：通过标签和搜索快速找到需要的内容

---

### 🛠️ 部署方式 / Deployment Methods

#### Docker 部署（推荐）
```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
cp config/config.template.yaml config/config.yaml
# 编辑 config.yaml 填写配置
docker compose up -d --build
```

#### 传统部署
```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
pip install -r requirements.txt
cp config/config.template.yaml config/config.yaml
# 编辑 config.yaml 填写配置
python main.py
```

---

### 📚 文档 / Documentation

- [README.md](README.md) - 项目简介（简体中文）
- [README.en.md](README.en.md) - Project Introduction (English)
- [README.zh-TW.md](README.zh-TW.md) - 專案介紹（繁體中文）
- [README.ja.md](README.ja.md) - プロジェクト紹介（日本語）
- [README.ko.md](README.ko.md) - 프로젝트 소개（한국어）
- [README.es.md](README.es.md) - Introducción del Proyecto (Español)
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - 快速开始指南
- [docs/DOCKER_QUICK_START.md](docs/DOCKER_QUICK_START.md) - Docker 部署指南
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - 开发指南
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - 系统架构文档
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - 部署文档

---

### 🔧 配置文件 / Configuration Files

- `config/config.template.yaml` - 配置模板（简体中文）
- `config/config.template.en.yaml` - Configuration Template (English)
- `config/config.template.zh-TW.yaml` - 配置範本（繁體中文）
- `config/config.template.ja.yaml` - 設定テンプレート（日本語）
- `config/config.template.ko.yaml` - 구성 템플릿（한국어）
- `config/config.template.es.yaml` - Plantilla de Configuración (Español)

---

### 🙏 致谢 / Acknowledgments

感谢以下开源项目和服务：

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 优秀的 Telegram Bot 框架
- [Grok-4 by xAI](https://x.ai) - 强大的 AI 能力支持
- [SQLite](https://www.sqlite.org/) - 可靠的嵌入式数据库
- [Trafilatura](https://github.com/adbar/trafilatura) - 高效的网页内容提取工具

---

### 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

### 🔗 链接 / Links

- **GitHub**: https://github.com/tealun/ArchiveBot
- **Issues**: https://github.com/tealun/ArchiveBot/issues
- **Discussions**: https://github.com/tealun/ArchiveBot/discussions

---

**下一步计划 / Next Steps**: 查看 [DEVELOPMENT.md](docs/DEVELOPMENT.md) 了解项目路线图

[1.0.0]: https://github.com/tealun/ArchiveBot/releases/tag/v1.0.0
