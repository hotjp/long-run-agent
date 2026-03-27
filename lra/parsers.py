"""
Input parsers for CLI arguments with backward compatibility.

Provides unified parsing for complex CLI inputs like dependencies and variables.
Supports both JSON format (preferred) and legacy formats (with deprecation warnings).
"""

import json
from typing import List, Dict, Any, Optional


def parse_dependencies(value: Optional[str]) -> Optional[List[str]]:
    """
    Parse dependencies from CLI argument.

    Supports:
    - JSON array: '["task_001", "task_002"]'
    - Comma-separated (deprecated): "task_001,task_002,task_003"

    Args:
        value: CLI argument value

    Returns:
        List of dependency IDs, or None if empty
    """
    if not value:
        return None

    # Try JSON first
    if value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for --dependencies: {e}")

    # Fall back to comma-separated (deprecated)
    import warnings
    warnings.warn(
        "Comma-separated --dependencies is deprecated. Use JSON array instead: "
        '--dependencies \'["task_001", "task_002"]\'',
        DeprecationWarning,
        stacklevel=2
    )
    return [d.strip() for d in value.split(",") if d.strip()]


def parse_variables(value: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Parse variables from CLI argument.

    Variables must be JSON object format.

    Args:
        value: CLI argument value

    Returns:
        Dictionary of variables, or None if empty

    Raises:
        ValueError: If JSON is invalid
    """
    if not value:
        return None

    if value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for --variables: {e}")

    raise ValueError(
        "--variables must be JSON object. Example: "
        '--variables \'{"requirements": "...", "acceptance": ["..."]}\''
    )


def parse_acceptance(value: Optional[str]) -> Optional[List[str]]:
    """
    Parse acceptance criteria from CLI argument.

    Supports:
    - JSON array: '["criteria1", "criteria2"]'
    - Comma-separated: "criteria1,criteria2,criteria3"

    Args:
        value: CLI argument value

    Returns:
        List of acceptance criteria, or None if empty
    """
    if not value:
        return None

    # Try JSON first
    if value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # Fall back to comma-separated
    return [c.strip() for c in value.split(",") if c.strip()]
