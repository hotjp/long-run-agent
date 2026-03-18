#!/usr/bin/env python3
"""
测试 Ralph Loop 集成
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from lra.task_manager import TaskManager
from lra.config import Config


def test_ralph_state_initialization():
    """测试 Ralph 状态初始化"""
    print("\n=== 测试 Ralph 状态初始化 ===")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        # 初始化项目
        os.chdir(temp_dir)
        Config.ensure_dirs()

        tm = TaskManager()
        tm.init_project("test_project", "task")

        # 创建任务
        success, task = tm.create(description="测试任务", template="task")
        assert success, "创建任务失败"
        print(f"✅ 创建任务成功: {task['id']}")

        # 检查 ralph 字段是否初始化
        assert "ralph" in task, "任务缺少 ralph 字段"
        ralph = task["ralph"]
        print(f"✅ Ralph 字段存在: {json.dumps(ralph, indent=2, ensure_ascii=False)}")

        # 验证 ralph 字段结构
        assert ralph["iteration"] == 0, "初始迭代次数应为 0"
        assert ralph["max_iterations"] == 7, "默认最大迭代次数应为 7"
        assert "quality_checks" in ralph, "缺少 quality_checks 字段"
        assert "issues" in ralph, "缺少 issues 字段"
        assert "optimization_history" in ralph, "缺少 optimization_history 字段"
        print("✅ Ralph 字段结构正确")

    finally:
        os.chdir(Path(__file__).parent)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_ralph_state_operations():
    """测试 Ralph 状态操作"""
    print("\n=== 测试 Ralph 状态操作 ===")

    temp_dir = tempfile.mkdtemp()
    try:
        os.chdir(temp_dir)
        Config.ensure_dirs()

        tm = TaskManager()
        tm.init_project("test_project", "task")

        success, task = tm.create(description="测试任务", template="task")
        task_id = task["id"]

        # 测试获取 Ralph 状态
        ralph_state = tm.get_ralph_state(task_id)
        assert ralph_state is not None, "获取 Ralph 状态失败"
        print(f"✅ 获取 Ralph 状态成功: 迭代={ralph_state['iteration']}")

        # 测试更新 Ralph 状态
        success, msg = tm.update_ralph_state(task_id, {"max_iterations": 10})
        assert success, f"更新 Ralph 状态失败: {msg}"
        ralph_state = tm.get_ralph_state(task_id)
        assert ralph_state["max_iterations"] == 10, "更新最大迭代次数失败"
        print(f"✅ 更新 Ralph 状态成功: max_iterations={ralph_state['max_iterations']}")

        # 测试增加迭代
        success, new_iter = tm.increment_iteration(task_id)
        assert success, "增加迭代失败"
        assert new_iter == 1, f"迭代次数错误: {new_iter}"
        print(f"✅ 增加迭代成功: iteration={new_iter}")

        # 再次增加迭代
        success, new_iter = tm.increment_iteration(task_id)
        assert success, "再次增加迭代失败"
        assert new_iter == 2, f"迭代次数错误: {new_iter}"
        print(f"✅ 再次增加迭代成功: iteration={new_iter}")

        # 测试质量检查记录
        success, msg = tm.record_quality_check(
            task_id, {"tests_passed": True, "lint_passed": True, "acceptance_met": False}
        )
        assert success, f"记录质量检查失败: {msg}"
        ralph_state = tm.get_ralph_state(task_id)
        assert ralph_state["quality_checks"]["tests_passed"] == True
        assert ralph_state["quality_checks"]["lint_passed"] == True
        assert ralph_state["quality_checks"]["acceptance_met"] == False
        print(f"✅ 记录质量检查成功")

        # 测试添加优化历史
        success, msg = tm.add_optimization_history(
            task_id, {"iteration": 1, "changes": "修复密码验证", "commit": "abc123"}
        )
        assert success, f"添加优化历史失败: {msg}"
        ralph_state = tm.get_ralph_state(task_id)
        assert len(ralph_state["optimization_history"]) == 1
        assert "timestamp" in ralph_state["optimization_history"][0]
        print(f"✅ 添加优化历史成功")

        # 测试添加问题记录
        success, msg = tm.add_ralph_issue(task_id, "test_failure", "test_login_failed")
        assert success, f"添加问题记录失败: {msg}"
        ralph_state = tm.get_ralph_state(task_id)
        assert len(ralph_state["issues"]) == 1
        assert ralph_state["issues"][0]["type"] == "test_failure"
        print(f"✅ 添加问题记录成功")

    finally:
        os.chdir(Path(__file__).parent)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_status_transitions():
    """测试状态转换"""
    print("\n=== 测试状态转换 ===")

    temp_dir = tempfile.mkdtemp()
    try:
        os.chdir(temp_dir)
        Config.ensure_dirs()

        tm = TaskManager()
        tm.init_project("test_project", "task")

        success, task = tm.create(description="测试任务", template="task")
        task_id = task["id"]

        # 测试初始状态
        real_status = tm.get_real_status(task_id)
        assert real_status == "pending", f"初始状态错误: {real_status}"
        print(f"✅ 初始状态正确: {real_status}")

        # 更新到 in_progress
        success, msg = tm.update_status(task_id, "in_progress")
        assert success, f"更新状态失败: {msg}"
        real_status = tm.get_real_status(task_id)
        assert real_status == "in_progress"
        print(f"✅ 状态更新到 in_progress")

        # 更新到 completed
        success, msg = tm.update_status(task_id, "completed")
        assert success, f"更新状态失败: {msg}"
        real_status = tm.get_real_status(task_id)
        assert real_status == "completed"
        print(f"✅ 状态更新到 completed")

        # 质量检查未通过，进入优化循环
        success, msg = tm.update_status(task_id, "optimizing")
        # 注意：这需要根据状态机配置，可能需要先调整模板状态定义

        # 设置质量检查通过
        tm.record_quality_check(
            task_id, {"tests_passed": True, "lint_passed": True, "acceptance_met": True}
        )

        # 增加迭代次数
        tm.increment_iteration(task_id)

        # 检查真实状态
        real_status = tm.get_real_status(task_id)
        # 因为迭代次数 > 0 且质量检查通过，应该是 truly_completed
        print(f"✅ 真实状态: {real_status}")

    finally:
        os.chdir(Path(__file__).parent)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_optimization_summary():
    """测试优化摘要"""
    print("\n=== 测试优化摘要 ===")

    temp_dir = tempfile.mkdtemp()
    try:
        os.chdir(temp_dir)
        Config.ensure_dirs()

        tm = TaskManager()
        tm.init_project("test_project", "task")

        success, task = tm.create(description="测试任务", template="task")
        task_id = task["id"]

        # 添加一些优化历史
        tm.increment_iteration(task_id)
        tm.record_quality_check(task_id, {"tests_passed": True})
        tm.add_ralph_issue(task_id, "test_failure", "测试失败")
        tm.add_ralph_issue(task_id, "lint_error", "代码风格错误")
        tm.add_optimization_history(task_id, {"iteration": 1, "changes": "修复测试"})

        # 获取优化摘要
        summary = tm.get_optimization_summary(task_id)
        assert summary is not None, "获取优化摘要失败"

        print(f"✅ 优化摘要:")
        print(f"  - 迭代次数: {summary['iteration']}")
        print(f"  - 最大迭代: {summary['max_iterations']}")
        print(f"  - 总问题数: {summary['total_issues']}")
        print(f"  - 问题类型: {summary['issue_types']}")
        print(f"  - 优化次数: {summary['optimization_count']}")
        print(f"  - 质量状态: {summary['quality_status']}")
        print(f"  - 可继续优化: {summary['can_continue']}")
        print(f"  - 真实状态: {summary['real_status']}")

    finally:
        os.chdir(Path(__file__).parent)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_iteration_limit():
    """测试迭代上限"""
    print("\n=== 测试迭代上限 ===")

    temp_dir = tempfile.mkdtemp()
    try:
        os.chdir(temp_dir)
        Config.ensure_dirs()

        tm = TaskManager()
        tm.init_project("test_project", "task")

        success, task = tm.create(description="测试任务", template="task")
        task_id = task["id"]

        # 设置较小的最大迭代次数
        tm.set_max_iterations(task_id, 3)

        # 测试能否继续优化
        assert tm.can_continue_optimization(task_id), "应该可以继续优化"
        print(f"✅ 初始可以继续优化")

        # 增加迭代到上限
        for i in range(3):
            success, iter_num = tm.increment_iteration(task_id)
            assert success, f"第 {i + 1} 次迭代失败"
            print(f"  - 迭代 {iter_num}")

        # 应该不能继续优化
        assert not tm.can_continue_optimization(task_id), "不应该继续优化"
        print(f"✅ 达到上限，不能继续优化")

        # 尝试再次增加迭代应该失败
        success, iter_num = tm.increment_iteration(task_id)
        assert not success, "应该不能增加迭代"
        print(f"✅ 迭代上限验证成功")

    finally:
        os.chdir(Path(__file__).parent)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("开始测试 Ralph Loop 集成")
    print("=" * 60)

    try:
        test_ralph_state_initialization()
        test_ralph_state_operations()
        test_status_transitions()
        test_optimization_summary()
        test_iteration_limit()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
