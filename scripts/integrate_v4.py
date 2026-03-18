#!/usr/bin/env python3
"""
LRA v5.0 CLI 集成脚本
自动将新功能集成到现有CLI
"""

import os
import sys
from pathlib import Path


def integrate_cli_extensions():
    """集成CLI扩展到主CLI"""

    cli_path = Path("long_run_agent/cli.py")

    if not cli_path.exists():
        print("❌ 找不到 cli.py 文件")
        return False

    # 读取现有CLI
    with open(cli_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否已集成
    if "from .cli_extensions import CLIExtensions" in content:
        print("✅ CLI扩展已集成")
        return True

    print("📝 开始集成CLI扩展...")

    # 1. 添加导入
    import_insert = """
from .cli_extensions import CLIExtensions
"""

    # 在其他导入后添加
    if "from .batch_lock_manager import BatchLockManager" in content:
        content = content.replace(
            "from .batch_lock_manager import BatchLockManager",
            "from .batch_lock_manager import BatchLockManager\n" + import_insert.strip(),
        )

    # 2. 在 __init__ 中初始化扩展
    init_insert = """
        self.extensions = CLIExtensions(self)
"""

    if "self.system_check_available = HAS_SYSTEM_CHECK" in content:
        content = content.replace(
            "self.system_check_available = HAS_SYSTEM_CHECK",
            "self.system_check_available = HAS_SYSTEM_CHECK\n" + init_insert.strip(),
        )

    # 3. 添加新命令方法（在类的末尾）
    new_methods = '''

    # ==================== v5.0 新增命令 ====================

    def cmd_status(self, json_mode: bool = False):
        """项目进度可视化"""
        self.extensions.cmd_status(json_mode)

    def cmd_orientation(self, json_mode: bool = False):
        """上下文重建协议"""
        self.extensions.cmd_orientation(json_mode)

    def cmd_regression_test(self, task_id=None, template=None, report=False, json_mode=False):
        """回归测试"""
        self.extensions.cmd_regression_test(task_id, template, report, json_mode)

    def cmd_browser_test(self, task_id=None, generate_script=False, json_mode=False):
        """浏览器自动化测试"""
        self.extensions.cmd_browser_test(task_id, generate_script, json_mode)

    def cmd_quality_check(self, task_id=None, report=False, json_mode=False):
        """代码质量检查"""
        self.extensions.cmd_quality_check(task_id, report, json_mode)
'''

    # 找到类的末尾（在 setup_parser 之前）
    if "def setup_parser():" in content:
        content = content.replace("def setup_parser():", new_methods + "\n\ndef setup_parser():")

    # 保存修改
    with open(cli_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ CLI扩展集成完成")
    return True


def add_new_commands_to_parser():
    """添加新命令到参数解析器"""

    cli_path = Path("long_run_agent/cli.py")

    with open(cli_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("📝 添加新命令到参数解析器...")

    # 找到 subparsers 定义位置
    # 在 status-guide 命令后添加新命令

    new_commands = """
    # ==================== v5.0 新增命令 ====================
    
    # status - 项目进度可视化
    status_p = subparsers.add_parser("status", help="项目进度可视化")
    status_p.set_defaults(command="status")
    
    # orientation - 上下文重建协议
    orientation_p = subparsers.add_parser("orientation", help="上下文重建协议 (Agent专用)")
    orientation_p.set_defaults(command="orientation")
    
    # regression-test - 回归测试
    regression_p = subparsers.add_parser("regression-test", help="回归测试")
    regression_p.add_argument("task_id", nargs="?", help="任务ID (可选)")
    regression_p.add_argument("--template", help="模板过滤器")
    regression_p.add_argument("--report", action="store_true", help="查看测试报告")
    regression_p.set_defaults(command="regression-test")
    
    # browser-test - 浏览器自动化测试
    browser_p = subparsers.add_parser("browser-test", help="浏览器自动化测试")
    browser_p.add_argument("task_id", nargs="?", help="任务ID (可选)")
    browser_p.add_argument("--script", action="store_true", dest="generate_script", 
                          help="生成测试脚本")
    browser_p.set_defaults(command="browser-test")
    
    # quality-check - 代码质量检查
    quality_p = subparsers.add_parser("quality-check", help="代码质量检查")
    quality_p.add_argument("task_id", nargs="?", help="任务ID (可选)")
    quality_p.add_argument("--report", action="store_true", help="查看质量报告")
    quality_p.set_defaults(command="quality-check")
    
"""

    # 在 start 命令前插入
    if 'start_p = subparsers.add_parser("start"' in content:
        content = content.replace(
            'start_p = subparsers.add_parser("start"',
            new_commands + '    start_p = subparsers.add_parser("start"',
        )

        with open(cli_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ 新命令已添加到解析器")
        return True

    print("⚠️  未能自动添加命令，请手动添加")
    return False


def add_command_dispatch():
    """添加命令分发逻辑"""

    cli_path = Path("long_run_agent/cli.py")

    with open(cli_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("📝 添加命令分发逻辑...")

    dispatch_code = """
    # ==================== v5.0 新增命令分发 ====================
    
    elif args.command == "status":
        cli.cmd_status(json_mode)
    
    elif args.command == "orientation":
        cli.cmd_orientation(json_mode)
    
    elif args.command == "regression-test":
        cli.cmd_regression_test(
            getattr(args, 'task_id', None),
            getattr(args, 'template', None),
            args.report,
            json_mode
        )
    
    elif args.command == "browser-test":
        cli.cmd_browser_test(
            getattr(args, 'task_id', None),
            getattr(args, 'generate_script', False),
            json_mode
        )
    
    elif args.command == "quality-check":
        cli.cmd_quality_check(
            getattr(args, 'task_id', None),
            args.report,
            json_mode
        )
    
"""

    # 在 start 命令分发前插入
    if 'elif args.command == "start":' in content:
        content = content.replace(
            'elif args.command == "start":', dispatch_code + '    elif args.command == "start":'
        )

        with open(cli_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ 命令分发逻辑已添加")
        return True

    print("⚠️  未能自动添加分发逻辑，请手动添加")
    return False


def update_agent_guide():
    """更新Agent指南"""

    cli_path = Path("long_run_agent/cli.py")

    with open(cli_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("📝 更新Agent指南...")

    # 更新 AGENT_GUIDE
    new_guide = '''AGENT_GUIDE = """
LRA v5.0 | AI Agent 任务管理 + 质量保障

🚀 快速开始
   lra start                           # 智能启动（推荐）
   lra init --name <项目名>             # 初始化项目
   lra analyze-project                 # 生成文档+索引

📂 常用命令（按工作流）
   项目: start | init | status | orientation | analyze-project
   任务: list | create | show | set | split | search
   执行: claim | heartbeat | checkpoint | pause | resume | publish
   测试: regression-test | browser-test | quality-check
   依赖: deps | check-blocked
   批量: batch set|delete|claim

🔐 锁机制: claim → heartbeat → publish
🧪 测试: regression-test → browser-test → quality-check
💡 提示: list自动显示下一步，show显示状态流转

📚 帮助
   lra <cmd> --help        命令详情
   lra status-guide        状态流转图
   lra orientation         Agent上下文重建
   cat long_run_agent/prompts/agent_prompt.md  # 完整指南
   lra where               文件位置
"""
'''

    if "AGENT_GUIDE = " in content:
        # 找到旧的 AGENT_GUIDE 并替换
        import re

        pattern = r'AGENT_GUIDE = """.*?"""'
        content = re.sub(pattern, new_guide.strip(), content, flags=re.DOTALL)

        with open(cli_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ Agent指南已更新")
        return True

    return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  LRA v5.0 CLI 集成脚本")
    print("=" * 60 + "\n")

    # 检查当前目录
    if not Path("long_run_agent").exists():
        print("❌ 请在项目根目录运行此脚本")
        return

    # 执行集成步骤
    steps = [
        ("集成CLI扩展", integrate_cli_extensions),
        ("添加新命令", add_new_commands_to_parser),
        ("添加命令分发", add_command_dispatch),
        ("更新Agent指南", update_agent_guide),
    ]

    success_count = 0

    for step_name, step_func in steps:
        print(f"\n▶ {step_name}...")
        try:
            if step_func():
                success_count += 1
        except Exception as e:
            print(f"❌ 失败: {e}")

    # 总结
    print("\n" + "=" * 60)
    print(f"  集成完成: {success_count}/{len(steps)} 步骤成功")
    print("=" * 60 + "\n")

    if success_count == len(steps):
        print("✅ 所有功能已成功集成！")
        print("\n📋 下一步:")
        print("   1. 测试新命令: lra status")
        print("   2. 查看帮助: lra --help")
        print("   3. Agent指南: cat long_run_agent/prompts/agent_prompt.md")
        print("   4. 实施报告: cat IMPLEMENTATION_REPORT.md")
    else:
        print("⚠️  部分功能需要手动集成")
        print("\n请查看 IMPLEMENTATION_REPORT.md 中的 'CLI集成指南' 章节")

    print()


if __name__ == "__main__":
    main()
