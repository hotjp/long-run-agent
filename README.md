# LRA - AI Agent Task Manager v5.1.3

**规范驱动 + 任务管理 + 质量保障系统 + 迭代阶段引导**

## 核心特性

- **通用任务模型**：支持软件开发、小说写作、数据处理等多种场景
- **Jinja2 模板**：强大的模板引擎，支持条件/循环语法
- **任务依赖**：DAG 依赖关系，自动解锁完成的任务
- **优先级调度**：P0-P3 优先级，Agent 自评
- **多 Agent 协作**：层级锁机制，支持大模型拆分任务、小模型并行开发
- **输出限制感知**：根据模型输出能力推荐/拆分任务
- **🆕 Agent 自治初始化** (v3.3.0): 自动预检 + 增量处理 + 文档闭环
- **✨ 质量保障系统** (v5.0.0): 验证机制 + 回归测试 + 代码质量检查
- **🎯 迭代阶段引导** (v4.1.0): 7阶段渐进式优化 + 智能引导 + 安全检查
- **🚀 Constitution机制** (v5.0.0): **规范驱动开发 + 质量门禁 + 不可协商原则**
- **🌍 跨平台支持** (v5.0.0): **Windows / Linux / macOS 全平台兼容**
- **🔄 Relay 全自动接力** (v5.1.0): **任务全自动执行 + 断点续跑 + 多任务串行**

## 安装

```bash
# 安装（自动包含 Jinja2）
pip install long-run-agent

# 开发环境
pip install long-run-agent[dev]

# 完整安装（包含浏览器测试支持）
pip install long-run-agent[full]
```

**注意**：安装包名为 `long-run-agent`，命令行工具为 `lra`。

## 快速开始

```bash
# 初始化项目（自动创建Constitution）
cd /your/project
lra init --name "My Project"

# 快速创建+认领任务（推荐）
lra new "实现登录功能"

# 复杂任务：自动拆分+认领第一个子任务
lra new "实现用户认证模块" --auto-split

# 查看Constitution配置
lra constitution show

# Agent 获取上下文
lra context --output-limit 8k

# Agent 上下文重建（推荐）
lra orientation

# 查看项目进度
lra status
```

## 🆕 Constitution功能 (v5.0)

### 核心概念

Constitution定义项目的**不可协商原则**和**质量标准**，在任务完成前自动验证，确保质量底线。

### 快速上手

```bash
# 1. 查看Constitution使用指南
lra constitution help

# 2. 查看当前配置
lra constitution show

# 3. 验证配置有效性
lra constitution validate

# 4. 创建任务
lra create "实现登录功能"

# 5. 完成任务（自动验证Constitution）
lra set task_001 completed
# 如果验证失败，会自动进入optimizing状态并给出修复建议
```

### 三层原则体系

| 原则类型 | 说明 | 强制性 |
|---------|------|--------|
| 🔴 NON_NEGOTIABLE | 不可协商原则 | 必须通过，无法绕过 |
| 🟡 MANDATORY | 强制原则 | 必需门禁必须通过 |
| 🟢 CONFIGURABLE | 可配置原则 | 可启用/禁用 |

### 三种门禁类型

- **command**: 执行shell命令检查（如：`pytest tests/`）
- **field_exists**: 检查任务文件字段（如：`test_evidence`）
- **custom**: 自定义检查函数

### 强制执行机制

⚠️ **重要**: Constitution在以下场景**自动验证**，AI无法绕过：

1. **任务完成时** (`lra set task completed`) - 自动验证所有原则
2. **Ralph Loop完成时** - 必须通过所有原则
3. **强制完成时** - NON_NEGOTIABLE原则仍需通过

**无法偷懒保证**: 即使使用`--force`参数，NON_NEGOTIABLE原则也必须通过！

### 配置文件

配置文件位置：`.long-run-agent/constitution.yaml`

示例配置：
```yaml
core_principles:
  - id: "no_broken_tests"
    type: "NON_NEGOTIABLE"
    name: "测试必须通过"
    gates:
      - type: "command"
        command: "pytest tests/"
```

### 详细文档

- `docs/CONSTITUTION_ENFORCEMENT.md` - 强制执行机制说明
- `docs/CONSTITUTION_DESIGN.md` - 详细设计文档
- `CONSTITUTION_COMPLETE.md` - 功能完成报告

## 🆕 Relay 全自动接力 (v5.1)

### 核心概念

