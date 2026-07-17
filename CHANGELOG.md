# Changelog

All notable changes to this project will be documented in this file.

## [5.3.0] - 2026-07-17

### ♻️ 任务生命周期：跳过 / 取消 / 召回（新功能）

此前任务状态机只有一个正向终态（completed→optimizing→truly_completed），无法表达"暂时不做"、"作废"这类横向退出。本版新增两种与正向状态机正交的生命周期状态及专用命令：

- **`lra skip <id> [--reason]`**：跳过——暂时不做，移出 `lra ready`，但可召回。依赖它的任务**继续等待**（不解锁）。
- **`lra cancel <id> [--reason]`**：取消——作废（创建错误/与目标无关），移出 `lra ready`，依赖它的任务**被解锁**（视为依赖已了结）。
- **`lra recall <id>`**：召回——把 `skipped`/`cancelled` 任务恢复到初始状态，重新进入正常流程；依赖关系由 `ready` 动态重算。

实现要点：

- 把 `get_ready_tasks` / `_check_dependencies_satisfied` 原本混用的 `completed_statuses` 拆成三个语义集合：`done_statuses`（正向终态）、`hidden_from_ready`（+skipped/cancelled，自身移出 ready）、`dep_satisfied`（+cancelled，作依赖算满足）。"取消解锁下游、跳过不解锁"由此自然成立。
- `cancelled` 因可召回而非硬终态，故 `cancel` 时**显式**调用 `_unblock_dependents` 触发解锁，而非依赖终态判定。
- skip/cancel 写入 `lifecycle` 元数据（action/reason/at/previous_status），`lra list` 带原因展示，供审计。

### 🐛 Agent 提示自相矛盾修复

修复一套让工作 agent 产生困扰的指令矛盾（实测中 agent 为此消耗大量推理）：

- **claim 死结**：`lra claim` 要求任务 `.md` 的需求/验收/交付物字段已填，但角色模板却写"❌ 不要编辑 task 文件"——而 `lra` 又没有填字段的命令，agent 无路可走。现把过宽规则改为"状态用 `lra set` 改；内容字段（需求/验收/交付物/证据）可以且应当编辑"，三处指令文档（agent_prompt / lra-full / lra-minimal）统一。
- **claim 失败提示**：补充歧义消除说明（"这些是内容字段，编辑允许；只有状态才用 lra set"），并修复畸形的文件路径（`f".{metadata_dir}/..."` 拼出 `./Users/...`）→ 用 `os.path.join` 生成干净的相对路径。

### ✅ 验证

- 新增 `tests/test_skip_cancel.py`（12 个测试：ready 隐藏、cancel 解锁下游、skip 不解锁、recall 恢复与动态重阻塞、非法转换、lifecycle 元数据、CLI 端到端）。
- 全量 **93 测试通过**（原 81 + 新 12）。
- 端到端冒烟：skip/cancel/recall 经 CLI 验证；依赖阻塞经改动的 `get_ready_tasks` 回归确认正常。

---

## [5.2.2] - 2026-07-02

### 🐛 Windows 兼容性（续 5.2.1）

5.2.1 之后的补充修复，让 Windows 支持真正完整（由新增的 `windows-latest` CI 揭示）：

- **subprocess 输出解码**：全部 15 处 `subprocess.run(..., text=True)` 加 `encoding="utf-8", errors="replace"`。此前 Windows 用 cp1252/charmap 解码子进程 stdout，遇到中文（git 中文 commit、pytest 中文输出、`lra` 自身输出）即 `UnicodeDecodeError` 且 stdout 变 None。
  - 涉及：`config.py`、`cli_extensions.py`、`constitution.py`、`quality_checker.py`、`task_manager.py`、`relay/git_utils.py`、`relay/claude_adapter.py`

### 🧪 测试基础设施（Windows）

- **tempdir 清理崩溃**（WinError 32）：3 个集成测试 `chdir` 进 `TemporaryDirectory` 不还原，Windows 无法删除进程当前目录。新增 `tests/conftest.py` 的 `chdir_to()` 上下文管理器。
- **CLI 测试输出解码**：测试用 `subprocess(text=True)` 解码 `lra` 中文输出失败，改用 UTF-8 + 诊断断言。

