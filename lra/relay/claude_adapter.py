"""Claude CLI adapter for subprocess management."""

import json
import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass
class AgentResult:
    output: dict
    usage: TokenUsage


class ClaudeAdapter:
    """Claude CLI subprocess manager.

    Key features:
    - spawn Claude with structured prompt
    - Parse JSONL output stream
    - Graceful shutdown with 15s grace period
    - JSON schema enforcement via --json-schema
    """

    FINAL_RESULT_GRACE_MS = 15_000

    def __init__(
        self,
        bin_path: str = "claude",
        schema_path: Optional[Path] = None,
        extra_args: Optional[list[str]] = None,
    ):
        self.bin = bin_path
        self.schema_path = schema_path
        self.extra_args = extra_args or []
        self._child: Optional[subprocess.Popen] = None
        self._aborted = False

    def _build_args(self, prompt: str) -> list[str]:
        """Build Claude CLI arguments."""
        args = [
            *self.extra_args,
            "-p",
            prompt,
            "--verbose",
            "--output-format",
            "stream-json",
        ]
        if self.schema_path and self.schema_path.exists():
            args.extend(["--json-schema", str(self.schema_path)])
        # Non-interactive mode: skip permission confirmation
        skip_perm_args = {"--dangerously-skip-permissions", "--permission-mode"}
        if not any(a in self.extra_args for a in skip_perm_args):
            args.append("--dangerously-skip-permissions")
        return args

    def run(
        self,
        prompt: str,
        cwd: Path,
        log_path: Optional[Path] = None,
    ) -> AgentResult:
        """Run Claude CLI, return structured output."""
        args = self._build_args(prompt)

        # Spawn child process (Unix: new process group for easy kill)
        self._child = subprocess.Popen(
            [self.bin, *args],
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=(sys.platform != "win32"),
        )

        stdout_lines: list[str] = []
        stderr_text = ""
        final_structured_event: Optional[dict] = None
        result_event: Optional[dict] = None
        latest_usage: Optional[dict] = None

        # Read stdout JSONL
        for line in self._child.stdout:
            line = line.strip()
            if not line:
                continue
            stdout_lines.append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "result":
                latest_usage = event.get("usage", {})
                if self._is_final_structured_result(event):
                    final_structured_event = event
                elif not final_structured_event:
                    result_event = event

        # Read stderr
        stderr_text = self._child.stderr.read() or ""

        # Wait for child
        return_code = self._child.wait()
        self._child = None

        if return_code != 0:
            raise RuntimeError(f"claude exited with code {return_code}: {stderr_text}")

        # Determine terminal event
        terminal = final_structured_event or result_event
        if not terminal:
            raise RuntimeError("claude returned no result event")

        if terminal.get("is_error") or terminal.get("subtype") != "success":
            raise RuntimeError(f"claude reported error: {json.dumps(terminal)}")

        structured = terminal.get("structured_output")
        if not structured:
            raise RuntimeError("claude returned no structured_output")

        usage = self._to_token_usage(latest_usage or terminal.get("usage", {}))

        # Write log
        if log_path:
            log_path.write_text("\n".join(stdout_lines), encoding="utf-8")

        return AgentResult(output=structured, usage=usage)

    def _is_final_structured_result(self, event: dict) -> bool:
        return (
            not event.get("is_error")
            and event.get("subtype") == "success"
            and event.get("structured_output") is not None
        )

    def _to_token_usage(self, usage: dict) -> TokenUsage:
        return TokenUsage(
            input_tokens=usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        )

    def _terminate_child(self) -> None:
        """Terminate Claude subprocess."""
        if not self._child or self._child.poll() is not None:
            return

        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(self._child.pid)],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
        else:
            try:
                os.killpg(os.getpgid(self._child.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                self._child.terminate()

    def shutdown(self) -> None:
        """Graceful shutdown: 15s grace period then SIGTERM."""
        if not self._child or self._child.poll() is not None:
            return

        timer = threading.Timer(self.FINAL_RESULT_GRACE_MS / 1000, self._terminate_child)
        timer.start()

        try:
            self._child.wait(timeout=self.FINAL_RESULT_GRACE_MS / 1000)
            timer.cancel()
        except subprocess.TimeoutExpired:
            pass

    def __del__(self) -> None:
        self.shutdown()
