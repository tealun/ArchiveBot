"""
AI Chat Router

Handles AI interactive chat mode with Function Calling:
1. AI understands intent and decides which functions to call
2. System executes requested functions
3. AI generates response based on function results

Uses language context for multi-language support.
"""
from __future__ import annotations

import logging
import re
import json
import httpx
from typing import Optional, Dict, Any, List

from .prompts.chat import ChatPrompts
from .functions import get_function_registry
from ..utils.config import get_config

logger = logging.getLogger(__name__)


async def handle_chat_message_with_functions(
    user_message: str,
    session_data: Dict[str, Any],
    context: Any,
    language: str = 'auto',
    progress_callback=None,
    message: Any = None
) -> str:
    """
    Handle message using Function Calling (New Architecture)
    
    Flow:
    1. AI understands intent and requests functions
    2. System executes functions and returns structured results
    3. AI generates response based on function results
    
    Args:
        user_message: User's message text
        session_data: Current session context
        context: Bot context
        language: User's language preference
        progress_callback: Optional callback for progress updates
        message: Telegram message object (for sending resources)
        
    Returns:
        AI response text
    """
    from ..utils.i18n import I18n
    from ..utils.language_context import DEFAULT_LANGUAGE
    
    i18n = I18n(language if language != 'auto' else DEFAULT_LANGUAGE)
    
    # Simple commands
    text_lower = user_message.lower().strip()
    if text_lower in ['退出', '結束', '结束', 'exit', 'quit', 'bye', '再见', '再見']:
        actual_lang = language if language != 'auto' else DEFAULT_LANGUAGE
        return handle_exit(actual_lang)
    if text_lower in ['帮助', '幫助', 'help', '?', '？']:
        actual_lang = language if language != 'auto' else DEFAULT_LANGUAGE
        return handle_help(actual_lang)
    
    try:
        config = get_config()
        api_key = config.get('ai.api.api_key') or config.ai.get('api', {}).get('api_key')
        api_url = config.get('ai.api.api_url') or config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        model = config.get('ai.api.model') or 'grok-4-1-fast-non-reasoning'
        temperature = config.get('ai.api.temperature', 0.7)
        
        # Get function registry
        registry = get_function_registry()
        tools = registry.get_openai_tools()
        
        # Stage 1: AI decides which functions to call
        logger.info(f"🧠 Stage 1: AI analyzing intent with {len(tools)} available functions...")
        if progress_callback:
            await progress_callback(i18n.t('ai_chat_understanding'))
        
        # Build initial prompt
        system_prompt = ChatPrompts.get_function_calling_system_prompt(language)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Call AI with tools
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": temperature
                }
            )
            
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return i18n.t('ai_chat_error')
            
            result = response.json()
            assistant_message = result['choices'][0]['message']
            
            # Check if AI wants to call functions
            tool_calls = assistant_message.get('tool_calls', [])
            
            if not tool_calls:
                # No function calls, direct response
                content = assistant_message.get('content', '')
                if content:
                    logger.info("✓ AI generated direct response (no function calls)")
                    return content
                else:
                    logger.warning("No tool calls and no content")
                    return i18n.t('ai_chat_error')
            
            # Stage 2: Execute requested functions
            logger.info(f"⚙️ Stage 2: Executing {len(tool_calls)} function(s)...")
            if progress_callback:
                await progress_callback(i18n.t('ai_chat_gathering'))
            
            function_results = []
            for tool_call in tool_calls:
                func_name = tool_call['function']['name']
                func_args_str = tool_call['function']['arguments']
                
                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}
                
                logger.info(f"  → Calling: {func_name}({func_args})")
                
                # Execute function
                result = await registry.execute(func_name, func_args, context)
                
                function_results.append({
                    'tool_call_id': tool_call['id'],
                    'role': 'tool',
                    'name': func_name,
                    'content': json.dumps(result, ensure_ascii=False)
                })
                
                logger.info(f"  ✓ Result: {result}")
            
            # Stage 2.5: Check if we can directly format structured data
            # Instead of letting AI describe it, use message builder for actual content
            direct_response, should_send_resource = await _try_format_structured_response(
                tool_calls[0] if len(tool_calls) == 1 else None,
                function_results,
                context,
                language,
                message
            )
            
            if direct_response:
                logger.info("✓ Returning directly formatted structured response")
                return direct_response
            
            # If should_send_resource is True, resource was sent directly, return success marker
            if should_send_resource:
                logger.info("✓ Resource sent directly to user")
                return "__RESOURCE_SENT__"
            
            # Stage 3: AI generates response based on function results
            logger.info(f"💬 Stage 3: AI generating response based on function results...")
            if progress_callback:
                await progress_callback(i18n.t('ai_chat_generating'))
            
            # Add assistant message and function results to conversation
            messages.append(assistant_message)
            messages.extend(function_results)
            
            # Call AI again for final response
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    return i18n.t('ai_chat_error')
                
                result = response.json()
                final_response = result['choices'][0]['message']['content']
                
                logger.info(f"✓ AI generated final response: {final_response[:100]}...")
                return final_response
    
    except Exception as e:
        logger.error(f"Function calling error: {e}", exc_info=True)
        return i18n.t('ai_chat_error')


