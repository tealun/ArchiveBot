#!/usr/bin/env python
"""
日志查看工具
Log viewer utility for ArchiveBot
"""

import sys
import os
from pathlib import Path

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def view_logs(lines=50, level=None, follow=False):
    """
    查看日志
    
    Args:
        lines: 显示最后多少行（默认50）
        level: 过滤日志级别（INFO, WARNING, ERROR）
        follow: 是否实时跟踪日志
    """
    log_file = Path("data/bot.log")
    
    if not log_file.exists():
        print("❌ 日志文件不存在")
        return
    
    print(f"📋 ArchiveBot 日志 (最后 {lines} 行)")
    print("=" * 80)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
            # 取最后 N 行
            recent_lines = all_lines[-lines:]
            
            # 过滤日志级别
            if level:
                recent_lines = [line for line in recent_lines if level.upper() in line]
            
            # 显示日志
            for line in recent_lines:
                # 颜色高亮（Windows 支持）
                if 'ERROR' in line:
                    print(f"\033[91m{line}\033[0m", end='')  # 红色
                elif 'WARNING' in line:
                    print(f"\033[93m{line}\033[0m", end='')  # 黄色
                elif 'INFO' in line:
                    print(f"\033[92m{line}\033[0m", end='')  # 绿色
                else:
                    print(line, end='')
        
        # 显示统计
        print("\n" + "=" * 80)
        print(f"📊 统计信息：")
        print(f"   总行数: {len(all_lines)}")
        print(f"   INFO: {sum(1 for line in all_lines if 'INFO' in line)}")
        print(f"   WARNING: {sum(1 for line in all_lines if 'WARNING' in line)}")
        print(f"   ERROR: {sum(1 for line in all_lines if 'ERROR' in line)}")
        
    except Exception as e:
        print(f"❌ 读取日志失败: {e}")


def clear_logs():
    """清空日志文件"""
    log_file = Path("data/bot.log")
    
    if not log_file.exists():
        print("❌ 日志文件不存在")
        return
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")
        print("✅ 日志已清空")
    except Exception as e:
        print(f"❌ 清空日志失败: {e}")


def show_errors_only():
    """只显示错误日志"""
    log_file = Path("data/bot.log")
    
    if not log_file.exists():
        print("❌ 日志文件不存在")
        return
    
    print("🔴 错误日志")
    print("=" * 80)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            error_lines = [line for line in f if 'ERROR' in line or 'Traceback' in line]
            
            if not error_lines:
                print("✅ 没有错误日志")
            else:
                for line in error_lines:
                    print(f"\033[91m{line}\033[0m", end='')
                    
    except Exception as e:
        print(f"❌ 读取日志失败: {e}")


def show_menu():
    """显示菜单"""
    print("\n" + "="*80)
    print("📋 ArchiveBot 日志查看工具")
    print("="*80)
    print("1. 查看最新日志 (50行)")
    print("2. 查看最新日志 (100行)")
    print("3. 查看最新日志 (500行)")
    print("4. 只看错误日志")
    print("5. 只看警告日志")
    print("6. 清空日志文件")
    print("7. 日志统计")
    print("0. 退出")
    print("="*80)


def show_stats():
    """显示日志统计"""
    log_file = Path("data/bot.log")
    
    if not log_file.exists():
        print("❌ 日志文件不存在")
        return
    
    print("\n📊 日志统计")
    print("=" * 80)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        total = len(lines)
        info_count = sum(1 for line in lines if 'INFO' in line)
        warning_count = sum(1 for line in lines if 'WARNING' in line)
        error_count = sum(1 for line in lines if 'ERROR' in line)
        
        print(f"总行数: {total}")
        print(f"INFO:    {info_count:6d} ({info_count/total*100:.1f}%)" if total > 0 else "INFO:    0")
        print(f"WARNING: {warning_count:6d} ({warning_count/total*100:.1f}%)" if total > 0 else "WARNING: 0")
        print(f"ERROR:   {error_count:6d} ({error_count/total*100:.1f}%)" if total > 0 else "ERROR:   0")
        
        # 文件大小
        file_size = log_file.stat().st_size
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024*1024:
            size_str = f"{file_size/1024:.2f} KB"
        else:
            size_str = f"{file_size/(1024*1024):.2f} MB"
        
        print(f"\n文件大小: {size_str}")
        print(f"文件路径: {log_file.absolute()}")
        
    except Exception as e:
        print(f"❌ 统计失败: {e}")


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式
        if sys.argv[1] == 'view':
            lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            view_logs(lines)
        elif sys.argv[1] == 'errors':
            show_errors_only()
        elif sys.argv[1] == 'clear':
            clear_logs()
        elif sys.argv[1] == 'stats':
            show_stats()
        else:
            print("用法: python view_logs.py [view|errors|clear|stats] [行数]")
    else:
        # 交互模式
        while True:
            show_menu()
            choice = input("\n请选择 (0-7): ").strip()
            
            if choice == '0':
                print("👋 再见！")
                break
            elif choice == '1':
                view_logs(50)
            elif choice == '2':
                view_logs(100)
            elif choice == '3':
                view_logs(500)
            elif choice == '4':
                show_errors_only()
            elif choice == '5':
                view_logs(100, level='WARNING')
            elif choice == '6':
                confirm = input("确认清空日志？(y/n): ")
                if confirm.lower() == 'y':
                    clear_logs()
            elif choice == '7':
                show_stats()
            else:
                print("❌ 无效选择")
            
            input("\n按回车继续...")


if __name__ == "__main__":
    main()
