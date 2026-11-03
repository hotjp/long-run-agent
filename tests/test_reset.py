"""
Tests for `lra reset` —— 把卡住的任务复位到初始状态。

背景（GitHub issue #2 问题3）：worker 超时被 kill，任务卡在 in_progress；
`lra set <id> pending` 被状态机拒绝（in_progress → pending 不是合法流转），
旧办法是手改 task_list.json —— 多 worker 并发写时会丢更新。

覆盖：
- 复位语义：in_progress / blocked / pending_test → 初始状态
- 拒绝复位的情况：pending / completed / skipped / cancelled / 不存在
- 审计记录：reset_history（谁、何时、从什么状态、为什么）
- Ralph 迭代上下文归零（optimization_history 保留）
- 锁保护：心跳正常的 worker 持有锁时拒绝复位；孤儿锁不算活着；--force 强制
- CLI 端到端：退出码、JSON 输出、stdout 锚点
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

from lra.config import Config, SafeJson
from lra.locks_manager import LocksManager
from lra.task_manager import TaskManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import chdir_to  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- fixtures ----------

def _make_task(tid, status="pending", **extra):
    task = {
        "id": tid,
        "description": f"task {tid}",
        "template": "task",
        "priority": "P1",
        "status": status,
        "parent_id": None,
        "dependencies": [],
        "dependency_type": "all",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "ralph": {
            "iteration": 3,
            "max_iterations": 7,
            "quality_checks": {"tests_passed": True},
            "issues": ["something"],
            "optimization_history": [{"iteration": 1}],
        },
    }
    task.update(extra)
    return task


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


def _write_lock(task_id, status="claimed", heartbeat_minutes_ago=0):
    path = Config.get_locks_path()
    data = SafeJson.read(path) or {"locks": {}}
    data.setdefault("locks", {})[task_id] = {
        "session_id": f"sess_{task_id}",
        "task_id": task_id,
        "status": status,
        "claimed_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "last_heartbeat": (
            datetime.now() - timedelta(minutes=heartbeat_minutes_ago)
        ).isoformat(),
        "checkpoint": None,
    }
    SafeJson.write(path, data)


# ---------- API: 基本复位 ----------

def test_reset_in_progress_to_pending(temp_project):
    _write_tasks([_make_task("task_001", "in_progress")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001", reason="worker 超时被 kill")
    assert ok and msg == "pending"
    assert tm.get("task_001")["status"] == "pending"


def test_reset_blocked_to_pending(temp_project):
    _write_tasks([_make_task("task_001", "blocked")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001")
    assert ok and msg == "pending"
    assert tm.get("task_001")["status"] == "pending"


def test_reset_pending_test_to_pending(temp_project):
    _write_tasks([_make_task("task_001", "pending_test")])
    tm = TaskManager()
    ok, _ = tm.reset_task("task_001")
    assert ok
    assert tm.get("task_001")["status"] == "pending"


def test_reset_not_found(temp_project):
    tm = TaskManager()
    ok, msg = tm.reset_task("task_999")
    assert not ok and msg == "not_found"


# ---------- API: 拒绝复位的情况 ----------

def test_reset_pending_is_noop_error(temp_project):
    _write_tasks([_make_task("task_001", "pending")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001")
    assert not ok and msg == "already_pending"
    assert tm.get("task_001")["status"] == "pending"


def test_reset_completed_refused(temp_project):
    _write_tasks([_make_task("task_001", "completed")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001")
    assert not ok and msg.startswith("invalid_state:")
    assert tm.get("task_001")["status"] == "completed"


def test_reset_truly_completed_refused(temp_project):
    _write_tasks([_make_task("task_001", "truly_completed")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001")
    assert not ok and msg.startswith("invalid_state:")


def test_reset_skipped_refused(temp_project):
    _write_tasks([_make_task("task_001", "skipped")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001")
    assert not ok and msg == "lifecycle_state:skipped"


def test_reset_cancelled_refused(temp_project):
    _write_tasks([_make_task("task_001", "cancelled")])
    tm = TaskManager()
    ok, msg = tm.reset_task("task_001")
    assert not ok and msg == "lifecycle_state:cancelled"


# ---------- API: 审计记录 ----------

def test_reset_writes_audit_record(temp_project):
    _write_tasks([_make_task("task_001", "in_progress")])
    tm = TaskManager()
    ok, _ = tm.reset_task("task_001", reason="worker 超时被 kill")
    assert ok

    history = tm.get("task_001")["reset_history"]
    assert len(history) == 1
    entry = history[0]
    assert entry["previous_status"] == "in_progress"
    assert entry["status"] == "pending"
    assert entry["reason"] == "worker 超时被 kill"
    assert entry["agent"]
    assert entry["forced"] is False
    datetime.fromisoformat(entry["at"])  # 时间戳可解析


def test_reset_history_accumulates(temp_project):
    _write_tasks([_make_task("task_001", "in_progress")])
    tm = TaskManager()
    tm.reset_task("task_001", reason="第一次")

    # 模拟再次卡住：把状态改回 in_progress，保留已有 reset_history
    data = tm._load()
    data["tasks"][0]["status"] = "in_progress"
    tm._save(data)

    tm.reset_task("task_001", reason="第二次", force=True)
    history = tm.get("task_001")["reset_history"]
    assert len(history) == 2
    assert [h["reason"] for h in history] == ["第一次", "第二次"]
    assert history[1]["forced"] is True


def test_reset_clears_ralph_but_keeps_history(temp_project):
    _write_tasks([_make_task("task_001", "in_progress")])
    tm = TaskManager()
    tm.reset_task("task_001")
    ralph = tm.get("task_001")["ralph"]
    assert ralph["iteration"] == 0
    assert ralph["quality_checks"] == {}
    assert ralph["issues"] == []
    # 审计痕迹保留
    assert ralph["optimization_history"] == [{"iteration": 1}]


# ---------- 锁保护 ----------

def test_is_lock_active_false_without_lock(temp_project):
    lm = LocksManager()
    active, lock = lm.is_lock_active("task_001")
    assert active is False and lock is None


def test_is_lock_active_true_for_live_worker(temp_project):
    _write_lock("task_001", heartbeat_minutes_ago=1)
    lm = LocksManager()
    active, lock = lm.is_lock_active("task_001")
    assert active is True
    assert lock["session_id"] == "sess_task_001"


def test_is_lock_active_false_for_orphan(temp_project):
    # 心跳 1 小时前 → 孤儿锁（worker 已被 kill），不算活着
    _write_lock("task_001", heartbeat_minutes_ago=60)
    lm = LocksManager()
    active, lock = lm.is_lock_active("task_001")
    assert active is False
    assert lock is not None  # 锁还在，但已经死了


def test_is_lock_active_false_for_locked_by_parent(temp_project):
    _write_lock("task_001", status="locked_by_parent")
    lm = LocksManager()
    active, _ = lm.is_lock_active("task_001")
    assert active is False


# ---------- CLI ----------

def _run(args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [sys.executable, "-m", "lra.cli"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


@pytest.fixture
def cli_project():
    with tempfile.TemporaryDirectory() as tmpdir, chdir_to(tmpdir):
        rc, _, err = _run(["init", "--name", "t"], tmpdir)
        assert rc == 0, err
        rc, out, err = _run(["create", "一个会被 kill 的任务"], tmpdir)
        assert rc == 0, err
        assert "Created: task_001" in out
        yield tmpdir


def test_cli_reset_resets_task(cli_project):
    rc, _, err = _run(["set", "task_001", "in_progress"], cli_project)
    assert rc == 0, err

    rc, out, err = _run(["reset", "task_001", "--reason", "worker 被 kill"], cli_project)
    assert rc == 0, err
    assert "Reset: task_001" in out  # stdout 末行锚点
    assert out.strip().splitlines()[-1] == "Reset: task_001"

    tasks = json.load(open(os.path.join(cli_project, ".long-run-agent", "task_list.json")))
    assert tasks["tasks"][0]["status"] == "pending"


def test_cli_reset_failure_exits_nonzero(cli_project):
    rc, out, _ = _run(["reset", "task_001"], cli_project)  # 本来就是 pending
    assert rc != 0
    assert "already_pending" in out


def test_cli_reset_json_output(cli_project):
    _run(["set", "task_001", "in_progress"], cli_project)
    rc, out, err = _run(
        ["reset", "task_001", "--reason", "json 模式", "--json"], cli_project
    )
    assert rc == 0, err
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert payload["task_id"] == "task_001"
    assert payload["status"] == "pending"
    assert payload["previous_status"] == "in_progress"
    assert payload["reason"] == "json 模式"


def test_cli_reset_refuses_when_live_worker_holds_lock(cli_project):
    _run(["set", "task_001", "in_progress"], cli_project)
    _write_lock("task_001", heartbeat_minutes_ago=0)

    rc, out, _ = _run(["reset", "task_001"], cli_project)
    assert rc != 0
    assert "locked_by_active_worker" in out or "心跳正常" in out

    # 任务状态没被动过
    tasks = json.load(open(os.path.join(cli_project, ".long-run-agent", "task_list.json")))
    assert tasks["tasks"][0]["status"] == "in_progress"


def test_cli_reset_force_overrides_live_lock(cli_project):
    _run(["set", "task_001", "in_progress"], cli_project)
    _write_lock("task_001", heartbeat_minutes_ago=0)

    rc, out, err = _run(["reset", "task_001", "--force"], cli_project)
    assert rc == 0, err
    assert "Reset: task_001" in out

    # 死掉的 worker 的锁被一并清掉 —— 否则新 worker claim 不到
    locks = json.load(open(os.path.join(cli_project, ".long-run-agent", "locks.json")))
    assert "task_001" not in locks.get("locks", {})


def test_cli_reset_releases_orphan_lock(cli_project):
    _run(["set", "task_001", "in_progress"], cli_project)
    _write_lock("task_001", heartbeat_minutes_ago=60)  # 孤儿锁

    rc, out, err = _run(["reset", "task_001"], cli_project)
    assert rc == 0, err
    locks = json.load(open(os.path.join(cli_project, ".long-run-agent", "locks.json")))
    assert "task_001" not in locks.get("locks", {})
