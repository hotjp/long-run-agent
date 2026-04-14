# Beads-Inspired Enhancements for LRA

> Design document for adding Beads-inspired features to LRA

## Overview

This document describes enhancements to LRA (Long-Running Agent) inspired by [Beads](https://github.com/steveyegge/beads), a distributed graph issue tracker designed for AI agents.

**Why Beads?** Beads excels at:
- Agent-optimized CLI commands (`ready`, `doctor`)
- Safety guards for destructive operations
- Machine-readable JSON output
- Comprehensive health diagnostics
- Agent instruction files (AGENTS.md)

## Table of Contents

1. [Command: `lra ready`](#1-lra-ready-command)
2. [Command: `lra doctor`](#2-lra-doctor-command)
3. [Enhanced: `lra init`](#3-enhanced-lra-init)
4. [Feature: AGENTS.md Integration](#4-agentsmd-integration)
5. [Implementation Plan](#5-implementation-plan)

---

## 1. `lra ready` Command

### Purpose

Show tasks that are ready to work on — tasks with no active blockers, not locked by others, and with all dependencies satisfied.

### Rationale

In multi-agent workflows, agents need to quickly find work without stepping on each other. `lra ready` answers the question: "What can I work on right now?"

### Logic

```
ready = tasks where ALL of:
  - status NOT IN (completed, truly_completed, force_completed)
  - NOT locked by another session
  - NOT blocked by dependencies
  - All parent dependencies are completed
```

### CLI Interface

```bash
lra ready              # Show ready tasks (default limit: 10)
lra ready --json      # Machine-readable output
lra ready -n 20       # Limit output to 20 tasks
lra ready -p 1        # Filter by priority (P1)
lra ready -a agent_1  # Filter by assignee
lra ready -u          # Show only unassigned tasks
lra ready -s oldest   # Sort by creation time (default: priority)
lra ready --explain   # Show dependency reasoning
```

### Output Format

**Human-readable:**
```
$ lra ready
📋 Ready work (3 tasks):

1. [P1] task_002: Implement user auth
   └─ Parent: task_001 (epic: user management)

2. [P2] task_003: Add API tests
   └─ Waiting on: task_002 (blocks)

3. [P0] task_005: Fix critical bug
   └─ Assignee: agent_1

Run 'lra show <id>' for details.
```

**JSON:**
```json
{
  "tasks": [
    {
      "id": "task_002",
      "title": "Implement user auth",
      "priority": "P1",
      "status": "in_progress",
      "parent_id": "task_001",
      "blocked_by": [],
      "assignee": null
    }
  ],
  "count": 3,
  "total": 3
}
```

### `--explain` Output

```
$ lra ready --explain
📊 Ready Work Explanation

✅ Ready (3 tasks):

  task_002 [P1] Implement user auth
    Reason: No blockers, parent task completed
    Unblocks: 1 task(s)

  task_003 [P2] Add API tests
    Reason: No blockers
    Resolved blockers: task_002

❌ Blocked (2 tasks):

  task_006 [P1] Deploy to staging
    ← blocked by task_004: API integration (in_progress)

⚠ Cycles detected (1):
  task_007 → task_008 → task_007

─ Summary: 3 ready, 2 blocked, 1 cycle(s)
```

### Flags Reference

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--limit` | `-n` | Max tasks to show | 10 |
| `--priority` | `-p` | Filter by priority (0-4) | all |
| `--assignee` | `-a` | Filter by assignee | all |
| `--unassigned` | `-u` | Only unassigned tasks | false |
| `--sort` | `-s` | Sort: `priority` (default), `oldest` | priority |
| `--explain` | | Show dependency reasoning | false |
| `--json` | | JSON output | false |

---

## 2. `lra doctor` Command

### Purpose

Diagnose LRA installation health, detect issues, and optionally fix them.

### Rationale

When things go wrong (corrupted files, orphaned locks, broken constitution), agents need a way to diagnose and recover without manual intervention.

### CLI Interface

```bash
lra doctor              # Run all checks
lra doctor --json       # Machine-readable output
lra doctor --fix       # Auto-fix issues (with confirmation)
lra doctor --fix --yes # Auto-fix (no confirmation)
lra doctor --dry-run    # Preview fixes without applying
lra doctor --verbose   # Show all checks (not just failures)
lra doctor --check=orphaned_locks  # Run single check
```

### Check Categories

#### Core (blocking)

| Check | Description | Fix Available |
|-------|-------------|---------------|
| `installation` | `.long-run-agent/` exists | `lra init` |
| `task_list` | `task_list.json` is valid JSON | warn |
| `locks_valid` | `locks.json` is valid JSON | warn |
| `constitution_valid` | `constitution.yaml` is valid YAML | regenerate |

#### Task Data

| Check | Description | Fix Available |
|-------|-------------|---------------|
| `task_files` | All referenced task .md files exist | warn |
| `orphaned_tasks` | Task files without index entry | warn |
| `circular_deps` | Cycle in dependency graph | error |
| `task_consistency` | Status matches Ralph Loop rules | warn |

#### Lock State

| Check | Description | Fix Available |
|-------|-------------|---------------|
| `orphaned_locks` | Lock with no heartbeat > 15min | `lra doctor --fix` |
| `stale_locks` | Lock held > expected duration | warn |
| `lock_file_valid` | locks.json structure valid | rebuild |

#### Configuration

| Check | Description | Fix Available |
|-------|-------------|---------------|
| `config_valid` | `config.json` is valid | regenerate |
| `version_tracking` | `.lra_version` matches code | update |

#### Integration

| Check | Description | Fix Available |
|-------|-------------|---------------|
| `git_repo` | Parent dir is a git repo | warn |
| `git_clean` | Working tree is clean | warn |
| `git_hooks` | Pre-commit hooks installed | install |

### Check Result Structure

```python
@dataclass
class DoctorCheck:
    name: str           # "orphaned_locks"
    status: str        # "ok" | "warning" | "error"
    message: str       # Human-readable status
    detail: str        # Additional context
    fix: str           # Command to fix (if fixable)
    category: str      # "core" | "data" | "locks" | "config" | "integration"

@dataclass
class DoctorResult:
    path: str
    overall_ok: bool
    checks: List[DoctorCheck]
    cli_version: str
    timestamp: str     # ISO8601
```

### Output Format

**Human-readable:**
```
$ lra doctor
🔍 LRA Doctor v5.0.0

  ✓  ✓ installation: .long-run-agent/ exists
  ✓  ✓ task_list: task_list.json valid (12 tasks)
  ✓  ✓ constitution_valid: constitution.yaml valid
  ⚠  ⚡ orphaned_locks: 2 locks marked orphaned
     └─ Run 'lra doctor --fix' to clean up

Core (3/3 passed)
Data (4/4 passed)
Locks (1/3 passed, 2 warnings)
Config (2/2 passed)
Integration (1/1 passed)

⚠ 2 warnings, 0 errors
Run 'lra doctor --verbose' for details.
Run 'lra doctor --fix' to auto-fix.
```

**JSON:**
```json
{
  "path": "/path/to/project",
  "overall_ok": true,
  "checks": [
    {
      "name": "orphaned_locks",
      "status": "warning",
      "message": "2 locks marked orphaned",
      "detail": "task_001, task_003",
      "fix": "lra doctor --fix",
      "category": "locks"
    }
  ],
  "cli_version": "5.0.0",
  "timestamp": "2026-04-08T10:30:00Z"
}
```

### Agent Mode (`--agent`)

For AI agent consumption, output includes remediation context:

```bash
$ lra doctor --agent
```

**Output includes:**
- **Observed state**: What the system actually looks like
- **Expected state**: What it should look like
- **Explanation**: Full prose context about the issue
- **Commands**: Exact remediation commands to run
- **Source files**: Where to investigate further
- **Severity**: `blocking` | `degraded` | `advisory`

### Auto-fix Behavior

```bash
# Preview what would be fixed
lra doctor --dry-run

# Interactive fix (confirm each)
lra doctor --fix -i

# Non-interactive fix (--yes skips confirmations)
lra doctor --fix --yes
```

---

## 3. Enhanced `lra init`

### Current State

LRA's current `lra init` creates basic directory structure but lacks:
- Safety guards against accidental re-initialization
- Version tracking
- Agent instructions
- Git integration

### Enhanced Features

#### Safety Improvements

**1. Existing Data Detection**

```bash
$ lra init
Error: Already initialized

This workspace is already initialized with 12 tasks.

To re-initialize (DESTRUCTIVE):
  lra init --force --destroy-token=DESTROY-myproject
```

**2. Destroy Confirmation**

```bash
$ lra init --force
WARNING: Re-initializing will destroy the existing database.

  Existing tasks: 12
  This action CANNOT be undone.

Type 'destroy 12 tasks' to confirm: destroy 12 tasks
✓ Re-initialized successfully
```

**3. Destroy Token (non-interactive)**

```bash
# For CI/automation
lra init --force --destroy-token=DESTROY-myproject
```

#### New Flags

| Flag | Description |
|------|-------------|
| `--name <name>` | Project name (default: directory name) |
| `--force` | Overwrite existing |
| `--destroy-token <token>` | Required for force in non-interactive |
| `--quiet` | Minimal output |
| `--no-git` | Skip git operations |
| `--skip-agents` | Skip AGENTS.md generation |

#### Post-Init Actions

1. Create `.long-run-agent/` structure
2. Generate `constitution.yaml` with defaults
3. Write `.lra_version` file
4. Initialize git repo if not exists
5. Create AGENTS.md with instructions
6. Run `lra doctor` to verify init

#### Version Tracking

```bash
# .lra_version file
LRA_VERSION=5.0.0
INITIALIZED=2026-04-08T10:30:00Z
```

Purpose:
- Detect when CLI version doesn't match project version
- Warn about potential compatibility issues
- Guide upgrade process

---

## 4. AGENTS.md Integration

### Purpose

Tell AI agents how to use LRA. This file is auto-generated during `lra init` and should be added to version control.

### Generated Content

```markdown
# LRA (Long-Running Agent) Instructions

## Quick Start

```bash
lra list              # List all tasks
lra ready             # List tasks ready to work on
lra show <id>         # Show task details
lra new "<title>" -p 1  # Create new task
```

## Standard Workflow

1. **Check ready tasks**: `lra ready`
2. **Claim task**: `lra claim <id>`
3. **Do work**, checkpoint: `lra checkpoint <id> --note "progress message"`
4. **Complete task**: `lra complete <id>`

## Task Lifecycle

```
pending → in_progress → completed → optimizing → truly_completed
                      ↘ blocked ↗
```

- `pending`: Not started, may have blockers
- `in_progress`: Being worked on
- `completed`: Initial work done, quality checks may run
- `optimizing`: Fixing quality issues
- `truly_completed`: All quality gates passed

## Important Rules

1. **ALWAYS** use `lra ready` before asking "what should I work on?"
2. **NEVER** edit task files directly — use `lra set <id> --field value`
3. **DO** use `lra heartbeat <id>` if taking a break > 15 min
4. **DO** checkpoint frequently with `lra checkpoint <id> --note "..."`
5. **DO** link related work with `lra deps add <child> <parent>`

## Task Dependencies

```bash
# Add dependency (child blocked by parent)
lra deps add <child_id> <parent_id>

# View dependencies
lra deps <id>

# Remove dependency
lra deps remove <id> <dep_id>
```

## Priority Levels

- `P0`: Critical — security, data loss, broken builds
- `P1`: High — major features, important bugs
- `P2`: Medium — default, nice-to-have
- `P3`: Low — polish, optimization
- `P4`: Backlog — future ideas

## Non-Interactive Commands

Some commands may prompt for confirmation. Use these forms to avoid hangs:

```bash
# Answer yes automatically
yes | lra init --force

# Use --yes flag
lra doctor --fix --yes
```

## Health Checks

```bash
lra doctor              # Check for issues
lra doctor --fix        # Auto-fix issues
lra doctor --verbose    # Show all checks
```

## Getting Help

```bash
lra --help             # General help
lra <command> --help   # Command-specific help
```
```

### Agent Profile Support

```bash
# Minimal profile (default) — just workflow
lra init --agents-profile minimal

# Full profile — complete command reference
lra init --agents-profile full
```

---

## 5. Implementation Plan

### Phase 1: Core Infrastructure

1. **Add `get_ready_tasks()` to TaskManager**
   - Filter by status, locks, dependencies
   - Support sorting and limits

2. **Add `cmd_ready()` to CLI**
   - Add subparser
   - Implement flags: `--json`, `-n`, `-p`, `-a`, `-u`, `-s`, `--explain`
   - Format output

### Phase 2: Health Checks

3. **Create `lra/doctor.py`**
   - Define `DoctorCheck`, `DoctorResult` dataclasses
   - Implement check functions for each category
   - Add `fix` functions where applicable

4. **Add `cmd_doctor()` to CLI**
   - Flags: `--json`, `--fix`, `--dry-run`, `--verbose`, `--check`

### Phase 3: Init Enhancement

5. **Enhance `cmd_init()`**
   - Add `--force`, `--destroy-token`, `--quiet`, `--name`
   - Add existing data detection
   - Add confirmation prompts

6. **Add version tracking**
   - Create `.lra_version` file
   - Add version check to doctor

### Phase 4: AGENTS.md

7. **Add AGENTS.md generation to init**
   - Create template in `lra/templates/agents/`
   - Generate during `lra init`
   - Support `--skip-agents` flag

---

## Files to Modify

| File | Changes |
|------|---------|
| `lra/cli.py` | Add `cmd_ready()`, `cmd_doctor()`, enhance `cmd_init()` |
| `lra/task_manager.py` | Add `get_ready_tasks()` |
| `lra/locks_manager.py` | Add `get_orphaned_locks()`, `cleanup_orphaned()` |
| `lra/config.py` | Add version tracking constants |
| `lra/doctor.py` | **NEW** — Health check implementations |
| `lra/templates/agents/defaults/` | **NEW** — AGENTS.md templates |

---

## Reference: Beads Commands Compared

| Beads | LRA | Notes |
|-------|-----|-------|
| `bd ready` | `lra ready` | Ready tasks |
| `bd doctor` | `lra doctor` | Health checks |
| `bd init` | `lra init` | Enhanced |
| `bd create` | `lra new` | Task creation |
| `bd update --claim` | `lra claim` | Atomic claim |
| `bd list` | `lra list` | List tasks |
| `bd show` | `lra show` | Task details |
| `bd close` | `lra complete` | Complete task |
| `bd blocked` | `lra check-blocked` | Blocked tasks |

---

## Open Questions

1. Should `lra ready` automatically exclude tasks assigned to other agents?
2. Should `lra doctor --fix` handle lock cleanup automatically?
3. Should AGENTS.md be generated in the project root or `.long-run-agent/`?
4. Should we support `lra doctor --agent` output format for LLM consumption?
