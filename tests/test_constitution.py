"""
测试Constitution模块
"""

import pytest
import tempfile
import os
from pathlib import Path
from lra.constitution import (
    ConstitutionManager,
    PrincipleValidator,
    GateEvaluator,
    PrincipleType,
    GateType,
    Gate,
    Principle,
    ValidationResult,
    GateResult,
    create_default_constitution,
    init_constitution,
)


def test_principle_type_enum():
    """测试原则类型枚举"""
    assert PrincipleType.NON_NEGOTIABLE.value == "NON_NEGOTIABLE"
    assert PrincipleType.MANDATORY.value == "MANDATORY"
    assert PrincipleType.CONFIGURABLE.value == "CONFIGURABLE"


def test_gate_type_enum():
    """测试门禁类型枚举"""
    assert GateType.COMMAND.value == "command"
    assert GateType.FIELD_EXISTS.value == "field_exists"
    assert GateType.CUSTOM.value == "custom"


def test_gate_dataclass():
    """测试门禁数据类"""
    gate = Gate(
        type="command", name="test_gate", required=True, weight=0.5, description="Test gate"
    )

    assert gate.type == "command"
    assert gate.name == "test_gate"
    assert gate.required is True
    assert gate.weight == 0.5
    assert gate.description == "Test gate"


def test_principle_dataclass():
    """测试原则数据类"""
    principle = Principle(
        id="test_principle",
        type="MANDATORY",
        name="Test Principle",
        description="A test principle",
        gates=[],
        enabled=True,
    )

    assert principle.id == "test_principle"
    assert principle.type == "MANDATORY"
    assert principle.name == "Test Principle"
    assert principle.enabled is True


def test_validation_result():
    """测试验证结果"""
    result = ValidationResult(passed=True, message="All checks passed", failures=[], warnings=[])

    assert result.passed is True
    assert result.message == "All checks passed"
    assert len(result.failures) == 0


def test_gate_result():
    """测试门禁结果"""
    result = GateResult(passed=False, gate_name="test_gate", message="Gate failed", exit_code=1)

    assert result.passed is False
    assert result.gate_name == "test_gate"
    assert result.exit_code == 1


def test_create_default_constitution():
    """测试创建默认Constitution"""
    constitution = create_default_constitution("Test Project")

    assert constitution["schema_version"] == "1.0"
    assert constitution["project"]["name"] == "Test Project"
    assert "core_principles" in constitution
    assert len(constitution["core_principles"]) > 0


def test_constitution_manager_init():
    """测试ConstitutionManager初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 设置临时配置目录
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        manager = ConstitutionManager()

        # 应该加载默认Constitution
        assert manager.constitution is not None
        assert "schema_version" in manager.constitution

        # 清理
        del os.environ["LRA_CONFIG_DIR"]


def test_constitution_manager_get_principles():
    """测试获取原则"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        manager = ConstitutionManager()

        # 测试获取不可协商原则
        non_negotiable = manager.get_non_negotiable_principles()
        assert isinstance(non_negotiable, list)

        # 测试获取强制原则
        mandatory = manager.get_mandatory_principles()
        assert isinstance(mandatory, list)

        # 测试获取可配置原则
        configurable = manager.get_enabled_configurable_principles()
        assert isinstance(configurable, list)

        del os.environ["LRA_CONFIG_DIR"]


def test_constitution_manager_get_all_applicable_principles():
    """测试获取所有适用原则"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        manager = ConstitutionManager()

        principles = manager.get_all_applicable_principles()
        assert isinstance(principles, list)
        assert len(principles) > 0

        del os.environ["LRA_CONFIG_DIR"]


def test_gate_evaluator_command_gate():
    """测试命令门禁评估"""
    evaluator = GateEvaluator()

    # 测试成功的命令
    gate_config = {"type": "command", "name": "test_echo", "command": "echo test"}

    result = evaluator.evaluate_gate(gate_config, "test_task", {})
    assert result.passed is True
    assert result.gate_name == "test_echo"


def test_gate_evaluator_field_gate():
    """测试字段门禁评估"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        # 创建测试任务文件
        task_dir = Path(tmpdir) / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)

        task_file = task_dir / "test_task.md"
        task_file.write_text("# Test Task\n\n## test_field\nSome content\n")

        evaluator = GateEvaluator()

        gate_config = {"type": "field_exists", "name": "field_check", "field": "test_field"}

        result = evaluator.evaluate_gate(gate_config, "test_task", {})
        assert result.passed is True
        assert "test_field" in result.message

        del os.environ["LRA_CONFIG_DIR"]


def test_principle_validator():
    """测试原则验证器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        manager = ConstitutionManager()
        validator = PrincipleValidator(manager)

        # 测试验证原则（无门禁）
        principle = {"id": "test", "type": "MANDATORY", "name": "Test Principle", "gates": []}

        result = validator.validate_principle(principle, "test_task", {})
        assert result.passed is True

        del os.environ["LRA_CONFIG_DIR"]


def test_principle_validator_validate_all():
    """测试验证所有原则"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        manager = ConstitutionManager()
        validator = PrincipleValidator(manager)

        result = validator.validate_all_principles("test_task", {})
        assert isinstance(result, ValidationResult)
        assert isinstance(result.passed, bool)

        del os.environ["LRA_CONFIG_DIR"]


def test_init_constitution():
    """测试初始化Constitution"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LRA_CONFIG_DIR"] = tmpdir

        # 首次创建应该成功
        success, message = init_constitution("Test Project")
        assert success is True
        assert "成功" in message

        # 再次创建应该失败（文件已存在）
        success, message = init_constitution("Test Project")
        assert success is False
        assert "已存在" in message

        del os.environ["LRA_CONFIG_DIR"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
