# 链接智能处理功能规划

## ✅ 第一阶段 - 元数据提取（已完成）

### 功能说明
当用户发送链接时，自动提取网页的基本信息：

### 提取的元数据
- ✅ **标题** - 网页 title
- ✅ **描述** - Meta description / OG description
- ✅ **站点名称** - 网站名称
- ✅ **作者** - 文章作者
- ✅ **发布日期** - 发布时间
- ✅ **关键词** - 页面关键词
- ✅ **预览图** - OG image / Twitter Card
- ✅ **内容预览** - 前300字正文
- ✅ **域名** - 网站域名

### 实现方式
1. 使用 `httpx` 异步获取网页
2. 使用 `BeautifulSoup` 解析 HTML
3. 按优先级提取元数据：
   - Open Graph (og:*) 
   - Twitter Card (twitter:*)
   - 标准 HTML meta 标签
   - HTML 标签 (h1, p, etc.)

### 使用示例
```python
from src.utils.link_extractor import extract_link_metadata

# 提取链接元数据
metadata = await extract_link_metadata('https://example.com/article')

print(metadata['title'])        # "文章标题"
print(metadata['description'])  # "文章描述"
print(metadata['image'])        # "https://example.com/image.jpg"
```

### 存储位置
元数据保存在 `metadata` 字段（JSON格式）：
```json
{
  "title": "网页标题",
  "description": "网页描述",
  "image": "预览图URL",
  "site_name": "站点名称",
  "author": "作者",
  "published_date": "2024-01-01",
  "keywords": ["关键词1", "关键词2"],
  "content_preview": "内容预览..."
}
```

---

## 🚀 第二阶段 - AI 智能总结（规划中）

### 功能说明
使用 AI 模型对网页内容进行深度分析和总结。

### 核心功能

#### 1. 智能摘要生成
- 📝 提取文章主要观点
- 🎯 生成关键要点列表
- 📊 识别重要数据和统计
- 💡 提炼核心结论

#### 2. 智能分类和标签
- 🏷️ 自动识别文章主题
- 📂 智能分类（技术/新闻/教程等）
- 🔍 生成相关标签
- 🌐 识别文章语言和领域

#### 3. 内容质量评估
- ⭐ 评估文章质量
- 📈 估计阅读时间
- 🎓 判断内容难度
- 💰 识别是否为广告内容

#### 4. 深度分析
- 📖 提取作者观点
- 🔗 识别引用和参考
- 📌 标记重要段落
- 🗺️ 生成思维导图结构

### 技术方案

#### 方案 A：本地 AI 模型
**优点**：
- ✅ 完全私有，无数据泄露
- ✅ 无 API 成本
- ✅ 可离线使用

**缺点**：
- ❌ 需要较高硬件配置（GPU）
- ❌ 首次启动慢
- ❌ 模型较大（数GB）

**推荐模型**：
- **LLaMA 2 7B** - Meta开源，效果好
- **Mistral 7B** - 轻量高效
- **Qwen 7B** - 中文支持好

**实现方案**：
```python
# 使用 llama-cpp-python
from llama_cpp import Llama

llm = Llama(model_path="./models/llama-2-7b.gguf")
summary = llm("总结以下文章：\n\n{content}")
```

#### 方案 B：云端 AI API
**优点**：
- ✅ 无需本地资源
- ✅ 效果最好
- ✅ 即开即用

**缺点**：
- ❌ 需要 API 费用
- ❌ 需要网络连接
- ❌ 可能有数据隐私问题

**推荐服务**：

1. **OpenAI GPT-4** ⭐ 推荐
   - 效果最好，理解力强
   - 支持中英文
   - 费用：$0.03/1K tokens
   
2. **Anthropic Claude**
   - 安全性高，上下文长
   - 适合长文章
   - 费用：$0.008/1K tokens

3. **智谱 AI (GLM-4)**
   - 国内服务，速度快
   - 中文效果好
   - 费用：¥0.1/1K tokens

4. **阿里云通义千问**
   - 国内服务
   - 性价比高
   - 费用：¥0.008/1K tokens

5. **Cohere**
   - 专注摘要
   - 免费额度大
   - 费用：前100万tokens免费

#### 方案 C：混合方案 ⭐ 最佳实践
- 🔹 简单任务用本地模型（标签、分类）
- 🔹 复杂任务用云端API（深度总结）
- 🔹 可配置选择，灵活切换

### 配置示例

```yaml
# config/config.yaml
ai:
  enabled: true
  
  # 本地模型配置
  local:
    enabled: true
    model_path: "models/llama-2-7b.gguf"
    max_tokens: 500
    
  # 云端 API 配置  
  api:
    provider: "openai"  # openai, claude, zhipu, qwen
    api_key: "your-api-key"
    model: "gpt-4-turbo"
    max_tokens: 1000
    
  # 功能开关
  features:
    auto_summary: true        # 自动摘要
    auto_tagging: true        # 自动标签
    quality_check: false      # 质量评估
    translation: false        # 自动翻译
```

