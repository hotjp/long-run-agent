"""Task queue with caching over TaskManager.get_ready_tasks()."""

import os
from typing import Optional

from lra.config import Config
from lra.locks_manager import LocksManager
from lra.task_manager import TaskManager


class TaskQueue:
    """Task queue with mtime-based caching over TaskManager.get_ready_tasks()."""

    def __init__(
        self,
        task_manager: Optional[TaskManager] = None,
        locks_manager: Optional[LocksManager] = None,
    ):
        self.tm = task_manager or TaskManager()
        self.lm = locks_manager or LocksManager()
        self._cache_mtime: float = 0
        self._cached_ready_tasks: list[dict] = []

    def get_next_task(self) -> Optional[dict]:
        """Return highest-priority available task."""
        ready = self._get_ready_tasks_cached()

        # Filter out already-claimed tasks
        available = []
        for task in ready:
            task_id = task["id"]
            can_claim, _ = self.lm.can_claim(task_id)
            if can_claim:
                available.append(task)

        if not available:
            return None

        # Sort by priority (P0 > P1 > P2 > P3)
        priority_weights = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        available.sort(key=lambda t: priority_weights.get(t.get("priority", "P3"), 3))
        return available[0]

    def _get_ready_tasks_cached(self) -> list[dict]:
        """Get ready tasks, using cache if task_list.json hasn't changed."""
        task_list_path = Config.get_task_list_path()
        try:
            mtime = os.path.getmtime(task_list_path)
        except OSError:
            mtime = 0

        if mtime > self._cache_mtime:
            self._cached_ready_tasks = self.tm.get_ready_tasks(
                locks_manager=self.lm,
                sort="priority",
            )
            self._cache_mtime = mtime

        return self._cached_ready_tasks

    def invalidate_cache(self) -> None:
        """Invalidate cache after task status changes."""
        self._cache_mtime = 0

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get single task by ID (bypasses cache)."""
        return self.tm.get(task_id)
