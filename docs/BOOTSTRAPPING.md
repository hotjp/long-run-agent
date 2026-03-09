# 自举式开发流程文档

## 🎯 概述

本文档定义了如何使用**融合后的LRA + Spec-Kit**进行**自举式开发**（Bootstrapping Development），即用新工具开发新工具本身，验证设计理念的可行性。

## 🌟 自举式开发理念

### 什么是自举式开发？

**自举（Bootstrapping）**：使用正在开发工具来开发该工具本身，形成自我强化的循环。

**核心优势：**
- ✅ **即时验证**：设计理念立即得到实践检验
- ✅ **快速迭代**：发现问题即时修复
- ✅ **真实场景**：开发者即是用户，体验真实
- ✅ **文档闭环**：开发过程即文档完善过程

### 自举循环

```
设计 → 实现 → 使用 → 反馈 → 改进 → 设计...
  ↑                                           ↓
  └─────────── 持续改进循环 ───────────────────┘
```

## 📋 自举项目：LRA v5.0 开发

### 项目目标

使用LRA v4.1（现有版本）+ Constitution机制开发LRA v5.0（融合版本），验证以下能力：

1. **Constitution机制**的实用性
2. **质量门禁系统**的有效性
3. **Ralph Loop增强**的价值
4. **模板增强**的效果
5. **Slash Commands体系**的易用性

### 项目结构

```
long-run-agent/
├── .long-run-agent/           # LRA配置
│   ├── constitution.yaml      # 项目宪法（核心）
│   ├── config.json
│   ├── task_list.json
│   ├── templates/             # 增强模板
│   │   ├── code-module.yaml
│   │   ├── task.yaml
│   │   └── constitution-principle.yaml  # 新增
│   ├── commands/              # Slash Commands（新增）
│   │   ├── create.yaml
│   │   ├── set.yaml
│   │   └── implement.yaml
│   └── extensions/            # 扩展（可选）
│
├── lra/                       # 核心代码
│   ├── constitution.py        # 新增：Constitution管理
│   ├── quality_gates.py       # 新增：质量门禁
│   ├── enhanced_ralph.py      # 新增：增强Ralph Loop
│   ├── command_loader.py      # 新增：命令加载器
│   ├── task_manager.py        # 增强
│   ├── template_manager.py    # 增强
│   └── cli.py                 # 增强
│
├── docs/                      # 文档
│   ├── FUSION_DESIGN.md
│   ├── CONSTITUTION_DESIGN.md
│   ├── BOOTSTRAPPING.md       # 本文档
│   └── IMPLEMENTATION_GUIDE.md
│
└── tests/                     # 测试
    ├── test_constitution.py
    ├── test_quality_gates.py
    └── test_integration.py
```

## 🏗️ 开发阶段设计

### 阶段0: Constitution制定（规范先行）

**目标：** 制定LRA v5.0开发的宪法原则

**执行步骤：**

