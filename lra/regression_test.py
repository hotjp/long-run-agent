#!/usr/bin/env python3
"""
回归测试管理器
v1.0 - 自动验证已完成任务
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from lra.config import Config, SafeJson


class RegressionTestManager:
    """回归测试管理器"""

    def __init__(self):
        self.results_path = Path(Config.get_metadata_dir()) / "regression_results.json"
        self.results_path.parent.mkdir(parents=True, exist_ok=True)

    def run_regression_tests(
        self, task_id: str = None, template_filter: str = None
    ) -> Dict[str, Any]:
        """
        运行回归测试

        参数:
            task_id: 指定任务ID，None表示测试所有completed任务
            template_filter: 模板过滤器，如 "code-module"

        返回:
            {
                "timestamp": "...",
                "total": 10,
                "passed": 8,
                "failed": 2,
                "failed_tasks": ["task_001", "task_002"],
                "results": [...]
            }
        """
        from lra.task_manager import TaskManager

        task_manager = TaskManager()
        data = task_manager._load()

        if not data:
            return {
                "timestamp": datetime.now().isoformat(),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_tasks": [],
                "results": [],
            }

        # 获取completed任务
        completed_tasks = [t for t in data.get("tasks", []) if t.get("status") == "completed"]

        # 过滤
        if task_id:
            completed_tasks = [t for t in completed_tasks if t["id"] == task_id]

        if template_filter:
            completed_tasks = [t for t in completed_tasks if t.get("template") == template_filter]

        results = {
            "timestamp": datetime.now().isoformat(),
            "total": len(completed_tasks),
            "passed": 0,
            "failed": 0,
            "failed_tasks": [],
            "results": [],
        }

        for task in completed_tasks:
            test_result = self._reverify_task(task)
            results["results"].append(test_result)

            if test_result["success"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["failed_tasks"].append(task["id"])

                # 自动标记为需要修复
                self._mark_task_for_fix(task["id"], test_result["reason"])

        # 保存结果
        self._save_results(results)

        return results

    def _reverify_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        重新验证单个任务

        返回:
            {
                "task_id": "...",
                "success": True/False,
                "reason": "...",
                "checks": {...}
            }
        """
        from pathlib import Path

        task_id = task["id"]
        result = {"task_id": task_id, "success": True, "reason": "", "checks": {}}

        # 读取任务文件
        task_file = Path(Config.get_tasks_dir()) / f"{task_id}.md"
        if not task_file.exists():
            result["success"] = False
            result["reason"] = "任务文件不存在"
            result["checks"]["file_exists"] = False
            return result

        content = task_file.read_text()

        # 检查1: 是否有测试证据
        has_evidence = self._check_test_evidence(content)
        result["checks"]["has_evidence"] = has_evidence

        if not has_evidence:
            result["success"] = False
            result["reason"] = "缺少测试证据"
            return result

        # 检查2: 验证步骤是否完整
        has_verification_steps = self._check_verification_steps(content)
        result["checks"]["has_verification_steps"] = has_verification_steps

        # 检查3: 是否有测试输出
        has_test_output = self._check_test_output(content)
        result["checks"]["has_test_output"] = has_test_output

        # 根据模板类型执行特定检查
        template = task.get("template", "task")
        if template == "code-module":
            code_checks = self._check_code_module(content, task)
            result["checks"].update(code_checks)

            if not code_checks.get("has_tests", False):
                result["success"] = False
                result["reason"] = "代码模块缺少测试"

        # 检查4: 截图（如果适用）
        has_screenshots = self._check_screenshots(task_id, content)
        result["checks"]["has_screenshots"] = has_screenshots

        return result

    def _check_test_evidence(self, content: str) -> bool:
        """检查是否有测试证据"""
        keywords = [
            "测试证据",
            "验证证据",
            "测试结果",
            "verification",
            "test evidence",
            "screenshot",
        ]
        return any(kw in content.lower() for kw in keywords)

    def _check_verification_steps(self, content: str) -> bool:
        """检查是否有验证步骤"""
        keywords = ["测试步骤", "验证步骤", "test steps", "verification steps"]
        return any(kw in content.lower() for kw in keywords)

    def _check_test_output(self, content: str) -> bool:
        """检查是否有测试输出"""
        indicators = ["```", "passed", "failed", "测试通过", "测试失败", "✅", "❌"]
        return any(ind in content for ind in indicators)

    def _check_code_module(self, content: str, task: Dict[str, Any]) -> Dict[str, bool]:
        """检查代码模块特定内容"""
        checks = {
            "has_tests": "测试" in content or "test" in content.lower(),
            "has_code_snippet": "```" in content,
            "has_implementation": "实现" in content or "implement" in content.lower(),
        }
        return checks

    def _check_screenshots(self, task_id: str, content: str) -> bool:
        """检查是否有截图"""
        # 检查任务文件中是否提到截图
        if "screenshot" in content.lower() or "截图" in content:
            return True

        # 检查截图目录
        screenshot_dir = Path(Config.get_metadata_dir()) / "screenshots"
        if screenshot_dir.exists():
            screenshots = list(screenshot_dir.glob(f"{task_id}_*.png"))
            return len(screenshots) > 0

        return False

    def _mark_task_for_fix(self, task_id: str, reason: str):
        """标记任务需要修复"""
        from lra.task_manager import TaskManager

        task_manager = TaskManager()

        # 将状态改为 test_failed（如果模板支持）
        template = task_manager.get_task_template(task_id)
        if template == "code-module":
            task_manager.update_status(task_id, "test_failed", force=True)
        else:
            # 其他模板：添加标记到任务文件
            task_file = Path(Config.get_tasks_dir()) / f"{task_id}.md"
            if task_file.exists():
                content = task_file.read_text()
                warning = f"\n\n## ⚠️ 回归测试失败\n\n**原因**: {reason}\n**时间**: {datetime.now().isoformat()}\n"
                task_file.write_text(content + warning)

    def _save_results(self, results: Dict[str, Any]):
        """保存回归测试结果"""
        SafeJson.write(self.results_path, results)

    def get_regression_report(self) -> str:
        """生成回归测试报告"""
        if not self.results_path.exists():
            return "未找到回归测试结果"

        results = SafeJson.read(self.results_path)
        if not results:
            return "回归测试结果为空"

        report = f"""# 回归测试报告

**测试时间**: {results["timestamp"]}

## 总体结果

- 总计: {results["total"]} 个任务
- ✅ 通过: {results["passed"]}
- ❌ 失败: {results["failed"]}

"""

        if results["failed"] > 0:
            report += "## 失败任务\n\n"
            for task_id in results["failed_tasks"]:
                report += f"- {task_id}\n"
            report += "\n"

        report += "## 详细结果\n\n"
        for result in results.get("results", []):
            status = "✅" if result["success"] else "❌"
            report += f"### {status} {result['task_id']}\n\n"
            if result.get("reason"):
                report += f"**原因**: {result['reason']}\n\n"

            checks = result.get("checks", {})
            if checks:
                report += "**检查项**:\n"
                for check, passed in checks.items():
                    check_status = "✅" if passed else "❌"
                    report += f"- {check_status} {check}\n"
                report += "\n"

        return report

    def get_last_results(self) -> Optional[Dict[str, Any]]:
        """获取最近的回归测试结果"""
        if not self.results_path.exists():
            return None

        return SafeJson.read(self.results_path)

    def should_run_regression(self) -> bool:
        """判断是否应该运行回归测试"""
        last_results = self.get_last_results()

        if not last_results:
            return True

        # 如果上次测试有失败，建议重测
        if last_results.get("failed", 0) > 0:
            return True

        # 如果距离上次测试超过24小时，建议重测
        last_time = datetime.fromisoformat(last_results["timestamp"])
        hours_since = (datetime.now() - last_time).total_seconds() / 3600

        return hours_since > 24
