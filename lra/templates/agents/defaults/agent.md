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
