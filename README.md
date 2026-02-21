<div align="center">

# LRA - Long-Running Agent Tool

**一个强大的长时 AI Agent 任务管理框架**

基于 Anthropic 论文 [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的最佳实践实现。

**A powerful framework for managing long-running AI Agent tasks**

Based on best practices from Anthropic's paper [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

[![PyPI version](https://img.shields.io/pypi/v/long-run-agent.svg)](https://pypi.org/project/long-run-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

**[English](#english) | [中文](#中文)**

</div>

---

# 中文

## 一键安装

```bash
pip install long-run-agent
```

就这么简单。

---

## 🤖 给 AI Agent 使用

**只需两步，让你的 AI Agent 拥有长期记忆：**

### 1. 初始化项目

```bash
cd /path/to/your/project
lra project create --name "我的项目"
```

### 2. 告诉你的 AI Agent

> **每次开始工作时，先读取 `.long-run-agent/feature_list.json`，了解当前项目进度和待开发功能。完成后更新对应 Feature 的状态。**

就这样。AI Agent 会自动：
- 知道哪些功能已完成
- 知道哪些功能待开发
- 知道每个功能的优先级
- 跨会话保持项目记忆

**高级用法：** 让 AI Agent 读取 `.long-run-agent/specs/` 下的需求文档，了解每个功能的详细设计。

---

## 快速上手

```bash
# 查看版本
lra version

# 创建 Feature
lra feature create "用户登录功能" --category backend --priority P0

# 查看状态
lra feature list

# 更新状态
lra feature status feature_001 --set in_progress
lra feature status feature_001 --set completed

# 查看统计
lra stats
```

---

## 解决的问题

| 挑战 | LRA 如何解决 |
|------|-------------|
| **上下文窗口限制** | 状态持久化在 `.long-run-agent/` 目录，AI 随时可读 |
| **过早完成** | 状态流转规则强制验证，测试通过才能标记完成 |
| **一次性做太多** | Feature 粒度拆分，按优先级逐个开发 |
| **状态追踪困难** | `lra feature list` 一目了然 |
| **需求文档混乱** | 标准模板 + 自动校验 |

---

## 核心特性

### 🔄 自动升级
- 版本检测 + 自动数据迁移
- 备份 + 回滚，零风险

### 📋 7 状态管理
```
pending → in_progress → pending_test → completed
         ↓              ↓
      blocked ←     test_failed
```

### 📝 需求文档
- 标准模板自动生成
- 完整性自动校验

### 📊 代码变更记录
- 按 Feature 分文件存储
- 支持 Git Commit 关联

### 📜 操作审计
- 谁在什么时候做了什么
- 完整追溯

### 🔀 Git 集成
- 自动获取 Commit 信息
- Branch 命名规范检测

---

## CLI 命令速查

```bash
# 版本管理
lra version              # 显示版本
lra upgrade              # 执行升级
lra rollback             # 回滚

# Feature 管理
lra feature create <title> [--priority P0|P1|P2]
lra feature list
lra feature status <id> [--set <status>]

# 需求文档
lra spec create <feature_id>
lra spec validate <feature_id>
lra spec list

# 代码记录
lra records --feature <id>
lra records --file <path>

# 项目管理
lra project create --name <name>
lra project list

# 其他
lra stats                # 项目统计
lra logs                 # 操作日志
lra code check <path>    # 代码检查
lra git --feature <id>   # Git 信息
lra statuses             # 状态列表
```

---

## 目录结构

初始化后会在项目根目录创建：

```
.long-run-agent/
├── config.json              # 项目配置 + 版本
├── feature_list.json        # Feature 列表 ← AI Agent 读这个
├── progress.log             # 操作流水账
├── operation_log.json       # 审计日志
├── specs/                   # 需求文档 ← 也可以读这个
├── records/                 # 代码变更记录
└── backup/                  # 升级备份
```

---

## 与 AI Agent 协作示例

**场景：新功能开发**

```bash
# 1. 创建 Feature
lra feature create "支付功能" --priority P0

# 2. 告诉 AI Agent
# "请读取 .long-run-agent/feature_list.json，实现 feature_042 支付功能。
#  完成后运行 lra feature status feature_042 --set pending_test"

# 3. AI Agent 工作完成后检查
lra feature status feature_042

# 4. 测试通过后标记完成
lra feature status feature_042 --set completed
```

**场景：跨会话继续开发**

```
# AI Agent 启动时说：
> "请读取 .long-run-agent/feature_list.json，告诉我：
>  1. 当前有哪些 pending 状态的功能
>  2. 哪些是 P0 优先级
>  3. 继续开发哪个功能"
```

---

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.8 |
| Git | ≥ 2.0（可选） |

---

## 更多资源

- **GitHub**: https://github.com/hotjp/long-run-agent
- **PyPI**: https://pypi.org/project/long-run-agent/
- **问题反馈**: https://github.com/hotjp/long-run-agent/issues

---

# English

## One-Line Install

```bash
pip install long-run-agent
```

That's it.

---

## 🤖 For AI Agents

**Two steps to give your AI Agent long-term memory:**

### 1. Initialize Project

```bash
cd /path/to/your/project
lra project create --name "My Project"
```

### 2. Tell Your AI Agent

> **At the start of each session, read `.long-run-agent/feature_list.json` to understand current progress and pending features. Update Feature status when done.**

Your AI Agent will automatically:
- Know which features are completed
- Know which features are pending
- Know feature priorities
- Maintain project memory across sessions

---

## Quick Reference

```bash
lra version                           # Show version
lra project create --name "My App"    # Initialize project
lra feature create "Login" -p P0      # Create feature
lra feature list                      # List features
lra feature status feature_001 --set in_progress
lra stats                             # Show statistics
```

---

## CLI Commands

```bash
# Version
lra version / upgrade / rollback

# Features
lra feature create <title> [--priority P0|P1|P2]
lra feature list / status <id>

# Specs
lra spec create / validate / list

# Records
lra records --feature <id> / --file <path>

# Project
lra project create / list

# Utils
lra stats / logs / code check / git / statuses
```

---

## Directory Structure

```
.long-run-agent/
├── config.json              # Config + version
├── feature_list.json        # Feature list ← AI reads this
├── specs/                   # Requirement docs
├── records/                 # Code change records
└── backup/                  # Upgrade backups
```

---

## Requirements

| Dependency | Version |
|------------|---------|
| Python | ≥ 3.8 |
| Git | ≥ 2.0 (optional) |

---

## Links

- **GitHub**: https://github.com/hotjp/long-run-agent
- **PyPI**: https://pypi.org/project/long-run-agent/
- **Issues**: https://github.com/hotjp/long-run-agent/issues

---

<div align="center">

**Made with ❤️ for AI Agent Developers**

</div>
