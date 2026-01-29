# 提示词架构重构方案

## 问题现状

当前提示词硬编码在Python代码中（`src/ai/prompts/*.py`），存在以下问题：

1. **维护困难**：提示词与代码逻辑混在一起，修改提示词需要改Python代码
2. **版本控制差**：提示词修改历史与代码修改混在一起，难以追踪提示词演进
3. **多语言支持混乱**：每种语言一个方法（`_get_understanding_prompt_zh_cn`/`_get_understanding_prompt_zh_tw`/`_get_understanding_prompt_en`），重复代码多
4. **无法热更新**：修改提示词需要重启服务
5. **难以A/B测试**：无法轻松切换不同版本的提示词进行对比测试
6. **职责不清**：提示词管理逻辑分散在各个模块中

## 理想架构设计

### 目录结构
```
src/ai/prompts/
├── templates/                    # 提示词模板文件
│   ├── chat/
│   │   ├── understanding.yaml    # 理解阶段提示词
│   │   ├── generation.yaml       # 生成阶段提示词
│   │   └── api_spec.yaml         # API规范（可独立维护）
│   ├── note/
│   │   ├── create.yaml           # 创建笔记提示词
│   │   └── enhance.yaml          # 增强笔记提示词
│   ├── summarize/
│   │   └── summarize.yaml        # 总结提示词
│   └── title/
│       └── generate.yaml         # 标题生成提示词
├── prompt_manager.py             # 提示词管理器（加载、缓存、版本控制）
├── prompt_builder.py             # 提示词构建器（模板渲染、变量替换）
├── chat.py                       # 保留，但只作为调用入口
├── note.py
├── summarize.py
└── title.py
```

### YAML模板格式示例

**templates/chat/understanding.yaml**:
```yaml
version: "1.0"
type: "understanding"
description: "AI理解用户意图的提示词模板"

# 多语言支持
languages:
  zh-CN:
    system_prompt: |
      你是智能助手规划器。用户有一个归档管理系统（{total}条归档，{tags}个标签）。
      
      用户说："{user_message}"
      
      请理解用户需求并规划回答方式...
    
    intent_definitions:
      pure_chat:
        description: "纯粹闲聊"
        examples:
          - "你好"
          - "今天天气真好"
        markers: ["你好", "早安", "晚安"]
      
      general_query:
        description: "一般性询问"
        examples:
          - "我写了多少笔记"
          - "最近的一条笔记"
        markers: ["多少", "最近", "总共"]
    
    api_spec_ref: "api_spec.yaml"  # 引用API规范文件
  
  zh-TW:
    system_prompt: |
      你是智能助手規劃器。用戶有一個歸檔管理系統（{total}條歸檔，{tags}個標籤）。
      ...
  
  en:
    system_prompt: |
      You are an intelligent assistant planner...

# 默认配置
defaults:
  temperature: 0.4
  max_tokens: 1000

# 变量定义
variables:
  total:
    type: int
    description: "归档总数"
    default: 0
  
  tags:
    type: int
    description: "标签总数"
    default: 0
  
  user_message:
    type: string
    description: "用户消息"
    required: true
```

**templates/chat/api_spec.yaml**:
```yaml
version: "1.0"
description: "系统API规范 - 数据库表结构和参数约束"

database_tables:
  archives:
    description: "存档表"
    fields:
      id:
        type: INTEGER
        primary_key: true
        description: "主键"
      content_type:
        type: TEXT
        nullable: false
        values: ["text", "photo", "video", "audio", "file", "ebook"]
        description: "内容类型"
      title:
        type: TEXT
        nullable: true
        description: "标题"
      # ... 其他字段
  
  notes:
    description: "笔记表"
    fields:
      # ... 字段定义
  
  tags:
    description: "标签表"
    fields:
      # ... 字段定义

api_parameters:
  statistics:
    description: "统计数据字段"
    fields:
      total:
        type: int
        description: "归档总数"
        forbidden_names: ["total_archives", "archive_count"]
      tags:
        type: int
        description: "标签总数"
        forbidden_names: ["total_tags", "tag_count"]
  
  notes_query:
    description: "笔记查询参数"
    fields:
      enabled:
        type: bool
        required: true
      limit:
        type: int
        min: 1
        max: 100
        default: 10
        forbidden_values: [0]
      sort:
        type: string
        values: ["recent", "oldest"]
        default: "recent"
```

### 核心组件设计

#### 1. PromptManager（提示词管理器）

**职责**：
- 加载和缓存提示词模板
- 提供版本管理和回滚
- 支持热更新（文件变化自动重新加载）
- A/B测试支持

```python
class PromptManager:
    """提示词管理器"""
    
    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)
        self.cache = {}  # 提示词缓存
        self.versions = {}  # 版本记录
        self.watcher = None  # 文件监听器（可选）
    
    def load_template(self, template_path: str, language: str) -> dict:
        """加载指定语言的提示词模板"""
        pass
    
    def get_prompt(self, template_name: str, language: str, version: str = "latest") -> dict:
        """获取提示词（带缓存）"""
        pass
    
    def reload_templates(self):
        """重新加载所有模板（热更新）"""
        pass
    
    def get_available_versions(self, template_name: str) -> list:
        """获取模板的可用版本"""
        pass
```

