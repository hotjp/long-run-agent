<div align="center">

# LRA - Long-Running Agent Tool

**一个强大的长时 AI Agent 任务管理框架**

基于 Anthropic 论文 [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的最佳实践实现。

**A powerful framework for managing long-running AI Agent tasks**

Based on best practices from Anthropic's paper [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#)

**[English](#english) | [中文](#中文)**

</div>

---

# 中文

## 解决的问题 | Problems Solved

AI Agent 在长时间开发任务中面临的核心挑战：

| 挑战 | 描述 |
|------|------|
| **上下文窗口限制** | 每个新会话对之前的工作没有记忆 |
| **过早完成** | Agent 看到已有进展后容易过早宣布完成 |
| **一次性做太多** | 试图一口气完成整个项目导致中途失败 |
| **状态追踪困难** | 大型项目难以追踪每个功能的开发状态 |
| **需求文档混乱** | 缺乏统一的需求文档管理和校验机制 |

## 核心特性 | Core Features

### 🔄 自动升级机制
- 版本检测与自动数据迁移
- 升级前自动备份，失败自动回滚
- 零破坏、弱感知升级体验

### 📋 Feature 状态管理
- 7 种状态完整流转（pending → completed）
- 状态流转规则校验，防止非法变更
- 进度百分比追踪

### 📝 需求文档管理
- 标准化需求文档模板
- 自动完整性校验
- 需求状态管理（draft → approved）

### 📊 代码变更记录
- 按 Feature 分文件存储
- 双向索引（by_feature / by_file）
- 支持关联 Git Commit 信息

### 📜 操作日志审计
- 详细操作记录（谁、何时、做了什么）
- 多维度筛选（操作人、类型、Feature）
- 完整审计追溯

### 🔀 Git 集成
- 自动获取 Commit 信息
- Branch 命名规范检测
- Feature 与 Commit 自动关联

### 🔧 代码语法检查
- 多语言支持（Python, JavaScript, Go）
- 终端快速检查命令
- 自动匹配语言检测器

### 📁 多项目管理
- 项目隔离，数据独立
- 快速切换项目上下文
- 支持项目级配置

---

## 环境依赖 | Requirements

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.8 | 核心运行环境 |
| Git | ≥ 2.0 | 版本控制集成（可选） |

**可选依赖（代码检查）：**
- Node.js ≥ 14（JavaScript 检查）
- Go ≥ 1.16（Go 检查）

---

## 安装 | Installation

```bash
# 克隆仓库
git clone https://github.com/your-username/long-run-agent.git
cd long-run-agent

# 添加到 PATH（可选）
ln -s $(pwd)/lra /usr/local/bin/lra

# 或直接使用完整路径
./lra version
```

---

## 快速开始 | Quick Start

### 1. 初始化项目

```bash
# 进入你的项目目录
cd /path/to/your/project

# 初始化 LRA
lra project create my-project
```

这将在项目根目录创建 `.long-run-agent/` 目录：

```
.long-run-agent/
├── config.json              # 项目配置 + 版本信息
├── feature_list.json        # Feature 列表
├── progress.log             # 操作流水账
├── operation_log.json       # 审计日志
├── records/                 # 代码变更记录
│   └── index.json
├── specs/                   # 需求文档目录
└── backup/                  # 升级备份目录
```

### 2. 创建 Feature

```bash
# 创建新 Feature
lra feature create "用户登录功能" --category backend --priority P0 --assignee dev_001

# 查看 Feature 列表
lra feature list
```

### 3. 管理需求文档

```bash
# 创建需求文档（使用标准模板）
lra spec create feature_001

# 校验需求文档完整性
lra spec validate feature_001

# 查看所有需求文档
lra spec list
```

### 4. 状态流转

```bash
# 查看当前状态
lra feature status feature_001

# 更新状态
lra feature status feature_001 --set in_progress
lra feature status feature_001 --set pending_test
lra feature status feature_001 --set completed
```

### 5. 记录代码变更

```bash
# 关联 Git Commit 到 Feature
lra git --feature feature_001

# 按 Feature 检索代码变更
lra records --feature feature_001

# 按文件路径检索关联 Feature
lra records --file src/auth/login.py --format detail
```

### 6. 代码检查

```bash
# 检查单个文件
lra code check src/main.py

# 检查整个目录
lra code check src/ --verbose

# JavaScript 检查
lra code check src/index.js

# Go 检查
lra code check cmd/server/main.go
```

### 7. 查看统计

```bash
# 项目统计
lra stats

# 操作日志
lra logs --limit 20
lra logs --action status_change --feature feature_001
```

---

## CLI 命令参考 | CLI Reference

### 全局命令

```bash
lra version              # 显示版本信息
lra upgrade              # 执行升级
lra rollback             # 回滚到最近备份
lra stats                # 显示项目统计
lra statuses             # 列出所有可用状态
```

### Feature 管理

```bash
lra feature create <title> [--category CAT] [--priority P0|P1|P2] [--assignee NAME]
lra feature list
lra feature status <feature_id> [--set <status>]
```

### 需求文档管理

```bash
lra spec create <feature_id>
lra spec validate <feature_id>
lra spec list
```

### 代码变更记录

```bash
lra records --feature <feature_id> [--format brief|detail]
lra records --file <file_path> [--format brief|detail]
```

### 项目管理

```bash
lra project create <name>
lra project switch <name>
lra project list
```

### 操作日志

```bash
lra logs [--action ACTION] [--operator NAME] [--feature ID] [--limit N]
```

### 代码检查

```bash
lra code check <path> [--verbose]
```

### Git 集成

```bash
lra git --feature <feature_id>
```

---

## Feature 状态流转 | Status Flow

```
┌─────────────┐
│   pending   │  ← 待开发
└──────┬──────┘
       │ 启动开发
       ▼
┌─────────────┐
│ in_progress │  ← 进行中
└──────┬──────┘
       │
       ├──── 遇到阻塞 ────→ ┌─────────────┐
       │                   │   blocked   │
       │                   └──────┬──────┘
       │                          │ 阻塞解除
       │                          ▼
       │                   ┌─────────────┐
       │                   │ in_progress │
       │                   └─────────────┘
       │
       └──── 开发完成 ────→ ┌─────────────┐
                           │pending_test │  ← 待测试
                           └──────┬──────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
              测试通过                    测试失败
                    ▼                           ▼
             ┌─────────────┐            ┌─────────────┐
             │  completed  │            │ test_failed │
             └─────────────┘            └──────┬──────┘
                                                │ 返工
                                                ▼
                                         ┌─────────────┐
                                         │ in_progress │
                                         └─────────────┘
```

**特殊状态：**
- `skipped` - 从 `pending` 直接跳过（废弃需求）

---

## 需求文档模板 | Spec Template

```markdown
# Feature {id} - {title}

## 元信息
- **优先级**: P0/P1/P2（必填）
- **负责人**: （必填）
- **预计工时**: （可选）
- **创建时间**: {自动生成}

## 功能描述
<!-- 简要描述功能目标，100字以内 -->

## 功能设计方案
<!-- 详细设计方案，包含核心逻辑、接口设计等 -->

## 开发步骤
- [ ] 步骤 1：xxx
- [ ] 步骤 2：xxx

## 测试用例
| 用例编号 | 场景 | 操作步骤 | 预期结果 |
|----------|------|----------|----------|
| TC-001 | ... | ... | ... |

## 验收标准
- [ ] 标准 1：xxx
- [ ] 标准 2：xxx

## 变更记录
| 日期 | 变更内容 | 变更人 |
|------|----------|--------|
| ... | ... | ... |
```

---

## 目录结构 | Directory Structure

```
long-run-agent/
├── lra                      # CLI 入口脚本
├── config.py                # 配置管理 + 版本控制
├── feature_manager.py       # Feature 管理
├── status_manager.py        # 状态流转管理
├── spec_manager.py          # 需求文档管理
├── records_manager.py       # 代码变更记录
├── operation_logger.py      # 操作日志
├── upgrade_manager.py       # 自动升级
├── git_integration.py       # Git 集成
├── code_checker.py          # 代码语法检查
├── progress_tracker.py      # 进度追踪
├── session_manager.py       # 会话管理
├── session_orchestrator.py  # 会话编排
├── registry.py              # 资源注册
├── resource_coordinator.py  # 资源协调
├── README.md                # 本文档
├── DEVELOPMENT_STANDARDS.md # 开发规范
├── MULTI_PROJECT_GUIDE.md   # 多项目指南
└── COMPLETION_REPORT.md     # 完成报告
```

---

## 最佳实践 | Best Practices

1. **测试驱动开发** - 实现功能 → 测试 → 失败则修复 → 重测 → 通过 → 下一功能
2. **证据优先** - 无测试证据不声称完成
3. **每功能独立分支** - 每个功能在单独 Git 分支开发
4. **状态如实更新** - 及时更新 Feature 状态，保持进度可见
5. **需求先行** - 开发前确保需求文档通过校验

---

## 升级说明 | Upgrade Notes

LRA 支持自动无感知升级：

```bash
# 检查当前版本
lra version

# 手动触发升级
lra upgrade

# 如有问题回滚
lra rollback
```

升级时自动：
- 备份现有数据到 `backup/{timestamp}/`
- 迁移历史数据到新格式
- 补充缺失字段（使用默认值）
- 记录升级历史到 `config.json`

---

## 贡献指南 | Contributing

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 许可证 | License

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**Made with ❤️ for AI Agent Developers**

</div>

---

# English

## Problems Solved

Core challenges AI Agents face in long-running development tasks:

| Challenge | Description |
|-----------|-------------|
| **Context Window Limits** | Each new session has no memory of previous work |
| **Premature Completion** | Agents tend to declare completion too early after seeing progress |
| **Doing Too Much at Once** | Attempting to complete entire projects in one go leads to mid-task failures |
| **Status Tracking Difficulty** | Hard to track development status of each feature in large projects |
| **Chaotic Requirements** | Lack of unified requirements document management and validation |

## Core Features

### 🔄 Auto-Upgrade Mechanism
- Version detection and automatic data migration
- Auto-backup before upgrade, auto-rollback on failure
- Zero-destruction, low-friction upgrade experience

### 📋 Feature Status Management
- 7-state complete workflow (pending → completed)
- State transition validation, preventing illegal changes
- Progress percentage tracking

### 📝 Requirements Document Management
- Standardized requirements document template
- Automatic completeness validation
- Requirements status management (draft → approved)

### 📊 Code Change Records
- Per-feature file storage
- Bidirectional index (by_feature / by_file)
- Git Commit information association support

### 📜 Operation Log Audit
- Detailed operation records (who, when, what)
- Multi-dimensional filtering (operator, type, feature)
- Complete audit trail

### 🔀 Git Integration
- Automatic Commit information retrieval
- Branch naming convention detection
- Feature-Commit auto-association

### 🔧 Code Syntax Checking
- Multi-language support (Python, JavaScript, Go)
- Quick terminal check commands
- Auto language detector matching

### 📁 Multi-Project Management
- Project isolation, independent data
- Quick project context switching
- Project-level configuration support

---

## Requirements

| Dependency | Version | Description |
|------------|---------|-------------|
| Python | ≥ 3.8 | Core runtime |
| Git | ≥ 2.0 | Version control integration (optional) |

**Optional dependencies (code checking):**
- Node.js ≥ 14 (JavaScript checking)
- Go ≥ 1.16 (Go checking)

---

## Installation

```bash
# Clone repository
git clone https://github.com/your-username/long-run-agent.git
cd long-run-agent

# Add to PATH (optional)
ln -s $(pwd)/lra /usr/local/bin/lra

# Or use full path directly
./lra version
```

---

## Quick Start

### 1. Initialize Project

```bash
# Enter your project directory
cd /path/to/your/project

# Initialize LRA
lra project create my-project
```

This creates a `.long-run-agent/` directory:

```
.long-run-agent/
├── config.json              # Project config + version info
├── feature_list.json        # Feature list
├── progress.log             # Operation log
├── operation_log.json       # Audit log
├── records/                 # Code change records
│   └── index.json
├── specs/                   # Requirements docs
└── backup/                  # Upgrade backups
```

### 2. Create Feature

```bash
# Create new Feature
lra feature create "User Login" --category backend --priority P0 --assignee dev_001

# List all features
lra feature list
```

### 3. Manage Requirements

```bash
# Create requirements doc (using standard template)
lra spec create feature_001

# Validate requirements completeness
lra spec validate feature_001

# List all requirements
lra spec list
```

### 4. Status Transitions

```bash
# Check current status
lra feature status feature_001

# Update status
lra feature status feature_001 --set in_progress
lra feature status feature_001 --set pending_test
lra feature status feature_001 --set completed
```

### 5. Record Code Changes

```bash
# Associate Git Commit with Feature
lra git --feature feature_001

# Query code changes by Feature
lra records --feature feature_001

# Query associated Features by file path
lra records --file src/auth/login.py --format detail
```

### 6. Code Checking

```bash
# Check single file
lra code check src/main.py

# Check entire directory
lra code check src/ --verbose

# JavaScript check
lra code check src/index.js

# Go check
lra code check cmd/server/main.go
```

### 7. View Statistics

```bash
# Project statistics
lra stats

# Operation logs
lra logs --limit 20
lra logs --action status_change --feature feature_001
```

---

## CLI Reference

### Global Commands

```bash
lra version              # Show version info
lra upgrade              # Execute upgrade
lra rollback             # Rollback to latest backup
lra stats                # Show project statistics
lra statuses             # List all available statuses
```

### Feature Management

```bash
lra feature create <title> [--category CAT] [--priority P0|P1|P2] [--assignee NAME]
lra feature list
lra feature status <feature_id> [--set <status>]
```

### Requirements Management

```bash
lra spec create <feature_id>
lra spec validate <feature_id>
lra spec list
```

### Code Change Records

```bash
lra records --feature <feature_id> [--format brief|detail]
lra records --file <file_path> [--format brief|detail]
```

### Project Management

```bash
lra project create <name>
lra project switch <name>
lra project list
```

### Operation Logs

```bash
lra logs [--action ACTION] [--operator NAME] [--feature ID] [--limit N]
```

### Code Checking

```bash
lra code check <path> [--verbose]
```

### Git Integration

```bash
lra git --feature <feature_id>
```

---

## Best Practices

1. **Test-Driven Development** - Implement → Test → Fix if failed → Retest → Pass → Next feature
2. **Evidence First** - Don't claim completion without test evidence
3. **One Feature Per Branch** - Develop each feature in separate Git branch
4. **Keep Status Updated** - Update Feature status timely for visibility
5. **Requirements First** - Ensure requirements document passes validation before development

---

## Contributing

Contributions are welcome!

1. Fork this repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Create Pull Request

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for AI Agent Developers**

</div>
