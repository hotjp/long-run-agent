# lra/doctor.py

> 语言：python | 代码行数：621

## 概述

LRA Doctor - Health diagnostics for LRA projects
v5.0 - Check installation, locks, tasks, constitution, and more

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `DoctorCheck` | 0 | - |
| `DoctorResult` | 0 | - |

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `check_installation` | `path` | Check if .long-run-agent/ exists |
| `check_task_list_valid` | `path` | Check if task_list.json exists and is valid JSON |
| `check_locks_valid` | `path` | Check if locks.json is valid JSON |
| `check_constitution_valid` | `path` | Check if constitution.yaml exists and is valid YAM |
| `check_task_files` | `path` | Check if all referenced task .md files exist |
| `check_orphaned_tasks` | `path` | Check for task files without index entry |
| `check_circular_deps` | `path` | Check for cycles in dependency graph |
| `check_orphaned_locks` | `path` | Check for locks with no heartbeat > 15 min |
| `check_stale_locks` | `path` | Check for locks held > expected duration |
| `check_lock_file_valid` | `path` | Check if locks.json structure is valid |
| `check_config_valid` | `path` | Check if config.json is valid |
| `check_version_tracking` | `path` | Check if .lra_version matches CURRENT_VERSION |
| `check_git_repo` | `path` | Check if parent dir is a git repo |
| `run_diagnostics` | `path` | Run all diagnostics and return combined result |
| `fix_orphaned_locks` | `path` | Clean up orphaned locks - release them |
| `dfs` | `task_id, path` | - |

## 依赖

- os
- dataclasses
- datetime
- typing
- lra.config
- lra.locks_manager
