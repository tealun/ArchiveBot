"""
AI Knowledge Base

系统文档知识库，用于AI回答用户关于系统使用的问题
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
# 单例模式：全局缓存知识库实例，避免重复加载
_knowledge_base_instance: Optional['KnowledgeBase'] = None

class KnowledgeBase:
    """系统知识库管理"""
    
    def __init__(self):
        self.knowledge = None
        self._load_knowledge()
    
    def _load_knowledge(self):
        """加载系统文档作为知识库"""
        try:
            project_root = Path(__file__).parent.parent.parent
            
            # 读取README.md
            readme_path = project_root / "README.md"
            readme_content = ""
            if readme_path.exists():
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
            
            # 读取QUICKSTART.md（如果存在）
            quickstart_path = project_root / "docs" / "QUICKSTART.md"
            quickstart_content = ""
            if quickstart_path.exists():
                with open(quickstart_path, 'r', encoding='utf-8') as f:
                    quickstart_content = f.read()
            
            # 提取核心信息（避免token消耗过大）
            self.knowledge = self._extract_key_info(readme_content, quickstart_content)
            
            logger.info(f"Knowledge base loaded: {len(self.knowledge)} chars")
            
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            self.knowledge = ""
    
    def _extract_key_info(self, readme: str, quickstart: str) -> str:
        """提取关键信息，控制token数量"""
        # 提取核心特性、命令列表、常见问题部分
        sections = []
        
        # 从README提取核心特性
        if "核心特性" in readme or "Core Features" in readme:
            start = readme.find("核心特性") if "核心特性" in readme else readme.find("Core Features")
            end = readme.find("##", start + 10) if start > 0 else -1
            if start > 0:
                section = readme[start:end if end > 0 else start + 1000]
                sections.append(section)
        
        # 从README提取命令列表
        if "命令" in readme or "Commands" in readme:
            start = readme.find("基础命令") if "基础命令" in readme else readme.find("Commands")
            end = readme.find("##", start + 10) if start > 0 else -1
            if start > 0:
                section = readme[start:end if end > 0 else start + 1500]
                sections.append(section)
        
        # 添加反馈引导说明
        from ..utils.config import get_config
        config = get_config()
        feedback_url = config.get('bot.feedback_url', 'https://github.com/tealun/ArchiveBot/issues')
        
        feedback_section = f"""

【用户反馈与问题提交】
- 如果用户提出系统bug、功能建议或无法解决的问题
- 应引导用户访问项目Issue页面提交反馈
- 反馈地址：{feedback_url}
- 提醒用户提交时包含：问题描述、复现步骤、系统环境等信息
"""
        sections.append(feedback_section)
        
        # 合并内容并限制长度
        combined = "\n\n".join(sections)
        
        # 限制在3000字符以内（约1000 tokens）
        if len(combined) > 3000:
            combined = combined[:3000] + "\n...[内容已截断]"
        
        return combined
    
    def get_knowledge(self) -> str:
        """获取知识库内容"""
        return self.knowledge or ""
    
    def is_system_related_query(self, user_message: str) -> bool:
        """
        判断用户问题是否与系统使用相关
        
        Args:
            user_message: 用户消息
            
        Returns:
            True表示系统相关问题，需要引入知识库
        """
        # 关键词检测
        system_keywords = [
            # 中文关键词
            "怎么用", "如何使用", "使用方法", "功能", "命令", "帮助",
            "怎么", "如何", "可以", "支持", "有什么",
            "归档", "标签", "搜索", "备份", "导出", "笔记", "AI",
            "问题", "错误", "不能", "无法", "失败",
            "建议", "反馈", "bug", "改进",
            # 英文关键词
            "how to", "how do", "usage", "feature", "command", "help",
            "what", "can I", "support", "archive", "tag", "search",
            "backup", "export", "note", "problem", "error", "issue",
            "suggestion", "feedback"
        ]
        
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in system_keywords)


# 单例模式
_knowledge_base_instance = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = KnowledgeBase()
    return _knowledge_base_instance
