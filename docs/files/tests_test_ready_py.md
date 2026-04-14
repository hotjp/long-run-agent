# tests/test_ready.py

> 语言：python | 代码行数：311

## 概述

Tests for the lra ready command and get_ready_tasks functionality.

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `temp_project` | `` | Create a temporary project directory for testing. |
| `sample_tasks` | `temp_project` | Create sample tasks for testing. |
| `test_get_ready_tasks_excludes_completed` | `temp_project, sample_tasks` | Test that get_ready_tasks excludes completed tasks |
| `test_get_ready_tasks_includes_pending` | `temp_project, sample_tasks` | Test that get_ready_tasks includes pending tasks. |
| `test_get_ready_tasks_excludes_blocked` | `temp_project, sample_tasks` | Test that get_ready_tasks excludes tasks with unme |
| `test_get_ready_tasks_sort_by_priority` | `temp_project, sample_tasks` | Test that get_ready_tasks sorts by priority by def |
| `test_get_ready_tasks_sort_by_oldest` | `temp_project, sample_tasks` | Test that get_ready_tasks sorts by oldest (task nu |
| `test_get_ready_tasks_limit` | `temp_project, sample_tasks` | Test that get_ready_tasks respects the limit param |
| `test_get_ready_tasks_priority_filter` | `temp_project, sample_tasks` | Test that get_ready_tasks filters by priority. |
| `test_get_ready_tasks_returns_correct_fields` | `temp_project, sample_tasks` | Test that get_ready_tasks returns correct fields. |
| `test_get_ready_tasks_empty_project` | `` | Test that get_ready_tasks handles empty project gr |
| `test_get_blocked_tasks` | `temp_project, sample_tasks` | Test that get_blocked_tasks returns blocked tasks  |
| `test_get_ready_tasks_with_dependencies_satisfied` | `temp_project` | Test that tasks are ready when their dependencies  |
| `test_get_ready_tasks_no_locks_manager` | `temp_project, sample_tasks` | Test that get_ready_tasks works without locks_mana |

## 依赖

- os
- tempfile
- pytest
- lra.config
- lra.task_manager