# Alias for backward compatibility
handle_chat_message = handle_chat_message_with_functions


async def _try_format_structured_response(
    tool_call: Optional[Dict[str, Any]],
    function_results: List[Dict[str, Any]],
    context: Any,
    language: str,
    message: Any = None
) -> tuple[Optional[str], bool]:
    """
    Try to format structured data directly instead of AI description
    
    Returns:
        (formatted_message, resource_sent): 
            - formatted_message: Text message if can be displayed as text
            - resource_sent: True if actual resource file was sent
    """
    if not tool_call or not function_results:
        return None, False
    
    try:
        # Parse function result
        result_data = json.loads(function_results[0]['content'])
        logger.debug(f"Checking structured response for data: {list(result_data.keys())}")
        
        # Check if it's an execute_command result
        if result_data.get('command') or result_data.get('operation_type'):
            operation_type = result_data.get('operation_type', result_data.get('command'))
            data = result_data.get('data', {})
            logger.info(f"Detected execute_command operation: {operation_type}")
            
            # Handle different operation types
            if operation_type == 'search':
                response, sent = await _format_search_results(data, context, language, message)
                return response, sent
            elif operation_type == 'notes':
                response = await _format_notes_results(data, context, language)
                return response, False
            elif operation_type == 'tags':
                response = _format_tags_results(data, context, language)
                return response, False
            elif operation_type == 'review':
                logger.info(f"Detected review operation, data type: {data.get('type')}")
                if data.get('type') == 'random':
                    # Check if multiple archives or single archive
                    if 'archives' in data:
                        # Multiple random archives - show list
                        archives = data.get('archives', [])
                        logger.info(f"Detected review random with {len(archives)} archives, showing list")
                        response, sent = await _format_archives_list(archives, context, language, message)
                        return response, sent
                    elif 'archive' in data:
                        # Single random archive - send actual resource
                        logger.info("Detected review random operation, sending single resource")
                        archive = data.get('archive')
                        logger.info(f"Archive data present: {archive is not None}, keys: {list(archive.keys()) if archive else 'None'}")
                        result = await _format_single_archive(archive, context, language, message)
                        logger.info(f"_format_single_archive returned: {result}")
                        return result
                else:
                    logger.info(f"Review operation type '{data.get('type')}' not handled, skipping")
        
        # Check for direct data structures
        if 'archives' in result_data or 'results' in result_data:
            archives = result_data.get('archives') or result_data.get('results', [])
            if archives:
                logger.info(f"Detected direct archives/results structure with {len(archives)} items")
                response, sent = await _format_archives_list(archives, context, language, message)
                return response, sent
        
        if 'notes' in result_data:
            response = await _format_notes_results(result_data, context, language)
            return response, False
        
        if 'tags' in result_data:
            response = _format_tags_results(result_data, context, language)
            return response, False
        
    except Exception as e:
        logger.error(f"Error in _try_format_structured_response: {e}", exc_info=True)
    
    return None, False


