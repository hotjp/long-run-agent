# LRA Agent Relay 设计文档

## 背景

LRA (Long-Running Agent) 目前在 task 拆分、Constitution 质量门禁、层次锁协调上有成熟能力，但 task 执行完成后依赖人工介入切换 agent — 需要人工执行 `lra ready` 查看可执行任务、`lra claim <id>` 认领任务、`lra set <id> completed` 完成流转。

gnhf（good night, have fun）提供了一个纯 CLI 的 agent 循环运行框架，其核心设计值得借鉴：

- 每次迭代是独立 git commit，失败自动 `git reset --hard`
- 结构化输出契约：agent 必须返回 `{success, summary, key_changes, key_learnings}`
- 指数退避：硬错误 exponentially backoff，软错误立即继续
- 文件系统记忆：agent 主动读 `notes.md`，不污染 LLM 上下文
- 3 次连续失败 abort

本文档设计如何在 LRA 中实现**全自动 agent 接力**，让 task 链可以无人值守运行。

---

## 目标

1. task 按拓扑顺序自动推进，无需人工介入
2. agent 输出必须符合 Constitution 契约
3. 失败自动回滚，不污染后续迭代
4. 完整的调试日志和迭代历史
5. **与现有手动模式（`lra ready / claim / set`）完全共存，不破坏已有工作流**

---

## 三大优势策略

### 1. Agent 驱动链策略：深度复用现有基础设施，不做重复建设

**核心原则**：Relay 不是另起炉灶，而是自动化执行现有手动工作流。

| 现有手动流程 | Relay 自动化映射 |
|-------------|-----------------|
| `lra ready` 发现可执行任务 | `TaskQueue.get_next_task()` → 复用 `TaskManager.get_ready_tasks()` |
| `lra claim <id>` 获取锁 | `LocksManager.claim(task_id)` → 自动 claim，自动生成 session_id |
| `lra heartbeat <id>` 保活 | `AgentRunner` 后台线程每 4 分钟自动 heartbeat |
| `lra checkpoint <id>` 保存进度 | 每次迭代前自动 `git stash push -m "relay-{task_id}-{attempt}"` |
| `lra set <id> completed` | `TaskManager.update_status(task_id, "completed")` → 自动触发 Constitution 验证 |
| 父子任务层次锁 | 完全复用 `LocksManager` 的 `LOCKED_BY_PARENT` / `publish_children` 机制 |
| Ralph Loop 质量迭代 | 复用 task["ralph"] 子状态，而非新建计数器 |

**Agent 固定为 Claude**：不实现多 agent 类型切换，所有 task 统一调用 Claude。

**与现有手动模式的关系澄清**：
> 代码库中**不存在** `lra next` 命令。现有手动模式的核心是 `lra ready` + `lra claim`。Relay 模式是这套手动流程的全自动封装，两者底层共享同一套 `TaskManager`、`LocksManager`、`ConstitutionManager`。

### 2. 性能策略：最小化 I/O、缓存拓扑、批量更新

| 优化点 | 策略 | 实现 |
|--------|------|------|
| **拓扑排序缓存** | 懒加载 + 状态变化失效 | `TaskQueue` 在首次调用时复用 `get_ready_tasks()`，仅在检测到 `task_list.json` mtime 变化时重新加载 |
| **减少文件写次数** | 批量状态更新 | orchestrator 统一写 `task_list.json` 和 `locks.json`，不在 runner 内部频繁写盘 |
| **Constitution 预编译** | 初始化时构建 schema | `StructuredOutputVerifier` 在 `__init__` 时解析 schema，避免每次验证都重新构建 |
| **notes.md 分页读取** | 只读最近 N 次迭代 | `NotesStore` 维护内存索引，避免每次读取都解析整个文件 |
| **避免重复 git 操作** | 迭代内不提交 | 每次 task 的多次 retry 不生成 git commit，只在最终 success 时 `git commit` |

### 3. 安全性策略：防御性回滚、进程保活、锁安全

| 风险场景 | 防御策略 | 实现 |
|---------|---------|------|
| **git reset --hard 销毁用户数据** | 分支隔离 | 每次 relay 在独立 `relay/{timestamp}` 分支运行，失败时 `git reset --hard` 只影响 relay 分支，不影响原分支 |
| **命令注入** | 无 shell 执行 | `git_utils.py` 所有 git 命令通过 `subprocess.run(["git", ...], cwd=...)` 执行，参数以列表传入，永不拼接 shell 字符串 |
| **并发读写 task_list.json** | 文件锁保护 | 所有写操作通过 `Config.FileLock` 包裹 |
| **agent 进程崩溃导致锁泄漏** | 心跳 + orphan 自动回收 | `AgentRunner` 启动后台线程每 4 分钟 heartbeat；若进程崩溃，15 分钟后 `LocksManager` 自动标记为 ORPHANED，可被后续 relay 实例 reclaim |
| **无限循环重试** | 硬上限 + 指数退避 | 单 task 最多 3 次连续失败 abort；硬错误指数退避，上限 15 分钟 |
| **JSON 解析失败** | Claude CLI 强制 schema + Python 兜底 | `ClaudeAdapter` 通过 `--json-schema` 参数让 Claude 客户端保证输出格式；Python 侧只做 `json.loads()` 兜底校验 |
| **relay 中途被 kill** | atexit 清理 | `orchestrator` 注册 `atexit` 处理器，确保退出时关闭 agent 进程 |
| **脏工作区启动** | 前置检查 | `orchestrator.run()` 开头调用 `ensure_clean_working_tree()`，发现未提交更改立即报错退出 |

