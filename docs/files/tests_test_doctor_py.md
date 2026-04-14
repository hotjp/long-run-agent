# tests/test_doctor.py

> 语言：python | 代码行数：442

## 概述

Tests for LRA Doctor module

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `TestDoctorChecks` | 30 | Test individual doctor checks |
| `TestRunDiagnostics` | 4 | Test run_diagnostics function |
| `TestFixOrphanedLocks` | 4 | Test fix_orphaned_locks function |

## 依赖

- os
- shutil
- tempfile
- datetime
- lra.config
- lra.doctor