async def _format_search_results(data: Dict[str, Any], context: Any, language: str, message: Any = None) -> tuple[Optional[str], bool]:
    """Format search results using message builder"""
    from ..utils.message_builder import MessageBuilder
    from ..utils.i18n import I18n
    
    results = data.get('results', [])
    keyword = data.get('keyword', '')
    
    if not results:
        i18n = I18n(language)
        return i18n.t('search_no_results', keyword=keyword), False
    
    if len(results) == 1:
        # Single result - send actual resource
        return await _format_single_archive(results[0], context, language, message)
    else:
        # Multiple results - show list
        return await _format_archives_list(results, context, language, message)


async def _format_archives_list(archives: List[Dict[str, Any]], context: Any, language: str, message: Any = None) -> tuple[str, bool]:
    """Format archives list using message builder"""
    from ..utils.message_builder import MessageBuilder
    from ..utils.i18n import I18n
    
    i18n = I18n(language)
    db_storage = context.bot_data.get('db_storage')
    
    # Ensure archives have tags field
    for archive in archives:
        if 'tags' not in archive and db_storage:
            archive['tags'] = db_storage.get_archive_tags(archive.get('id'))
    
    formatted_list = MessageBuilder.format_archive_list(
        archives,
        i18n,
        db_instance=db_storage.db if db_storage else None,
        with_links=True
    )
    
    # Add header with count
    header = i18n.t('search_results_header', count=len(archives)) if hasattr(i18n, 't') else f"📚 找到 {len(archives)} 个结果："
    final_text = f"{header}\n\n{formatted_list}"
    
    return final_text, False


async def _format_single_archive(archive: Dict[str, Any], context: Any, language: str, message: Any = None) -> tuple[Optional[str], bool]:
    """Send actual archive resource file to user"""
    if not archive:
        logger.warning("_format_single_archive: archive is None")
        return None, False
    
    from ..utils.message_builder import MessageBuilder
    
    # Get notes for this archive
    note_manager = context.bot_data.get('note_manager')
    notes = []
    if note_manager and archive.get('id'):
        notes = note_manager.get_notes(archive['id'])
    
    # Get bot and chat_id for sending resource
    bot = context.bot if context else None
    chat_id = message.chat_id if message else None
    
    logger.info(f"_format_single_archive: bot={bot is not None}, chat_id={chat_id}, message={message is not None}")
    
    content_type = archive.get('content_type', 'text')
    storage_type = archive.get('storage_type')
    
    logger.info(f"_format_single_archive: content_type={content_type}, storage_type={storage_type}")
    
    # For media types stored in telegram, send actual resource file
    if content_type in ['image', 'photo', 'video', 'audio', 'voice', 'file', 'document', 'ebook'] and storage_type == 'telegram':
        logger.info(f"Attempting to send resource for archive #{archive.get('id')}")
        if bot and chat_id:
            try:
                # Build caption
                caption = MessageBuilder.format_media_archive_caption(archive, notes, max_length=1000)
                
                # Build buttons
                has_notes = notes and len(notes) > 0
                buttons = MessageBuilder.build_media_archive_buttons(archive, has_notes)
                
                # Send actual resource
                sent_message = await MessageBuilder.send_archive_resource(bot, chat_id, archive, caption, buttons)
                
                if sent_message:
                    logger.info(f"✓ Sent archive #{archive.get('id')} resource to chat {chat_id}")
                    return None, True  # Resource sent successfully
                else:
                    logger.warning(f"Failed to send archive #{archive.get('id')} resource, falling back to text")
            except Exception as e:
                logger.error(f"Error sending archive resource: {e}", exc_info=True)
        else:
            logger.warning(f"Cannot send resource: bot={bot is not None}, chat_id={chat_id}")
    else:
        logger.info(f"Not sending resource: content_type={content_type}, storage_type={storage_type}")
    
    # Fallback: return text description
    if content_type == 'text':
        text_msg, _ = MessageBuilder.format_text_archive_reply(archive, notes)
        return text_msg, False
    elif content_type in ['photo', 'video', 'audio', 'file']:
        caption = MessageBuilder.format_media_archive_caption(archive, notes)
        return caption, False
    else:
        text_msg, _ = MessageBuilder.format_other_archive_reply(archive, len(notes) > 0)
        return text_msg, False