---

## 架构设计

### 整体流程

```
┌─────────────────────────────────────────────────────────────┐
│                      LRA Relay Orchestrator                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌───────────┐   ┌──────────────────────┐   │
│  │TaskQueue │──►│ AgentRunner│──►│ ConstitutionVerifier │   │
│  │(ready   )│   │(claim    )│   │(schema + quality    )│   │
│  │(topo    )│   │(heartbeat)│   │                      │   │
│  └────┬─────┘   └─────┬─────┘   └──────────┬───────────┘   │
│       │               │                    │                 │
│       ▼               ▼                    ▼                 │
│  get_ready_tasks() run_agent()      verify()                 │
│                    │                    │                     │
│                    │         ┌─────────┴───────────┐          │
│                    │         │  pass → commit+next │          │
│                    │         │  fail → stash+reset+retry     │
│                    │         └─────────────────────┘          │
│                    ▼                                          │
│              notes_store.py  ←──  agent 主动读取               │
│                    │                                          │
│              iteration.log  ←── JSONL 调试日志                 │
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
│  │LocksManager │   │TaskManager  │   │GitUtils         │    │
│  │(claim      )│   │(update_status│   │(safe git cmds  │    │
│  │(heartbeat  )│   │(get_ready   )│   │(branch isolate│    │
│  │(release    )│   │(check_blocked│   │(clean check   │    │
│  └─────────────┘   └─────────────┘   └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 新增模块

```
lra/
├── relay/
│   ├── __init__.py
│   ├── orchestrator.py      # 主循环：选 task → claim → 跑 agent → 验证 → 推进
│   ├── task_queue.py        # 任务队列：基于 get_ready_tasks() 的拓扑缓存层
│   ├── agent_runner.py      # agent 生命周期管理（含心跳、checkpoint）
│   ├── claude_adapter.py    # Claude CLI 子进程管理（spawn / JSONL parse / abort / shutdown）
│   ├── notes_store.py       # 文件系统记忆（append-only）
│   ├── backoff.py           # 指数退避策略（硬/软错误分离）
│   ├── structured_output.py # 输出 schema 定义 + Python 侧兜底验证
│   ├── iteration_log.py     # JSONL 调试日志
│   └── git_utils.py         # 安全的 git 操作封装（无 shell + clean check + 分支管理）
```

---

## 核心模块设计

### 1. notes_store.py

**设计原则**: append-only，agent 主动读文件，不注入 LLM 上下文。

```python
# notes_store.py
from pathlib import Path

class NotesStore:
    def __init__(self, run_dir: Path):
        self.path = run_dir / "notes.md"
        self._cache: dict[str, list[dict]] = {}  # task_id -> entries 的内存索引

    def append(
        self,
        task_id: str,
        attempt: int,
        summary: str,
        changes: list[str],
        learnings: list[str],
    ):
        entry = f"""
### Task {task_id} — Attempt {attempt}

**Summary:** {summary}

**Changes:**
{chr(10).join(f"- {c}" for c in changes)}

**Learnings:**
{chr(10).join(f"- {l}" for l in learnings)}
"""
        if self.path.exists():
            self.path.write_text(self.path.read_text() + entry)
        else:
            self.path.write_text(entry)
        
        # 更新内存索引，避免每次读取都解析文件
        self._cache.setdefault(task_id, []).append({
            "attempt": attempt,
            "summary": summary,
            "changes": changes,
            "learnings": learnings,
        })

    def read_task_context(self, task_id: str, max_entries: int = 5) -> str:
        """只读最近 N 次尝试，减少上下文膨胀"""
        entries = self._cache.get(task_id, [])
        if not entries:
            return ""
        recent = entries[-max_entries:]
        lines = [f"- {e['summary']}" for e in recent]
        return "\n".join(lines)
```

**关键**: agent 通过文件系统读历史，不走 LLM prompt。内存索引确保 `read_task_context` 是 O(1) 而非 O(n)。

---

### 2. structured_output.py

**设计原则**: Claude CLI 客户端通过 `--json-schema` 参数强制执行结构化输出；Python 侧只做兜底校验和字段类型检查。

```python
# structured_output.py
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AgentOutput:
    success: bool
    summary: str
    key_changes: list[str]
    key_learnings: list[str]
    should_fully_stop: bool = False

class OutputValidationError(Exception):
    pass

class StructuredOutputVerifier:
    """Python 侧兜底校验：验证 agent 输出是否满足 schema"""
    
    REQUIRED_SCHEMA = {
        "success": bool,
        "summary": str,
        "key_changes": list,
        "key_learnings": list,
    }
    
    def verify(self, raw_output: str) -> AgentOutput:
        """解析 agent 原始输出，验证是否满足 schema
        
        Claude CLI 已通过 --json-schema 强制输出格式，此处只做轻量兜底校验。
        """
        data = json.loads(raw_output)
        return AgentOutput(**data)
    @staticmethod
    def build_json_schema(include_stop_field: bool = False) -> dict:
        """生成供 Claude CLI --json-schema 使用的 schema"""
        properties = {
            "success": {"type": "boolean"},
            "summary": {"type": "string"},
            "key_changes": {"type": "array", "items": {"type": "string"}},
            "key_learnings": {"type": "array", "items": {"type": "string"}},
        }
        required = ["success", "summary", "key_changes", "key_learnings"]
        if include_stop_field:
            properties["should_fully_stop"] = {"type": "boolean"}
            required.append("should_fully_stop")
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": required,
        }

    @staticmethod
    def write_schema_file(path: Path, include_stop_field: bool = False):
        """将 schema 写入文件，供 Claude CLI 读取"""
        schema = StructuredOutputVerifier.build_json_schema(include_stop_field)
        path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
