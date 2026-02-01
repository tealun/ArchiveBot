# ArchiveBot 开发指南

## 📊 当前项目状态

**版本**: v1.0 ✅  
**更新日期**: 2026年1月31日

### 已完成功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础框架 | ✅ | Bot启动、配置管理、多语言支持 |
| 数据库 | ✅ | SQLite + FTS5全文搜索 + AI字段索引 + 软删除 |
| 内容分析 | ✅ | 支持11种内容类型 |
| 存储管理 | ✅ | 简化三级存储（Database→Telegram→Reference） |
| 标签系统 | ✅ | 自动标签 + 手动标签 + AI智能标签 + 批量操作 |
| 搜索引擎 | ✅ | FTS5全文搜索 + 分页展示(10项/页) + AI数据搜索 |
| AI功能 | ✅ | Grok-4 API，智能摘要/关键点/分类/标签 |
| AI对话 | ✅ | 智能聊天 + 资源回复 + 意图识别 + 禁止虚构 |
| 消息构建框架 | ✅ | MessageBuilder统一列表格式 + 资源发送 |
| 多语言 | ✅ | 英语/简体中文/繁体中文（含区域术语优化） |
| 命令系统 | ✅ | 12个命令 (start/help/search/tags/stats/ai/language/note/notes/trash/export/backup) |
| 交互优化 | ✅ | AI解析按钮 + 搜索分页导航 |
| 笔记管理 | ✅ | 添加笔记、查看笔记、笔记搜索 |
| 垃圾箱 | ✅ | 软删除、恢复、永久删除、清空 |
| 导出功能 | ✅ | JSON/HTML/Markdown导出 + 打包下载 |
| 备份管理 | ✅ | 创建备份、列表查看、恢复、删除 + 自动备份调度 |
| 精选收藏 | ✅ | 一键标记精选（❤️）、精选筛选 |
| 快速转发 | ✅ | 一键转发到频道或对话 |
| 回顾统计 | ✅ | 随机回顾/活动概要 + 命令对接完成 |
| 批量操作 | 🔄 | 核心层完成（标签批量移除/替换），待UI对接 |

### 生产环境数据

- **归档记录**: 32+条
- **标签数量**: 81+个（含AI生成标签）
- **支持类型**: 文本、链接、图片、视频、文档、音频、语音、动画、贴纸、联系人、位置
- **AI状态**: 已启用（Grok-4 API via xAI）
- **存储**: SQLite数据库 + Telegram频道
- **搜索**: 分页展示（10项/页）+ AI解析查看

### 技术栈

- **语言**: Python 3.14.2
- **框架**: python-telegram-bot 21.x
- **数据库**: SQLite (WAL模式 + FTS5 + AI字段索引)
- **AI**: httpx (Grok-4 API via xAI)
- **配置**: PyYAML

### 下一步计划

**近期任务（1-2周）**：
1. **批量操作UI** - 批量标签管理的交互界面（Inline Keyboard）
2. **代码优化** - 清理未使用的导入和冗余代码
3. **智能去重** - MD5检测和内容相似度算法
4. **测试覆盖** - 为核心功能编写单元测试

**中期计划（1-2个月）**：
1. **AI增强功能**
   - 语音转文字 + 智能摘要（OpenAI Whisper API）
   - OCR识别（图片文字提取）
   - 智能分类优化
2. **用户体验优化** 
   - 命令别名
   - 智能识别
   - 配置向导
3. **高级搜索** 
   - 组合筛选
   - 时间范围
   - 内容类型筛选

**长期规划（3-6个月）**：
1. **Web管理界面** - 提供Web端浏览和管理
2. **RESTful API** - 开放API接口
3. **云存储集成** - Google Drive/阿里云盘支持
4. **性能优化** - 缓存机制、异步处理优化

---

## 1. 开发环境准备

### 1.1 必需工具

- Python 3.9+
- Git
- 文本编辑器（推荐 VS Code）
- Telegram 账号

### 1.2 获取 Bot Token

1. 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新 Bot
3. 按提示设置 Bot 名称和用户名
4. 获取 Bot Token（格式：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）
5. 保存 Token，后续配置使用

