# ArchiveBot 快速开始指南

## 安装步骤

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 配置Bot

#### 2.1 获取Bot Token

1. 在Telegram中找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新Bot
3. 按提示设置Bot名称和用户名
4. 复制获得的Bot Token

#### 2.2 获取你的Telegram ID

1. 在Telegram中找到 [@userinfobot](https://t.me/userinfobot)
2. 发送任意消息
3. 记录返回的ID

#### 2.3 创建私有频道（可选，用于文件存储）

1. 创建新频道并设为私有
2. 将Bot添加为频道管理员
3. 获取频道ID（通过Bot发送测试消息）

#### 2.4 配置文件

```bash
# 复制配置模板
cp config/config.template.yaml config/config.yaml

# 编辑配置文件
# Windows: notepad config/config.yaml
# Linux/Mac: nano config/config.yaml
```

填入你的信息：
```yaml
bot:
  token: "你的Bot Token"
  owner_id: 你的Telegram ID
  language: "zh-CN"  # 或 "en", "zh-TW"

storage:
  telegram:
    channel_id: 你的频道ID  # 可选
```

### 3. 运行Bot

```bash
python main.py
```

## 使用方法

### 基础命令

- `/start` - 初始化Bot
- `/help` - 查看帮助
- `/search <关键词>` - 搜索归档内容
- `/tags` - 查看所有标签
- `/stats` - 查看统计信息
- `/language` - 切换语言

### 归档内容

直接发送任何内容给Bot：
- 文本消息
- 图片
- 视频
- 文档
- 链接
- 等等...

### 添加标签

发送内容时加上标签：
```
这是一篇关于Python的文章 #Python #编程 #学习
```

### 搜索

```
/search Python        # 关键词搜索
/search #Python       # 标签搜索
/search #Python 教程  # 组合搜索
```

## 多语言支持

ArchiveBot支持三种语言：
- **English** (en)
- **简体中文** (zh-CN)
- **繁體中文** (zh-TW)

使用 `/language` 命令切换语言。

## 故障排除

### Bot无法启动

1. 检查config.yaml是否正确配置
2. 确认Bot Token有效
3. 确认owner_id正确
4. 查看data/bot.log日志文件

### 权限错误

确保你的Telegram ID与config.yaml中的owner_id匹配。

### 数据库错误

删除data/archive.db文件，重新启动Bot会自动创建新数据库。

## 目录结构

```
ArchiveBot/
├── main.py                 # 程序入口
├── requirements.txt        # Python依赖
├── config/
│   ├── config.yaml        # 配置文件（需创建）
│   └── config.template.yaml  # 配置模板
├── src/
│   ├── bot/               # Bot交互层
│   ├── core/              # 核心业务逻辑
│   ├── storage/           # 存储提供商
│   ├── models/            # 数据模型
│   ├── utils/             # 工具函数
│   └── locales/           # 语言文件
├── data/                  # 数据目录
│   ├── archive.db        # SQLite数据库
│   └── temp/             # 临时文件
└── docs/                 # 文档
```

## 下一步

查看完整文档：
- [架构设计](docs/ARCHITECTURE.md)
- [开发指南](docs/DEVELOPMENT.md)

开始使用你的个人归档系统吧！🚀
