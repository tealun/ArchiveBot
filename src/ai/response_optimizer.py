"""
Response Optimizer - AI响应智能优化器

在AI生成最终回复前，对结果进行智能优化：
1. 空结果智能建议
2. 大量结果筛选提示
3. 相关内容推荐
4. 友好错误提示
"""

import logging
from typing import Dict, List, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class ResponseOptimizer:
    """响应优化器 - 让AI回复更智能、更人性化"""
    
    @staticmethod
    def optimize(
        user_intent: str,
        data_context: Dict[str, Any],
        user_message: str,
        language: str = 'zh-CN'
    ) -> Dict[str, Any]:
        """
        优化数据上下文，添加智能建议
        
        Args:
            user_intent: 用户意图类型
            data_context: 原始数据上下文
            user_message: 用户原始消息
            language: 语言代码
            
        Returns:
            优化后的数据上下文（包含suggestions等）
        """
        optimized = data_context.copy()
        
        # 1. 搜索结果优化
        if user_intent == 'specific_search':
            optimized = ResponseOptimizer._optimize_search_results(
                optimized, user_message, language
            )
        
        # 2. 统计查询优化
        elif user_intent in ['stats_analysis', 'general_query']:
            optimized = ResponseOptimizer._optimize_stats_display(
                optimized, language
            )
        
        # 3. 资源请求优化
        elif user_intent == 'resource_request':
            optimized = ResponseOptimizer._optimize_resource_response(
                optimized, language
            )
        
        return optimized
    
    @staticmethod
    def _optimize_search_results(
        data_context: Dict,
        query: str,
        language: str
    ) -> Dict:
        """优化搜索结果"""
        results = data_context.get('search_results', [])
        
        # 空结果 - 提供智能建议
        if not results:
            data_context['empty_result_suggestions'] = ResponseOptimizer._generate_search_suggestions(
                query, language
            )
            logger.info(f"Added empty result suggestions for query: {query}")
        
        # 结果过多 - 提供筛选建议
        elif len(results) > 15:
            data_context['filter_suggestions'] = ResponseOptimizer._generate_filter_suggestions(
                results, language
            )
            logger.info(f"Added filter suggestions for {len(results)} results")
        
        # 少量结果 - 提供扩展建议
        elif 1 <= len(results) <= 3:
            data_context['expand_suggestions'] = ResponseOptimizer._generate_expand_suggestions(
                query, language
            )
        
        return data_context
    
    @staticmethod
    def _generate_search_suggestions(query: str, language: str) -> str:
        """生成搜索建议（空结果时）"""
        if language == 'en':
            return (
                f"💡 Suggestions:\n"
                f"• Try simpler keywords\n"
                f"• Check for typos\n"
                f"• Use /tags to browse by tags\n"
                f"• Use /stats to see what's in your archive"
            )
        elif language == 'zh-TW':
            return (
                f"💡 建議：\n"
                f"• 試試更簡單的關鍵詞\n"
                f"• 檢查是否有錯別字\n"
                f"• 使用 /tags 瀏覽標籤\n"
                f"• 使用 /stats 查看歸檔概況"
            )
        else:
            return (
                f"💡 建议：\n"
                f"• 试试更简单的关键词\n"
                f"• 检查是否有错别字\n"
                f"• 使用 /tags 浏览标签\n"
                f"• 使用 /stats 查看归档概况"
            )
    
    @staticmethod
    def _generate_filter_suggestions(results: List[Dict], language: str) -> str:
        """生成筛选建议（结果过多时）"""
        # 分析结果中的常见标签
        all_tags = []
        for item in results:
            tags = item.get('tags', [])
            all_tags.extend(tags)
        
        if all_tags:
            tag_counts = Counter(all_tags)
            top_tags = [f"#{tag}" for tag, _ in tag_counts.most_common(3)]
            tag_str = '、'.join(top_tags)
            
            if language == 'en':
                return f"💡 {len(results)} results found. Try filtering by tags: {tag_str}"
            elif language == 'zh-TW':
                return f"💡 找到 {len(results)} 個結果，可以用標籤篩選：{tag_str}"
            else:
                return f"💡 找到 {len(results)} 个结果，可以用标签筛选：{tag_str}"
        else:
            if language == 'en':
                return f"💡 {len(results)} results found. Showing top matches."
            elif language == 'zh-TW':
                return f"💡 找到 {len(results)} 個結果，顯示最相關的。"
            else:
                return f"💡 找到 {len(results)} 个结果，显示最相关的。"
    
    @staticmethod
    def _generate_expand_suggestions(query: str, language: str) -> str:
        """生成扩展建议（少量结果时）"""
        if language == 'en':
            return "💡 Want more? Try broader keywords or check /tags"
        elif language == 'zh-TW':
            return "💡 想要更多？試試更寬泛的關鍵詞或查看 /tags"
        else:
            return "💡 想要更多？试试更宽泛的关键词或查看 /tags"
    
    @staticmethod
    def _optimize_stats_display(data_context: Dict, language: str) -> Dict:
        """优化统计数据展示"""
        stats = data_context.get('statistics', {})
        
        # 空归档提示
        if stats.get('total', 0) == 0 or stats.get('total_archives', 0) == 0:
            if language == 'en':
                data_context['onboarding_hint'] = (
                    "📝 Your archive is empty. Start by forwarding messages or sending content!"
                )
            elif language == 'zh-TW':
                data_context['onboarding_hint'] = (
                    "📝 您的歸檔還是空的。開始轉發訊息或發送內容吧！"
                )
            else:
                data_context['onboarding_hint'] = (
                    "📝 你的归档还是空的。开始转发消息或发送内容吧！"
                )
        
        # 标签数量异常提示
        elif stats.get('tags', 0) == 0 or stats.get('total_tags', 0) == 0:
            if language == 'en':
                data_context['tagging_hint'] = (
                    "💡 Tip: Add hashtags when archiving for better organization!"
                )
            elif language == 'zh-TW':
                data_context['tagging_hint'] = (
                    "💡 提示：歸檔時加上標籤（#hashtag），方便管理！"
                )
            else:
                data_context['tagging_hint'] = (
                    "💡 提示：归档时加上标签（#hashtag），方便管理！"
                )
        
        return data_context
    
    @staticmethod
    def _optimize_resource_response(data_context: Dict, language: str) -> Dict:
        """优化资源响应"""
        resources = data_context.get('resources', [])
        
        # 无资源提示
        if not resources:
            if language == 'en':
                data_context['no_resource_hint'] = (
                    "📭 No matching resources found.\n"
                    "💡 Try: 'show me photos' or 'random video'"
                )
            elif language == 'zh-TW':
                data_context['no_resource_hint'] = (
                    "📭 沒有找到符合條件的資源。\n"
                    "💡 試試：「給我看圖片」或「隨機視頻」"
                )
            else:
                data_context['no_resource_hint'] = (
                    "📭 没有找到符合条件的资源。\n"
                    "💡 试试：「给我看图片」或「随机视频」"
                )
        
        # 单个资源 - 添加"再来一个"提示
        elif len(resources) == 1:
            if language == 'en':
                data_context['next_hint'] = "💬 Say 'another one' for more"
            elif language == 'zh-TW':
                data_context['next_hint'] = "💬 說「再來一個」查看更多"
            else:
                data_context['next_hint'] = "💬 说「再来一个」查看更多"
        
        return data_context
    
    @staticmethod
    def format_optimized_response(
        base_response: str,
        data_context: Dict,
        language: str
    ) -> str:
        """
        将优化建议附加到基础响应后
        
        Args:
            base_response: AI生成的基础回复
            data_context: 包含优化建议的数据上下文
            language: 语言代码
            
        Returns:
            增强后的完整响应
        """
        response_parts = [base_response]
        
        # 添加各种提示
        if 'empty_result_suggestions' in data_context:
            response_parts.append('\n\n' + data_context['empty_result_suggestions'])
        
        if 'filter_suggestions' in data_context:
            response_parts.append('\n' + data_context['filter_suggestions'])
        
        if 'expand_suggestions' in data_context:
            response_parts.append('\n' + data_context['expand_suggestions'])
        
        if 'onboarding_hint' in data_context:
            response_parts.append('\n\n' + data_context['onboarding_hint'])
        
        if 'tagging_hint' in data_context:
            response_parts.append('\n\n' + data_context['tagging_hint'])
        
        if 'no_resource_hint' in data_context:
            response_parts.append('\n\n' + data_context['no_resource_hint'])
        
        if 'next_hint' in data_context:
            response_parts.append('\n' + data_context['next_hint'])
        
        return ''.join(response_parts)
