# Ralph Loop 使用指南（简化版）

## 🎯 核心理念

**LRA 是无状态的 CLI 工具**，只负责：
1. 记录任务状态（在 `task_list.json` 中）
2. 触发质量检查（在 `lra set completed` 时）
3. 查询任务状态（`lra show`, `lra context`）

**循环逻辑由 Agent 自己控制**，LRA 不提供循环控制器。

---

## ✅ 已实现的功能

### 1. 任务数据结构扩展

每个任务都有 `ralph` 字段记录优化状态：

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
    "issues": [...],
    "optimization_history": [...]
  }
}
```

### 2. 质量检查触发

```bash
# 提交任务时自动触发质量检查
lra set task_001 completed

# 输出：
🔍 自动运行质量检查...
❌ 质量检查未通过:
  • test: test_login_failed
  
进入优化循环 (1/7)
状态已自动更新为: optimizing
```

### 3. 状态查询

```bash
# 查看任务详情（包含优化状态）
lra show task_001

# 查看项目上下文（显示优化中的任务）
lra context
```

---

## 🔄 Agent 循环实现

Agent 应该自己实现循环逻辑，示例脚本：`scripts/ralph-agent-loop.sh`

### 基本模式

```bash
#!/bin/bash

# 主循环
while true; do
    # 1. 查看任务状态
    lra context
    
    # 2. 判断是否还有任务
    if [ 没有任务 ]; then
        break
    fi
    
    # 3. 领取任务
    lra claim task_001
    
    # 4. 执行工作（Agent 实际工作）
    # ... 实现/优化代码 ...
    
    # 5. 提交任务（触发质量检查）
    lra set task_001 completed
    # 质量检查自动运行，结果记录在任务中
    
    # 6. 检查状态
    status=$(lra show task_001 --json | jq -r '.status')
    if [ "$status" = "optimizing" ]; then
        echo "需要继续优化"
    fi
    
    # 7. 清空上下文（下一轮循环）
done
```

---

## 📊 状态流转

```
pending
   ↓ (lra claim)
in_progress
   ↓ (lra set completed + 质量检查)
   ├─ 通过 → truly_completed ✅
   └─ 未通过 → optimizing 🔄
              ↓ (优化后再次 set completed)
              ├─ 通过 → truly_completed ✅
              └─ 达到上限 → force_completed ⚠️
```

---

## 🛠️ 新增的任务管理器方法

```python
from lra.task_manager import TaskManager

tm = TaskManager()

# 获取 Ralph 状态
ralph_state = tm.get_ralph_state("task_001")

# 增加迭代计数
tm.increment_iteration("task_001")

# 记录质量检查结果
tm.record_quality_check("task_001", {
    "tests_passed": True,
    "lint_passed": True,
    "acceptance_met": False
})

# 添加优化历史
tm.add_optimization_history("task_001", {
    "iteration": 2,
    "changes": "修复了测试",
    "commit": "abc123"
})

# 获取真实状态
real_status = tm.get_real_status("task_001")
# 返回: "completed" | "optimizing" | "truly_completed" | "force_completed"
```

---

## 🧪 质量检查配置

模板中的 `ralph` 配置：

```yaml
# .long-run-agent/templates/code-module.yaml
ralph:
  enabled: true
  max_iterations: 7
  quality_gates:
    - type: test
      command: "pytest tests/"
      required: true
      weight: 0.4
    - type: lint
      command: "ruff check ."
      required: false
      weight: 0.2
    - type: acceptance
      check: "acceptance_criteria"
      required: true
      weight: 0.3
```

---

## 📝 使用示例

### 示例 1：查看优化任务

```bash
$ lra context

⚠️  优化中任务（优先处理）

【task_001】实现用户登录API
  状态: 🟡 需要优化 (优化轮次: 2/7)
  当前迭代: 2
  最大迭代: 7
```

### 示例 2：提交任务触发质量检查

```bash
$ lra set task_001 completed

✅ 任务已提交

🔍 自动运行质量检查...

❌ 质量检查未通过:
  • test: test_login_failed

进入优化循环 (1/7)

💡 建议操作:
   lra show task_001          # 查看详细优化状态
   lra quality-check task_001 # 查看完整质量报告

状态已自动更新为: optimizing
```

### 示例 3：查看任务优化状态

```bash
$ lra show task_001

ID: task_001
描述: 实现用户登录API
状态: optimizing

## 🔄 Ralph Loop 状态

当前轮次: 2/7
已优化次数: 1次

### 质量检查结果
- ❌ 测试未通过
- ✅ Lint 通过
- ❌ 验收标准未达标

### 优化历史
1. 轮次1: 实现基础功能 → 测试失败
```

---

## 🎯 关键设计

### LRA 的职责边界

✅ **LRA 负责**：
- 任务状态管理
- 质量检查触发
- 状态查询

❌ **LRA 不负责**：
- 循环控制
- 上下文管理
- Agent 调度

### Agent 的职责

✅ **Agent 负责**：
- 自己实现循环逻辑
- 管理上下文
- 调用 LRA 命令
- 执行实际工作

---

## 📚 参考文档

- **示例脚本**: `scripts/ralph-agent-loop.sh`
- **任务管理器文档**: `lra/task_manager.py`
- **质量检查器文档**: `lra/quality_checker.py`

---

## ✨ 总结

**正确理解**：
- LRA = 无状态 CLI 工具
- 状态存储在 `task_list.json` 中
- 循环由 Agent 自己控制
- 质量检查在 `lra set completed` 时自动触发

**核心价值**：
- 任务级优化状态跟踪
- 自动质量检查
- 清晰的状态查询
- Agent 友好的 CLI 接口

---

**版本**: v4.0.1 (简化版)  
**更新时间**: 2026-03-05