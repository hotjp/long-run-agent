"""Structured output schema for relay agent results."""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AGENT_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["success", "summary"],
    "properties": {
        "success": {"type": "boolean"},
        "summary": {"type": "string"},
        "key_changes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "key_learnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


@dataclass
class AgentOutput:
    """Validated agent output structure."""

    success: bool
    summary: str
    key_changes: List[str] = field(default_factory=list)
    key_learnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentOutput":
        return cls(
            success=bool(data.get("success", False)),
            summary=str(data.get("summary", "")),
            key_changes=list(data.get("key_changes", [])),
            key_learnings=list(data.get("key_learnings", [])),
        )


class OutputValidationError(Exception):
    pass


def validate_output(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate agent output against schema. Returns (is_valid, errors)."""
    errors = []

    if "success" not in data:
        errors.append("Missing required field: 'success'")
    elif not isinstance(data["success"], bool):
        errors.append("Field 'success' must be boolean")

    if "summary" not in data:
        errors.append("Missing required field: 'summary'")
    elif not isinstance(data["summary"], str):
        errors.append("Field 'summary' must be string")

    if "key_changes" in data:
        if not isinstance(data["key_changes"], list):
            errors.append("Field 'key_changes' must be array")
        elif not all(isinstance(item, str) for item in data["key_changes"]):
            errors.append("All items in 'key_changes' must be strings")

    if "key_learnings" in data:
        if not isinstance(data["key_learnings"], list):
            errors.append("Field 'key_learnings' must be array")
        elif not all(isinstance(item, str) for item in data["key_learnings"]):
            errors.append("All items in 'key_learnings' must be strings")

    return len(errors) == 0, errors


def parse_json_output(raw_output: str) -> Optional[Dict[str, Any]]:
    """Parse raw agent output into structured dict. Handles markdown-wrapped JSON."""
    raw = raw_output.strip()
    if not raw:
        return None

    # Try direct JSON parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try extracting first { ... } block
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def build_json_schema(include_stop_field: bool = False) -> dict:
    """Generate schema for Claude CLI --json-schema."""
    properties = {
        "success": {"type": "boolean"},
        "summary": {"type": "string"},
        "key_changes": {"type": "array", "items": {"type": "string"}},
        "key_learnings": {"type": "array", "items": {"type": "string"}},
    }
    required = ["success", "summary", "key_changes", "key_learnings"]
    if include_stop_field:
        properties["should_fully_stop"] = {"type": "boolean"}
        required.append("should_fully_stop")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def write_schema_file(path: Path, include_stop_field: bool = False) -> None:
    """Write schema file for Claude CLI --json-schema."""
    schema = build_json_schema(include_stop_field)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
