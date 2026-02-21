#!/usr/bin/env python3
"""
会话编排器
管理 Agent 会话生命周期，协调功能实现和进度追踪
"""

import os
import sys
import subprocess
import json
from datetime import datetime

# 导入共享配置
try:
    from .config import (
        Config, SafeJson, GitHelper,
        validate_feature_id, validate_project_initialized
    )
except ImportError:
    print("警告: 无法导入 config 模块，使用默认配置")
    METADATA_DIR = ".long-run-agent"
    FEATURE_LIST_FILE = os.path.join(METADATA_DIR, "feature_list.json")
    PROGRESS_FILE = os.path.join(METADATA_DIR, "progress.txt")
    SESSION_STATE_FILE = os.path.join(METADATA_DIR, "session_state.json")

    def validate_project_initialized():
        if not os.path.exists(FEATURE_LIST_FILE):
            return False, f"未找到功能清单: {FEATURE_LIST_FILE}"
        return True, "项目已初始化"

    def validate_feature_id(feature_id):
        return feature_id and feature_id.startswith("feature_")


def get_feature_manager():
    """导入 feature_manager 模块"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        return __import__("feature_manager")
    except Exception as e:
        print(f"❌ 无法导入 feature_manager: {str(e)}")
        return None


def get_progress_tracker():
    """导入 progress_tracker 模块"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        return __import__("progress_tracker")
    except Exception as e:
        print(f"❌ 无法导入 progress_tracker: {str(e)}")
        return None


def get_next_task():
    """获取下一个待完成任务"""
    # 验证项目初始化
    ok, msg = validate_project_initialized()
    if not ok:
        print(f"❌ 错误: {msg}")
        print("请先初始化项目: python3 feature_manager.py init")
        return None

    # 导入 feature_manager
    feature_manager = get_feature_manager()
    if not feature_manager:
        return None

    next_feature = feature_manager.get_next_feature()

    if not next_feature:
        print("✅ 所有功能已完成！")
        return None

    print(f"\n📋 下一个任务:\n")
    print(f"  ID: {next_feature['id']}")
    print(f"  描述: {next_feature['description']}")
    print(f"  类别: {next_feature['category']}")
    print(f"  优先级: {next_feature['priority']}")
    print(f"\n  步骤:")
    for i, step in enumerate(next_feature['steps'], 1):
        print(f"    {i}. {step}")

    return next_feature


