# Changelog

All notable changes to this project will be documented in this file.

## [3.4.1] - 2026-03-02

### Added

- **Smart Start Command** - `lra start` 智能启动
  - 自动检测项目状态并引导
  - 支持 5 种场景：全新项目/部分初始化/需要恢复/有待执行任务/正常运营
  - `--auto` 模式：全自动处理，无需交互
  - `--task` 参数：直接创建第一个任务
  - `--name` 参数：指定项目名称

- **Recovery Command** - `lra recover` 数据恢复
  - 从 `tasks/` 目录扫描任务文件
  - 重建 `task_list.json` 索引
  - 提取任务描述和模板信息
  - 使用文件时间戳作为元数据

- **Enhanced List Output** - `lra list` 增强
  - 自动显示下一步建议
  - pending 任务：→ lra claim
  - in_progress 任务：→ lra set completed 或心跳提醒
  - 超时检测：>45 分钟自动提醒 heartbeat

- **Enhanced Show Output** - `lra show` 增强
  - 显示可用状态流转 `available_transitions`
  - 显示推荐命令 `_next_commands`
  - Agent 友好的结构化输出

- **Project State Detection** - 项目状态检测
  - `TaskManager.detect_project_state()` 新方法
  - 检测 8 种项目状态
  - 为智能引导提供决策依据

### Changed

- `_check_project()` 添加智能检测
  - 检测到任务文件但索引损坏时，提示 `lra recover`
  - 友好的错误提示和解决建议

- `lra guide` 更新
  - 添加 `lra start` 快速开始指南
  - 新增"容错功能"章节
  - 新增"增强功能"说明

- Version bump: 3.4.0 → 3.4.1

### Fixed

- `lra start` 在部分初始化项目中的处理逻辑
- 状态检测边界条件处理

### Documentation

- CHANGELOG.md 更新（本文件）
- `lra --help` 和 `lra guide` 输出更新
- 命令帮助文档自动同步

### Technical

- 新增代码：~565 行
  - `cli.py`: +305 行
  - `task_manager.py`: +260 行
- Token 开销：~8,500 tokens
- 遵循"永不崩溃"原则，所有异常都已捕获

### Usage Examples

```bash
# 智能启动（推荐）
lra start

# 全自动模式
lra start --auto

# 创建第一个任务
lra start --task "实现用户登录"

# 恢复损坏的索引
lra recover

# 查看下一步建议
lra list
lra show task_001
```

## [3.4.0] - 2026-03-02

### Added

- **Project Analyzer** - 多语言项目代码分析器
  - 支持 Python、JavaScript/TypeScript、Go
  - 分析模块结构、类/函数、依赖关系
  - 生成文档覆盖率报告
  - 输出 Mermaid 依赖关系图

- **Agent 快速索引**
  - `index.json` - O(1) 查找类/函数位置
  - 相对路径，便于移植

- **新命令**
  - `lra analyze-project` - 分析整个项目，生成文档和索引
  - `lra analyze-module <name>` - 分析指定模块
  - `lra where` - 显示所有关键文件位置
  - `lra index` - 输出 Agent 索引路径或内容

- **方法签名提取** - 显示 `add(a: int, b: int) -> int`

- **模块 docstring 提取** - 从 `__init__.py` 读取模块概述

### Changed

- `lra init --template` 默认值改为 `task`，不再必填
- `lra --help` 输出优化，添加 Agent 快速开始指引
- `lra init` 输出优化，提示执行 `analyze-project`
- `lra analyze-project` 输出优化，显示文档位置和 Agent 使用方式

### Fixed

- `analyze-module` 命令从简单搜索重构为真正的代码分析

### Documentation

- README.md 更新项目分析器说明
- 添加 Agent 索引使用示例

## [3.3.0] - 2026-02-25

### Added

- System check and preflight
- `lra system-check` command
- `lra analyze-module` command (basic implementation)
- Template-based status transitions
- Batch lock management

### Changed

- Improved task creation with auto system check
- Better error messages

## [3.2.0] - 2026-02-20

### Added

- Batch operations support
- Priority management (P0-P3)
- Dependency checking
- Record management for feature tracking

## [3.1.0] - 2026-02-15

### Added

- Initial release
- Task management with templates
- Lock mechanism for multi-agent coordination
- Context command for agent workflow
- Heartbeat and checkpoint support