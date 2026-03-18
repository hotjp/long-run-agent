# lra/constitution.py

> 语言：python | 代码行数：587

## 概述

Constitution - 项目宪法管理器
定义和验证项目的不可协商原则和质量标准

v1.0 - 初始实现

## 类

| 类名 | 方法数 | 说明 |
|------|--------|------|
| `PrincipleType` | 0 | 原则类型 |
| `GateType` | 0 | 门禁类型 |
| `Gate` | 0 | 门禁定义 |
| `Principle` | 0 | 原则定义 |
| `ValidationResult` | 0 | 验证结果 |
| `GateResult` | 0 | 门禁检查结果 |
| `ConstitutionManager` | 12 | Constitution管理器 |
| `GateEvaluator` | 6 | 门禁评估器 |
| `PrincipleValidator` | 3 | 原则验证器 |

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `create_default_constitution` | `project_name` | 创建默认Constitution |
| `init_constitution` | `project_name` | 初始化Constitution文件 |

## 依赖

- dataclasses
- typing
- enum
- pathlib
- yaml
- subprocess
- hashlib
