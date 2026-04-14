# lra/errors.py

> 语言：python | 代码行数：169

## 概述

LRA Error Messages with Actionable Suggestions

This module provides a centralized error catalog that gives agents
clear guidance on how to recover from errors.

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `get_error_with_action` | `error_code, context` | Get error message with actionable suggestion.

Arg |
| `format_error_display` | `err` | Format error for CLI display with emoji.

Returns: |
| `parse_error_from_msg` | `msg` | Parse error code and details from raw error messag |

## 依赖

- typing
