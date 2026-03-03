# long_run_agent/system_check.py

> 语言：python | 代码行数：420

## 概述

系统预检任务
v3.3.0 - Agent 自治式初始化预检

核心功能:
- 代码规模统计
- Git 信息分析
- 文档覆盖率计算
- 函数注释分析
- 自动决策（全量/增量）

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `SystemCheckTask` | 13 | 系统预检任务执行器 |
| `ConfigManager` | 4 | 配置管理器 |

## 依赖

- os
- re
- json
- datetime
- typing
- pathlib
- config