def start_session():
    """开始新会话"""
    print(f"\n🚀 开始新会话\n")

    # 验证项目初始化
    ok, msg = validate_project_initialized()
    if not ok:
        print(f"❌ 错误: {msg}")
        print("请先初始化项目")
        return None

    # 导入模块
    feature_manager = get_feature_manager()
    progress_tracker = get_progress_tracker()

    if not feature_manager or not progress_tracker:
        return None

    print("📊 项目状态:")
    stats = feature_manager.get_feature_stats()
    if stats:
        print(f"  总功能数: {stats['total']}")
        print(f"  已完成: {stats['completed']}")
        print(f"  待完成: {stats['pending']}")
        print(f"  进度: {stats['progress']:.1f}%")
    print()

    # 获取下一个任务
    next_task = get_next_task()
    if not next_task:
        return None

    # 记录会话开始
    progress_tracker.log(f"开始会话，处理功能: {next_task['id']}", "INFO")

    # 保存会话状态
    session_state = {
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "current_feature": next_task["id"],
        "started_at": datetime.now().isoformat(),
        "status": "in_progress"
    }

    try:
        if 'Config' in globals():
            session_state_path = Config.get_session_state_path()
            metadata_dir = Config.get_metadata_dir()
        else:
            session_state_path = SESSION_STATE_FILE
            metadata_dir = METADATA_DIR

        os.makedirs(metadata_dir, exist_ok=True)
        with open(session_state_path, "w", encoding="utf-8") as f:
            json.dump(session_state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 保存会话状态失败: {str(e)}")
        return None

    print(f"\n💡 会话已启动 (ID: {session_state['session_id']})")
    print(f"   当前任务: {next_task['id']}")

    return next_task


def run_init_script():
    """运行初始化脚本"""
    init_script = "init.sh"

    if not os.path.exists(init_script):
        print(f"⚠️  警告: 未找到初始化脚本 '{init_script}'")
        print("请创建 init.sh 脚本来启动开发环境")
        return False

    print(f"\n🔧 运行初始化脚本: {init_script}")
    try:
        result = subprocess.run(
            ["bash", init_script],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode == 0:
            print("✓ 初始化成功")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ 初始化失败 (返回码: {result.returncode})")
            if result.stderr:
                print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ 初始化超时")
        return False
    except Exception as e:
        print(f"❌ 运行错误: {str(e)}")
        return False


def verify_environment():
    """验证环境状态"""
    print(f"\n🔍 验证环境状态...")

    # 检查 Git 仓库
    try:
        if 'GitHelper' in globals():
            git_initialized = GitHelper.is_initialized()
            git_configured = GitHelper.is_configured()
        else:
            git_initialized = os.path.exists(".git")
            git_configured = git_initialized  # 简化检查

        if git_initialized:
            print("✓ Git 仓库已初始化")
        else:
            print("⚠️  Git 仓库未初始化 (建议运行 git init)")

        if git_configured:
            print("✓ Git 已配置")
        else:
            print("⚠️  Git 未配置用户信息")
    except:
        print("⚠️  无法检查 Git 状态")

    # 检查功能清单
    try:
        if 'Config' in globals():
            feature_list_path = Config.get_feature_list_path()
        else:
            feature_list_path = FEATURE_LIST_FILE

        if os.path.exists(feature_list_path):
            print("✓ 功能清单存在")
        else:
            print("❌ 功能清单不存在")
    except:
        print("❌ 无法检查功能清单")

    return git_initialized


def complete_task(feature_id, notes=None, commit_message=None):
    """完成任务"""
    print(f"\n✅ 完成任务: {feature_id}\n")

    # 验证功能 ID
    if not validate_feature_id(feature_id):
        print(f"❌ 错误: 无效的功能 ID '{feature_id}'")
        return

    # 导入模块
    feature_manager = get_feature_manager()
    progress_tracker = get_progress_tracker()

    if not feature_manager or not progress_tracker:
        return

    # 更新功能状态
    feature_manager.update_feature_status(feature_id, True, notes)

    # 记录进度
    progress_tracker.log(f"完成功能: {feature_id} - {notes}", "SUCCESS")

    # Git 提交
    if commit_message:
        try:
            print(f"\n📦 Git 提交...")
            if 'GitHelper' in globals():
                success, message = GitHelper.commit(commit_message)
                if success:
                    print(f"✓ {message}")
                    progress_tracker.log(f"Git 提交: {commit_message}", "INFO")
                else:
                    print(f"⚠️  {message}")
            else:
                # 降级处理
                result = subprocess.run(
                    ["git", "commit", "-am", commit_message],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print("✓ Git 提交成功")
                    progress_tracker.log(f"Git 提交: {commit_message}", "INFO")
                else:
                    print("⚠️  Git 提交失败")
                    print(result.stderr)
        except Exception as e:
            print(f"⚠️  Git 提交错误: {str(e)}")

    # 更新会话状态
    try:
        if 'Config' in globals():
            session_state_path = Config.get_session_state_path()
        else:
            session_state_path = SESSION_STATE_FILE

        if os.path.exists(session_state_path):
            with open(session_state_path, "r", encoding="utf-8") as f:
                session_state = json.load(f)

            session_state["status"] = "completed"
            session_state["ended_at"] = datetime.now().isoformat()

            with open(session_state_path, "w", encoding="utf-8") as f:
                json.dump(session_state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  更新会话状态失败: {str(e)}")

    # 显示下一个任务
    print(f"\n📊 更新后的进度:")
    stats = feature_manager.get_feature_stats()
    if stats:
        print(f"  已完成: {stats['completed']}/{stats['total']} ({stats['progress']:.1f}%)")

    print(f"\n📋 下一个任务:")
    next_feature = get_next_task()
    if not next_feature:
        print("  所有功能已完成！")


def get_session_state():
    """获取当前会话状态"""
    try:
        if 'Config' in globals():
            session_state_path = Config.get_session_state_path()
        else:
            session_state_path = SESSION_STATE_FILE

        if not os.path.exists(session_state_path):
            return None

        with open(session_state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取会话状态失败: {str(e)}")
        return None


def quick_check():
    """快速检查项目状态（用于会话开始时的简短报告）"""
    print(f"\n📌 快速状态检查:\n")

    # 检查 Git
    try:
        if 'GitHelper' in globals():
            if GitHelper.is_initialized():
                print("✓ Git 仓库")
        else:
            if os.path.exists(".git"):
                print("✓ Git 仓库")
    except:
        pass

    # 检查功能清单
    try:
        ok, msg = validate_project_initialized()
        if ok:
            feature_manager = get_feature_manager()
            if feature_manager:
                stats = feature_manager.get_feature_stats()
                if stats:
                    print(f"✓ 功能清单: {stats['completed']}/{stats['total']} 完成")
    except:
        pass

    # 检查会话状态
    try:
        session_state = get_session_state()
        if session_state:
            status_emoji = "🔄" if session_state["status"] == "in_progress" else "✅"
            print(f"{status_emoji} 会话 {session_state['session_id']}: {session_state['status']}")
    except:
        pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="会话编排器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # next-task 命令
    subparsers.add_parser("next-task", help="获取下一个任务")

    # start-session 命令
    subparsers.add_parser("start-session", help="开始新会话")

    # run-init 命令
    subparsers.add_parser("run-init", help="运行初始化脚本")

    # verify 命令
    subparsers.add_parser("verify", help="验证环境")

    # complete 命令
    complete_parser = subparsers.add_parser("complete", help="完成任务")
    complete_parser.add_argument("--feature-id", required=True, help="功能 ID")
    complete_parser.add_argument("--notes", help="完成说明")
    complete_parser.add_argument("--commit-message", help="Git 提交消息")

    # session-state 命令
    subparsers.add_parser("session-state", help="显示会话状态")

    # quick-check 命令
    subparsers.add_parser("quick-check", help="快速状态检查")

    args = parser.parse_args()

    if args.command == "next-task":
        get_next_task()
    elif args.command == "start-session":
        start_session()
    elif args.command == "run-init":
        run_init_script()
    elif args.command == "verify":
        verify_environment()
    elif args.command == "complete":
        complete_task(args.feature_id, args.notes, args.commit_message)
    elif args.command == "session-state":
        state = get_session_state()
        if state:
            print(f"\n📊 会话状态:\n")
            print(f"  会话 ID: {state.get('session_id', 'N/A')}")
            print(f"  当前功能: {state.get('current_feature', 'N/A')}")
            print(f"  状态: {state.get('status', 'N/A')}")
            print(f"  开始时间: {state.get('started_at', 'N/A')}")
            print(f"  结束时间: {state.get('ended_at', 'N/A')}")
        else:
            print("没有活动会话")
    elif args.command == "quick-check":
        quick_check()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