Relay 让 `lra relay` 成为 Agent 的**自动驾驶模式**——从 `get_ready_tasks()` 获取任务 → CLAIM 加锁 → 运行 Claude agent → Constitution 验证 → `update_status()` → git commit，全部自动完成，无需人工干预。

### 快速上手

```bash
# 干跑（不执行，只显示将要运行的任务）
lra relay --dry-run

# 运行 relay，最多执行 10 个任务
lra relay --max-steps 10

# 全自动运行（直到队列空或达到 max-steps）
lra relay
```

### 崩溃恢复

Relay 通过**阶段级提交**实现断点续跑：

```
task_001: stage1 commit → stage2 commit → stage3 commit → crash!
新进程: 读取 ralph.iteration=2 → 从 stage3 续跑
       （stage2 重复提交无害）
```

- **每阶段完成后立即 git commit**，iteration 在 commit 之后才递增
- **锁超时 15 分钟**：进程崩溃后 15 分钟锁变为 orphan，新进程可接管
- **接续后 iteration 对齐**：新进程从 `ralph.iteration` 指向的下一个阶段开始

### 并发安全

- **文件锁**（`fcntl.flock`）：同一 repo 同时只能运行一个 relay 实例
- **任务级锁**（`LocksManager.claim`）：同一任务同时只能被一个进程 claim
- 多 Agent 并发时，各自 claim 不同任务，提交到同一分支，无 merge 冲突

### 设计原则

| 原则 | 说明 |
|------|------|
| 无 relay branch | 所有提交直接在当前分支，简化 merge 冲突 |
| Per-stage commit | 每个阶段完成后立即提交，崩溃不丢进度 |
| 提交后再递增 iteration | iteration 值永远对应已 commit 的状态 |
| 单实例文件锁 | 防止同一 repo 并发运行多个 relay |
| 不 reset_hard | Constitution 失败后只释放锁，不回滚代码（阶段已提交） |

### 工作流

```bash
# 启动 tmux session
tmux new -s lra-relay

# 在 tmux 中运行 relay
lra relay --max-steps 100

# 如果进程崩溃，tmux session 还在
# 重新连接并运行，relay 会自动从断点续跑
tmux attach -t lra-relay
lra relay
```

## 命令参考

### 核心命令

| 命令 | 用途 |
|------|------|
| `lra init --name <name>` | 初始化项目（自动创建Constitution） |
| `lra new <desc>` | 🆕 快速创建+认领任务（自动填充字段） |
| `lra new <desc> --auto-split` | 🆕 创建+自动拆分+认领第一个子任务 |
| `lra constitution help` | 🆕 Constitution使用指南 |
| `lra constitution show` | 🆕 查看Constitution配置 |
| `lra constitution validate` | 🆕 验证Constitution有效性 |
| `lra relay [--max-steps N]` | 🆕 全自动 relay 循环（断点续跑） |
| `lra relay --dry-run` | 🆕 干跑（显示将执行的任务） |
| `lra context [--output-limit Xk]` | 获取项目状态 + 可领取任务 |
| `lra list [--status X] [--template X]` | 列出任务 |
| `lra create <desc> --template <name>` | 创建任务 |
| `lra show <id>` | 任务详情（包含迭代进度和阶段引导） |
| `lra set <id> <status>` | 更新状态（自动Constitution验证） |
| `lra set <id> force_next_stage` | 🆕 强制进入下一迭代阶段（含阶段质量检查） |
| `lra split <id> --auto` | 🆕 使用decompose建议自动拆分 |
| `lra decompose <id>` | 🆕 分析任务并建议如何拆分 |

### 🎯 Ralph Loop 迭代阶段引导 (v4.1.0)

**核心特性**：Ralph Loop 是任务级循环优化机制，让 Agent 不再"偷懒"，每一步都扎实。

**渐进式优化路径**：每个任务最多7次迭代，每次迭代有明确的目标、优先级检查项和忽略项。

**查看迭代状态**：
```bash
lra show task_001

# 输出示例：
## 🔄 Ralph Loop 状态

当前轮次: 3/7
已优化次数: 2次

### 质量检查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 测试通过 | ✅ | 通过 |
| Lint检查 | ❌ | 失败 |
| 验收标准 | ✅ | 满足 |

╔═══════════════════════════════════════════════════════════╗
║                     🎯 迭代阶段引导                   ║
╠═══════════════════════════════════════════════════════════╣
║  当前迭代: 3/7                                        ║
║  阶段名称: 质量提升                                   ║
║                                                           ║
║  📌 本次重点:                                         ║
║     • 修复 lint 警告                                  ║
║     • 改善代码结构                                    ║
║     • 增加注释                                         ║
║                                                           ║
║  ⏭️  可跳过:                                          ║
║     • 性能优化                                         ║
║     • 高级功能                                         ║
╚═══════════════════════════════════════════════════════════╝
```

