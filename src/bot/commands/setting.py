"""
Setting command - 配置管理命令
允许用户通过交互界面修改非敏感配置项
"""

from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.config import get_config
from ...utils.language_context import with_language_context
from .note_mode_interceptor import intercept_in_note_mode
from ...utils.helpers import send_or_update_reply

logger = logging.getLogger(__name__)


# 配置项定义：分类 -> 配置项列表
CONFIG_CATEGORIES = {
    'features': {
        'name': '功能开关',
        'icon': '🎛️',
        'items': {
            'features.auto_tag': {
                'name': '自动标签',
                'type': 'bool',
                'description': '自动生成类型标签'
            },
            'features.auto_file_type_tag': {
                'name': '文件类型标签',
                'type': 'bool',
                'description': '自动生成文件类型标签（如#图片、#视频等）'
            },
            'features.extract_tags_from_caption': {
                'name': '提取Caption标签',
                'type': 'bool',
                'description': '从转发消息caption中提取#标签'
            }
        }
    },
    'ai': {
        'name': 'AI设置',
        'icon': '🤖',
        'items': {
            'ai.enabled': {
                'name': 'AI功能',
                'type': 'bool',
                'description': '启用AI智能分析功能'
            },
            'ai.auto_summarize': {
                'name': '自动摘要',
                'type': 'bool',
                'description': '自动总结新归档内容'
            },
            'ai.auto_generate_tags': {
                'name': 'AI自动标签',
                'type': 'bool',
                'description': '自动生成AI标签'
            },
            'ai.max_generated_tags': {
                'name': 'AI标签数量',
                'type': 'int',
                'description': 'AI自动生成标签的最大数量（5-10为佳）',
                'min': 3,
                'max': 15,
                'default': 8
            },
            'ai.cache_enabled': {
                'name': 'AI缓存',
                'type': 'bool',
                'description': '启用AI响应缓存以避免重复调用'
            },
            'ai.chat_enabled': {
                'name': 'AI聊天模式',
                'type': 'bool',
                'description': '启用短消息自动AI聊天模式'
            },
            'ai.chat_session_ttl_seconds': {
                'name': '会话超时时间',
                'type': 'int',
                'description': '会话超时时间（秒），默认600秒（10分钟）',
                'min': 60,
                'max': 3600,
                'default': 600
            },
            'ai.text_thresholds.short_text': {
                'name': '短文本阈值',
                'type': 'int',
                'description': '短文本判断阈值（触发AI对话）',
                'min': 20,
                'max': 200,
                'default': 50
            }
        }
    },
    'storage': {
        'name': '存储设置',
        'icon': '💾',
        'items': {
            'storage.backup.auto_interval_hours': {
                'name': '自动备份间隔',
                'type': 'int',
                'description': '自动备份间隔（小时），默认168小时（7天）',
                'min': 1,
                'max': 720,
                'default': 168
            },
            'storage.backup.keep_count': {
                'name': '备份保留数量',
                'type': 'int',
                'description': '保留备份数量，默认保留最近10个',
                'min': 1,
                'max': 50,
                'default': 10
            }
        }
    },
    'review': {
        'name': '回顾设置',
        'icon': '🎲',
        'items': {
            'review.random_count': {
                'name': '随机回顾数量',
                'type': 'int',
                'description': '随机回顾命令默认返回的存档数量',
                'min': 1,
                'max': 10,
                'default': 3
            }
        }
    },
    'web_archiver': {
        'name': '网页存档',
        'icon': '🌐',
        'items': {
            'web_archiver.enabled': {
                'name': '智能链接存档',
                'type': 'bool',
                'description': '启用智能网页抓取、正文提取和PDF生成'
            },
            'web_archiver.strategies.http.enabled': {
                'name': 'HTTP抓取',
                'type': 'bool',
                'description': '启用HTTP直接抓取（快速但可能被反爬）'
            },
            'web_archiver.strategies.http.timeout': {
                'name': 'HTTP超时时间',
                'type': 'int',
                'description': 'HTTP抓取超时时间（秒）',
                'min': 10,
                'max': 120,
                'default': 30
            },
            'web_archiver.pdf_generation.enabled': {
                'name': 'PDF生成',
                'type': 'bool',
                'description': '将网页内容生成PDF存档'
            },
            'web_archiver.quality.min_score_for_pdf': {
                'name': 'PDF质量阈值',
                'type': 'float',
                'description': '只有质量分数达到此值才生成PDF（0.0-1.0）',
                'min': 0.1,
                'max': 1.0,
                'default': 0.5,
                'step': 0.1
            },
            'web_archiver.quality.min_score_for_ai': {
                'name': 'AI摘要阈值',
                'type': 'float',
                'description': '只有质量分数达到此值才进行AI摘要（0.0-1.0）',
                'min': 0.1,
                'max': 1.0,
                'default': 0.3,
                'step': 0.1
            }
        }
    }
}


