# lra/parsers.py

> 语言：python | 代码行数：104

## 概述

Input parsers for CLI arguments with backward compatibility.

Provides unified parsing for complex CLI inputs like dependencies and variables.
Supports both JSON format (preferred) and legacy formats (with deprecation warnings).

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `parse_dependencies` | `value` | Parse dependencies from CLI argument.

Supports:
- |
| `parse_variables` | `value` | Parse variables from CLI argument.

Variables must |
| `parse_acceptance` | `value` | Parse acceptance criteria from CLI argument.

Supp |

## 依赖

- json
- typing