```

**与现有 Constitution 的关系**:
- `structured_output.py` 验证 agent 是否"说人话"（JSON schema 正确）
- 现有的 `ConstitutionManager` / `PrincipleValidator` 验证代码是否"做对事"（测试通过、交付物存在、字段完整）
- 两者是**串联关系**：schema 验证失败 → 立即重试；schema 通过 → 执行 Constitution 质量门禁 → 门禁失败 → rollback

**与 gnhf 的差异**: gnhf 的 schema 文件由 `run.py` 在启动时写入；Relay 的 schema 文件在 `ClaudeAdapter.__init__` 时写入 run 目录，始终跟随任务生命周期。

---

### 3. backoff.py

**设计原则**: 区分硬错误（agent 崩溃/超时/JSON 解析失败）和软错误（agent 报告 success=false）。

```python
# backoff.py

class ExponentialBackoff:
    def __init__(
        self,
        base_ms: float = 60_000,  # 60 秒
        max_errors: int = 3,
        max_backoff_ms: float = 900_000,  # 15 分钟上限
    ):
        self.base_ms = base_ms
        self.max_errors = max_errors
        self.max_backoff_ms = max_backoff_ms
        self.consecutive_errors = 0
        self.consecutive_failures = 0

    def record_error(self):
        """硬错误：agent 崩溃/异常/JSON 解析失败"""
        self.consecutive_errors += 1
        self.consecutive_failures = 0

    def record_failure(self):
        """软错误：agent 报告 success=false"""
        self.consecutive_failures += 1
        self.consecutive_errors = 0

    def record_success(self):
        self.consecutive_errors = 0
        self.consecutive_failures = 0

    @property
    def should_abort(self) -> bool:
        return self.consecutive_failures >= self.max_errors

    @property
    def backoff_duration_ms(self) -> float:
        """硬错误的退避时间，有上限"""
        if self.consecutive_errors == 0:
            return 0
        return min(self.base_ms * (2 ** (self.consecutive_errors - 1)), self.max_backoff_ms)

    @property
    def should_wait_before_retry(self) -> bool:
        return self.consecutive_errors > 0
```

---

### 4. task_queue.py

**设计原则**: 基于现有 `TaskManager.get_ready_tasks()` 的轻量缓存层，不重新发明依赖检查逻辑。

```python
# task_queue.py
import os
from lra.task_manager import TaskManager
from lra.locks_manager import LocksManager
from lra.config import Config

class TaskQueue:
    def __init__(self, task_manager: TaskManager, locks_manager: LocksManager):
        self.tm = task_manager
        self.lm = locks_manager
        self._cache_mtime: float = 0
        self._cached_ready_tasks: list[dict] = []

    def get_next_task(self) -> dict | None:
        """返回优先级最高的可执行任务"""
        ready = self._get_ready_tasks_cached()
        
        # 过滤掉已被 claim 的（手动或另一个 relay 实例）
        available = []
        for task in ready:
            task_id = task["id"]
            can_claim, _ = self.lm.can_claim(task_id)
            if can_claim:
                available.append(task)
        
        if not available:
            return None
        
        # 按优先级排序（P0 > P1 > P2 > P3）
        priority_weights = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        available.sort(key=lambda t: priority_weights.get(t.get("priority", "P3"), 3))
        return available[0]

    def _get_ready_tasks_cached(self) -> list[dict]:
        """缓存 ready tasks，避免每次调用都读盘"""
        task_list_path = Config.get_task_list_path()
        try:
            mtime = os.path.getmtime(task_list_path)
        except OSError:
            mtime = 0
        
        if mtime > self._cache_mtime:
            self._cached_ready_tasks = self.tm.get_ready_tasks(
                locks_manager=self.lm,
                sort="priority",
            )
            self._cache_mtime = mtime
        
        return self._cached_ready_tasks

    def invalidate_cache(self):
        """任务状态变化后调用，强制下次重新加载"""
        self._cache_mtime = 0
```

**关键**: 不自己实现拓扑排序和依赖检查，完全复用 `TaskManager.get_ready_tasks()`（它内部已经做了依赖检查、父任务检查、锁检查）。缓存层只解决性能问题。

---

### 5. claude_adapter.py

**设计原则**: 通过 `spawn` 启动 Claude CLI 子进程，利用 `--json-schema` 参数让 Claude 客户端强制执行结构化输出；stdout 按 JSONL 解析；支持 `AbortSignal` 中断；15s graceful shutdown。

```python
# claude_adapter.py
import json
import subprocess
import signal
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

@dataclass
class AgentResult:
    output: dict
    usage: TokenUsage

