# lra/project_analyzer.py

> 语言：python | 代码行数：1294

## 概述

Project Analyzer - 项目代码分析器
v1.0 - 多语言支持

核心功能:
- 扫描项目结构
- 识别模块
- 分析代码元素（类、函数、依赖）
- 生成结构化文档

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `ClassInfo` | 0 | - |
| `FunctionInfo` | 0 | - |
| `FileInfo` | 0 | - |
| `ModuleInfo` | 0 | - |
| `PythonParser` | 8 | Python 代码解析器 |
| `JavaScriptParser` | 10 | JavaScript/TypeScript 代码解析器（基于正则） |
| `GoParser` | 10 | Go 代码解析器 |
| `ProjectAnalyzer` | 25 | 项目代码分析器 |

## 依赖

- os
- re
- json
- ast
- datetime
- typing
- dataclasses
- pathlib
- lra.config
