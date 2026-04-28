"""Append-only file-based notes store for relay observations."""

from pathlib import Path
from typing import Any, Dict, List


class NotesStore:
    """Append-only JSONL notes store with in-memory cache per task_id."""

    def __init__(self, notes_path: Path):
        self.path = notes_path
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def append(
        self,
        task_id: str,
        attempt: int,
        summary: str,
        changes: List[str],
        learnings: List[str],
    ) -> None:
        """Append a note entry to the store."""
        import json

        entry = {
            "task_id": task_id,
            "attempt": attempt,
            "summary": summary,
            "changes": changes,
            "learnings": learnings,
        }

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Update memory index
        self._cache.setdefault(task_id, []).append(
            {
                "attempt": attempt,
                "summary": summary,
                "changes": changes,
                "learnings": learnings,
            }
        )

    def read_task_context(self, task_id: str, max_entries: int = 5) -> str:
        """Read recent context for a task (from memory cache)."""
        entries = self._cache.get(task_id, [])
        if not entries:
            return ""
        recent = entries[-max_entries:]
        lines = [f"- {e['summary']}" for e in recent]
        return "\n".join(lines)

    def get_task_attempts(self, task_id: str) -> int:
        """Get number of attempts for a task from memory cache."""
        return len(self._cache.get(task_id, []))
