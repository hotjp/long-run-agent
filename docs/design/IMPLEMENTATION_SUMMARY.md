# 阶段卡住检测机制实现总结

## 实现内容

### 1. 核心功能

已在 `lra/cli.py` 中实现阶段卡住检测和处理机制，包括：

- **阶段卡住检测**：当质量检查未通过时，自动检测是否在当前阶段卡住超过3次
- **强制进入下一阶段**：新增 `lra set <task_id> force_next_stage` 命令
- **用户引导**：卡住时显示警告和操作建议

### 2. 实现细节

#### 2.1 阶段卡住检测逻辑

位置：`lra/cli.py:_run_quality_check_on_complete` 方法

```python
# 检查是否卡住
is_stuck, stuck_count = self.task_manager.check_stage_stuck(task_id, threshold=3)

if is_stuck:
    # 在当前阶段卡住了
    current_stage = ralph_state.get("current_stage", {})
    stage_name = current_stage.get("name", "未知阶段")
    
    print(f"\n⚠️  警告：在【{stage_name}】阶段已尝试 {stuck_count} 次")
    print(f"   当前迭代: {iteration}/{max_iterations}")
    print(f"\n❌ 质量检查仍未通过:")
    for check in failed_required:
        print(f"   • {check}")
    
    print(f"\n💡 建议选项：")
    print(f"   1. 强制进入下一阶段（放弃当前阶段目标）")
    print(f"      执行: lra set {task_id} force_next_stage")
    print(f"   2. 继续尝试当前阶段")
    print(f"      继续工作并提交: lra set {task_id} completed")
```

#### 2.2 强制进入下一阶段命令

位置：`lra/cli.py:cmd_set` 方法

```python
def cmd_set(self, task_id: str, status: str, json_mode: bool = False):
    # ...
    
    if status == "force_next_stage":
        self._force_next_stage(task_id, json_mode)
        return
    
    # ...
```

#### 2.3 强制进入下一阶段实现

位置：`lra/cli.py:_force_next_stage` 方法

```python
def _force_next_stage(self, task_id: str, json_mode: bool):
    """强制进入下一阶段"""
    # 1. 检查是否能增加迭代
    # 2. 强制增加迭代次数
    # 3. 获取下一阶段信息
    # 4. 显示下一阶段引导
    # 5. 更新任务状态为 optimizing
```

### 3. 依赖的现有方法

这些方法已存在于 `lra/task_manager.py` 中：

- `check_stage_stuck(task_id, threshold=3)` - 检查是否卡住
- `increment_iteration(task_id)` - 增加迭代次数
- `get_iteration_stage(task_id, iteration)` - 获取阶段配置
- `get_stage_suggestion(task_id)` - 获取阶段建议
- `update_status(task_id, status, force=True)` - 更新任务状态

### 4. 测试验证

已创建测试脚本验证实现：

#### 4.1 单元测试

`test_force_next_stage.py` 测试了：
- `check_stage_stuck` 方法正确检测卡住状态
- 强制进入下一阶段的逻辑

运行结果：
```
✅ check_stage_stuck 测试通过
✅ 强制进入下一阶段逻辑测试通过
```

#### 4.2 CLI 集成测试

`test_cli_force_next_stage.py` 测试了：
- `lra set <task_id> force_next_stage` 命令
- 完整的用户流程

### 5. 使用示例

#### 场景1：任务卡在某个阶段

```bash
# 1. 任务完成，自动运行质量检查
lra set task_001 completed

# 输出示例：
🔍 自动运行质量检查...

❌ 质量检查未通过:
  • test: 测试失败
  • lint: 代码风格问题

⚠️  警告：在【初始实现】阶段已尝试 3 次
   当前迭代: 1/7

❌ 质量检查仍未通过:
   • test_failure
   • lint_error

💡 建议选项：
   1. 强制进入下一阶段（放弃当前阶段目标）
      执行: lra set task_001 force_next_stage
   2. 继续尝试当前阶段
      继续工作并提交: lra set task_001 completed

进入优化循环 (2/7)

# 2. 用户选择强制进入下一阶段
lra set task_001 force_next_stage

# 输出示例：
🚀 强制进入下一阶段...

✅ 已进入迭代 2/7
   新阶段: 代码优化

📌 当前迭代: 2/7
阶段: 代码优化

🎯 本次重点:
   • 重构代码
   • 提升性能

💡 提示: 查看完整引导: lra show task_001
```

#### 场景2：达到最大迭代次数

```bash
# 如果已达到最大迭代次数，会提示：
❌ 已达到最大迭代次数 (7)，无法进入下一阶段
   建议: lra set task_001 force_completed
```

### 6. 验收标准

✅ `check_stage_stuck()` 正确检测卡住状态  
✅ 卡住时显示警告和选项  
✅ `lra set <task_id> force_next_stage` 命令可用  
✅ 强制进入下一阶段时显示新阶段引导  

### 7. 技术要点

1. **卡住检测逻辑**：
   - 检查 `optimization_history` 中最近3次的迭代值
   - 如果连续3次 `iteration` 相同，则判定为卡住

2. **强制进入下一阶段**：
   - 调用 `increment_iteration()` 增加迭代次数
   - 自动更新 `current_stage` 到下一阶段
   - 显示新阶段的重点和建议

3. **用户体验**：
   - 清晰的警告信息
   - 明确的操作选项
   - 详细的阶段引导

### 8. 文件修改清单

- `lra/cli.py` - 主要修改
  - `_run_quality_check_on_complete` - 添加卡住检测
  - `cmd_set` - 处理 `force_next_stage` 命令
  - `_force_next_stage` - 新增方法

### 9. 注意事项

1. **LSP错误**：检测到的LSP类型错误是预先存在的，与本次实现无关
2. **向后兼容**：新功能不影响现有命令的正常使用
3. **错误处理**：所有操作都有错误处理和用户友好的提示

### 10. 后续优化建议

1. 可以考虑添加配置项来自定义卡住阈值（当前硬编码为3）
2. 可以添加自动跳过选项（例如：连续5次失败后自动进入下一阶段）
3. 可以记录跳过原因，供后续分析