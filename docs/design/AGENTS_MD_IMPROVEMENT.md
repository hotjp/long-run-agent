# Agent 文件改进设计文档

## 背景

LRA 当前在 `lra init` 时复制 `AGENTS.md` 模板到项目根目录，但：
1. 模板内容简单，缺少企业级特性
2. 无 profile 机制，无法区分场景
3. 无 section 标记，无法增量更新
4. 无多 agent 入口文件

## 借鉴 Beads 的设计

### Beads 的关键设计

1. **Profile 机制**: `full` vs `minimal` 两种模板
2. **Section 标记**: `<!-- BEGIN/END BEADS INTEGRATION -->` 包裹
3. **增量更新**: 只更新 section 部分，保留用户内容
4. **Session Completion**: 明确的工作结束 checklist
5. **禁止规则**: 明确禁止使用其他追踪系统

## 目标文件结构

```
lra init 生成：
├── agent.md      # 通用入口（任何 agent 读这个）
├── lra.md       # LRA 专用指南（用 LRA 的 agent 读这个）
└── CLAUDE.md    # Claude Code 专用（Claude Code 读这个）
```

### 文件职责分工

| 文件 | 读取者 | 内容 |
|------|--------|------|
| `agent.md` | 任何 agent | 通用入口、项目概述、快速开始、外部依赖、**链接到 lra.md** |
| `lra.md` | 用 LRA 的 agent | LRA CLI 工具指南、命令参考、workflow、禁止规则 |
| `CLAUDE.md` | Claude Code | Claude 特定优化、项目架构决策、**链接到 lra.md** |

## 目标文件内容

### agent.md (通用入口)

```markdown
# Agent Guide

> 本项目使用 **LRA** (Long-Running Agent) 管理任务进度。

## 项目信息

- **项目**: {project_name}
- **任务管理**: 使用 LRA
- **Constitution**: [.long-run-agent/constitution.yaml](.long-run-agent/constitution.yaml)

## 快速开始

```bash
cat lra.md              # 查看 LRA 工具使用说明
lra ready               # 查看可认领任务
lra show <id>          # 查看任务详情
```

## 外部依赖

详见: [.long-run-agent/config.json](.long-run-agent/config.json)

## 相关文档

- [lra.md](lra.md) - LRA 详细命令 ← 工具使用说明
- [CLAUDE.md](CLAUDE.md) - Claude Code 特定优化

<!-- BEGIN LRA AGENT SECTION -->

## LRA 任务管理

本项目使用 **LRA** (Long-Running Agent) 管理任务。

- 详细说明: [lra.md](lra.md)
- ❌ 不要使用 markdown TODO 列表

<!-- END LRA AGENT SECTION -->
```

### lra.md (LRA 专用)

lra.md 是 agent 了解 LRA 的唯一渠道，内容必须完整。

详见下方 **lra-full.md 内容** 章节（完整内容）。

### CLAUDE.md (Claude Code 专用)

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Project**: {project_name}
**Description**: {project_description}

## Architecture

{project_architecture}

## Task Management

This project uses **LRA** for task tracking.
See [lra.md](lra.md) for command reference.

## Quick Start

```bash
lra ready              # Find available work
lra show <id>          # View task details
```

<!-- BEGIN LRA CLAUDE SECTION -->

## LRA Task Management

This project uses **LRA** profile: **{profile}**

- Detailed guide: [lra.md](lra.md)
- Use `lra` for all task management
- Run `lra ready` before starting work
- ❌ Do not use markdown TODO lists

<!-- END LRA CLAUDE SECTION -->
```

## 实现方案

### 模板文件结构

```
lra/templates/agents/
├── defaults/
│   ├── agent.md          # 通用入口模板
│   ├── lra-minimal.md   # LRA minimal profile
│   └── lra-full.md       # LRA full profile
└── partials/
    └── ...
```

### 三种文件的创建/更新逻辑

| 文件 | 不存在 | 存在 |
|------|--------|------|
| `lra.md` | 创建 | **只更新 LRA 相关 section** |
| `agent.md` | 创建 | 有 LRA section 则不更新，没有则更新 |
| `CLAUDE.md` | 创建 | 有 LRA section 则不更新，没有则更新 |

**核心原则**：
- `lra.md` 支持增量更新（通过 section 标记）
- `agent.md` 和 `CLAUDE.md` 首次创建后，如果已有 LRA section 则保留用户内容

### 修改 `_copy_agents_template` 方法

```python
def _copy_agents_template(self, profile: str = "minimal"):
    """
    创建/更新 agent 指南文件

    逻辑：
    - lra.md: 不存在则创建，存在则只更新 LRA section
    - agent.md: 不存在则创建，存在则不更新
    - CLAUDE.md: 不存在则创建，存在则不更新
    """
    import shutil

    lra_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(lra_dir, "templates", "agents", "defaults")
    dst_dir = os.getcwd()

    # 1. lra.md (LRA 专用) - 存在则更新 section
    lra_src = os.path.join(templates_dir, f"lra-{profile}.md")
    if not os.path.exists(lra_src):
        lra_src = os.path.join(templates_dir, "lra-full.md")
    lra_dst = os.path.join(dst_dir, "lra.md")
    self._update_or_create(lra_dst, lra_src, "BEGIN LRA INTEGRATION")

    # 2. agent.md (通用入口) - 不存在则创建，存在但无 LRA section 则更新
    agent_dst = os.path.join(dst_dir, "agent.md")
    self._update_or_create(agent_dst,
                           os.path.join(templates_dir, "agent.md"),
                           "BEGIN LRA AGENT SECTION")

    # 3. CLAUDE.md - 不存在则创建，存在但无 LRA section 则更新
    claude_dst = os.path.join(dst_dir, "CLAUDE.md")
    self._update_or_create(claude_dst,
                           os.path.join(templates_dir, "claude.md"),
                           "BEGIN LRA CLAUDE SECTION")
