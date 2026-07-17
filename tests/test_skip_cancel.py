"""
Tests for skip / cancel / recall —— 横向生命周期退出。

覆盖：
- skipped/cancelled 任务从 get_ready_tasks 隐藏
- cancel 解锁下游依赖（skipped 不解锁）
- recall 恢复 skipped/cancelled 到 pending，并动态重新阻塞下游
- 非法转换（重复 skip/cancel、对非生命周期状态 recall）
- lifecycle 元数据写入
- CLI 端到端：lra skip / cancel / recall
"""

import os
import subprocess
import sys
import tempfile

import pytest

from lra.config import Config, SafeJson
from lra.task_manager import TaskManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import chdir_to  # noqa: E402


# ---------- fixtures ----------

def _make_task(tid, status="pending", dependencies=None, dependency_type="all"):
    return {
        "id": tid,
        "description": f"task {tid}",
        "template": "task",
        "priority": "P1",
        "status": status,
        "parent_id": None,
        "dependencies": dependencies or [],
        "dependency_type": dependency_type,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


def _write_tasks(tasks):
    SafeJson.write(
        Config.get_task_list_path(),
        {"project_name": "t", "created_at": "2024-01-01T00:00:00", "tasks": tasks},
    )


@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        orig = os.getcwd()
        os.chdir(tmpdir)
        Config.METADATA_DIR = ".long-run-agent"
        Config.ensure_dirs()
        _write_tasks([])
        yield tmpdir
        os.chdir(orig)


def _ready_ids(tm):
    return [t["id"] for t in tm.get_ready_tasks()]


# ---------- API: 隐藏 ----------

def test_skip_hides_from_ready(temp_project):
    _write_tasks([_make_task("task_001", "pending")])
    tm = TaskManager()
    assert "task_001" in _ready_ids(tm)

    ok, msg = tm.skip_task("task_001", reason="暂不做")
    assert ok and msg == "skipped"

    assert tm.get("task_001")["status"] == "skipped"
    assert "task_001" not in _ready_ids(tm)


def test_cancel_hides_from_ready(temp_project):
    _write_tasks([_make_task("task_001", "in_progress")])
    tm = TaskManager()
    ok, _ = tm.cancel_task("task_001", reason="建错了")
    assert ok
    assert tm.get("task_001")["status"] == "cancelled"
    assert "task_001" not in _ready_ids(tm)


# ---------- API: 依赖连带 ----------

def test_cancel_unblocks_dependents(temp_project):
    # A 被 B 依赖；B 因 A 未完成而 blocked
    _write_tasks(
        [
            _make_task("task_A", "pending"),
            _make_task("task_B", "blocked", dependencies=["task_A"]),
        ]
    )
    tm = TaskManager()
    assert "task_B" not in _ready_ids(tm)  # 依赖未满足

    ok, _ = tm.cancel_task("task_A", reason="无关")
    assert ok

    # cancelled 视为依赖已了结 → B 被解锁，出现在 ready
    assert "task_B" in _ready_ids(tm)
    assert tm.get("task_B")["status"] == "pending"  # stored-blocked 被翻回 pending


def test_skip_does_not_unblock_dependents(temp_project):
    _write_tasks(
        [
            _make_task("task_A", "pending"),
            _make_task("task_B", "blocked", dependencies=["task_A"]),
        ]
    )
    tm = TaskManager()
    ok, _ = tm.skip_task("task_A", reason="等外部接口")
    assert ok

    # skipped 不满足依赖 → B 继续等
    assert "task_B" not in _ready_ids(tm)


# ---------- API: recall ----------

def test_recall_skipped(temp_project):
    _write_tasks([_make_task("task_001", "skipped")])
    tm = TaskManager()
    ok, msg = tm.recall_task("task_001")
    assert ok and msg == "pending"
    assert tm.get("task_001")["status"] == "pending"
    assert "task_001" in _ready_ids(tm)


def test_recall_cancelled(temp_project):
    _write_tasks([_make_task("task_001", "cancelled")])
    tm = TaskManager()
    ok, msg = tm.recall_task("task_001")
    assert ok and msg == "pending"
    assert "task_001" in _ready_ids(tm)


def test_recall_reblocks_dependents_after_cancel(temp_project):
    # cancel A 解锁 B；recall A 后，B 应再次因依赖未满足而移出 ready
    _write_tasks(
        [
            _make_task("task_A", "pending"),
            _make_task("task_B", "blocked", dependencies=["task_A"]),
        ]
    )
    tm = TaskManager()
    tm.cancel_task("task_A")
    assert "task_B" in _ready_ids(tm)

    tm.recall_task("task_A")
    assert tm.get("task_A")["status"] == "pending"
    # A 回到 pending → B 的依赖重新未满足 → 动态移出 ready
    assert "task_B" not in _ready_ids(tm)


# ---------- API: 非法转换 ----------

def test_double_skip_errors(temp_project):
    _write_tasks([_make_task("task_001", "skipped")])
    tm = TaskManager()
    ok, msg = tm.skip_task("task_001")
    assert not ok and "already_lifecycle_state" in msg

    ok, msg = tm.cancel_task("task_001")
    assert not ok and "already_lifecycle_state" in msg


def test_recall_non_lifecycle_errors(temp_project):
    _write_tasks([_make_task("task_001", "pending")])
    tm = TaskManager()
    ok, msg = tm.recall_task("task_001")
    assert not ok and "not_lifecycle_state" in msg


def test_skip_cancel_unknown_task(temp_project):
    tm = TaskManager()
    assert tm.skip_task("nope") == (False, "not_found")
    assert tm.cancel_task("nope") == (False, "not_found")
    assert tm.recall_task("nope") == (False, "not_found")


# ---------- API: 元数据 ----------

def test_lifecycle_metadata(temp_project):
    _write_tasks([_make_task("task_001", "in_progress")])
    tm = TaskManager()
    tm.skip_task("task_001", reason="等设计")

    lc = tm.get("task_001").get("lifecycle")
    assert lc["action"] == "skipped"
    assert lc["reason"] == "等设计"
    assert lc["previous_status"] == "in_progress"
    assert "at" in lc

    tm.recall_task("task_001")
    assert tm.get("task_001")["lifecycle"]["action"] == "recalled"
    assert tm.get("task_001")["lifecycle"]["previous_status"] == "skipped"


# ---------- CLI 端到端 ----------

def _run(cmd):
    r = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return r.returncode, r.stdout, r.stderr


def test_skip_cancel_recall_cli():
    with tempfile.TemporaryDirectory() as tmpdir, chdir_to(tmpdir):
        assert _run("lra init --name t")[0] == 0
        assert _run('lra create "做一半可能要跳过的任务"')[0] == 0
        tid = "task_001"

        # skip
        rc, out, err = _run(f'lra skip {tid} --reason "暂时不做"')
        assert rc == 0, f"skip failed: {err!r}"
        assert "skipped" in out and "recall" in out

        # ready 不再显示
        rc, out, _ = _run("lra ready")
        assert tid not in out

        # recall 回到 ready
        assert _run(f"lra recall {tid}")[0] == 0
        rc, out, _ = _run("lra ready")
        assert tid in out

        # cancel
        rc, out, err = _run(f'lra cancel {tid} --reason "建错了"')
        assert rc == 0, f"cancel failed: {err!r}"
        assert "cancelled" in out

        rc, out, _ = _run("lra ready")
        assert tid not in out

        # recall cancelled 也能恢复
        assert _run(f"lra recall {tid}")[0] == 0
        rc, out, _ = _run("lra ready")
        assert tid in out

        # list 仍可见 skipped/cancelled（审计）
        _run(f'lra cancel {tid} --reason "再次取消"')
        rc, out, _ = _run("lra list")
        assert tid in out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
