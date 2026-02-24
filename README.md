# LRA - AI Agent Task Manager v3.2

**通用 AI Agent 任务管理框架**

## 核心特性

- **通用任务模型**：支持软件开发、小说写作、数据处理等多种场景
- **Jinja2 模板**：强大的模板引擎，支持条件/循环语法
- **任务依赖**：DAG 依赖关系，自动解锁完成的任务
- **优先级调度**：P0-P3 优先级，Agent 自评
- **多 Agent 协作**：层级锁机制，支持大模型拆分任务、小模型并行开发
- **输出限制感知**：根据模型输出能力推荐/拆分任务

## 安装

```bash
# 基础安装
pip install long-run-agent

# 完整安装（包含 Jinja2 模板引擎）
pip install long-run-agent[full]
```

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
| `lra context [--output-limit Xk]` | 获取项目状态 + 可领取任务 |
| `lra list [--status X] [--template X]` | 列出任务 |
| `lra create <desc> --template <name>` | 创建任务 |
| `lra show <id>` | 任务详情 |
| `lra set <id> <status>` | 更新状态（受模板约束） |
| `lra split <id> --plan '<json>'` | 拆分任务（模型提供方案） |

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

## 环境要求

- Python ≥ 3.8
- Git ≥ 2.0（可选）

## 链接

- GitHub: https://github.com/hotjp/long-run-agent
- PyPI: https://pypi.org/project/long-run-agent/
