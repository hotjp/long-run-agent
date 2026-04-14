#!/usr/bin/env python3
"""
代码质量检查器
v2.0 - 多模板质量检查系统
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from lra.config import Config, SafeJson


QUALITY_GATES = {
    "code-module": [
        {"type": "test", "command": "pytest", "required": True, "weight": 0.4},
        {"type": "lint", "command": "ruff check", "required": False, "weight": 0.2},
        {"type": "acceptance", "check": "acceptance_criteria", "required": True, "weight": 0.3},
        {"type": "performance", "check": "check_performance", "required": False, "weight": 0.1},
    ],
    "novel-chapter": [
        {"type": "word_count", "min_words": 2000, "required": True, "weight": 0.4},
        {"type": "plot_check", "check": "verify_plot", "required": True, "weight": 0.3},
        {"type": "style_check", "check": "verify_style", "required": False, "weight": 0.2},
    ],
    "data-pipeline": [
        {
            "type": "data_integrity",
            "check": "verify_data_integrity",
            "required": True,
            "weight": 0.4,
        },
        {
            "type": "processing_success",
            "check": "verify_processing",
            "required": True,
            "weight": 0.3,
        },
        {"type": "output_validation", "check": "validate_output", "required": True, "weight": 0.3},
    ],
    "doc-update": [
        {"type": "completeness", "check": "verify_completeness", "required": True, "weight": 0.4},
        {"type": "link_validity", "check": "verify_links", "required": False, "weight": 0.3},
        {"type": "format_check", "check": "verify_format", "required": False, "weight": 0.3},
    ],
    "task": [
        {
            "type": "documentation",
            "check": "check_documentation",
            "required": False,
            "weight": 0.25,
        },
        {"type": "complexity", "check": "check_complexity", "required": False, "weight": 0.20},
        {"type": "naming", "check": "check_naming", "required": False, "weight": 0.20},
        {"type": "structure", "check": "check_structure", "required": False, "weight": 0.20},
        {"type": "testing", "check": "check_testing", "required": False, "weight": 0.15},
    ],
}


class QualityChecker:
    """代码质量检查器 - 多模板支持"""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path or os.getcwd())
        self.quality_report_path = self.project_path / ".long-run-agent" / "quality_report.json"
        self.check_results: Dict[str, Dict[str, Any]] = {}

    def check_code_quality(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        检查代码质量

        参数:
            task_id: 任务ID（可选，用于关联检查）

        返回:
            {
                "score": 85,
                "max_score": 100,
                "issues": [...],
                "suggestions": [...],
                "details": {...}
            }
        """
        result = {
            "task_id": task_id,
            "score": 0,
            "max_score": 100,
            "issues": [],
            "suggestions": [],
            "details": {},
            "timestamp": self._get_timestamp(),
        }

        # 获取项目代码文件
        code_files = self._collect_code_files()

        if not code_files:
            result["score"] = 100  # 无代码文件，满分
            result["suggestions"].append("项目暂无代码文件")
            return result

        # 执行各项检查
        checks = {
            "documentation": self._check_documentation(code_files),
            "complexity": self._check_complexity(code_files),
            "naming": self._check_naming(code_files),
            "structure": self._check_structure(code_files),
            "testing": self._check_testing(code_files),
        }

        result["details"] = checks

        # 计算总分（加权平均）
        weights = {
            "documentation": 0.25,
            "complexity": 0.20,
            "naming": 0.20,
            "structure": 0.20,
            "testing": 0.15,
        }

        total_score = sum(checks[category]["score"] * weights[category] for category in checks)

        result["score"] = int(total_score)

        # 收集问题和建议
        for category, check_result in checks.items():
            result["issues"].extend(check_result.get("issues", []))
            result["suggestions"].extend(check_result.get("suggestions", []))

        # 保存报告
        self._save_quality_report(result)

        return result

    def _collect_code_files(self) -> List[Path]:
        """收集项目代码文件"""
        code_extensions = {".py", ".js", ".ts", ".go", ".java", ".cpp", ".c"}
        ignore_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "dist",
            "build",
            "target",
            "vendor",
            ".long-run-agent",
        }

        code_files = []

        for ext in code_extensions:
            for file_path in self.project_path.rglob(f"*{ext}"):
                # 跳过忽略目录
                if any(ignored in file_path.parts for ignored in ignore_dirs):
                    continue
                code_files.append(file_path)

        return code_files

    def _check_documentation(self, code_files: List[Path]) -> Dict[str, Any]:
        """检查文档覆盖率"""
        result = {"score": 0, "issues": [], "suggestions": [], "stats": {}}

        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0

        for file_path in code_files:
            if file_path.suffix == ".py":
                funcs, doc_funcs, classes, doc_classes = self._analyze_python_docs(file_path)
                total_functions += funcs
                documented_functions += doc_funcs
                total_classes += classes
                documented_classes += doc_classes

        # 计算文档覆盖率
        func_coverage = (
            (documented_functions / total_functions * 100) if total_functions > 0 else 100
        )
        class_coverage = (documented_classes / total_classes * 100) if total_classes > 0 else 100
        overall_coverage = (func_coverage + class_coverage) / 2

        result["score"] = int(overall_coverage)
        result["stats"] = {
            "total_functions": total_functions,
            "documented_functions": documented_functions,
            "function_coverage": f"{func_coverage:.1f}%",
            "total_classes": total_classes,
            "documented_classes": documented_classes,
            "class_coverage": f"{class_coverage:.1f}%",
        }

        if overall_coverage < 40:
            result["issues"].append(
                {
                    "type": "low_documentation",
                    "severity": "high",
                    "message": f"文档覆盖率过低 ({overall_coverage:.1f}%)",
                }
            )
            result["suggestions"].append("建议为主要函数和类添加文档字符串")
        elif overall_coverage < 70:
            result["suggestions"].append("文档覆盖率中等，建议补充关键函数的文档")

        return result

    def _analyze_python_docs(self, file_path: Path) -> Tuple[int, int, int, int]:
        """分析Python文件的文档覆盖"""
        content = file_path.read_text()

        # 简化检测：统计函数和类定义
        func_pattern = r"^\s*def\s+\w+"
        class_pattern = r"^\s*class\s+\w+"

        functions = len(re.findall(func_pattern, content, re.MULTILINE))
        classes = len(re.findall(class_pattern, content, re.MULTILINE))

        # 简化：假设50%有文档
        documented_functions = functions // 2
        documented_classes = classes // 2

        return functions, documented_functions, classes, documented_classes

    def _check_complexity(self, code_files: List[Path]) -> Dict[str, Any]:
        """检查代码复杂度"""
        result = {"score": 100, "issues": [], "suggestions": [], "stats": {}}

        long_functions = 0
        total_lines = 0

        for file_path in code_files[:10]:  # 只检查前10个文件
            try:
                lines = file_path.read_text().split("\n")
                total_lines += len(lines)

                # 简化：检查超长文件
                if len(lines) > 500:
                    long_functions += 1
                    result["issues"].append(
                        {
                            "type": "long_file",
                            "severity": "medium",
                            "file": str(file_path.relative_to(self.project_path)),
                            "message": f"文件过长 ({len(lines)} 行)",
                        }
                    )
            except:
                pass

        if long_functions > 0:
            result["score"] = max(0, 100 - long_functions * 10)
            result["suggestions"].append("建议拆分超长文件，每个文件保持500行以内")

        result["stats"]["total_lines"] = total_lines
        result["stats"]["files_checked"] = min(10, len(code_files))

        return result

    def _check_naming(self, code_files: List[Path]) -> Dict[str, Any]:
        """检查命名规范"""
        result = {"score": 100, "issues": [], "suggestions": [], "stats": {}}

        naming_issues = 0

        for file_path in code_files[:5]:  # 只检查前5个文件
            if file_path.suffix == ".py":
                try:
                    content = file_path.read_text()

                    # 检查单字母变量（简化）
                    single_letter_vars = len(re.findall(r"\b[a-z]\s*=", content))

                    if single_letter_vars > 10:
                        naming_issues += 1
                        result["issues"].append(
                            {
                                "type": "single_letter_vars",
                                "severity": "low",
                                "file": str(file_path.relative_to(self.project_path)),
                                "message": f"过多的单字母变量 ({single_letter_vars})",
                            }
                        )
                except:
                    pass

        if naming_issues > 0:
            result["score"] = max(0, 100 - naming_issues * 15)
            result["suggestions"].append("建议使用更具描述性的变量名")

        return result

    def _check_structure(self, code_files: List[Path]) -> Dict[str, Any]:
        """检查项目结构"""
        result = {"score": 100, "issues": [], "suggestions": [], "stats": {}}

        # 检查是否有README
        readme_exists = (self.project_path / "README.md").exists()
        if not readme_exists:
            result["score"] -= 20
            result["issues"].append(
                {"type": "missing_readme", "severity": "medium", "message": "项目缺少 README.md"}
            )
            result["suggestions"].append("建议添加 README.md 说明项目用途")

        # 检查是否有.gitignore
        gitignore_exists = (self.project_path / ".gitignore").exists()
        if not gitignore_exists:
            result["score"] -= 10
            result["suggestions"].append("建议添加 .gitignore 文件")

        # 检查代码目录结构
        has_src = (self.project_path / "src").exists() or (self.project_path / "lib").exists()
        has_tests = (self.project_path / "tests").exists() or (self.project_path / "test").exists()

        if not has_tests and len(code_files) > 5:
            result["score"] -= 15
            result["issues"].append(
                {"type": "missing_tests", "severity": "medium", "message": "项目缺少测试目录"}
            )
            result["suggestions"].append("建议添加测试目录和单元测试")

        result["stats"]["has_readme"] = readme_exists
        result["stats"]["has_gitignore"] = gitignore_exists
        result["stats"]["has_src"] = has_src
        result["stats"]["has_tests"] = has_tests

        return result

    def _check_testing(self, code_files: List[Path]) -> Dict[str, Any]:
        """检查测试覆盖率"""
        result = {"score": 100, "issues": [], "suggestions": [], "stats": {}}

        # 统计测试文件
        test_files = [f for f in code_files if "test" in f.name.lower()]

        if len(code_files) > 5 and len(test_files) == 0:
            result["score"] = 50
            result["issues"].append(
                {"type": "no_tests", "severity": "high", "message": "项目没有测试文件"}
            )
            result["suggestions"].append("建议添加单元测试以确保代码质量")

        test_ratio = len(test_files) / len(code_files) if code_files else 0
        result["stats"]["test_files"] = len(test_files)
        result["stats"]["code_files"] = len(code_files)
        result["stats"]["test_ratio"] = f"{test_ratio:.1%}"

        return result

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _save_quality_report(self, report: Dict[str, Any]):
        """保存质量报告"""
        from lra.config import SafeJson

        SafeJson.write(str(self.quality_report_path), report)

    def generate_quality_report(self) -> str:
        """生成人类可读的质量报告"""
        if not self.quality_report_path.exists():
            return "未找到质量报告，请先运行质量检查"

        from lra.config import SafeJson

        report = SafeJson.read(str(self.quality_report_path))

        if not report:
            return "质量报告为空"

        md_report = f"""# 代码质量报告

**检查时间**: {report.get("timestamp", "N/A")}

## 总体评分

**得分**: {report["score"]}/{report["max_score"]}

"""

        # 评分等级
        score = report["score"]
        if score >= 90:
            grade = "优秀 🌟"
        elif score >= 70:
            grade = "良好 👍"
        elif score >= 60:
            grade = "及格 ⚠️"
        else:
            grade = "不及格 ❌"

        md_report += f"**等级**: {grade}\n\n"

        # 详细检查
        md_report += "## 检查详情\n\n"
        for category, details in report.get("details", {}).items():
            category_name = {
                "documentation": "文档",
                "complexity": "复杂度",
                "naming": "命名",
                "structure": "结构",
                "testing": "测试",
            }.get(category, category)

            md_report += f"### {category_name}\n\n"
            md_report += f"**得分**: {details['score']}/100\n\n"

            if details.get("stats"):
                md_report += "**统计**:\n"
                for key, value in details["stats"].items():
                    md_report += f"- {key}: {value}\n"
                md_report += "\n"

        # 问题列表
        if report.get("issues"):
            md_report += "## 发现的问题\n\n"
            for issue in report["issues"]:
                severity = issue.get("severity", "unknown")
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")

                md_report += f"- {severity_icon} **{issue['type']}**: {issue['message']}"
                if "file" in issue:
                    md_report += f" ({issue['file']})"
                md_report += "\n"
            md_report += "\n"

        # 建议
        if report.get("suggestions"):
            md_report += "## 改进建议\n\n"
            for i, suggestion in enumerate(report["suggestions"], 1):
                md_report += f"{i}. {suggestion}\n"
            md_report += "\n"

        return md_report

    def check_quality_by_template(self, task_id: str, template_name: str) -> Dict[str, Any]:
        """
        按模板检查质量

        参数:
            task_id: 任务ID
            template_name: 模板名称

        返回:
            质量检查结果
        """
        gates = QUALITY_GATES.get(template_name, QUALITY_GATES["task"])

        result = {
            "task_id": task_id,
            "template": template_name,
            "score": 0,
            "max_score": 100,
            "checks": [],
            "failed_required": [],
            "issues": [],
            "suggestions": [],
            "timestamp": self._get_timestamp(),
        }

        check_results = []
        total_weight = 0
        weighted_score = 0

        for gate in gates:
            check_result = self._execute_quality_gate(gate, task_id)
            check_results.append(check_result)

            if check_result["passed"]:
                weighted_score += gate["weight"] * 100
            total_weight += gate["weight"]

            if not check_result["passed"] and gate.get("required", False):
                result["failed_required"].append(gate["type"])

            if check_result.get("issues"):
                result["issues"].extend(check_result["issues"])

            if check_result.get("suggestions"):
                result["suggestions"].extend(check_result["suggestions"])

        result["checks"] = check_results

        if total_weight > 0:
            result["score"] = int(weighted_score / total_weight)

        if result["failed_required"]:
            result["score"] = min(result["score"], 50)

        self.check_results[task_id] = result
        self._save_quality_report(result)

        return result

    def _execute_quality_gate(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """执行单个质量门禁检查"""
        gate_type = gate["type"]

        result = {
            "type": gate_type,
            "required": gate.get("required", False),
            "weight": gate.get("weight", 1.0),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        try:
            if gate_type == "test":
                result = self._check_test_execution(gate, task_id)
            elif gate_type == "lint":
                result = self._check_lint_execution(gate, task_id)
            elif gate_type == "acceptance":
                result = self._check_acceptance_criteria(gate, task_id)
            elif gate_type == "performance":
                result = self._check_performance(gate, task_id)
            elif gate_type == "word_count":
                result = self._check_word_count(gate, task_id)
            elif gate_type == "plot_check":
                result = self._check_plot_coherence(gate, task_id)
            elif gate_type == "style_check":
                result = self._check_writing_style(gate, task_id)
            elif gate_type == "data_integrity":
                result = self._check_data_integrity(gate, task_id)
            elif gate_type == "processing_success":
                result = self._check_processing_success(gate, task_id)
            elif gate_type == "output_validation":
                result = self._check_output_validation(gate, task_id)
            elif gate_type == "completeness":
                result = self._check_documentation_completeness(gate, task_id)
            elif gate_type == "link_validity":
                result = self._check_link_validity(gate, task_id)
            elif gate_type == "format_check":
                result = self._check_format(gate, task_id)
            else:
                code_files = self._collect_code_files()
                if gate_type == "documentation":
                    result = self._check_documentation(code_files)
                elif gate_type == "complexity":
                    result = self._check_complexity(code_files)
                elif gate_type == "naming":
                    result = self._check_naming(code_files)
                elif gate_type == "structure":
                    result = self._check_structure(code_files)
                elif gate_type == "testing":
                    result = self._check_testing(code_files)

            result["passed"] = result.get("score", 0) >= 60

        except Exception as e:
            result["issues"].append(
                {
                    "type": f"{gate_type}_error",
                    "severity": "high",
                    "message": f"检查失败: {str(e)}",
                }
            )

        return result

    def _check_test_execution(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查测试执行"""
        result = {
            "type": "test",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.4),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        try:
            r = subprocess.run(
                ["pytest", "--co", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_path),
            )

            if r.returncode == 0:
                result["score"] = 100
                result["passed"] = True
                result["details"]["tests_found"] = True
            else:
                result["score"] = 0
                result["issues"].append(
                    {
                        "type": "test_not_found",
                        "severity": "high",
                        "message": "未找到测试文件或测试配置错误",
                    }
                )
                result["suggestions"].append("建议添加测试文件到 tests/ 目录")
        except FileNotFoundError:
            result["score"] = 50
            result["suggestions"].append("pytest 未安装，建议运行: pip install pytest")
        except Exception as e:
            result["score"] = 0
            result["issues"].append(
                {
                    "type": "test_error",
                    "severity": "high",
                    "message": f"测试检查失败: {str(e)}",
                }
            )

        return result

    def _check_lint_execution(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查 Lint 执行"""
        result = {
            "type": "lint",
            "required": gate.get("required", False),
            "weight": gate.get("weight", 0.2),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        try:
            r = subprocess.run(
                ["ruff", "check", "--statistics", "."],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_path),
            )

            if r.returncode == 0:
                result["score"] = 100
                result["passed"] = True
                result["details"]["lint_clean"] = True
            else:
                lines = r.stdout.strip().split("\n")
                error_count = len([l for l in lines if l.strip()])
                result["score"] = max(0, 100 - error_count * 5)
                result["issues"].append(
                    {
                        "type": "lint_issues",
                        "severity": "medium",
                        "message": f"发现 {error_count} 个 lint 问题",
                    }
                )
                result["suggestions"].append("建议运行 'ruff check --fix' 自动修复")
        except FileNotFoundError:
            result["score"] = 100
            result["passed"] = True
            result["suggestions"].append("ruff 未安装，建议运行: pip install ruff")
        except Exception as e:
            result["score"] = 50
            result["issues"].append(
                {
                    "type": "lint_error",
                    "severity": "medium",
                    "message": f"Lint 检查失败: {str(e)}",
                }
            )

        return result

    def _check_acceptance_criteria(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查验收标准"""
        result = {
            "type": "acceptance",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.3),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        task_path = Config.get_task_path(task_id)
        if not os.path.exists(task_path):
            result["score"] = 0
            result["issues"].append(
                {
                    "type": "task_not_found",
                    "severity": "high",
                    "message": f"任务文件不存在: {task_id}",
                }
            )
            return result

        try:
            with open(task_path, "r", encoding="utf-8") as f:
                content = f.read()

            acceptance_patterns = [
                r"\[x\].*测试.*",
                r"\[x\].*验证.*",
                r"\[x\].*完成.*",
                r"测试通过",
                r"验证成功",
                r"### 测试命令",
                r"### 测试输出",
            ]

            matched = 0
            for pattern in acceptance_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matched += 1

            result["score"] = min(100, matched * 20)
            result["passed"] = matched >= 3
            result["details"]["criteria_matched"] = matched

            if not result["passed"]:
                result["issues"].append(
                    {
                        "type": "acceptance_incomplete",
                        "severity": "high",
                        "message": "验收标准未满足",
                    }
                )
                result["suggestions"].append("请在任务文件中填写测试命令和测试输出")

        except Exception as e:
            result["score"] = 0
            result["issues"].append(
                {
                    "type": "acceptance_check_error",
                    "severity": "high",
                    "message": f"验收标准检查失败: {str(e)}",
                }
            )

        return result

    def _check_performance(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查性能"""
        result = {
            "type": "performance",
            "required": gate.get("required", False),
            "weight": gate.get("weight", 0.1),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "性能检查需要具体实现"},
        }

        return result

    def _check_word_count(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查字数"""
        result = {
            "type": "word_count",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.4),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        min_words = gate.get("min_words", 2000)

        novel_paths = list(self.project_path.rglob("*.md")) + list(self.project_path.rglob("*.txt"))
        novel_paths = [p for p in novel_paths if ".long-run-agent" not in str(p)]

        if not novel_paths:
            result["score"] = 0
            result["issues"].append(
                {
                    "type": "no_novel_file",
                    "severity": "high",
                    "message": "未找到小说文件",
                }
            )
            return result

        try:
            total_words = 0
            for path in novel_paths[:5]:
                content = path.read_text(encoding="utf-8")
                words = len(content)
                total_words += words

            result["details"]["total_words"] = total_words
            result["details"]["min_words"] = min_words

            if total_words >= min_words:
                result["score"] = 100
                result["passed"] = True
            else:
                ratio = total_words / min_words
                result["score"] = int(ratio * 100)
                result["issues"].append(
                    {
                        "type": "word_count_insufficient",
                        "severity": "high",
                        "message": f"字数不足: {total_words}/{min_words}",
                    }
                )
                result["suggestions"].append(f"建议增加内容，至少需要 {min_words - total_words} 字")

        except Exception as e:
            result["score"] = 0
            result["issues"].append(
                {
                    "type": "word_count_error",
                    "severity": "high",
                    "message": f"字数统计失败: {str(e)}",
                }
            )

        return result

    def _check_plot_coherence(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查情节连贯性"""
        result = {
            "type": "plot_check",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.3),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "情节连贯性检查需要人工审核"},
        }

        return result

    def _check_writing_style(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查写作风格"""
        result = {
            "type": "style_check",
            "required": gate.get("required", False),
            "weight": gate.get("weight", 0.2),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "写作风格检查需要人工审核"},
        }

        return result

    def _check_data_integrity(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查数据完整性"""
        result = {
            "type": "data_integrity",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.4),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        data_dirs = ["data", "output", "results"]
        found_data = False

        for data_dir in data_dirs:
            dir_path = self.project_path / data_dir
            if dir_path.exists() and dir_path.is_dir():
                files = list(dir_path.rglob("*"))
                if files:
                    found_data = True
                    break

        if found_data:
            result["score"] = 100
            result["passed"] = True
            result["details"]["data_found"] = True
        else:
            result["score"] = 50
            result["issues"].append(
                {
                    "type": "no_data_found",
                    "severity": "medium",
                    "message": "未找到数据输出目录",
                }
            )
            result["suggestions"].append("建议在 data/ 或 output/ 目录中存放处理结果")

        return result

    def _check_processing_success(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查处理成功率"""
        result = {
            "type": "processing_success",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.3),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "处理成功率需要日志分析"},
        }

        return result

    def _check_output_validation(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查输出验证"""
        result = {
            "type": "output_validation",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.3),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "输出验证需要具体实现"},
        }

        return result

    def _check_documentation_completeness(
        self, gate: Dict[str, Any], task_id: str
    ) -> Dict[str, Any]:
        """检查文档完整性"""
        result = {
            "type": "completeness",
            "required": gate.get("required", True),
            "weight": gate.get("weight", 0.4),
            "passed": False,
            "score": 0,
            "issues": [],
            "suggestions": [],
            "details": {},
        }

        doc_files = []
        for pattern in ["*.md", "*.rst", "*.txt"]:
            doc_files.extend(self.project_path.rglob(pattern))

        doc_files = [f for f in doc_files if ".git" not in str(f) and "node_modules" not in str(f)]

        readme_exists = (self.project_path / "README.md").exists()

        if readme_exists and len(doc_files) > 0:
            result["score"] = 100
            result["passed"] = True
            result["details"]["doc_files_count"] = len(doc_files)
        else:
            result["score"] = 50 if readme_exists else 0
            result["issues"].append(
                {
                    "type": "incomplete_docs",
                    "severity": "medium",
                    "message": "文档不完整",
                }
            )
            result["suggestions"].append("建议添加 README.md 和相关文档")

        return result

    def _check_link_validity(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查链接有效性"""
        result = {
            "type": "link_validity",
            "required": gate.get("required", False),
            "weight": gate.get("weight", 0.3),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "链接有效性检查需要网络请求"},
        }

        return result

    def _check_format(self, gate: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检查格式"""
        result = {
            "type": "format_check",
            "required": gate.get("required", False),
            "weight": gate.get("weight", 0.3),
            "passed": True,
            "score": 100,
            "issues": [],
            "suggestions": [],
            "details": {"note": "格式检查需要具体实现"},
        }

        return result

    def generate_optimization_hints(self, task_id: str) -> List[Dict[str, Any]]:
        """
        生成优化建议

        参数:
            task_id: 任务ID

        返回:
            优化建议列表
        """
        hints = []

        result = self.check_results.get(task_id)
        if not result:
            report = SafeJson.read(str(self.quality_report_path))
            if report and report.get("task_id") == task_id:
                result = report

        if not result:
            return [{"type": "no_data", "message": "未找到质量检查数据"}]

        for check in result.get("checks", []):
            if not check.get("passed", False):
                hint = self._generate_hint_for_failed_check(check)
                if hint:
                    hints.append(hint)

        for issue in result.get("issues", []):
            hint = {
                "type": "issue_hint",
                "severity": issue.get("severity", "medium"),
                "issue_type": issue["type"],
                "message": issue.get("message", ""),
                "suggestions": result.get("suggestions", []),
            }
            hints.append(hint)

        return hints

    def _generate_hint_for_failed_check(self, check: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """为失败的检查生成提示"""
        check_type = check.get("type")

        if not check_type:
            return None

        hints_map = {
            "test": {
                "type": "test_hint",
                "action": "运行测试",
                "command": "pytest tests/ -v",
                "file_path": "tests/",
                "description": "添加单元测试并确保所有测试通过",
            },
            "lint": {
                "type": "lint_hint",
                "action": "修复代码风格",
                "command": "ruff check --fix .",
                "file_path": ".",
                "description": "运行 ruff 自动修复代码风格问题",
            },
            "acceptance": {
                "type": "acceptance_hint",
                "action": "完善验收标准",
                "file_path": Config.get_task_path(""),
                "description": "在任务文件中填写测试命令、测试输出和验证步骤",
            },
            "word_count": {
                "type": "word_count_hint",
                "action": "增加内容",
                "description": "扩充章节内容，增加场景描写和人物对话",
            },
            "data_integrity": {
                "type": "data_hint",
                "action": "验证数据",
                "file_path": "data/",
                "description": "确保数据处理流程正确，输出数据完整",
            },
            "completeness": {
                "type": "doc_hint",
                "action": "完善文档",
                "file_path": "README.md",
                "description": "添加或更新文档，包括安装说明和使用示例",
            },
        }

        return hints_map.get(check_type)

    def calculate_quality_score(self, checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算综合质量分

        参数:
            checks: 检查项列表

        返回:
            质量评分详情
        """
        if not checks:
            return {
                "score": 0,
                "max_score": 100,
                "passed_required": True,
                "weight_sum": 0,
                "weighted_score": 0,
            }

        total_weight = sum(c.get("weight", 1.0) for c in checks)
        weighted_score = 0
        passed_required = True

        for check in checks:
            weight = check.get("weight", 1.0)
            score = check.get("score", 0)
            required = check.get("required", False)
            passed = check.get("passed", False)

            weighted_score += weight * score

            if required and not passed:
                passed_required = False

        final_score = int(weighted_score / total_weight) if total_weight > 0 else 0

        if not passed_required:
            final_score = min(final_score, 50)

        return {
            "score": final_score,
            "max_score": 100,
            "passed_required": passed_required,
            "weight_sum": total_weight,
            "weighted_score": weighted_score,
            "check_count": len(checks),
        }

    def get_failed_checks(self, task_id: str) -> List[Dict[str, Any]]:
        """
        获取失败的检查项

        参数:
            task_id: 任务ID

        返回:
            失败的检查项列表
        """
        result = self.check_results.get(task_id)
        if not result:
            report = SafeJson.read(str(self.quality_report_path))
            if report and report.get("task_id") == task_id:
                result = report

        if not result:
            return []

        failed = []
        for check in result.get("checks", []):
            if not check.get("passed", False):
                failed.append(
                    {
                        "type": check.get("type"),
                        "required": check.get("required", False),
                        "weight": check.get("weight", 1.0),
                        "score": check.get("score", 0),
                        "issues": check.get("issues", []),
                        "suggestions": check.get("suggestions", []),
                    }
                )

        return failed

    def get_supported_templates(self) -> List[str]:
        """获取支持的模板列表"""
        return list(QUALITY_GATES.keys())

    def get_quality_gates(self, template_name: str) -> List[Dict[str, Any]]:
        """
        获取指定模板的质量门禁配置

        参数:
            template_name: 模板名称

        返回:
            质量门禁配置列表
        """
        return QUALITY_GATES.get(template_name, QUALITY_GATES["task"])