```

### Section 增量更新逻辑

```python
import re

def _update_or_create(self, dst: str, src: str, section_marker: str, allow_replace: bool = False):
    """
    增量更新: 只更新 section 标记内的内容

    Args:
        dst: 目标文件路径
        src: 模板文件路径
        section_marker: section 标记（如 "BEGIN LRA INTEGRATION"）
        allow_replace: 是否允许替换 section（lra.md 允许，agent.md/CLAUDE.md 不允许）

    逻辑：
    - 如果目标文件不存在: 直接复制
    - 如果目标文件存在但没有 section 标记: 追加模板内容
    - 如果目标文件存在且有 section 标记:
        - lra.md (allow_replace=True): 替换 section 部分
        - agent.md/CLAUDE.md (allow_replace=False): 保持不变
    """
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        return

    with open(dst, 'r') as f:
        existing = f.read()

    with open(src, 'r') as f:
        template = f.read()

    # 如果没有 section 标记，追加
    if section_marker not in existing:
        if not existing.endswith('\n'):
            existing += '\n'
        with open(dst, 'w') as f:
            f.write(existing + '\n' + template)
        return

    # 如果有 section 标记
    if not allow_replace:
        # agent.md / CLAUDE.md: 已有 LRA section，不更新
        return

    # lra.md: 替换 section 部分
    self._replace_section(existing, template, section_marker, dst)


def _replace_section(self, existing: str, template: str, section_marker: str, dst: str):
    """
    替换 section 标记内的内容
    """
    import re

    # 从模板中提取新的 section 内容（包括标记）
    pattern = rf'(<!-- {section_marker} -->\n).*?(<!-- END {section_marker} -->)'
    match = re.search(pattern, template, re.DOTALL)
    if not match:
        return

    new_section = template[match.start():match.end()]

    # 替换目标文件中的 section
    new_content = re.sub(pattern, new_section, existing, flags=re.DOTALL)

    with open(dst, 'w') as f:
        f.write(new_content)
```

### 调用时区分

```python
# lra.md - 允许替换 section
self._update_or_create(lra_dst, lra_src, "BEGIN LRA INTEGRATION", allow_replace=True)

# agent.md / CLAUDE.md - 不允许替换
self._update_or_create(agent_dst, agent_src, "BEGIN LRA AGENT SECTION", allow_replace=False)
self._update_or_create(claude_dst, claude_src, "BEGIN LRA CLAUDE SECTION", allow_replace=False)
```

### Profile 一致性检查

```python
def _get_profile_from_section(self, content: str, section_marker: str) -> str:
    """从现有 section 中提取 profile"""
    import re
    pattern = rf'<!-- {section_marker} profile:(\w+) -->'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None

# 在替换前检查
existing_profile = self._get_profile_from_section(existing, "BEGIN LRA INTEGRATION")
if existing_profile and existing_profile != profile:
    if existing_profile == "full" and profile == "minimal":
        # 不降级，保持 full
        return
    # 其他情况（minimal -> full）允许升级
```

### 重复内容清理

```python
def _deduplicate_sections(self, content: str, section_marker: str) -> str:
    """清理重复的 section"""
    import re
    pattern = rf'(<!-- {section_marker} -->\n.*?<!-- END {section_marker} -->\n?)'
    matches = re.findall(pattern, content, re.DOTALL)
    if len(matches) <= 1:
        return content
    # 只保留最后一个
    result = content
    for _ in range(len(matches) - 1):
        result = re.sub(pattern, '', result, count=1, flags=re.DOTALL)
    return result.strip() + '\n'
```

### 添加 --profile 参数

```python
init_p.add_argument(
    "--profile",
    choices=["minimal", "full"],
    default="full",
    help="Agent profile template to use"
)
```

## Profile 说明

| Profile | 适用场景 | 内容 |
|---------|---------|------|
| `minimal` | 简单项目、个人项目 | 基础 CLI + lra.md 链接 |
| `full` | 团队协作、企业项目（默认） | CLI + 禁止规则 + Session Completion |

### lra-minimal.md 内容

```markdown
# LRA Instructions

> 本项目使用 **LRA** (Long-Running Agent) 管理任务。

## Quick Start

