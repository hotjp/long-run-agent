# tests/test_constitution.py

> 语言：python | 代码行数：235

## 概述

测试Constitution模块

## 函数

| 函数名 | 参数 | 说明 |
|--------|------|------|
| `test_principle_type_enum` | `` | 测试原则类型枚举 |
| `test_gate_type_enum` | `` | 测试门禁类型枚举 |
| `test_gate_dataclass` | `` | 测试门禁数据类 |
| `test_principle_dataclass` | `` | 测试原则数据类 |
| `test_validation_result` | `` | 测试验证结果 |
| `test_gate_result` | `` | 测试门禁结果 |
| `test_create_default_constitution` | `` | 测试创建默认Constitution |
| `test_constitution_manager_init` | `` | 测试ConstitutionManager初始化 |
| `test_constitution_manager_get_principles` | `` | 测试获取原则 |
| `test_constitution_manager_get_all_applicable_principles` | `` | 测试获取所有适用原则 |
| `test_gate_evaluator_command_gate` | `` | 测试命令门禁评估 |
| `test_gate_evaluator_field_gate` | `` | 测试字段门禁评估 |
| `test_principle_validator` | `` | 测试原则验证器 |
| `test_principle_validator_validate_all` | `` | 测试验证所有原则 |
| `test_init_constitution` | `` | 测试初始化Constitution |

## 依赖

- pytest
- tempfile
- os
- pathlib
- lra.constitution
