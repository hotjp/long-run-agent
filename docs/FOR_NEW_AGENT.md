# LRA 工具测试任务

## 你的任务

测试 LRA (Long-Run-Agent) 任务管理工具，发现并修复问题。

## 背景

这是一个AI Agent任务管理工具，通过CLI命令使用。

**项目路径**: `/Users/kingj/.openclaw/workspace/long-run-agent`

**当前版本**: v5.0 (🆕 Constitution功能已集成)

## 🆕 新功能：Constitution (v5.0)

### 核心概念

Constitution定义项目的**不可协商原则**和**质量标准**，在任务完成前**自动验证**。

### 关键命令

```bash
lra constitution help       # 使用指南
lra constitution init       # 初始化Constitution
lra constitution show       # 查看配置
lra constitution validate   # 验证配置
```

### 三层原则

- 🔴 **NON_NEGOTIABLE** - 不可协商，必须通过
- 🟡 **MANDATORY** - 强制，必需门禁通过
- 🟢 **CONFIGURABLE** - 可配置，可启用/禁用

### 强制执行

⚠️ **重要**: Constitution在任务完成时自动验证，AI无法绕过！

- 任务标记completed时自动验证
- 验证失败自动进入optimizing状态
- NON_NEGOTIABLE原则不能违反

### 快速测试

```bash
# 1. 查看Constitution配置
lra constitution show

# 2. 创建任务
lra create "测试任务"

# 3. 尝试完成任务（会自动验证Constitution）
lra set task_001 completed

# 如果验证失败，会看到详细的失败原因和修复建议
```

### 相关文档

- `docs/CONSTITUTION_ENFORCEMENT.md` - 强制执行机制
- `docs/CONSTITUTION_DESIGN.md` - 详细设计
- `CONSTITUTION_COMPLETE.md` - 功能完成报告

## 测试要求

### 🚫 限制
- **不要阅读源码**（除非修复bug时需要定位）
- **不要查看文档**（README等）
- 只通过运行命令和观察输出来学习

### ✅ 目标
1. 摸索如何使用这个工具
2. 测试未测试的命令和场景
3. 记录遇到的所有卡点和困惑
4. 修复发现的问题

### 📋 已测试的命令（上一个agent）

✅ **核心工作流** (9个): start, init, context, list, create, show, set, split, claim  
✅ **查询命令** (6个): search, guide, status-guide, where, index, deps  
✅ **项目管理** (3个): analyze-project, system-check, recover  
✅ **任务执行** (3个): pause, checkpoint, resume  
✅ **🆕 Constitution** (4个): constitution help, show, init, validate  
⚠️ **部分测试** (2个): template list, batch claim

**测试覆盖率**: 80% (27/34)

## 🎯 测试场景设计

### 场景1: 任务协作与锁机制（高优先级）

**目标**: 测试多agent协作场景下的锁机制

**测试命令**: 
- publish - 发布子任务
- heartbeat - 心跳续期
- batch-lock - 批量锁管理

**测试流程**:
```bash
# 1. 创建父任务并拆分
lra create "Web应用开发" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计","deliverables":["文件"]}'
lra split task_001 --plan '[{"desc":"子任务1","requirements":"需求","acceptance":["完成"],"deliverables":["文件"]},{"desc":"子任务2","requirements":"需求","acceptance":["完成"],"deliverables":["文件"]},{"desc":"子任务3","requirements":"需求","acceptance":["完成"],"deliverables":["文件"]}]'

# 2. 认领父任务
lra claim task_001

# 3. 发布子任务（测试点：子任务状态变化）
lra publish task_001
lra list  # 查看子任务是否可被认领

# 4. 测试心跳（测试点：锁续期）
lra claim task_002
lra heartbeat task_002
lra show task_002  # 查看锁状态

# 5. 测试批量锁（测试点：并发控制）
lra batch-lock status
lra batch-lock acquire --operation batch_claim --tasks task_003,task_004
lra batch-lock status
lra batch-lock release
lra batch-lock logs  # 查看操作日志
```

**预期结果**:
- publish 后子任务状态变为可认领
- heartbeat 成功续期锁
- batch-lock 能正确管理并发操作
- batch-lock logs 显示操作历史

---

### 场景2: 依赖管理与阻塞检测（高优先级）

**目标**: 测试复杂依赖关系和阻塞处理

**测试命令**:
- check-blocked - 检查阻塞
- deps - 依赖查看
- --dependency-type any/all - 依赖类型