class ClaudeAdapter:
    """Claude CLI 子进程管理器
    
    参考 gnhf 的 ClaudeAgent 实现，核心设计：
    1. spawn 启动子进程（detached=True，独立进程组）
    2. stdout 按 JSONL stream 解析
    3. stderr 收集用于错误诊断
    4. 支持 abort_signal 中断（SIGTERM 进程组）
    5. 收到最终结果后 15s graceful shutdown
    6. Windows / Unix 差异处理
    """
    
    FINAL_RESULT_GRACE_MS = 15_000
    
    def __init__(
        self,
        bin_path: str = "claude",
        schema_path: Path | None = None,
        extra_args: list[str] | None = None,
    ):
        self.bin = bin_path
        self.schema_path = schema_path
        self.extra_args = extra_args or []
        self._child: subprocess.Popen | None = None
        self._aborted = False

    def _build_args(self, prompt: str) -> list[str]:
        """构建 Claude CLI 参数"""
        args = [
            *self.extra_args,
            "-p", prompt,
            "--verbose",
            "--output-format", "stream-json",
        ]
        if self.schema_path and self.schema_path.exists():
            args.extend(["--json-schema", str(self.schema_path)])
        # 非交互模式下跳过权限确认（gnhf 默认行为）
        if not any(a in self.extra_args for a in [
            "--dangerously-skip-permissions",
            "--permission-mode",
        ]):
            args.append("--dangerously-skip-permissions")
        return args

    def run(
        self,
        prompt: str,
        cwd: Path,
        log_path: Path | None = None,
    ) -> AgentResult:
        """运行 Claude CLI，返回结构化输出"""
        args = self._build_args(prompt)
        
        # 启动子进程（Unix 下创建新进程组，方便整体 kill）
        self._child = subprocess.Popen(
            [self.bin, *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=(sys.platform != "win32"),
        )
        
        stdout_lines: list[str] = []
        stderr_text = ""
        result_event: dict | None = None
        final_structured_event: dict | None = None
        latest_usage: dict | None = None
        
        # 读取 stdout JSONL
        for line in self._child.stdout:
            line = line.strip()
            if not line:
                continue
            stdout_lines.append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if event.get("type") == "result":
                latest_usage = event.get("usage")
                if self._is_final_structured_result(event):
                    final_structured_event = event
                elif not final_structured_event:
                    result_event = event
        
        # 读取 stderr
        stderr_text = self._child.stderr.read() or ""
        
        # 等待子进程结束
        return_code = self._child.wait()
        self._child = None
        
        if return_code != 0:
            raise RuntimeError(f"claude exited with code {return_code}: {stderr_text}")
        
        # 确定最终事件
        terminal = final_structured_event or result_event
        if not terminal:
            raise RuntimeError("claude returned no result event")
        
        if terminal.get("is_error") or terminal.get("subtype") != "success":
            raise RuntimeError(f"claude reported error: {json.dumps(terminal)}")
        
        structured = terminal.get("structured_output")
        if not structured:
            raise RuntimeError("claude returned no structured_output")
        
        usage = self._to_token_usage(latest_usage or terminal.get("usage", {}))
        
        # 写日志
        if log_path:
            log_path.write_text("\n".join(stdout_lines), encoding="utf-8")
        
        return AgentResult(
            output=structured,
            usage=usage,
        )

    def _is_final_structured_result(self, event: dict) -> bool:
        return (
            not event.get("is_error")
            and event.get("subtype") == "success"
            and event.get("structured_output") is not None
        )

    def _to_token_usage(self, usage: dict) -> TokenUsage:
        return TokenUsage(
            input_tokens=usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        )

    def _terminate_child(self):
        """终止 Claude 子进程"""
        if not self._child or self._child.poll() is not None:
            return
        
        if sys.platform == "win32":
            # Windows: taskkill /T /F /PID
            try:
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(self._child.pid)],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
        else:
            # Unix: 先 SIGTERM 整个进程组
            try:
                os.killpg(os.getpgid(self._child.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                # 进程组不存在，直接 kill 子进程
                self._child.terminate()

    def shutdown(self):
        """优雅关闭：如果子进程还在运行，给 15s  grace period 后强制终止"""
        if not self._child or self._child.poll() is not None:
            return
        
        import threading
        timer = threading.Timer(self.FINAL_RESULT_GRACE_MS / 1000, self._terminate_child)
        timer.start()
        
        try:
            self._child.wait(timeout=self.FINAL_RESULT_GRACE_MS / 1000)
            timer.cancel()
        except subprocess.TimeoutExpired:
            pass  # timer 会触发 terminate

    def __del__(self):
        self.shutdown()
```

**关键设计（直接取自 gnhf 精华）**:
- `--json-schema` 参数：让 Claude CLI 客户端强制执行结构化输出，Python 侧只需 `json.loads()`
- `--output-format stream-json`：每行一个 JSON event，便于流式解析
- `detached=True`（`start_new_session`）：Unix 下创建独立进程组，方便 `killpg` 整体终止
- `stderr` 收集：Claude 崩溃时的诊断信息
- 15s grace period：收到成功结果后，给 Claude 清理进程的时间
- Windows / Unix 差异：`taskkill /T /F` vs `killpg(SIGTERM)`

---

### 6. agent_runner.py

**设计原则**: 单一 task 的执行单元，管理 agent 完整生命周期（claim → 心跳 → 运行 → 释放）。

```python
# agent_runner.py
import asyncio
import threading
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class IterationResult:
    success: bool
    summary: str
    key_changes: list[str]
    key_learnings: list[str]
    error: str | None = None
    schema_valid: bool = True  # False 表示 JSON 解析失败（硬错误）

class AgentRunner:
    def __init__(
        self,
        adapter: ClaudeAdapter,
        constitution_verifier: StructuredOutputVerifier,
        notes_store: NotesStore,
        backoff: ExponentialBackoff,
        locks_manager: LocksManager,
    ):
        self.adapter = adapter
        self.verifier = constitution_verifier
        self.notes = notes_store
        self.backoff = backoff
        self.lm = locks_manager
        self._heartbeat_thread: threading.Thread | None = None
        self._stop_heartbeat = threading.Event()

    async def run_task(
        self,
        task: dict,
        attempt: int,
        run_dir: Path,
    ) -> IterationResult:
        task_id = task["id"]
        
        # 1. Claim 任务（获取层次锁）
        claim_ok, claim_info = self.lm.claim(task_id)
        if not claim_ok:
            return IterationResult(
                success=False,
                summary="",
                key_changes=[],
                key_learnings=[],
                error=f"Failed to claim task: {claim_info}",
            )
        
        # 2. 启动心跳保活
        self._start_heartbeat(task_id)
        
        try:
            # 3. 构建 prompt
            prompt = self._build_prompt(task, attempt, run_dir)
            
            # 4. 运行 agent（固定调用 Claude，通过子进程 spawn）
            log_path = run_dir / f"attempt-{attempt}-{task_id}.jsonl"
            result = await asyncio.to_thread(
                self.adapter.run,
                prompt=prompt,
                cwd=run_dir,
                log_path=log_path,
            )
            
            # 5. Python 侧兜底校验（Claude 已经通过 --json-schema 保证格式，这里是二次确认）
            try:
                output = self.verifier.verify(json.dumps(result.output))
            except (json.JSONDecodeError, OutputValidationError) as e:
                self.backoff.record_error()
                return IterationResult(
                    success=False,
                    summary="",
                    key_changes=[],
                    key_learnings=[],
                    error=f"Schema validation failed: {e}",
                    schema_valid=False,
                )
            
            if not output.success:
                self.backoff.record_failure()
                return IterationResult(
                    success=False,
                    summary=output.summary,
                    key_changes=[],
                    key_learnings=output.key_learnings,
                )
            
            self.backoff.record_success()
            return IterationResult(
                success=True,
                summary=output.summary,
                key_changes=output.key_changes,
                key_learnings=output.key_learnings,
            )
        
        except Exception as e:
            self.backoff.record_error()
            return IterationResult(
                success=False,
                summary="",
                key_changes=[],
                key_learnings=[],
                error=f"Agent crashed: {type(e).__name__}: {e}",
            )
        
        finally:
            # 6. 停止心跳 + 优雅关闭 Claude 进程
            self._stop_heartbeat.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=5)
            self.adapter.shutdown()
            # 注意：不在此处释放锁，由 orchestrator 根据结果决定

    def _start_heartbeat(self, task_id: str):
        """后台线程每 4 分钟发送心跳"""
        def heartbeat_loop():
            while not self._stop_heartbeat.wait(timeout=240):  # 4 分钟
                try:
                    self.lm.heartbeat(task_id)
                except Exception:
                    pass
        
        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _build_prompt(self, task: dict, attempt: int, run_dir: Path) -> str:
        """prompt 只告诉 agent 文件路径，不注入历史"""
        task_file = task.get("task_file", f"tasks/{task['id']}.md")
        notes_path = run_dir / "notes.md"
        return f"""You are working on task: {task.get('description', task['id'])}

Task ID: {task['id']}
Priority: {task.get('priority', 'P1')}
Attempt: {attempt}

Read the full task at: .long-run-agent/{task_file}

After completing your work:
1. Output JSON: {{"success": bool, "summary": str, "key_changes": [], "key_learnings": []}}
2. Do NOT commit — that is handled automatically
3. If you determine the task is impossible to complete, set "success": false and explain in "summary"
"""
```

**关键变化**:
- `adapter` 类型固定为 `ClaudeAdapter`，通过 `asyncio.to_thread()` 在子线程运行阻塞的 `Popen`
- 增加了 `locks_manager.claim()` 调用，复用现有层次锁
- 增加了后台心跳线程，复用现有 orphan 检测机制
- `finally` 中调用 `adapter.shutdown()` 优雅关闭 Claude 进程
- 区分 `schema_valid=False`（硬错误）和 `success=False`（软错误）

---

### 7. git_utils.py

**设计原则**: 所有 git 命令通过 `subprocess.run(argv数组)` 执行，永不使用 shell 拼接；启动前检查 clean working tree；支持分支隔离。

```python
# git_utils.py
import subprocess
from pathlib import Path

class GitError(Exception):
    pass

class GitUtils:
    """安全的 git 操作封装
    
    直接取自 gnhf 的 git.ts 精华设计：
    1. 所有命令通过 subprocess.run(["git", ...]) 执行，无 shell
    2. 启动前 ensure_clean_working_tree() 防止数据丢失
    3. reset 时同时执行 clean -fd
    4. commit 时自动处理 "nothing to commit" 情况
    """
    
    @staticmethod
    def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
        """执行 git 命令，参数以列表传入，永不经过 shell"""
        try:
            return subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                check=check,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"git {' '.join(args)} failed: {e.stderr}")

    @staticmethod
    def ensure_clean_working_tree(cwd: Path) -> None:
        """确保工作区干净，防止 reset --hard 销毁未提交的更改"""
        result = GitUtils._git(["status", "--porcelain"], cwd, check=False)
        if result.stdout.strip():
            raise GitError(
                "Working tree is not clean. Commit or stash changes first.\n"
                f"Dirty files:\n{result.stdout}"
            )

    @staticmethod
    def get_head_commit(cwd: Path) -> str:
        result = GitUtils._git(["rev-parse", "HEAD"], cwd)
        return result.stdout.strip()

    @staticmethod
    def get_current_branch(cwd: Path) -> str:
        result = GitUtils._git(["symbolic-ref", "--short", "HEAD"], cwd, check=False)
        if result.returncode != 0:
            result = GitUtils._git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        return result.stdout.strip()

    @staticmethod
    def create_branch(branch_name: str, cwd: Path) -> None:
        GitUtils._git(["checkout", "-b", branch_name], cwd)

    @staticmethod
    def commit_all(message: str, cwd: Path) -> None:
        GitUtils._git(["add", "-A"], cwd)
        result = GitUtils._git(["commit", "-m", message], cwd, check=False)
        if result.returncode != 0 and "nothing to commit" not in result.stderr:
            raise GitError(f"git commit failed: {result.stderr}")

    @staticmethod
    def reset_hard(cwd: Path) -> None:
        """reset --hard + clean -fd，彻底回滚到 HEAD"""
        GitUtils._git(["reset", "--hard", "HEAD"], cwd)
        GitUtils._git(["clean", "-fd"], cwd, check=False)

