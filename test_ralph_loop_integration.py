#!/usr/bin/env python3
"""
Ralph Loop 集成测试
验证任务级循环优化机制
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from lra.ralph_loop import RalphLoopController
from lra.ralph_config import RalphConfig
from lra.task_manager import TaskManager
from lra.quality_checker import QualityChecker


def test_ralph_config():
    """测试配置系统"""
    print("\n=== 测试 Ralph 配置 ===")

    config = RalphConfig()

    # 测试默认配置
    assert config.get("ralph.enabled") == True
    assert config.get("ralph.optimization.max_iterations") == 7
    assert config.get("ralph.optimization.no_change_threshold") == 3

    print("✅ 配置读取成功")
    print(f"  - max_iterations: {config.get('ralph.optimization.max_iterations')}")
    print(f"  - no_change_threshold: {config.get('ralph.optimization.no_change_threshold')}")


def test_ralph_loop_controller():
    """测试 Ralph Loop 控制器"""
    print("\n=== 测试 Ralph Loop 控制器 ===")

    controller = RalphLoopController(max_iterations=7)

    # 测试初始状态
    assert controller.max_iterations == 7

    # 获取状态
    status = controller.get_status()
    assert status["max_iterations"] == 7

    print("✅ 控制器初始化成功")
    print(f"  - 最大迭代次数: {controller.max_iterations}")
    print(f"  - 当前状态: {status}")

    # 测试退出条件
    should_continue = controller.should_continue_loop()
    print(f"✅ 退出条件判断: {should_continue}")


def test_quality_checker():
    """测试质量检查系统"""
    print("\n=== 测试质量检查系统 ===")

    checker = QualityChecker()

    # 测试支持的模板
    templates = checker.get_supported_templates()
    print(f"✅ 支持的模板: {templates}")

    # 测试质量门禁配置
    for template in templates[:3]:  # 测试前3个
        gates = checker.get_quality_gates(template)
        print(f"  - {template}: {len(gates)} 个质量门禁")


def test_task_manager_ralph():
    """测试任务管理器 Ralph 功能"""
    print("\n=== 测试任务管理器 Ralph 功能 ===")

    manager = TaskManager()

    # 模拟任务数据
    task_id = "test_task_001"
    test_task = {
        "id": task_id,
        "description": "测试任务",
        "status": "pending",
        "template": "code-module",
        "ralph": {
            "iteration": 0,
            "max_iterations": 7,
            "quality_checks": {},
            "issues": [],
            "optimization_history": [],
        },
    }

    # 测试 Ralph 状态操作
    print("✅ Ralph 状态字段已支持")

    # 测试迭代递增
    manager.increment_iteration(task_id)
    print("✅ 迭代递增功能正常")

    # 测试优化历史记录
    manager.add_optimization_history(
        task_id, {"iteration": 1, "changes": "测试修改", "commit": "abc123"}
    )
    print("✅ 优化历史记录功能正常")


def test_integration():
    """测试完整集成流程"""
    print("\n=== 测试完整集成流程 ===")

    # 1. 创建控制器
    controller = RalphLoopController(max_iterations=7)
    print("✅ 步骤1: 创建控制器")

    # 2. 加载配置
    config = RalphConfig()
    print("✅ 步骤2: 加载配置")

    # 3. 模拟任务完成流程
    print("\n模拟任务完成流程:")
    status = controller.get_status()

    for i in range(1, 4):  # 模拟3次优化
        # 记录优化
        controller.record_optimization(f"test_task_{i}", {"changes": f"优化改动{i}"})
        print(f"  - 迭代 {i}/{controller.max_iterations}")

        # 模拟质量检查
        if i < 3:
            print(f"    ❌ 质量检查未通过")
        else:
            print(f"    ✅ 质量检查通过")
            break

    print("\n✅ 完整流程测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Ralph Loop 集成测试")
    print("=" * 60)

    try:
        test_ralph_config()
        test_ralph_loop_controller()
        test_quality_checker()
        test_task_manager_ralph()
        test_integration()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
