"""
Constitution - 项目宪法管理器
定义和验证项目的不可协商原则和质量标准

v1.0 - 初始实现
"""

import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class PrincipleType(Enum):
    """原则类型"""

    NON_NEGOTIABLE = "NON_NEGOTIABLE"  # 不可协商
    MANDATORY = "MANDATORY"  # 强制
    CONFIGURABLE = "CONFIGURABLE"  # 可配置


class GateType(Enum):
    """门禁类型"""

    COMMAND = "command"  # 命令门禁
    FIELD_EXISTS = "field_exists"  # 字段存在门禁
    CUSTOM = "custom"  # 自定义门禁


@dataclass
class Gate:
    """门禁定义"""

    type: str
    name: str
    required: bool = True
    weight: float = 1.0
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Principle:
    """原则定义"""

    id: str
    type: str
    name: str
    description: str
    gates: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ValidationResult:
    """验证结果"""

    passed: bool
    message: str = ""
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    gate_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GateResult:
    """门禁检查结果"""

    passed: bool
    gate_name: str
    message: str = ""
    output: str = ""
    exit_code: int = 0
    weight: float = 1.0
    required: bool = True


class ConstitutionManager:
    """Constitution管理器"""

    DEFAULT_CONSTITUTION = {
        "schema_version": "1.0",
        "project": {
            "name": "Default Project",
            "description": "Default Constitution for projects without explicit constitution",
            "ratified": "2024-03-09",
            "version": "1.0.0",
        },
        "core_principles": [
            {
                "id": "quality_first",
                "type": "MANDATORY",
                "name": "质量优先",
                "description": "任务完成前应确保基本质量",
                "gates": [],
            },
            {
                "id": "deliverables_exist",
                "type": "NON_NEGOTIABLE",
                "name": "交付物必须存在",
                "description": "任务文件中列出的交付物文件必须实际存在",
                "gates": [
                    {
                        "type": "custom",
                        "name": "deliverables_exist",
                        "check_func": "check_deliverables_exist",
                        "check_level": "basic",
                        # v6.0: check file is not empty and has code patterns
                        "required": True,
                        "description": "检查 deliverables 中的文件是否存在且包含代码",
                    }
                ],
            },
        ],
        "template_gates": {},
        "amendments": [],
    }

    def __init__(self):
        """初始化Constitution管理器"""
        self.constitution_path = self._get_constitution_path()
        self.constitution = self._load_constitution()
        self._validate_constitution()

    def _get_constitution_path(self) -> Path:
        """获取Constitution文件路径"""
        from lra.config import Config

        return Path(Config.get_config_dir()) / "constitution.yaml"

    def _load_constitution(self) -> Dict[str, Any]:
        """加载Constitution配置"""
        if not self.constitution_path.exists():
            return self.DEFAULT_CONSTITUTION.copy()

        try:
            with open(self.constitution_path, encoding="utf-8") as f:
                constitution = yaml.safe_load(f)
                return constitution if constitution else self.DEFAULT_CONSTITUTION.copy()
        except Exception as e:
            print(f"⚠️  加载Constitution失败: {e}")
            return self.DEFAULT_CONSTITUTION.copy()

    def _validate_constitution(self):
        """验证Constitution配置完整性"""
        required_fields = ["schema_version", "core_principles"]

        for req_field in required_fields:
            if req_field not in self.constitution:
                raise ValueError(f"Constitution缺少必需字段: {field}")

        # 验证原则结构
        for principle in self.constitution.get("core_principles", []):
            if "id" not in principle or "type" not in principle:
                raise ValueError(f"原则缺少必需字段: {principle}")

    def get_principle(self, principle_id: str) -> Optional[Dict[str, Any]]:
        """获取指定原则"""
        for principle in self.constitution.get("core_principles", []):
            if principle.get("id") == principle_id:
                return principle
        return None

    def get_principles_by_type(self, principle_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的所有原则"""
        return [
            p
            for p in self.constitution.get("core_principles", [])
            if p.get("type") == principle_type
        ]

    def get_non_negotiable_principles(self) -> List[Dict[str, Any]]:
        """获取所有不可协商原则"""
        return self.get_principles_by_type("NON_NEGOTIABLE")

    def get_mandatory_principles(self) -> List[Dict[str, Any]]:
        """获取所有强制原则"""
        return self.get_principles_by_type("MANDATORY")

    def get_enabled_configurable_principles(self) -> List[Dict[str, Any]]:
        """获取所有启用的可配置原则"""
        configurables = self.get_principles_by_type("CONFIGURABLE")
        return [p for p in configurables if p.get("enabled", False)]

    def get_template_gates(self, template: str, stage: str) -> List[Dict[str, Any]]:
        """获取模板特定门禁"""
        template_gates = self.constitution.get("template_gates", {})
        return template_gates.get(template, {}).get(stage, [])

    def get_iteration_gates(self, iteration: int) -> List[Dict[str, Any]]:
        """获取迭代阶段门禁（轻量级检查，每个迭代阶段运行）"""
        iteration_gates = self.constitution.get("iteration_gates", {})
        # iteration_gates 结构: {1: [gates], 2: [gates], ...}
        gates = iteration_gates.get(iteration, [])
        if not gates:
            # 如果没有配置，使用默认门禁
            defaults = self.get_default_iteration_gates()
            gates = defaults.get(iteration, [])
        return gates

    def get_default_iteration_gates(self) -> Dict[int, List[Dict[str, Any]]]:
        """获取默认的迭代阶段门禁。

        框架不硬编码语言相关的工具命令，由 Agent 自主根据项目类型选择工具。
        如需配置，在 constitution.yaml 的 iteration_gates 中定义。
        """
        return {}

    def get_all_applicable_principles(self, template: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有适用原则"""
        principles = []

        # 不可协商原则
        principles.extend(self.get_non_negotiable_principles())

        # 强制原则
        principles.extend(self.get_mandatory_principles())

        # 启用的可配置原则
        principles.extend(self.get_enabled_configurable_principles())

        # 模板特定门禁
        if template:
            template_gates = self.get_template_gates(template, "pre_completion")
            if template_gates:
                principles.append(
                    {
                        "id": f"template_{template}",
                        "type": "MANDATORY",
                        "name": f"{template}模板门禁",
                        "description": f"{template}模板特定门禁",
                        "gates": template_gates,
                    }
                )

        return principles

    def reload(self):
        """重新加载Constitution"""
        self.constitution = self._load_constitution()
        self._validate_constitution()


class GateEvaluator:
    """门禁评估器"""

    ALLOWED_COMMANDS = [
        "pytest",
        "python",
        "ruff",
        "mypy",
        "eslint",
        "npm",
        "yarn",
        "pip",
        "coverage",
        "black",
        "flake8",
    ]

    def evaluate_gate(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """评估单个门禁"""
        gate_type = gate_config.get("type")
        gate_name = gate_config.get("name", "unnamed_gate")
        required = gate_config.get("required", True)
        weight = gate_config.get("weight", 1.0)

        try:
            if gate_type == "command":
                result = self._evaluate_command_gate(gate_config, task_id, task)
            elif gate_type == "field_exists":
                result = self._evaluate_field_gate(gate_config, task_id, task)
            elif gate_type == "custom":
                result = self._evaluate_custom_gate(gate_config, task_id, task)
            else:
                result = GateResult(
                    passed=False,
                    gate_name=gate_name,
                    message=f"未知门禁类型: {gate_type}",
                    required=required,
                    weight=weight,
                )

            result.required = required
            result.weight = weight
            return result

        except Exception as e:
            return GateResult(
                passed=False,
                gate_name=gate_name,
                message=f"门禁评估异常: {str(e)}",
                required=required,
                weight=weight,
            )

    def _evaluate_command_gate(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """评估命令门禁"""
        command = gate_config.get("command")
        gate_name = gate_config.get("name", "command_gate")

        if not command:
            return GateResult(passed=False, gate_name=gate_name, message="命令门禁缺少command字段")

        # 安全检查：白名单
        cmd_name = command.split()[0] if command else ""
        if cmd_name not in self.ALLOWED_COMMANDS:
            return GateResult(
                passed=False, gate_name=gate_name, message=f"命令不在白名单中: {cmd_name}"
            )

        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)

            passed = result.returncode == 0

            return GateResult(
                passed=passed,
                gate_name=gate_name,
                message=f"命令执行{'成功' if passed else '失败'}",
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return GateResult(
                passed=False, gate_name=gate_name, message=f"命令执行超时(60s): {command}"
            )
        except Exception as e:
            return GateResult(passed=False, gate_name=gate_name, message=f"命令执行异常: {str(e)}")

    def _evaluate_field_gate(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """评估字段存在门禁"""
        field_name = gate_config.get("field")
        gate_name = gate_config.get("name", "field_gate")

        if not field_name:
            return GateResult(passed=False, gate_name=gate_name, message="字段门禁缺少field字段")

        # 检查任务文件中是否存在该字段
        from lra.config import Config

        task_file = Path(Config.get_task_path(task_id))

        if not task_file.exists():
            return GateResult(
                passed=False, gate_name=gate_name, message=f"任务文件不存在: {task_id}"
            )

        try:
            content = task_file.read_text(encoding="utf-8")

            # 简单的字段检查：查找字段名或markdown标题
            if (
                field_name in content
                or f"## {field_name}" in content
                or f"### {field_name}" in content
            ):
                return GateResult(
                    passed=True, gate_name=gate_name, message=f"字段存在: {field_name}"
                )
            else:
                return GateResult(
                    passed=False, gate_name=gate_name, message=f"字段缺失: {field_name}"
                )

        except Exception as e:
            return GateResult(passed=False, gate_name=gate_name, message=f"文件读取异常: {str(e)}")

    def _evaluate_custom_gate(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """评估自定义门禁"""
        gate_name = gate_config.get("name", "custom_gate")
        check_func = gate_config.get("check_func")

        if not check_func:
            return GateResult(passed=False, gate_name=gate_name, message="自定义门禁缺少check_func")

        # 内置自定义检查函数
        builtin_checks = {
            "validate_constitution_yaml": self._check_constitution_yaml,
            "check_test_coverage": self._check_test_coverage,
            "check_deliverables_exist": self._check_deliverables_exist,
        }

        if check_func in builtin_checks:
            return builtin_checks[check_func](gate_config, task_id, task)

        # 尝试动态导入
        try:
            # TODO: 实现动态函数加载
            return GateResult(
                passed=False, gate_name=gate_name, message=f"自定义检查函数未实现: {check_func}"
            )
        except Exception as e:
            return GateResult(
                passed=False, gate_name=gate_name, message=f"自定义门禁执行失败: {str(e)}"
            )

    def _check_constitution_yaml(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """检查Constitution YAML格式"""
        from lra.config import Config

        constitution_path = Path(Config.get_config_dir()) / "constitution.yaml"

        if not constitution_path.exists():
            return GateResult(
                passed=False, gate_name="constitution_validation", message="Constitution文件不存在"
            )

        try:
            with open(constitution_path, encoding="utf-8") as f:
                yaml.safe_load(f)

            return GateResult(
                passed=True,
                gate_name="constitution_validation",
                message="Constitution YAML格式正确",
            )
        except yaml.YAMLError as e:
            return GateResult(
                passed=False,
                gate_name="constitution_validation",
                message=f"Constitution YAML格式错误: {str(e)}",
            )

    def _check_test_coverage(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """检查测试覆盖率"""
        min_coverage = gate_config.get("min_coverage", 80)

        try:
            result = subprocess.run(
                f"pytest --cov=lra --cov-report=term-missing --cov-fail-under={min_coverage}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )

            passed = result.returncode == 0

            return GateResult(
                passed=passed,
                gate_name="test_coverage",
                message=f"覆盖率{'达到' if passed else '未达到'} {min_coverage}%",
                output=result.stdout,
            )
        except Exception as e:
            return GateResult(
                passed=False, gate_name="test_coverage", message=f"覆盖率检查异常: {str(e)}"
            )

    def _check_deliverables_exist(
        self, gate_config: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> GateResult:
        """检查 deliverables 中的文件是否实际存在

        Args:
            gate_config: 门禁配置，支持 check_level:
                - "none": 只检查文件存在（默认）
                - "nonempty": 文件必须非空
                - "basic": 非空 + 检查代码基本模式
        """
        import os

        from lra.config import Config

        # 获取检查级别
        check_level = gate_config.get("check_level", "none")

        # 读取任务文件获取 deliverables
        task_dir = Config.get_tasks_dir()
        task_path = os.path.join(task_dir, f"{task_id}.md")

        if not os.path.exists(task_path):
            return GateResult(
                passed=False, gate_name="deliverables_exist", message=f"任务文件不存在: {task_path}"
            )

        try:
            with open(task_path, encoding="utf-8") as f:
                content = f.read()

            # 提取 deliverables 部分
            deliverables = []
            if "## 交付物 (deliverables)" in content:
                section = content.split("## 交付物 (deliverables)")[1].split("##")[0]
                for line in section.split("\n"):
                    if line.strip().startswith("- "):
                        file_path = line.strip()[2:].strip()
                        if file_path and not file_path.startswith("["):
                            deliverables.append(file_path)
            elif "## deliverables" in content.lower():
                section = content.split("## deliverables")[1].split("##")[0]
                for line in section.split("\n"):
                    if line.strip().startswith("- "):
                        file_path = line.strip()[2:].strip()
                        if file_path and not file_path.startswith("["):
                            deliverables.append(file_path)

            # 检查文件是否存在
            project_root = os.getcwd()
            missing_files = []
            empty_files = []
            invalid_files = []
            existing_files = []

            for d in deliverables:
                # 跳过占位符
                if d.startswith("[") or "交付物" in d or "在此填写" in d:
                    continue
                # 支持相对路径
                file_path = d if os.path.isabs(d) else os.path.join(project_root, d)
                if not os.path.exists(file_path):
                    missing_files.append(d)
                else:
                    existing_files.append(d)

                    # 根据 check_level 进行额外检查
                    if check_level in ("nonempty", "basic"):
                        if os.path.getsize(file_path) == 0:
                            empty_files.append(d)
                            continue

                        if check_level == "basic" and self._is_code_file(file_path):
                            if not self._has_basic_code_patterns(open(file_path).read()):
                                invalid_files.append(d)

            # 汇总错误
            all_errors = missing_files.copy()
            if check_level == "nonempty":
                all_errors.extend(empty_files)
            elif check_level == "basic":
                all_errors.extend(empty_files)
                all_errors.extend(invalid_files)

            if all_errors:
                error_msg = []
                if missing_files:
                    error_msg.append(f"缺失: {', '.join(missing_files)}")
                if empty_files:
                    error_msg.append(f"空文件: {', '.join(empty_files)}")
                if invalid_files:
                    error_msg.append(f"无代码模式: {', '.join(invalid_files)}")

                return GateResult(
                    passed=False,
                    gate_name="deliverables_exist",
                    message=f"交付物问题: {'; '.join(error_msg)}",
                    output=f"存在的文件: {', '.join(existing_files) if existing_files else '无'}",
                )

            return GateResult(
                passed=True,
                gate_name="deliverables_exist",
                message=f"所有交付物文件已创建 ({len(existing_files)} 个)"
                + (f", 内容检查通过 ({check_level})" if check_level != "none" else ""),
                output=f"交付物: {', '.join(existing_files)}",
            )

        except Exception as e:
            return GateResult(
                passed=False, gate_name="deliverables_exist", message=f"检查交付物时异常: {str(e)}"
            )

    def _is_code_file(self, filepath: str) -> bool:
        """检查文件是否是代码文件"""
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".go",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".rs",
            ".rb",
            ".php",
            ".cs",
            ".swift",
            ".kt",
            ".scala",
            ".lua",
            ".sh",
        }
        return Path(filepath).suffix in code_extensions

    def _has_basic_code_patterns(self, content: str) -> bool:
        """检查内容是否包含基本代码模式"""
        patterns = [
            r"^(import|from)\s+",  # Python imports
            r"^(export|const|let|var|function|class)\s+",  # JS/TS
            r"^def\s+",  # Python function
            r"^class\s+",  # Class definition
            r"^func\s+",  # Go function
            r"^fn\s+",  # Rust function
            r"^public\s+",  # Java public
            r"^private\s+",  # Java private
            r"^package\s+",  # Java package
        ]
        # Check for actual code patterns (not just comments)
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False


class PrincipleValidator:
    """原则验证器"""

    def __init__(self, constitution_manager: ConstitutionManager):
        self.constitution = constitution_manager
        self.gate_evaluator = GateEvaluator()

    def validate_principle(
        self, principle: Dict[str, Any], task_id: str, task: Dict[str, Any]
    ) -> ValidationResult:
        """验证单个原则"""
        principle_type = principle.get("type")
        principle_name = principle.get("name", "unnamed")

        # 可配置原则未启用，直接通过
        if principle_type == "CONFIGURABLE" and not principle.get("enabled", False):
            return ValidationResult(passed=True, message=f"可配置原则未启用: {principle_name}")

        gates = principle.get("gates", [])

        if not gates:
            return ValidationResult(passed=True, message=f"原则无门禁: {principle_name}")

        gate_results = []
        failures = []
        warnings = []

        for gate_config in gates:
            result = self.gate_evaluator.evaluate_gate(gate_config, task_id, task)
            gate_results.append(
                {
                    "gate_name": result.gate_name,
                    "passed": result.passed,
                    "message": result.message,
                    "required": result.required,
                    "weight": result.weight,
                }
            )

            if not result.passed:
                if result.required:
                    failures.append(f"{result.gate_name}: {result.message}")
                else:
                    warnings.append(f"{result.gate_name}: {result.message}")

        # 不可协商原则：所有必需门禁必须通过
        if principle_type == "NON_NEGOTIABLE":
            passed = len(failures) == 0
        # 强制和可配置原则：必需门禁必须通过
        else:
            passed = len(failures) == 0

        return ValidationResult(
            passed=passed,
            message=f"原则{'验证通过' if passed else '验证失败'}: {principle_name}",
            failures=failures,
            warnings=warnings,
            gate_results=gate_results,
        )

    def validate_all_principles(
        self, task_id: str, task: Dict[str, Any], template: Optional[str] = None
    ) -> ValidationResult:
        """验证所有适用原则"""
        principles = self.constitution.get_all_applicable_principles(template)

        all_failures = []
        all_warnings = []
        all_gate_results = []

        for principle in principles:
            result = self.validate_principle(principle, task_id, task)

            all_failures.extend(result.failures)
            all_warnings.extend(result.warnings)
            all_gate_results.extend(result.gate_results)

        # 只要有一个不可协商原则失败，整体就不通过
        non_negotiable_failed = False
        for principle in principles:
            if principle.get("type") == "NON_NEGOTIABLE":
                principle_result = self.validate_principle(principle, task_id, task)
                if not principle_result.passed:
                    non_negotiable_failed = True
                    break

        passed = not non_negotiable_failed and len(all_failures) == 0

        return ValidationResult(
            passed=passed,
            message=f"整体验证{'通过' if passed else '失败'}",
            failures=all_failures,
            warnings=all_warnings,
            gate_results=all_gate_results,
        )


def create_default_constitution(project_name: str = "My Project") -> Dict[str, Any]:
    """创建默认Constitution"""
    return {
        "schema_version": "1.0",
        "project": {
            "name": project_name,
            "description": "项目质量宪法",
            "ratified": "2024-03-09",
            "version": "1.0.0",
        },
        "core_principles": [
            {
                "id": "quality_first",
                "type": "MANDATORY",
                "name": "质量优先",
                "description": "任务完成前应确保基本质量",
                "gates": [],
            },
            {
                "id": "deliverables_exist",
                "type": "NON_NEGOTIABLE",
                "name": "交付物必须存在",
                "description": "任务文件中列出的交付物文件必须实际存在",
                "gates": [
                    {
                        "type": "custom",
                        "name": "deliverables_exist",
                        "check_func": "check_deliverables_exist",
                        "check_level": "basic",
                        # v6.0: check file is not empty and has code patterns
                        "required": True,
                        "description": "检查 deliverables 中的文件是否存在且包含代码",
                    }
                ],
            },
        ],
        "template_gates": {},
        "amendments": [],
    }


def init_constitution(project_name: str) -> Tuple[bool, str]:
    """初始化Constitution文件"""
    from lra.config import Config

    Config.ensure_dirs()

    constitution_path = Path(Config.get_config_dir()) / "constitution.yaml"

    if constitution_path.exists():
        return False, "Constitution文件已存在"

    constitution = create_default_constitution(project_name)

    try:
        with open(constitution_path, "w", encoding="utf-8") as f:
            yaml.dump(constitution, f, allow_unicode=True, default_flow_style=False)

        return True, f"Constitution创建成功: {constitution_path}"
    except Exception as e:
        return False, f"Constitution创建失败: {str(e)}"


__all__ = [
    "ConstitutionManager",
    "PrincipleValidator",
    "GateEvaluator",
    "PrincipleType",
    "GateType",
    "Gate",
    "Principle",
    "ValidationResult",
    "GateResult",
    "create_default_constitution",
    "init_constitution",
]