```

**关键设计（直接取自 gnhf 精华）**:
- `subprocess.run(["git", ...])`：参数以列表传入，无 shell 解释，彻底避免命令注入
- `ensure_clean_working_tree()`：启动前检查 `git status --porcelain`，有未提交更改则立即报错
- `reset_hard()`：同时执行 `git clean -fd`，删除未跟踪文件（gnhf 的标准做法）
- `commit_all()`：捕获 "nothing to commit" 作为正常情况，不抛异常
- `ensure_run_metadata_ignored()`：将 run 目录加入 `.gitignore`，避免污染 tracked 文件

---

### 8. orchestrator.py

**设计原则**: 主循环，驱动整个 relay。使用 `try/finally` 确保资源清理，使用 FileLock 确保并发安全，启动前检查 clean working tree，每次 run 在独立分支。

```python
# orchestrator.py
import asyncio
import atexit
from pathlib import Path
from datetime import datetime
from lra.config import Config, FileLock

class RelayOrchestrator:
    def __init__(
        self,
        task_manager: TaskManager,
        locks_manager: LocksManager,
        adapter: ClaudeAdapter,
        constitution: ConstitutionManager,
        run_dir: Path,
        limits: RunLimits,
        branch_name: str,
    ):
        self.tm = task_manager
        self.lm = locks_manager
        self.queue = TaskQueue(task_manager, locks_manager)
        self.adapter = adapter
        self.constitution = constitution
        self.run_dir = run_dir
        self.limits = limits
        self.branch_name = branch_name
        self.notes = NotesStore(run_dir)
        self.backoff = ExponentialBackoff()
        self.verifier = StructuredOutputVerifier()
        self.git = GitUtils()
        
        self._global_step = 0
        self._current_task_id: str | None = None
        self._should_stop_flag = False
        # 注册退出清理
        atexit.register(self._emergency_cleanup)

    async def run(self):
        # 1. 启动前安全检查
        try:
            self.git.ensure_clean_working_tree(Path.cwd())
        except GitError as e:
            self._log_error(f"Git safety check failed: {e}")
            return
        
        # 2. 创建 relay 分支
        try:
            self.git.create_branch(self.branch_name, Path.cwd())
        except GitError:
            # 分支已存在，直接切换
            self.git._git(["checkout", self.branch_name], Path.cwd())
        
        try:
            while not self._should_stop():
                # 4. 检查是否需要 abort
                if self.backoff.should_abort:
                    self._log_error(f"Abort after {self.backoff.max_errors} consecutive failures")
                    break
                
                if self.backoff.should_wait_before_retry:
                    wait_ms = self.backoff.backoff_duration_ms
                    self._log_info(f"Backing off {wait_ms}ms before retry")
                    await asyncio.sleep(wait_ms / 1000)
                
                # 5. 获取下一个 task
                task = self.queue.get_next_task()
                if task is None:
                    self._log_info("No more tasks to run, exiting")
                    break
                
                self._current_task_id = task["id"]
                
                # 6. 运行 task
                runner = AgentRunner(
                    adapter=self.adapter,
                    constitution_verifier=self.verifier,
                    notes_store=self.notes,
                    backoff=self.backoff,
                    locks_manager=self.lm,
                )
                
                result = await runner.run_task(task, self._get_attempt(task), self.run_dir)
                self._global_step += 1
                
                # 7. 处理结果
                if result.success:
                    quality_ok = self._run_constitution_gates(task, result)
                    if quality_ok:
                        self._commit_and_advance(task, result)
                    else:
                        self._rollback_and_retry(task, result)
                else:
                    self._handle_failure(task, result)
                
                # 8. 缓存失效
                self.queue.invalidate_cache()
        
        finally:
            self._emergency_cleanup()

    def _commit_and_advance(self, task: dict, result: IterationResult):
        task_id = task["id"]
        
        # Git 提交（安全：无 shell）
        commit_msg = f"relay {task_id}: {result.summary[:50]}"
        self.git.commit_all(commit_msg, Path.cwd())
        
        # 写 notes
        self.notes.append(
            task_id=task_id,
            attempt=self._get_attempt(task),
            summary=result.summary,
            changes=result.key_changes,
            learnings=result.key_learnings,
        )
        
        # 更新 task 状态为 completed
        with FileLock(Config.get_task_list_path()):
            self.tm.update_status(task_id, "completed")
        
        # 释放锁
        self.lm.release(task_id)
        
        self.backoff.record_success()
        self._current_task_id = None

    def _rollback_and_retry(self, task: dict, result: IterationResult):
        task_id = task["id"]
        
        # 回滚：reset + clean（在 relay 分支上执行，不影响原分支）
        self.git.reset_hard(Path.cwd())
        
        # 写 notes
        self.notes.append(
            task_id=task_id,
            attempt=self._get_attempt(task),
            summary=f"[ROLLED BACK] {result.summary}",
            changes=[],
            learnings=result.key_learnings + ["Rollback reason: Constitution gates failed"],
        )
        
        self._current_task_id = None

    def _handle_failure(self, task: dict, result: IterationResult):
        task_id = task["id"]
        
        if not result.schema_valid:
            self._log_error(f"Hard error on {task_id}: {result.error}")
        else:
            self._log_error(f"Soft failure on {task_id}: {result.summary}")
        
        self._current_task_id = None

    def _should_stop(self) -> bool:
        if self._should_stop_flag:
            return True
        if self.limits.max_steps and self._global_step >= self.limits.max_steps:
            return True
        return False

    def _emergency_cleanup(self):
        """退出时确保：释放当前 task 锁、关闭 agent 进程、flush 日志"""
        if self._current_task_id:
            try:
                self._log_info(f"Emergency cleanup: leaving {self._current_task_id} as orphanable")
            except Exception:
                pass
        self.adapter.shutdown()
        self._current_task_id = None

    def _get_attempt(self, task: dict) -> int:
        """从 notes_store 内存索引中获取当前 task 的尝试次数"""
        entries = self.notes._cache.get(task["id"], [])
        return len(entries) + 1

    def _run_constitution_gates(self, task: dict, result: IterationResult) -> bool:
        validation = self.tm._validate_constitution(
            task_id=task["id"],
            task=task,
            template=task.get("template", "task"),
        )
        return validation.get("passed", False)

    def _log_info(self, msg: str): ...
    def _log_error(self, msg: str): ...
