# Ralph Loop 使用指南

## 📖 概述

Ralph Loop 是一个任务级循环优化机制，支持编程、写作、数据分析等多种场景。

**核心特性**：
- ✅ 自动质量检查
- ✅ 任务级循环（每个任务独立优化）
- ✅ 最多7次优化
- ✅ 智能退出条件
- ✅ 错误处理和回滚

---

## 🚀 快速开始

### 1. 基本工作流

```bash
# 查看项目状态
lra context

# 输出示例：
⚠️  优化中任务（优先处理）

【task_001】实现用户登录API
  状态: 🟡 需要优化 (优化轮次: 2/7)
  
  ❌ 质量问题:
    • 测试失败: test_login_failed
    • 性能问题: 响应时间 800ms
  
  💡 建议: 检查密码验证逻辑
```

### 2. 查看任务详情

```bash
lra show task_001

# 输出包含：
# - Ralph Loop 状态
# - 质量检查结果
# - 优化历史
# - 下一步建议
```

### 3. 提交任务并触发质量检查

```bash
lra set task_001 completed

# 自动执行：
# ✅ 任务已提交
# 🔍 自动运行质量检查...
# ❌ 质量检查未通过 -> 进入优化循环(1/7)
```

---

## 📊 质量检查系统

### 支持的模板

| 模板 | 质量门禁 | 权重 |
|------|---------|------|
| **code-module** | 测试(0.4)、Lint(0.2)、验收标准(0.3)、性能(0.1) | 1.0 |
| **novel-chapter** | 字数(0.4)、情节(0.3)、风格(0.2) | 0.9 |
| **data-pipeline** | 数据完整性(0.4)、处理成功(0.3)、输出验证(0.2) | 0.9 |
| **doc-update** | 内容完整性(0.4)、格式检查(0.3)、链接检查(0.2) | 0.9 |
| **task** | 完成度检查(0.5)、质量检查(0.5) | 1.0 |

### 质量评分

- **优秀**: ≥ 90分
- **良好**: ≥ 70分
- **及格**: ≥ 60分
- **不及格**: < 60分（需要优化）

---

## ⚙️ 配置说明

### 全局配置 (.long-run-agent/ralph_config.yaml)

```yaml
ralph:
  enabled: true
  
  optimization:
    max_iterations: 7           # 最大优化次数
    no_change_threshold: 3      # 无改动退出阈值
    auto_rollback: true         # 无进展时自动回滚
  
  quality_check:
    auto_run: true              # 自动运行质量检查
    strict_mode: false          # 严格模式
  
  error_handling:
    max_failures: 3             # 最大失败次数
    max_rollbacks: 3            # 最大回滚次数
    record_issues: true         # 记录问题
```

### 模板配置

每个模板都有独立的 Ralph 配置：

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
```

---

## 🔄 优化流程

### 标准流程

```
1. Agent 提交任务 (lra set completed)
     ↓
2. 自动质量检查
     ↓
   ┌─────────┐
   │ 通过？  │
   └────┬────┘
        │
   ┌────┴────┐
   │ 是      │ 否
   ▼         ▼
真正完成  进入优化循环
              ↓
         优化轮次 1/7
              ↓
         质量检查
              ↓
         ...
              ↓
         优化轮次 7/7 (最后机会)
              ↓
         强制完成或真正完成
```

### 退出条件

| 条件 | 说明 |
|------|------|
| **质量检查通过** | 所有必需检查项通过 |
| **达到优化上限** | 已优化7次 |
| **无改动退出** | 连续3次无代码变更 |
| **错误上限** | 错误+回滚超过6次 |

---

## 📝 Agent 提示示例

### lra context 输出

```
⚠️  优化中任务（优先处理）

【task_001】实现用户登录API
  状态: 🟡 需要优化 (优化轮次: 2/7)
  
  ❌ 质量问题:
    • 测试失败: test_login_failed
  
  💡 建议:
    1. 检查密码验证逻辑 (tests/test_auth.py:45)
    2. 优化响应性能 (src/api/login.py:120)
  
  📂 相关文件:
    • src/api/login.py
    • tests/test_auth.py
```

### lra show 输出

```
## 🔄 Ralph Loop 状态

当前轮次: 2/7
已优化次数: 1次