**质量门禁按阶段触发**：
| 阶段 | 触发检查 | 忽略检查 |
|------|---------|---------|
| 1. 理解规划 | 目标理解、计划创建 | 实现细节 |
| 2. 基础实现 | 核心功能、可运行性 | 性能、边界 |
| 3. 功能完善 | 边界处理、错误处理 | 优化、重构 |
| 4. 质量提升 | Lint、测试覆盖 | 性能深入 |
| 5. 优化改进 | 性能指标 | 单元测试 |
| 6. 验证测试 | 全部测试、回归测试 | 文档 |
| 7. 交付准备 | 验收标准、文档完整 | - |

**支持的模板**：
- **code-module**: 理解需求 → 基础功能 → 功能完善 → 质量提升 → 优化改进 → 全面测试 → 交付准备
- **novel-chapter**: 理解大纲 → 完成初稿 → 情节完善 → 人物塑造 → 语言润色 → 逻辑检查 → 最终定稿
- **data-pipeline**: 理解需求 → 数据可用 → 数据质量 → 功能完整 → 性能优化 → 可视化 → 交付验证
- **doc-update**: 理解需求 → 内容收集 → 结构设计 → 内容编写 → 格式优化 → 审校修改 → 最终发布
- **task**: 理解规划 → 基础实现 → 功能完善 → 质量提升 → 优化改进 → 验证测试 → 交付准备

**关键特性**：
- ✅ **提前完成**：所有必需检查通过即可提前完成（不必走完7次）
- ✅ **阶段卡住检测**：同一阶段卡住3次后提示强制进入下一阶段
- ✅ **安全检查**：代码重构阶段提供测试覆盖率检查等安全提示
- ✅ **自动质量门禁**：根据当前阶段自动触发对应的质量检查

**工作流示例**：
```bash
# 1. 创建任务（自动启用 Ralph Loop）
lra create "用户登录功能" --template code-module

# 2. 认领并开始工作
lra claim task_001

# 3. 完成任务（自动触发质量检查）
lra set task_001 completed

# 4. 如果质量检查未通过，显示迭代引导
#    - 当前阶段和进度
#    - 失败原因
#    - 本次重点和可跳过项
#    - 修复建议

# 5. 修复后再次提交，可能提前完成
# 输出：🎉 恭喜！任务可提前完成（迭代 2/7）

# 6. 如果在同一阶段卡住3次
# 输出：⚠️ 在当前阶段已尝试3次，建议使用：
lra set task_001 force_next_stage  # 强制进入下一阶段
```

### 项目分析命令

| 命令 | 用途 |
|------|------|
| `lra analyze project` | 分析整个项目结构，生成文档和索引 |
| `lra analyze module <name>` | 分析指定模块代码 |
| `lra analyze module <name> --output-doc` | 分析模块并生成文档 |
| `lra system-check` | 执行系统预检 |
| `lra system-check --report` | 查看预检报告 |

### Agent 索引命令

| 命令 | 用途 |
|------|------|
| `lra where` | 显示所有关键文件位置 |
| `lra where --index` | 输出完整索引内容（JSON） |

### 锁命令

| 命令 | 用途 |
|------|------|
| `lra claim <id>` | 领取任务（锁定自己+子任务） |
| `lra publish <id>` | 发布子任务（释放子任务锁） |
| `lra pause <id>` | 暂停并保存快照 |
| `lra resume <id>` | 查看快照 |
| `lra heartbeat <id>` | 心跳保活（每5分钟） |
| `lra batch lock status` | 查看批量锁状态 |
| `lra batch lock acquire` | 获取批量锁 |

### 模板命令

| 命令 | 用途 |
|------|------|
| `lra template list` | 列出模板 |
| `lra template show <name>` | 查看模板详情 |
| `lra template create <name>` | 创建模板 |

### 依赖命令

