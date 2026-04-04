# Changelog

All notable changes to this project will be documented in this file.

## [5.0.1] - 2026-04-02

### 🔄 重构

- **CLI 命令精简**：合并 `batch-lock` 到 `batch lock`，合并 `analyze-module/analyze-project` 到 `analyze {module|project}`，合并 `quality-check/regression-test/browser-test` 到 `test {quality|regression|browser}`，简化 `record` 命令（移除 timeline/analyze），`index` 并入 `where --index`。命令总数从 35+ 减少到 ~25。

### ✨ 新增功能

- **lra new 变量支持**：新增 `requirements`、`acceptance`、`design` 等字段支持，子任务名称更有意义
- **统一解析器模块**：`lra/parsers.py` 提供统一的输入解析
- **错误目录**：`lra/errors.py` 提供错误目录和操作建议
- **统一状态转换**：使用统一的状态转换和可操作错误信息
- **分解建议**：`lra decompose <id>` 分析任务并建议如何拆分
- **自动拆分**：`lra split <id> --auto` 使用上一次 decompose 的建议自动拆分

### 🐛 Bug 修复

- 设置 `check_level=basic` 作为默认值，修复代码模式检测
- 移除 `--context-hint` 的误导性弃用警告
- 修复 `browser-test` 命令示例（添加缺失的 task_id 参数）
- 移除未使用的 `format_error_display` 导入

### 📚 文档更新

- 文档更新报告
- FOR_NEW_AGENT 更新
- 添加 constitution 和 quality check 文档

### 🔧 代码质量

- ruff lint 错误修复

## [5.0.0] - 2026-03-10

### 🎉 重大版本发布

- **Constitution 机制**：规范驱动开发 + 质量宪法 + 不可协商原则
- **质量保障系统**：验证机制 + 回归测试 + 浏览器测试 + 代码质量检查
- **Ralph Loop 迭代引导**：7 阶段渐进式优化 + 智能引导 + 安全检查
- **跨平台支持**：Windows / Linux / macOS 全平台兼容
- **进度可视化**：`lra status` 项目进度可视化
- **上下文重建**：`lra orientation` Agent 上下文重建协议

## [4.1.0] - 2026-03-05

### ✨ 新增功能

#### 迭代阶段引导机制

- **7阶段渐进式优化**：每个任务最多7次迭代，每次迭代有明确的目标和引导
  - 支持5种模板：code-module, novel-chapter, data-pipeline, doc-update, task
  - 每个阶段有明确的重点、优先检查项、忽略项和详细建议
  
- **提前完成机制**：所有必需检查通过即可提前退出（不必走完7次迭代）

- **阶段卡住检测**：同一阶段失败3次后提示强制进入下一阶段
  - 新增命令：`lra set <task_id> force_next_stage`

- **重构安全检查**：代码重构阶段提供测试覆盖率检查等安全提示

- **迭代进度可视化**：`lra show` 命令新增迭代进度条和阶段引导框

#### 模板配置扩展

- 所有模板新增 `ralph.iteration_stages` 字段
- 每个阶段包含：name, focus, priority_checks, ignore_checks, suggestion, safety_checks

#### TaskManager 扩展

新增方法：
- `get_iteration_stage()` - 获取当前迭代阶段配置
- `update_iteration_stage()` - 更新迭代阶段
- `get_stage_suggestion()` - 获取阶段建议文本
- `check_stage_stuck()` - 检查阶段卡住
- `can_complete_early()` - 检查是否可提前完成

#### TemplateManager 扩展

新增方法：
- `load_iteration_stages()` - 加载迭代阶段配置
- `_validate_stage()` - 验证阶段配置
- `_get_default_stages()` - 获取默认阶段
- `get_stage_by_iteration()` - 获取指定阶段

#### CLI 命令增强

- `lra show <id>` - 新增迭代进度条和阶段引导框显示
- `lra set <id> completed` - 新增提前完成检测和阶段卡住检测
- `lra set <id> force_next_stage` - 新增强制进入下一阶段命令

### 📚 文档更新

- 更新 README.md 添加迭代阶段引导说明
- 新增 ITERATION_GUIDANCE_FINAL_REPORT.md（详细实施报告）
- 新增 ITERATION_GUIDANCE_QUICK_START.md（快速使用指南）

### 🐛 Bug 修复

- 修复了 Ralph Loop 控制器不符合"无状态 CLI 工具"设计理念的问题
- 删除了不必要的全局状态管理（ralph_loop.py, ralph_config.py, memory/）

### 🔄 变更

- Ralph Loop 机制从"项目级循环"改为"任务级循环"
- 状态管理从全局改为仅存储在 task_list.json 的任务对象中
- 优化次数固定为7次

## [4.0.0] - 2026-03-03

### Added

- **Ralph Loop 机制** - 任务级循环优化
  - 任务完成后自动质量检查
  - 最多7次优化迭代
  - 支持提前完成
  - 错误处理和回滚机制

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