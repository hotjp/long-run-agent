"""Agent runner — task execution lifecycle with full Ralph Loop."""

import asyncio
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lra.config import Config, FileLock
from lra.locks_manager import LocksManager
from lra.relay.backoff import ExponentialBackoff
from lra.relay.claude_adapter import ClaudeAdapter
from lra.relay.notes_store import NotesStore
from lra.relay.structured_output import AgentOutput, validate_output


@dataclass
class IterationResult:
    success: bool
    summary: str
    key_changes: list[str]
    key_learnings: list[str]
    error: Optional[str] = None
    schema_valid: bool = True  # False = hard error (JSON parse failure)
    stage_passed: bool = False  # True = Constitution gates passed for this stage
    final: bool = False  # True = all 7 stages completed


@dataclass
class TaskRunResult:
    """Result of running a task through all Ralph Loop stages."""

    success: bool
    summary: str
    key_changes: list[str]
    key_learnings: list[str]
    iterations_completed: int  # How many stages finished
    errors: list[str]


class AgentRunner:
    """Manages full task lifecycle with Ralph Loop iteration.

    For each task, runs through 7 stages:
    1. Agent does stage work
    2. Constitution gates for that stage run
    3. If pass and not last stage: advance to next stage
    4. If all 7 stages pass: task is completed
    5. If any stage fails: rollback and retry (up to max_errors)
    """

    HEARTBEAT_INTERVAL_SECONDS = 240  # 4 minutes

    def __init__(
        self,
        adapter: ClaudeAdapter,
        notes_store: NotesStore,
        backoff: ExponentialBackoff,
        locks_manager: LocksManager,
        task_manager,  # TaskManager instance
    ):
        self.adapter = adapter
        self.notes = notes_store
        self.backoff = backoff
        self.lm = locks_manager
        self.tm = task_manager
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat = threading.Event()

    async def run_task(
        self,
        task: dict,
        attempt: int,
        run_dir: Path,
    ) -> TaskRunResult:
        """Execute a task through all Ralph Loop stages."""
        task_id = task["id"]

        # 1. Claim task
        claim_ok, claim_info = self.lm.claim(task_id)
        if not claim_ok:
            return TaskRunResult(
                success=False,
                summary="",
                key_changes=[],
                key_learnings=[],
                iterations_completed=0,
                errors=[f"Failed to claim: {claim_info}"],
            )

        # 2. Start heartbeat
        self._start_heartbeat(task_id)

        try:
            # 3. Ralph Loop: iterate through all 7 stages
            return await self._run_ralph_loop(task, attempt, run_dir)

        except Exception as e:
            self.backoff.record_error()
            return TaskRunResult(
                success=False,
                summary="",
                key_changes=[],
                key_learnings=[],
                iterations_completed=0,
                errors=[f"Agent crashed: {type(e).__name__}: {e}"],
            )

        finally:
            self._stop_heartbeat.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=5)
            self.adapter.shutdown()

    async def _run_ralph_loop(
        self,
        task: dict,
        attempt: int,
        run_dir: Path,
    ) -> TaskRunResult:
        """Run all 7 Ralph Loop stages for a task."""
        task_id = task["id"]
        all_changes: list[str] = []
        all_learnings: list[str] = []
        final_summary = ""

        # Load fresh task to get current ralph.iteration
        fresh_task = self.tm.get(task_id)
        if not fresh_task:
            return TaskRunResult(
                success=False,
                summary="",
                key_changes=[],
                key_learnings=[],
                iterations_completed=0,
                errors=["Task not found"],
            )

        current_iteration = fresh_task.get("ralph", {}).get("iteration", 0)
        max_iterations = fresh_task.get("ralph", {}).get("max_iterations", 7)

        # Stages 0 through 6 (7 total stages)
        for stage_idx in range(current_iteration, max_iterations):
            stage_num = stage_idx + 1  # Human-readable: 1-7

            # Run Claude agent for this stage
            prompt = self._build_stage_prompt(task, stage_num, run_dir)
            log_path = run_dir / f"attempt-{attempt}-stage-{stage_num}-{task_id}.jsonl"

            result = await asyncio.to_thread(
                self.adapter.run,
                prompt=prompt,
                cwd=run_dir,
                log_path=log_path,
            )

            # Validate output
            try:
                output = AgentOutput.from_dict(result.output)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.backoff.record_error()
                return TaskRunResult(
                    success=False,
                    summary="",
                    key_changes=all_changes,
                    key_learnings=all_learnings,
                    iterations_completed=stage_idx,
                    errors=[f"Stage {stage_num}: Schema validation failed: {e}"],
                )

            valid, errors = validate_output(result.output)
            if not valid:
                self.backoff.record_error()
                return TaskRunResult(
                    success=False,
                    summary="",
                    key_changes=all_changes,
                    key_learnings=all_learnings,
                    iterations_completed=stage_idx,
                    errors=[f"Stage {stage_num}: Output validation errors: {errors}"],
                )

            if not output.success:
                self.backoff.record_failure()
                return TaskRunResult(
                    success=False,
                    summary=output.summary,
                    key_changes=all_changes,
                    key_learnings=all_learnings + output.key_learnings,
                    iterations_completed=stage_idx,
                    errors=[f"Stage {stage_num}: Agent reported failure: {output.summary}"],
                )

            all_changes.extend(output.key_changes)
            all_learnings.extend(output.key_learnings)
            final_summary = output.summary

            # Run Constitution gates for this stage (stage 1-7)
            gate_result = self._run_stage_gates(task_id, stage_num)
            if not gate_result["passed"]:
                failed_gates = [g["name"] for g in gate_result["gates"] if not g["passed"]]
                self.backoff.record_failure()
                return TaskRunResult(
                    success=False,
                    summary=final_summary,
                    key_changes=all_changes,
                    key_learnings=all_learnings,
                    iterations_completed=stage_idx,
                    errors=[f"Stage {stage_num}: Constitution gates failed: {failed_gates}"],
                )

            # Stage passed. If not last stage, advance to next.
            if stage_num < max_iterations:
                ok, new_iter = self._advance_stage(task_id, stage_num)
                if not ok:
                    return TaskRunResult(
                        success=False,
                        summary=final_summary,
                        key_changes=all_changes,
                        key_learnings=all_learnings,
                        iterations_completed=stage_idx,
                        errors=[f"Stage {stage_num}: Failed to advance to stage {stage_num + 1}"],
                    )

        # All 7 stages passed — mark task as completed
        self._mark_completed(task_id)
        self.backoff.record_success()

        return TaskRunResult(
            success=True,
            summary=final_summary,
            key_changes=all_changes,
            key_learnings=all_learnings,
            iterations_completed=7,
            errors=[],
        )

    def _run_stage_gates(self, task_id: str, stage: int) -> dict:
        """Run Constitution iteration gates for a stage."""
        return self.tm.run_iteration_gates(task_id, stage)

    def _advance_stage(self, task_id: str, current_stage: int) -> tuple:
        """Advance to next Ralph Loop stage. Returns (ok, new_iteration)."""
        # Check if we can advance
        task = self.tm.get(task_id)
        if not task:
            return False, 0

        ralph = task.get("ralph", {})
        if ralph.get("iteration", 0) >= ralph.get("max_iterations", 7):
            return False, 0

        # Increment iteration
        ok, new_iter = self.tm.increment_iteration(task_id)
        if not ok:
            return False, 0

        # Update status to optimizing
        self.tm.update_status(task_id, "optimizing", force=True)

        return True, new_iter

    def _mark_completed(self, task_id: str) -> None:
        """Mark task as completed after all stages pass."""
        with FileLock(Config.get_task_list_path()):
            self.tm.update_status(task_id, "completed")

    def _start_heartbeat(self, task_id: str) -> None:
        """Start background thread that sends heartbeat every 4 minutes."""

        def heartbeat_loop():
            while not self._stop_heartbeat.wait(self.HEARTBEAT_INTERVAL_SECONDS):
                try:
                    self.lm.heartbeat(task_id)
                except Exception:
                    pass

        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _build_stage_prompt(self, task: dict, stage: int, run_dir: Path) -> str:
        """Build prompt for a specific Ralph Loop stage.

        The Agent is fully autonomous — it reads the task file, detects project
        type, runs whatever tools are appropriate, and reports results.
        Constitution gates validate AFTER the agent reports, not during.
        """
        task_id = task["id"]
        task_file = task.get("task_file", f"tasks/{task['id']}.md")

        stage_names = [
            "理解规划",  # 1
            "基础实现",  # 2
            "功能完善",  # 3
            "质量提升",  # 4
            "优化改进",  # 5
            "验证测试",  # 6
            "交付准备",  # 7
        ]
        stage_name = stage_names[stage - 1] if stage <= 7 else f"Stage {stage}"

        return f"""You are working on task: {task.get("description", task_id)}

Task ID: {task_id}
Priority: {task.get("priority", "P1")}
Ralph Loop Stage: {stage}/7 ({stage_name})

Read the full task at: .long-run-agent/{task_file}

== 当前阶段: {stage_name} ==
自主完成本阶段工作：分析需求、实现功能、运行验证工具（由你根据项目类型自主选择）。

After completing your work:
1. Output JSON: {{"success": bool, "summary": str, "key_changes": [], "key_learnings": []}}
2. Do NOT call 'lra set' commands — stage advancement is handled automatically
3. Do NOT commit — that is handled automatically
"""
