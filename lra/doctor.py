#!/usr/bin/env python3
"""
LRA Doctor - Health diagnostics for LRA projects
v5.0 - Check installation, locks, tasks, constitution, and more
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

from lra.config import CURRENT_VERSION, Config, SafeJson
from lra.locks_manager import LockStatus


@dataclass
class DoctorCheck:
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    detail: str = ""
    fix: str = ""
    category: str = "core"


@dataclass
class DoctorResult:
    path: str
    overall_ok: bool = True
    checks: List[DoctorCheck] = field(default_factory=list)
    cli_version: str = ""
    timestamp: str = ""


def check_installation(path: str) -> DoctorCheck:
    """Check if .long-run-agent/ exists"""
    meta_dir = os.path.join(path, Config.METADATA_DIR)
    if os.path.exists(meta_dir):
        return DoctorCheck(
            name="installation",
            status="ok",
            message=".long-run-agent/ exists",
            category="core",
        )
    else:
        return DoctorCheck(
            name="installation",
            status="error",
            message="Project not initialized",
            detail="Run 'lra init' first",
            fix="lra init --name <project>",
            category="core",
        )


def check_task_list_valid(path: str) -> DoctorCheck:
    """Check if task_list.json exists and is valid JSON"""
    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    if not os.path.exists(task_list_path):
        return DoctorCheck(
            name="task_list",
            status="error",
            message="task_list.json not found",
            detail=f"Expected at: {task_list_path}",
            category="core",
        )

    data = SafeJson.read(task_list_path)
    if data is None:
        return DoctorCheck(
            name="task_list",
            status="error",
            message="task_list.json is invalid JSON",
            category="core",
        )

    tasks = data.get("tasks", [])
    return DoctorCheck(
        name="task_list",
        status="ok",
        message=f"task_list.json valid ({len(tasks)} tasks)",
        category="core",
    )


def check_locks_valid(path: str) -> DoctorCheck:
    """Check if locks.json is valid JSON"""
    locks_path = os.path.join(path, Config.METADATA_DIR, Config.LOCKS_FILE)
    if not os.path.exists(locks_path):
        return DoctorCheck(
            name="locks_file",
            status="ok",
            message="locks.json not created yet (no locks held)",
            category="locks",
        )

    data = SafeJson.read(locks_path)
    if data is None:
        return DoctorCheck(
            name="locks_file",
            status="error",
            message="locks.json is invalid JSON",
            category="locks",
        )

    locks = data.get("locks", {})
    return DoctorCheck(
        name="locks_file",
        status="ok",
        message=f"locks.json valid ({len(locks)} locks)",
        category="locks",
    )


def check_constitution_valid(path: str) -> DoctorCheck:
    """Check if constitution.yaml exists and is valid YAML"""
    import yaml

    const_path = os.path.join(path, Config.METADATA_DIR, "constitution.yaml")
    if not os.path.exists(const_path):
        return DoctorCheck(
            name="constitution",
            status="warning",
            message="constitution.yaml not found",
            detail="Constitution defines quality gates",
            fix="lra constitution init",
            category="core",
        )

    try:
        with open(const_path, encoding="utf-8") as f:
            yaml.safe_load(f)
        return DoctorCheck(
            name="constitution",
            status="ok",
            message="constitution.yaml valid",
            category="core",
        )
    except yaml.YAMLError as e:
        return DoctorCheck(
            name="constitution",
            status="error",
            message="constitution.yaml has YAML errors",
            detail=str(e),
            category="core",
        )


def check_task_files(path: str) -> DoctorCheck:
    """Check if all referenced task .md files exist"""
    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    data = SafeJson.read(task_list_path)
    if not data:
        return DoctorCheck(
            name="task_files",
            status="ok",
            message="No task_list to check",
            category="tasks",
        )

    missing = []
    tasks = data.get("tasks", [])

    for task in tasks:
        task_file = task.get("task_file", "")
        if task_file:
            task_path = os.path.join(path, Config.METADATA_DIR, task_file)
            if not os.path.exists(task_path):
                missing.append(task.get("id", "unknown"))

    if missing:
        return DoctorCheck(
            name="task_files",
            status="error",
            message=f"{len(missing)} task file(s) missing",
            detail=f"Missing: {', '.join(missing[:5])}" + ("..." if len(missing) > 5 else ""),
            category="tasks",
        )

    return DoctorCheck(
        name="task_files",
        status="ok",
        message=f"All {len(tasks)} task files exist",
        category="tasks",
    )


def check_orphaned_tasks(path: str) -> DoctorCheck:
    """Check for task files without index entry"""
    tasks_dir = os.path.join(path, Config.METADATA_DIR, Config.TASKS_DIR)
    if not os.path.exists(tasks_dir):
        return DoctorCheck(
            name="orphaned_tasks",
            status="ok",
            message="No tasks directory",
            category="tasks",
        )

    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    data = SafeJson.read(task_list_path)
    if not data:
        return DoctorCheck(
            name="orphaned_tasks",
            status="warning",
            message="task_list.json missing, all task files are orphaned",
            category="tasks",
        )

    indexed_ids = {t.get("id") for t in data.get("tasks", [])}

    orphaned = []
    for f in os.listdir(tasks_dir):
        if f.endswith(".md"):
            task_id = f[:-3]
            if task_id not in indexed_ids:
                orphaned.append(task_id)

    if orphaned:
        return DoctorCheck(
            name="orphaned_tasks",
            status="warning",
            message=f"{len(orphaned)} orphaned task file(s)",
            detail=f"Orphaned: {', '.join(orphaned[:5])}" + ("..." if len(orphaned) > 5 else ""),
            fix="lra recover",
            category="tasks",
        )

    return DoctorCheck(
        name="orphaned_tasks",
        status="ok",
        message="No orphaned task files",
        category="tasks",
    )


def check_circular_deps(path: str) -> DoctorCheck:
    """Check for cycles in dependency graph"""
    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    data = SafeJson.read(task_list_path)
    if not data:
        return DoctorCheck(
            name="circular_deps",
            status="ok",
            message="No tasks to check",
            category="tasks",
        )

    tasks = data.get("tasks", [])
    task_map = {t.get("id"): t for t in tasks}

    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(task_id: str, path: List[str]) -> bool:
        visited.add(task_id)
        rec_stack.add(task_id)
        path.append(task_id)

        task = task_map.get(task_id)
        if not task:
            path.pop()
            rec_stack.remove(task_id)
            return False

        deps = task.get("dependencies", [])
        for dep in deps:
            if dep not in visited:
                if dfs(dep, path):
                    return True
            elif dep in rec_stack:
                cycle_start = path.index(dep)
                cycle = path[cycle_start:] + [dep]
                cycles.append(cycle)
                return True

        path.pop()
        rec_stack.remove(task_id)
        return False

    for task in tasks:
        tid = task.get("id")
        if tid not in visited:
            dfs(tid, [])

    if cycles:
        return DoctorCheck(
            name="circular_deps",
            status="error",
            message=f"Found {len(cycles)} circular dependency",
            detail=" -> ".join(cycles[0][:5]) if cycles else "",
            category="tasks",
        )

    return DoctorCheck(
        name="circular_deps",
        status="ok",
        message="No circular dependencies",
        category="tasks",
    )


def check_orphaned_locks(path: str) -> DoctorCheck:
    """Check for locks with no heartbeat > 15 min"""
    from lra.config import ORPHAN_THRESHOLD_MINUTES

    locks_path = os.path.join(path, Config.METADATA_DIR, Config.LOCKS_FILE)
    if not os.path.exists(locks_path):
        return DoctorCheck(
            name="orphaned_locks",
            status="ok",
            message="No locks file",
            category="locks",
        )

    data = SafeJson.read(locks_path)
    if not data:
        return DoctorCheck(
            name="orphaned_locks",
            status="ok",
            message="No locks",
            category="locks",
        )

    locks = data.get("locks", {})
    orphaned = []

    for task_id, lock in locks.items():
        status = lock.get("status")
        if status not in (LockStatus.CLAIMED, LockStatus.PAUSED):
            continue

        last_hb = lock.get("last_heartbeat") or lock.get("claimed_at")
        if not last_hb:
            orphaned.append(task_id)
            continue

        try:
            last = datetime.fromisoformat(last_hb)
            threshold = timedelta(minutes=ORPHAN_THRESHOLD_MINUTES)
            if datetime.now() - last > threshold:
                orphaned.append(task_id)
        except Exception:
            orphaned.append(task_id)

    if orphaned:
        threshold_min = ORPHAN_THRESHOLD_MINUTES
        return DoctorCheck(
            name="orphaned_locks",
            status="warning",
            message=f"{len(orphaned)} orphaned lock(s) (> {threshold_min} min no heartbeat)",
            detail=f"Orphaned: {', '.join(orphaned[:5])}" + ("..." if len(orphaned) > 5 else ""),
            fix="lra doctor --fix",
            category="locks",
        )

    return DoctorCheck(
        name="orphaned_locks",
        status="ok",
        message="No orphaned locks",
        category="locks",
    )


def check_stale_locks(path: str) -> DoctorCheck:
    """Check for locks held > expected duration"""
    locks_path = os.path.join(path, Config.METADATA_DIR, Config.LOCKS_FILE)
    if not os.path.exists(locks_path):
        return DoctorCheck(
            name="stale_locks",
            status="ok",
            message="No locks file",
            category="locks",
        )

    data = SafeJson.read(locks_path)
    if not data:
        return DoctorCheck(
            name="stale_locks",
            status="ok",
            message="No locks",
            category="locks",
        )

    locks = data.get("locks", {})
    stale = []

    for task_id, lock in locks.items():
        if lock.get("status") != LockStatus.CLAIMED:
            continue

        claimed_at = lock.get("claimed_at")
        if not claimed_at:
            continue

        try:
            claimed = datetime.fromisoformat(claimed_at)
            # Consider stale if held > 2 hours
            if datetime.now() - claimed > timedelta(hours=2):
                stale.append(task_id)
        except Exception:
            pass

    if stale:
        return DoctorCheck(
            name="stale_locks",
            status="warning",
            message=f"{len(stale)} stale lock(s) (> 2 hours)",
            detail=f"Stale: {', '.join(stale[:5])}" + ("..." if len(stale) > 5 else ""),
            category="locks",
        )

    return DoctorCheck(
        name="stale_locks",
        status="ok",
        message="No stale locks",
        category="locks",
    )


def check_lock_file_valid(path: str) -> DoctorCheck:
    """Check if locks.json structure is valid"""
    locks_path = os.path.join(path, Config.METADATA_DIR, Config.LOCKS_FILE)
    if not os.path.exists(locks_path):
        return DoctorCheck(
            name="lock_structure",
            status="ok",
            message="No locks file to check",
            category="locks",
        )

    data = SafeJson.read(locks_path)
    if data is None:
        return DoctorCheck(
            name="lock_structure",
            status="error",
            message="locks.json is not valid JSON",
            category="locks",
        )

    locks = data.get("locks")
    if locks is None or not isinstance(locks, dict):
        return DoctorCheck(
            name="lock_structure",
            status="error",
            message="locks.json missing 'locks' dict",
            category="locks",
        )

    return DoctorCheck(
        name="lock_structure",
        status="ok",
        message=f"locks.json structure valid ({len(locks)} entries)",
        category="locks",
    )


def check_config_valid(path: str) -> DoctorCheck:
    """Check if config.json is valid"""
    config_path = os.path.join(path, Config.METADATA_DIR, Config.CONFIG_FILE)
    if not os.path.exists(config_path):
        return DoctorCheck(
            name="config_file",
            status="warning",
            message="config.json not found",
            category="core",
        )

    data = SafeJson.read(config_path)
    if data is None:
        return DoctorCheck(
            name="config_file",
            status="error",
            message="config.json is invalid JSON",
            category="core",
        )

    return DoctorCheck(
        name="config_file",
        status="ok",
        message="config.json valid",
        category="core",
    )


def check_version_tracking(path: str) -> DoctorCheck:
    """Check if .lra_version matches CURRENT_VERSION"""
    version_file = os.path.join(path, Config.METADATA_DIR, ".lra_version")

    if not os.path.exists(version_file):
        return DoctorCheck(
            name="version_tracking",
            status="warning",
            message="No .lra_version file",
            detail="Consider tracking version for migrations",
            category="core",
        )

    try:
        with open(version_file, encoding="utf-8") as f:
            tracked_version = f.read().strip()

        if tracked_version != CURRENT_VERSION:
            return DoctorCheck(
                name="version_tracking",
                status="warning",
                message=f"Version mismatch: tracked={tracked_version}, current={CURRENT_VERSION}",
                category="core",
            )

        return DoctorCheck(
            name="version_tracking",
            status="ok",
            message=f"Version tracking OK ({CURRENT_VERSION})",
            category="core",
        )
    except Exception as e:
        return DoctorCheck(
            name="version_tracking",
            status="warning",
            message="Could not read .lra_version",
            detail=str(e),
            category="core",
        )


def check_git_repo(path: str) -> DoctorCheck:
    """Check if parent dir is a git repo"""
    git_dir = os.path.join(path, ".git")
    if os.path.exists(git_dir):
        return DoctorCheck(
            name="git_repo",
            status="ok",
            message="Project is a git repository",
            category="core",
        )
    else:
        return DoctorCheck(
            name="git_repo",
            status="warning",
            message="Not a git repository",
            detail="Consider running 'git init' for version control",
            category="core",
        )


def run_diagnostics(path: str = ".") -> DoctorResult:
    """Run all diagnostics and return combined result"""
    result = DoctorResult(
        path=os.path.abspath(path),
        cli_version=CURRENT_VERSION,
        timestamp=datetime.now().isoformat(),
    )

    checks = [
        check_installation(path),
        check_task_list_valid(path),
        check_locks_valid(path),
        check_constitution_valid(path),
        check_task_files(path),
        check_orphaned_tasks(path),
        check_circular_deps(path),
        check_orphaned_locks(path),
        check_stale_locks(path),
        check_lock_file_valid(path),
        check_config_valid(path),
        check_version_tracking(path),
        check_git_repo(path),
    ]

    result.checks = checks

    # Overall status: error if any error, else warning if any warning, else ok
    has_error = any(c.status == "error" for c in checks)

    result.overall_ok = not has_error

    return result


def fix_orphaned_locks(path: str) -> bool:
    """Clean up orphaned locks - release them"""
    locks_path = os.path.join(path, Config.METADATA_DIR, Config.LOCKS_FILE)
    if not os.path.exists(locks_path):
        return True

    data = SafeJson.read(locks_path)
    if not data:
        return True

    locks = data.get("locks", {})
    from lra.config import ORPHAN_THRESHOLD_MINUTES

    cleaned = []
    for task_id, lock in list(locks.items()):
        status = lock.get("status")
        if status not in (LockStatus.CLAIMED, LockStatus.PAUSED):
            continue

        last_hb = lock.get("last_heartbeat") or lock.get("claimed_at")
        if not last_hb:
            locks[task_id]["status"] = LockStatus.ORPHANED
            cleaned.append(task_id)
            continue

        try:
            last = datetime.fromisoformat(last_hb)
            threshold = timedelta(minutes=ORPHAN_THRESHOLD_MINUTES)
            if datetime.now() - last > threshold:
                locks[task_id]["status"] = LockStatus.ORPHANED
                cleaned.append(task_id)
        except Exception:
            locks[task_id]["status"] = LockStatus.ORPHANED
            cleaned.append(task_id)

    if cleaned:
        data["locks"] = locks
        SafeJson.write(locks_path, data)

    return True