| 命令 | 用途 |
|------|------|
| `lra deps <id>` | 查看任务依赖 |
| `lra deps <id> --dependents` | 查看依赖此任务的其他任务 |
| `lra check-blocked` | 检查并解锁 blocked 任务 |

### 优先级命令

| 命令 | 用途 |
|------|------|
| `lra set-priority <id> <P0\|P1\|P2\|P3>` | 设置任务优先级 |

## 内置模板

| 模板 | 用途 | 状态 |
|------|------|------|
| `task` | 通用任务 | pending → in_progress → completed |
| `novel-chapter` | 小说章节 | drafting → revising → finalized |
| `code-module` | 代码模块 | pending → in_progress → pending_test → completed |
| `data-pipeline` | 数据流程 | pending → running → success |

## 多 Agent 协作流程

```
1. 大模型 new "Web应用开发" --auto-split（创建+拆分+认领第一个子任务）
2. 大模型编写架构/接口契约
3. 大模型 decompose task_001（查看拆分建议）
4. 大模型 split task_001 --auto（使用建议自动拆分）
5. 大模型 publish task_001（释放子任务锁）
6. 小模型 context --output-limit 8k（获取可领取任务）
7. 小模型 claim task_001_02（领取子任务）
8. 小模型按契约开发
9. 大模型验收/集成
```

## 输出限制适配

| 模型 | 输出限制 | 使用 |
|------|----------|------|
| GPT-4o-mini | 4K | `--output-limit 4k` |
| Claude 3.5 | 8K | `--output-limit 8k` |
| Claude 3.5 Sonnet | 16K | `--output-limit 16k` |
| Claude 3.5 Sonnet Max | 128K | `--output-limit 128k` |

## 数据结构

```
.long-run-agent/
├── config.json          # 项目配置
├── task_list.json       # 任务列表
├── locks.json           # 任务锁
├── templates/           # 模板（可自定义）
│   ├── task.yaml
│   ├── novel-chapter.yaml
│   ├── code-module.yaml
│   └── data-pipeline.yaml
├── tasks/               # 任务文件
│   └── task_001.md
└── records/             # 变更记录
    └── task_001.json
```

## 自定义模板

```yaml
# .long-run-agent/templates/my-template.yaml
name: my-template
description: 我的自定义模板
version: "2.0"
template_engine: jinja2  # 使用 Jinja2 引擎

structure: |
  # {{ id }}
  
  ## 描述
  {{ description }}
  
  {% if tech_stack %}
  ## 技术栈
  {{ tech_stack }}
  {% endif %}
  
  ## 交付物
  <!-- 请列出交付物 -->

states:
  - pending
  - working
  - done

transitions:
  pending: [working]
  working: [done]
  done: []

acceptance:
  - 验收标准 1
  - 验收标准 2
```

## 创建任务示例

```bash
# 基础创建
lra create "实现用户登录"

# 带优先级
lra create "紧急 Bug 修复" --priority P0

# 带依赖
lra create "集成测试" --dependencies task_001,task_002 --dependency-type all

# 带截止时间
lra create "发布版本" --deadline "2026-02-28T23:59:59"

# 带模板变量
lra create "API 开发" --template code-module \
  --variables '{"tech_stack": "FastAPI", "input_params": "user_id"}'
```

## 状态说明

| 状态 | 说明 |
|------|------|
| `blocked` | 依赖未完成，不可领取 |
| `pending` | 初始状态，可领取 |
| `in_progress` | 进行中 |
| `completed` | 完成（终态） |

**blocked 状态自动解锁**：当依赖的任务完成后，blocked 任务会自动变为 pending 状态。

## 🆕 v3.3.0 Agent 自治式初始化

### 系统预检任务

LRA v3.3.0 引入**自动化系统预检**，在首次创建任务时自动执行项目评估：

**检测维度**：
- ✅ 代码规模（≤5MB）
- ✅ Git 提交规范性（≥30%）
- ✅ 文档覆盖率（≥40%）
- ✅ 函数注释占比（≥20%）

**决策模式**：
- **全量模式**（OR 逻辑，任一条件满足）：
  - 代码体积 ≤ 5MB
  - 或 文档覆盖率 ≥ 40%
  - 或 Git 规范提交 ≥ 30%
- **增量模式**（所有条件均不满足）：仅允许创建模块级任务

**强制全量解析**：
使用 `--force` 参数可强制进入全量解析模式，忽略所有阈值检查。

