# 质量检查器 v2.0 - 增强说明

## 更新内容

### ✅ 新增功能

1. **多模板支持** - 支持 5 种模板的质量检查
   - `code-module`: 代码模块开发
   - `novel-chapter`: 小说章节
   - `data-pipeline`: 数据处理流程
   - `doc-update`: 文档更新
   - `task`: 通用任务

2. **质量门禁（Quality Gates）**
   - 每个模板定义独立的质量门禁配置
   - 支持必需项和可选项
   - 支持权重计算

3. **新增方法**
   - `check_quality_by_template(task_id, template_name)`: 按模板检查质量
   - `generate_optimization_hints(task_id)`: 生成优化建议
   - `calculate_quality_score(checks)`: 计算综合质量分
   - `get_failed_checks(task_id)`: 获取失败的检查项
   - `get_supported_templates()`: 获取支持的模板列表
   - `get_quality_gates(template_name)`: 获取质量门禁配置

4. **优化建议生成**
   - 根据失败的检查项生成具体建议
   - 包含文件路径和命令
   - 提供修复方向

### 🔧 技术改进

- 保持向后兼容
- 扩展现有 `QualityChecker` 类
- 完整的错误处理
- 集成到 Ralph Loop 控制器

## 验收标准

- ✅ 支持至少 3 种模板的质量检查（已支持 5 种）
- ✅ 能够生成具体的优化建议
- ✅ 计算综合质量评分
- ✅ 与 Ralph Loop 控制器集成

## 测试

运行测试验证功能：

```bash
python3 test_quality_checker.py
```

运行示例查看使用方法：

```bash
python3 examples_quality_checker.py
```

## 文件清单

- `lra/quality_checker.py`: 增强的质量检查器（v2.0）
- `test_quality_checker.py`: 测试文件
- `examples_quality_checker.py`: 使用示例
- `docs/quality_checker_v2.md`: 使用文档

## 快速开始

```python
from lra.quality_checker import QualityChecker

# 初始化
qc = QualityChecker()

# 查看支持的模板
print(qc.get_supported_templates())

# 按模板检查质量
result = qc.check_quality_by_template("task-001", "code-module")

# 生成优化建议
hints = qc.generate_optimization_hints("task-001")

# 获取失败的检查项
failed = qc.get_failed_checks("task-001")
```

## 质量评分规则

- 加权平均计算综合评分
- 必需项失败时，最高分限制为 50 分
- 每个检查项独立评分（0-100）
- ≥60 分为通过，<60 分为失败

## 下一步

- 集成到 CI/CD 流程
- 添加更多检查项
- 支持自定义质量门禁配置