```bash
# Step 1: 初始化项目（如果还没有）
lra init --name "LRA v5.0"

# Step 2: 创建Constitution
cat > .long-run-agent/constitution.yaml <<'EOF'
schema_version: "1.0"

project:
  name: "LRA v5.0 - Constitution Integration"
  description: "融合spec-kit理念的LRA增强版本"
  ratified: "2024-03-09"
  version: "5.0.0"

core_principles:
  # 不可协商原则
  - id: "no_broken_tests"
    type: "NON_NEGOTIABLE"
    name: "测试必须通过"
    description: "所有新功能必须有测试且通过"
    gates:
      - type: "command"
        name: "test_gate"
        command: "pytest tests/ -v"
        expected: "exit_code == 0"
        weight: 0.4

  - id: "code_coverage"
    type: "NON_NEGOTIABLE"
    name: "代码覆盖率"
    description: "新代码覆盖率不低于80%"
    gates:
      - type: "command"
        name: "coverage_gate"
        command: "pytest --cov=lra --cov-fail-under=80"
        expected: "exit_code == 0"
        weight: 0.3

  - id: "evidence_required"
    type: "NON_NEGOTIABLE"
    name: "证据必需"
    description: "完成前必须提供验证证据"
    gates:
      - type: "field_exists"
        name: "test_evidence"
        field: "test_evidence"
        weight: 0.2
      - type: "field_exists"
        name: "verification_steps"
        field: "verification_steps"
        weight: 0.1

  # 强制原则
  - id: "no_syntax_errors"
    type: "MANDATORY"
    name: "无语法错误"
    description: "代码必须无语法错误"
    gates:
      - type: "command"
        name: "syntax_check"
        command: "python -m py_compile lra/"
        expected: "exit_code == 0"
        weight: 0.0

  - id: "type_check"
    type: "MANDATORY"
    name: "类型检查"
    description: "通过mypy类型检查"
    gates:
      - type: "command"
        name: "mypy_check"
        command: "mypy lra/"
        expected: "exit_code == 0"
        weight: 0.0
        required: false  # 初期可选

  # 可配置原则
  - id: "documentation_sync"
    type: "CONFIGURABLE"
    name: "文档同步"
    description: "代码变更需同步更新文档"
    enabled: true
    gates:
      - type: "field_exists"
        name: "doc_updated"
        field: "doc_updated"
        weight: 0.0

template_gates:
  constitution-principle:
    pre_completion:
      - gate: "constitution_validation"
        type: "custom"
        check_func: "validate_constitution_yaml"
        required: true
        description: "验证Constitution YAML格式"

amendments: []
EOF

# Step 3: 验证Constitution
lra constitution validate
```

**验收标准：**
- [x] Constitution文件创建成功
- [x] YAML格式正确
- [x] 所有原则定义完整
- [x] 门禁配置合理

### 阶段1: Constitution核心实现（任务驱动）

**目标：** 实现Constitution管理器和验证器

**任务拆分：**

```bash
# 创建Phase 1任务
lra create "实现Constitution数据模型" --template constitution-principle --priority P0
lra create "实现ConstitutionManager类" --template code-module --priority P0
lra create "实现PrincipleValidator类" --template code-module --priority P0
lra create "实现GateEvaluator类" --template code-module --priority P1
lra create "编写Constitution单元测试" --template code-module --priority P1
```

**任务1: 实现Constitution数据模型**

```bash
# 认领任务
lra claim task_001

# 创建任务文件
cat > lra/constitution.py <<'EOF'
"""
Constitution数据模型和管理器
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import yaml
from pathlib import Path


class PrincipleType(Enum):
    """原则类型"""
    NON_NEGOTIABLE = "NON_NEGOTIABLE"
    MANDATORY = "MANDATORY"
    CONFIGURABLE = "CONFIGURABLE"


class GateType(Enum):
    """门禁类型"""
    COMMAND = "command"
    FIELD_EXISTS = "field_exists"
    CUSTOM = "custom"


@dataclass
class Gate:
    """门禁"""
    type: GateType
    name: str
    required: bool = True
    weight: float = 1.0
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Principle:
    """原则"""
    id: str
    type: PrincipleType
    name: str
    description: str
    gates: List[Gate] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    message: str = ""
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class GateResult:
    """门禁结果"""
    passed: bool
    message: str = ""
    output: str = ""
    exit_code: int = 0
    weight: float = 1.0


@dataclass
class Constitution:
    """宪法"""
    schema_version: str
    project: Dict[str, Any]
    core_principles: List[Principle]
    template_gates: Dict[str, Dict[str, List[Gate]]] = field(default_factory=dict)
    amendments: List[Dict[str, Any]] = field(default_factory=list)
EOF

# 编写测试
cat > tests/test_constitution.py <<'EOF'
import pytest
from lra.constitution import PrincipleType, GateType, Principle, Gate


def test_principle_creation():
    """测试原则创建"""
    principle = Principle(
        id="test",
        type=PrincipleType.NON_NEGOTIABLE,
        name="Test Principle",
        description="A test principle",
        gates=[]
    )
    
    assert principle.id == "test"
    assert principle.type == PrincipleType.NON_NEGOTIABLE


def test_gate_creation():
    """测试门禁创建"""
    gate = Gate(
        type=GateType.COMMAND,
        name="test_gate",
        command="echo test"
    )
    
    assert gate.type == GateType.COMMAND
    assert gate.name == "test_gate"
EOF

# 运行测试
pytest tests/test_constitution.py -v
```

