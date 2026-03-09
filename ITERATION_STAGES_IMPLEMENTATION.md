# TemplateManager 迭代阶段配置加载功能

## 实现总结

✅ **已完成所有要求的方法**：

### 1. `load_iteration_stages(template_name: str)` -> List[Dict[str, Any]]
- 从模板配置文件加载迭代阶段定义
- 支持从 YAML 文件读取 `ralph.iteration_stages` 配置
- 自动验证阶段配置
- 提供默认配置作为 fallback

### 2. `_validate_stage(stage: Dict)` -> bool
- 验证阶段配置是否完整有效
- 检查必需字段：`iteration`, `name`, `focus`, `suggestion`
- 验证 `iteration` 值范围（1-7）
- 验证 `focus` 类型为列表
- 支持可选字段：`priority_checks`, `ignore_checks`, `safety_checks`

### 3. `_get_default_stages()` -> List[Dict[str, Any]]
- 返回默认的7阶段配置
- 当模板没有配置时使用
- 包含完整的7个迭代阶段

### 4. `get_stage_by_iteration(template_name: str, iteration: int)` -> Optional[Dict[str, Any]]
- 获取指定迭代的阶段配置
- 当找不到指定迭代时返回最后一个阶段

## 测试结果

```
============================================================
测试迭代阶段配置加载功能
============================================================
✓ 不存在的模板返回默认阶段: 7 个阶段
✓ 获取迭代1的配置: 基础实现
✓ 获取迭代10的配置（返回最后一个）: 最终验证
✓ 有效阶段验证通过
✓ 缺少字段的阶段被正确拒绝
✓ iteration超出范围的阶段被正确拒绝
✓ focus类型错误的阶段被正确拒绝
✓ 从test-stages模板加载阶段: 3 个阶段
✓ 获取迭代2: 核心实现
✓ 获取不存在的迭代返回最后一个: 完善优化
============================================================
✅ 所有测试通过!
============================================================
```

## 集成验证

TaskManager 已成功集成新功能：

```python
# task_manager.py:1309
stages = self.template_manager.load_iteration_stages(template_name)
```

- `TaskManager.get_iteration_stage()` 方法已在使用 `load_iteration_stages()`
- `TaskManager.update_iteration_stage()` 方法通过 `get_iteration_stage()` 间接使用

## 使用示例

### 从模板文件加载阶段配置

模板文件 `.long-run-agent/templates/my-template.yaml`:
```yaml
ralph:
  iteration_stages:
    - iteration: 1
      name: 需求分析
      focus: [理解需求, 设计架构]
      priority_checks: [test]
      suggestion: "🎯 首次迭代：深入理解需求"
```

Python 代码：
```python
from lra.template_manager import TemplateManager

tm = TemplateManager()
stages = tm.load_iteration_stages("my-template")
stage = tm.get_stage_by_iteration("my-template", 1)
```

### 使用默认配置

```python
tm = TemplateManager()
stages = tm.load_iteration_stages("non-existent")
# 返回7个默认阶段
```

## 验收标准

- ✅ 4个新方法都已实现
- ✅ 能正确读取模板中的 iteration_stages
- ✅ 有完整的验证逻辑
- ✅ 提供默认配置作为 fallback
- ✅ 所有测试通过
- ✅ 与 TaskManager 成功集成