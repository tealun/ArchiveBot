# ArchiveBot 测试清单

## 🧪 功能测试清单

### 1. Bot 启动测试 ✅
- [ ] 配置文件正确加载
- [ ] 数据库成功初始化
- [ ] 日志系统正常工作
- [ ] Bot 成功连接到 Telegram
- [ ] 启动日志显示统计信息

**测试命令**:
```bash
python main.py
```

**预期输出**:
```
==================================================
ArchiveBot Starting...
==================================================
Language: English
Database: data/archive.db
Database stats: 0 archives, 0 tags
Bot owner ID: <your_id>
Bot is ready! Starting polling...
```

---

### 2. 身份验证测试 ✅
- [ ] 使用 owner_id 账户发送 /start - 应成功
- [ ] 使用其他账户发送 /start - 应被拒绝
- [ ] 检查日志中的未授权访问记录

**测试步骤**:
1. 用自己的账户向 bot 发送 /start
2. 用其他账户（或询问朋友）发送 /start
3. 检查 `data/bot.log` 中是否有 "Unauthorized" 记录

**预期结果**:
- Owner: 看到欢迎消息
- Others: 看到 "⛔ Unauthorized" 消息

---

### 3. 命令测试 ✅

#### /start 命令
- [ ] 返回欢迎消息
- [ ] 消息包含功能说明
- [ ] 消息格式正确

#### /help 命令
- [ ] 返回帮助信息
- [ ] 包含所有命令说明
- [ ] 包含使用示例

#### /stats 命令
- [ ] 显示统计信息
- [ ] 显示归档数量
- [ ] 显示标签数量
- [ ] 显示存储使用情况

#### /tags 命令
- [ ] 初始为空时显示提示
- [ ] 有标签时显示列表
- [ ] 显示每个标签的数量

#### /language 命令
- [ ] 显示语言选择按钮
- [ ] 包含三种语言（英文、简体中文、繁体中文）

---

### 4. 内容归档测试 ✅

#### 文本消息
```
测试文本：这是一条测试消息 #测试 #文本
```
- [ ] 成功归档
- [ ] 返回确认消息
- [ ] 自动添加 #text 标签
- [ ] 正确识别手动标签（#测试 #文本）
- [ ] 数据库中有记录

#### 链接消息
```
https://github.com #链接 #技术
```
- [ ] 成功归档
- [ ] 识别为 link 类型
- [ ] 自动添加 #link 标签
- [ ] 保存 URL

#### 图片
- [ ] 上传图片到 bot
- [ ] 添加描述和标签: `这是测试图片 #图片 #测试`
- [ ] 成功归档到 Telegram 频道
- [ ] 返回的 storage_type 为 "telegram"

#### 文档
- [ ] 上传文档（PDF/DOCX等）
- [ ] 添加描述: `测试文档 #文档`
- [ ] 根据大小选择正确的存储策略
- [ ] 记录文件大小

#### 视频
- [ ] 上传短视频
- [ ] 添加标签
- [ ] 检查存储类型

#### 其他类型
- [ ] 音频文件
- [ ] 语音消息
- [ ] 贴纸
- [ ] 动画 GIF

---

### 5. 标签系统测试 ✅

#### 自动标签
- [ ] text 类型自动添加 #text
- [ ] image 类型自动添加 #image
- [ ] 其他类型类似

#### 手动标签
- [ ] 识别 #标签 格式
- [ ] 支持中文标签
- [ ] 支持英文标签
- [ ] 支持数字和下划线
- [ ] 拒绝过长标签（>50字符）
- [ ] 拒绝无效字符

#### 标签统计
- [ ] /tags 显示所有标签
- [ ] 每个标签显示计数
- [ ] 计数正确

---

### 6. 搜索功能测试 ✅

#### 关键词搜索
```
/search 测试
```
- [ ] 返回包含"测试"的所有归档
- [ ] 显示标题和时间
- [ ] 结果正确

#### 标签搜索
```
/search #图片
```
- [ ] 返回所有带 #图片 标签的归档
- [ ] 结果正确

#### 组合搜索
```
/search #技术 python
```
- [ ] 返回带 #技术 标签且包含 "python" 的归档
- [ ] 结果正确

#### 空结果
```
/search 不存在的内容xxxyyyzzz
```
- [ ] 返回 "No results found"
- [ ] 提示尝试其他关键词

#### 中文搜索
```
/search 中文
```
- [ ] 正确搜索中文内容
- [ ] 支持简体和繁体

---

### 7. 多语言测试 ✅

#### 切换到简体中文
1. 发送 /language
2. 点击 "简体中文" 按钮
3. 检查所有消息是否变为简体中文

