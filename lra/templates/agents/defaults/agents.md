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
3. **Do work**, checkpoint frequently: `lra checkpoint <id> --note "progress"`
4. **Complete task**: `lra complete <id>`

## Task Lifecycle

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
- `P2`: Medium (default) — nice-to-have
- `P3`: Low — polish, optimization
- `P4`: Backlog — future ideas

## Health Checks

```bash
lra doctor              # Check for issues
lra doctor --fix        # Auto-fix issues
lra doctor --verbose    # Show all checks
```

## Non-Interactive Commands

Some commands may prompt for confirmation. Use these forms to avoid hangs:

```bash
# Answer yes automatically
yes | lra init --force

# Use --yes flag where available
lra doctor --fix --yes
```
