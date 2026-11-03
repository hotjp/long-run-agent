#!/usr/bin/env python3
"""
LRA Doctor - Health diagnostics for LRA projects
v5.0 - Check installation, locks, tasks, constitution, and more
"""

import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict, List

from lra.config import CURRENT_VERSION, Config, SafeJson
from lra.deps import (
    externally_managed,
    install_missing,
    missing_install_hint,
    pip_install_command,
    probe_all,
)
from lra.locks_manager import LockStatus


class DoctorCheck:
    """单个检查项。

    用普通类而非 dataclass：dataclasses 自己 import inspect，
    而 inspect 正是最常被同名文件遮蔽的标准库模块——用 dataclass 会让
    doctor 在"环境被遮蔽"这种它本该诊断的场景里自己先崩掉。
    """

    __slots__ = ("name", "status", "message", "detail", "fix", "category")

    def __init__(
        self,
        name: str,
        status: str,  # "ok", "warning", "error"
        message: str,
        detail: str = "",
        fix: str = "",
        category: str = "core",
    ):
        self.name = name
        self.status = status
        self.message = message
        self.detail = detail
        self.fix = fix
        self.category = category

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"DoctorCheck({self.name}, {self.status})"


class DoctorResult:
    __slots__ = ("path", "overall_ok", "checks", "cli_version", "timestamp")

    def __init__(
        self,
        path: str,
        overall_ok: bool = True,
        checks: List[DoctorCheck] = None,
        cli_version: str = "",
        timestamp: str = "",
    ):
        self.path = path
        self.overall_ok = overall_ok
        self.checks = checks if checks is not None else []
        self.cli_version = cli_version
        self.timestamp = timestamp

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"DoctorResult({self.path}, ok={self.overall_ok})"


def check_runtime_dependencies(path: str) -> DoctorCheck:
    """检查运行依赖是否可用（jinja2 / pyyaml / filelock）。

    这几个包缺失或被同名文件遮蔽时，症状是"任务书渲染不出来""任务书模板损坏"，
    但真正的原因是环境——所以单独查，别让用户去查模板。

    判定逻辑与 lra create 共用 lra/deps.py，保证两边结论一致。
    """
    statuses = probe_all()

    missing = [s for s in statuses if s.state == "missing"]
    shadowed = [s for s in statuses if s.state == "shadowed"]
    broken = [s for s in statuses if s.state == "broken"]

    if missing or shadowed or broken:
        parts = []
        if missing:
            parts.append(
                "缺少依赖: "
                + "、".join(f"{s.package}（{s.purpose}）" for s in missing)
            )
        if shadowed:
            parts.append(
                "依赖被同名文件遮蔽: "
                + "、".join(f"{s.package} → {s.detail}" for s in shadowed)
            )
        if broken:
            parts.append(
                "依赖导入失败: " + "、".join(f"{s.package} → {s.detail}" for s in broken)
            )
        if externally_managed():
            parts.append(
                "当前 Python 受 PEP 668 保护，普通 pip install 会被拒绝——"
                "安装命令需带 --user --break-system-packages，或改用虚拟环境"
            )

        # 修复建议必须对症：装包只治"没装"，治不了"被遮蔽"
        if shadowed and not missing:
            fix = "把上面点名的文件改名或移出工作目录（装包无用）"
        elif missing:
            fix = missing_install_hint()
        else:
            # 装坏了 → 强制重装。命令同样要适配 PEP 668，
            # 裸 `pip install --force-reinstall` 在 homebrew Python 上会被直接拒。
            pkgs = [s.package for s in broken] or ["jinja2"]
            fix = " ".join(pip_install_command(["--force-reinstall"] + pkgs))

        if shadowed:
            headline = "依赖被同名文件遮蔽，任务书无法渲染"
        elif missing:
            headline = "运行环境缺少依赖，任务书无法渲染"
        else:
            headline = "依赖导入失败，任务书无法渲染"

        return DoctorCheck(
            name="runtime_dependencies",
            status="error",
            message=headline,
            detail="; ".join(parts),
            fix=fix,
            category="environment",
        )

    return DoctorCheck(
        name="runtime_dependencies",
        status="ok",
        message="运行依赖齐全（jinja2 / pyyaml / filelock）",
        category="environment",
    )


