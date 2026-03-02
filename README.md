# LRA - AI Agent Task Manager v3.3

**通用 AI Agent 任务管理框架 - Agent 自治式初始化**

## 核心特性

- **通用任务模型**：支持软件开发、小说写作、数据处理等多种场景
- **Jinja2 模板**：强大的模板引擎，支持条件/循环语法
- **任务依赖**：DAG 依赖关系，自动解锁完成的任务
- **优先级调度**：P0-P3 优先级，Agent 自评
- **多 Agent 协作**：层级锁机制，支持大模型拆分任务、小模型并行开发
- **输出限制感知**：根据模型输出能力推荐/拆分任务
- **🆕 Agent 自治初始化** (v3.3.0): 自动预检 + 增量处理 + 文档闭环

## 安装

```bash
# 安装（自动包含 Jinja2）
pip install long-run-agent

# 开发环境
pip install long-run-agent[dev]
```

**注意**：v3.2.0+ Jinja2 已自动安装，无需额外操作。

## 快速开始

```bash
# 初始化项目
cd /your/project
lra init --name "My Project"

# Agent 获取上下文
lra context --output-limit 8k
```

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

### 项目分析命令

| 命令 | 用途 |
|------|------|
| `lra analyze-project` | 分析整个项目结构，生成文档和索引 |
| `lra analyze-module <name>` | 分析指定模块代码 |
| `lra analyze-module <name> --output-doc` | 分析模块并生成文档 |
| `lra system-check` | 执行系统预检 |
| `lra system-check --report` | 查看预检报告 |

### Agent 索引命令

| 命令 | 用途 |
|------|------|
| `lra where` | 显示所有关键文件位置 |
| `lra index` | 输出 Agent 索引文件路径 |
| `lra index --content` | 输出完整索引内容（JSON） |

### 锁命令

| 命令 | 用途 |
|------|------|
| `lra claim <id>` | 领取任务（锁定自己+子任务） |
| `lra publish <id>` | 发布子任务（释放子任务锁） |
| `lra pause <id>` | 暂停并保存快照 |
| `lra resume <id>` | 查看快照 |
| `lra heartbeat <id>` | 心跳保活（每5分钟） |

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
1. 大模型 claim task_001（整个模块）
2. 大模型编写架构/接口契约
3. 大模型 split task_001 --plan '[...]'
4. 大模型 publish task_001（释放子任务锁）
5. 小模型 context --output-limit 8k（获取可领取任务）
6. 小模型 claim task_001_01（领取子任务）
7. 小模型按契约开发
8. 大模型验收/集成
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
lra analyze-module QAFetch

# 分析模块并生成文档
lra analyze-module QAFetch --output-doc

# 分析整个项目
lra analyze-project

# 分析项目并生成文档到指定目录
lra analyze-project --output-dir docs

# 强制重新分析
lra analyze-project --force

# 分析项目但不创建任务
lra analyze-project --no-create-tasks
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
lra analyze-project

# 查看 Agent 索引位置
lra where

# 输出索引内容（JSON）
lra index --content

# 查看模块详情
lra analyze-module payment --output-doc

# 强制重新分析
lra analyze-project --force
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
- PyPI: https://pypi.org/project/long-run-agent/
