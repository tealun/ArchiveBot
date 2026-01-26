<div align="center">

# ArchiveBot

**📖 Read this in other languages / 其他語言版本**

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

---

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

</div>

Personal Content Archiving System for Telegram

## 📖 Introduction

ArchiveBot is an open-source Telegram Bot that helps you intelligently categorize and archive various types of content (files, images, videos, text, links, etc.) from Telegram, creating your personal knowledge base and content collection system.

**Core Philosophy**: Personal instance tool - everyone deploys their own Bot with completely private data.

## ✨ Core Features

- 📦 **Smart Archiving**: Automatically recognizes and categorizes 10+ content types
- 🏷️ **Intelligent Tagging**: Auto-tagging with manual tags (#tag) + AI-powered tags
- 🔍 **Full-Text Search**: FTS5 full-text search engine with pagination (10 items/page)
- ❤️ **Favorites Collection**: One-click favorite marking for quick access to important materials
- 📝 **Note System**: Support for standalone and linked notes to record thoughts and insights
- ↗️ **Quick Forward**: One-click forwarding of archived content to channels or chats
- 🗑️ **Recycle Bin**: Recover accidentally deleted content, auto-cleanup after 30 days
- 💾 **Data Export**: Support for Markdown/JSON format export
- 🔄 **Auto Backup**: Scheduled automatic database backups for data security
- 🤖 **AI Enhancement**: Grok-4 intelligent analysis (summary/key points/classification/tags)
- 💬 **AI Chat**: Natural language interaction with automatic intent and language detection
- � **Smart Resource Reply**: Intelligently identifies intent and directly returns resource files (no fabricated URLs)
- �🌏 **Multi-language**: English/Simplified Chinese/Traditional Chinese (with regional terms)
- 🔗 **Smart Links**: Automatic extraction of webpage titles, descriptions, and metadata
- 💾 **Simplified Storage**: Local storage for small data → Channel storage for large files → Reference-only for huge files (three-tier strategy)
- 🔒 **Privacy Protection**: Completely private data, single-user mode
- 🛡️ **Security & Reliability**: SQL injection protection, sensitive info filtering, thread-safe
- ⚡ **High Performance**: WAL mode, index optimization, concurrent support

## 🎯 Use Cases

- 📝 Save important messages and conversations
- 🖼️ Collect images and e-books
- 📄 Archive documents and materials
- 🔗 Collect useful links
- 🎬 Save videos and audio
- 📚 Build personal knowledge base

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

**Easiest way - no need to configure Python environment**

#### Prerequisites

- Install [Docker](https://www.docker.com/get-started) and Docker Compose
- Telegram account
- Bot Token (obtain from [@BotFather](https://t.me/BotFather))

#### Deployment Steps

```bash
# 1. Clone the repository
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 2. Configure the Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # Fill in bot_token, owner_id, channel_id

# 3. Start (one-command deployment)
docker-compose up -d --build

# 4. View logs
docker-compose logs -f
```

**Done!** Find your Bot on Telegram and send `/start` to begin.

#### Common Commands

```bash
docker-compose restart          # Restart
docker-compose logs -f          # View logs
docker-compose down             # Stop
git pull && docker-compose up -d --build  # Update to latest version
```

#### Configuration Methods

**Method 1: Config File (Recommended)**
- Edit `config/config.yaml`
- All settings in the file

**Method 2: Environment Variables (For CI/CD)**
- Edit environment section in `docker-compose.yml`
- Priority: Environment Variables > Config File

---

### Option 2: Traditional Deployment

#### Prerequisites

- Python 3.9+
- Telegram account
- Bot Token (obtain from [@BotFather](https://t.me/BotFather))

#### Installation

1. **Clone the repository**

```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure the Bot**

```bash
# Copy config template
cp config/config.template.yaml config/config.yaml

# Edit config file
nano config/config.yaml
```

**Required configuration**:

- `bot_token`: Obtain from [@BotFather](https://t.me/BotFather)
- `owner_id`: Your Telegram User ID (get from [@userinfobot](https://t.me/userinfobot))
- `storage.telegram.channels.default`: Default private channel ID (for file storage, supports multi-channel categorized storage)

4. **Start the Bot**

```bash
python main.py
```

5. **Start using**

Find your Bot on Telegram and send `/start` to begin!

📚 **Detailed guides**: [Quick Start Guide](docs/QUICKSTART.md) | [Deployment Guide](docs/DEPLOYMENT.md)

## 📦 Storage Strategy

ArchiveBot uses a simplified three-tier storage strategy, fully leveraging Telegram's free storage:

| Content Type | Size Range | Storage Method | Description |
|-------------|-----------|----------------|-------------|
| Text/Links | - | SQLite database | Direct storage with full-text search support |
| Media files | 0-2GB | Telegram private channel | Permanent & reliable, file_id forwarding |
| Huge files | >2GB | Reference info only | No space occupied, depends on original message |

**Key advantages**:

- ✅ No download/upload needed, direct file_id forwarding
- ✅ Channel message file_id permanently valid
- ✅ Full 2GB limit support
- ✅ Simple & reliable, no timeout risks

## 🎮 Usage

### Command List

| Command | Description |
|---------|-------------|
| `/start` | Initialize Bot, show welcome message |
| `/help` | View detailed help information |
| `/search <keyword>` | Search archived content |
| `/tags` | View all tags and statistics |
| `/stats` | View archive statistics |
| `/notes` | View all notes list |
| `/review` | Activity review and statistics (weekly/monthly/yearly) |
| `/trash` | View recycle bin contents |
| `/export` | Export archived data |
| `/backup` | Create database backup |
| `/ai` | View AI feature status |
| `/language` | Switch interface language |

### Archive Content

**Simply send any content to archive!**

```
Supported content types:
📝 Text messages
🔗 Links
🖼️ Images
🎬 Videos
📄 Documents
🎵 Audio
🎤 Voice
🎭 Stickers
🎞️ Animations
```

**Add tags**:

```text
Include #tag when sending:

This is a test message #test #important
https://github.com #tech #opensource
```

### Search Content

```bash
# Keyword search
/search python

# Tag search
/search #tech

# Combined search
/search #tech python
```

## 🛠️ Technical Architecture

### Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.14.2 |
| Framework | python-telegram-bot 21.x |
| Database | SQLite (WAL mode, FTS5, AI field indexing) |
| AI | httpx (Grok-4 via xAI) |
| Config | PyYAML |

### Architecture Design

```text
ArchiveBot/
├── main.py                      # Entry point
├── src/
│   ├── bot/                     # Bot layer
│   │   ├── commands.py          # Command handlers
│   │   ├── handlers.py          # Message handlers
│   │   ├── callbacks.py         # Callback handlers
│   │   ├── message_aggregator.py # Message aggregator
│   │   └── unknown_command.py   # Unknown command handler
│   ├── core/                    # Core business
│   │   ├── analyzer.py          # Content analyzer
│   │   ├── tag_manager.py       # Tag manager
│   │   ├── storage_manager.py   # Storage manager
│   │   ├── search_engine.py     # Search engine
│   │   ├── note_manager.py      # Note manager
│   │   ├── trash_manager.py     # Trash manager
│   │   ├── export_manager.py    # Export manager
│   │   ├── backup_manager.py    # Backup manager
│   │   ├── review_manager.py    # Content review
│   │   ├── ai_session.py        # AI session manager
│   │   ├── ai_cache.py          # AI cache base
│   │   └── ai_data_cache.py     # AI data cache
│   ├── ai/                      # AI features
│   │   ├── summarizer.py        # AI summary generator
│   │   ├── chat_router.py       # Smart chat router
│   │   ├── fallback.py          # AI fallback strategy
│   │   └── prompts/             # Prompt templates
│   │       ├── chat.py
│   │       ├── note.py
│   │       ├── summarize.py
│   │       └── title.py
│   ├── storage/                 # Storage layer
│   │   ├── base.py              # Storage base
│   │   ├── database.py          # Database storage
│   │   └── telegram.py          # Telegram storage
│   ├── models/                  # Data models
│   │   └── database.py          # Database models
│   ├── utils/                   # Utility modules
│   │   ├── config.py            # Config manager
│   │   ├── logger.py            # Logging system
│   │   ├── i18n.py              # Internationalization
│   │   ├── language_context.py  # Language context
│   │   ├── message_builder.py   # Message builder framework
│   │   ├── validators.py        # Input validation
│   │   ├── helpers.py           # Helper functions
│   │   ├── constants.py         # Constants
│   │   ├── file_handler.py      # File handler
│   │   ├── link_extractor.py    # Link metadata extractor
│   │   └── db_maintenance.py    # Database maintenance
│   └── locales/                 # Language files
│       ├── en.json
│       ├── zh-CN.json
│       └── zh-TW.json
└── config/
    └── config.yaml              # Config file
```

## 🤖 AI Features (Optional)

ArchiveBot supports cloud AI services that can **automatically** generate content summaries, extract key points, intelligently classify, and recommend tags, significantly improving content management efficiency.

### Supported AI Services

| Provider | Model | Features | Recommended For |
|----------|-------|----------|-----------------|
| **xAI** | Grok-4 | Strong multilingual understanding, fast | Default recommendation |
| **OpenAI** | GPT-4/GPT-3.5 | Most powerful, best results | Sufficient budget |
| **Anthropic** | Claude 3.5 | Cost-effective, good Chinese support | Cost-conscious |
| **Alibaba Cloud** | Qwen | Domestic service, stable access | Users in China |

💡 **Lightweight Design**: Only uses HTTP API calls, no need to install bulky SDKs

### AI Feature Highlights

✅ **Smart Summary**: Auto-generate 30-100 word concise summaries  
✅ **Key Points**: Extract 3-5 core insights  
✅ **Smart Classification**: Auto-categorize into appropriate categories  
✅ **Precise Tags**: Generate 5 searchable professional tags  
✅ **Smart Chat**: Natural language interaction with automatic intent and language detection  
✅ **Prompt Engineering**: Role-playing + Few-Shot + Chain-of-Thought optimization  
✅ **Language Detection**: Auto-detect Chinese/English content  
✅ **Smart Fallback**: Adjust analysis depth based on content length  
✅ **Multi-language Optimization**: Adaptive Simplified/Traditional/English terminology  

### Search Enhancement

✅ **Pagination**: 10 items/page with left/right arrow navigation  
✅ **AI Analysis Button**: 🤖 formatted display, one-click AI analysis view  
✅ **Quick View**: Click to see full AI summary/tags/classification  
✅ **Direct Jump**: Click title link to jump to channel message  

### ⚠️ Impact of Not Enabling AI

If you choose not to enable AI features, the following functions will be **unavailable**:

❌ **Auto Summary Generation** - Cannot auto-generate content summaries  
❌ **AI Smart Tags** - Cannot auto-generate AI recommended tags  
❌ **Smart Classification** - Cannot auto-classify content  
❌ **Key Points Extraction** - Cannot extract content key insights  
❌ **Smart Chat** - Cannot use natural language interaction  
❌ **Search AI Analysis** - Search results won't have 🤖 button and AI info  

**✅ Core features that remain functional:**

✅ Content archiving and storage  
✅ Manual tags (#tag)  
✅ Full-text search (FTS5)  
✅ Note system  
✅ Recycle bin  
✅ Data export/backup  
✅ All commands work normally  

> 💡 **Suggestion**: Even without AI, ArchiveBot's core archiving and search features remain fully functional. You can start with basic features and enable AI later when needed.

### Quick Setup AI

1. **Configure API key**

Edit `config/config.yaml`:

```yaml
ai:
  enabled: true              # Enable AI features
  auto_summarize: true       # Auto-generate summaries
  auto_generate_tags: true   # Auto-generate AI tags
  api:
    provider: xai            # Provider: xai/openai/anthropic/qwen
    api_key: 'xai-xxx'       # API key
    base_url: 'https://api.x.ai/v1'  # API endpoint
    model: grok-4-1-fast-non-reasoning  # Fast model for generating responses
    reasoning_model: grok-4-1-fast-reasoning  # Reasoning model for intent analysis
    max_tokens: 1000         # Maximum tokens
    timeout: 30              # Request timeout (seconds)
```

**Configuration examples for other providers:**

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
    model: gpt-4-turbo       # Model for generating responses
    reasoning_model: gpt-4-turbo  # Reasoning model for intent analysis
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
    model: claude-3-5-sonnet-20241022  # Model for generating responses
    reasoning_model: claude-3-5-sonnet-20241022  # Reasoning model for intent analysis
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>Alibaba Cloud Qwen</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: qwen
    api_key: 'sk-xxx'
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: qwen-plus         # Model for generating responses
    reasoning_model: qwen-plus  # Reasoning model for intent analysis
    max_tokens: 1000
    timeout: 30
```

</details>

1. **Restart the Bot**

```bash
python main.py
```

1. **Verify AI status**

```bash
# Send command to Bot in Telegram to check AI status
/ai
```

1. **Start using AI features**

Send any content to the Bot (text/links/images/documents, etc.), and AI will automatically analyze it in the background. When using `/search`, content with AI analysis will show a 🤖 button that you can click to view the full AI analysis (summary/key points/tags/classification).

## 📚 Documentation

- 📖 [Quick Start](docs/QUICKSTART.md) - Get started in 5 minutes
- 🚀 [Deployment Guide](docs/DEPLOYMENT.md) - Production environment deployment

## 🔒 Security Features

- ✅ **SQL Injection Protection** - Parameterized queries + ESCAPE escaping
- ✅ **Input Validation** - All inputs strictly validated and sanitized
- ✅ **Sensitive Info Filtering** - Logs automatically filter tokens and IDs
- ✅ **Thread Safety** - RLock + WAL mode
- ✅ **Authentication** - owner_only decorator protection
- ✅ **Error Handling** - Comprehensive exception handling and recovery

## 🎯 Roadmap

### ✅ Phase 1 (Completed)

- ✅ Basic Bot framework and command system
- ✅ Smart content analysis and archiving
- ✅ Full-text search engine (FTS5)
- ✅ Multi-language support (en/zh-CN/zh-TW/zh-HK/zh-MO)
- ✅ AI enhancement (Grok-4)
  - ✅ Smart summary/key points/classification/tags
  - ✅ Smart intent detection and natural language interaction
  - ✅ Prompt engineering optimization
  - ✅ Content language detection
  - ✅ Smart fallback strategy
  - ✅ Multi-language terminology optimization
- ✅ Search experience optimization
  - ✅ Pagination (10 items/page)
  - ✅ AI analysis button
  - ✅ Navigation optimization
- ✅ Simplified Telegram storage strategy

### ✅ Phase 2 (Completed)

- ✅ Note and annotation system
  - ✅ Standalone and linked notes
  - ✅ Note mode for quick additions
  - ✅ Note list display
  - ✅ Note status indicators (📝/📝✓)
- ✅ Favorites collection feature
  - ✅ One-click favorite marking (🤍/❤️)
  - ✅ Favorites filtering
  - ✅ Favorites status display
- ✅ Quick action buttons
  - ✅ Forward function (↗️)
  - ✅ Action buttons per record
  - ✅ Action buttons on archive success messages
- ✅ Recycle bin system
  - ✅ Soft delete mechanism
  - ✅ Content recovery
  - ✅ Scheduled cleanup
- ✅ Data export (Markdown/JSON/CSV)
- ✅ Auto backup system
  - ✅ Scheduled backup scheduling (hourly checks)
  - ✅ Backup file management
  - ✅ Backup restoration
  - ✅ Configurable backup intervals

### ✅ Phase 3 (Completed)

- ✅ User experience optimization
  - ✅ Command aliases (/s = /search, /t = /tags, /st = /stats, /lang = /language)
  - ✅ Auto-deduplication (file MD5 detection to prevent duplicate archiving)
- ✅ Content review features
  - ✅ Activity statistics reports (weekly/monthly/yearly trends, popular tags, daily activity)
  - ✅ Random review display (auto-included in statistics reports)
  - ✅ `/review` command (button-based period selection)
  - 🚧 Standalone random review command (configurable quantity for quick history viewing)
- 🔄 Batch operations (underlying API completed, UI pending)
  - 🚧 Batch tag replacement API (replace_tag)
  - 🚧 Batch tag removal API
  - 🚧 Batch operation user interface (commands/buttons)
  - 🚧 Batch delete/restore
  - 🚧 Batch export
- 🚧 Advanced search
  - 🚧 Combined filtering
  - 🚧 Time range
  - 🚧 Content type filtering

### 📝 Phase 4 (Future Plans)

- 🔮 **AI Enhancement**
  - Voice to text (Whisper API)
  - OCR image text recognition
  - Smart content similarity analysis
  - Exclude specific archive channels from AI reference content
  - Exclude specific tags and categories from AI reference content
- 🔮 **Archive Enhancement**
  - Specify archive channel based on forward source
  - Specify archive channel for personally sent documents
  - Specify archive channel based on tags
- 🔮 **Extended Features**
  - Web management interface
  - RESTful API
  - Cloud storage integration (Google Drive/Aliyun Drive)
  - Cross-device sync
- 🔮 **Performance Optimization**
  - Cache mechanism optimization
  - Async processing enhancement
  - Batch operation optimization

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

This project is licensed under the [MIT License](LICENSE)

## 🙏 Acknowledgments

### Special Thanks

- **[@WangPanBOT](https://t.me/WangPanBOT)** - Telegram network drive bot project that inspired this project, demonstrating the great potential of Telegram Bots in personal content management

### Open Source Projects

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot framework, powerful and easy to use
- [SQLite](https://www.sqlite.org/) - Reliable embedded database, lightweight and efficient

### AI Service Providers

- [xAI](https://x.ai/) - Grok-4 fast reasoning model
- [OpenAI](https://openai.com/) - GPT series models
- [Anthropic](https://anthropic.com/) - Claude series models
- [Alibaba Cloud](https://www.aliyun.com/) - Qwen models

## 📧 Contact

- **GitHub Issues**: [Submit Issue](https://github.com/tealun/ArchiveBot/issues)
- **X (Twitter)**: [@TealunDu](https://x.com/TealunDu)
- **Email**: <tealun@gmail.com>

### Community Groups

- **Chinese Group**: [@ArchiveBotCN](https://t.me/joinchat/3753827356)
- **English Group**: [@ArchiveBotEN](https://t.me/joinchat/3877196244)

---

## ⚠️ Disclaimer

### Terms of Use

1. **Personal Use**: This project is for learning, research, and personal use only. Not for commercial purposes or illegal activities
2. **Terms of Service**: Strictly comply with [Telegram Terms of Service](https://telegram.org/tos) and related API usage policies when using this project
3. **Content Responsibility**: Users are fully responsible for all content archived through the Bot. Developers assume no responsibility for user-stored content
4. **Data Security**: This project is a locally deployed tool with data stored in the user's own environment. Please properly safeguard configuration files and databases to prevent sensitive information leakage

### Third-Party Services

1. **AI Services**: When using AI features, your content will be sent to third-party AI service providers (xAI/OpenAI/Anthropic/Alibaba Cloud). Please ensure compliance with these providers' terms of use and privacy policies
2. **API Usage**: Users must apply for and legally use API keys for various third-party services. Users bear consequences of API abuse

### Intellectual Property & Privacy

1. **Copyright Protection**: Do not use this project to archive copyrighted content or materials that infringe on others' intellectual property rights
2. **Privacy Respect**: Do not archive others' private information or conversation content without authorization
3. **Open Source License**: This project is licensed under MIT License but provides no warranties or guarantees

### No Warranty Statement

1. **Provided As-Is**: This software is provided "as is" without any express or implied warranties, including but not limited to merchantability, fitness for a particular purpose, and non-infringement
2. **Use at Your Own Risk**: Developers assume no responsibility for any direct or indirect losses (including but not limited to data loss, service interruptions, business losses, etc.) resulting from using this project
3. **Security Risks**: While security measures are implemented, any software may have unknown vulnerabilities. Users should assess security risks themselves

### Legal Compliance

1. **Local Laws**: Ensure that using this project complies with local laws and regulations in your region
2. **No Illegal Use**: Strictly prohibited from using this project for any illegal activities, including but not limited to spreading illegal information, privacy infringement, network attacks, etc.

---
