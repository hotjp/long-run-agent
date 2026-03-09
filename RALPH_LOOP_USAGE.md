# Ralph Loop 状态管理使用指南

## 概述

TaskManager 现已支持 Ralph Loop 状态跟踪，可以记录任务优化过程中的迭代、质量检查和问题历史。

## 数据结构

每个任务现在包含一个 `ralph` 字段，结构如下：

```json
{
  "id": "task_001",
  "status": "completed",
  "ralph": {
    "iteration": 2,
    "max_iterations": 7,
    "quality_checks": {
      "tests_passed": false,
      "lint_passed": true,
      "acceptance_met": false
    },
    "issues": [
      {
        "round": 1,
        "type": "test_failure",
        "message": "test_login_failed",
        "timestamp": "2026-03-05T10:30:00"
      }
    ],
    "optimization_history": [
      {
        "iteration": 1,
        "changes": "修复密码验证",
        "commit": "abc123",
        "timestamp": "2026-03-05T10:35:00"
      }
    ]
  }
}
```

## 主要功能

### 1. 获取 Ralph 状态

```python
from lra.task_manager import TaskManager

tm = TaskManager()
ralph_state = tm.get_ralph_state("task_001")

print(f"当前迭代: {ralph_state['iteration']}")
print(f"最大迭代: {ralph_state['max_iterations']}")
print(f"质量检查: {ralph_state['quality_checks']}")
```

### 2. 更新 Ralph 状态

```python
# 更新最大迭代次数
tm.update_ralph_state("task_001", {"max_iterations": 10})

# 批量更新多个字段
tm.update_ralph_state("task_001", {
    "iteration": 3,
    "max_iterations": 10
})
```

### 3. 增加迭代计数

```python
success, new_iteration = tm.increment_iteration("task_001")
if success:
    print(f"新迭代次数: {new_iteration}")
else:
    print("已达到最大迭代次数")
```

### 4. 记录质量检查

```python
# 记录单项检查
tm.record_quality_check("task_001", {"tests_passed": True})

# 记录多项检查
tm.record_quality_check("task_001", {
    "tests_passed": True,
    "lint_passed": True,
    "acceptance_met": False
})
```

### 5. 添加优化历史

```python
tm.add_optimization_history("task_001", {
    "iteration": 1,
    "changes": "修复密码验证逻辑",
    "commit": "abc123def456"
})
```

### 6. 记录问题

```python
# 添加问题记录
tm.add_ralph_issue("task_001", "test_failure", "test_login_failed")

# 指定轮次
tm.add_ralph_issue("task_001", "lint_error", "E501 line too long", round_num=2)
```

### 7. 获取真实状态

```python
real_status = tm.get_real_status("task_001")

# 可能的状态：
# - pending: 待处理
# - in_progress: 进行中
# - completed: 首次完成（待质量检查）
# - optimizing: 优化循环中
# - truly_completed: 质量检查通过
# - force_completed: 达到优化上限强制完成
```

### 8. 检查是否可继续优化

```python
if tm.can_continue_optimization("task_001"):
    print("可以继续优化")
else:
    print("已达到优化上限")
```

### 9. 获取优化摘要

```python
summary = tm.get_optimization_summary("task_001")

print(f"迭代次数: {summary['iteration']}/{summary['max_iterations']}")
print(f"总问题数: {summary['total_issues']}")
print(f"问题类型: {summary['issue_types']}")
print(f"优化次数: {summary['optimization_count']}")
print(f"质量状态: {summary['quality_status']}")
print(f"可继续: {summary['can_continue']}")
```

## 状态转换流程

```
pending → in_progress: 任务开始
    ↓
in_progress → completed: 第一次完成
    ↓
completed → optimizing: 质量检查未通过（可选）
    ↓
optimizing → truly_completed: 质量检查通过
    或
optimizing → force_completed: 达到优化上限
```

## 完整示例：Ralph Loop 控制器集成