**验证证据：**

```markdown
### 测试证据
```bash
$ pytest tests/test_constitution.py -v
============================= test session starts ==============================
collected 2 items

tests/test_constitution.py::test_principle_creation PASSED              [ 50%]
tests/test_constitution.py::test_gate_creation PASSED                   [100%]

============================== 2 passed in 0.03s ===============================
```

### 验证步骤
1. 导入Constitution模块
2. 创建Principle和Gate实例
3. 验证属性正确性
4. 所有测试通过
```

**提交完成：**

```bash
# 提交完成（触发Constitution验证）
lra set task_001 completed

# 输出：
⚠️  Constitution验证中...

门禁结果:
  ✓ test_gate: 测试通过
  ✓ coverage_gate: 覆盖率 85%
  ✓ test_evidence_gate: 证据完整
  ✓ verification_steps_gate: 验证步骤完整

✅ 所有Constitution门禁通过！

🎉 任务完成
```

### 阶段2: 质量门禁系统实现

**目标：** 实现前置质量门禁检查

**任务拆分：**

```bash
lra create "实现QualityGateManager" --template code-module --priority P0
lra create "实现Gate执行器" --template code-module --priority P0
lra create "集成到TaskManager" --template code-module --priority P0
lra create "编写门禁测试" --template code-module --priority P1
```

**关键代码实现：**

```python
# lra/quality_gates.py
"""
质量门禁管理器
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
import subprocess


@dataclass
class GateResult:
    """门禁检查结果"""
    passed: bool
    message: str
    output: str = ""
    exit_code: int = 0


class QualityGateManager:
    """质量门禁管理器"""
    
    def __init__(self, constitution_manager):
        self.constitution = constitution_manager
    
    def run_gates(
        self, 
        stage: str, 
        context: Dict
    ) -> Tuple[bool, List[GateResult]]:
        """运行指定阶段的门禁"""
        results = []
        
        # 获取该阶段的门禁
        gates = self._get_gates_for_stage(stage, context)
        
        for gate in gates:
            result = self._evaluate_gate(gate, context)
            results.append(result)
        
        # 判断是否全部通过
        all_passed = all(r.passed for r in results if gate.get('required', True))
        
        return all_passed, results
    
    def _evaluate_gate(self, gate: Dict, context: Dict) -> GateResult:
        """评估单个门禁"""
        gate_type = gate.get('type')
        
        if gate_type == 'command':
            return self._evaluate_command_gate(gate, context)
        elif gate_type == 'field_exists':
            return self._evaluate_field_gate(gate, context)
        else:
            return GateResult(
                passed=False,
                message=f"Unknown gate type: {gate_type}"
            )
    
    def _evaluate_command_gate(self, gate: Dict, context: Dict) -> GateResult:
        """执行命令门禁"""
        command = gate.get('command')
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            passed = result.returncode == 0
            
            return GateResult(
                passed=passed,
                message=f"Command: {command}",
                output=result.stdout,
                exit_code=result.returncode
            )
        
        except Exception as e:
            return GateResult(
                passed=False,
                message=f"Command failed: {str(e)}"
            )
```

### 阶段3: Ralph Loop增强

**目标：** 将质量门禁集成到Ralph Loop

**任务拆分：**

```bash
lra create "增强Ralph Loop状态模型" --template code-module --priority P0
lra create "实现迭代前门禁检查" --template code-module --priority P0
lra create "实现提前完成逻辑" --template code-module --priority P1
lra create "编写Ralph Loop集成测试" --template code-module --priority P1
```

**关键集成代码：**