def fix_missing_dependencies(dry_run: bool = False) -> Dict[str, Any]:
    """装上缺失的运行依赖（doctor --fix 的自愈动作）。

    只装真的没装的（state == missing）。被同名文件遮蔽的装包没用——
    得先把那个顶替标准库的文件挪走，doctor 的 detail 里会指出是哪个文件。
    """
    result = install_missing(dry_run=dry_run)
    return result


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
    try:
        import yaml
    except ImportError:
        return DoctorCheck(
            name="constitution",
            status="error",
            message="缺少 PyYAML 依赖，无法校验 constitution",
            detail="pip install -U long-run-agent   # 会带上 pyyaml",
            fix="pip install -U long-run-agent",
            category="environment",
        )

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
    """Check if all referenced task .md files exist

    两类问题都算"任务书缺失"：
    - task_file 指向的文件不存在（模板损坏时创建失败留下的僵尸任务）
    - 记录里根本没有 task_file（撞号去重时被解绑的那条）
    """
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
    unbound = []
    tasks = data.get("tasks", [])

    for task in tasks:
        task_file = task.get("task_file", "")
        if not task_file:
            unbound.append(task.get("id", "unknown"))
            continue
        task_path = os.path.join(path, Config.METADATA_DIR, task_file)
        if not os.path.exists(task_path):
            missing.append(task.get("id", "unknown"))

    broken = missing + unbound
    if broken:
        detail_parts = []
        if missing:
            detail_parts.append(
                f"Missing: {', '.join(missing[:5])}" + ("..." if len(missing) > 5 else "")
            )
        if unbound:
            detail_parts.append(
                f"No task_file: {', '.join(unbound[:5])}" + ("..." if len(unbound) > 5 else "")
            )
        return DoctorCheck(
            name="task_files",
            status="error",
            message=f"{len(broken)} task file(s) missing",
            detail="; ".join(detail_parts),
            fix="lra doctor --fix  # 用模板重建缺失的任务书",
            category="tasks",
        )

    return DoctorCheck(
        name="task_files",
        status="ok",
        message=f"All {len(tasks)} task files exist",
        category="tasks",
    )