#### 切换到繁体中文
1. 发送 /language
2. 点击 "繁體中文" 按钮
3. 检查所有消息是否变为繁体中文

#### 切换回英文
1. 发送 /language
2. 点击 "English" 按钮
3. 检查所有消息是否变为英文

#### 测试项目
- [ ] 欢迎消息翻译正确
- [ ] 帮助信息翻译正确
- [ ] 错误消息翻译正确
- [ ] 按钮文字翻译正确
- [ ] 标签名称翻译正确（自动标签）

---

### 8. 存储策略测试 ✅

#### 小文件 (<10MB)
- [ ] 存储到数据库
- [ ] storage_type = "database"
- [ ] storage_path 为空或 NULL

#### 中等文件 (10MB - 100MB)
- [ ] 存储到 Telegram 频道
- [ ] storage_type = "telegram"
- [ ] storage_path 格式: "channel_id:message_id"
- [ ] 可以在频道中看到文件

#### 大文件 (>100MB)
- [ ] storage_type = "reference"
- [ ] 不实际存储文件
- [ ] 保存文件信息

---

### 9. 数据库测试 ✅

#### 完整性检查
```bash
python -c "from src.utils.db_maintenance import verify_database; verify_database('data/archive.db')"
```
- [ ] 返回 "ok"
- [ ] 无错误消息

#### 备份功能
```bash
python -c "from src.utils.db_maintenance import backup_database; backup_database('data/archive.db')"
```
- [ ] 创建备份文件
- [ ] 文件名包含时间戳
- [ ] 备份文件在 data/backups/ 目录

#### 优化功能
```bash
python -c "from src.utils.db_maintenance import optimize_database; optimize_database('data/archive.db')"
```
- [ ] 执行 VACUUM
- [ ] 执行 ANALYZE
- [ ] 数据库文件大小可能减小

---

### 10. 错误处理测试 ✅

#### 无效命令
```
/notexist
```
- [ ] 不崩溃
- [ ] 忽略或提示未知命令

#### 无效标签
```
发送消息: #这是一个超过五十个字符的非常非常非常长的标签名称应该被拒绝
```
- [ ] 标签被清理或忽略
- [ ] 仍然成功归档

#### 网络错误
- [ ] 断开网络
- [ ] 尝试归档内容
- [ ] 检查错误日志
- [ ] 恢复网络后重试

#### 频道权限错误
- [ ] 移除 bot 的频道管理员权限
- [ ] 尝试归档图片
- [ ] 应降级为 reference 类型
- [ ] 记录错误日志

---

### 11. 并发测试 ✅

#### 快速连续发送
- [ ] 快速发送 10 条消息
- [ ] 所有消息都成功归档
- [ ] 无数据库锁定错误
- [ ] 标签计数正确

#### 同时搜索和归档
- [ ] 一个终端归档内容
- [ ] 另一个终端搜索
- [ ] 两者都正常工作

---

### 12. 安全测试 ✅

#### SQL 注入测试
```
/search ' OR '1'='1
/search '; DROP TABLE archives; --
```
- [ ] 不会执行 SQL 注入
- [ ] 返回安全的搜索结果或无结果

#### 特殊字符
```
发送消息: <script>alert('xss')</script> #测试
```
- [ ] 成功归档
- [ ] 特殊字符被正确处理
- [ ] 不会影响其他功能

#### 敏感信息泄露
```bash
# 检查日志文件
grep -E "bot_token|[0-9]{8,}" data/bot.log
```
- [ ] Bot token 应该是 [REDACTED]
- [ ] User ID 应该是 [REDACTED]

---

### 13. 性能测试 ✅

#### 归档 100 条消息
- [ ] 连续归档 100 条短文本
- [ ] 检查响应时间
- [ ] 平均响应时间 < 1 秒

#### 搜索性能
- [ ] 归档 1000 条消息
- [ ] 执行搜索
- [ ] 搜索时间 < 1 秒

#### 数据库大小
- [ ] 归档 1000 条消息后
- [ ] 检查数据库文件大小
- [ ] 应该 < 50MB

---

### 14. 日志测试 ✅

#### 日志文件
```bash
cat data/bot.log
```
- [ ] 文件存在
- [ ] 包含启动信息
- [ ] 包含操作日志
- [ ] 包含错误日志（如果有）
- [ ] 敏感信息已过滤

#### 日志级别
- [ ] INFO 级别记录正常操作
- [ ] ERROR 级别记录错误
- [ ] DEBUG 级别（如果启用）记录详细信息

---

### 15. 优雅关闭测试 ✅

