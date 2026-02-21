#!/usr/bin/env python3
"""
进度追踪器
记录和管理 Agent 工作进度
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 导入共享配置
try:
    from .config import Config, SafeJson
except ImportError:
    print("警告: 无法导入 config 模块，使用默认配置")
    METADATA_DIR = ".long-run-agent"
    PROGRESS_FILE = os.path.join(METADATA_DIR, "progress.txt")
    CONFIG_FILE = os.path.join(METADATA_DIR, "config.json")

    def get_progress_path():
        return PROGRESS_FILE

    def get_config_path():
        return CONFIG_FILE
else:
    def get_progress_path():
        return Config.get_progress_path()

    def get_config_path():
        return Config.get_config_path()


def log(message, level="INFO"):
    """记录进度日志"""
    try:
        from .config import Config
        metadata_dir = Config.get_metadata_dir()
        progress_path = Config.get_progress_path()
    except ImportError:
        metadata_dir = METADATA_DIR
        progress_path = get_progress_path()

    os.makedirs(metadata_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"

    try:
        with open(progress_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"✓ 日志已记录: {message}")
    except Exception as e:
        print(f"❌ 写入日志失败: {str(e)}")


def get_recent_history(lines=20):
    """获取最近的进度日志"""
    progress_path = get_progress_path()

    if not os.path.exists(progress_path):
        return []

    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        # 返回最后 N 行
        recent = all_lines[-lines:]
        return [line.strip() for line in recent if line.strip()]
    except Exception as e:
        print(f"❌ 读取日志失败: {str(e)}")
        return []


def show_status():
    """显示当前状态"""
    progress_path = get_progress_path()

    if not os.path.exists(progress_path):
        print("暂无进度记录")
        return

    print(f"\n📝 最近进度记录 (最后 10 条):\n")
    recent = get_recent_history(10)

    for line in recent:
        # 解析时间戳和级别
        parts = line.split("] ")
        if len(parts) >= 3:
            timestamp = parts[0].strip().replace("[", "")
            level = parts[1].strip().replace("[", "")
            message = "] ".join(parts[2:])

            # 根据级别添加 emoji
            if level == "INFO":
                emoji = "ℹ️"
            elif level == "SUCCESS":
                emoji = "✅"
            elif level == "ERROR":
                emoji = "❌"
            elif level == "WARNING":
                emoji = "⚠️"
            else:
                emoji = "📌"

            print(f"{emoji} {timestamp} {message}")
        else:
            print(f"  {line}")


def show_full_history():
    """显示完整历史"""
    progress_path = get_progress_path()

    if not os.path.exists(progress_path):
        print("暂无进度记录")
        return

    print(f"\n📝 完整进度记录:\n")

    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            for line in f:
                print(line.rstrip())
    except Exception as e:
        print(f"❌ 读取日志失败: {str(e)}")


def get_config():
    """获取配置"""
    config_path = get_config_path()

    if not os.path.exists(config_path):
        return None

    try:
        import json
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取配置失败: {str(e)}")
        return None


def show_config():
    """显示配置信息"""
    config = get_config()

    if not config:
        print("未找到配置文件")
        return

    print(f"\n⚙️ 项目配置:\n")
    print(f"  项目名称: {config.get('project_name', 'N/A')}")
    print(f"  创建时间: {config.get('created_at', 'N/A')}")
    print(f"  版本: {config.get('version', 'N/A')}")
    print(f"  规格描述: {config.get('spec', 'N/A')}")


def get_session_summary():
    """获取会话摘要（用于快速了解当前状态）"""
    summary = []

    # 添加配置
    config = get_config()
    if config:
        summary.append(f"项目: {config.get('project_name', 'Unknown')}")

    # 添加最近进度
    recent = get_recent_history(5)
    if recent:
        summary.append("最近活动:")
        for line in recent[-3:]:
            parts = line.split("] ")
            if len(parts) >= 3:
                message = "] ".join(parts[2:])
                summary.append(f"  - {message}")

    # 导入 feature_manager 获取统计
    feature_stats = None
    try:
        # 使用绝对路径导入
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        feature_manager_path = os.path.join(current_dir, 'feature_manager.py')

        if feature_manager_path not in sys.path:
            sys.path.insert(0, current_dir)

        import feature_manager
        feature_stats = feature_manager.get_feature_stats()
    except Exception as e:
        print(f"⚠️  无法获取功能统计: {str(e)}")

    if feature_stats:
        summary.append(f"\n功能进度: {feature_stats['completed']}/{feature_stats['total']} ({feature_stats['progress']:.1f}%)")

    return "\n".join(summary)


def main():
    parser = argparse.ArgumentParser(description="进度追踪器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # log 命令
    log_parser = subparsers.add_parser("log", help="记录进度")
    log_parser.add_argument("--message", required=True, help="日志消息")
    log_parser.add_argument("--level", default="INFO", help="日志级别 (INFO|SUCCESS|ERROR|WARNING)")

    # status 命令
    subparsers.add_parser("status", help="显示状态")

    # history 命令
    subparsers.add_parser("history", help="显示完整历史")

    # config 命令
    subparsers.add_parser("config", help="显示配置")

    # summary 命令
    subparsers.add_parser("summary", help="显示会话摘要")

    args = parser.parse_args()

    if args.command == "log":
        log(args.message, args.level)
    elif args.command == "status":
        show_config()
        print()
        show_status()
    elif args.command == "history":
        show_full_history()
    elif args.command == "config":
        show_config()
    elif args.command == "summary":
        print(get_session_summary())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
