# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LRA (Long-Running Agent) is a task management framework for AI agents with quality assurance. It provides structured task workflows, multi-agent coordination via hierarchical locks, and a Constitution-based quality gate system.

**Entry point**: `lra` CLI command (installed via `pip install long-run-agent`)

## Common Commands

```bash
# Run tests
python3 -m pytest tests/ -v                    # all tests
python3 -m pytest tests/test_constitution.py  # single test file

# Linting & type checking
ruff check lra/           # lint with ruff
ruff format lra/          # format with ruff
mypy lra/                 # type check

# Install for development
pip install -e ".[dev]"   # includes test/lint tools
pip install -e ".[full]"  # includes playwright for browser tests
```

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `lra/cli.py` | CLI entry point (120k+ bytes), orchestrates all commands |
| `lra/task_manager.py` | Task CRUD, status workflow, Ralph Loop iteration tracking |
| `lra/locks_manager.py` | Hierarchical locks for multi-agent coordination with heartbeat/orphan detection |
| `lra/constitution.py` | Quality gates and validation (NON_NEGOTIABLE/MANDATORY/CONFIGURABLE principles) |
| `lra/quality_checker.py` | Code quality checks, regression testing |
| `lra/template_manager.py` | Jinja2-based task templates with 7-stage iteration paths |
| `lra/config.py` | Configuration, paths, SafeJson (atomic file I/O with FileLock) |

### Data Flow

1. Project initialized via `lra init` → creates `.long-run-agent/` directory
2. Tasks stored in `task_list.json` + individual `tasks/{id}.md` files
3. Locks tracked in `locks.json` with heartbeat mechanism
4. Constitution validation triggered on task completion

### Ralph Loop (7-Stage Iteration)

Each task follows a progressive optimization path:
`理解规划 → 基础实现 → 功能完善 → 质量提升 → 优化改进 → 验证测试 → 交付准备`

Quality gates are staged-based - early stages skip performance/deep testing, later stages enforce stricter checks.

### Constitution System

Quality gates defined in `.long-run-agent/constitution.yaml`:
- **NON_NEGOTIABLE**: Cannot be bypassed (even with `--force`)
- **MANDATORY**: Required gates must pass
- **CONFIGURABLE**: Optional gates

Gate types: `command` (shell), `field_exists` (file checks), `custom`

### Multi-Agent Coordination

- Parent tasks can lock child tasks until published
- Orphan detection: locks marked orphaned after 15 minutes without heartbeat
- Batch operations via `BatchLockManager`

## Metadata Directory Structure

```
.long-run-agent/
├── task_list.json      # Main task index
├── config.json         # Project config
├── locks.json          # Lock state
├── tasks/              # Individual task files (.md)
├── templates/          # Task templates
├── records/            # Change records
└── backup/             # Version backups
```
