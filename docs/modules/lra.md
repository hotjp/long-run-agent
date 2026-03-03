# lra 模块

> 分析时间：2026-03-03 13:15
> 文件数：17 | 代码行数：7548 | 文档覆盖：100%

## 概述

LRA - AI Agent Task Manager with Quality Assurance v4.0.0

## 核心类

### `LockStatus`

> -

### `LocksManager`

> -

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__` | `(self)` | - |
| `_ensure_file` | `(self)` | - |
| `_load` | `(self)` | - |
| `_save` | `(self, data) -> bool` | - |
| `_generate_session_id` | `(self, task_id: str) -> str` | - |
| `_check_orphan` | `(self, lock) -> bool` | - |
| `get_lock` | `(self, task_id: str)` | - |
| `_get_parent_id` | `(self, task_id: str)` | - |
| `_get_children_ids` | `(self, task_id: str)` | - |
| `claim` | `(self, task_id: str)` | - |

### `BatchLockManager`

> -

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__` | `(self)` | - |
| `_current_time_ms` | `(self) -> int` | 获取当前 Unix 时间戳（毫秒） |
| `_load_lock` | `(self)` | 加载锁文件 |
| `_save_lock` | `(self, data) -> bool` | 保存锁文件（使用文件锁保证原子性） |
| `_delete_lock` | `(self)` | 删除锁文件 |
| `acquire` | `(self, agent_id: str, operation: str, task_ids, timeout_ms: int, wait: bool, max_wait_ms: int)` | 获取批量操作锁

Args:
    agent_id: Agent 唯一标识
 |
| `_try_acquire` | `(self, agent_id: str, operation: str, task_ids, timeout_ms: int)` | 尝试获取锁（不等待） |
| `release` | `(self, agent_id: str)` | 释放锁 |
| `heartbeat` | `(self, agent_id: str, extend_ms: int)` | 心跳续期 |
| `status` | `(self)` | 查看锁状态 |

### `RWLock`

> 读写锁（Read-Write Lock）

- 读锁：允许多个并发读
- 写锁：独占写，阻塞所有读写

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__` | `(self, lock_path: str)` | - |
| `_ensure_lock_file` | `(self)` | 确保锁文件存在 |
| `acquire_read` | `(self)` | 获取读锁（共享锁） |
| `acquire_write` | `(self)` | 获取写锁（独占锁） |
| `release` | `(self)` | 释放锁 |
| `__enter__` | `(self)` | 默认获取写锁（安全起见） |
| `__exit__` | `(self, exc_type, exc_val, exc_tb)` | - |

### `ReadLock`

> 读锁上下文管理器

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__` | `(self, lock_path: str)` | - |
| `__enter__` | `(self)` | - |
| `__exit__` | `(self, exc_type, exc_val, exc_tb)` | - |

### `WriteLock`

> 写锁上下文管理器

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__` | `(self, lock_path: str)` | - |
| `__enter__` | `(self)` | - |
| `__exit__` | `(self, exc_type, exc_val, exc_tb)` | - |

### `Config`

> -

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `get_metadata_dir` | `(cls) -> str` | - |
| `get_task_list_path` | `(cls) -> str` | - |
| `get_config_path` | `(cls) -> str` | - |
| `get_locks_path` | `(cls) -> str` | - |
| `get_templates_dir` | `(cls) -> str` | - |
| `get_template_path` | `(cls, name: str) -> str` | - |
| `get_tasks_dir` | `(cls) -> str` | - |
| `get_task_path` | `(cls, task_id: str) -> str` | - |
| `get_records_dir` | `(cls) -> str` | - |
| `get_records_index_path` | `(cls) -> str` | - |

### `FileLock`

> -

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__` | `(self, lock_path: str)` | - |
| `__enter__` | `(self)` | - |
| `__exit__` | `(self, exc_type, exc_val, exc_tb)` | - |

### `SafeJson`

> -

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `read` | `(path: str)` | - |
| `write` | `(path: str, data) -> bool` | - |

### `GitHelper`

> -

**方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `is_repo` | `() -> bool` | - |
| `get_current_commit` | `()` | - |
| `get_diff_files` | `()` | - |


## 核心函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `current_time_ms` | `` | 获取当前 Unix 时间戳（毫秒） |
| `ms_to_iso` | `ms` | 毫秒时间戳转 ISO 格式 |
| `iso_to_ms` | `iso_str` | ISO 格式转毫秒时间戳 |
| `get_agent_id` | `` | 获取 Agent ID（环境变量优先，否则生成 UUID） |
| `validate_project_initialized` | `` | - |
| `sort_key` | `t` | - |
| `output` | `data, json_mode` | - |
| `main` | `` | - |
| `dfs` | `node` | - |

## 依赖关系

### 本模块依赖

- time
- uuid
- lra.template_manager
- argparse
- fcntl
- lra.locks_manager
- lra.batch_lock_manager
- os
- ast
- lra.config
- json
- lra.tips
- random
- subprocess
- lra.cli

## 使用示例

```python
# 待补充
```

✅ 文档完善度良好