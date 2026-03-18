#!/usr/bin/env python3
"""
验证阶段卡住检测和强制进入下一阶段功能
"""

import os
import sys
import tempfile
import subprocess


def run_cmd(cmd):
    """运行命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_force_next_stage_cli():
    """测试 CLI 命令 force_next_stage"""
    print("=" * 60)
    print("测试 lra set <task_id> force_next_stage 命令")
    print("=" * 60)
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        print("1. 初始化项目...")
        rc, out, err = run_cmd("lra init --name test-project")
        if rc != 0:
            print(f"   ❌ 初始化失败: {err}")
            return
        print(f"   ✓ {out.strip()}")
        print()

        print("2. 创建任务...")
        rc, out, err = run_cmd('lra create "测试任务"')
        if rc != 0:
            print(f"   ❌ 创建任务失败: {err}")
            return
        task_id = "task_001"
        print(f"   ✓ 创建任务: {task_id}")
        print()

        print("3. 更新任务状态为 in_progress...")
        rc, out, err = run_cmd(f"lra set {task_id} in_progress")
        if rc != 0:
            print(f"   ❌ 更新状态失败: {err}")
            return
        print(f"   ✓ {out.strip()}")
        print()

        print("4. 测试 force_next_stage 命令...")
        rc, out, err = run_cmd(f"lra set {task_id} force_next_stage")
        if rc != 0:
            print(f"   ❌ 执行失败: {err}")
            return
        print(f"   ✓ 输出:\n{out}")

        if "强制进入下一阶段" in out:
            print("   ✓ 命令执行成功")
        else:
            print("   ❌ 未找到预期输出")
            return
        print()

        print("5. 查看任务状态...")
        rc, out, err = run_cmd(f"lra show {task_id}")
        if rc != 0:
            print(f"   ❌ 查看任务失败: {err}")
            return
        print(f"   ✓ 任务状态:\n{out[:500]}...")
        print()

        print("=" * 60)
        print("✅ CLI 命令测试通过！")
        print("=" * 60)


if __name__ == "__main__":
    test_force_next_stage_cli()
