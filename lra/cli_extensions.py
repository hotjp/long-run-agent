#!/usr/bin/env python3
"""
CLI 扩展命令
v5.0 - 新增验证、测试、质量检查功能
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from lra.config import Config


class CLIExtensions:
    """CLI扩展命令集合"""

    def __init__(self, cli_instance):
        self.cli = cli_instance
        self.task_manager = cli_instance.task_manager
        self.project_path = os.getcwd()  # 项目根目录

    def cmd_status(self, json_mode: bool = False):
        """项目进度可视化"""
        data = self.task_manager._load()

        if not data:
            if json_mode:
                self.cli.output({"error": "not_initialized"}, True)
            else:
                print("❌ 项目未初始化")
            return

        tasks = data.get("tasks", [])

        # 统计各状态任务数
        stats = {
            "total": len(tasks),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "blocked": 0,
            "test_failed": 0,
        }

        # 按优先级统计
        priority_stats = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

        for task in tasks:
            status = task.get("status", "pending")
            priority = task.get("priority", "P1")

            if status in stats:
                stats[status] += 1
            if priority in priority_stats:
                priority_stats[priority] += 1

        # 计算完成率
        completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0

        if json_mode:
            result = {
                "stats": stats,
                "priority_stats": priority_stats,
                "completion_rate": round(completion_rate, 1),
            }
            self.cli.output(result, True)
            return

        # 可视化输出
        print(f"\n📊 项目进度: {stats['completed']}/{stats['total']} ({completion_rate:.1f}%)\n")

        # 进度条
        bar_length = 40
        filled = int(bar_length * completion_rate / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}]")
        print()

        # 任务分布
        print("📈 任务分布:")
        status_icons = {
            "completed": "✅",
            "in_progress": "🔄",
            "pending": "⏳",
            "blocked": "🚫",
            "test_failed": "❌",
        }

        for status, count in stats.items():
            if status == "total":
                continue
            if count > 0:
                icon = status_icons.get(status, "•")
                bar_count = min(count, 30)  # 限制bar长度
                print(f"  {icon} {status:15s}: {count:3d} {'█' * bar_count}")

        print()

        # 优先级分布
        print("🎯 优先级分布:")
        for priority in ["P0", "P1", "P2", "P3"]:
            count = priority_stats[priority]
            if count > 0:
                print(f"  {priority}: {count}")

        # 预估剩余时间（简化）
        if stats["completed"] > 0 and stats["total"] > stats["completed"]:
            remaining = stats["total"] - stats["completed"]
            # 假设每个任务平均30分钟
            estimated_hours = (remaining * 30) / 60
            print(f"\n⏱️  预估剩余时间: {estimated_hours:.1f} 小时 (基于 {remaining} 个任务)")

        print()

    def cmd_orientation(self, json_mode: bool = False):
        """上下文重建协议 - 为Agent提供完整上下文"""
        if not self.cli._check_project():
            if json_mode:
                self.cli.output({"error": "not_initialized"}, True)
            return

        if json_mode:
            # JSON模式：返回结构化数据
            context = self.task_manager.get_context("8k")

            # 添加项目结构
            context["orientation"] = {
                "working_dir": os.getcwd(),
                "project_structure": self._get_project_structure(),
                "recent_commits": self._get_recent_commits(5),
                "analysis_index": str(Path(Config.get_metadata_dir()) / "analysis" / "index.json"),
                "tasks_dir": str(Config.get_tasks_dir()),
                "progress_file": str(Path(Config.get_metadata_dir()) / "progress.txt"),
            }

            self.cli.output(context, True)
        else:
            # 人类可读模式
            print("\n## 项目定位\n")
            print(f"**工作目录**: {os.getcwd()}\n")

            print("## 项目结构")
            self._print_project_structure()
            print()

            print("## 最近提交")
            self._print_recent_commits()
            print()

            print("## 任务进度")
            self.cmd_status()

            print("## 可领取任务")
            self.cli.cmd_context("8k")

            print("\n## 关键文件位置")
            print(f"- 任务文件: {Config.get_tasks_dir()}")
            print(f"- Agent索引: {Path(Config.get_metadata_dir()) / 'analysis' / 'index.json'}")
            print(f"- 进度笔记: {Path(Config.get_metadata_dir()) / 'progress.txt'}")
            print()

    def _get_project_structure(self) -> List[str]:
        """获取项目结构"""
        structure = []
        try:
            for root, dirs, files in os.walk(".", maxdepth=2):
                # 跳过隐藏目录和忽略目录
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "__pycache__", "dist", "build"]
                ]

                level = root.count(os.sep)
                indent = " " * 2 * level
                structure.append(f"{indent}{os.path.basename(root)}/")

                if level < 2:  # 只显示前2层的文件
                    subindent = " " * 2 * (level + 1)
                    for file in files[:5]:  # 每个目录最多5个文件
                        if not file.startswith("."):
                            structure.append(f"{subindent}{file}")
                    if len(files) > 5:
                        structure.append(f"{subindent}... ({len(files) - 5} more files)")
        except:
            pass

        return structure[:50]  # 最多50行

    def _print_project_structure(self):
        """打印项目结构"""
        structure = self._get_project_structure()
        for line in structure:
            print(line)

    def _get_recent_commits(self, count: int = 5) -> List[str]:
        """获取最近提交"""
        commits = []
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--oneline", f"-{count}"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                commits = result.stdout.strip().split("\n")
        except:
            pass

        return commits

    def _print_recent_commits(self):
        """打印最近提交"""
        commits = self._get_recent_commits(10)
        if commits:
            for commit in commits:
                print(f"  {commit}")
        else:
            print("  (无Git历史或非Git项目)")

    def cmd_regression_test(
        self,
        task_id: str = None,
        template: str = None,
        report: bool = False,
        json_mode: bool = False,
    ):
        """运行回归测试"""
        try:
            from lra.regression_test import RegressionTestManager
        except ImportError:
            print("❌ 回归测试模块未安装")
            return

        manager = RegressionTestManager()

        if report:
            # 显示报告
            report_content = manager.get_regression_report()
            if json_mode:
                results = manager.get_last_results()
                self.cli.output(results or {"error": "no_results"}, True)
            else:
                print(report_content)
            return

        # 运行测试
        if not json_mode:
            print("🧪 运行回归测试...")

        results = manager.run_regression_tests(task_id, template)

        if json_mode:
            self.cli.output(results, True)
            return

        # 可视化输出
        print(f"\n{'=' * 60}")
        print("回归测试结果")
        print(f"{'=' * 60}\n")

        print(f"总计: {results['total']} 个任务")
        print(f"✅ 通过: {results['passed']}")
        print(f"❌ 失败: {results['failed']}")
        print()

        if results["failed"] > 0:
            print("❌ 失败任务:")
            for tid in results["failed_tasks"]:
                print(f"  - {tid}")
            print()
            print("💡 建议:")
            print("  1. 查看失败任务详情: lra show <task_id>")
            print("  2. 修复后重新测试: lra regression-test")
            print("  3. 查看详细报告: lra regression-test --report")
        else:
            print("✅ 所有任务验证通过！")

        print()

    def cmd_browser_test(
        self, task_id: str = None, generate_script: bool = False, json_mode: bool = False
    ):
        """浏览器自动化测试"""
        try:
            from lra.browser_automation import BrowserAutomation
        except ImportError:
            print("❌ 浏览器自动化模块未安装")
            return

        automation = BrowserAutomation()

        if task_id:
            # 测试指定任务
            status = automation.get_verification_status(task_id)

            if json_mode:
                self.cli.output(status, True)
                return

            print(f"\n任务 {task_id} 验证状态:\n")
            print(f"有证据: {'✅' if status['has_evidence'] else '❌'}")

            if status["evidence_details"]:
                print("\n证据详情:")
                for key, value in status["evidence_details"].items():
                    if isinstance(value, list):
                        print(f"  {key}:")
                        for item in value:
                            print(f"    - {item}")
                    else:
                        print(f"  {key}: {value}")

            if status["recommendations"]:
                print("\n💡 建议:")
                for rec in status["recommendations"]:
                    print(f"  - {rec}")

            if generate_script and not status["has_evidence"]:
                print("\n📝 生成测试脚本...")
                # 从任务文件读取测试步骤
                task_file = Config.get_tasks_dir() / f"{task_id}.md"
                if task_file.exists():
                    content = task_file.read_text()
                    # 简化：提取测试步骤
                    test_steps = ["步骤1: 打开应用", "步骤2: 执行测试"]
                    script_path = automation.save_verification_script(task_id, test_steps)
                    print(f"✅ 测试脚本已生成: {script_path}")
                    print("   运行: python " + script_path)

            print()
        else:
            # 显示帮助
            print("\n浏览器自动化测试\n")
            print("用法:")
            print("  lra browser-test <task_id>           # 检查任务验证状态")
            print("  lra browser-test <task_id> --script  # 生成测试脚本")
            print("  lra browser-test --help              # 显示帮助")
            print()

    def cmd_quality_check(self, task_id: str = None, report: bool = False, json_mode: bool = False):
        """代码质量检查"""
        try:
            from lra.quality_checker import QualityChecker
        except ImportError:
            print("❌ 质量检查模块未安装")
            return

        checker = QualityChecker()

        if report:
            # 显示报告
            report_content = checker.generate_quality_report()
            if json_mode:
                from lra.config import SafeJson

                results = SafeJson.read(checker.quality_report_path)
                self.cli.output(results or {"error": "no_results"}, True)
            else:
                print(report_content)
            return

        # 运行检查
        if not json_mode:
            print("🔍 运行代码质量检查...")

        results = checker.check_code_quality(task_id)

        if json_mode:
            self.cli.output(results, True)
            return

        # 可视化输出
        score = results["score"]

        if score >= 90:
            grade = "优秀 🌟"
        elif score >= 70:
            grade = "良好 👍"
        elif score >= 60:
            grade = "及格 ⚠️"
        else:
            grade = "不及格 ❌"

        print(f"\n{'=' * 60}")
        print("代码质量报告")
        print(f"{'=' * 60}\n")

        print(f"总分: {score}/100")
        print(f"等级: {grade}\n")

        # 详细检查
        if results.get("details"):
            print("检查详情:")
            for category, details in results["details"].items():
                category_name = {
                    "documentation": "文档",
                    "complexity": "复杂度",
                    "naming": "命名",
                    "structure": "结构",
                    "testing": "测试",
                }.get(category, category)

                print(f"\n  {category_name}: {details['score']}/100")

        # 问题
        if results.get("issues"):
            print("\n❌ 发现的问题:")
            for issue in results["issues"][:5]:  # 只显示前5个
                severity = issue.get("severity", "unknown")
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"  {icon} {issue['message']}")

        # 建议
        if results.get("suggestions"):
            print("\n💡 改进建议:")
            for i, suggestion in enumerate(results["suggestions"][:5], 1):
                print(f"  {i}. {suggestion}")

        print()
