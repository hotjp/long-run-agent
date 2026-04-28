"""Relay orchestrator — main loop driving the automated execution cycle."""

import asyncio
import atexit
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

    Each "step" = one task going through all 7 Ralph Loop stages.
    The AgentRunner handles stage iteration internally.

    Loop:
    1. Verify preconditions (git clean, project initialized)
    2. Create isolated relay/{timestamp} branch
    3. Get next task from queue
    4. AgentRunner.run_task() — runs all 7 stages internally
    5. On success: git commit + release lock
    6. On Constitution failure: reset_hard + retry
    7. On 3 consecutive failures: abort
    8. On exit: cleanup locks, close agent进程
    """

    def __init__(
        self,
        task_queue: TaskQueue,
        adapter,  # ClaudeAdapter
        constitution_manager,  # ConstitutionManager
        run_dir: Path,
        max_steps: int = 50,
        branch_name: Optional[str] = None,
    ):
        self.queue = task_queue
        self.adapter = adapter
        self.constitution = constitution_manager
        self.run_dir = run_dir
        self.max_steps = max_steps
        self.branch_name = branch_name or f"relay/{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.notes = NotesStore(run_dir / "notes.md")
        self.backoff = ExponentialBackoff()
        self.git = GitUtils()

        self._global_step = 0
        self._current_task_id: Optional[str] = None
        self._original_branch: Optional[str] = None
        self._should_stop_flag = False

        atexit.register(self._emergency_cleanup)

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
            "relay_branch": self.branch_name,
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

        # 2. Create relay branch
        self._original_branch = self.git.get_current_branch(cwd)
        try:
            self.git.create_branch(self.branch_name, cwd)
        except GitError:
            # Branch exists, switch to it
            self.git._git(["checkout", self.branch_name], cwd)

        # Write output schema for Claude CLI
        schema_path = self.run_dir / "output-schema.json"
        write_schema_file(schema_path)

        try:
            while not self._should_stop():
                # Check abort condition (3 consecutive failures)
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

                # Build agent runner WITH TaskManager
                runner = AgentRunner(
                    adapter=self.adapter,
                    notes_store=self.notes,
                    backoff=self.backoff,
                    locks_manager=self.queue.lm,
                    task_manager=self.queue.tm,
                )

                # Run task through all Ralph Loop stages
                attempt = self.notes.get_task_attempts(task["id"]) + 1
                result: TaskRunResult = await runner.run_task(task, attempt, self.run_dir)
                self._global_step += 1
                summary["tasks_processed"] += 1

                # Handle result
                if result.success:
                    self._commit_and_advance(task, result, summary)
                else:
                    self._rollback_and_retry(task, result, summary)

                # Invalidate cache
                self.queue.invalidate_cache()

        finally:
            self._emergency_cleanup()

        summary["completed_at"] = datetime.now().isoformat()
        return summary

    def _commit_and_advance(self, task: dict, result: TaskRunResult, summary: dict) -> None:
        """Commit changes after successful task completion."""
        task_id = task["id"]
        cwd = Path.cwd()

        # Git commit
        stg = f"{result.iterations_completed}/7 stages"
        commit_msg = f"relay {task_id}: {result.summary[:50]} ({stg})"
        self.git.add_all(cwd)
        self.git.commit(commit_msg, cwd)

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

    def _rollback_and_retry(self, task: dict, result: TaskRunResult, summary: dict) -> None:
        """Rollback and retry task after Constitution failure."""
        task_id = task["id"]
        cwd = Path.cwd()

        # Reset + clean to rollback changes
        self.git.reset_hard(cwd)

        # Write notes
        attempt = self.notes.get_task_attempts(task_id) + 1
        self.notes.append(
            task_id=task_id,
            attempt=attempt,
            summary=f"[ROLLED BACK] {result.summary}",
            changes=[],
            learnings=result.key_learnings + result.errors,
        )

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