**测试流程**:
```bash
# 1. 创建依赖链
lra create "数据库设计" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "API接口" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "前端页面" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "集成测试" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}' --dependencies task_001,task_002,task_003

# 2. 查看依赖
lra deps task_004
lra deps task_004 --dependents  # 查看谁依赖它

# 3. 检查阻塞
lra check-blocked  # task_004 应该被阻塞

# 4. 测试 --dependency-type any
lra create "任意依赖任务" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}' --dependencies task_001,task_002 --dependency-type any

# 5. 完成前置任务
lra claim task_001
lra set task_001 in_progress
lra set task_001 completed
lra check-blocked  # 应该仍然阻塞（还有2个未完成）

# 6. 完成所有前置
lra set task_002 completed
lra set task_003 completed
lra check-blocked  # 应该不再阻塞
lra show task_004  # 检查状态
```

**预期结果**:
- 依赖任务被正确标记为 blocked
- 完成前置任务后自动解除阻塞
- deps 命令正确显示依赖关系
- --dependency-type any 在任一依赖完成时解除阻塞

---

### 场景3: 模板系统与自定义（中优先级）

**目标**: 测试模板系统的完整功能

**测试命令**:
- template show - 查看模板详情
- template create - 创建自定义模板
- template delete - 删除模板
- status-guide - 状态流转指南

**测试流程**:
```bash
# 1. 查看现有模板
lra template list
lra template show task
lra template show code-module  # 查看有测试流程的模板

# 2. 查看所有模板的状态流转
lra status-guide

# 3. 创建自定义模板
lra template create my-feature --from task
lra create "测试自定义模板" --template my-feature -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'

# 4. 测试模板的状态流转
lra show <task_id>  # 查看可用状态流转
lra set <task_id> in_progress

# 5. 删除自定义模板
lra template delete my-feature
lra template list  # 确认删除
```

**预期结果**:
- template show 显示完整的模板定义
- status-guide 显示所有模板的状态流转图
- 自定义模板能正常使用
- 模板状态流转正确

---

### 场景4: 批量操作与优先级（中优先级）

**目标**: 测试批量操作和优先级管理

**测试命令**:
- batch set - 批量更新状态
- batch delete - 批量删除
- set-priority - 设置优先级
- search --status - 按状态搜索

**测试流程**:
```bash
# 1. 创建多个任务
lra create "批量任务1" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "批量任务2" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "批量任务3" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "批量任务4" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "批量任务5" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'

# 2. 设置优先级
lra set-priority task_001 P0  # 最高优先级
lra set-priority task_002 P0
lra set-priority task_003 P1
lra context  # 查看优先级排序

# 3. 批量认领
lra batch claim task_001 task_002

# 4. 批量更新状态
lra batch set task_001 task_002 in_progress
lra list  # 查看状态

# 5. 按状态搜索
lra search "批量" --status in_progress
lra search "批量" --status pending

# 6. 批量删除
lra create "临时任务1" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra create "临时任务2" -var '{"requirements":"需求","acceptance":["完成"],"design":"设计"}'
lra batch delete <temp_id1> <temp_id2>
lra list  # 确认删除
```

**预期结果**:
- set-priority 正确影响任务排序
- batch set 批量更新状态成功
- batch delete 批量删除成功
- search --status 正确过滤任务

---

### 场景5: 记录与变更跟踪（中优先级）

**目标**: 测试记录功能

**测试命令**:
- record - 记录变更
- record --auto - 自动记录git提交

**测试流程**:
```bash
# 1. 查看record帮助
lra record --help

# 2. 初始化git仓库（如果没有）
git init
echo "test" > test.txt
git add .
git commit -m "initial commit"

# 3. 自动记录git提交
lra record add feature_001 --auto

# 4. 手动创建feature记录
lra record add feature_002 --desc "用户认证功能"

# 5. 记录git提交
lra record add feature_002 --commit $(git rev-parse HEAD) --desc "实现登录API"

# 6. 查看记录
lra record list
lra record show feature_001
lra record show feature_002

# 7. 查看时间线
lra record timeline feature_002
```

**预期结果**:
- record 命令能正确记录变更
- record --auto 自动获取当前git提交信息
- 能查询历史记录
- 时间线显示正确

---

### 场景6: 快速了解项目（中优先级）

**目标**: 测试快速了解项目的命令

**测试命令**:
- orientation - 项目定位
- status - 项目进度可视化

**测试流程**:
```bash
# 1. 快速了解项目（推荐）
lra orientation

# 2. 查看项目进度可视化
lra status

# 3. 查看详细上下文
lra context --full
lra context --output-limit 16k

# 4. 查看文件位置
lra where
lra index
```

**预期结果**:
- orientation 一次性显示项目定位、进度、任务列表
- status 显示可视化进度条
- context --full 显示完整上下文
- where 显示关键文件位置

---

