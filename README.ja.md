<div align="center">

# ArchiveBot

**✨ Version 1.0 | 正式リリース**

**🌍 他の言語で読む / Read in other languages**

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

---

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

</div>

Telegram Bot ベースの個人コンテンツアーカイブシステム | Personal Content Archiving System for Telegram

## 📖 プロジェクト概要

ArchiveBot は、Telegram 上のあらゆる種類のコンテンツ（ファイル、画像、動画、テキスト、リンクなど）をインテリジェントに分類してアーカイブするオープンソースの Telegram Bot です。個人のナレッジベースとコンテンツコレクションシステムを構築できます。

**コアコンセプト**：個人用インスタンスツール。各ユーザーが独自の Bot をデプロイし、データは完全にプライベートです。

## ✨ コア機能

- 📦 **スマートアーカイブ**：10種類以上のコンテンツタイプを自動認識して分類保存
- 🏷️ **スマートタグ**：自動タグ付け、手動タグ（#tag）と AI スマートタグをサポート
- 🔍 **全文検索**：FTS5 全文検索エンジン、ページング表示（10件/ページ）
- ❤️ **お気に入りコレクション**：ワンクリックでお気に入りコンテンツをマーク、重要な資料を素早くフィルタリング
- 📝 **ノートシステム**：独立したノートと関連ノートをサポート、アイデアや感想を記録
- ↗️ **クイック転送**：アーカイブしたコンテンツをチャンネルや他の会話にワンクリックで転送
- 🗑️ **ごみ箱**：誤って削除したコンテンツを復元可能、30日後に自動クリーンアップ
- 💾 **データエクスポート**：Markdown/JSON 形式でのエクスポートをサポート
- 🔄 **自動バックアップ**：定期的なデータベースの自動バックアップでデータの安全性を確保
- 🤖 **AI スマート強化**：Grok-4 インテリジェント分析（要約/キーポイント/分類/タグ）
- 💬 **AI スマート対話**：自然言語インタラクション、インテントをインテリジェントに認識してリソースファイルを直接返信
- 🌏 **多言語サポート**：6言語対応（英語/簡体字中国語/繁体字中国語/日本語/韓国語/スペイン語）
- 🔗 **スマートリンク抽出**：ウェブページのタイトル、説明、著者、重要な情報などのメタデータを自動抽出し、後続の検索と管理を容易にする
- 💾 **簡素化されたストレージ**：小データはローカルストレージ → 大ファイルはチャンネルストレージ → 超大ファイルは参照のみ（3段階戦略）
- 🔒 **プライバシー保護**：データは完全にプライベート、シングルユーザーモード
- 🛡️ **安全で信頼性が高い**：SQL インジェクション保護、機密情報フィルタリング、スレッドセーフ
- ⚡ **高性能**：WAL モード、インデックス最適化、同時実行サポート

## 🎯 適用シーン

- 📝 重要なメッセージや会話を保存
- 🖼️ 画像や電子書籍を収集
- 📄 ドキュメントや資料をアーカイブ
- 🔗 便利なリンクを収集
- 🎬 動画やオーディオを保存
- 📚 個人のナレッジベースを構築

## 🚀 クイックスタート

### 方法1：Docker デプロイ（推奨）

**最も簡単なデプロイ方法、Python 環境の設定は不要です**

#### 前提条件

