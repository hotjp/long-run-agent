"""Relay orchestrator — main loop driving the automated execution cycle."""

import asyncio
import atexit
import fcntl
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from lra.config import Config
from lra.relay.agent_runner import AgentRunner, TaskRunResult
from lra.relay.backoff import ExponentialBackoff
from lra.relay.git_utils import GitError, GitUtils
from lra.relay.notes_store import NotesStore
from lra.relay.structured_output import write_schema_file
from lra.relay.task_queue import TaskQueue


class RelayOrchestrator:
    """Main relay orchestrator that runs the automated task loop.

    Design principles:
    - No relay branch — all commits go directly to the current branch
    - Per-stage commits for crash recovery (each stage = one git commit)
    - Single-instance enforcement via file lock (one relay per repo at a time)
    - Crash recovery: read ralph.iteration, resume from next stage

    Loop:
    1. Verify preconditions (git clean, project initialized)
    2. Acquire file lock (single-instance per repo)
    3. Get next task from queue
    4. AgentRunner.run_task() — runs all 7 stages, each stage committed immediately
    5. On success: release lock
    6. On Constitution failure: release lock, next relay run resumes from current iteration
    7. On exit: cleanup locks, close agent进程
    """

    def __init__(
        self,
        task_queue: TaskQueue,
        adapter,  # ClaudeAdapter
        constitution_manager,  # ConstitutionManager
        run_dir: Path,
        max_steps: int = 50,
    ):
        self.queue = task_queue
        self.adapter = adapter
        self.constitution = constitution_manager
        self.run_dir = run_dir
        self.max_steps = max_steps

        self.notes = NotesStore(run_dir / "notes.md")
        self.backoff = ExponentialBackoff()
        self.git = GitUtils()

        self._global_step = 0
        self._current_task_id: Optional[str] = None
        self._should_stop_flag = False
        self._lock_fd: Optional[int] = None

        atexit.register(self._emergency_cleanup)

    def _acquire_file_lock(self, cwd: Path) -> bool:
        """Acquire exclusive file lock to prevent concurrent relay instances."""
        lock_path = Path(Config.get_metadata_dir()) / ".relay.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, OSError):
            os.close(self._lock_fd)
            self._lock_fd = None
            return False

    def _release_file_lock(self) -> None:
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except (IOError, OSError):
                pass
            self._lock_fd = None

    async def run(self) -> dict:
        """Run the relay orchestrator. Returns summary dict."""
        cwd = Path.cwd()
        summary = {
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "errors": [],
        }

        # 1. Precondition checks
        try:
            self.git.ensure_clean_working_tree(cwd)
        except GitError as e:
            summary["errors"].append(f"Git safety check failed: {e}")
            return summary

        # Check project initialized
        if not Path(Config.get_task_list_path()).exists():
            summary["errors"].append("Project not initialized (run lra init)")
            return summary

        # 2. Single-instance lock
        if not self._acquire_file_lock(cwd):
            summary["errors"].append("Another relay instance is already running in this repo")
            return summary

        # Write output schema for Claude CLI
        schema_path = self.run_dir / "output-schema.json"
        write_schema_file(schema_path)

        try:
            while not self._should_stop():
                # Check abort condition (per-task backoff)
                if self.backoff.should_abort:
                    summary["errors"].append(
                        f"Abort after {self.backoff.consecutive_failures} consecutive failures"
                    )
                    break

                # Backoff wait for hard errors
                if self.backoff.should_wait_before_retry:
                    wait_secs = self.backoff.backoff_duration
                    await asyncio.sleep(wait_secs)

                # Get next task
                task = self.queue.get_next_task()
                if task is None:
                    break

                self._current_task_id = task["id"]

                # Fresh backoff per task (per-task, not global across all tasks)
                self.backoff = ExponentialBackoff()

                # Build agent runner
                runner = AgentRunner(
                    adapter=self.adapter,
                    notes_store=self.notes,
                    backoff=self.backoff,
                    locks_manager=self.queue.lm,
                    task_manager=self.queue.tm,
                    git_utils=self.git,
                    repo_root=cwd,
                )

                # Run task through all Ralph Loop stages
                attempt = self.notes.get_task_attempts(task["id"]) + 1
                result: TaskRunResult = await runner.run_task(task, attempt, self.run_dir)
                self._global_step += 1
                summary["tasks_processed"] += 1

                # Handle result
                if result.success:
                    self._on_task_success(task, result, summary)
                else:
                    self._on_task_failure(task, result, summary)

                # Invalidate cache
                self.queue.invalidate_cache()

        finally:
            self._emergency_cleanup()

        summary["completed_at"] = datetime.now().isoformat()
        return summary

    def _on_task_success(self, task: dict, result: TaskRunResult, summary: dict) -> None:
        """Handle successful task completion."""
        task_id = task["id"]

        # Write notes
        attempt = self.notes.get_task_attempts(task_id) + 1
        self.notes.append(
            task_id=task_id,
            attempt=attempt,
            summary=result.summary,
            changes=result.key_changes,
            learnings=result.key_learnings,
        )

        # Release lock (AgentRunner already called update_status("completed"))
        self.queue.lm.release(task_id)

        self.backoff.record_success()
        summary["tasks_succeeded"] += 1
        self._current_task_id = None

    def _on_task_failure(self, task: dict, result: TaskRunResult, summary: dict) -> None:
        """Handle Constitution failure — do NOT reset_hard (stages already committed).

        The task's ralph.iteration is at the last passed stage. Next relay run
        will resume from the next stage. Duplicate work on retry is acceptable
        since stages are idempotent.
        """
        task_id = task["id"]

        # Write notes
        attempt = self.notes.get_task_attempts(task_id) + 1
        self.notes.append(
            task_id=task_id,
            attempt=attempt,
            summary=f"[FAILED] {result.summary}",
            changes=[],
            learnings=result.key_learnings + result.errors,
        )

        # Release lock so task can be retried
        self.queue.lm.release(task_id)

        summary["tasks_failed"] += 1
        summary["errors"].extend([f"{task_id}: {e}" for e in result.errors])
        self._current_task_id = None

    def _should_stop(self) -> bool:
        if self._should_stop_flag:
            return True
        if self.max_steps and self._global_step >= self.max_steps:
            return True
        return False

    def _emergency_cleanup(self) -> None:
        """Ensure: release locks, close agent进程, flush logs."""
        self._release_file_lock()
        if self._current_task_id:
            try:
                self.queue.lm.release(self._current_task_id)
            except Exception:
                pass
        self.adapter.shutdown()
        self._current_task_id = None

    def stop(self) -> None:
        """Signal orchestrator to stop after current task."""
        self._should_stop_flag = True
