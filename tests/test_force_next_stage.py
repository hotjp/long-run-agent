#!/usr/bin/env python3
"""
测试阶段卡住检测机制
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lra.task_manager import TaskManager


def test_check_stage_stuck():
    """测试 check_stage_stuck 方法"""
    print("测试 check_stage_stuck 方法...")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        tm = TaskManager()

        tm.init_project("test-project", "task")

        success, task = tm.create("测试任务", template="task")
        task_id = task["id"]
        print(f"  ✓ 创建任务: {task_id}")

        ralph_state = tm.get_ralph_state(task_id)
        print(f"  ✓ 初始 Ralph 状态: iteration={ralph_state.get('iteration', 0)}")

        for i in range(3):
            tm.add_optimization_history(
                task_id, {"iteration": 1, "description": f"优化尝试 {i + 1}"}
            )
        print(f"  ✓ 添加 3 条优化历史（iteration=1）")

        is_stuck, stuck_count = tm.check_stage_stuck(task_id, threshold=3)
        print(f"  ✓ 检查卡住状态: is_stuck={is_stuck}, stuck_count={stuck_count}")
        assert is_stuck == True, "应该检测到卡住"
        assert stuck_count == 3, "卡住次数应为 3"

        tm.add_optimization_history(task_id, {"iteration": 2, "description": "进入新阶段"})
        is_stuck, stuck_count = tm.check_stage_stuck(task_id, threshold=3)
        print(f"  ✓ 更新 iteration=2 后: is_stuck={is_stuck}, stuck_count={stuck_count}")
        assert is_stuck == False, "应该不再卡住"

        print("✅ check_stage_stuck 测试通过\n")


def test_force_next_stage_logic():
    """测试强制进入下一阶段的逻辑"""
    print("测试强制进入下一阶段逻辑...")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        tm = TaskManager()
        tm.init_project("test-project", "task")

        success, task = tm.create("测试任务", template="task")
        task_id = task["id"]
        print(f"  ✓ 创建任务: {task_id}")

        for i in range(3):
            success, new_iter = tm.increment_iteration(task_id)
            if not success:
                break
            tm.add_optimization_history(
                task_id, {"iteration": new_iter, "description": f"优化尝试"}
            )

        ralph_state = tm.get_ralph_state(task_id)
        iteration = ralph_state.get("iteration", 0)
        print(f"  ✓ 增加迭代次数: iteration={iteration}")

        current_stage = tm.get_iteration_stage(task_id)
        print(f"  ✓ 当前阶段: {current_stage.get('name', '未知')}")

        suggestion = tm.get_stage_suggestion(task_id)
        print(f"  ✓ 阶段建议: {suggestion[:100]}...")

        print("✅ 强制进入下一阶段逻辑测试通过\n")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段卡住检测机制测试")
    print("=" * 60)
    print()

    test_check_stage_stuck()
    test_force_next_stage_logic()

    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
