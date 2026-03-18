# tests/test_v4_fixes.py

> 语言：python | 代码行数：313

## 概述

测试 v5.0 修复的功能
测试用例覆盖：
1. batch-lock agent_id 一致性
2. record 功能（list/show/timeline）
3. check-blocked 显示被阻塞任务
4. blocked 任务 lock_status 清理

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `TestBatchLockAgentId` | 6 | 测试 batch-lock agent_id 一致性修复 |
| `TestRecordFunctionality` | 7 | 测试 record 功能 |
| `TestCheckBlocked` | 4 | 测试 check-blocked 功能 |
| `TestBlockedTaskLockCleanup` | 3 | 测试 blocked 任务的 lock_status 清理 |

## 依赖

- os
- sys
- json
- tempfile
- shutil
- unittest
- pathlib
- lra.config
- lra.batch_lock_manager
- lra.records_manager
- lra.task_manager
- lra.locks_manager
