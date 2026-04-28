"""LRA Relay — Automated task execution loop."""

from lra.relay.agent_runner import AgentRunner, IterationResult, TaskRunResult
from lra.relay.backoff import BackoffConfig, ExponentialBackoff, HardError, SoftError
from lra.relay.claude_adapter import AgentResult, ClaudeAdapter, TokenUsage
from lra.relay.git_utils import GitError, GitUtils, check_working_tree_clean
from lra.relay.notes_store import NotesStore
from lra.relay.orchestrator import RelayOrchestrator
from lra.relay.structured_output import (
    AgentOutput,
    OutputValidationError,
    build_json_schema,
    parse_json_output,
    validate_output,
    write_schema_file,
)
from lra.relay.task_queue import TaskQueue

__all__ = [
    "RelayOrchestrator",
    "AgentRunner",
    "IterationResult",
    "TaskRunResult",
    "TaskQueue",
    "ClaudeAdapter",
    "AgentResult",
    "TokenUsage",
    "AgentOutput",
    "validate_output",
    "parse_json_output",
    "build_json_schema",
    "write_schema_file",
    "OutputValidationError",
    "ExponentialBackoff",
    "BackoffConfig",
    "HardError",
    "SoftError",
    "NotesStore",
    "GitUtils",
    "GitError",
    "check_working_tree_clean",
]
