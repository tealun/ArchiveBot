"""
Note refine handler
处理笔记精炼功能
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.helpers import truncate_text

logger = logging.getLogger(__name__)


async def handle_note_refine(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> bool:
    """
    处理笔记精炼指令
    
    Returns:
        bool: 如果处理了精炼请求返回True，否则返回False
    """
    refine_context = context.user_data.get('refine_note_context')
    if not refine_context or not refine_context.get('waiting_for_instruction'):
        return False
    
    message = update.message
    if not message.text:
        return True  # 处理了但没有文本
    
    instruction = message.text.strip()
    archive_id = refine_context['archive_id']
    notes = refine_context['notes']
    
    # 组合所有笔记内容
    notes_text = "\n\n".join([note['content'] for note in notes])
    
    # 使用AI精炼笔记
    ai_summarizer = context.bot_data.get('ai_summarizer')
    if ai_summarizer and ai_summarizer.is_available():
        try:
            await message.reply_text(lang_ctx.t('ai_refining_note'))
            
            # 构造提示词
            refine_prompt = f"""请根据用户的指令修改以下笔记：

原始笔记：
{notes_text}

用户指令：{instruction}

请输出修改后的笔记内容，保持简洁清晰。"""
            
            # 调用AI
            refined_content = await ai_summarizer.summarize_content(
                content=refine_prompt,
                content_type='note_refinement',
                max_tokens=500,
                language=lang_ctx.language
            )
            
            if refined_content:
                # 删除旧笔记
                note_manager = context.bot_data.get('note_manager')
                if note_manager:
                    for note in notes:
                        note_manager.delete_note(note['id'])
                    
                    # 添加精炼后的笔记
                    new_note_id = note_manager.add_note(archive_id, refined_content)
                    
                    if new_note_id:
                        await message.reply_text(
                            lang_ctx.t('ai_refine_note_success', archive_id=archive_id, content=truncate_text(refined_content, 300)),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        logger.info(f"Refined notes for archive {archive_id}")
                    else:
                        await message.reply_text(lang_ctx.t('ai_refine_note_save_failed'))
                else:
                    await message.reply_text(lang_ctx.t('note_manager_uninitialized'))
            else:
                await message.reply_text(lang_ctx.t('ai_refine_note_failed'))
                
        except Exception as e:
            logger.error(f"Error refining note: {e}", exc_info=True)
            await message.reply_text(lang_ctx.t('ai_refine_note_error', error=str(e)))
    else:
        await message.reply_text(lang_ctx.t('ai_feature_disabled'))
    
    # 清除等待状态
    context.user_data.pop('refine_note_context', None)
    # 清理其他可能的临时数据
    context.user_data.pop('waiting_note_for_archive', None)
    context.user_data.pop('note_modify_mode', None)
    context.user_data.pop('note_id_to_modify', None)
    context.user_data.pop('note_append_mode', None)
    context.user_data.pop('note_id_to_append', None)
    
    return True
