# lra/rwlock.py

> 语言：python | 代码行数：107

## 概述

读写锁实现
支持多读单写，优化并发性能

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `RWLock` | 7 | 读写锁（Read-Write Lock）

- 读锁：允许多个并发读
- 写锁：独占写，阻塞所有读写 |
| `ReadLock` | 3 | 读锁上下文管理器 |
| `WriteLock` | 3 | 写锁上下文管理器 |

## 依赖

- os
- fcntl
- typing
