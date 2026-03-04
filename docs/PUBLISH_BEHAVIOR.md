# publish 命令行为说明

## 命令用途

`lra publish <parent_task_id>` 用于发布父任务的子任务，使其可以被认领。

## 工作原理

1. **释放子任务锁定**: 父任务创建子任务时，所有子任务会被父任务锁定
2. **保持父任务控制**: publish 后，子任务仍然受父任务锁的控制
3. **认领限制**: 只有持有父任务锁的 agent 才能认领其子任务

## 使用场景

### 场景1: 单 agent 管理子任务

```bash
# 1. 创建并拆分父任务
lra create "Web应用开发"
lra split task_001 --count 3

# 2. 认领父任务（获得所有子任务的控制权）
lra claim task_001

# 3. 发布子任务
lra publish task_001

# 4. 认领子任务（因为持有父任务锁，所以可以认领）
lra claim task_001_01
lra claim task_001_02

# 5. 执行子任务
lra set task_001_01 in_progress
# ... 工作中 ...
lra set task_001_01 completed
```

### 场景2: 多 agent 协作（推荐方式）

如果需要多个 agent 协作处理子任务，建议：

**方式1**: 不同的 agent 认领不同的父任务

```bash
# Agent A 认领父任务1
lra claim task_001
lra publish task_001
lra claim task_001_01  # 可以认领，因为持有父任务锁

# Agent B 认领父任务2（不同的任务分支）
lra claim task_002
lra publish task_002
lra claim task_002_01  # 可以认领
```

**方式2**: 释放父任务锁后让其他 agent 认领

```bash
# Agent A 准备子任务
lra claim task_001
lra split task_001 --count 3
lra publish task_001

# Agent A 释放父任务锁
lra set task_001 in_progress  # 先设置状态
# 注意：需要手动释放锁（如果有这个功能）

# Agent B 认领子任务
lra claim task_001_01  # 现在可以认领了
```

## 设计原因

这种设计的目的是：
1. **任务完整性**: 确保相关联的子任务由同一个 agent 或协调的 agents 处理
2. **避免冲突**: 防止多个 agents 同时操作同一组相关任务
3. **责任明确**: 父任务拥有者对整体进度负责

## 常见问题

### Q: 为什么 publish 后其他 agent 不能认领子任务？

A: 因为父任务仍然被锁定。只有父任务的拥有者才能认领其子任务。这是为了保持任务组的一致性。

### Q: 如何让其他 agent 认领子任务？

A: 有几种方式：
1. 让其他 agent 认领不同的父任务分支
2. 释放父任务的锁（需要先设置父任务状态）
3. 使用任务分配系统预先分配任务

### Q: 如果我真的需要其他 agent 认领子任务怎么办？

A: 联系系统管理员或使用 `lra recover` 命令（谨慎使用）。

## 相关命令

- `lra claim` - 认领任务
- `lra split` - 拆分任务
- `lra heartbeat` - 心跳续期
- `lra set` - 更新任务状态

## 版本信息

- 文档版本: v4.0
- 最后更新: 2026-03-03
