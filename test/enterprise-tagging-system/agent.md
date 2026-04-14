# Agent 通用指南

> 本项目使用 LRA (Long-Running Agent) 管理任务进度。

## 项目信息

- **项目**: 企业标签系统
- **任务管理**: 使用 LRA
- **当前阶段**: 规划中 (task_001 进行中)

## 快速开始

### 1. 了解项目
```bash
cat CLAUDE.md           # 项目架构和决策
cat AGENTS.md           # LRA 使用说明
```

### 2. 查看任务
```bash
lra list               # 全部任务
lra ready              # 可认领的任务
lra show <task_id>     # 任务详情
```

### 3. 开始工作
```bash
lra claim <task_id>    # 认领任务
lra set <task_id> in_progress  # 开始工作
```

### 4. 更新进度
```bash
lra checkpoint <task_id> --note "完成设计"
lra set <task_id> completed     # 完成任务
```

## 外部依赖

| 服务 | 说明 |
|------|------|
| auth-center | 企业 IAM 服务，本系统调用其 API，不自行实现 |

详见: [.long-run-agent/config.json](.long-run-agent/config.json)

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 项目架构决策
- [AGENTS.md](AGENTS.md) - LRA 详细命令
- [docs/](docs/) - 详细设计文档