### 1.3 获取你的 Telegram ID

1. 在 Telegram 中找到 [@userinfobot](https://t.me/userinfobot)
2. 发送任意消息，Bot 会返回你的 ID
3. 记录这个 ID，用于配置 owner_id

### 1.4 创建私有频道

1. 在 Telegram 创建新频道（Channel）
2. 设置为私有频道
3. 将 Bot 添加为频道管理员
4. 获取频道 ID（通过 Bot 发送测试消息获取）

## 2. 项目结构

```
ArchiveBot/
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖
├── config/
│   ├── config.yaml        # 主配置文件（不提交到 Git）
│   └── config.template.yaml  # 配置模板
├── src/
│   ├── bot/               # Bot 相关
│   │   ├── handlers.py    # 消息处理器 ✅
│   │   ├── commands.py    # 命令处理 ✅
│   │   └── callbacks.py   # 回调处理 ✅
│   ├── core/              # 核心业务逻辑
│   │   ├── analyzer.py    # 内容分析 ✅
│   │   ├── storage_manager.py  # 存储管理 ✅
│   │   ├── tag_manager.py      # 标签管理 ✅
│   │   └── search_engine.py    # 搜索引擎 ✅
│   ├── ai/                # AI 功能 ✅
│   │   └── summarizer.py  # 智能摘要和标签生成
│   ├── storage/           # 存储提供商
│   │   ├── database.py    # 数据库存储 ✅
│   │   └── telegram.py    # Telegram 频道存储 ✅
│   ├── locales/           # 多语言支持 ✅
│   │   ├── en.json        # 英语
│   │   ├── zh-CN.json     # 简体中文
│   │   └── zh-TW.json     # 繁体中文
│   └── utils/             # 工具函数
│       ├── config.py      # 配置管理 ✅
│       ├── i18n.py        # 国际化 ✅
│       ├── helpers.py     # 辅助函数 ✅
│       └── constants.py   # 常量定义 ✅
├── data/                  # 数据目录（不提交到 Git）
│   ├── archive.db        # SQLite 数据库
│   └── temp/             # 临时文件
├── docs/                 # 文档
│   ├── ARCHITECTURE.md   # 架构文档
│   └── DEVELOPMENT.md    # 开发文档
├── tests/               # 测试
│   └── test_*.py
└── scripts/             # 脚本
    └── setup.py         # 初始化脚本
```

## 3. 开发流程

### 3.1 MVP 开发顺序

#### 第一步：基础框架（2-3天）✅ 已完成

**目标**：搭建 Bot 基础框架，能接收消息

**任务清单**：
- [x] 项目结构创建
- [x] 配置文件系统
- [x] Bot 初始化和启动
- [x] 所有者身份验证
- [x] 基础命令（/start, /help）
- [x] 消息接收和类型识别

**关键文件**：
- `main.py`：程序入口
- `src/bot/handlers.py`：消息处理
- `config/config.yaml`：配置

**验证标准**：
- Bot 能正常启动
- 能响应 /start 命令
- 能验证所有者身份，拒绝其他用户
- 能接收并打印消息内容

---

#### 第二步：数据库设计（2-3天）✅ 已完成

**目标**：设计数据库结构，实现基础 CRUD

**任务清单**：
- [x] 数据库表设计（archives, tags, config）
- [x] ORM 模型定义（或使用原生 SQL）
- [x] 数据库初始化脚本
- [x] 基础增删改查接口

**关键文件**：
- `src/models/database.py`：数据模型
- `src/storage/database.py`：数据库操作

**验证标准**：
- 数据库文件能正常创建
- 能插入和查询测试数据
- 表结构符合设计（无 user_id 字段）

---

#### 第三步：内容分析模块（3-4天）✅ 已完成

**目标**：识别和分析不同类型的内容

**任务清单**：
- [x] 内容类型识别（文本/图片/视频/文档/音频/语音/动画/贴纸/联系人/位置）
- [x] 元数据提取（文件名、大小、时间）
- [x] 文本内容处理
- [x] 链接识别和解析

**关键文件**：
- `src/core/analyzer.py`：内容分析

**实现逻辑**：

```
接收消息 → 判断类型
│
├─ 文本消息
│  ├─ 纯文本：直接存储
│  └─ 包含链接：提取 URL
│
├─ 图片消息
│  ├─ 获取 photo_id
│  ├─ 提取 caption
│  └─ 获取图片尺寸
│
├─ 视频消息
│  ├─ 获取 video_id
│  ├─ 获取时长
│  └─ 获取缩略图
│
└─ 文档消息
   ├─ 获取 file_id
   ├─ 获取文件名
   └─ 获取文件大小
```

**验证标准**：
- 能正确识别各种类型
- 元数据完整准确
- 错误处理完善

---

#### 第四步：文本/链接存储（2-3天）✅ 已完成

**目标**：实现文本和链接的归档

**任务清单**：
- [x] 文本内容存入数据库
- [x] 链接内容存入数据库
- [x] 自动标签生成（#文本、#链接）
- [x] 归档成功反馈

**关键文件**：
- `src/core/storage_manager.py`：存储管理
- `src/storage/database.py`：数据库存储

**实现逻辑**：

```python
# 伪代码
def archive_text(message):
    # 1. 提取内容
    content = message.text
    
    # 2. 生成标签
    tags = ['#文本']
    if is_url(content):
        tags.append('#链接')
    
    # 3. 存入数据库
    archive = {
        'content_type': 'text',
        'content': content,
        'storage_type': 'database',
        'created_at': now()
    }
    save_to_database(archive)
    
    # 4. 关联标签
    for tag in tags:
        associate_tag(archive.id, tag)
    
    # 5. 返回确认
    return "✅ 已归档\n🏷️ " + " ".join(tags)
```

**验证标准**：
- 文本能正确存储
- 标签正确关联
- 能通过数据库查询到

---

#### 第五步：Telegram 频道存储（3-4天）✅ 已完成

**目标**：实现小文件到 Telegram 频道的存储

**任务清单**：
- [x] 创建并配置私有频道
- [x] 实现文件发送到频道
- [x] 记录频道消息 ID
- [x] 实现从频道读取文件
- [x] 处理存储失败情况

**关键文件**：
- `src/storage/telegram.py`：Telegram 存储

**实现逻辑**：

```python
# 伪代码
def store_to_telegram(file, metadata):
    # 1. 发送到私有频道
    channel_msg = bot.send_document(
        chat_id=CHANNEL_ID,
        document=file.file_id,
        caption=metadata.caption
    )
    
    # 2. 记录到数据库
    archive = {
        'content_type': metadata.type,
        'file_id': file.file_id,
        'storage_type': 'telegram_channel',
        'storage_path': f"{CHANNEL_ID}:{channel_msg.message_id}",
        'file_size': file.file_size,
        'metadata': metadata
    }
    save_to_database(archive)
    
    return archive.id
```

**验证标准**：
- 文件成功发送到频道
- 消息 ID 正确记录
- 能通过 ID 访问文件

---

#### 第六步：基础搜索功能（2-3天）✅ 已完成

**目标**：实现简单的关键词搜索

**任务清单**：
- [x] `/search` 命令实现（支持FTS5全文搜索）
- [x] 关键词匹配查询
- [x] 搜索结果展示
- [x] 分页显示

**关键文件**：
- `src/core/search_engine.py`：搜索引擎

**实现逻辑**：

```python
# 伪代码
def search(keyword):
    # 简单的 LIKE 查询
    results = query_database(
        "SELECT * FROM archives "
        "WHERE title LIKE ? OR content LIKE ? "
        "ORDER BY created_at DESC LIMIT 10",
        f"%{keyword}%", f"%{keyword}%"
    )
    
    # 格式化结果
    return format_search_results(results)
```

**验证标准**：
- 能搜索到相关内容
- 结果按时间排序
- 展示格式友好

---

#### 第七步：标签系统（2-3天）✅ 已完成

**目标**：完善标签功能

**任务清单**：
- [x] 手动添加标签
- [x] 标签搜索
- [x] 标签列表查看
- [x] 标签统计

**关键文件**：
- `src/core/tag_manager.py`：标签管理

**功能设计**：

```
归档时添加标签：
用户: [发送图片] #旅游 #上海

查看标签列表：
/tags → 显示所有标签及使用次数

按标签搜索：
/search #旅游 → 显示所有带该标签的内容
```

**验证标准**：
- 标签能正确关联
- 标签搜索准确
- 统计数据正确

---

### 3.2 MVP 验收标准 ✅ 全部完成

完成 MVP 后，应该能实现：

✅ **基础归档** - 已完成
- 文本消息归档
- 链接归档
- 图片归档（< 10MB）
- 视频归档（< 10MB）
- 文档归档（< 10MB）
- 音频/语音归档
- 动画/贴纸归档
- 联系人/位置归档

✅ **标签管理** - 已完成
- 自动标签（类型标签）
- 手动标签
- 标签搜索
- AI智能标签（可选）

✅ **搜索功能** - 已完成
- 关键词搜索（FTS5全文搜索）
- 标签搜索
- 高级搜索（tag:, type:, before:, after:）
- 分页结果展示

✅ **基础命令** - 已完成
- `/start` - 初始化
- `/help` - 帮助
- `/search <关键词>` - 搜索
- `/tags` - 标签列表
- `/stats` - 统计信息
- `/language` - 切换语言
- `/summarize` - AI摘要（可选）
- `/ai` - AI状态（可选）

✅ **多语言支持** - 已完成
- 英语（en）
- 简体中文（zh-CN）
- 繁体中文（zh-TW）

✅ **AI功能（云端API）** - 已完成
- 云端API支持（OpenAI/Claude/Qwen）
- 自动标签生成
- 自动摘要生成
- HTTP直连（仅需httpx，轻量级）

---

### 3.3 AI功能实现✅

在MVP基础上，已实现AI智能增强功能：

#### 云端API方案

**架构设计**：
- **云端API**：OpenAI/Claude/Qwen HTTP直连
  - 优势：效果好、速度快、无需本地资源
  - 注意：仅HTTP调用，无SDK依赖（仅需httpx，2MB vs 150MB）
  - 支持：OpenAI GPT-4/3.5、Claude、通义千问

**已实现功能**：

1. **自动标签生成**
   - AI分析内容自动生成3-5个相关标签
   - 与手动标签合并去重
   - 支持中英文标签

2. **自动摘要生成**
   - 长文本（>500字符）自动生成摘要
   - 提取关键信息
   - 存储在archive记录中

3. **手动AI命令**
   - `/summarize` - 对归档内容生成摘要
   - `/ai` - 查看AI配置和状态

**配置示例**：
```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  
  api:
    provider: openai  # 支持 openai, claude, qwen
    api_key: 'xai-xxx'  # xAI API Key for Grok-4
    base_url: 'https://api.x.ai/v1'  # xAI endpoint
    model: grok-beta  # Grok-4模型
    max_tokens: 1000
    timeout: 30
```

**使用统计**（当前生产环境）：
- 32个归档记录
- 81个标签（包含AI生成的精准标签）
- AI功能已启用并正常工作
- Grok-4多语言智能分析（支持中英文内容语言检测）
- 搜索结果分页展示（10项/页）
- AI解析按钮（标题预览 + 完整解析）

### 3.4 AI提示词优化✅

已实现完整的AI提示词工程策略：

#### 1. **角色扮演（Role-Playing）**
```
你是一位专业的信息管理员和知识组织专家。
你的任务是分析各类文档、媒体文件，帮助用户：
1. 快速理解核心内容
2. 建立清晰的分类体系
3. 创建精准的搜索标签
```

#### 2. **上下文信息（Context Information）**
提供文件元数据增强分析准确性：
- 文件类型和扩展名
- 文件大小
- 已有标签（避免重复）
- 标题信息
- 内容语言（自动检测）
- 分析深度（minimal/brief/full）

#### 3. **Few-Shot示例学习**
```
输入：华尔街之狼电影片段.mp4
输出：{
  "summary": "描述华尔街金融交易员生活的电影片段，展示了奢华与欲望",
  "key_points": ["金融欺诈主题", "华尔街背景", "传记电影"],
  "category": "娱乐",
  "suggested_tags": ["电影", "金融", "传记", "影片片段", "马丁·斯科塞萨"]
}
```

#### 4. **输出质量约束**
- 摘要：30-100字，客观描述
- 关键点：每个10-30字，核心信息
- 分类：只返回一个主分类
- 标签：5个精准标签（主题词+属性词）
- ✓ 正确："Python教程"、"机器学习"
- ✗ 错误："文件"、"内容"（太宽泛）

#### 5. **思维链（Chain-of-Thought）**
```
第一步：识别内容类型和主题
第二步：提取核心信息和关键观点
第三步：确定适合的分类
第四步：生成精准、可搜索的标签
```

#### 6. **内容语言检测**
```python
def detect_content_language(content: str) -> str:
    """检测内容主要语言（中文/英文/混合/未知）"""
    # 基于字符统计的智能检测
    # 前500字符采样分析
```

#### 7. **智能降级策略**
根据内容长度自动调整分析深度：
- **minimal** (<50字符): 基于文件名推测
- **brief** (50-200字符): 简要分析
- **full** (>=200字符): 完整深度分析

#### 8. **多语言术语优化**

**简体中文**：文档、教程、视频、照片  
**繁体中文**：文件、教學、影片、相片  
**英文**：完整优化的专业术语

每种语言的prompt都包含所有优化特性，确保全球用户获得一致的高质量体验。

---

## 4. v1.0 开发计划（1-2个月）

### 4.1 用户体验优化

#### 快速笔记和批注（3-4天）✅ 已完成

**任务清单**：
- [x] 回复归档消息添加笔记
- [x] 笔记存储和关联
- [x] 多次追加笔记
- [x] 笔记搜索集成
- [x] 查看归档的所有笔记

**关键文件**：
- `src/core/note_manager.py`
- `/note` - 添加笔记命令
- `/notes` - 查看笔记命令

#### 批量操作（3-4天）🚧 进行中

**任务清单**：
- [ ] 批量选择界面（Inline Keyboard）
- [x] 批量打标签（核心层）- `tag_manager.remove_tag/replace_tag`
- [ ] 批量删除（需对接命令）
- [x] 批量导出（已有 `/export` 命令）
- [ ] 操作确认和撤销

**关键文件**：
- `src/core/tag_manager.py` - 批量标签操作
- `src/storage/database.py` - 数据层批量方法

**待完成**：命令层对接和交互界面

#### 快捷命令和别名（2-3天）

**任务清单**：
- [ ] 命令别名系统
- [ ] 智能识别（无需命令前缀）
- [ ] 快捷标签映射
- [ ] 语音命令支持

**关键文件**：
- `src/bot/command_parser.py`

#### 交互式配置向导（2-3天）

**任务清单**：
- [ ] 首次使用引导
- [ ] 可视化配置界面
- [ ] 健康检查功能
- [ ] 一键修复常见问题

**关键文件**：
- `src/bot/setup_wizard.py`

### 4.2 数据管理

#### 回顾和统计（2-3天）🚧 进行中

**任务清单**：
- [x] 随机回看功能（核心层）- `ReviewManager.get_random_archive`
- [x] 周/月/年统计（核心层）- `ReviewManager.get_activity_summary`
- [x] 归档趋势图（数据层）- 日活跃度、热门标签
- [x] 导出统计报告（核心层）- `ReviewManager.build_report`

**关键文件**：
- `src/core/review_manager.py` ✅ 已完成
- `src/storage/database.py` - `get_activity_summary`, `get_random_archive`

**待完成**：
- [ ] 对接 Bot 命令（/review, /recap 等）
- [ ] 统计报告格式化输出
- [ ] 图表可视化（可选）

#### 智能去重（3-4天）

**任务清单**：
- [ ] MD5 检测
- [ ] 内容相似度算法
- [ ] 归档前检查
- [ ] 合并重复内容
- [ ] 模糊匹配

**关键文件**：
- `src/core/dedup_manager.py`

#### 数据库备份（2-3天）✅ 已完成

**任务清单**：
- [x] 手动备份功能
- [x] 备份元数据记录
- [x] 备份列表查看
- [x] 一键恢复功能
- [ ] 自动备份调度（待实现）
- [ ] 增量备份算法（待实现）

**关键文件**：
- `src/core/backup_manager.py` ✅ 已完成
- `/backup` - 备份管理命令

**已实现功能**：
- 创建数据库完整备份
- 列出历史备份记录
- 从备份恢复数据库
- 删除旧备份文件

#### 垃圾箱和清理（2-3天）🚧 进行中

**任务清单**：
- [x] 垃圾箱机制（软删除）
- [x] 查看垃圾箱内容
- [x] 恢复已删除内容
- [x] 永久删除功能
- [ ] 定期清理策略（待实现）
- [ ] 智能清理建议（待实现）
- [ ] 归档压缩（待实现）

**关键文件**：
- `src/core/trash_manager.py` ✅ 已完成
- `/trash` - 垃圾箱管理命令
- `database.py` - 软删除支持（deleted/deleted_at字段）

**已实现功能**：
- 软删除归档（moved to trash）
- 垃圾箱列表查看
- 从垃圾箱恢复
- 永久删除（物理删除）
- 清空垃圾箱

---

## 5. v1.5 开发计划（2-3个月）

### 5.1 AI 智能增强

#### 智能摘要生成（1周）✅ 已完成

**任务清单**：
- [x] AI API 集成（OpenAI/Claude/Qwen）
- [x] 文章摘要生成
- [x] 关键信息提取
- [x] 自动标签生成
- [ ] TL;DR 模式（待优化）
- [ ] Markdown 思维导图生成（待开发）

**关键文件**：
- `src/ai/summarizer.py`

#### OCR 和内容提取（1周）

**任务清单**：
- [ ] 图片 OCR 集成
- [ ] PDF 文本提取
- [ ] 网页内容快照
- [ ] 视频字幕提取（可选）

**关键文件**：
- `src/ai/content_extractor.py`

#### 自动分类和整理（1周）

**任务清单**：
- [ ] AI 分类模型
- [ ] 自动命名
- [ ] 智能推荐标签
- [ ] 自动归档规则

**关键文件**：
- `src/ai/classifier.py`

#### 翻译功能（3-4天）

**任务清单**：
- [ ] 翻译 API 集成
- [ ] 归档时自动翻译
- [ ] 双语对照显示
- [ ] 跨语言搜索

**关键文件**：
- `src/ai/translator.py`

### 5.2 数据增强

#### 关联和引用系统（1周）

**任务清单**：
- [ ] 手动关联接口
- [ ] 关联关系存储
- [ ] 关联网络可视化
- [ ] 智能推荐相关内容
- [ ] 引用语法支持

**关键文件**：
- `src/core/relation_manager.py`

#### 版本管理（3-4天）

**任务清单**：
- [ ] 变更历史记录
- [ ] 版本对比
- [ ] 回滚功能
- [ ] 适用于笔记和链接

**关键文件**：
- `src/core/version_manager.py`

#### 高级筛选和视图（1周）

**任务清单**：
- [ ] 时间线视图
- [ ] 看板视图
- [ ] 热力图
- [ ] 自定义视图保存

**关键文件**：
- `src/core/view_manager.py`

#### 数据分析面板（1周）

**任务清单**：
- [ ] 归档统计图表
- [ ] 标签云可视化
- [ ] 存储分析
- [ ] 活跃度分析
- [ ] 导出 Markdown/PDF 报告

**关键文件**：
- `src/core/analytics.py`

### 5.3 性能优化

#### 缓存优化（3-4天）

**任务清单**：
- [ ] 常用内容缓存
- [ ] 搜索结果缓存
- [ ] 标签列表缓存
- [ ] 智能预加载

**关键文件**：
- `src/core/cache_manager.py`

---

## 6. v2.0 开发计划（长期迭代）

### 6.1 知识管理

#### 智能问答（RAG）（2周）

**任务清单**：
- [ ] 向量数据库集成
- [ ] 内容向量化
- [ ] 问答接口
- [ ] 引用来源标注
- [ ] 本地 Embedding 支持

**关键文件**：
- `src/ai/rag_engine.py`

#### 知识图谱（2周）

**任务清单**：
- [ ] 关系图谱构建
- [ ] 可视化展示
- [ ] 导出为 Obsidian/Notion 格式
- [ ] 知识连接发现

**关键文件**：
- `src/core/knowledge_graph.py`

#### 归档模板（1周）

**任务清单**：
- [ ] 模板定义系统
- [ ] 预设模板（书籍、电影等）
- [ ] 自定义模板
- [ ] 结构化数据存储

**关键文件**：
- `src/core/template_manager.py`

#### 时光机（1周）

**任务清单**：
- [ ] 历史的今天
- [ ] 随机回忆
- [ ] 年度报告生成
- [ ] 成长轨迹

**关键文件**：
- `src/core/timemachine.py`

### 6.2 集成扩展

#### Web 管理界面（3-4周）

**任务清单**：
- [ ] 前端框架搭建
- [ ] 归档浏览界面
- [ ] 搜索和筛选
- [ ] 数据可视化
- [ ] 响应式设计

**技术栈**：
- FastAPI / Flask
- Vue.js / React
- Chart.js

#### 浏览器扩展（2-3周）

**任务清单**：
- [ ] Chrome 扩展开发
- [ ] 一键归档网页
- [ ] 右键菜单
- [ ] 选中文本归档

**关键文件**：
- `extensions/chrome/`

#### RSS 订阅（1周）

**任务清单**：
- [ ] RSS 源管理
- [ ] 自动抓取
- [ ] 智能过滤
- [ ] 生成 RSS 输出

**关键文件**：
- `src/integrations/rss_manager.py`

#### 社交媒体同步（2周）

**任务清单**：
- [ ] Twitter API 集成
- [ ] GitHub Star 同步
- [ ] YouTube 播放列表
- [ ] 微博收藏（可选）

**关键文件**：
- `src/integrations/social_sync.py`

### 6.3 高级功能

#### 内容监控（1周）

**任务清单**：
- [ ] 网页变化监控
- [ ] 关键词告警
- [ ] 定期检查调度
- [ ] 通知推送

**关键文件**：
- `src/core/monitor.py`

#### 游戏化（3-4天）

**任务清单**：
- [ ] 成就系统
- [ ] 连续记录
- [ ] 挑战任务
- [ ] 徽章设计

**关键文件**：
- `src/core/gamification.py`

#### 加密功能（1周）

**任务清单**：
- [ ] 敏感归档加密
- [ ] 密码保护
- [ ] 隐藏模式
- [ ] 端到端加密

**关键文件**：
- `src/core/encryption.py`

#### 主题和个性化（3-4天）

**任务清单**：
- [ ] 回复格式自定义
- [ ] Emoji 风格
- [ ] 通知频率设置
- [ ] 语言切换

**关键文件**：
- `src/core/personalization.py`

---

## 7. 开发规范

### 5.1 代码风格

- 遵循 PEP 8
- 使用类型注解（Type Hints）
- 函数和类要有文档字符串

```python
def archive_content(
    user_id: int,
    content: str,
    content_type: str,
    tags: List[str]
) -> int:
    """
    归档内容到数据库
    
    Args:
        user_id: 用户 ID
        content: 内容文本
        content_type: 内容类型
        tags: 标签列表
        
    Returns:
        归档 ID
    """
    pass
```

### 5.2 错误处理

- 所有外部调用（API、数据库、文件 IO）都要 try-catch
- 记录错误日志
- 给用户友好的错误提示

```python
try:
    result = upload_to_drive(file)
except NetworkError:
    logger.error("网络错误", exc_info=True)
    await message.reply("❌ 上传失败：网络连接错误，请稍后重试")
except QuotaExceeded:
    await message.reply("❌ 上传失败：网盘空间不足")
except Exception as e:
    logger.error(f"未知错误: {e}", exc_info=True)
    await message.reply("❌ 上传失败：系统错误")
```

### 5.3 日志记录

- 使用 Python logging 模块
- 分级记录（DEBUG/INFO/WARNING/ERROR）
- 敏感信息脱敏

```python
import logging

logger = logging.getLogger(__name__)

# INFO: 正常操作
logger.info(f"用户 {user_id} 归档了文件: {filename}")

# WARNING: 需要注意的情况
logger.warning(f"用户 {user_id} 接近配额上限")

# ERROR: 错误
logger.error(f"上传失败: {error}", exc_info=True)
```

### 5.4 配置管理

- 敏感信息不写死在代码中
- 使用配置文件或环境变量
- 提供配置模板

```python
# 不要这样
BOT_TOKEN = "123456:ABC-DEF..."

# 应该这样
BOT_TOKEN = os.getenv("BOT_TOKEN") or config.get("bot.token")
```

### 5.5 测试

- 核心功能要写单元测试
- 关键流程要写集成测试
- 测试覆盖率 > 60%

```python
# tests/test_analyzer.py
def test_content_type_detection():
    # 测试文本消息
    msg = create_mock_message(text="Hello")
    assert detect_content_type(msg) == 'text'
    
    # 测试图片消息
    msg = create_mock_message(photo=Mock())
    assert detect_content_type(msg) == 'image'
```

---

## 8. 调试技巧

### 8.1 日志调试

```python
# 开启详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 8.2 Bot 调试

- 创建测试 Bot（不影响正式 Bot）
- 使用 Telegram Bot API 的 webhook 模式方便调试
- 或使用 polling 模式在本地运行

### 8.3 数据库调试

```python
# 打印 SQL 查询
import sqlite3
sqlite3.enable_callback_tracebacks(True)

# 或使用 ORM 的 echo 模式
engine = create_engine('sqlite:///archive.db', echo=True)
```

---

## 9. 常见问题

### 9.1 如何获取频道 ID？

```python
# 方法1：让 Bot 发送消息到频道，查看返回的 chat_id
msg = await bot.send_message(chat_id="@your_channel_username", text="test")
print(msg.chat.id)  # 这就是频道 ID

# 方法2：使用 getUpdates API
```

### 9.2 如何处理大文件上传超时？

```python
# 使用异步上传
async def upload_large_file(file):
    # 显示进度
    progress_msg = await bot.send_message("⏳ 上传中...")
    
    try:
        # 异步上传
        result = await async_upload(file, on_progress=lambda p: 
            progress_msg.edit_text(f"⏳ 上传中... {p}%")
        )
        await progress_msg.edit_text("✅ 上传完成")
    except TimeoutError:
        await progress_msg.edit_text("❌ 上传超时")
```

### 9.3 如何实现配置热更新？

```python
# 使用文件监听
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('config.yaml'):
            reload_config()
```

---

## 10. 发布流程

### 10.1 版本号规则

- 遵循语义化版本（Semantic Versioning）
- 格式：`主版本号.次版本号.修订号`
- 例如：`v1.0.0`、`v1.1.0`、`v1.1.1`

### 10.2 发布清单

- [ ] 代码审查
- [ ] 测试通过
- [ ] 更新 CHANGELOG
- [ ] 更新文档
- [ ] 打 Git Tag
- [ ] 发布 Release
- [ ] 更新 README

### 10.3 开源注意事项

- 添加开源协议（MIT License）
- 移除所有敏感信息（Token、密钥）
- 提供详细的 README
- 添加贡献指南（CONTRIBUTING.md）

---

## 11. 资源链接

### 11.1 官方文档

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [python-telegram-bot 文档](https://docs.python-telegram-bot.org/)
- [Google Drive API](https://developers.google.com/drive)
- [阿里云盘开放平台](https://www.aliyundrive.com/drive/file/backup)

### 11.2 参考项目

- 类似的归档 Bot 项目
- Telegram 工具类 Bot
- 网盘同步工具

### 11.3 社区

- Telegram Bot 开发者社区
- Python 开发社区
- GitHub Discussions

---

## 12. 下一步

1. **立即开始**：创建项目目录，搭建基础框架
2. **分阶段开发**：按 MVP → v1.0 → v2.0 逐步完善
3. **持续迭代**：根据实际使用反馈调整功能
4. **社区建设**：开源后与社区互动，收集需求

---

好的规划是成功的一半，现在开始动手吧！🚀