```bash
lra ready              # 查看可认领任务
lra show <id>         # 查看任务详情
lra claim <id>        # 认领任务
```

<!-- BEGIN LRA INTEGRATION profile:minimal -->

## Issue Tracking

- ✅ 使用 `lra` 管理所有任务
- ❌ 不要使用 markdown TODO

<!-- END LRA INTEGRATION -->
```

### lra-full.md 内容

```markdown
# LRA Instructions

> **LRA** (Long-Running Agent) 是本项目的任务管理框架。
> agent 必须通过本文件了解 LRA，不要假设其他知识。

## 核心概念

LRA 使用 **Ralph Loop** 7 阶段迭代：
`pending → in_progress → completed → optimizing → truly_completed`

质量门控：后期阶段才强制性能测试和 lint。

## 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 未开始，可能有依赖阻塞 |
| `in_progress` | 进行中 |
| `completed` | 初始完成，等待质量检查 |
| `optimizing` | 修复质量问题中 |
| `truly_completed` | 全部质量门控通过 |

## 优先级

| 优先级 | 说明 |
|--------|------|
| P0 | 关键（安全、数据丢失、破坏构建）|
| P1 | 高（主要功能、重要 bug）|
| P2 | 中（默认）|
| P3 | 低（优化）|

## 完整命令参考

```bash
# 查看任务
lra list                # 列出所有任务
lra ready              # 列出可认领任务
lra show <id>          # 查看任务详情
lra status             # 查看项目进度

# 认领和操作
lra claim <id>         # 原子性认领任务
lra new "描述"         # 快速创建并认领
lra set <id> <status>  # 更新状态

# 状态流转
lra set <id> in_progress     # 开始
lra set <id> completed       # 初始完成
lra set <id> optimizing      # 优化
lra set <id> truly_completed # 完成

# 检查点
lra checkpoint <id> --note "进度"  # 保存检查点

# 依赖管理
lra deps <id>         # 查看依赖
lra deps add <child> <parent>  # 添加依赖

# 其他
lra doctor             # 健康检查
lra constitution show  # 查看 Constitution 规则
```

## Constitution 质量门控

LRA 通过 Constitution 验证任务质量：

```bash
lra check <id>         # 运行质量检查
lra constitution show  # 查看规则
```

**规则类型**：
- `NON_NEGOTIABLE`: 无法绕过
- `MANDATORY`: 必须通过
- `CONFIGURABLE`: 可选

## 工作流程

```
1. lra ready              # 查看可认领任务
2. lra claim <id>        # 原子性认领
3. lra set <id> in_progress
4. 实现功能
5. lra checkpoint <id> --note "完成核心逻辑"
6. lra set <id> completed
7. lra check <id>        # 运行 Constitution 验证
8. 如果失败: lra set <id> optimizing → 修复 → 回到 step 6
9. 成功后: lra set <id> truly_completed
```

## Session 完成 Checklist

**结束 session 前必须**：

1. `lra checkpoint <id> --note "当前进度"` 保存所有进行中的任务
2. `lra set <id> completed/optimizing` 更新状态
3. Git 推送：
   ```bash
   git add .
   git commit -m "..."
   git push
   ```
4. 为下一个 agent 提供上下文（已完成什么、下一步是什么）

## 禁止规则

- ❌ 不要创建 markdown TODO 列表
- ❌ 不要使用 LRA 以外的追踪系统
- ❌ 不要跳过 `lra ready` 直接问"我该做什么"
- ❌ 不要编辑 task 文件（用 `lra set` 命令）

## 非交互命令

**始终使用非交互标志**，避免命令挂起：

```bash
cp -f source dest      # 不要用: cp source dest
rm -f file            # 不要用: rm file
rm -rf directory      # 不要用: rm -r directory
```

## 外部依赖

本项目的外部服务配置在 `.long-run-agent/config.json`。

<!-- BEGIN LRA INTEGRATION profile:full -->
<!-- 此 section 由 lra init 管理，请勿手动修改 -->
<!-- END LRA INTEGRATION -->
```

## 迁移计划

### Phase 1: 新文件名 + 创建逻辑
- 重命名 `AGENTS.md` → `lra.md`
- 新增 `agent.md` 模板
- 新增 `CLAUDE.md` 模板
- 实现创建逻辑（不存在则创建）

### Phase 2: Section 增量更新
- 实现 `<!-- BEGIN LRA INTEGRATION -->` 标记
- 实现 `_update_or_create` 逻辑
- `allow_replace` 参数区分 lra.md 和 agent.md/CLAUDE.md

### Phase 3: Profile 机制
- 支持 `minimal` 和 `full` 两种 profile
- Profile 一致性检查（full 不会降级到 minimal）
- 重复内容清理

## 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 文件不存在 | 直接复制 |
| lra.md 有 section | 替换 section |
| lra.md 无 section | 追加 |
| agent.md/CLAUDE.md 有 section | 不更新（保留用户内容） |
| agent.md/CLAUDE.md 无 section | 追加 |
| full → minimal | 保持 full（不降级） |
| minimal → full | 升级为 full |
| 重复 init | 去重处理，只保留一个 section |