#### 2. PromptBuilder（提示词构建器）

**职责**：
- 渲染提示词模板（变量替换）
- 组装多段提示词（system + user + API spec）
- 验证必填变量
- 格式化输出

```python
class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self, manager: PromptManager):
        self.manager = manager
    
    def build(
        self,
        template_name: str,
        language: str,
        variables: dict,
        include_api_spec: bool = True
    ) -> str:
        """构建完整的提示词"""
        pass
    
    def render_template(self, template: dict, variables: dict) -> str:
        """渲染模板（Jinja2或简单格式化）"""
        pass
    
    def validate_variables(self, template: dict, variables: dict):
        """验证必填变量"""
        pass
    
    def format_output(self, content: str, format_type: str = "markdown") -> str:
        """格式化输出"""
        pass
```

#### 3. 调用方式改造

**现有代码**（硬编码）:
```python
# src/ai/prompts/chat.py
def _get_understanding_prompt_zh_cn(user_message: str, stats: dict) -> str:
    return f"""你是智能助手规划器。用户有一个归档管理系统（{stats['total']}条归档，{stats['tags']}个标签）。
    
    用户说："{user_message}"
    
    ...长长的硬编码提示词..."""
```

**改造后**（模板驱动）:
```python
# src/ai/prompts/chat.py
from .prompt_manager import PromptManager
from .prompt_builder import PromptBuilder

# 初始化（单例）
_manager = PromptManager("src/ai/prompts/templates")
_builder = PromptBuilder(_manager)

def get_understanding_prompt(user_message: str, stats: dict, language: str) -> str:
    """获取理解阶段提示词（多语言支持）"""
    return _builder.build(
        template_name="chat/understanding",
        language=language,
        variables={
            "user_message": user_message,
            "total": stats.get('total', 0),
            "tags": stats.get('tags', 0)
        },
        include_api_spec=True  # 自动包含API规范
    )
```

## 与i18n系统集成

利用现有的i18n系统（`src/utils/i18n.py`）：

```python
from src.utils.i18n import I18n

def get_understanding_prompt(user_message: str, stats: dict, user_id: int) -> str:
    """获取理解阶段提示词（自动识别用户语言）"""
    language = I18n.get_user_language(user_id)
    
    return _builder.build(
        template_name="chat/understanding",
        language=language,
        variables={
            "user_message": user_message,
            "total": stats.get('total', 0),
            "tags": stats.get('tags', 0)
        }
    )
```

## 重构步骤（渐进式）

### 阶段1：基础设施（1-2天）
- [ ] 创建`prompt_manager.py`和`prompt_builder.py`
- [ ] 实现基础的模板加载和渲染
- [ ] 编写单元测试

### 阶段2：迁移API规范（0.5天）
- [ ] 将API规范提取到`templates/chat/api_spec.yaml`
- [ ] 修改三种语言的提示词引用API规范文件
- [ ] 验证功能正常

### 阶段3：迁移chat提示词（1天）
- [ ] 将`chat.py`的理解提示词迁移到`templates/chat/understanding.yaml`
- [ ] 将生成提示词迁移到`templates/chat/generation.yaml`
- [ ] 修改调用代码使用新架构
- [ ] 回归测试

### 阶段4：迁移其他模块（1-2天）
- [ ] 迁移`note.py`提示词
- [ ] 迁移`summarize.py`提示词
- [ ] 迁移`title.py`提示词
- [ ] 全面回归测试

### 阶段5：增强功能（可选，1-2天）
- [ ] 实现热更新（文件监听）
- [ ] 实现版本管理
- [ ] 实现A/B测试框架
- [ ] 添加提示词性能监控

## 优势

### 短期优势
1. **易维护**：提示词集中管理，修改只需编辑YAML文件
2. **多语言清晰**：同一文件内管理所有语言版本，对比和同步更容易
3. **职责分离**：提示词管理从业务逻辑中分离

### 长期优势
1. **版本控制**：可以回滚到任意版本的提示词
2. **A/B测试**：轻松对比不同提示词的效果
3. **热更新**：修改提示词无需重启服务
4. **可扩展**：易于添加新语言、新模块
5. **团队协作**：非开发人员也可以修改提示词

## 注意事项

1. **向后兼容**：重构期间保持现有接口不变，只改内部实现
2. **充分测试**：每个阶段都需要完整的回归测试
3. **性能考虑**：模板加载和渲染要做好缓存，避免频繁IO
4. **错误处理**：YAML解析错误、变量缺失等异常要有完善的错误提示
5. **文档同步**：更新开发文档和贡献指南

## 待讨论问题

1. 是否使用Jinja2模板引擎？还是简单的format格式化？
2. 是否需要提示词版本管理？如何设计版本号规则？
3. 热更新是否必要？如何保证线程安全？
4. A/B测试需要什么样的配置和统计功能？

---

**创建时间**: 2026-01-29  
**创建者**: GitHub Copilot  
**状态**: 待评审  
**优先级**: 中（功能稳定后进行）