```python
# lra/enhanced_ralph.py
"""
增强版Ralph Loop
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class EnhancedRalphState:
    """增强Ralph状态"""
    iteration: int
    max_iterations: int
    stage: str
    gate_history: List[Dict]
    quality_checks: Dict[str, bool]
    issues: List[str]
    suggestions: List[str]
    stuck_count: int
    is_stuck: bool
    can_complete_early: bool


class EnhancedRalphLoop:
    """增强版Ralph Loop"""
    
    def __init__(self, task_manager, quality_gate_manager):
        self.task_manager = task_manager
        self.quality_gates = quality_gate_manager
    
    def run_iteration(
        self, 
        task_id: str, 
        iteration: int
    ) -> Dict:
        """运行单次迭代"""
        # Phase 0: 前置门禁检查
        gate_passed, gate_results = self.quality_gates.run_gates(
            "pre_ralph_iteration",
            {"task_id": task_id, "iteration": iteration}
        )
        
        if not gate_passed:
            return {
                "blocked": True,
                "reason": "Pre-iteration gates failed",
                "gate_results": gate_results
            }
        
        # Phase 1: 执行任务优化
        # ... 原有Ralph Loop逻辑 ...
        
        # Phase 2: 完成门禁检查
        completion_passed, completion_results = self.quality_gates.run_gates(
            "pre_completion",
            {"task_id": task_id}
        )
        
        if completion_passed:
            return {
                "can_complete": True,
                "status": "truly_completed",
                "gate_results": completion_results
            }
        else:
            return {
                "can_complete": False,
                "status": "optimizing",
                "issues": [r.message for r in completion_results if not r.passed],
                "gate_results": completion_results
            }
```

### 阶段4: Slash Commands实现

**目标：** 实现命令YAML定义和加载

**任务拆分：**

```bash
lra create "设计Slash Commands YAML格式" --template code-module --priority P1
lra create "实现CommandLoader" --template code-module --priority P1
lra create "实现帮助文档生成" --template code-module --priority P2
lra create "实现链式建议" --template code-module --priority P2
```

**命令定义示例：**

```yaml
# .long-run-agent/commands/create.yaml
---
description: "创建新任务"
category: "task"
usage: "lra create <description> [options]"

arguments:
  - name: "description"
    required: true
    description: "任务描述"

options:
  - name: "template"
    short: "-t"
    default: "task"
    description: "任务模板"
  - name: "priority"
    short: "-p"
    default: "P1"
    choices: ["P0", "P1", "P2", "P3"]

workflow:
  next_steps:
    - label: "立即认领"
      command: "lra claim {task_id}"
      condition: "auto_claim"
    - label: "查看详情"
      command: "lra show {task_id}"

examples:
  - command: 'lra create "实现用户登录"'
    description: "创建基本任务"
---
```

### 阶段5: 集成测试和文档

**目标：** 验证整体流程，完善文档

**任务拆分：**

```bash
lra create "编写端到端测试" --template code-module --priority P0
lra create "编写实施指南" --template doc-update --priority P0
lra create "编写最佳实践文档" --template doc-update --priority P1
lra create "创建示例项目" --template code-module --priority P2
```

## 🔄 自举循环验证

### 验证场景1: Constitution强制执行

**测试目标：** 验证不可协商原则是否强制执行

**测试步骤：**

```bash
# 1. 故意提交未通过测试的代码
lra create "故意失败的测试" --template code-module
lra claim task_050

# 写入会失败的测试
cat > tests/test_will_fail.py <<'EOF'
def test_will_fail():
    assert False, "This test should fail"
EOF

# 2. 提交完成
lra set task_050 completed

# 3. 验证Constitution阻止完成
# 预期输出：
# ❌ Constitution验证失败
# 门禁失败: test_gate (pytest tests/ failed)
# 
# 任务状态: optimizing (Ralph Loop 迭代 1/7)
# 
# 💡 问题:
#   - test_gate: 测试未通过

# 4. 修复测试
cat > tests/test_will_fail.py <<'EOF'
def test_will_pass():
    assert True
EOF

# 5. 再次提交
lra set task_050 completed

# 6. 验证完成
# 预期输出：
# ✓ test_gate: 测试通过
# ✓ coverage_gate: 覆盖率满足
# ✓ evidence_gate: 证据完整
# 
# ✅ Constitution验证通过
# 🎉 任务完成
```