```

**关键变化（全部 4 处差距已补）**:
- **Git 安全**: 所有 git 操作通过 `GitUtils`（`subprocess.run(argv)`，无 shell）
- **Clean Working Tree**: `run()` 开头调用 `ensure_clean_working_tree()`
- **分支隔离**: 每次 relay 创建 `relay/{timestamp}` 分支，所有 commit 在分支上
- **Reset + Clean**: `reset_hard()` 同时执行 `git clean -fd`
- **Schema 客户端强制**: `ClaudeAdapter` 通过 `--json-schema` 参数让 Claude 自己保证输出格式
- **Agent 进程管理**: `ClaudeAdapter` 通过 `spawn` + JSONL 解析 + 15s graceful shutdown

---

## 现有模块的改动

### task_manager.py

| 改动 | 说明 | 必要性 |
|------|------|--------|
| `get_ready_tasks()` | 已存在，无需改动 | ✅ 直接复用 |
| `update_status(task_id, "completed")` | 已存在，无需改动 | ✅ 直接复用 |
| `update_ralph_state(task_id, ralph_dict)` | 已存在，无需改动 | ✅ 直接复用 |
| `_validate_constitution()` | 已存在，无需改动 | ✅ 直接复用 |
| `get(task_id)` | 已存在，无需改动 | ✅ 直接复用 |
| 新增 `references` 字段 | **不需要** | ❌ 现有 `dependencies` 已足够 |

**结论**: `task_manager.py` **不需要任何改动**。

### locks_manager.py

| 改动 | 说明 | 必要性 |
|------|------|--------|
| `claim(task_id)` | 已存在，无需改动 | ✅ 直接复用 |
| `release(task_id)` | 已存在，无需改动 | ✅ 直接复用 |
| `heartbeat(task_id)` | 已存在，无需改动 | ✅ 直接复用 |
| `can_claim(task_id)` | 已存在，无需改动 | ✅ 直接复用 |

**结论**: `locks_manager.py` **不需要任何改动**。

### constitution.py

| 改动 | 说明 | 必要性 |
|------|------|--------|
| `PrincipleValidator.validate_all_principles()` | 已存在，无需改动 | ✅ 由 orchestrator 间接调用 |
| `GateEvaluator` | 已存在，无需改动 | ✅ 直接复用 |
| 新增 `output_contract` | **不需要** | ❌ schema 由 `structured_output.py` 生成，Constitution 继续负责代码质量 |

**结论**: `constitution.py` **不需要任何改动**。

### cli.py

新增 `relay` 子命令：

```python
@dataclass
class RunLimits:
    max_steps: int = 50

