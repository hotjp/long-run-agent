# Changelog

All notable changes to this project will be documented in this file.

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