### 使用示例

```python
from src.ai.summarizer import AILinkSummarizer

summarizer = AILinkSummarizer()

# 生成摘要
result = await summarizer.summarize(url, content)

print(result['summary'])      # 文章摘要
print(result['key_points'])   # 关键要点
print(result['tags'])         # 建议标签
print(result['category'])     # 文章分类
```

### 数据存储

在数据库中添加 AI 分析结果：

```sql
ALTER TABLE archives ADD COLUMN ai_summary TEXT;
ALTER TABLE archives ADD COLUMN ai_tags TEXT;
ALTER TABLE archives ADD COLUMN ai_category TEXT;
ALTER TABLE archives ADD COLUMN ai_score REAL;
```

---

## 📊 功能对比

| 功能 | 第一阶段（元数据） | 第二阶段（AI） |
|------|------------------|---------------|
| 标题提取 | ✅ 基础 | ✅ 智能清理 |
| 描述提取 | ✅ Meta标签 | ✅ AI生成 |
| 内容摘要 | ✅ 前300字 | ✅ 智能总结 |
| 标签生成 | ❌ | ✅ AI推荐 |
| 分类识别 | ❌ | ✅ 自动分类 |
| 质量评估 | ❌ | ✅ 智能评分 |
| 翻译功能 | ❌ | ✅ 多语言 |
| 成本 | 免费 | 有成本 |
| 速度 | 快（1-2秒） | 较慢（5-10秒） |

---

## 🎯 开发优先级

### 短期（1-2周）
- [x] **P0** - 基础元数据提取（已完成）
- [ ] **P0** - 元数据展示优化
- [ ] **P1** - 添加超时和重试机制
- [ ] **P1** - 支持更多网站特殊处理

### 中期（1个月）
- [ ] **P0** - 集成 OpenAI API（可选）
- [ ] **P1** - 实现基础摘要功能
- [ ] **P1** - 添加 AI 标签建议
- [ ] **P2** - 支持配置开关

### 长期（2-3个月）
- [ ] **P1** - 本地 AI 模型支持
- [ ] **P2** - 多种 AI 服务支持
- [ ] **P2** - AI 训练和优化
- [ ] **P3** - 自定义 prompt 模板

---

## 💡 使用建议

### 何时使用元数据提取？
- ✅ 所有链接（默认开启）
- ✅ 快速归档
- ✅ 节省成本

### 何时使用 AI 总结？
- ✅ 重要文章、长文
- ✅ 需要深度理解
- ✅ 研究和学习
- ⚠️ 注意 API 成本

### 最佳实践
1. **默认使用元数据** - 快速且免费
2. **手动触发 AI** - 用命令 `/summarize` 触发
3. **设置预算** - 限制 AI API 调用次数
4. **缓存结果** - 避免重复分析

---

## 🔧 技术细节

### 元数据提取流程
```
1. 接收链接
2. 发送HTTP请求（超时10秒）
3. 解析HTML（BeautifulSoup）
4. 按优先级提取元数据
5. 保存到数据库
6. 返回结果
```

### AI 总结流程（规划）
```
1. 获取网页内容
2. 清理HTML标签
3. 提取正文内容
4. 调用AI模型
5. 解析AI响应
6. 保存结果
7. 返回摘要
```

---

## 📝 相关命令（规划）

```bash
# 基础命令
/archive <url>              # 归档链接（自动元数据）
/summarize <archive_id>     # AI总结已归档链接
/summarize <url>            # 直接总结链接

# 高级命令
/summarize <id> --detailed  # 详细总结
/translate <id> zh-CN       # 翻译内容
/tags <id> --ai            # AI推荐标签
```

---

## 🎁 示例输出

### 元数据提取结果
```
✅ 归档成功

📝 类型: 链接
🔗 URL: https://example.com/article
📋 标题: 如何构建个人知识库
📄 描述: 本文介绍了构建个人知识库的方法...
🏢 站点: Example Blog
👤 作者: 张三
📅 发布: 2024-01-15
🏷️ 标签: #链接 #知识管理
💾 存储: 数据库
```

### AI 总结结果（规划）
```
🤖 AI 智能总结

📖 核心观点:
• 个人知识库需要系统化管理
• 使用标签和分类提高检索效率
• 定期回顾和整理很重要

🎯 关键要点:
1. 选择合适的工具
2. 建立标签体系
3. 保持持续更新

🏷️ 建议标签:
#知识管理 #效率工具 #个人成长

📊 文章评分: ⭐⭐⭐⭐ (4/5)
⏱️ 阅读时间: 约8分钟
🎓 难度级别: 中等
```

---

## 📚 参考资源

- [Open Graph Protocol](https://ogp.me/)
- [Twitter Cards](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [LLaMA Model](https://github.com/facebookresearch/llama)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [BeautifulSoup文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

---

**当前状态**: ✅ 元数据提取已实现
**下一步**: 测试和优化元数据提取
**未来计划**: 集成 AI 总结功能
