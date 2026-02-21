<div align="center">

# LRA - Long-Running Agent Tool

**一个强大的长时 AI Agent 任务管理框架**

基于 Anthropic 论文 [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的最佳实践实现。

[![PyPI version](https://img.shields.io/pypi/v/long-run-agent.svg)](https://pypi.org/project/long-run-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

**[English](#english) | [中文](#中文)**

</div>

---

# 中文

## 安装

```bash
pip install long-run-agent
```

**安装后，运行初始化：**

```bash
python3 -m long_run_agent
```

这会启动交互式安装向导：
- 🌐 语言选择（中文/英文）- **方向键切换，回车确认**
- 🔧 自动配置 PATH 环境变量
- ✅ 配置完成后立即可用 `lra` 命令
- 🤖 显示 AI Agent 引导提示词

> 💡 **提示**：如果提示 `command not found`，请运行 `source ~/.zshrc` 或重新打开终端。

---

## 🤖 给 AI Agent 使用（30秒上手）

**第一步：初始化项目**

```bash
cd /path/to/your/project
lra project create --name "我的项目"
```

**第二步：告诉 AI Agent**

> **每次开始工作，先读取 `.long-run-agent/feature_list.json` 了解项目进度和待开发功能。完成后更新对应 Feature 的状态。**

就这样！AI Agent 会自动拥有跨会话的项目记忆。

---

## 快速命令

```bash
lra version                           # 查看版本
lra project create --name "我的项目"   # 初始化项目
lra feature create "登录功能" -p P0    # 创建功能
lra feature list                      # 功能列表
lra feature status <id> --set completed  # 标记完成
lra stats                             # 项目统计
```

---

## 解决的问题

| 挑战 | LRA 如何解决 |
|------|-------------|
| **上下文窗口限制** | 状态持久化，AI 随时可读 |
| **过早完成** | 状态流转强制验证 |
| **一次性做太多** | Feature 粒度拆分 |
| **状态追踪困难** | `lra feature list` 一目了然 |
| **需求文档混乱** | 标准模板 + 自动校验 |

---

## 核心功能

- 🔄 **自动升级** - 版本检测 + 数据迁移
- 📋 **7 状态管理** - pending → completed 完整流转
- 📝 **需求文档** - 标准模板 + 完整性校验
- 📊 **代码变更记录** - 按 Feature 分文件存储
- 📜 **操作审计** - 完整操作日志追溯
- 🔀 **Git 集成** - Commit/Branch 自动关联

---

## CLI 命令速查

```bash
# 初始化
lra init                    # 安装向导
lra version                 # 版本信息

# 项目
lra project create --name <name>
lra project list

# Feature
lra feature create <title> [--priority P0|P1|P2]
lra feature list
lra feature status <id> [--set <status>]

# 需求文档
lra spec create <feature_id>
lra spec validate <feature_id>
lra spec list

# 记录
lra records --feature <id>
lra records --file <path>

# 其他
lra stats / logs / code check / git / statuses
```

---

## 与 AI Agent 协作示例

```
# 告诉 AI Agent：

请读取 .long-run-agent/feature_list.json，告诉我：
1. 当前有哪些 pending 状态的功能
2. 哪些是 P0 优先级
3. 继续开发哪个功能

完成后更新状态：lra feature status <id> --set completed
```

---

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.8 |
| Git | ≥ 2.0（可选） |

---

## 链接

- **GitHub**: https://github.com/hotjp/long-run-agent
- **PyPI**: https://pypi.org/project/long-run-agent/
- **问题反馈**: https://github.com/hotjp/long-run-agent/issues

---

# English

## Installation

```bash
pip install long-run-agent
```

**After installation, run the setup:**

```bash
python3 -m long_run_agent
```

This will:
- 🌐 Let you choose language (Chinese/English)
- 🔧 Auto-configure PATH environment variable
- ✅ After setup, `lra` command is ready to use
- 🤖 Display AI Agent guidance prompt

> 💡 **Tip**: If you see `command not found`, run `source ~/.zshrc` or restart your terminal.

---

## 🤖 For AI Agents (30 seconds)

**Step 1: Initialize Project**

```bash
cd /path/to/your/project
lra project create --name "My Project"
```

**Step 2: Tell Your AI Agent**

> **At the start of each session, read `.long-run-agent/feature_list.json` to understand current progress and pending features. Update Feature status when done.**

That's it! Your AI Agent now has cross-session project memory.

---

## Quick Commands

```bash
lra version                            # Show version
lra project create --name "My Project" # Initialize project
lra feature create "Login" -p P0       # Create feature
lra feature list                       # List features
lra feature status <id> --set completed
lra stats                              # Project statistics
```

---

## Core Features

- 🔄 **Auto-upgrade** - Version detection + data migration
- 📋 **7-state management** - pending → completed workflow
- 📝 **Requirements docs** - Templates + validation
- 📊 **Code change records** - Per-feature storage
- 📜 **Operation audit** - Complete logs
- 🔀 **Git integration** - Commit/Branch tracking

---

## CLI Reference

```bash
# Init
lra init / version

# Project
lra project create --name <name>
lra project list

# Feature
lra feature create <title> [--priority P0|P1|P2]
lra feature list / status <id>

# Spec
lra spec create / validate / list

# Records
lra records --feature <id> / --file <path>

# Utils
lra stats / logs / code check / git / statuses
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