- [Docker](https://www.docker.com/get-started) と Docker Compose をインストール
- Telegram アカウント
- Bot Token（[@BotFather](https://t.me/BotFather) から取得）

#### デプロイ手順

```bash
# 1. プロジェクトをクローン
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 2. Bot を設定
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # bot_token, owner_id, channel_id を入力

# 3. 設定を検証（オプションですが推奨）
python verify_docker.py

# 4. 起動（ワンクリックデプロイ）
docker-compose up -d --build

# 5. ログを確認
docker-compose logs -f
```

**完了！** Telegram で Bot を見つけて、`/start` を送信して使用を開始します。

#### よく使うコマンド

```bash
docker-compose restart          # 再起動
docker-compose logs -f          # ログを確認
docker-compose down             # 停止
git pull && docker-compose up -d --build  # 最新版に更新
```

#### 設定方法

**方法1：設定ファイル（推奨）**
- `config/config.yaml` を編集
- すべての設定をファイルに記述

**方法2：環境変数（CI/CD に適している）**
- `docker-compose.yml` の environment セクションを編集
- 優先順位：環境変数 > 設定ファイル

---

### 方法2：従来のデプロイ

#### 前提条件

- Python 3.9+
- Telegram アカウント
- Bot Token（[@BotFather](https://t.me/BotFather) から取得）

#### インストール手順

1. **プロジェクトをクローン**

```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

2. **依存関係をインストール**

```bash
pip install -r requirements.txt
```

3. **Bot を設定**

```bash
# 設定テンプレートをコピー
cp config/config.template.yaml config/config.yaml

# 設定ファイルを編集
nano config/config.yaml
```

**必須設定項目**:

- `bot_token`: [@BotFather](https://t.me/BotFather) から取得
- `owner_id`: あなたの Telegram User ID（[@userinfobot](https://t.me/userinfobot) から取得）
- `storage.telegram.channels.default`: デフォルトのプライベートチャンネル ID（ファイル保存用、複数チャンネルの分類保存をサポート）

4. **Bot を起動**

```bash
python main.py
```

5. **使用開始**

Telegram で Bot を見つけて、`/start` を送信して使用を開始！

📚 **詳細ガイド**: [クイックスタートドキュメント](docs/QUICKSTART.md) | [デプロイガイド](docs/DEPLOYMENT.md)

## 📦 ストレージ戦略

ArchiveBot は、Telegram の無料ストレージスペースを最大限に活用する、簡素化された3段階ストレージ戦略を採用しています：

| コンテンツタイプ | サイズ範囲 | ストレージ方法 | 説明 |
| --------- | --------- | --------- | ------ |
| テキスト/リンク | - | SQLite データベース | 直接保存、全文検索をサポート |
| メディアファイル | 0-2GB | Telegram プライベートチャンネル | 永久的で信頼性が高く、file_id で転送 |
| 超大ファイル | >2GB | 参照情報のみ保存 | スペースを取らず、元のメッセージに依存 |

**コアの利点**：

- ✅ ダウンロード/アップロード不要、file_id で直接転送
- ✅ チャンネルメッセージの file_id は永久に有効
- ✅ 完全な 2GB 制限をサポート
- ✅ シンプルで信頼性が高く、タイムアウトリスクなし

## 🎮 使用方法

### コマンド一覧

| コマンド | 略記 | 説明 |
| ------ | ------ | ------ |
| `/start` | - | Bot を初期化、ウェルカムメッセージを表示 |
| `/help` | - | 詳細なヘルプ情報を表示 |
| `/search <キーワード>` | `/s` | アーカイブコンテンツを検索 |
| `/note` | `/n` | ノートを追加 |
| `/notes` | - | すべてのノートリストを表示 |
| `/tags` | `/t` | すべてのタグと統計を表示 |
| `/stats` | `/st` | アーカイブ統計情報を表示 |
| `/setting` | `/set` | システム設定 |
| `/review` | - | アクティビティレビューと統計（週/月/年） |
| `/rand` | `/r` | ランダムに履歴アーカイブを表示 |
| `/trash` | - | ごみ箱のコンテンツを表示 |
| `/export` | - | アーカイブデータをエクスポート |
| `/backup` | - | データベースのバックアップを作成 |
| `/ai` | - | AI 機能の状態を表示 |
| `/language` | `/la` | インターフェース言語を切り替え |
| `/restart` | - | システムを再起動 |
| `/cancel` | - | 現在の操作をキャンセル |

### コンテンツをアーカイブ

**任意のコンテンツを直接送信するだけでアーカイブできます！**

```text
サポートされているコンテンツタイプ：
📝 テキストメッセージ
🔗 リンク
🖼️ 画像
🎬 動画
📄 ドキュメント
🎵 オーディオ
🎤 音声
🎭 ステッカー
🎞️ アニメーション
```

**タグを追加**:

```text
メッセージを送信する際に #タグ を追加するだけです：

これはテストメッセージです #テスト #重要
https://github.com #技術 #オープンソース
```

### コンテンツを検索

```bash
# キーワード検索
/search python

# タグ検索
/search #技術

# 組み合わせ検索
/search #技術 python
```

## 🛠️ 技術アーキテクチャ

### 技術スタック

| カテゴリ | 技術 |
| ------ | ------ |
| 言語 | Python 3.14.2 |
| フレームワーク | python-telegram-bot 21.x |
| データベース | SQLite (WALモード, FTS5, AIフィールドインデックス) |
| AI | httpx (Grok-4 via xAI) |
| 設定 | PyYAML |

### アーキテクチャ設計

```text
ArchiveBot/
├── main.py                      # エントリーファイル
├── src/
│   ├── bot/                     # Bot レイヤー
│   │   ├── commands.py          # コマンド処理
│   │   ├── handlers.py          # メッセージ処理
│   │   ├── callbacks.py         # コールバック処理
│   │   ├── message_aggregator.py # メッセージアグリゲーター
│   │   └── unknown_command.py   # 未知のコマンド処理
│   ├── core/                    # コアビジネス
│   │   ├── analyzer.py          # コンテンツ分析
│   │   ├── tag_manager.py       # タグ管理
│   │   ├── storage_manager.py   # ストレージ管理
│   │   ├── search_engine.py     # 検索エンジン
│   │   ├── note_manager.py      # ノート管理
│   │   ├── trash_manager.py     # ごみ箱管理
│   │   ├── export_manager.py    # データエクスポート
│   │   ├── backup_manager.py    # バックアップ管理
│   │   ├── review_manager.py    # コンテンツレビュー
│   │   ├── ai_session.py        # AI セッション管理
│   │   ├── ai_cache.py          # AI キャッシュベースクラス
│   │   └── ai_data_cache.py     # AI データキャッシュ
│   ├── ai/                      # AI 機能
│   │   ├── summarizer.py        # AI 要約生成
│   │   ├── chat_router.py       # スマート対話ルーティング
│   │   ├── fallback.py          # AI フォールバック戦略
│   │   └── prompts/             # プロンプトテンプレート
│   │       ├── chat.py
│   │       ├── note.py
│   │       ├── summarize.py
│   │       └── title.py
│   ├── storage/                 # ストレージレイヤー
│   │   ├── base.py              # ストレージベースクラス
│   │   ├── database.py          # データベースストレージ
│   │   └── telegram.py          # Telegram ストレージ
│   ├── models/                  # データモデル
│   │   └── database.py          # データベースモデル
│   ├── utils/                   # ユーティリティモジュール
│   │   ├── config.py            # 設定管理
│   │   ├── logger.py            # ログシステム
│   │   ├── i18n.py              # 国際化
│   │   ├── language_context.py  # 言語コンテキスト
│   │   ├── message_builder.py   # メッセージビルドフレームワーク
│   │   ├── validators.py        # 入力検証
│   │   ├── helpers.py           # ヘルパー関数
│   │   ├── constants.py         # 定数定義
│   │   ├── file_handler.py      # ファイル処理
│   │   ├── link_extractor.py    # リンクメタデータ抽出
│   │   └── db_maintenance.py    # データベースメンテナンス
│   └── locales/                 # 言語ファイル
│       ├── en.json
│       ├── zh-CN.json
│       ├── zh-TW.json
│       ├── ja.json
│       ├── ko.json
│       └── es.json
└── config/
    └── config.yaml              # 設定ファイル
```

## 🤖 AI機能（オプション）

ArchiveBot は、クラウド AI サービスをサポートしており、コンテンツの要約、キーポイントの抽出、インテリジェントな分類、タグの推奨を**自動的に**生成し、コンテンツ管理の効率を大幅に向上させます。

### サポートされている AI サービス

| プロバイダー | モデル | 特徴 | 推奨シーン |
| -------- | ------ | ------ | ---------- |
| **xAI** | Grok-4 | 多言語理解が強い、速度が速い | デフォルト推奨 |
| **OpenAI** | GPT-4/GPT-3.5 | 最も強力、最高の効果 | 予算が十分 |
| **Anthropic** | Claude 3.5 | コストパフォーマンスが高い、中国語が良い | コストに敏感 |
| **阿里云** | 通義千問 | 国内サービス、アクセスが安定 | 国内ユーザー |

💡 **軽量設計**：HTTP API 呼び出しのみを使用、大規模な SDK のインストールは不要

### AI 機能のハイライト

✅ **スマート要約**：30〜100文字の簡潔な要約を自動生成  
✅ **キーポイント抽出**：3〜5のコア観点を抽出  
✅ **スマート分類**：適切なカテゴリに自動分類  
✅ **正確なタグ**：検索可能な5つの専門的なタグを生成  
✅ **スマート対話**：自然言語インタラクション、インテントと言語を自動認識  
✅ **プロンプトエンジニアリング**：ロールプレイ + Few-Shot + 思考チェーン最適化  
✅ **言語検出**：中国語/英語コンテンツを自動認識  
✅ **スマートフォールバック**：コンテンツの長さに応じて分析の深さを調整  
✅ **多言語最適化**：簡体字/繁体字/英語用語の自動適応  

### 検索強化

✅ **ページング表示**：10件/ページ、左右の矢印ナビゲーション  
✅ **AI 解析ボタン**：🤖 フォーマット表示、ワンクリックで AI 分析を表示  
✅ **クイックビュー**：クリックして完全な AI 要約/タグ/分類を表示  
✅ **直接ジャンプ**：タイトルリンクをクリックしてチャンネルメッセージにジャンプ  

### ⚠️ AI を有効にしない場合の影響

AI 機能を有効にしない場合、以下の機能が**使用できません**：

❌ **自動要約生成** - コンテンツの要約を自動生成できません  
❌ **AI スマートタグ** - AI 推奨タグを自動生成できません  
❌ **スマート分類** - コンテンツを自動分類できません  
❌ **キーポイント抽出** - コンテンツのキーポイントを抽出できません  
❌ **スマート対話** - 自然言語インタラクションを使用できません  
❌ **検索 AI 解析** - 検索結果に🤖ボタンと AI 情報がありません  

**✅ 影響を受けないコア機能：**

✅ コンテンツのアーカイブ保存  
✅ 手動タグ（#tag）  
✅ 全文検索（FTS5）  
✅ ノートシステム  
✅ ごみ箱  
✅ データエクスポート/バックアップ  
✅ すべてのコマンドが正常に使用可能  

> 💡 **推奨**：AI を有効にしなくても、ArchiveBot のコアアーカイブおよび検索機能は完全に使用できます。まず基本機能を使用し、必要に応じて後で AI を有効にすることができます。

### AI を素早く有効にする

1. **API キーを設定**

`config/config.yaml` を編集：

```yaml
ai:
  enabled: true              # AI 機能を有効化
  auto_summarize: true       # 自動要約生成
  auto_generate_tags: true   # AI タグ自動生成
  api:
    provider: xai            # プロバイダー: xai/openai/anthropic/qwen
    api_key: 'xai-xxx'       # API キー
    base_url: 'https://api.x.ai/v1'  # API エンドポイント
    model: grok-4-1-fast-non-reasoning  # 応答生成用の高速モデル
    reasoning_model: grok-4-1-fast-reasoning  # インテント分析用の推論モデル
    max_tokens: 1000         # 最大トークン数
    timeout: 30              # リクエストタイムアウト（秒）
```

**他のプロバイダーの設定例：**

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
    model: gpt-4-turbo       # 応答生成用のモデル
    reasoning_model: gpt-4-turbo  # インテント分析用の推論モデル
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
    model: claude-3-5-sonnet-20241022  # 応答生成用のモデル
    reasoning_model: claude-3-5-sonnet-20241022  # インテント分析用の推論モデル
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>阿里云通義千問</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: qwen
    api_key: 'sk-xxx'
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: qwen-plus         # 応答生成用のモデル
    reasoning_model: qwen-plus  # インテント分析用の推論モデル
    max_tokens: 1000
    timeout: 30
```

</details>

1. **Bot を再起動**

```bash
python main.py
```

1. **AI 状態を確認**

```bash
# Telegram で Bot に次のコマンドを送信
/ai
```

1. **AI 機能の使用を開始**

Bot に任意のコンテンツ（テキスト/リンク/画像/ドキュメントなど）を送信すると、AI がバックグラウンドで自動的に分析します。`/search` で検索すると、AI 分析のあるコンテンツには🤖ボタンが表示され、クリックすると完全な AI 分析結果（要約/キーポイント/タグ/分類）を確認できます。

## 📚 ドキュメント

- 📖 [クイックスタート](docs/QUICKSTART.md) - 5分でクイックスタート
- 🚀 [デプロイガイド](docs/DEPLOYMENT.md) - 本番環境のデプロイ

## 🔒 セキュリティ機能

- ✅ **SQL インジェクション保護** - パラメータ化クエリ + ESCAPE エスケープ
- ✅ **入力検証** - すべての入力は厳格に検証およびクリーニング
- ✅ **機密情報フィルタリング** - ログは token と ID を自動的にフィルタリング
- ✅ **スレッドセーフ** - RLock + WAL モード
- ✅ **認証** - owner_only デコレーターで保護
- ✅ **エラー処理** - 完全な例外処理と回復メカニズム

## 🎯 開発ロードマップ

### ✅ フェーズ1（完了）

- ✅ 基本的な Bot フレームワークとコマンドシステム
- ✅ スマートコンテンツ分析とアーカイブ
- ✅ 全文検索エンジン（FTS5）
- ✅ 多言語サポート（en/zh-CN/zh-TW/zh-HK/zh-MO）
- ✅ AI スマート強化（Grok-4）
  - ✅ スマート要約/キーポイント/分類/タグ
  - ✅ スマートインテント認識と自然言語インタラクション
  - ✅ プロンプトエンジニアリング最適化
  - ✅ コンテンツ言語検出
  - ✅ スマートフォールバック戦略
  - ✅ 多言語用語最適化
- ✅ 検索エクスペリエンス最適化
  - ✅ ページング表示（10件/ページ）
  - ✅ AI 解析ボタン
  - ✅ ナビゲーション最適化
- ✅ 簡素化された Telegram ストレージ戦略

### ✅ フェーズ2（完了）

- ✅ ノートと注釈システム
  - ✅ 独立したノートと関連ノート
  - ✅ ノートモード クイック追加
  - ✅ ノートリスト表示
  - ✅ ノート状態表示（📝/📝✓）
- ✅ お気に入りコレクション機能
  - ✅ ワンクリックでお気に入りマーク（🤍/❤️）
  - ✅ お気に入りフィルタークエリ
  - ✅ お気に入り状態表示
- ✅ クイック操作ボタン
  - ✅ 転送機能（↗️）
  - ✅ 各レコードの操作ボタン
  - ✅ アーカイブ成功メッセージの操作ボタン
- ✅ ごみ箱システム
  - ✅ ソフト削除メカニズム
  - ✅ コンテンツの復元
  - ✅ 定期的なクリーンアップ
- ✅ データエクスポート機能（Markdown/JSON/CSV）
- ✅ 自動バックアップシステム
  - ✅ スケジュールされたバックアップスケジューリング（毎時チェック）
  - ✅ バックアップファイル管理
  - ✅ バックアップの復元
  - ✅ 設定可能なバックアップ間隔

### ✅ フェーズ3（完了）

- ✅ ユーザーエクスペリエンスの最適化
  - ✅ コマンドエイリアスサポート（/s = /search, /t = /tags, /st = /stats, /la = /language）
  - ✅ 自動重複検出（ファイル MD5 検出、重複アーカイブを防ぐ）
- ✅ コンテンツレビュー機能
  - ✅ アクティビティ統計レポート（週/月/年のトレンド、人気タグ、毎日のアクティビティ）
  - ✅ ランダムレビュー表示（統計レポートにランダムな履歴コンテンツを自動的に含む）
  - ✅ `/review` コマンド（ボタンで期間を選択）
  - ✅ `/rand` 独立したランダムレビューコマンド（設定可能な数量、履歴アーカイブをすばやく表示）
- ✅ AI機能強化
  - ✅ 機密コンテンツをスマートに認識して指定チャンネルにアーカイブ
  - ✅ AI 参照コンテンツは指定アーカイブチャンネルを除外
  - ✅ AI 参照コンテンツは指定タグとカテゴリを除外
- ✅ アーカイブ機能強化
  - ✅ 転送元に基づいて指定アーカイブチャンネル
  - ✅ 個人が直接送信したドキュメントを指定アーカイブチャンネル
  - ✅ タグに基づいて指定アーカイブチャンネル

### 📝 フェーズ4（将来の計画）

- 🔄 バッチ操作（低レベル API は完了、UI は開発中）
  - 🚧 バッチタグ置換 API（replace_tag）
  - 🚧 バッチタグ削除 API
  - 🚧 バッチ操作ユーザーインターフェース（コマンド/ボタン）
  - 🚧 バッチ削除/復元
  - 🚧 バッチエクスポート
- 🚧 高度な検索
  - 🚧 組み合わせフィルター
  - 🚧 時間範囲
  - 🚧 コンテンツタイプフィルター
- 🔮 **AI 機能強化**
  - 🚧 音声からテキストへ（Whisper API）
  - 🚧 OCR 画像テキスト認識
  - 🚧 スマートコンテンツ類似性分析
- 🔮 **拡張機能**
  - 🚧 Web 管理インターフェース
  - 🚧 RESTful API インターフェース
  - 🚧 クラウドストレージ統合（Google Drive/阿里云盘）
  - 🚧 強化型URLコンテンツ反スクレイピング取得
- 🔮 **パフォーマンス最適化**
  - 🚧 キャッシュメカニズムの最適化
  - 🚧 非同期処理の強化
  - 🚧 バッチ操作の最適化

## 🤝 貢献

Issue と Pull Request の提出を歓迎します！

## 📄 ライセンス

本プロジェクトは [MIT License](LICENSE) を採用しています

## 🙏 謝辞

### 特別な感謝

- **[@WangPanBOT](https://t.me/WangPanBOT)** - Telegram ネットワークストレージロボットプロジェクト、本プロジェクトのインスピレーション源として、個人コンテンツ管理における Telegram Bot の大きな可能性を示しています

### オープンソースプロジェクト

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 優れた Telegram Bot フレームワーク、強力で使いやすい
- [SQLite](https://www.sqlite.org/) - 信頼性の高い組み込みデータベース、軽量で効率的

### AI サービスプロバイダー

- [xAI](https://x.ai/) - Grok-4 高速推論モデル
- [OpenAI](https://openai.com/) - GPT シリーズモデル
- [Anthropic](https://anthropic.com/) - Claude シリーズモデル
- [阿里云](https://www.aliyun.com/) - 通義千問モデル

## 📧 連絡先

- **GitHub Issues**: [問題を提出](https://github.com/tealun/ArchiveBot/issues)
- **X (Twitter)**: [@TealunDu](https://x.com/TealunDu)
- **Email**: <tealun@gmail.com>

### コミュニティグループ

- **中文交流群**: [@ArchiveBotCN](https://t.me/joinchat/3753827356)
- **English Group**: [@ArchiveBotEN](https://t.me/joinchat/3877196244)

---

## ⚠️ 免責事項

### 使用上の注意

1. **個人使用**：本プロジェクトは学習研究と個人使用のみを目的としており、商業目的または違法行為に使用してはなりません
2. **利用規約**：本プロジェクトを使用する際は、[Telegram 利用規約](https://telegram.org/tos)および関連する API 使用ポリシーを厳守してください
3. **コンテンツの責任**：ユーザーは Bot を通じてアーカイブされたすべてのコンテンツに対して完全な責任を負い、開発者はユーザーが保存したコンテンツに対して一切の責任を負いません
4. **データセキュリティ**：本プロジェクトはローカルデプロイツールであり、データはユーザー自身の環境に保存されます。設定ファイルとデータベースを適切に管理し、機密情報の漏洩を防いでください

### サードパーティサービス

1. **AI サービス**：AI 機能を使用すると、コンテンツがサードパーティの AI サービスプロバイダー（xAI/OpenAI/Anthropic/阿里云）に送信されます。これらのサービスプロバイダーの利用規約とプライバシーポリシーに従うことを確認してください
2. **API 使用**：ユーザーは各サードパーティサービスの API キーを自分で申請し、合法的に使用する必要があります。API の乱用によって生じる結果は、ユーザー自身が責任を負います

### 知的財産権とプライバシー

1. **著作権保護**：本プロジェクトを使用して、著作権で保護されたコンテンツ、または他者の知的財産権を侵害する資料をアーカイブしないでください
2. **プライバシーの尊重**：許可なく他者の私的情報または会話内容をアーカイブしないでください
3. **オープンソースライセンス**：本プロジェクトは MIT License を採用していますが、いかなる保証も含まれていません

### 無保証声明

1. **現状のまま提供**：本ソフトウェアは「現状のまま」提供され、明示的または黙示的な保証は提供されません。これには、商品性、特定目的への適合性、および非侵害性が含まれますが、これらに限定されません
2. **リスク自己責任**：本プロジェクトの使用によって生じる直接的または間接的な損失（データの損失、サービスの中断、ビジネスの損失などを含むがこれらに限定されない）について、開発者は一切の責任を負いません
3. **セキュリティリスク**：プロジェクトはセキュリティ対策を講じていますが、どのソフトウェアにも未知の脆弱性が存在する可能性があります。ユーザーはセキュリティリスクを自己評価する必要があります

### 法的遵守

1. **地域法**：お住まいの地域で本プロジェクトを使用することが地域の法律および規制に準拠していることを確認してください
2. **違法行為の禁止**：本プロジェクトを使用して、違法情報の拡散、プライバシーの侵害、ネットワーク攻撃などの違法行為を行うことを厳しく禁じます

---