def fix_missing_task_files(path: str, dry_run: bool = False) -> Dict[str, Any]:
    """重建缺失的任务书

    只用 task_list 里已有的信息重建：template + description（+ variables）。
    原始的 requirements / acceptance / design 如果创建时没被记录，
    重建出来的任务书只有占位符，需要人工补 —— 这一点会写进返回值。

    任务书路径由 Config 相对当前工作目录解析，所以整个过程在目标项目目录下执行。
    """
    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    data = SafeJson.read(task_list_path)
    if not data:
        return {"ok": False, "error": "task_list_unreadable", "rebuilt": [], "failed": []}

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        return {"ok": False, "error": "task_list_malformed", "rebuilt": [], "failed": []}

    from lra.template_manager import TemplateManager

    rebuilt: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []
    changed = False
    now = datetime.now().isoformat()

    origin_cwd = os.getcwd()
    try:
        os.chdir(path)
        tm = TemplateManager()
        for task in tasks:
            tid = task.get("id")
            if not tid:
                continue
            expected = task.get("task_file") or f"tasks/{tid}.md"
            expected_abs = os.path.join(Config.get_metadata_dir(), expected)
            if os.path.exists(expected_abs):
                continue

            template = task.get("template") or "task"
            description = task.get("description") or ""
            variables = task.get("variables") or None

            if dry_run:
                rebuilt.append({"id": tid, "template": template})
                continue

            ok, detail = tm.create_task_file(tid, template, description, variables)
            if not ok:
                failed.append({"id": tid, "error": str(detail)})
                continue

            # create_task_file 写到规范路径 tasks/{tid}.md；
            # 记录里写的是别的路径时把它搬过去
            canonical = os.path.join(Config.get_tasks_dir(), f"{tid}.md")
            if os.path.abspath(canonical) != os.path.abspath(expected_abs):
                os.makedirs(os.path.dirname(expected_abs), exist_ok=True)
                shutil.move(canonical, expected_abs)

            if task.get("task_file") != expected:
                task["task_file"] = expected
            task["updated_at"] = now
            changed = True
            rebuilt.append({"id": tid, "template": template})
    finally:
        os.chdir(origin_cwd)

    if changed and not dry_run:
        # 与去重修复保持一致：动手前先留一份快照
        backup_dir = os.path.join(path, Config.METADATA_DIR, Config.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(
            backup_dir, f"task_list.json.pre-rebuild.{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        try:
            shutil.copy2(task_list_path, backup_path)
        except OSError:
            pass

        if not SafeJson.write(task_list_path, data):
            return {"ok": False, "error": "write_failed", "rebuilt": rebuilt, "failed": failed}

    return {
        "ok": True,
        "rebuilt": rebuilt,
        "failed": failed,
        "count": len(rebuilt),
        "dry_run": dry_run,
    }



def check_duplicate_task_ids(path: str) -> DoctorCheck:
    """Check for duplicate task IDs in task_list.json

    重复 ID 是最危险的数据完整性问题：读取任务时只能命中其中一条，
    worker 因此可能拿到另一条记录的任务书（issue #2）。
    """
    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    data = SafeJson.read(task_list_path)
    if not data:
        return DoctorCheck(
            name="duplicate_task_ids",
            status="ok",
            message="No task_list to check",
            category="tasks",
        )

    groups = {}
    for task in data.get("tasks", []):
        tid = task.get("id")
        if tid:
            groups.setdefault(tid, []).append(task)

    duplicates = {tid: recs for tid, recs in groups.items() if len(recs) > 1}

    if duplicates:
        names = ", ".join(list(duplicates)[:5]) + ("..." if len(duplicates) > 5 else "")
        return DoctorCheck(
            name="duplicate_task_ids",
            status="error",
            message=f"{len(duplicates)} duplicate task id(s) found",
            detail=(
                f"Duplicated: {names} "
                "(每个 ID 有多条记录；读取任务时会拿到错误的记录)"
            ),
            fix="lra doctor --fix  # 重新编号冲突记录",
            category="tasks",
        )

    return DoctorCheck(
        name="duplicate_task_ids",
        status="ok",
        message="No duplicate task ids",
        category="tasks",
    )


def _reserved_ids_and_files(path: str, tasks: List[Dict[str, Any]]) -> set:
    """已被占用的 ID：task_list 中的记录 + tasks/ 目录下已存在的 md 文件名"""
    reserved = {t.get("id") for t in tasks if t.get("id")}
    tasks_dir = os.path.join(path, Config.METADATA_DIR, Config.TASKS_DIR)
    if os.path.isdir(tasks_dir):
        for filename in os.listdir(tasks_dir):
            if filename.endswith(".md"):
                reserved.add(filename[:-3])
    return reserved


def _next_free_id(old_id: str, reserved: set, known_ids: set) -> str:
    """为一条重复记录分配一个未被占用的新 ID

    - 子任务（``{parent}_{NN}``）保持父任务前缀，在父任务下顺延
    - 顶层任务（``task_NNN``）在全局最大编号后顺延
    - 其它格式无法安全推断父级，退回全局 task_NNN 序列
    """
    m = re.match(r"^(?P<base>.+)_(?P<num>\d+)$", old_id or "")
    if m and m.group("base") in known_ids:
        parent = m.group("base")
        n = int(m.group("num"))
        while f"{parent}_{n:02d}" in reserved:
            n += 1
        return f"{parent}_{n:02d}"

    max_num = 0
    for tid in reserved:
        tm = re.match(r"^task_(\d+)$", tid or "")
        if tm:
            max_num = max(max_num, int(tm.group(1)))
    num = max_num + 1
    while f"task_{num:03d}" in reserved:
        num += 1
    return f"task_{num:03d}"


def _find_task_book_owner(path: str, group: List[Dict[str, Any]], tid: str) -> int:
    """判断一组同 ID 记录中，谁真正拥有磁盘上的那份任务书

    撞号意味着多条记录共用同一个 md 文件，而文件里只会留下最后一次写入
    的内容。任务书正文里带着该任务的描述，用它做匹配可以确定主人；
    匹配不上（人工改过等）则退回"最后创建的那条"—— 也就是最后写文件的那条。
    """
    for task in group:
        rel = task.get("task_file") or f"tasks/{tid}.md"
        abs_path = os.path.join(path, Config.METADATA_DIR, rel)
        if not os.path.exists(abs_path):
            continue
        try:
            with open(abs_path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            break
        matches = [
            i
            for i, t in enumerate(group)
            if (t.get("description") or "").strip() and (t.get("description") or "").strip() in text
        ]
        if len(matches) == 1:
            return matches[0]
        # 内容对不上 → 取 created_at 最晚的那条（最后写文件的人）
        return max(
            range(len(group)),
            key=lambda i: (group[i].get("created_at") or "", i),
        )
    # 没有物理任务书 → 保持原状，第一条记录沿用原 ID
    return 0


def fix_duplicate_task_ids(path: str, dry_run: bool = False) -> Dict[str, Any]:
    """修复 task_list.json 中的重复任务 ID

    策略：

    1. 一组同 ID 的记录里，**拥有磁盘任务书的那条保留原 ID**（任务书正文
       里的描述决定了主人），其余记录分配新 ID；
    2. 失去任务书的记录把 ``task_file`` 清空 —— 继续指向那份文件只会让
       worker 读到描述别的任务的任务书，正是本次要消除的串台；
    3. 依赖与父子关系不改写：它们指向的 ID 字符串保持不变，只是从
       "随机命中某一条"变成"确定命中唯一一条"。

    修复前会自动在 ``backup/`` 留一份 task_list.json 快照。
    """
    task_list_path = os.path.join(path, Config.METADATA_DIR, Config.TASK_LIST_FILE)
    data = SafeJson.read(task_list_path)
    if not data:
        return {"ok": False, "error": "task_list_unreadable", "fixed": []}

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        return {"ok": False, "error": "task_list_malformed", "fixed": []}

    groups: Dict[str, List[int]] = {}
    for idx, task in enumerate(tasks):
        tid = task.get("id")
        if tid:
            groups.setdefault(tid, []).append(idx)

    duplicated = {tid: idxs for tid, idxs in groups.items() if len(idxs) > 1}
    if not duplicated:
        return {"ok": True, "fixed": [], "count": 0, "dry_run": dry_run}

    known_ids = set(groups.keys())
    reserved = _reserved_ids_and_files(path, tasks)

    fixed: List[Dict[str, str]] = []
    lost: List[Dict[str, str]] = []
    now = datetime.now().isoformat()

    for tid, idxs in duplicated.items():
        group = [tasks[i] for i in idxs]
        owner_pos = _find_task_book_owner(path, group, tid)
        owner_idx = idxs[owner_pos]

        for idx in idxs:
            if idx == owner_idx:
                continue
            task = tasks[idx]
            new_id = _next_free_id(tid, reserved, known_ids)
            reserved.add(new_id)

            if not dry_run:
                task["id"] = new_id
                task["task_file"] = ""  # 任务书归主人这条，被撞号的那条没有自己的
                task["updated_at"] = now

            entry = {
                "old_id": tid,
                "new_id": new_id,
                "description": (task.get("description") or "")[:60],
            }
            fixed.append(entry)
            lost.append(entry)

    if not dry_run and fixed:
        backup_dir = os.path.join(path, Config.METADATA_DIR, Config.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(
            backup_dir, f"task_list.json.pre-dedupe.{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        try:
            shutil.copy2(task_list_path, backup_path)
        except OSError:
            backup_path = ""

        if not SafeJson.write(task_list_path, data):
            return {"ok": False, "error": "write_failed", "fixed": fixed, "lost": lost}

    return {
        "ok": True,
        "fixed": fixed,
        "lost": lost,
        "count": len(fixed),
        "dry_run": dry_run,
    }


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
        check_runtime_dependencies(path),
        check_installation(path),
        check_task_list_valid(path),
        check_locks_valid(path),
        check_constitution_valid(path),
        check_task_files(path),
        check_duplicate_task_ids(path),
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
