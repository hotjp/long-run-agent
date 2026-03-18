# lra/config.py

> 语言：python | 代码行数：266

## 概述

LRA v4.0 配置模块
通用任务管理框架

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `Config` | 14 | - |
| `FileLock` | 3 | - |
| `SafeJson` | 2 | - |
| `GitHelper` | 3 | - |

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `current_time_ms` | `` | 获取当前 Unix 时间戳（毫秒） |
| `ms_to_iso` | `ms` | 毫秒时间戳转 ISO 格式 |
| `iso_to_ms` | `iso_str` | ISO 格式转毫秒时间戳 |
| `get_agent_id` | `` | 获取 Agent ID

优先级:
1. 环境变量 LRA_AGENT_ID
2. 进程全局缓存
3 |
| `validate_project_initialized` | `` | - |

## 依赖

- os
- json
- subprocess
- time
- typing
- datetime
- filelock