```python
from lra.task_manager import TaskManager

def run_ralph_loop(task_id: str):
    """执行 Ralph 优化循环"""
    tm = TaskManager()
    
    # 1. 检查任务状态
    real_status = tm.get_real_status(task_id)
    if real_status != "completed":
        print(f"任务状态不是 completed: {real_status}")
        return
    
    # 2. 进入优化循环
    tm.update_status(task_id, "optimizing")
    
    while tm.can_continue_optimization(task_id):
        # 增加迭代
        success, iteration = tm.increment_iteration(task_id)
        if not success:
            print("已达到最大迭代次数")
            break
        
        print(f"\n=== 开始第 {iteration} 轮优化 ===")
        
        # 执行优化（这里是示例）
        # optimization_result = perform_optimization(task_id)
        
        # 记录优化历史
        tm.add_optimization_history(task_id, {
            "iteration": iteration,
            "changes": "优化代码逻辑",
            "commit": "new_commit_hash"
        })
        
        # 运行质量检查
        test_result = run_tests()
        lint_result = run_lint()
        acceptance_result = check_acceptance()
        
        # 记录质量检查结果
        tm.record_quality_check(task_id, {
            "tests_passed": test_result,
            "lint_passed": lint_result,
            "acceptance_met": acceptance_result
        })
        
        # 记录问题
        if not test_result:
            tm.add_ralph_issue(task_id, "test_failure", "测试失败")
        if not lint_result:
            tm.add_ralph_issue(task_id, "lint_error", "代码风格问题")
        
        # 检查是否全部通过
        if test_result and lint_result and acceptance_result:
            # 质量检查通过
            tm.update_status(task_id, "truly_completed")
            print(f"✅ 第 {iteration} 轮优化成功，质量检查全部通过")
            return
    
    # 达到优化上限，强制完成
    tm.update_status(task_id, "force_completed")
    print("⚠️ 达到优化上限，任务强制完成")

def run_tests():
    """运行测试"""
    # 实现测试逻辑
    return True

def run_lint():
    """运行 lint 检查"""
    # 实现 lint 逻辑
    return True

def check_acceptance():
    """检查验收标准"""
    # 实现验收检查
    return True
```

## API 参考

### TaskManager 新增方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_ralph_state(task_id)` | task_id: str | Dict[str, Any] | 获取 Ralph 状态 |
| `update_ralph_state(task_id, ralph_state)` | task_id: str, ralph_state: Dict | Tuple[bool, str] | 更新 Ralph 状态 |
| `increment_iteration(task_id)` | task_id: str | Tuple[bool, int] | 增加迭代计数 |
| `record_quality_check(task_id, checks)` | task_id: str, checks: Dict[str, bool] | Tuple[bool, str] | 记录质量检查 |
| `add_optimization_history(task_id, entry)` | task_id: str, entry: Dict | Tuple[bool, str] | 添加优化历史 |
| `add_ralph_issue(task_id, issue_type, message, round_num)` | task_id: str, issue_type: str, message: str, round_num: int (optional) | Tuple[bool, str] | 添加问题记录 |
| `get_real_status(task_id)` | task_id: str | str | 获取真实状态 |
| `set_max_iterations(task_id, max_iterations)` | task_id: str, max_iterations: int | Tuple[bool, str] | 设置最大迭代次数 |
| `can_continue_optimization(task_id)` | task_id: str | bool | 检查是否可继续优化 |
| `get_optimization_summary(task_id)` | task_id: str | Dict[str, Any] | 获取优化摘要 |

## 注意事项

1. **向后兼容**: 旧任务会自动获得默认的 `ralph` 字段
2. **默认值**: 
   - 初始迭代次数: 0
   - 默认最大迭代: 7
   - 质量检查初始状态: 全部 false
3. **状态验证**: `update_status` 方法支持 `force` 参数跳过状态转换验证
4. **时间戳**: 优化历史和问题记录会自动添加时间戳

## 验收标准

- ✅ 支持 ralph 状态字段
- ✅ 能够记录优化历史
- ✅ 状态转换逻辑正确
- ✅ 与 Ralph Loop 控制器集成
- ✅ 向后兼容现有任务
- ✅ 完整的测试覆盖