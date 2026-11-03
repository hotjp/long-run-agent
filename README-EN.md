<div align="center">

# LRA - Long-Running Agent Tool

**A powerful framework for managing long-running AI Agent tasks**

Based on best practices from Anthropic's paper [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#)

**English | [中文](README.md)**

</div>

---

> This is the English version of the documentation. For the complete bilingual documentation with all features, CLI reference, and usage examples, please see [README.md](README.md#english).

## Quick Overview

LRA is a command-line tool that helps manage long-running AI agent development tasks with:

- 🔄 **Auto-upgrade** - Seamless version migration with backup
- 📋 **Feature status workflow** - 7 states with transition validation
- 📝 **Requirements management** - Templates and validation
- 📊 **Code change tracking** - Per-feature records with Git integration
- 📜 **Operation audit logs** - Complete traceability
- 🔧 **Multi-language code checking** - Python, JavaScript, Go
- ♻️ **Skip / cancel / recall** - Lateral lifecycle exits for tasks (v5.3.0)
- 🩹 **Self-healing tasks** - Collision-free task IDs, rollback on create failure; `lra doctor --fix` de-dupes and rebuilds missing task books (v5.3.1)
- 🔄 **Task reset** - `lra reset` sends a task stranded by a killed worker back to pending — lock-guarded and audited, no more hand-editing task_list.json (v5.4.0)
- 🔧 **Dependency self-healing** - `lra doctor` checks jinja2/pyyaml/filelock and tells apart "not installed / shadowed by a same-named file / broken install"; `doctor --fix` installs what's missing, and the commands it prints actually run under PEP 668 (v5.5.0)

## Installation

```bash
# Install from PyPI (all runtime dependencies included)
pip install long-run-agent

# Development environment
pip install long-run-agent[dev]

# Full install (adds browser test support)
pip install long-run-agent[full]
```

> The PyPI package is named `long-run-agent`; the CLI command is `lra`.

### Runtime dependencies

LRA has three hard dependencies — `pip install long-run-agent` pulls them in automatically:

| Dependency | Purpose | Symptom when missing |
|------------|---------|----------------------|
| `jinja2>=3.0` | Renders task-book templates | `lra create` fails and rolls the task back |
| `pyyaml>=6.0` | Reads/writes templates and constitution | `lra init` / template I/O fails |
| `filelock>=3.9.0` | File locking (concurrent writes to task_list) | Locking fails, concurrent writes break |

### Environment check: `lra doctor`

```bash
lra doctor --check runtime_dependencies   # inspect dependencies only
lra doctor --fix                          # install whatever is missing
```

`doctor` also catches the subtler case: a dependency that *is* installed but shadowed by a same-named file in your working directory (e.g. a stray `inspect.py`). Installing again does not help there — `doctor` names the offending file.

### Install blocked? PEP 668 (externally-managed)

Homebrew and system Pythons refuse `pip install` outright:

```
error: externally-managed-environment
```

Two ways out:

```bash
# Option A: install into the user directory (recommended)
python3 -m pip install --user --break-system-packages long-run-agent

# Option B: use a virtualenv (cleanest)
python3 -m venv .venv && source .venv/bin/activate
pip install long-run-agent
```

> ⚠️ **Use `python3 -m pip`, not bare `pip`.** With several Pythons on `PATH`, bare `pip` frequently installs into a *different* interpreter than the one running `lra` — the dependency still looks missing afterwards.
>
> The commands printed by `lra doctor` and by LRA's error messages already account for PEP 668; just copy them.

## Quick Start

```bash
# Initialize a project (creates the Constitution automatically)
cd /path/to/your/project
lra init --name "My Project"

# Create + claim a task (recommended)
lra new "Implement login"

# Or create a complex task and auto-split it
lra new "Implement the auth module" --auto-split

# Inspect the Constitution
lra constitution show

# Give an agent its context
lra orientation

# See what's ready to work on
lra ready

# Health check (also detects missing/shadowed dependencies)
lra doctor
```

## Documentation

Full documentation with CLI reference, status flow diagrams, and best practices is available in the [main README](README.md#english).

## License

MIT License
