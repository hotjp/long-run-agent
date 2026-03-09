# Constitution 强制执行机制说明

## 🎯 核心机制

### 1. 自动触发点

Constitution验证在以下关键节点**自动触发**：

#### 任务完成时（completed）
```python
# TaskManager.update_status() 第372行
if status in ["completed", "truly_completed"] and not force:
    constitution_result = self._validate_constitution(task_id, t, template)
    if not constitution_result["passed"]:
        # 自动进入optimizing状态
        t["status"] = "optimizing"
        # 返回失败信息
        return False, f"constitution_failed:{failures}"
```

#### Ralph Loop完成时（truly_completed）
```python
# 第405行
elif current_real_status == "optimizing" and status == "truly_completed":
    # 先验证Constitution
    constitution_result = self._validate_constitution(task_id, t, template)
    if not constitution_result["passed"]:
        # 验证失败，继续迭代
        return False, f"constitution_failed:{failures}"
```

#### 强制完成时（force_completed）
```python
# 第419行
elif status == "force_completed":
    # 即使强制完成，也要检查NON_NEGOTIABLE原则
    constitution_result = self._validate_constitution(
        task_id, t, template, check_non_negotiable_only=True
    )
    if not constitution_result["passed"]:
        # NON_NEGOTIABLE原则不能违反
        return False, f"constitution_non_negotiable_violation:{failures}"
```

### 2. 不可绕过机制

#### NON_NEGOTIABLE原则强制
```python
def _validate_constitution(
    self, 
    task_id: str, 
    task: Dict, 
    template: str, 
    check_non_negotiable_only: bool = False
) -> Dict[str, Any]:
    """验证Constitution原则"""
    
    # 只检查NON_NEGOTIABLE原则
    if check_non_negotiable_only:
        principles = manager.get_non_negotiable_principles()
        # 必须全部通过
        all_failures = []
        for principle in principles:
            result = validator.validate_principle(principle, task_id, task)
            if not result.passed:
                all_failures.extend(result.failures)
        
        return {
            "passed": len(all_failures) == 0,
            "failures": all_failures
        }
```

### 3. 防止AI偷懒

#### 强制验证流程

```
AI尝试标记任务完成
    ↓
自动触发Constitution验证
    ↓
┌─────────────────────┐
│ 验证是否通过？      │
└─────────────────────┘
    ↓           ↓
   通过        失败
    ↓           ↓
 任务完成    自动进入optimizing
    ↓           ↓
              Ralph Loop启动
              最多7次迭代
              修复问题
```

#### 强制场景

| 场景 | 强制验证 | 可否绕过 |
|------|---------|---------|
| completed | 全部原则 | ❌ 不可以 |
| truly_completed | 全部原则 | ❌ 不可以 |
| force_completed | NON_NEGOTIABLE原则 | ❌ 不可以 |
| force=True参数 | NON_NEGOTIABLE原则 | ❌ 不可以 |

## 💡 AI无法偷懒的原因

### 1. 自动触发
- **无需手动调用** - 完成任务时自动验证
- **不可跳过** - 在状态转换逻辑中强制检查
- **透明拦截** - 失败时自动进入优化状态

### 2. 明确反馈
```bash
$ lra set task_001 completed

❌ Constitution验证失败

   任务: task_001
   状态: 自动进入 optimizing (优化中)

📋 失败项:

   1. test_gate: 测试未通过
   2. test_evidence_gate: 字段缺失

💡 修复建议:

   1. 查看任务详情: lra show task_001
   2. 修复上述问题
   3. 重新标记完成: lra set task_001 completed
   4. 查看Constitution: lra constitution show

📚 帮助: lra constitution help
```

### 3. 不可绕过
- **NON_NEGOTIABLE原则必须通过**
- **即使force=True也要验证**
- **验证失败明确告知原因**

## 🔍 实现细节

### 关键代码位置

1. **TaskManager.update_status()** (lra/task_manager.py:350)
   - 集成Constitution验证
   - 自动状态转换

2. **TaskManager._validate_constitution()** (lra/task_manager.py:429)
   - 验证逻辑实现
   - 支持只检查NON_NEGOTIABLE

3. **CLI.cmd_set()** (lra/cli.py:832)
   - 友好的失败提示
   - 修复建议

### 验证流程图

```
┌─────────────────────────────────────────────────────────┐
│                  任务完成请求                            │
│            lra set task_001 completed                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Constitution自动验证                        │
│  • 加载Constitution配置                                 │
│  • 获取所有适用原则                                      │
│  • 执行所有门禁检查                                      │
└─────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   验证是否通过？      │
              └───────────────────────┘
                    ↓           ↓
                   通过        失败
                    ↓           ↓
         ┌──────────────┐  ┌──────────────────┐
         │  任务完成    │  │ 进入optimizing   │
         │  ✅ success  │  │ Ralph Loop启动   │
         └──────────────┘  │ 最多7次迭代      │
                           └──────────────────┘
                                   ↓
                           ┌──────────────┐
                           │  修复问题    │
                           └──────────────┘
                                   ↓
                           ┌──────────────┐
                           │ 重新验证     │
                           └──────────────┘
                                   ↓
                           通过 → truly_completed
```

## 📊 对比：改进前 vs 改进后

### 改进前 ❌
```bash
# AI可以偷懒
$ lra set task_001 completed
✅ 状态已更新

# 没有验证，直接完成
# 质量问题被忽略
```

### 改进后 ✅
```bash
# AI无法偷懒
$ lra set task_001 completed

❌ Constitution验证失败
   自动进入optimizing状态

📋 失败项:
   1. test_gate: 测试未通过
   2. evidence_gate: 证据缺失

💡 必须修复问题才能完成！
```

## 🎯 效果保证

### 1. 质量保证
- ✅ 所有任务必须通过Constitution验证
- ✅ NON_NEGOTIABLE原则不可违反
- ✅ 质量问题自动拦截

### 2. AI行为约束
- ✅ 无法绕过验证
- ✅ 必须修复问题
- ✅ 明确的失败原因

### 3. 用户体验
- ✅ 自动验证，无需手动
- ✅ 友好的失败提示
- ✅ 明确的修复建议

## 🚀 使用示例

### 场景1: 正常完成
```bash
$ lra create "实现登录功能"
# 创建任务

$ lra claim task_001
# 认领任务

# ... 实现功能、编写测试、添加证据 ...

$ lra set task_001 completed
# 自动Constitution验证

✅ Constitution验证通过
✅ 任务完成
```

### 场景2: 验证失败
```bash
$ lra set task_001 completed

❌ Constitution验证失败

📋 失败项:
   1. test_gate: pytest tests/ failed (2 failed)

💡 修复建议:
   1. 查看测试失败详情
   2. 修复测试问题
   3. lra set task_001 completed

# AI必须修复问题才能完成
```

### 场景3: 强制完成（仅限NON_NEGOTIABLE原则通过）
```bash
# 达到优化上限
$ lra set task_001 force_completed

# 仍然验证NON_NEGOTIABLE原则
❌ 违反不可协商原则

🔴 不可协商原则违反:
   1. test_gate: 测试未通过

⚠️  不可协商原则不能绕过，必须修复问题
```

## 📚 相关文档

- **CONSTITUTION_DESIGN.md** - Constitution设计文档
- **CONSTITUTION_COMPLETE.md** - 功能完成报告
- **lra/constitution.py** - 核心实现代码
- **lra/task_manager.py** - 强制集成代码

---

**文档版本**: v1.0  
**最后更新**: 2024-03-09  
**作者**: LRA Team