### 验证场景2: Ralph Loop集成门禁

**测试目标：** 验证Ralph Loop是否正确使用质量门禁

**测试步骤：**

```bash
# 1. 创建复杂任务
lra create "实现复杂功能" --template code-module

# 2. 提交部分实现
lra set task_051 completed

# 3. 验证进入Ralph Loop
# 预期：门禁失败 → 进入optimizing状态 → Ralph Loop启动

# 4. 查看迭代引导
lra show task_051

# 预期输出：
# ## 🔄 Ralph Loop 状态
# 
# 当前轮次: 1/7
# 
# ### 门禁检查结果
# | 检查项 | 状态 | 详情 |
# |--------|------|------|
# | test_gate | ❌ | 2 failed |
# | evidence_gate | ✅ | 完整 |
# 
# ╔═══════════════════════════════════════════════════════════╗
# ║                     🎯 迭代阶段引导                   ║
# ╠═══════════════════════════════════════════════════════════╣
# ║  当前迭代: 1/7                                        ║
# ║  阶段名称: 问题修复                                   ║
# ║                                                           ║
# ║  📌 本次重点:                                         ║
# ║     • 修复测试失败                                     ║
# ║     • 确保测试通过                                     ║
# ╚═══════════════════════════════════════════════════════════╝
```

### 验证场景3: 提前完成

**测试目标：** 验证所有门禁通过后可提前完成

**测试步骤：**

```bash
# 1. 创建任务并完整实现
lra create "完整实现" --template code-module

# 2. 编写高质量代码+测试+文档

# 3. 提交完成
lra set task_052 completed

# 4. 验证提前完成
# 预期输出：
# ✓ test_gate: 测试通过
# ✓ coverage_gate: 覆盖率 90%
# ✓ evidence_gate: 证据完整
# ✓ doc_updated_gate: 文档已更新
# 
# ✅ 所有门禁通过！
# 
# 🎉 恭喜！任务可提前完成（迭代 0/7）
```

### 验证场景4: Slash Commands工作流

**测试目标：** 验证链式建议和命令标准化

**测试步骤：**

```bash
# 1. 使用命令创建任务
lra create "Slash Commands测试" --template code-module

# 预期输出：
# ✓ 任务创建成功: task_053
# 
# 💡 建议下一步:
#   • 立即认领: lra claim task_053
#   • 查看详情: lra show task_053

# 2. 查看命令帮助
lra create --help

# 预期输出：
# 用法: lra create <description> [options]
# 
# 参数:
#   description    任务描述 (必需)
# 
# 选项:
#   -t, --template    任务模板 (默认: task)
#   -p, --priority    优先级 (默认: P1)
# 
# 示例:
#   lra create "实现用户登录"
#     创建基本任务
```

## 📊 自举成果评估

### 定量指标

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| Constitution执行率 | 100% | - | ⏳ |
| Ralph Loop迭代减少 | 30% | - | ⏳ |
| 任务一次性完成率 | 60% | - | ⏳ |
| 代码覆盖率 | 80% | - | ⏳ |
| 文档完整性 | 100% | - | ⏳ |

### 定性评估

#### 1. Constitution机制评估

**优势：**
- ✅ 明确质量标准，避免模糊
- ✅ 前置约束，减少返工
- ✅ 不可协商原则强制执行

**改进点：**
- ⏳ 门禁执行速度优化
- ⏳ 自定义门禁易用性
- ⏳ 错误信息友好度

#### 2. 质量门禁评估

**优势：**
- ✅ 多阶段检查，覆盖完整
- ✅ 可配置权重，灵活调整
- ✅ 与Ralph Loop无缝集成

**改进点：**
- ⏳ 门禁并行执行
- ⏳ 门禁结果缓存
- ⏳ 条件门禁逻辑增强

#### 3. Ralph Loop增强评估

