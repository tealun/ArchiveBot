#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步私密仓库到公开仓库的脚本
将开发分支的所有提交压缩为一个提交推送到公开仓库
"""

import subprocess
import sys
from datetime import datetime


def run_command(cmd, cwd=None, check=True):
    """执行shell命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if check and result.returncode != 0:
        print(f"命令执行失败: {cmd}")
        sys.exit(1)
    
    return result


def get_current_branch():
    """获取当前分支名"""
    result = run_command("git branch --show-current")
    return result.stdout.strip()


def check_public_repo_exists():
    """检查公开仓库是否已有提交"""
    result = run_command("git ls-remote --heads public-origin main", check=False)
    return bool(result.stdout.strip())


def init_public_repo():
    """初始化公开仓库（清空历史，创建全新初始提交）"""
    print("\n" + "=" * 60)
    print("初始化公开仓库（清空历史）")
    print("=" * 60)
    
    # 获取版本信息
    version_info = run_command("git describe --tags --always")
    commit_hash = version_info.stdout.strip()
    
    # 生成提交消息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Initial Release: {timestamp} ({commit_hash})"
    
    # 创建孤儿分支（无历史记录）
    temp_branch = f"orphan-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"\n创建孤儿分支: {temp_branch}")
    run_command(f"git checkout --orphan {temp_branch}")
    
    # 添加所有文件（排除.github目录）
    print("\n添加所有文件（排除.github目录）...")
    run_command("git add -A")
    run_command("git reset -- .github", check=False)  # 移除.github目录
    
    # 创建初始提交
    print(f"\n创建初始提交: {commit_msg}")
    run_command(f'git commit -m "{commit_msg}"')
    
    # 强制推送到公开仓库
    print("\n强制推送到公开仓库...")
    run_command("git push public-origin HEAD:main --force")
    
    # 切回main分支并删除临时分支
    print("\n清理临时分支...")
    run_command("git checkout main")
    run_command(f"git branch -D {temp_branch}")
    
    print("\n" + "=" * 60)
    print("✓ 公开仓库初始化完成！")
    print("=" * 60)


def sync_to_public():
    """同步到公开仓库"""
    print("=" * 60)
    print("开始同步到公开仓库")
    print("=" * 60)
    
    # 1. 确保在main分支
    current_branch = get_current_branch()
    if current_branch != 'main':
        print(f"当前分支: {current_branch}")
        confirm = input("不在main分支，是否切换到main分支？(y/n): ")
        if confirm.lower() == 'y':
            run_command("git checkout main")
        else:
            print("已取消同步")
            return
    
    # 2. 确认工作目录干净
    status = run_command("git status --porcelain")
    if status.stdout.strip():
        print("工作目录有未提交的更改:")
        print(status.stdout)
        print("请先提交或暂存更改")
        return
    
    # 3. 拉取最新代码
    print("\n拉取私密仓库最新代码...")
    run_command("git pull origin main")
    
    # 4. 检查是否需要初始化公开仓库
    if not check_public_repo_exists():
        print("\n检测到公开仓库未初始化或为空")
        confirm = input("是否初始化公开仓库（清空历史）？(y/n): ")
        if confirm.lower() == 'y':
            init_public_repo()
            return
        else:
            print("已取消同步")
            return
    
    # 5. 获取版本信息
    version_info = run_command("git describe --tags --always")
    commit_hash = version_info.stdout.strip()
    
    # 6. 生成提交消息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Release: {timestamp} ({commit_hash})"
    
    print(f"\n提交信息: {commit_msg}")
    confirm = input("是否继续同步到公开仓库？(y/n): ")
    if confirm.lower() != 'y':
        print("已取消同步")
        return
    
    # 7. 获取公开仓库当前状态
    print("\n获取公开仓库状态...")
    run_command("git fetch public-origin main")
    
    # 8. 创建临时分支
    temp_branch = f"temp-sync-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"\n创建临时分支: {temp_branch}")
    run_command(f"git checkout -b {temp_branch} public-origin/main")
    
    # 9. 合并当前main分支的所有更改（squash方式）
    print("\n合并更改（排除.github目录）...")
    run_command("git merge main --squash --allow-unrelated-histories")
    # 移除.github目录（如果存在）
    run_command("git reset -- .github", check=False)
    run_command("git rm -rf --cached .github", check=False)
    
    # 10. 提交
    run_command(f'git commit -m "{commit_msg}"')
    
    # 11. 推送到公开仓库
    print("\n推送到公开仓库...")
    run_command("git push public-origin HEAD:main")
    
    # 12. 切回main分支并删除临时分支
    print("\n清理临时分支...")
    run_command("git checkout main")
    run_command(f"git branch -D {temp_branch}")
    
    print("\n" + "=" * 60)
    print("✓ 同步完成！")
    print("=" * 60)
    print(f"公开仓库已更新: https://github.com/tealun/ArchiveBot")
    print(f"私密仓库: https://github.com/tealun/ArchiveBot-dev")


if __name__ == "__main__":
    try:
        # 检查是否有--init参数强制初始化
        if len(sys.argv) > 1 and sys.argv[1] == '--init':
            print("强制初始化模式")
            # 确保在main分支
            current_branch = get_current_branch()
            if current_branch != 'main':
                run_command("git checkout main")
            # 确认工作目录干净
            status = run_command("git status --porcelain")
            if status.stdout.strip():
                print("工作目录有未提交的更改，请先提交")
                sys.exit(1)
            # 拉取最新代码
            run_command("git pull origin main")
            # 执行初始化
            init_public_repo()
        else:
            sync_to_public()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)
