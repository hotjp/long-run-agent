# LRA Agent — Ralph Loop 操作规程

## ⚠️ 绝对规则

1. **禁止跳过阶段** — 必须按顺序通过每个阶段，不能直接 set completed
2. **禁止跳过证据** — 每阶段必须填充证据字段才能推进
3. **禁止手动编辑 JSON** — 用 `lra set` 命令改状态
4. **禁止提交未验证代码** — 测试必须跑过才能 commit

---

## Ralph Loop — 7 阶段迭代模型

每个任务必须逐阶段完成，不能跳阶段：

```
Stage 1: 理解规划 → Stage 2: 基础实现 → Stage 3: 功能完善 →
Stage 4: 质量提升 → Stage 5: 优化改进 → Stage 6: 验证测试 →
Stage 7: 交付准备 → [完成]
```

### 每阶段检查项

| 阶段 | 门禁 | 命令 |
|------|------|------|
| 1 理解规划 | 理解需求，拆分任务 | — |
| 2 基础实现 | 代码能跑，无语法错误 | `python -m py_compile .` |
| 3 功能完善 | 功能完整，边界处理 | `ruff check .` |
| 4 质量提升 | 类型检查通过 | `mypy . --ignore-missing-imports` |
| 5 优化改进 | 性能/结构优化 | 代码 review |
| 6 验证测试 | 测试通过 | `pytest tests/ -v` |
| 7 交付准备 | 文档/变更记录 | `lra regression-test` |

### 阶段推进命令

每阶段完成后，推进到下一阶段：

```bash
lra set <task_id> force_next_stage
```

---

## 完整工作流

### 第一步：领取任务
```bash
lra claim <task_id>
lra show <task_id>
```

### 第二步：读懂任务
- 需求是什么？
- 验收标准是什么？
- 属于哪个阶段？（看任务状态）

### 第三步：按阶段工作

#### Stage 2 基础实现
1. 写核心代码
2. `python -m py_compile .` 验证语法
3. 填证据到任务文件
4. `lra set <task_id> force_next_stage`

#### Stage 3 功能完善
1. 补全功能，处理边界
2. `ruff check .` 验证风格
3. 更新证据
4. `lra set <task_id> force_next_stage`

#### Stage 4 质量提升
1. 类型注解、错误处理
2. `mypy . --ignore-missing-imports`
3. 更新证据
4. `lra set <task_id> force_next_stage`

#### Stage 5 优化改进
1. 重构/性能优化
2. 更新证据
3. `lra set <task_id> force_next_stage`

#### Stage 6 验证测试
1. 运行完整测试
2. `pytest tests/ -v`
3. `lra regression-test`
4. 更新证据
5. `lra set <task_id> force_next_stage`

#### Stage 7 交付准备
1. 文档更新
2. git commit
3. `lra set <task_id> completed`

### 第四步：证据格式

每阶段完成后，编辑 `.long-run-agent/tasks/<task_id>.md`：

```markdown
### 阶段 N 证据（<阶段名>）

- **通过检查**: [命令和结果]
- **改动内容**: [具体修改了什么]
- **影响范围**: [改了什么文件/功能]
```

---

## 证据必须包含的内容

```
### 测试证据
- [x] **实现证明**: [简要说明实现了什么]
- [x] **测试验证**: [运行了什么测试，结果如何]
- [x] **影响范围**: [改了哪些文件]

### 验证步骤
1. [执行命令]
2. [实际输出]
```

---

## 提交格式

```bash
git add .
git commit -m "feat(<stage>): <任务描述>

- Stage <N>: <阶段名>
- 检查: <通过的检查命令>
- 任务: <task_id>

🤖 Generated with LRA"
```

---

## 停止条件

**每轮结束前检查**：

- 所有阶段门禁已通过？
- 任务状态是 `completed`？

如果是，回复：
```
<promise>COMPLETE</promise>
```

如果还有阶段没完成，本轮结束。下一轮从当前阶段继续。

---

## 快速参考

| 操作 | 命令 |
|------|------|
| 推进阶段 | `lra set <id> force_next_stage` |
| 领取任务 | `lra claim <id>` |
| 查看任务 | `lra show <id>` |
| 查看进度 | `lra status` |
| 保活心跳 | `lra heartbeat <id>` |

---

**先运行 `lra orientation`，然后 `lra context --full` 开始工作。**
