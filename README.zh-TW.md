# ArchiveBot

**✨ Version 1.0 | 正式發佈版**

**🌍 Read this in other languages / 其他語言版本**

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

---

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

基於 Telegram Bot 的個人內容歸檔系統 | Personal Content Archiving System for Telegram

## 📖 專案簡介

ArchiveBot 是一個開源的 Telegram Bot，幫助你將 Telegram 中的各類內容（檔案、圖片、影片、文字、連結等）進行智慧分類和歸檔，打造個人知識庫和內容收藏系統。

**核心定位**：個人實例工具，每個人部署自己的 Bot，資料完全私有。

## ✨ 核心特性

- 📦 **智慧歸檔**：自動識別 10+ 種內容類型並分類儲存
- 🏷️ **智慧標籤**：自動打標籤，支援手動標籤（#tag）+ AI智慧標籤
- 🔍 **全文搜尋**：FTS5 全文搜尋引擎，分頁展示（10項/頁）
- ❤️ **精選收藏**：一鍵標記精選內容，快速篩選重要資料
- 📝 **筆記系統**：支援獨立筆記和關聯筆記，記錄想法和心得
- ↗️ **快速轉發**：一鍵轉發歸檔內容到頻道或其他對話
- 🗑️ **資源回收桶**：誤刪除內容可恢復，30天自動清理
- 💾 **資料匯出**：支援匯出 Markdown/JSON 格式
- 🔄 **自動備份**：定期自動備份資料庫，保障資料安全
- 🤖 **AI智慧增強**：Grok-4智慧分析（摘要/關鍵點/分類/標籤）
- 💬 **AI智慧對話**：自然語言互動，自動識別使用者意圖和語言
- 💬 **智慧資源回覆**：智慧識別意圖並直接返回資源檔案（絕不虛構URL）
- 🌏 **多語言支援**：6種語言（英語/簡體中文/繁體中文/日語/韓語/西班牙語）
- 🔗 **連結智慧提取**：自動提取網頁標題、描述、作者、關鍵資訊等詮釋資料，便於後續搜尋和管理
- 💾 **簡化儲存**：本地儲存小資料 → 頻道儲存大檔案 → 僅引用超大檔案（三級策略）
- 🔒 **隱私保護**：資料完全私有，單使用者模式
- 🛡️ **安全可靠**：SQL 注入防護、敏感資訊過濾、執行緒安全
- ⚡ **高效能**：WAL 模式、索引最佳化、並行支援

## 🎯 適用場景

- 📝 儲存重要訊息和對話
- 🖼️ 收藏圖片和電子書
- 📄 歸檔文件和資料
- 🔗 收集有用的連結
- 🎬 儲存影片和音訊
- 📚 建構個人知識庫

## 🚀 快速開始

### 方式一：Docker 部署（推薦）

**最簡單的部署方式，無需配置 Python 環境**

#### 前置需求

