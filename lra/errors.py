"""
LRA Error Messages with Actionable Suggestions

This module provides a centralized error catalog that gives agents
clear guidance on how to recover from errors.
"""

from typing import Any, Dict

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
    "duplicate_task_id": {
        "message": "任务 ID 重复: {task_id}（task_list 中存在 {count} 条同名记录）",
        "action": "lra doctor --fix  # 自动重新编号冲突记录",
        "hint": "重复 ID 会导致读取到错误的任务书，修复前请勿操作该任务；"
        "lra doctor --fix 会把冲突记录拆成独立 ID，任务书归实际持有它的那条",
        "category": "data_integrity",
    },
    "jinja2_not_installed": {
        "message": "缺少 Jinja2 依赖，无法渲染任务书（模板里的 Jinja2 占位符语法需要它）",
        "action": "{install_cmd}",
        "hint": "任务已回滚，未写入 task_list（不会产生无任务书的僵尸任务）。"
        "原始错误：{detail}。"
        "若 pip 明明装了却仍报此错，多半是有同名文件遮蔽了 Python 标准库"
        "（例如当前目录下有个 inspect.py）——`lra doctor --check runtime_dependencies` 会指出这一点",
        "category": "environment",
    },
    "jinja2_import_failed": {
        "message": "Jinja2 导入失败，无法渲染任务书",
        "action": "{install_cmd}",
        "hint": "任务已回滚，未写入 task_list（不会产生无任务书的僵尸任务）。"
        "原始错误：{detail}。"
        "如果原始错误里出现「遮蔽」字样，装包没用——得把那个文件改名或移出工作目录；"
        "否则先按上面的命令重装一次",
        "category": "environment",
    },
    "task_file_create_failed": {
        "message": "任务文件创建失败: {detail}",
        "action": "lra doctor  # 检查模板是否损坏",
        "hint": "任务已回滚，未写入 task_list（不会产生无任务书的僵尸任务）",
        "category": "data_integrity",
    },
    "save_failed": {
        "message": "task_list.json 写入失败",
        "action": "lra doctor  # 检查文件权限与磁盘空间",
        "hint": "任务未创建，task_list 未被修改",
        "category": "data_integrity",
    },
}


def _safe_format(template: str, context: Dict[str, Any]) -> str:
    """格式化模板，缺 key 时不炸。

    错误文案里的占位符不能因为调用方少传一个字段就崩掉——
    报错路径本身再抛异常，等于把问题藏得更深。

    缺掉的占位符也不能留成裸的 ``{key}``：那会被用户当成文案的一部分，
    看着像出了 bug。替换成可读的说明。
    """
    try:
        return template.format(**context)
    except (KeyError, IndexError, ValueError):
        # 逐个补齐缺失的占位符
        import string

        class _SafeDict(dict):
            def __missing__(self, key):  # noqa: D105
                return f"（未提供 {key}）"

        try:
            return string.Formatter().vformat(template, (), _SafeDict(context))
        except Exception:  # noqa: BLE001
            return template.replace("{", "").replace("}", "")


def _fill_dependency_context(error_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """依赖类错误自己补齐上下文，调用方不必知道细节。

    少了这一步，``action`` 里就只剩一个 ``{install_cmd}`` 占位符——
    报错文案引用了一个"看起来像命令、其实不是命令"的东西，
    用户照着做只会更迷惑。
    """
    if error_code not in ("jinja2_not_installed", "jinja2_import_failed"):
        return context

    ctx = dict(context)
    if not ctx.get("install_cmd"):
        try:
            from lra.deps import fix_hint_for

            ctx["install_cmd"] = fix_hint_for("jinja2")
        except Exception:  # noqa: BLE001 - 探测失败也不能让报错路径崩
            ctx["install_cmd"] = "python3 -m pip install --user long-run-agent"
    if not ctx.get("detail"):
        ctx["detail"] = "（无更多信息）"
    return ctx


def get_error_with_action(error_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get error message with actionable suggestion.

    Args:
        error_code: The error code (e.g., "invalid_transition")
        context: Dictionary with template variables (e.g., task_id, current, target)

    Returns:
        Dict with keys: error, message, action, hint, category
    """
    context = _fill_dependency_context(error_code, context or {})
    error_def = ERROR_CATALOG.get(
        error_code,
        {
            "message": f"错误: {error_code}",
            "action": "查看文档: lra --help",
            "hint": None,
            "category": "unknown",
        },
    )

    # Format message
    message = _safe_format(error_def["message"], context)

    # Format action
    action = _safe_format(error_def["action"], context)

    # Format hint if present
    hint = None
    if error_def.get("hint"):
        hint = _safe_format(error_def["hint"], context)

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
