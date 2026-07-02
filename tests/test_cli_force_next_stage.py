#!/usr/bin/env python3
"""
验证阶段卡住检测和强制进入下一阶段功能（CLI 端到端集成测试）
"""

import os
import sys
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import chdir_to


def run_cmd(cmd):
    """运行命令并返回 (returncode, stdout, stderr)"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.returncode, result.stdout, result.stderr


def test_force_next_stage_cli():
    """测试 lra set <task_id> force_next_stage 命令端到端"""
    # chdir_to restores cwd before the tempdir is cleaned up — required on
    # Windows, where deleting the cwd raises PermissionError (WinError 32).
    with tempfile.TemporaryDirectory() as tmpdir, chdir_to(tmpdir):
        # 1. 初始化项目
        rc, out, err = run_cmd("lra init --name test-project")
        assert rc == 0, f"lra init failed: rc={rc} stdout={out!r} stderr={err!r}"

        # 2. 创建任务
        rc, out, err = run_cmd('lra create "测试任务"')
        assert rc == 0, f"lra create failed: rc={rc} stdout={out!r} stderr={err!r}"
        task_id = "task_001"

        # 3. 更新状态为 in_progress
        rc, out, err = run_cmd(f"lra set {task_id} in_progress")
        assert rc == 0, f"lra set in_progress failed: rc={rc} stdout={out!r} stderr={err!r}"

        # 4. 强制进入下一阶段
        rc, out, err = run_cmd(f"lra set {task_id} force_next_stage")
        assert rc == 0, (
            f"lra set force_next_stage failed: rc={rc} stdout={out!r} stderr={err!r}"
        )
        assert "强制进入下一阶段" in (out or ""), f"unexpected output: {out!r}"

        # 5. 查看任务状态
        rc, out, err = run_cmd(f"lra show {task_id}")
        assert rc == 0, f"lra show failed: rc={rc} stdout={out!r} stderr={err!r}"


if __name__ == "__main__":
    test_force_next_stage_cli()
    print("CLI 集成测试通过")
