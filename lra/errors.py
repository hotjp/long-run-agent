"""
LRA Error Messages with Actionable Suggestions

This module provides a centralized error catalog that gives agents
clear guidance on how to recover from errors.
"""

from typing import Dict, Any, Optional


ERROR_CATALOG = {
    "invalid_transition": {
        "message": "{current} → {target} 无效",
        "action": "lra set {task_id} {first_valid}",
        "hint": "可用流转: → {available}",
        "category": "state_machine",
    },
    "optimizing_stuck": {
        "message": "任务在 optimizing 状态卡住",
        "action": "lra set {task_id} in_progress",
        "hint": "修复 Constitution 验证失败的问题后继续工作",
        "category": "state_machine",
    },
    "constitution_failed": {
        "message": "Constitution 验证失败",
        "action": "lra show {task_id}",
        "hint": "{failures}",
        "category": "quality",
    },
    "constitution_non_negotiable": {
        "message": "违反 NON_NEGOTIABLE 原则",
        "action": "lra show {task_id} 查看详情",
        "hint": "{failures}",
        "category": "quality",
    },
    "blocked_can_only_go_to": {
        "message": "blocked 状态只能转移到 {allowed}",
        "action": "lra show {task_id}  # 查看依赖任务",
        "hint": "请先完成依赖任务",
        "category": "dependency",
    },
    "cycle_dependency": {
        "message": "检测到循环依赖",
        "action": "使用 lra split 拆分任务，或调整依赖关系",
        "hint": "依赖路径: {path}",
        "category": "dependency",
    },
    "not_found": {
        "message": "任务 {task_id} 不存在",
        "action": "lra list  # 查看可用任务",
        "hint": None,
        "category": "task",
    },
    "not_initialized": {
        "message": "项目未初始化",
        "action": "lra init --name <项目名>",
        "hint": None,
        "category": "project",
    },
    "no_split_plan": {
        "message": "需要提供拆分计划",
        "action": "lra decompose {task_id}  # 获取建议，或使用 --auto",
        "hint": "使用 --auto 自动拆分，或 --plan 指定计划",
        "category": "task",
    },
    "max_iterations_reached": {
        "message": "已达到最大迭代次数 {max}",
        "action": "lra set {task_id} force_completed  # 强制完成",
        "hint": "或增加迭代上限: lra set {task_id} max_iterations 10",
        "category": "iteration",
    },
}


def get_error_with_action(error_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get error message with actionable suggestion.

    Args:
        error_code: The error code (e.g., "invalid_transition")
        context: Dictionary with template variables (e.g., task_id, current, target)

    Returns:
        Dict with keys: error, message, action, hint, category
    """
    error_def = ERROR_CATALOG.get(error_code, {
        "message": f"错误: {error_code}",
        "action": "查看文档: lra --help",
        "hint": None,
        "category": "unknown",
    })

    # Format message
    message = error_def["message"].format(**context)

    # Format action
    action = error_def["action"].format(**context)

    # Format hint if present
    hint = None
    if error_def.get("hint"):
        try:
            hint = error_def["hint"].format(**context)
        except KeyError:
            hint = error_def["hint"]

    return {
        "error": error_code,
        "message": message,
        "action": action,
        "hint": hint,
        "category": error_def.get("category", "unknown"),
    }


def format_error_display(err: Dict[str, Any]) -> str:
    """
    Format error for CLI display with emoji.

    Returns:
        Formatted multi-line string ready for print
    """
    lines = [
        f"❌ {err['message']}",
        f"💡 建议: {err['action']}",
    ]

    if err.get("hint"):
        lines.append(f"   原因: {err['hint']}")

    return "\n".join(lines)


def parse_error_from_msg(msg: str) -> tuple:
    """
    Parse error code and details from raw error message.

    Handles both old format ("invalid_transition:pending->foo")
    and new format (just "invalid_transition").

    Returns:
        (error_code, details_dict)
    """
    if ":" in msg and "->" in msg:
        # Old format: "invalid_transition:pending->foo"
        parts = msg.split(":", 1)
        error_code = parts[0]
        detail_str = parts[1]

        if "->" in detail_str:
            from_state, to_state = detail_str.split("->", 1)
            return error_code, {"from": from_state, "to": to_state}

        return error_code, {"detail": detail_str}

    # New format: just error code
    return msg, {}


# Backward compatibility: export old-style error constants
DEPRECATED_ERRORS = {
    "invalid_transition": "invalid_transition",
    "constitution_failed": "constitution_failed",
    "cycle_dependency": "cycle_dependency",
    "blocked_can_only_go_to": "blocked_can_only_go_to",
}
