# 质量检查器 v2.0 - 使用指南

## 概述

增强的质量检查系统支持多模板质量检查，集成质量门禁（Quality Gates）机制，能够生成具体的优化建议。

## 新增功能

### 1. 多模板支持

支持以下模板的质量检查：

- **code-module**: 代码模块开发
  - test: 测试检查
  - lint: 代码风格检查
  - acceptance: 验收标准检查
  - performance: 性能检查

- **novel-chapter**: 小说章节
  - word_count: 字数统计
  - plot_check: 情节连贯性
  - style_check: 写作风格

- **data-pipeline**: 数据处理流程
  - data_integrity: 数据完整性
  - processing_success: 处理成功率
  - output_validation: 输出验证

- **doc-update**: 文档更新
  - completeness: 文档完整性
  - link_validity: 链接有效性
  - format_check: 格式检查

- **task**: 通用任务
  - documentation: 文档覆盖
  - complexity: 代码复杂度
  - naming: 命名规范
  - structure: 项目结构
  - testing: 测试覆盖

### 2. 质量门禁配置

```python
QUALITY_GATES = {
    "code-module": [
        {"type": "test", "command": "pytest", "required": True, "weight": 0.4},
        {"type": "lint", "command": "ruff check", "required": False, "weight": 0.2},
        {"type": "acceptance", "check": "acceptance_criteria", "required": True, "weight": 0.3},
        {"type": "performance", "check": "check_performance", "required": False, "weight": 0.1}
    ],
    # ... 其他模板配置
}
```

每个门禁包含：
- `type`: 检查类型
- `required`: 是否必需
- `weight`: 权重 (0-1)
- `command`: 执行命令（可选）
- `check`: 检查方法（可选）

## 使用示例

### 基本用法

```python
from lra.quality_checker import QualityChecker

# 初始化
qc = QualityChecker()

# 查看支持的模板
templates = qc.get_supported_templates()
print(f"支持的模板: {templates}")

# 获取模板的质量门禁
gates = qc.get_quality_gates("code-module")
```

### 按模板检查质量

```python
# 检查代码模块质量
result = qc.check_quality_by_template(
    task_id="task-001",
    template_name="code-module"
)

print(f"质量评分: {result['score']}/{result['max_score']}")
print(f"失败必需项: {result['failed_required']}")

# 检查小说章节质量
result = qc.check_quality_by_template(
    task_id="chapter-001",
    template_name="novel-chapter"
)

print(f"字数: {result['checks'][0]['details'].get('total_words', 0)}")
```

### 生成优化建议

```python
# 检查质量
qc.check_quality_by_template("task-001", "code-module")

# 生成优化建议
hints = qc.generate_optimization_hints("task-001")

for hint in hints:
    print(f"类型: {hint['type']}")
    print(f"描述: {hint.get('description', hint.get('message'))}")
    if 'command' in hint:
        print(f"命令: {hint['command']}")
    if 'file_path' in hint:
        print(f"文件: {hint['file_path']}")
```

### 计算综合质量分

```python
checks = [
    {"type": "test", "score": 100, "weight": 0.4, "required": True, "passed": True},
    {"type": "lint", "score": 80, "weight": 0.2, "required": False, "passed": True},
    {"type": "acceptance", "score": 60, "weight": 0.3, "required": True, "passed": True},
]

score_info = qc.calculate_quality_score(checks)
print(f"综合评分: {score_info['score']}")
print(f"通过必需项: {score_info['passed_required']}")
```

### 获取失败的检查项

```python
qc.check_quality_by_template("task-001", "code-module")

failed = qc.get_failed_checks("task-001")

for item in failed:
    print(f"失败项: {item['type']}")
    print(f"评分: {item['score']}")
    print(f"是否必需: {item['required']}")
    print(f"问题: {item['issues']}")
```

## 质量评分规则

### 评分计算

1. **加权平均**: 每个检查项的分数乘以其权重，求和后除以总权重
   ```
   总分 = Σ (检查项分数 × 权重) / Σ 权重
   ```

2. **必需项失败**: 如果有必需项失败，最高分限制为 50 分

3. **单项评分**: 每个检查项独立评分 (0-100)
   - ≥60: 通过
   - <60: 不通过

### 示例

```python
# 代码模块质量检查
checks = [
    {"type": "test", "score": 100, "weight": 0.4, "required": True},
    {"type": "lint", "score": 80, "weight": 0.2, "required": False},
    {"type": "acceptance", "score": 60, "weight": 0.3, "required": True},
    {"type": "performance", "score": 100, "weight": 0.1, "required": False},
]

# 计算: (100×0.4 + 80×0.2 + 60×0.3 + 100×0.1) / (0.4+0.2+0.3+0.1)
# = (40 + 16 + 18 + 10) / 1.0
# = 84 分
```

## 与 Ralph Loop 集成

质量检查器已集成到 Ralph Loop 控制器中，可以在任务执行后自动进行质量检查：

```python
from lra.quality_checker import QualityChecker
from lra.ralph_loop import RalphLoop

# 在 Ralph Loop 中使用
loop = RalphLoop()
loop.quality_checker = QualityChecker()

# 任务完成后自动检查
# 质量不达标时提供优化建议
```

## 最佳实践

### 1. 为代码模块添加测试

```python
# 确保 tests/ 目录存在
# 添加单元测试文件
# 运行 pytest 验证
```

### 2. 完善验收标准

在任务文件中填写：
- 测试命令
- 测试输出
- 验证步骤

### 3. 定期运行质量检查

```bash
# 建议在 CI/CD 中集成
python3 -c "from lra.quality_checker import QualityChecker; qc = QualityChecker(); qc.check_code_quality()"
```

## 测试验证

运行测试文件验证功能：

```bash
python3 test_quality_checker.py
```

所有测试应该通过，输出：
```
✅ 所有测试通过！
✅ 支持至少3种模板的质量检查 (已支持5种模板)
✅ 能够生成具体的优化建议
✅ 计算综合质量评分
✅ 与 Ralph Loop 控制器集成
```

## 扩展开发

### 添加新的质量检查

1. 在 `_execute_quality_gate` 方法中添加新的检查类型
2. 实现检查方法（如 `_check_new_type`）
3. 在 `QUALITY_GATES` 中配置新的门禁

### 添加新的模板

1. 在 `QUALITY_GATES` 字典中添加新模板配置
2. 实现相应的检查方法
3. 更新模板管理器（如果需要）

## 故障排查

### pytest 未安装

```bash
pip install pytest
```

### ruff 未安装

```bash
pip install ruff
```

### 任务文件不存在

确保任务文件路径正确，默认在 `.long-run-agent/tasks/` 目录

## 版本历史

- v2.0 (2026-03-05): 多模板支持、质量门禁、优化建议
- v1.0 (初始版本): 基础质量检查