### 场景7: 质量检查与测试（中优先级）

**目标**: 测试质量保障相关命令

**测试命令**:
- quality-check - 代码质量检查
- regression-test - 回归测试
- browser-test - 浏览器测试

**测试流程**:
```bash
# 1. 代码质量检查
lra quality-check
lra quality-check --report

# 2. 回归测试
lra regression-test
lra regression-test --report
lra regression-test --template code-module

# 3. 浏览器测试
lra browser-test --script
```

**预期结果**:
- quality-check 显示代码质量报告
- regression-test 运行回归测试
- browser-test 生成测试脚本

---

### 场景8: 高级功能（低优先级）

**目标**: 测试其他未测试的命令

**测试命令**:
- analyze-module - 模块分析
- version - 版本信息

**测试流程**:
```bash
# 1. 查看版本
lra version

# 2. 分析整个项目
lra analyze-project
lra analyze-project --force

# 3. 分析单个模块（在有代码的项目中）
lra analyze-module <module_name>  # 需要在有Python/JS代码的项目中运行
```

**预期结果**:
- version 显示正确的版本号
- analyze-project 输出项目分析结果
- analyze-module 在空项目中有友好的错误提示

---

## 🔍 特别关注点

### 1. v5.0 新功能检查

**重要**: 检查以下命令是否已集成到主CLI

```bash
# 尝试运行这些命令，看是否可用
lra status           # 项目进度可视化
lra orientation      # 上下文重建
lra regression-test  # 回归测试
lra browser-test     # 浏览器测试
lra quality-check    # 质量检查
```

**如果不可用**:
- 记录为问题：v5.0功能未集成
- 查看 `lra/cli_extensions.py` 了解这些命令
- 尝试手动集成或报告问题

### 2. 锁机制完整性

- 测试锁冲突处理
- 测试锁过期自动释放
- 测试批量锁的事务性
- 测试 batch-lock logs 查看历史

### 3. 依赖管理

- 测试循环依赖检测
- 测试依赖类型（all vs any）
- 测试复杂依赖图

### 4. 边界条件

- 空任务列表
- 不存在的任务ID
- 无效的状态转换
- 重复操作

### 5. 新增功能验证

- `lra context --full` 参数是否正常
- `lra orientation` 快速了解项目
- `lra record --auto` 自动记录git
- `lra analyze-module` 友好错误提示
- `lra split --plan` 格式是否正确

## 开始方式

```bash
# 安装
cd /Users/kingj/.openclaw/workspace/long-run-agent
pip install -e . --quiet

# 查看帮助
lra --help

# 查看具体命令帮助
lra <command> --help

# 创建测试目录（建议）
mkdir -p /tmp/lra-test-advanced
cd /tmp/lra-test-advanced
lra start --name test-project
```

## 记录要求

### 问题记录格式

```markdown
## 问题记录

### 问题1: <简短描述>
- 场景: 场景X / 独立发现
- 命令: `lra xxx`
- 现象: 详细描述发生了什么
- 影响: 严重/中等/轻微
- 修复: 如何修复的（如果修复了）
```

### 测试覆盖记录

```markdown
## 测试覆盖

### 场景1: 任务协作与锁机制
- [x] publish 命令测试
- [x] heartbeat 命令测试
- [x] batch-lock 命令测试
- [x] batch-lock logs 测试
- [ ] 锁冲突处理
- [ ] 锁过期处理
...
```

## 修复原则

发现bug后：
1. 定位代码（允许此时查看源码）
2. 设计修复方案
3. 实施修复
4. 验证修复

**修复时要遵循**:
- 永不崩溃 - 所有异常都要捕获
- 智能降级 - 失败时返回默认值
- 友好提示 - 告诉用户怎么办
- 自动处理 - 能推断的不要求输入

## 输出要求

测试完成后，提供：

1. **测试覆盖报告** - 列出测试了哪些场景和命令
2. **问题列表** - 发现的所有问题
3. **v5.0状态** - v5.0新功能的集成状态
4. **修复内容** - 如何修复的
5. **体验评分** - 1-5星（分场景评分）
6. **改进建议** - 如何做得更好

## 参考资料

- **测试覆盖报告**: `TEST_COVERAGE.md`
- **改进报告**: `IMPROVEMENT_REPORT.md`
- **问题报告**: `TEST_ISSUES.md`

---

**记住**: 
- 从Agent视角评估，不是开发者视角
- 记录真实的困惑，不要带着预设
- 让工具更友好，减少错误和困惑
- 重点关注锁机制、依赖管理、批量操作
- 检查v5.0新功能的集成状态
- 验证新增的 --full 参数和 orientation 命令

开始吧！