def cmd_relay(self, max_steps: int = 50, dry_run: bool = False):
    """启动 relay 模式，全自动执行可执行任务链"""
    if dry_run:
        ready = self.task_manager.get_ready_tasks(self.locks_manager)
        for task in ready:
            print(f"Would run: {task['id']} ({task.get('priority', 'P3')}) - {task['description'][:60]}")
        return
    
    # 准备 run 元数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"relay/{timestamp}"
    run_dir = Path(".long-run-agent/runs") / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入 output-schema.json（供 Claude CLI --json-schema 使用）
    schema_path = run_dir / "output-schema.json"
    StructuredOutputVerifier.write_schema_file(schema_path)
    
    # 固定使用 ClaudeAdapter
    adapter = ClaudeAdapter(schema_path=schema_path)
    
    orchestrator = RelayOrchestrator(
        task_manager=self.task_manager,
        locks_manager=self.locks_manager,
        adapter=adapter,
        constitution=self.constitution,
        run_dir=run_dir,
        limits=RunLimits(max_steps=max_steps),
        branch_name=branch_name,
    )
    asyncio.run(orchestrator.run())
```

---

## 与 gnhf 的关键区别

| 维度 | gnhf | LRA Relay |
|------|------|-----------|
| 任务粒度 | 每次迭代一个 prompt | 每个 task 是一个完整单元（claim → run → set completed） |
| 记忆 | notes.md 全部历史 | notes.md 按 task 分区 + 内存索引缓存 |
| 质量门禁 | agent 自己判断 | **两层验证**：JSON schema（Claude CLI 强制 + Python 兜底）+ 代码质量（Constitution gates） |
| 任务选择 | 单一 prompt 无拓扑 | 复用 `get_ready_tasks()` 的拓扑 + 依赖 + 锁检查 |
| 错误区分 | 硬错误/软错误 | 同上 + schema 验证失败作为独立硬错误类型 |
| **Git 安全** | `execFileSync(argv)` 无 shell | **相同**：`subprocess.run(["git", ...])` 无 shell |
| **Clean 检查** | `ensureCleanWorkingTree()` | **相同**：`GitUtils.ensure_clean_working_tree()` |
| **Reset 安全** | `reset --hard + clean -fd` | **相同**：`GitUtils.reset_hard()` 包含 clean |
| **Schema 强制** | `--json-schema` 客户端强制 | **相同**：`ClaudeAdapter` 通过 `--json-schema` 参数 |
| **进程管理** | spawn + JSONL + 15s grace | **相同**：`ClaudeAdapter` spawn + JSONL + `FINAL_RESULT_GRACE_MS` |
| **分支隔离** | `gnhf/{slug}` 分支 | **相同**：`relay/{timestamp}` 分支 |
| **与手动模式关系** | 替代 | **共存**：`lra ready/claim/set` 继续可用，relay 是其自动化封装 |

---

## CLI 集成

```bash
# 启动 relay 模式（全自动执行所有可执行任务，固定调用 Claude）
# 启动前自动检查 git status，脏工作区会报错退出
lra relay