async def _format_notes_results(data: Dict[str, Any], context: Any, language: str) -> Optional[str]:
    """Format notes results using message builder"""
    from ..utils.message_builder import MessageBuilder
    from ..utils.i18n import I18n
    
    notes = data.get('notes', [])
    
    if not notes:
        i18n = I18n(language)
        return i18n.t('no_notes_found') if hasattr(i18n, 't') else "No notes found"
    
    if len(notes) == 1:
        # Single note - show full detail
        note = notes[0]
        text, _ = MessageBuilder.format_note_detail_reply(note)
        return text
    else:
        # Multiple notes - show list
        from ..utils.config import get_config
        from ..utils.language_context import LanguageContext
        
        config = get_config()
        lang_ctx = LanguageContext(language, config)
        text, _ = MessageBuilder.format_notes_list(notes, config, lang_ctx)
        return text


def _format_tags_results(data: Dict[str, Any], context: Any, language: str) -> Optional[str]:
    """Format tags results as button matrix (like /tags command)"""
    from ..utils.i18n import I18n
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    tags = data.get('tags', [])
    
    if not tags:
        i18n = I18n(language)
        return i18n.t('tags_empty') if hasattr(i18n, 't') else "No tags yet"
    
    # Build button matrix (3 columns)
    keyboard = []
    row = []
    
    for tag in tags[:30]:  # Limit to 30 tags
        tag_name = tag.get('tag_name') or tag.get('name')
        count = tag.get('count', 0)
        
        if not tag_name:
            continue
        
        button_text = f"#{tag_name} ({count})"
        callback_data = f"tag:{tag_name}:0"
        
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Format as text with markup info (since we can't send buttons directly in text response)
    # This will need to be handled at a higher level to actually send buttons
    i18n = I18n(language)
    header = i18n.t('tags_button_list_header', count=len(tags)) if hasattr(i18n, 't') else f"🏷️ Found {len(tags)} tags"
    
    # Return text representation for now
    # TODO: Need to return structured data that can be sent with buttons
    tags_text = "\n".join([f"#{tag.get('tag_name')} ({tag.get('count', 0)})" for tag in tags[:10]])
    return f"{header}\n\n{tags_text}"


def handle_exit(language: str) -> str:
    """Handle exit intent"""
    from ..utils.i18n import I18n
    i18n = I18n(language)
    return i18n.t('ai_chat_exit')


def handle_help(language: str) -> str:
    """Handle help intent"""
    from ..utils.i18n import I18n
    i18n = I18n(language)
    return i18n.t('ai_chat_help')


def should_trigger_ai_chat(message, context, config) -> tuple[bool, str]:
    """
    判断是否应触发AI对话模式
    复用helpers.py的工具函数
    
    Args:
        message: Telegram消息对象
        context: Bot context
        config: 配置对象
        
    Returns:
        (should_trigger, reason): 是否触发, 原因说明
    """
    from ..utils.helpers import is_url
    
    # AI功能未启用
    ai_config = config.ai
    chat_enabled = bool(ai_config.get('chat_enabled', False))
    if not chat_enabled:
        return False, 'chat_disabled'
    
    # 只处理文本消息且非转发
    if not message.text or message.forward_origin:
        return False, 'not_text_or_forwarded'
    
    # 如果消息属于媒体组（批量消息），不触发AI Chat
    if message.media_group_id:
        return False, 'belongs_to_media_group'
    
    text = message.text.strip()
    
    # 检查是否有其他特殊模式正在进行
    has_other_mode = (
        context.user_data.get('waiting_note_for_archive') or
        context.user_data.get('note_modify_mode') or
        context.user_data.get('note_append_mode') or
        (context.user_data.get('refine_note_context') and 
         context.user_data['refine_note_context'].get('waiting_for_instruction'))
    )
    
    if has_other_mode:
        return False, 'other_mode_active'
    
    # URL检测 - 不触发AI，让其归档
    if is_url(text):
        return False, 'url_detected'
    
    # 获取文本阈值
    text_thresholds = ai_config.get('text_thresholds', {})
    short_text_threshold = int(text_thresholds.get('short_text', 50))
    
    # 自动触发条件：短文本且无媒体
    if (len(text) < short_text_threshold and 
        not message.media_group_id and
        not message.photo and 
        not message.document and 
        not message.video and
        not message.audio):
        return True, 'short_text_auto_trigger'
    
    return False, 'does_not_match_criteria'


def detect_message_intent(text: str, language: str, config, has_active_session: bool) -> Dict[str, Any]:
    """
    检测消息意图（短文本/长文本/连贯性）
    复用helpers.should_create_note
    
    Args:
        text: 消息文本
        language: 用户语言
        config: 配置对象
        has_active_session: 是否有活跃会话
        
    Returns:
        intent字典: {type, threshold, ...}
    """
    from ..utils.helpers import should_create_note
    
    text_thresholds = config.ai.get('text_thresholds', {})
    
    # 如果在AI会话中，检测长文本意图
    if has_active_session:
        # 根据语言选择阈值
        if language in ['zh-CN', 'zh-TW', 'zh-HK', 'zh-MO']:
            threshold = int(text_thresholds.get('note_chinese', 150))
        else:
            threshold = int(text_thresholds.get('note_english', 250))
        
        if len(text) >= threshold:
            return {
                'type': 'long_text_in_session',
                'threshold': threshold,
                'length': len(text),
                'should_prompt': True
            }
    
    # 检查短文本
    is_short, note_type = should_create_note(text)
    
    if is_short:
        short_threshold = int(text_thresholds.get('short_text', 50))
        return {
            'type': 'short_text',
            'note_type': note_type,
            'length': len(text),
            'threshold': short_threshold,
            'should_prompt': len(text) < short_threshold
        }
    
    return {
        'type': 'normal',
        'length': len(text)
    }


async def process_ai_chat(
    message, 
    session_data: Dict[str, Any], 
    context, 
    lang_ctx,
    progress_callback=None
) -> tuple[bool, Optional[str]]:
    """
    统一的AI消息处理流程
    消除重复代码，提供可复用的AI调用
    
    Args:
        message: Telegram消息对象
        session_data: 会话数据
        context: Bot context
        lang_ctx: Language context
        progress_callback: 进度回调函数
        
    Returns:
        (success, response): 处理是否成功, AI响应内容或None
    """
    text = message.text.strip()
    
    try:
        # Stage 1: 理解需求
        if progress_callback:
            await progress_callback(lang_ctx.t('ai_chat_analyzing'))
        
        # 调用AI处理（使用'auto'让AI自动判断回复语言）
        ai_response = await handle_chat_message(
            text, 
            session_data, 
            context, 
            'auto', 
            progress_callback,
            message  # Pass message object for resource sending
        )
        
        logger.info(f"AI chat response generated for user")
        return True, ai_response
        
    except Exception as e:
        logger.error(f"AI chat processing error: {e}", exc_info=True)
        return False, None


def _log_audit_event(
    event_type: str,
    operation: str,
    params: dict,
    context: Any,
    language: str,
    result: str = None
) -> None:
    """
    Log AI operation audit trail (Phase 3)
    
    Args:
        event_type: Event type (forbidden_attempt, write_confirmed, write_cancelled, safe_executed)
        operation: Operation name
        params: Operation parameters
        context: Bot context
        language: Language code
        result: Operation result (success/failure message)
    """
    from datetime import datetime
    import json
    
    audit_log = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'operation': operation,
        'params': params,
        'language': language,
        'result': result
    }
    
    # Log to application logger with special prefix for audit trail
    logger.info(f"[AUDIT] {json.dumps(audit_log, ensure_ascii=False)}")
    
    # Optional: Store to database for persistent audit trail
    # TODO: Implement database audit table if needed