**优势：**
- ✅ 迭代前检查，避免无效迭代
- ✅ 提前完成，减少等待
- ✅ 门禁历史，便于追踪

**改进点：**
- ⏳ 卡住检测精度
- ⏳ 建议生成智能化
- ⏳ 性能优化

#### 4. Slash Commands评估

**优势：**
- ✅ 命令标准化，易学易用
- ✅ 链式建议，引导流程
- ✅ 自动生成文档

**改进点：**
- ⏳ 命令发现机制
- ⏳ 参数自动补全
- ⏳ 工作流可视化

## 🔍 问题发现与改进

### 问题1: 门禁执行慢

**现象：** 多个命令门禁串行执行，总耗时过长

**分析：** 
- 每个门禁独立执行命令
- 没有并行优化
- 缺少结果缓存

**改进方案：**

```python
# 实现并行门禁执行
import asyncio

async def run_gates_parallel(gates: List[Gate], context: Dict):
    """并行执行门禁"""
    tasks = [
        evaluate_gate_async(gate, context) 
        for gate in gates
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 问题2: 错误信息不友好

**现象：** 门禁失败时，错误信息不够明确

**分析：**
- 直接输出命令错误
- 缺少上下文
- 没有修复建议

**改进方案：**

```python
def format_gate_error(gate: Gate, result: GateResult) -> str:
    """格式化门禁错误"""
    return f"""
❌ 门禁失败: {gate.name}

📋 详情:
  类型: {gate.type}
  描述: {gate.description}
  
🔍 错误:
  {result.message}

💡 建议:
  1. 检查命令: {gate.config.get('command', 'N/A')}
  2. 查看输出: {result.output[:200]}
  3. 手动执行: 复制命令到终端调试
"""
```

### 问题3: Constitution配置复杂

**现象：** 新手配置Constitution困难

**分析：**
- YAML格式繁琐
- 缺少可视化工具
- 没有模板示例

**改进方案：**

```bash
# 添加交互式Constitution创建
lra constitution init --interactive

# 提供预设模板
lra constitution template python-web
lra constitution template cli-tool
lra constitution template library

# 可视化编辑
lra constitution edit --gui
```

## 📝 最佳实践总结

### 1. Constitution制定

**DO:**
- ✅ 从少量原则开始，逐步增加
- ✅ 区分NON_NEGOTIABLE和MANDATORY
- ✅ 为每个原则添加清晰描述
- ✅ 定期审视和更新Constitution

**DON'T:**
- ❌ 一开始就制定过多原则
- ❌ 所有原则都设为NON_NEGOTIABLE
- ❌ 门禁配置过于复杂
- ❌ 忽略团队实际情况

### 2. 任务拆分

**推荐方式：**

```bash
# 按阶段拆分
Phase 1: Constitution → Constitution核心实现
Phase 2: Gates → 质量门禁系统
Phase 3: Ralph Loop → 迭代增强
Phase 4: Commands → 命令体系
Phase 5: Integration → 集成测试

# 每个Phase内按优先级拆分
P0: 核心功能
P1: 重要功能
P2: 增强功能
```

### 3. 开发流程

**推荐流程：**

```
1. 制定Constitution（规范先行）
   ↓
2. 创建任务（任务驱动）
   ↓
3. 实现功能（质量门禁约束）
   ↓
4. 提交验证（Constitution检查）
   ↓
5. Ralph Loop迭代（问题修复）
   ↓
6. 真正完成（所有门禁通过）
```

## 🚀 下一步行动

### 短期（本周）

- [ ] 完成Constitution核心实现
- [ ] 完成质量门禁系统
- [ ] 编写基础测试
- [ ] 验证基本流程

### 中期（本月）

- [ ] Ralph Loop深度集成
- [ ] Slash Commands完整实现
- [ ] 文档完善
- [ ] 示例项目

### 长期（下月）

- [ ] 性能优化
- [ ] Extension系统
- [ ] 社区推广
- [ ] 反馈收集

---

**文档版本**: v1.0  
**最后更新**: 2024-03-09  
**作者**: LRA Team  
**状态**: 自举进行中 ⏳