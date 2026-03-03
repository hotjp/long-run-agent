# scripts/benchmark.py

> 语言：python | 代码行数：605

## 概述

LRA v3.2.1 性能基准测试

测试场景：
1. 单任务操作（创建/读取/更新/删除）
2. 并发任务操作（多进程模拟多 Agent）
3. 依赖关系解锁性能
4. 大数据量压力测试

性能指标：
- 内存占用（MB）
- 操作延迟（ms）
- 吞吐量（ops/s）
- I/O 读写（KB/s）

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `PerformanceMonitor` | 7 | 性能监控器 |
| `IOTracer` | 3 | I/O 追踪器 - 包装 SafeJson 来统计 I/O |

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `create_test_environment` | `test_dir` | 创建测试环境 |
| `cleanup_test_environment` | `test_dir` | 清理测试环境 |
| `benchmark_single_task` | `monitor, num_tasks` | 单任务操作基准测试 |
| `benchmark_concurrent_tasks` | `monitor, num_tasks, num_worker` | 并发任务操作测试 |
| `benchmark_dependencies` | `monitor, num_tasks, dependency` | 依赖关系性能测试 |
| `run_benchmark_suite` | `` | 运行完整的性能测试套件 |
| `generate_markdown_table` | `results` | 生成 Markdown 表格 |
| `main` | `` | 主函数 |
| `worker_task` | `task_id` | 工作进程 |
| `traced_read` | `path` | - |
| `traced_write` | `path, data` | - |

## 依赖

- os
- sys
- json
- time
- shutil
- tempfile
- multiprocessing
- datetime
- typing
- pathlib
- long_run_agent.task_manager
- long_run_agent.locks_manager
- long_run_agent.template_manager
- long_run_agent.config