#### Ctrl+C 关闭
- [ ] 按 Ctrl+C
- [ ] 看到 "Bot stopped by user"
- [ ] 数据库连接关闭
- [ ] "ArchiveBot shutdown complete"

#### SIGTERM 信号
```bash
# 获取 PID
ps aux | grep main.py

# 发送 SIGTERM
kill -SIGTERM <PID>
```
- [ ] Bot 优雅关闭
- [ ] 数据库连接关闭
- [ ] 日志记录关闭信息

---

## 📊 测试报告模板

```markdown
# ArchiveBot 测试报告

**测试日期**: YYYY-MM-DD
**测试人员**: [Your Name]
**版本**: MVP v1.0

## 测试环境
- 操作系统: [Windows/Linux/Mac]
- Python 版本: [3.9/3.10/3.11]
- Bot Token: [配置]
- Owner ID: [配置]

## 测试结果

| 测试项 | 状态 | 备注 |
|--------|------|------|
| Bot 启动 | ✅/❌ | |
| 身份验证 | ✅/❌ | |
| /start 命令 | ✅/❌ | |
| /help 命令 | ✅/❌ | |
| /stats 命令 | ✅/❌ | |
| /tags 命令 | ✅/❌ | |
| /language 命令 | ✅/❌ | |
| 文本归档 | ✅/❌ | |
| 图片归档 | ✅/❌ | |
| 文档归档 | ✅/❌ | |
| 标签系统 | ✅/❌ | |
| 搜索功能 | ✅/❌ | |
| 多语言 | ✅/❌ | |
| 存储策略 | ✅/❌ | |
| 数据库 | ✅/❌ | |
| 错误处理 | ✅/❌ | |
| 安全性 | ✅/❌ | |
| 性能 | ✅/❌ | |

## 发现的问题
1. [描述问题]
2. [描述问题]

## 建议改进
1. [建议]
2. [建议]

## 总体评价
- 功能完整性: [优秀/良好/一般/较差]
- 稳定性: [优秀/良好/一般/较差]
- 性能: [优秀/良好/一般/较差]
- 安全性: [优秀/良好/一般/较差]

## 结论
[通过/不通过]
```

---

## 🎯 快速测试脚本

创建 `test_bot.py`:

```python
"""
Quick test script for ArchiveBot
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import get_config
from src.models.database import init_database
from src.storage.database import DatabaseStorage
from src.core.tag_manager import TagManager


async def test_basic():
    """Test basic functionality"""
    print("🧪 Testing ArchiveBot...")
    
    # Test 1: Config
    print("\n1️⃣ Testing config...")
    try:
        config = get_config()
        print(f"   ✅ Config loaded: {config.bot_token[:10]}...")
    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return False
    
    # Test 2: Database
    print("\n2️⃣ Testing database...")
    try:
        db = init_database('data/test.db')
        stats = db.get_stats()
        print(f"   ✅ Database initialized: {stats}")
        db.close()
    except Exception as e:
        print(f"   ❌ Database failed: {e}")
        return False
    
    # Test 3: Storage
    print("\n3️⃣ Testing storage...")
    try:
        db = init_database('data/test.db')
        storage = DatabaseStorage(db)
        # Test create
        archive_id = storage.create_archive(
            content_type='text',
            content='Test message',
            storage_type='database',
            title='Test'
        )
        print(f"   ✅ Created archive: {archive_id}")
        
        # Test search
        results = storage.search_archives('Test')
        print(f"   ✅ Search results: {len(results)}")
        
        db.close()
    except Exception as e:
        print(f"   ❌ Storage failed: {e}")
        return False
    
    # Test 4: Tags
    print("\n4️⃣ Testing tags...")
    try:
        db = init_database('data/test.db')
        storage = DatabaseStorage(db)
        tag_manager = TagManager(storage)
        
        tags = tag_manager.extract_tags('Hello #test #python world', 'text')
        print(f"   ✅ Extracted tags: {tags}")
        
        db.close()
    except Exception as e:
        print(f"   ❌ Tags failed: {e}")
        return False
    
    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic())
    sys.exit(0 if success else 1)
```

运行测试:
```bash
python test_bot.py
```

---

## ✅ 测试完成标准

所有测试项目通过后，MVP 第一阶段即可认为测试完成，可以投入使用。

**建议测试顺序**:
1. 基本功能测试（启动、命令、归档）
2. 高级功能测试（搜索、标签、多语言）
3. 安全性测试
4. 性能测试
5. 压力测试

**最小测试集**（快速验证）:
- Bot 启动 ✅
- /start 命令 ✅
- 文本归档 ✅
- 搜索功能 ✅
- 多语言切换 ✅
