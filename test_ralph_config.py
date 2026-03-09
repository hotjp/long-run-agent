#!/usr/bin/env python3
"""测试 Ralph Loop 配置系统"""

from pathlib import Path
from lra.ralph_config import RalphConfig


def test_ralph_config():
    """测试配置读取"""
    config = RalphConfig(".")

    # 加载配置
    config_data = config.load()
    print("✓ 配置加载成功")

    # 测试默认配置
    assert config.get("ralph.enabled") == True, "enabled 应该为 True"
    print("✓ ralph.enabled = True")

    assert config.get("ralph.optimization.max_iterations") == 7, "max_iterations 应该为 7"
    print("✓ ralph.optimization.max_iterations = 7")

    assert config.get("ralph.optimization.no_change_threshold") == 3, "no_change_threshold 应该为 3"
    print("✓ ralph.optimization.no_change_threshold = 3")

    assert config.get("ralph.optimization.auto_rollback") == True, "auto_rollback 应该为 True"
    print("✓ ralph.optimization.auto_rollback = True")

    # 测试不存在的配置项
    assert config.get("ralph.nonexistent", "default") == "default", "应该返回默认值"
    print("✓ 不存在的配置项返回默认值")

    # 测试质量检查配置
    assert config.get("ralph.quality_check.auto_run") == True
    print("✓ ralph.quality_check.auto_run = True")

    assert config.get("ralph.quality_check.strict_mode") == False
    print("✓ ralph.quality_check.strict_mode = False")

    # 测试错误处理配置
    assert config.get("ralph.error_handling.max_failures") == 3
    print("✓ ralph.error_handling.max_failures = 3")

    assert config.get("ralph.error_handling.max_rollbacks") == 3
    print("✓ ralph.error_handling.max_rollbacks = 3")

    # 测试完成信号配置
    assert config.get("ralph.completion.auto_detect") == True
    print("✓ ralph.completion.auto_detect = True")

    assert "<promise>COMPLETE</promise>" in config.get("ralph.completion.manual_signal")
    print("✓ ralph.completion.manual_signal 包含完成信号")

    # 测试日志配置
    assert config.get("ralph.logging.enabled") == True
    print("✓ ralph.logging.enabled = True")

    assert "ralph_loop.log" in config.get("ralph.logging.log_file")
    print("✓ ralph.logging.log_file 包含 ralph_loop.log")

    print("\n✅ 所有配置测试通过！")


def test_file_structure():
    """测试文件结构"""
    base_path = Path(".long-run-agent")

    # 检查配置文件
    config_file = base_path / "ralph_config.yaml"
    assert config_file.exists(), "ralph_config.yaml 应该存在"
    print("✓ ralph_config.yaml 存在")

    # 检查 memory 目录
    memory_dir = base_path / "memory"
    assert memory_dir.exists(), "memory 目录应该存在"
    print("✓ memory 目录存在")

    # 检查 memory 目录下的文件
    gitkeep = memory_dir / ".gitkeep"
    assert gitkeep.exists(), ".gitkeep 应该存在"
    print("✓ .gitkeep 存在")

    ralph_state = memory_dir / "ralph_state.json"
    assert ralph_state.exists(), "ralph_state.json 应该存在"
    print("✓ ralph_state.json 存在")

    ralph_loop_log = memory_dir / "ralph_loop.log"
    assert ralph_loop_log.exists(), "ralph_loop.log 应该存在"
    print("✓ ralph_loop.log 存在")

    errors_log = memory_dir / "errors.log"
    assert errors_log.exists(), "errors.log 应该存在"
    print("✓ errors.log 存在")

    lessons_learned = memory_dir / "lessons_learned.md"
    assert lessons_learned.exists(), "lessons_learned.md 应该存在"
    print("✓ lessons_learned.md 存在")

    # 检查 Python 模块
    ralph_config_py = Path("lra/ralph_config.py")
    assert ralph_config_py.exists(), "ralph_config.py 应该存在"
    print("✓ lra/ralph_config.py 存在")

    print("\n✅ 所有文件结构测试通过！")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 Ralph Loop 配置系统")
    print("=" * 60)
    print()

    print("📁 测试文件结构...")
    print("-" * 60)
    test_file_structure()
    print()

    print("⚙️  测试配置读取...")
    print("-" * 60)
    test_ralph_config()
    print()

    print("=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)