# 带限制
lra relay --max-steps 50

# 干跑验证（不实际运行 agent，只打印执行计划）
lra relay --dry-run

# 查看 relay 运行历史
lra relay log

# 完成后合并 relay 分支到当前分支
git merge relay/20260427_163000
```

---

## 调试支持

每个 relay run 生成隔离目录：

```
.long-run-agent/runs/{timestamp}/
├── notes.md              # 迭代记忆（append-only）
├── relay.log             # JSONL 生命周期日志
├── output-schema.json    # 供 Claude CLI --json-schema 使用的 schema
├── attempt-1-{task_id}.jsonl   # agent 原始 JSONL 输出
├── attempt-2-{task_id}.jsonl
└── prompt.md             # 原始 prompt
```

Git 分支结构：
```
main                          # 原分支（ untouched ）
  └── relay/20260427_163000   # relay 运行分支（所有 agent commit 在此）
  └── relay/20260427_170000   # 另一次 relay 运行
```

主项目目录的 `.long-run-agent/` 结构保持不变：
```
.long-run-agent/
├── task_list.json        # 现有：任务索引
├── locks.json            # 现有：锁状态
├── constitution.yaml     # 现有：质量门禁定义
├── config.json           # 现有：项目配置
├── runs/                 # 新增：relay 运行历史
│   ├── 20260427_163000/
│   └── 20260427_170000/
└── tasks/                # 现有：任务详情 Markdown
```

---

## 待解决问题（更新后）

| 优先级 | 问题 | 当前策略 |
|--------|------|---------|
| **P1** | task 内部多迭代 | **复用 Ralph Loop**：一个 task 的多次尝试计入 `task["ralph"]["iteration"]`，最大 7 次后进入 `force_completed` 或停止 relay |
| **P1** | Constitution 验证失败后的策略 | **重试 3 次**（ Constitution 失败 → rollback → retry），超过后标记为 `FAILED` 并停止 relay |
| **P0** | 与现有手动模式的关系 | **明确共存**：relay 不替代 `lra ready/claim/set`，而是自动化封装。手动和 relay 通过 `LocksManager` 互斥 |
| **P1** | 资源清理 | **三层保障**：1) AgentRunner 心跳线程 join 超时；2) orchestrator `atexit` 注册；3) 锁不删除只停止心跳，15 分钟后自然 orphan |

---

## 实施顺序（更新后）

1. **`git_utils.py`**（最基础，所有模块依赖）
2. **`structured_output.py`**（独立，可测试 schema 生成）
3. **`backoff.py`**（逻辑简单，风险低）
4. **`notes_store.py`**（独立模块，可提前测试）
5. **`claude_adapter.py`**（核心，需要实际 Claude CLI 环境测试子进程管理）
6. **`task_queue.py`**（依赖 TaskManager + LocksManager）
7. **`agent_runner.py`**（组合 adapter + verifier + notes + backoff + locks）
8. **`orchestrator.py`**（主循环，集成所有模块）
9. **CLI 集成**（`lra relay` 命令）
10. **集成测试**（关键：验证 relay 与手动模式的锁互斥、git 安全、signal 中断）

---

## 最小可实施版本（MVP）

MVP 文件：

```
lra/relay/
├── __init__.py
├── git_utils.py          # 安全的 git 操作
├── structured_output.py  # schema 定义
├── backoff.py            # 指数退避
├── claude_adapter.py     # Claude CLI 子进程管理
├── agent_runner.py       # agent 生命周期
└── orchestrator.py       # 主循环
```

MVP 功能范围：
- ✅ 自动 `get_ready_tasks()` → `claim()` → run Claude → `update_status()`
- ✅ Claude CLI `--json-schema` 客户端强制结构化输出
- ✅ 失败时 `git stash` + `git reset --hard` + `git clean -fd`
- ✅ 无 shell 的 git 安全操作
- ✅ 写 notes.md
- ✅ `relay/{timestamp}` 分支隔离
- ❌ 心跳保活（MVP 可省略）
- ❌ Constitution 质量门禁（MVP 只验证 schema）
- ❌ SIGTERM 优雅停止（MVP 可先用 atexit）

等 MVP 跑通一个完整的无人值守 task 后，再逐步添加心跳、Constitution gates、signal 处理。
