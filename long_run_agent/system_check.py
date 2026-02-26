#!/usr/bin/env python3
"""
系统预检任务
v3.3.0 - Agent 自治式初始化预检

核心功能:
- 代码规模统计
- Git 信息分析
- 文档覆盖率计算
- 函数注释分析
- 自动决策（全量/增量）
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from git import Repo

    HAS_GIT = True
except ImportError:
    HAS_GIT = False

from .config import Config, SafeJson


class SystemCheckTask:
    """系统预检任务执行器"""

    # 默认阈值配置
    DEFAULT_THRESHOLDS = {
        "code_size_mb": 5.0,  # 代码体积阈值 (MB)
        "git_valid_ratio": 0.3,  # Git 规范提交占比
        "doc_coverage_ratio": 0.4,  # 文档覆盖率
        "func_comment_ratio": 0.2,  # 函数注释占比
    }

    def __init__(self, project_path: str = None, config: Dict[str, Any] = None):
        self.project_path = project_path or os.getcwd()
        self.config = config or self._load_config()
        self.thresholds = self.config.get("system_check", {}).get(
            "thresholds", self.DEFAULT_THRESHOLDS
        )
        self.report = {
            "project_id": self._get_project_id(),
            "check_time": datetime.now().isoformat(),
        }

    def _get_project_id(self) -> str:
        """获取项目 ID"""
        return os.path.basename(self.project_path)

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(self.project_path, ".long-run-agent", "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except:
                pass
        return {}

    def calculate_code_size(self) -> Dict[str, Any]:
        """计算代码总大小（MB），仅统计代码文件"""
        code_extensions = [".py", ".java", ".js", ".ts", ".go", ".cpp", ".c", ".rs", ".rb"]
        total_size = 0
        file_count = 0

        for root, _, files in os.walk(self.project_path):
            # 跳过隐藏目录和常见忽略目录
            if any(
                skip in root
                for skip in [".git", "node_modules", "__pycache__", ".venv", "dist", "build"]
            ):
                continue

            for file in files:
                if any(file.endswith(ext) for ext in code_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except:
                        pass

        size_mb = total_size / (1024 * 1024)
        self.report["code_total_size_mb"] = round(size_mb, 2)
        self.report["code_file_count"] = file_count

        return {
            "size_mb": round(size_mb, 2),
            "file_count": file_count,
        }

    def analyze_git_log(self) -> Dict[str, Any]:
        """分析 Git 有效提交占比"""
        if not HAS_GIT:
            self.report["git_valid_ratio"] = 0
            self.report["git_error"] = "GitPython not installed"
            return {"valid_ratio": 0, "error": "GitPython not installed"}

        try:
            repo = Repo(self.project_path)
            commits = list(repo.iter_commits(max_count=1000))

            if not commits:
                self.report["git_valid_ratio"] = 0
                self.report["git_total_commits"] = 0
                return {"valid_ratio": 0, "total": 0}

            valid_commits = 0
            commit_types = {"feat": 0, "fix": 0, "refactor": 0, "docs": 0, "test": 0, "other": 0}

            # 匹配规范的 commit message：feat(模块)/fix(模块)/refactor(模块)
            pattern = re.compile(r"^(feat|fix|refactor|docs|test)(\(\w+\))?: .+")

            for commit in commits:
                message = commit.message.strip()
                match = pattern.match(message)
                if match:
                    commit_type = match.group(1)
                    commit_types[commit_type] += 1
                    valid_commits += 1
                else:
                    commit_types["other"] += 1

            valid_ratio = valid_commits / len(commits) if commits else 0
            self.report["git_valid_ratio"] = round(valid_ratio, 2)
            self.report["git_total_commits"] = len(commits)
            self.report["git_commit_types"] = commit_types

            return {
                "valid_ratio": round(valid_ratio, 2),
                "total": len(commits),
                "types": commit_types,
            }

        except Exception as e:
            self.report["git_valid_ratio"] = 0
            self.report["git_error"] = str(e)
            return {"valid_ratio": 0, "error": str(e)}

    def calculate_doc_coverage(self) -> Dict[str, Any]:
        """计算文档覆盖率"""
        doc_extensions = [".md", ".rst", ".txt"]
        code_modules = set()
        doc_modules = set()

        # 提取代码模块（按文件名）
        for root, _, files in os.walk(self.project_path):
            # 跳过隐藏目录
            if any(
                skip in root
                for skip in [".git", "node_modules", "__pycache__", ".venv", "dist", "build"]
            ):
                continue

            for file in files:
                if file.endswith(".py"):
                    module = file.replace(".py", "")
                    code_modules.add(module)

        # 提取文档对应的模块
        for root, _, files in os.walk(self.project_path):
            if any(
                skip in root
                for skip in [".git", "node_modules", "__pycache__", ".venv", "dist", "build"]
            ):
                continue

            for file in files:
                if any(file.endswith(ext) for ext in doc_extensions):
                    # 文档名匹配模块名：payment.md → payment
                    module = os.path.splitext(file)[0]
                    doc_modules.add(module)

        # 计算覆盖率
        matched = code_modules & doc_modules
        coverage = len(matched) / len(code_modules) if code_modules else 0

        self.report["doc_coverage_ratio"] = round(coverage, 2)
        self.report["doc_code_modules"] = len(code_modules)
        self.report["doc_modules"] = len(doc_modules)
        self.report["doc_matched_modules"] = len(matched)

        return {
            "coverage": round(coverage, 2),
            "code_modules": len(code_modules),
            "doc_modules": len(doc_modules),
            "matched": len(matched),
        }

    def analyze_func_comments(self) -> Dict[str, Any]:
        """分析函数注释占比（简化版：统计有 docstring 的函数）"""
        total_funcs = 0
        commented_funcs = 0

        for root, _, files in os.walk(self.project_path):
            if any(
                skip in root
                for skip in [".git", "node_modules", "__pycache__", ".venv", "dist", "build"]
            ):
                continue

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # 简单统计：查找 def 关键字和紧随的 docstring
                        func_pattern = re.compile(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", re.MULTILINE)
                        docstring_pattern = re.compile(r'"""\s*.+?\s*"""', re.DOTALL)

                        functions = func_pattern.findall(content)
                        total_funcs += len(functions)

                        # 统计有 docstring 的函数（简化：假设有 docstring 就算有注释）
                        docstrings = docstring_pattern.findall(content)
                        commented_funcs += min(len(docstrings), len(functions))

                    except:
                        pass

        ratio = commented_funcs / total_funcs if total_funcs else 0
        self.report["func_comment_ratio"] = round(ratio, 2)
        self.report["func_total"] = total_funcs
        self.report["func_commented"] = commented_funcs

        return {
            "ratio": round(ratio, 2),
            "total": total_funcs,
            "commented": commented_funcs,
        }

    def make_decision(self, force_full: bool = False) -> Tuple[str, str]:
        """基于指标生成决策：full/incremental

        Args:
            force_full: 是否强制全量解析，默认为 False
        """
        if force_full:
            self.report["decision"] = "full"
            self.report["reason"] = "强制全量解析模式"
            return "full", self.report["reason"]

        reasons = []
        satisfied_conditions = []
        decision = "incremental"

        # 检查各项指标（OR 逻辑：只要有一条满足就可以全量分析）
        if self.report.get("code_total_size_mb", 0) <= self.thresholds.get("code_size_mb", 5.0):
            satisfied_conditions.append(
                f"代码体积{self.report['code_total_size_mb']}MB ≤ {self.thresholds['code_size_mb']}MB"
            )
        else:
            reasons.append(
                f"代码体积{self.report['code_total_size_mb']}MB > {self.thresholds['code_size_mb']}MB"
            )

        if self.report.get("doc_coverage_ratio", 0) >= self.thresholds.get(
            "doc_coverage_ratio", 0.4
        ):
            satisfied_conditions.append(
                f"文档覆盖率{self.report['doc_coverage_ratio']:.0%} ≥ {self.thresholds['doc_coverage_ratio']:.0%}"
            )
        else:
            reasons.append(
                f"文档覆盖率{self.report['doc_coverage_ratio']:.0%} < {self.thresholds['doc_coverage_ratio']:.0%}"
            )

        if self.report.get("git_valid_ratio", 0) >= self.thresholds.get("git_valid_ratio", 0.3):
            satisfied_conditions.append(
                f"Git 规范提交{self.report['git_valid_ratio']:.0%} ≥ {self.thresholds['git_valid_ratio']:.0%}"
            )
        else:
            reasons.append(
                f"Git 规范提交{self.report['git_valid_ratio']:.0%} < {self.thresholds['git_valid_ratio']:.0%}"
            )

        # OR 逻辑：只要有一个条件满足就可以全量分析
        if satisfied_conditions:
            decision = "full"

        if decision == "full":
            self.report["decision"] = "full"
            self.report["reason"] = "，".join(satisfied_conditions) + "，全量解析"
            if reasons:
                self.report["reason"] += f"（未满足：{','.join(reasons)}）"
        else:
            self.report["decision"] = "incremental"
            self.report["reason"] = "所有条件均不满足（" + "，".join(reasons) + "），触发增量处理"

        return decision, self.report["reason"]

    def generate_suggestions(self) -> List[str]:
        """生成建议"""
        suggestions = []

        if self.report.get("decision") == "incremental":
            if self.report.get("code_total_size_mb", 0) > 5:
                suggestions.append("分模块分析代码，优先处理核心模块")

            if self.report.get("doc_coverage_ratio", 0) < 0.4:
                suggestions.append("内置任务要求 Agent 同步更新模块文档")

            suggestions.append("按用户需求范围动态生成子任务，避免全量 Token 消耗")

        return suggestions

    def run(self, force_full: bool = False) -> Dict[str, Any]:
        """执行全量预检，生成报告

        Args:
            force_full: 是否强制全量解析，默认为 False
        """
        # 执行各项检测
        self.calculate_code_size()
        self.analyze_git_log()
        self.calculate_doc_coverage()
        self.analyze_func_comments()

        # 生成决策
        self.make_decision(force_full=force_full)

        # 生成建议
        self.report["suggestions"] = self.generate_suggestions()

        # 保存报告
        self.save_report()

        return self.report

    def save_report(self) -> str:
        """保存报告到文件"""
        reports_dir = os.path.join(self.project_path, ".long-run-agent", "reports")
        os.makedirs(reports_dir, exist_ok=True)

        report_path = os.path.join(reports_dir, "sys_check_001.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

        return report_path

    def get_report(self) -> Dict[str, Any]:
        """获取报告"""
        return self.report

    def is_incremental(self) -> bool:
        """是否需要增量处理"""
        return self.report.get("decision") == "incremental"


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG = {
        "system_check": {
            "thresholds": {
                "code_size_mb": 5.0,
                "git_valid_ratio": 0.3,
                "doc_coverage_ratio": 0.4,
                "func_comment_ratio": 0.2,
            },
            "auto_check_on_init": True,
            "auto_check_on_first_task": True,
            "doc_enforcement": "strict",  # strict | soft | disabled
        }
    }

    @classmethod
    def get_config_path(cls, project_path: str = None) -> str:
        """获取配置文件路径"""
        project_path = project_path or os.getcwd()
        return os.path.join(project_path, ".long-run-agent", "config.yaml")

    @classmethod
    def load_config(cls, project_path: str = None) -> Dict[str, Any]:
        """加载配置"""
        config_path = cls.get_config_path(project_path)
        if os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or cls.DEFAULT_CONFIG
            except:
                return cls.DEFAULT_CONFIG
        return cls.DEFAULT_CONFIG

    @classmethod
    def save_config(cls, config: Dict[str, Any], project_path: str = None) -> str:
        """保存配置"""
        import yaml

        config_path = cls.get_config_path(project_path)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        return config_path

    @classmethod
    def init_config(cls, project_path: str = None) -> str:
        """初始化配置文件"""
        config_path = cls.get_config_path(project_path)
        if os.path.exists(config_path):
            return config_path

        return cls.save_config(cls.DEFAULT_CONFIG, project_path)