**使用方法**：
```bash
# 自动触发（首次创建任务时）
lra create "支付模块开发"

# 手动执行预检
lra system-check

# 查看预检报告
lra system-check --report

# 强制重新检查
lra system-check --full

# 强制全量解析模式（忽略阈值）
lra system-check --force

# 分析指定模块（代码结构分析）
lra analyze module QAFetch

# 分析模块并生成文档
lra analyze module QAFetch --output-doc

# 分析整个项目
lra analyze project

# 分析项目并生成文档到指定目录
lra analyze project --output-dir docs

# 强制重新分析
lra analyze project --force

# 分析项目但不创建任务
lra analyze project --no-create-tasks
```

### 项目分析器

v3.4.0 新增**项目代码分析器**，支持多语言项目结构分析：

**支持语言**：Python、JavaScript/TypeScript、Go

**分析内容**：
- 项目模块结构
- 文件数量、代码行数
- 核心类和函数
- 模块依赖关系
- 文档覆盖率

**输出结构**：
```
项目根目录/
├── docs/                           # 人类可读文档
│   ├── MODULES.md                  # 模块总览
│   ├── modules/                    # 模块详情
│   └── files/                      # 文件详情
│
└── .long-run-agent/analysis/
    ├── index.json                  # Agent 快速索引（类/函数/文件）
    ├── summary.json                # 项目摘要
    └── modules/                    # 模块详情 JSON
```

**Agent 快速索引**：
```json
// .long-run-agent/analysis/index.json
{
  "classes": {
    "Calculator": {"file": "mymodule.py", "line": 3, "methods": ["add"]}
  },
  "functions": {
    "helper": {"file": "mymodule.py", "line": 10}
  }
}
```

**使用方法**：
```bash
# 初始化项目
lra init --name MyProject

# 执行完整项目分析
lra analyze project

# 查看 Agent 索引位置
lra where

# 输出索引内容（JSON）
lra where --index

# 查看模块详情
lra analyze module payment --output-doc

# 强制重新分析
lra analyze project --force
```

### 文档闭环

v3.3.0 新增**文档更新任务自动绑定**：

```bash
# 创建业务任务时，自动生成绑定的文档任务
lra create "支付模块开发" --priority P0

# 自动生成：doc_update_001（依赖 task_001）
# 描述：更新支付模块 README + 接口文档
```

**配置模式**（`.long-run-agent/config.yaml`）：
```yaml
system_check:
  doc_enforcement: strict  # strict(强制) | soft(推荐) | disabled(关闭)
```

### 预检报告示例

```json
{
  "project_id": "old_project_001",
  "decision": "incremental",
  "metrics": {
    "code_total_size_mb": 8.5,
    "git_valid_ratio": 0.15,
    "doc_coverage_ratio": 0.25
  },
  "reason": "代码体积 8.5MB>5MB，文档覆盖率 25%<40%，触发增量处理"
}
```

## 性能基准

### 测试环境

- **Python**: 3.9.6
- **操作系统**: macOS (darwin)
- **CPU 核心数**: 20
- **物理内存**: 64.0 GB

### 性能指标

| 规模 | 基础内存 (MB) | 峰值内存 (MB) | 每任务内存 (KB) | 创建延迟 (ms) | 读取延迟 (ms) | 更新延迟 (ms) | 吞吐量 (ops/s) |
|------|---------------|---------------|-----------------|---------------|---------------|---------------|----------------|
| 10 ⚡ | 21.8 | 22.2 | 41.6 | 2.85 | 0.06 | 3.03 | 807.58 |
| 50 ⚡ | 22.2 | 23.59 | 28.48 | 2.94 | 0.12 | 3.5 | 724.88 |
| 100 ⚡ | 23.59 | 23.83 | 2.4 | 3.25 | 0.2 | 4.25 | 663.94 |
| 200 ⚡ | 23.83 | 24.3 | 2.4 | 3.99 | 0.36 | 5.74 | 540.05 |
| 500 | 24.3 | 24.5 | 0.42 | 6.16 | 0.94 | 9.93 | 293.52 |
| 1000 | 24.5 | 26.52 | 2.06 | 9.9 | 1.91 | 17.23 | 172.12 |

**说明**:
- ⚡ 表示执行了依赖关系测试（200 任务以下）
- 测试包含：任务创建、读取、更新操作
- 详细报告：[scripts/BENCHMARK_RESULTS.md](scripts/BENCHMARK_RESULTS.md)

### 性能分析