@intercept_in_note_mode
@with_language_context
async def setting_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /setting or /set command - 显示配置分类菜单
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 构建分类选择菜单
        keyboard = []
        for category_key, category_info in CONFIG_CATEGORIES.items():
            icon = category_info['icon']
            name = category_info['name']
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} {name}",
                    callback_data=f"setting_cat:{category_key}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_or_update_reply(
            update,
            context,
            "⚙️ <b>系统配置</b>\n\n"
            "请选择要配置的分类：",
            'setting',
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        logger.info(f"Setting command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in setting_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, f"❌ 发生错误：{str(e)}", 'setting')


def get_config_item_info(config_key: str) -> dict:
    """
    获取配置项信息
    
    Args:
        config_key: 配置键（如 'ai.enabled'）
        
    Returns:
        配置项信息字典，如果找不到返回None
    """
    for category_key, category_info in CONFIG_CATEGORIES.items():
        if config_key in category_info['items']:
            return category_info['items'][config_key]
    return None


def get_current_value(config_key: str):
    """
    获取配置项的当前值
    
    Args:
        config_key: 配置键（如 'ai.enabled'）
        
    Returns:
        当前配置值
    """
    config = get_config()
    return config.get(config_key)


def validate_config_value(config_key: str, value: str) -> tuple[bool, any, str]:
    """
    验证配置值
    
    Args:
        config_key: 配置键
        value: 用户输入的值（字符串）
        
    Returns:
        (是否有效, 转换后的值, 错误消息)
    """
    item_info = get_config_item_info(config_key)
    if not item_info:
        return False, None, "配置项不存在"
    
    value_type = item_info['type']
    
    try:
        if value_type == 'bool':
            # 布尔值：true/false, yes/no, 1/0, 开/关, 启用/禁用
            value_lower = value.lower().strip()
            if value_lower in ['true', 'yes', '1', '开', '启用', 'on', 'enable', 'enabled']:
                return True, True, ""
            elif value_lower in ['false', 'no', '0', '关', '禁用', 'off', 'disable', 'disabled']:
                return True, False, ""
            else:
                return False, None, "请输入：true/false, yes/no, 1/0, 开/关"
        
        elif value_type == 'int':
            # 整数值：检查范围
            int_value = int(value)
            min_val = item_info.get('min')
            max_val = item_info.get('max')
            
            if min_val is not None and int_value < min_val:
                return False, None, f"值不能小于 {min_val}"
            if max_val is not None and int_value > max_val:
                return False, None, f"值不能大于 {max_val}"
            
            return True, int_value, ""
        
        elif value_type == 'string':
            # 字符串值：去除首尾空格
            str_value = value.strip()
            if not str_value:
                return False, None, "值不能为空"
            return True, str_value, ""
        
        elif value_type == 'choice':
            # 选择值：必须在choices列表中
            choices = item_info.get('choices', [])
            value_upper = value.upper().strip()
            if value_upper in choices:
                return True, value_upper, ""
            else:
                return False, None, f"请选择：{', '.join(choices)}"
        
        else:
            return False, None, f"不支持的配置类型：{value_type}"
    
    except ValueError as e:
        return False, None, f"值格式错误：{str(e)}"
    except Exception as e:
        return False, None, f"验证失败：{str(e)}"