### 质量检查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 测试通过 | ❌ | test_login_failed 失败 |
| Lint检查 | ✅ | 通过 |
| 验收标准 | ⚠️ | 2/3 通过 |
| 性能检查 | ⚠️ | 响应时间 800ms |

综合评分: 60/100 (需要优化)

### ❌ 失败的检查项

**测试失败**
- 文件: tests/test_auth.py:45
- 错误: AssertionError: Expected 401, got 200
- 建议: 检查密码验证逻辑

### 📊 优化历史

**优化轮次 1/7**
- 时间: 2026-03-05 10:30:00
- 改动: 实现基础登录功能
- 结果: 测试失败

---

## 💡 下一步操作

1. 查看任务文件: `cat .long-run-agent/tasks/task_001.md`
2. 检查相关代码: `cat src/api/login.py`
3. 运行失败测试: `pytest tests/test_auth.py::test_login_failed -v`
4. 修复问题
5. 提交优化: `lra set task_001 completed`
```

---

## 🛠️ 开发者接口

### Python API

```python
from lra.ralph_loop import RalphLoopController
from lra.ralph_config import RalphConfig
from lra.quality_checker import QualityChecker

# 创建控制器
controller = RalphLoopController(max_iterations=7)

# 检查是否继续循环
should_continue, reason = controller.should_continue_loop()

# 检查任务完成状态
is_complete, details = controller.check_completion(task_id)

# 检测代码改动
has_changes = controller.detect_code_changes()

# 处理错误
action = controller.handle_error(error)

# 生成优化提示
prompt = controller.generate_optimization_prompt(task_id)
```

### 配置读取

```python
from lra.ralph_config import RalphConfig

config = RalphConfig()

# 获取配置项
max_iterations = config.get("ralph.optimization.max_iterations")  # 7
no_change_threshold = config.get("ralph.optimization.no_change_threshold")  # 3
```

### 质量检查

```python
from lra.quality_checker import QualityChecker

checker = QualityChecker()

# 按模板检查质量
result = checker.check_quality_by_template("task_001", "code-module")

# 获取优化建议
hints = checker.generate_optimization_hints("task_001")

# 计算质量评分
score = checker.calculate_quality_score(result["checks"])

# 获取失败的检查项
failed = checker.get_failed_checks("task_001")
```

---

## 📁 文件结构

```
.long-run-agent/
├── ralph_config.yaml          # 全局配置
├── memory/                     # 状态和日志
│   ├── ralph_state.json       # Ralph 状态
│   ├── ralph_loop.log         # 循环日志
│   ├── errors.log             # 错误日志
│   └── lessons_learned.md     # 经验教训
├── templates/                  # 模板配置
│   ├── code-module.yaml       # 包含 ralph 字段
│   ├── novel-chapter.yaml
│   ├── data-pipeline.yaml
│   ├── doc-update.yaml
│   └── task.yaml
└── tasks/                      # 任务文件
    └── task_001.md            # 包含优化提示

lra/
├── ralph_loop.py              # 核心控制器
├── ralph_config.py            # 配置管理
├── quality_checker.py         # 质量检查（已增强）
└── task_manager.py            # 任务管理（已扩展）
```

---

## 🎯 最佳实践

### Agent 工作流

1. **查看上下文**：`lra context` - 了解优化任务
2. **查看详情**：`lra show <task_id>` - 查看具体问题
3. **查看任务文件**：包含优化标记和建议
4. **修复问题**：根据提示修复
5. **提交优化**：`lra set <task_id> completed`

### 避免偷懒

- ✅ 任务文件明确标记"需要优化"
- ✅ 显示具体问题列表
- ✅ 提供文件路径和修复建议
- ✅ 自动记录优化历史

### 错误处理

- **前3次错误**：尝试修复
- **3次后仍失败**：自动回滚
- **回滚3次后仍失败**：停止，等待人工介入

---

## 📚 参考资料

- [Ralph Loop 设计方案](./RALPH_LOOP_DESIGN.md)
- [质量检查器文档](./docs/quality_checker_v2.md)
- [任务管理器扩展](./RALPH_LOOP_USAGE.md)
- [集成测试](./test_ralph_loop_integration.py)

---

**版本**: v1.0  
**最后更新**: 2026-03-05  
**作者**: Ralph Loop Team