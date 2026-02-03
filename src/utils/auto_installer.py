"""
自动安装模块 - 用于自动安装 playwright 等依赖
Auto-installer module for playwright and other dependencies
"""

import logging
import asyncio
import sys
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def auto_install_playwright(progress_callback=None) -> Tuple[bool, str]:
    """
    自动安装 playwright 依赖
    
    Args:
        progress_callback: 进度回调函数，接收 (step, message) 参数
        
    Returns:
        (是否成功, 结果消息)
    """
    try:
        # 步骤 1: 安装 playwright 包
        if progress_callback:
            await progress_callback(1, "🔄 正在安装 Playwright 包...")
        
        logger.info("Starting playwright package installation")
        
        # 使用 pip 安装 playwright
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'install', 'playwright',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)  # 5分钟超时
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            logger.error(f"Playwright package installation failed: {error_msg}")
            # 给用户显示简短错误，完整错误记录到日志
            error_summary = error_msg.split('\n')[-1] if error_msg else "未知错误"
            return False, f"安装 Playwright 包失败：{error_summary[:200]}"
        
        logger.info("Playwright package installed successfully")
        
        # 步骤 2: 下载浏览器二进制文件
        if progress_callback:
            await progress_callback(2, "🔄 正在下载 Chromium 浏览器...")
        
        logger.info("Starting Chromium browser download")
        
        # 安装 Chromium 浏览器
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'playwright', 'install', 'chromium',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)  # 10分钟超时
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            logger.error(f"Chromium browser installation failed: {error_msg}")
            # 给用户显示简短错误，完整错误记录到日志
            error_summary = error_msg.split('\n')[-1] if error_msg else "未知错误"
            return False, f"下载 Chromium 浏览器失败：{error_summary[:200]}"
        
        logger.info("Chromium browser installed successfully")
        
        # 步骤 3: 验证安装
        if progress_callback:
            await progress_callback(3, "🔄 验证安装结果...")
        
        logger.info("Verifying playwright installation")
        
        # 验证安装是否成功
        try:
            # 重新导入以确保使用新安装的版本
            import importlib
            if 'playwright' in sys.modules:
                importlib.reload(sys.modules['playwright'])
            
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                p.chromium.executable_path
            
            logger.info("Playwright installation verified successfully")
            
            if progress_callback:
                await progress_callback(4, "✅ 安装完成！")
            
            return True, "✅ Playwright 安装成功！\n\n请使用 /restart 命令重启 Bot 以加载新依赖。"
            
        except Exception as e:
            logger.error(f"Playwright verification failed: {e}")
            return False, f"安装验证失败：{str(e)}"
    
    except asyncio.TimeoutError:
        logger.error("Playwright installation timeout")
        return False, "安装超时，请检查网络连接后重试"
    
    except Exception as e:
        logger.error(f"Unexpected error during playwright installation: {e}", exc_info=True)
        return False, f"安装过程发生错误：{str(e)}"


async def check_install_permissions() -> bool:
    """
    检查是否有安装权限（例如：在容器环境中可能没有）
    
    Returns:
        是否有安装权限
    """
    try:
        # 尝试运行一个简单的 pip 命令来检查权限
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await asyncio.wait_for(process.communicate(), timeout=10)
        return process.returncode == 0
    
    except Exception:
        return False


def get_manual_install_instructions() -> str:
    """
    获取手动安装说明
    
    Returns:
        手动安装指令文本
    """
    return (
        "📋 <b>手动安装指南</b>\n\n"
        "如果自动安装失败，请手动执行以下命令：\n\n"
        "<b>1. 安装 Playwright 包：</b>\n"
        "<code>pip install playwright</code>\n\n"
        "<b>2. 下载浏览器：</b>\n"
        "<code>python -m playwright install chromium</code>\n\n"
        "<b>3. 重启 Bot：</b>\n"
        "使用 /restart 命令\n\n"
        "详细文档：BROWSER_STRATEGY.md"
    )
