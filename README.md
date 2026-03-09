# LRA - AI Agent Task Manager v4.1

**通用 AI Agent 任务管理框架 + 质量保障系统 + 迭代阶段引导**

## 核心特性

- **通用任务模型**：支持软件开发、小说写作、数据处理等多种场景
- **Jinja2 模板**：强大的模板引擎，支持条件/循环语法
- **任务依赖**：DAG 依赖关系，自动解锁完成的任务
- **优先级调度**：P0-P3 优先级，Agent 自评
- **多 Agent 协作**：层级锁机制，支持大模型拆分任务、小模型并行开发
- **输出限制感知**：根据模型输出能力推荐/拆分任务
- **🆕 Agent 自治初始化** (v3.3.0): 自动预检 + 增量处理 + 文档闭环
- **✨ 质量保障系统** (v4.0.0): 验证机制 + 回归测试 + 代码质量检查
- **🎯 迭代阶段引导** (v4.1.0): 7阶段渐进式优化 + 智能引导 + 安全检查

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
# 初始化项目
cd /your/project
lra init --name "My Project"

# Agent 获取上下文
lra context --output-limit 8k

# 🆕 Agent 上下文重建（推荐）
lra orientation

# 🆕 查看项目进度
lra status
```

## 命令参考

### 核心命令

| 命令 | 用途 |
|------|------|
| `lra init --name <name>` | 初始化项目（默认 task 模板） |
| `lra context [--output-limit Xk]` | 获取项目状态 + 可领取任务 |
| `lra list [--status X] [--template X]` | 列出任务 |
| `lra create <desc> --template <name>` | 创建任务 |
| `lra show <id>` | 任务详情（包含迭代进度和阶段引导） |
| `lra set <id> <status>` | 更新状态（触发质量检查，支持提前完成） |
| `lra set <id> force_next_stage` | 🆕 强制进入下一迭代阶段 |
| `lra split <id> --plan '<json>'` | 拆分任务（模型提供方案） |

### 🆕 迭代阶段引导 (v4.1.0)

**渐进式优化路径**：每个任务最多7次迭代，每次迭代有明确的目标和引导。

**查看迭代状态**：
```bash
lra show task_001

# 输出示例：
📊 迭代进度
[████████████████░░░░░░░░░░░░░░░░░░░░] 3/7 (43%)

✓ 迭代1: 基础功能验证 ✓
✓ 迭代2: 功能完善 ✓
● 迭代3: 代码质量提升 (当前)
○ 迭代4: 初步优化
○ 迭代5: 代码重构
○ 迭代6: 全面测试
○ 迭代7: 交付准备

╔═══════════════════════════════════════════════════════════╗
║                     🎯 迭代阶段引导                        ║
╠═══════════════════════════════════════════════════════════╣
║  当前迭代: 3/7                                            ║
║  阶段名称: 代码质量提升                                    ║
║                                                           ║
║  📌 本次重点:                                             ║
║     • 修复 lint 警告                                      ║
║     • 改善代码结构                                        ║
║     • 增加注释                                            ║
╚═══════════════════════════════════════════════════════════╝
```

**支持的模板**：
- **code-module**: 基础功能 → 功能完善 → 质量提升 → 性能优化 → 代码重构 → 全面测试 → 交付准备
- **novel-chapter**: 完成初稿 → 情节完善 → 人物塑造 → 场景描写 → 语言润色 → 逻辑检查 → 最终定稿
- **data-pipeline**: 数据可用 → 数据质量 → 功能完整 → 性能优化 → 可视化 → 文档编写 → 交付验证
- **doc-update**: 内容收集 → 结构设计 → 内容编写 → 格式优化 → 示例补充 → 审校修改 → 最终发布
- **task**: 理解与规划 → 基础实现 → 功能完善 → 质量提升 → 优化改进 → 验证测试 → 交付准备

**关键特性**：
- ✅ **提前完成**：所有必需检查通过即可提前完成（不必走完7次）
- ✅ **阶段卡住检测**：同一阶段卡住3次后提示强制进入下一阶段
- ✅ **安全检查**：代码重构阶段提供测试覆盖率检查等安全提示

**工作流示例**：
```bash
# 1. 完成任务（自动触发质量检查）
lra set task_001 completed

# 2. 如果质量检查通过，可能提前完成
# 输出：🎉 恭喜！任务可提前完成（迭代 3/7）

# 3. 如果阶段卡住（同一阶段3次失败）
# 输出：⚠️ 在当前阶段已尝试3次
# 选择：lra set task_001 force_next_stage  # 强制进入下一阶段
```

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
- PyPI: https://pypi.org/project/lra/

## 🆕 v4.0 新功能

### 质量保障系统

v4.0 新增了完整的质量保障系统，确保任务完成质量：

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
lra regression-test

# 查看报告
lra regression-test --report

# 测试特定模板
lra regression-test --template code-module
```

#### 3. 浏览器自动化测试

```bash
# 检查任务验证状态
lra browser-test task_001

# 生成测试脚本
lra browser-test task_001 --script
```

#### 4. 代码质量检查

```bash
# 运行质量检查
lra quality-check

# 查看报告
lra quality-check --report
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
| `lra regression-test [--report]` | 回归测试 |
| `lra browser-test <id> [--script]` | 浏览器自动化测试 |
| `lra quality-check [--report]` | 代码质量检查 |

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

