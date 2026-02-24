#!/usr/bin/env python3
"""
任务锁管理器
v3.1 - 支持层级锁、多 Agent 协调
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

from .config import Config, SafeJson, HEARTBEAT_INTERVAL_MINUTES, ORPHAN_THRESHOLD_MINUTES
from .task_manager import TaskManager


class LockStatus:
    FREE = "free"
    CLAIMED = "claimed"
    PAUSED = "paused"
    ORPHANED = "orphaned"
    LOCKED_BY_PARENT = "locked_by_parent"


class LocksManager:
    def __init__(self):
        self.locks_path = Config.get_locks_path()
        self.task_manager = TaskManager()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.locks_path):
            SafeJson.write(self.locks_path, {"locks": {}})

    def _load(self) -> Dict[str, Any]:
        data = SafeJson.read(self.locks_path)
        return data if data else {"locks": {}}

    def _save(self, data: Dict[str, Any]) -> bool:
        return SafeJson.write(self.locks_path, data)

    def _generate_session_id(self, task_id: str) -> str:
        ts = datetime.now().strftime("%Y%m%d%H%M")
        short = str(uuid4())[:4]
        return f"{task_id}_{ts}_{short}"

    def _check_orphan(self, lock: Dict[str, Any]) -> bool:
        if lock.get("status") != LockStatus.CLAIMED:
            return False
        last_heartbeat = lock.get("last_heartbeat") or lock.get("claimed_at")
        if not last_heartbeat:
            return True
        try:
            last = datetime.fromisoformat(last_heartbeat)
            threshold = timedelta(minutes=ORPHAN_THRESHOLD_MINUTES)
            return datetime.now() - last > threshold
        except:
            return True

    def get_lock(self, task_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        return data.get("locks", {}).get(task_id)

    def _get_parent_id(self, task_id: str) -> Optional[str]:
        task = self.task_manager.get(task_id)
        return task.get("parent_id") if task else None

    def _get_children_ids(self, task_id: str) -> List[str]:
        children = self.task_manager.get_children(task_id)
        return [c["id"] for c in children]

    def claim(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        data = self._load()
        locks = data.get("locks", {})
        now = datetime.now().isoformat()

        parent_id = self._get_parent_id(task_id)
        if parent_id:
            parent_lock = locks.get(parent_id)
            if parent_lock and parent_lock.get("status") == LockStatus.CLAIMED:
                return False, {"error": "parent_locked", "parent": parent_id}

        existing = locks.get(task_id)
        if existing:
            if self._check_orphan(existing):
                existing["status"] = LockStatus.ORPHANED
            elif existing.get("status") == LockStatus.LOCKED_BY_PARENT:
                pass
            elif existing.get("status") == LockStatus.PAUSED:
                pass
            elif existing.get("status") == LockStatus.CLAIMED:
                return False, {"error": "already_claimed", "lock": existing}

        session_id = self._generate_session_id(task_id)
        lock = {
            "session_id": session_id,
            "task_id": task_id,
            "status": LockStatus.CLAIMED,
            "claimed_at": now,
            "last_heartbeat": now,
            "checkpoint": None,
        }
        locks[task_id] = lock

        children = self._get_children_ids(task_id)
        for child_id in children:
            if child_id not in locks or locks[child_id].get("status") in [LockStatus.FREE, None]:
                locks[child_id] = {
                    "task_id": child_id,
                    "status": LockStatus.LOCKED_BY_PARENT,
                    "locked_by": task_id,
                    "locked_at": now,
                }

        data["locks"] = locks
        self._save(data)
        return True, {
            "session_id": session_id,
            "task_id": task_id,
            "children_locked": len(children),
        }

    def publish_children(self, task_id: str) -> Tuple[bool, str]:
        data = self._load()
        locks = data.get("locks", {})

        if task_id not in locks or locks[task_id].get("status") != LockStatus.CLAIMED:
            return False, "not_claimed"

        children = self._get_children_ids(task_id)
        released = 0
        for child_id in children:
            if child_id in locks and locks[child_id].get("status") == LockStatus.LOCKED_BY_PARENT:
                if locks[child_id].get("locked_by") == task_id:
                    locks[child_id] = {
                        "task_id": child_id,
                        "status": LockStatus.FREE,
                        "published_by": task_id,
                        "published_at": datetime.now().isoformat(),
                    }
                    released += 1

        locks[task_id]["children_published"] = True
        data["locks"] = locks
        self._save(data)
        return True, f"released {released} children"

    def pause(
        self, task_id: str, note: str = "", completed: List[str] = None, remaining: List[str] = None
    ) -> Tuple[bool, str]:
        data = self._load()
        locks = data.get("locks", {})
        lock = locks.get(task_id)

        if not lock:
            return False, "not_claimed"

        lock["status"] = LockStatus.PAUSED
        lock["paused_at"] = datetime.now().isoformat()
        lock["checkpoint"] = {
            "note": note,
            "completed": completed or [],
            "remaining": remaining or [],
            "timestamp": datetime.now().isoformat(),
        }

        data["locks"] = locks
        self._save(data)
        return True, "paused"

    def checkpoint(
        self,
        task_id: str,
        note: str = "",
        completed: List[str] = None,
        remaining: List[str] = None,
        files_changed: List[str] = None,
    ) -> Tuple[bool, str]:
        data = self._load()
        locks = data.get("locks", {})
        lock = locks.get(task_id)

        if not lock:
            return False, "not_claimed"

        lock["checkpoint"] = {
            "note": note,
            "completed": completed or [],
            "remaining": remaining or [],
            "files_changed": files_changed or [],
            "timestamp": datetime.now().isoformat(),
        }
        lock["last_heartbeat"] = datetime.now().isoformat()

        data["locks"] = locks
        self._save(data)
        return True, "checkpointed"

    def heartbeat(self, task_id: str) -> Tuple[bool, str]:
        data = self._load()
        locks = data.get("locks", {})
        lock = locks.get(task_id)

        if not lock:
            return False, "not_claimed"

        if lock.get("status") != LockStatus.CLAIMED:
            return False, "not_active"

        lock["last_heartbeat"] = datetime.now().isoformat()
        data["locks"] = locks
        self._save(data)
        return True, "ok"

    def release(self, task_id: str) -> Tuple[bool, str]:
        data = self._load()
        locks = data.get("locks", {})

        if task_id in locks:
            lock = locks[task_id]
            if lock.get("status") == LockStatus.LOCKED_BY_PARENT:
                return False, "locked_by_parent"

            children = self._get_children_ids(task_id)
            for child_id in children:
                if child_id in locks and locks[child_id].get("locked_by") == task_id:
                    del locks[child_id]

            del locks[task_id]
            data["locks"] = locks
            self._save(data)
            return True, "released"
        return False, "not_found"

    def resume(self, task_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        lock = data.get("locks", {}).get(task_id)

        if not lock:
            return None

        if lock.get("status") in [LockStatus.PAUSED, LockStatus.ORPHANED]:
            return {
                "task_id": task_id,
                "status": lock["status"],
                "checkpoint": lock.get("checkpoint"),
                "claimed_at": lock.get("claimed_at"),
                "can_resume": True,
            }
        return None

    def get_resumable(self) -> List[Dict[str, Any]]:
        data = self._load()
        locks = data.get("locks", {})
        result = []

        for tid, lock in locks.items():
            if lock.get("status") in [LockStatus.PAUSED, LockStatus.ORPHANED]:
                result.append(
                    {
                        "task_id": tid,
                        "status": lock["status"],
                        "checkpoint_note": (lock.get("checkpoint") or {}).get("note", ""),
                    }
                )
        return result

    def get_all_locks(self) -> Dict[str, Dict[str, Any]]:
        data = self._load()
        return data.get("locks", {})

    def cleanup_orphans(self) -> int:
        data = self._load()
        locks = data.get("locks", {})
        count = 0

        for tid, lock in locks.items():
            if self._check_orphan(lock):
                lock["status"] = LockStatus.ORPHANED
                count += 1

        if count > 0:
            data["locks"] = locks
            self._save(data)
        return count

    def can_claim(self, task_id: str) -> Tuple[bool, str]:
        data = self._load()
        locks = data.get("locks", {})

        parent_id = self._get_parent_id(task_id)
        if parent_id:
            parent_lock = locks.get(parent_id)
            if parent_lock and parent_lock.get("status") == LockStatus.CLAIMED:
                return False, "parent_locked"

        lock = locks.get(task_id)
        if not lock:
            return True, "ok"

        if lock.get("status") == LockStatus.LOCKED_BY_PARENT:
            return False, "locked_by_parent"

        if lock.get("status") == LockStatus.CLAIMED:
            if self._check_orphan(lock):
                return True, "ok_orphaned"
            return False, "already_claimed"

        if lock.get("status") == LockStatus.PAUSED:
            return True, "ok_resumable"

        return True, "ok"
