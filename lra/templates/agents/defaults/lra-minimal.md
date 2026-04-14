# LRA Instructions

> **LRA** (Long-Running Agent) 是本项目的任务管理框架。
> agent 必须通过本文件了解 LRA，不要假设其他知识。

## 核心概念

LRA 使用 **任务状态机** 管理任务生命周期：
`pending → in_progress → completed → optimizing → truly_completed`

## 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 未开始，可能有依赖阻塞 |
| `in_progress` | 进行中 |
| `completed` | 初始完成，等待质量检查 |
| `optimizing` | 修复质量问题中 |
| `truly_completed` | 全部质量门控通过 |

## 优先级

| 优先级 | 说明 |
|--------|------|
| P0 | 关键（安全、数据丢失、破坏构建）|
| P1 | 高（主要功能、重要 bug）|
| P2 | 中（默认）|
| P3 | 低（优化）|

## 命令参考

```bash
lra list                # 列出所有任务
lra ready              # 列出可认领任务
lra show <id>          # 查看任务详情
lra claim <id>         # 认领任务
lra new "描述"         # 快速创建并认领
lra set <id> <status>  # 更新状态
lra checkpoint <id> --note "进度"  # 保存检查点
lra deps <id>          # 查看依赖
lra doctor             # 健康检查
```

## 工作流程

```
1. lra ready              # 查看可认领任务
2. lra claim <id>        # 原子性认领
3. lra set <id> in_progress
4. 实现功能
5. lra checkpoint <id> --note "完成核心逻辑"
6. lra set <id> completed
7. 如果失败: lra set <id> optimizing → 修复 → 回到 step 6
8. 成功后: lra set <id> truly_completed
```

## 禁止规则

- ❌ 不要创建 markdown TODO 列表
- ❌ 不要使用 LRA 以外的追踪系统
- ❌ 不要跳过 `lra ready` 直接问"我该做什么"
- ❌ 不要编辑 task 文件（用 `lra set` 命令）

<!-- BEGIN LRA INTEGRATION profile:minimal -->
<!-- 此 section 由 lra init 管理，请勿手动修改 -->
<!-- END LRA INTEGRATION -->