### 🎨 代码质量

- 应用 ruff 安全自动修复（156 处：import 排序、冗余 f-string、未用 import、冗余 open 模式等）
- CI 中 ruff 步骤设为 advisory（剩余 112 处既有 lint 债：行长、裸 except 等，后续清理）

### ✅ 验证

- Windows CI 全绿：`windows-latest` × Python 3.10/3.11/3.12，81 测试全过
- `ubuntu-latest` 同样全绿

---

## [5.2.1] - 2026-07-02

### 🐛 Windows 兼容性修复

修复在 Windows 上运行 LRA 的多个问题（此前在 Windows 上无法正常使用）：

- **relay 导入即崩**：`relay/orchestrator.py` 顶层 `import fcntl`（POSIX-only）改用跨平台 `filelock` 库
- **claude CLI 启动失败**：`claude_adapter.py` 用 `shutil.which` 解析二进制，让 Windows 找到 `claude.cmd`（npm 安装为 `.cmd`，`CreateProcess` 无法直接执行）
- **中文/emoji 崩溃**：约 12 处文本 I/O 显式指定 `encoding="utf-8"`（Windows 默认 cp1252/gbk）
- **非原子改名**：`SafeJson.write` 用 `os.replace` 替代 `shutil.move`（后者在 Windows 覆盖已存在文件时退化为 copy+delete）
- **打包缺失**：`pyproject.toml` 补全 `lra.relay` 子包（此前 `pip install` 不安装 relay）
- **工具调用稳健**：pytest/ruff 改用 `sys.executable -m` 调用，避免依赖 PATH 里的 `.bat`/`.cmd`
- **终端显示**：`main()` 在 Windows 重配置 stdout/stderr 为 UTF-8，让 emoji/中文在老 conhost 正常显示

### 🧪 测试修复

- `Config.get_metadata_dir` 支持 `LRA_CONFIG_DIR` 环境变量（测试隔离 + 自定义元数据目录）
- 新增 `tests/conftest.py` cwd 隔离 fixture，消除测试间状态污染（此前整体跑有 43 errors）
- 修复 3 个 `test_constitution` 失败

### 🔧 CI

- 新增多 OS 测试矩阵：`ubuntu-latest` + `windows-latest`，Python 3.10/3.11/3.12，跑 `ruff check` + `pytest`

---

## [5.2.0] - 2026-04-28

### 🎉 重大功能：LRA Relay — 全自主 Agent 中继

新增 `lra relay` 命令，实现完全自主的 Agent 任务执行循环：

#### 核心组件 (`lra/relay/`)

| 组件 | 功能 |
|------|------|
| `orchestrator.py` | 主循环，Git 分支隔离 + 失败回滚 |
| `agent_runner.py` | Ralph Loop 7 阶段迭代执行器 |
| `claude_adapter.py` | Claude CLI 子进程管理，JSONL 输出，15s 宽限期 |
| `git_utils.py` | 安全 Git 操作（subprocess.run list 参数，无 shell） |
| `task_queue.py` | mtime 缓存任务队列，基于 `TaskManager.get_ready_tasks()` |
| `structured_output.py` | JSON Schema 生成 + Python 验证 |
| `backoff.py` | 指数退避，硬错误/软错误分离 |
| `notes_store.py` | 追加写 JSONL 内存存储 |

#### CLI 接口

```bash
lra relay --dry-run      # 预览任务，不执行
lra relay --max-steps N  # 最多执行 N 个任务
lra relay                # 全自主执行
```

#### Constitution 变革

- `get_default_iteration_gates()` 现在返回 `{}`（无硬编码语言工具）
- Agent 完全自主 — 自动检测项目类型并选择工具
- 框架仅在 Agent 报告后验证 Constitution gates

### 🔄 重构

- **Relay 简化**：移除 relay 分支，改为 per-stage commits + 文件锁
- **Agent Prompt 重写**：改为 Ralph Loop 操作规程

### 📚 文档更新

- README 和 index.html 更新适配 Relay v5.1

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