- **内存增长**: 10 任务 → 1000 任务，内存增长仅 **19.5%**
- **平均创建延迟**: 4.85 ms
- **平均读取延迟**: 0.60 ms
- **平均更新延迟**: 7.28 ms
- **性能评级**: 🟢 **优秀** - 系统性能优秀，适合大规模任务管理

### 结沦

- ✅ **100 任务以下**: 极快响应（< 4ms），适合实时交互
- ✅ **500 任务以下**: 良好性能（< 10ms），适合常规使用
- ✅ **1000 任务**: 可接受（< 20ms），适合批量处理

## 环境要求

- Python ≥ 3.8
- Git ≥ 2.0（可选）

## 链接

- GitHub: https://github.com/hotjp/long-run-agent
- PyPI: https://pypi.org/project/lra/

## 🆕 v5.0 新功能

### 质量保障系统

v5.0 新增了完整的质量保障系统，确保任务完成质量：

#### 1. 验证前置机制

任务完成前必须提供验证证据：

```markdown
## 验证证据（完成前必填）

- [ ] **实现证明**: [描述实现]
- [ ] **测试验证**: [如何测试]
- [ ] **影响范围**: [影响的功能]

### 测试步骤
1. [步骤1]
2. [步骤2]
```

#### 2. 回归测试

```bash
# 运行回归测试
lra test regression

# 查看报告
lra test regression --report

# 测试特定模板
lra test regression --template code-module
```

#### 3. 浏览器自动化测试

```bash
# 检查任务验证状态
lra test browser task_001

# 生成测试脚本
lra test browser task_001 --script
```

#### 4. 代码质量检查

```bash
# 运行质量检查
lra test quality

# 查看报告
lra test quality --report
```

### Agent 工作流优化

#### 上下文重建协议

```bash
# Agent 专用：完整上下文重建
lra orientation
```

提供：
- 工作目录
- 项目结构
- 最近提交
- 任务进度
- Agent 索引位置

#### 进度可视化

```bash
# 查看项目进度
lra status
```

输出示例：
```
📊 项目进度: 45/200 (22.5%)

[████████░░░░░░░░░░░░░░░░░░░░░░░░░░]

📈 任务分布:
  ✅ Completed:   45 █████████████████████████
  🔄 In Progress:  5 ███
  ⏳ Pending:    150 ████████████████

⏱️  预估剩余时间: 12.5 小时
```

### 统一提示词模板

查看完整的 Agent 工作流程：
```bash
cat lra/prompts/agent_prompt.md
```

13步标准化工作流，包含完整的故障排除指南。

## 命令参考

### 核心命令

| 命令 | 用途 |
|------|------|
| `lra init --name <name>` | 初始化项目（默认 task 模板） |
| `lra context [--output-limit Xk]` | 获取项目状态 + 可领取任务 |
| `lra list [--status X] [--template X]` | 列出任务 |
| `lra create <desc> --template <name>` | 创建任务 |
| `lra show <id>` | 任务详情 |
| `lra set <id> <status>` | 更新状态（受模板约束） |
| `lra split <id> --plan '<json>'` | 拆分任务（模型提供方案） |

### 🆕 质量保障命令

| 命令 | 用途 |
|------|------|
| `lra status` | 项目进度可视化 |
| `lra orientation` | Agent上下文重建 |
| `lra test regression [--report]` | 回归测试 |
| `lra test browser <id> [--script]` | 浏览器自动化测试 |
| `lra test quality [--report]` | 代码质量检查 |

## 🆕 迭代阶段引导机制

**每个任务支持最多7次迭代优化，每次迭代有明确的阶段目标**：

### 迭代阶段示例（code-module模板）

```
迭代1: 基础功能验证  - 让功能跑起来
迭代2: 功能完善      - 补充测试和边界情况
迭代3: 代码质量提升  - 修复lint、改善结构
迭代4: 初步优化      - 性能瓶颈分析
迭代5: 代码重构      - 消除重复、优化设计（有安全检查）
迭代6: 全面测试      - 集成测试、性能测试
迭代7: 交付准备      - 文档、审查、交付
```

### 关键特性

1. **提前完成**：所有必需检查通过即可提前退出（不必走完7次）
2. **阶段卡住检测**：同一阶段失败3次后提示强制进入下一阶段
3. **安全检查**：代码重构阶段自动检查测试覆盖率等安全指标

详细文档：`ITERATION_GUIDANCE_FINAL_REPORT.md`