- 安裝 [Docker](https://www.docker.com/get-started) 和 Docker Compose
- Telegram 帳號
- Bot Token（從 [@BotFather](https://t.me/BotFather) 獲取）

#### 部署步驟

```bash
# 1. 複製專案
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 2. 配置 Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # 填寫 bot_token, owner_id, channel_id

# 3. 啟動（一鍵部署）
docker-compose up -d --build

# 4. 查看日誌
docker-compose logs -f
```

**完成！** 去 Telegram 中找到你的 Bot，發送 `/start` 開始使用。

#### 常用命令

```bash
docker-compose restart          # 重啟
docker-compose logs -f          # 查看日誌
docker-compose down             # 停止
git pull && docker-compose up -d --build  # 更新到最新版本
```

#### 配置方式

**方式一：配置檔案（推薦）**
- 編輯 `config/config.yaml`
- 所有配置寫在檔案中

**方式二：環境變數（適合 CI/CD）**
- 編輯 `docker-compose.yml` 中的 environment 部分
- 優先級：環境變數 > 配置檔案

---

### 方式二：傳統部署

#### 前置需求

- Python 3.9+
- Telegram 帳號
- Bot Token（從 [@BotFather](https://t.me/BotFather) 取得）

#### 安裝步驟

1. **複製專案**

```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

2. **安裝相依性**

```bash
pip install -r requirements.txt
```

3. **設定 Bot**

```bash
# 複製設定範本
cp config/config.template.yaml config/config.yaml

# 編輯設定檔
nano config/config.yaml
```

**必填設定項**:

- `bot_token`: 從 [@BotFather](https://t.me/BotFather) 取得
- `owner_id`: 你的 Telegram User ID（從 [@userinfobot](https://t.me/userinfobot) 取得）
- `storage.telegram.channels.default`: 預設私有頻道 ID（用於儲存檔案，支援多頻道分類儲存）

4. **啟動 Bot**

```bash
python main.py
```

5. **開始使用**

在 Telegram 中找到你的 Bot，傳送 `/start` 開始使用！

📚 **詳細指南**: [快速開始文件](docs/QUICKSTART.md) | [部署指南](docs/DEPLOYMENT.md)

## 📦 儲存策略

ArchiveBot 採用簡化的三級儲存策略，充分利用 Telegram 的免費儲存空間：

| 內容類型 | 大小範圍 | 儲存方式 | 說明 |
|---------|---------|---------|------|
| 文字/連結 | - | SQLite 資料庫 | 直接儲存，支援全文搜尋 |
| 媒體檔案 | 0-2GB | Telegram 私有頻道 | 永久可靠，file_id 轉發 |
| 超大檔案 | >2GB | 僅存引用資訊 | 不佔空間，依賴原訊息 |

**核心優勢**：

- ✅ 無需下載/上傳，直接 file_id 轉發
- ✅ 頻道訊息 file_id 永久有效
- ✅ 支援完整 2GB 限制
- ✅ 簡單可靠，無逾時風險

## 🎮 使用方法

### 命令列表

| 命令 | 簡寫 | 說明 |
|------|------|------|
| `/start` | - | 初始化 Bot，顯示歡迎訊息 |
| `/help` | - | 查看詳細說明資訊 |
| `/search <關鍵詞>` | `/s` | 搜尋歸檔內容 |
| `/note` | `/n` | 添加筆記 |
| `/notes` | - | 查看所有筆記列表 |
| `/tags` | `/t` | 查看所有標籤及統計 |
| `/stats` | `/st` | 查看歸檔統計資訊 |
| `/setting` | `/set` | 系統設定 |
| `/review` | - | 活動回顧與統計（週/月/年） |
| `/rand` | `/r` | 隨機查看歷史歸檔 |
| `/trash` | - | 查看資源回收桶內容 |
| `/export` | - | 匯出歸檔資料 |
| `/backup` | - | 建立資料庫備份 |
| `/ai` | - | 查看AI功能狀態 |
| `/language` | `/la` | 切換介面語言 |
| `/restart` | - | 重啟系統 |
| `/cancel` | - | 取消當前操作 |

### 歸檔內容

**直接傳送任何內容即可歸檔！**

```
支援的內容類型：
📝 文字訊息
🔗 連結
🖼️ 圖片
🎬 影片
📄 文件
🎵 音訊
🎤 語音
🎭 貼圖
🎞️ 動畫
```

**新增標籤**:

```text
傳送訊息時加上 #標籤 即可：

這是一條測試訊息 #測試 #重要
https://github.com #技術 #開源
```

### 搜尋內容

```bash
# 關鍵詞搜尋
/search python

# 標籤搜尋
/search #技術

# 組合搜尋
/search #技術 python
```

## 🛠️ 技術架構

### 技術堆疊

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.14.2 |
| 框架 | python-telegram-bot 21.x |
| 資料庫 | SQLite (WAL模式, FTS5, AI欄位索引) |
| AI | httpx (Grok-4 via xAI) |
| 設定 | PyYAML |

### 架構設計

```text
ArchiveBot/
├── main.py                      # 進入點檔案
├── src/
│   ├── bot/                     # Bot 層
│   │   ├── commands.py          # 命令處理
│   │   ├── handlers.py          # 訊息處理
│   │   ├── callbacks.py         # 回呼處理
│   │   ├── message_aggregator.py # 訊息聚合器
│   │   └── unknown_command.py   # 未知命令處理
│   ├── core/                    # 核心業務
│   │   ├── analyzer.py          # 內容分析
│   │   ├── tag_manager.py       # 標籤管理
│   │   ├── storage_manager.py   # 儲存管理
│   │   ├── search_engine.py     # 搜尋引擎
│   │   ├── note_manager.py      # 筆記管理
│   │   ├── trash_manager.py     # 資源回收桶管理
│   │   ├── export_manager.py    # 資料匯出
│   │   ├── backup_manager.py    # 備份管理
│   │   ├── review_manager.py    # 內容回顧
│   │   ├── ai_session.py        # AI會話管理
│   │   ├── ai_cache.py          # AI快取基礎類別
│   │   └── ai_data_cache.py     # AI資料快取
│   ├── ai/                      # AI 功能
│   │   ├── summarizer.py        # AI摘要產生
│   │   ├── chat_router.py       # 智慧對話路由
│   │   ├── fallback.py          # AI降級策略
│   │   └── prompts/             # 提示詞範本
│   │       ├── chat.py
│   │       ├── note.py
│   │       ├── summarize.py
│   │       └── title.py
│   ├── storage/                 # 儲存層
│   │   ├── base.py              # 儲存基礎類別
│   │   ├── database.py          # 資料庫儲存
│   │   └── telegram.py          # Telegram儲存
│   ├── models/                  # 資料模型
│   │   └── database.py          # 資料庫模型
│   ├── utils/                   # 工具模組
│   │   ├── config.py            # 設定管理
│   │   ├── logger.py            # 日誌系統
│   │   ├── i18n.py              # 國際化
│   │   ├── language_context.py  # 語言上下文
│   │   ├── message_builder.py   # 訊息建構框架
│   │   ├── validators.py        # 輸入驗證
│   │   ├── helpers.py           # 輔助函式
│   │   ├── constants.py         # 常數定義
│   │   ├── file_handler.py      # 檔案處理
│   │   ├── link_extractor.py    # 連結詮釋資料提取
│   │   └── db_maintenance.py    # 資料庫維護
│   └── locales/                 # 語言檔案
│       ├── en.json
│       ├── zh-CN.json
│       ├── zh-TW.json
│       ├── ja.json
│       ├── ko.json
│       └── es.json
└── config/
    └── config.yaml              # 設定檔
```

## 🤖 AI功能（可選）

ArchiveBot 支援雲端 AI 服務，可以**自動**產生內容摘要、提取關鍵點、智慧分類、推薦標籤，大幅提升內容管理效率。

### 支援的AI服務

| 提供商 | 模型 | 特點 | 推薦場景 |
|--------|------|------|----------|
| **xAI** | Grok-4 | 多語言理解強，速度快 | 預設推薦 |
| **OpenAI** | GPT-4/GPT-3.5 | 功能最強，效果最好 | 預算充足 |
| **Anthropic** | Claude 3.5 | 性價比高，中文好 | 成本敏感 |
| **阿里雲** | 通義千問 | 國內服務，存取穩定 | 國內使用者 |

💡 **輕量級設計**：僅使用 HTTP API 呼叫，無需安裝龐大的 SDK

### AI功能亮點

✅ **智慧摘要**：自動產生30-100字精簡總結  
✅ **關鍵點提取**：提煉3-5個核心觀點  
✅ **智慧分類**：自動歸類到合適的category  
✅ **精準標籤**：產生5個可搜尋的專業標籤  
✅ **智慧對話**：自然語言互動，自動識別意圖和語言  
✅ **提示詞工程**：角色扮演 + Few-Shot + 思維鏈最佳化  
✅ **語言檢測**：自動識別中/英文內容  
✅ **智慧降級**：根據內容長度調整分析深度  
✅ **多語言最佳化**：簡體/繁體/英文術語自適應  

### 搜尋增強

✅ **分頁展示**：10項/頁，左右箭頭導航  
✅ **AI解析按鈕**：🤖 格式展示，一鍵查看AI分析  
✅ **快速查看**：點擊查看完整AI摘要/標籤/分類  
✅ **直接跳轉**：點擊標題連結跳轉頻道訊息  

### ⚠️ 不啟用AI的影響

如果選擇不啟用AI功能，以下功能將**不可用**：

❌ **自動摘要產生** - 無法自動產生內容摘要  
❌ **AI智慧標籤** - 無法自動產生AI推薦標籤  
❌ **智慧分類** - 無法自動分類內容  
❌ **關鍵點提取** - 無法提取內容關鍵觀點  
❌ **智慧對話** - 無法使用自然語言互動  
❌ **搜尋AI解析** - 搜尋結果無🤖按鈕和AI資訊  

**✅ 不受影響的核心功能：**

✅ 內容歸檔儲存  
✅ 手動標籤（#tag）  
✅ 全文搜尋（FTS5）  
✅ 筆記系統  
✅ 資源回收桶  
✅ 資料匯出/備份  
✅ 所有命令正常使用  

> 💡 **建議**：即使不啟用AI，ArchiveBot的核心歸檔和搜尋功能依然完整可用。可以先使用基礎功能，後續需要時再啟用AI。

### 快速啟用 AI

1. **設定API金鑰**

編輯 `config/config.yaml`:

```yaml
ai:
  enabled: true              # 啟用AI功能
  auto_summarize: true       # 自動產生摘要
  auto_generate_tags: true   # 自動產生AI標籤
  api:
    provider: xai            # 提供商: xai/openai/anthropic/qwen
    api_key: 'xai-xxx'       # API金鑰
    base_url: 'https://api.x.ai/v1'  # API端點
    model: grok-4-1-fast-non-reasoning  # 產生回覆的快速模型
    reasoning_model: grok-4-1-fast-reasoning  # 意圖分析的推理模型
    max_tokens: 1000         # 最大token數
    timeout: 30              # 請求逾時（秒）
```

**其他提供商設定範例：**

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
    model: gpt-4-turbo       # 產生回覆的模型
    reasoning_model: gpt-4-turbo  # 意圖分析的推理模型
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
    model: claude-3-5-sonnet-20241022  # 產生回覆的模型
    reasoning_model: claude-3-5-sonnet-20241022  # 意圖分析的推理模型
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>阿里雲通義千問</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: qwen
    api_key: 'sk-xxx'
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: qwen-plus         # 產生回覆的模型
    reasoning_model: qwen-plus  # 意圖分析的推理模型
    max_tokens: 1000
    timeout: 30
```

</details>

1. **重新啟動Bot**

```bash
python main.py
```

1. **驗證AI狀態**

```bash
# 在 Telegram 中向 Bot 發送以下指令
/ai
```

1. **開始使用AI功能**

向Bot傳送任何內容（文字/連結/圖片/文件等），AI會自動在背景進行分析。使用 `/search` 搜尋時，有AI分析的內容會顯示🤖按鈕，點擊可查看完整AI分析結果（摘要/關鍵點/標籤/分類）。

## 📚 文件

- 📖 [快速開始](docs/QUICKSTART.md) - 5分鐘快速上手
- 🚀 [部署指南](docs/DEPLOYMENT.md) - 生產環境部署

## 🔒 安全特性

- ✅ **SQL 注入防護** - 參數化查詢 + ESCAPE 跳脫
- ✅ **輸入驗證** - 所有輸入經過嚴格驗證和清理
- ✅ **敏感資訊過濾** - 日誌自動過濾 token 和 ID
- ✅ **執行緒安全** - RLock + WAL 模式
- ✅ **身分驗證** - owner_only 裝飾器保護
- ✅ **錯誤處理** - 完善的異常處理和恢復機制

## 🎯 開發路線圖

### ✅ 第一階段 (已完成)

- ✅ 基礎 Bot 框架和命令系統
- ✅ 智慧內容分析和歸檔
- ✅ 全文搜尋引擎 (FTS5)
- ✅ 多語言支援 (en/zh-CN/zh-TW/zh-HK/zh-MO)
- ✅ AI智慧增強 (Grok-4)
  - ✅ 智慧摘要/關鍵點/分類/標籤
  - ✅ 智慧意圖識別和自然語言互動
  - ✅ 提示詞工程最佳化
  - ✅ 內容語言檢測
  - ✅ 智慧降級策略
  - ✅ 多語言術語最佳化
- ✅ 搜尋體驗最佳化
  - ✅ 分頁展示 (10項/頁)
  - ✅ AI解析按鈕
  - ✅ 導航最佳化
- ✅ 簡化的 Telegram 儲存策略

### ✅ 第二階段 (已完成)

- ✅ 筆記和批註系統
  - ✅ 獨立筆記和關聯筆記
  - ✅ 筆記模式快速新增
  - ✅ 筆記列表展示
  - ✅ 筆記狀態顯示 (📝/📝✓)
- ✅ 精選收藏功能
  - ✅ 一鍵標記精選 (🤍/❤️)
  - ✅ 精選篩選查詢
  - ✅ 精選狀態顯示
- ✅ 快速操作按鈕
  - ✅ 轉發功能 (↗️)
  - ✅ 每條記錄操作按鈕
  - ✅ 歸檔成功訊息操作按鈕
- ✅ 資源回收桶系統
  - ✅ 軟刪除機制
  - ✅ 內容恢復
  - ✅ 定期清理
- ✅ 資料匯出功能 (Markdown/JSON/CSV)
- ✅ 自動備份系統
  - ✅ 定時備份排程（每小時檢查）
  - ✅ 備份檔案管理
  - ✅ 備份恢復
  - ✅ 可設定備份間隔

### ✅ 第三階段 (已完成)

- ✅ 使用者體驗最佳化
  - ✅ 命令別名支援（/s = /search, /t = /tags, /st = /stats, /la = /language）
  - ✅ 自動去重檢測（檔案MD5檢測，防止重複歸檔）
- ✅ 內容回顧功能
  - ✅ 活動統計報告（週/月/年趨勢、熱門標籤、每日活動）
  - ✅ 隨機回顧展示（統計報告中自動包含隨機歷史內容）
  - ✅ `/review` 命令（按鈕選擇期間）
  - ✅ `/rand` 獨立隨機回看命令（可設定數量，快速查看歷史歸檔）
- ✅ AI功能增強
  - ✅ 智慧識別敏感內容存檔指定頻道
  - ✅ AI參考內容排除指定存檔頻道
  - ✅ AI參考內容排除指定標籤與分類
- ✅ 存檔功能增強
  - ✅ 根據轉發來源指定存檔頻道
  - ✅ 個人直接傳送文件指定存檔頻道
  - ✅ 根據標籤指定存檔頻道

### 📝 第四階段 (未來規劃)

- 🔄 批次操作（底層API已完成，UI待開發）
  - 🚧 批次標籤替換 API（replace_tag）
  - 🚧 批次標籤移除 API
  - 🚧 批次操作使用者介面（命令/按鈕）
  - 🚧 批次刪除/恢復
  - 🚧 批次匯出
- 🚧 進階搜尋
  - 🚧 組合篩選
  - 🚧 時間範圍
  - 🚧 內容類型篩選
- 🔮 **AI功能增強**
  - 🚧 語音轉文字（Whisper API）
  - 🚧 OCR圖片文字識別
  - 🚧 智慧內容相似度分析
- 🔮 **擴充功能**
  - 🚧 Web管理介面
  - 🚧 RESTful API介面
  - 🚧 雲端儲存整合（Google Drive/阿里雲盤）
  - 🚧 增強型URL內容反爬取獲取
- 🔮 **效能最佳化**
  - 🚧 快取機制最佳化
  - 🚧 非同步處理增強
  - 🚧 批次操作最佳化

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權條款

本專案採用 [MIT License](LICENSE)

## 🙏 致謝

### 特別感謝

- **[@WangPanBOT](https://t.me/WangPanBOT)** - Telegram 網盤機器人專案，作為本專案的靈感來源，展示了 Telegram Bot 在個人內容管理方面的巨大潛力

### 開源專案

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 優秀的 Telegram Bot 框架，強大而易用
- [SQLite](https://www.sqlite.org/) - 可靠的嵌入式資料庫，輕量且高效

### AI 服務提供商

- [xAI](https://x.ai/) - Grok-4 快速推理模型
- [OpenAI](https://openai.com/) - GPT 系列模型
- [Anthropic](https://anthropic.com/) - Claude 系列模型
- [阿里雲](https://www.aliyun.com/) - 通義千問模型

## 📧 聯絡方式

- **GitHub Issues**: [提交問題](https://github.com/tealun/ArchiveBot/issues)
- **X (Twitter)**: [@TealunDu](https://x.com/TealunDu)
- **Email**: <tealun@gmail.com>

### 交流群組

- **中文交流群**: [@ArchiveBotCN](https://t.me/joinchat/3753827356)
- **English Group**: [@ArchiveBotEN](https://t.me/joinchat/3877196244)

---

## ⚠️ 免責聲明

### 使用須知

1. **個人使用**：本專案僅供學習研究和個人使用，不得用於商業用途或違法活動
2. **服務條款**：使用本專案時請嚴格遵守 [Telegram 服務條款](https://telegram.org/tos)和相關 API 使用政策
3. **內容責任**：使用者對透過 Bot 歸檔的所有內容負全部責任，開發者不對使用者儲存的內容承擔任何責任
4. **資料安全**：本專案為本地部署工具，資料儲存在使用者自己的環境中。請妥善保管設定檔和資料庫，防止敏感資訊洩露

### 第三方服務

1. **AI 服務**：使用 AI 功能時，您的內容會傳送至第三方 AI 服務商（xAI/OpenAI/Anthropic/阿里雲）。請確保遵守這些服務商的使用條款和隱私政策
2. **API 使用**：使用者需自行申請並合法使用各項第三方服務的 API 金鑰，因 API 濫用產生的後果由使用者自行承擔

### 智慧財產權與隱私

1. **著作權保護**：請勿使用本專案歸檔受著作權保護的內容，或侵犯他人智慧財產權的資料
2. **隱私尊重**：請勿未經授權歸檔他人的私密資訊或對話內容
3. **開源協議**：本專案採用 MIT License，但不包含任何擔保或保證

### 無擔保聲明

1. **按原樣提供**：本軟體按「原樣」提供，不提供任何明示或暗示的擔保，包括但不限於適銷性、特定用途適用性和非侵權性
2. **風險自負**：使用本專案產生的任何直接或間接損失（包括但不限於資料遺失、服務中斷、業務損失等），開發者概不負責
3. **安全風險**：雖然專案採取了安全措施，但任何軟體都可能存在未知漏洞。使用者應自行評估安全風險

### 法律合規

1. **地區法律**：請確保在您所在地區使用本專案符合當地法律法規
2. **禁止違法**：嚴禁使用本專案從事任何違法違規活動，包括但不限於傳播違法資訊、侵犯隱私、網路攻擊等

---
