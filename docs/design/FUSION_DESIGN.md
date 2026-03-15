# LRA + Spec-Kit 融合设计

## 🎯 愿景

将 **long-run-agent (LRA)** 的任务驱动迭代优化能力，与 **spec-kit** 的规范驱动开发理念深度融合，构建"**规范驱动 + 任务执行 + 质量保障**"的完整AI Agent开发框架。

## 📊 设计哲学对比

### 当前理念

| 维度 | LRA | Spec-Kit |
|------|-----|----------|
| **核心真理** | 任务状态 | 规范文档 |
| **驱动方式** | 任务驱动 | 规范驱动 |
| **质量保障** | Ralph Loop（后验迭代） | Constitution Gates（前置门禁） |
| **约束机制** | 模板结构化 | 模板强制约束 + 反模式检测 |
| **工作流** | 命令式CLI | Slash Commands + 链式建议 |

### 融合后理念

```
规范 (Constitution) → 任务 (Tasks) → 执行 (Execution) → 验证 (Gates) → 迭代 (Ralph Loop)
     ↑                                                              ↓
     └──────────── 反馈闭环 (Feedback Loop) ────────────────────────┘
```

**关键创新：**
- **规范先行**：Constitution定义项目不可协商原则
- **任务驱动**：保持LRA的任务管理优势
- **前置约束**：质量门禁在完成前强制检查
- **后验迭代**：Ralph Loop处理复杂问题
- **持续改进**：反馈闭环优化规范和任务

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                   Constitution Layer                     │
│  (项目宪法 - 定义不可协商原则和质量标准)                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Quality Gates Layer                   │
│  (质量门禁 - 多阶段前置约束和验证)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Pre-Task │→ │ Pre-Comp │→ │ Pre-Iter │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Task Management Layer                 │
│  (任务管理 - LRA核心功能)                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Create  │→ │  Update  │→ │  Query   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Ralph Loop Layer                      │
│  (迭代优化 - 处理复杂质量问题)                           │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │规划  │→│执行  │→│检查  │→│改进  │               │
│  └──────┘  └──────┘  └──────┘  └──────┘               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Template Layer                        │
│  (模板增强 - 强制证据 + 反模式检测)                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Slash Commands Layer                  │
│  (命令体系 - 标准化交互 + 链式建议)                      │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. Constitution Manager（宪法管理器）

**职责：** 管理项目的不可协商原则和质量标准

**关键特性：**
- 三层原则：NON_NEGOTIABLE（不可协商）、MANDATORY（强制）、CONFIGURABLE（可配置）
- 原则验证：自动检查任务是否符合原则
- 模板门禁：为不同模板定义特定门禁

**核心接口：**
```python
class ConstitutionManager:
    def validate_principle(principle_id: str, context: Dict) -> ValidationResult
    def get_gates_for_stage(stage: str, template: str) -> List[Gate]
    def get_non_negotiable_principles() -> List[Principle]
```

#### 2. Quality Gate Manager（质量门禁管理器）

**职责：** 在关键节点执行前置约束检查

**门禁阶段：**
- `pre_task_creation`: 任务创建前
- `pre_completion`: 任务完成前
- `pre_ralph_iteration`: Ralph迭代前

**门禁类型：**
- `REQUIRED`: 必须通过，否则阻塞
- `RECOMMENDED`: 建议通过，不阻塞但警告
- `CONDITIONAL`: 条件性，根据上下文决定

**核心接口：**
```python
class QualityGateManager:
    def run_gates(stage: str, context: Dict) -> GateResult
    def evaluate_gate(gate: Gate, context: Dict) -> GateEvaluation
    def can_complete_early(task_id: str) -> Tuple[bool, Dict]
```

#### 3. Enhanced Ralph Loop（增强版Ralph循环）

**职责：** 将质量门禁嵌入迭代循环

**改进点：**
- 迭代前门禁检查
- 完成门禁验证
- 提前完成支持
- 卡住检测和恢复

**核心接口：**
```python
class EnhancedRalphLoop:
    def run_iteration(task_id: str, iteration: int) -> IterationResult
    def check_stuck_detection(task_id: str) -> bool
    def suggest_next_action(task_id: str) -> str
```

#### 4. Enhanced Template Manager（增强版模板管理器）

**职责：** 模板驱动的质量约束

**新增特性：**
- 必需证据字段
- 完成检查清单
- 反模式自动检测
- 模板验证器

**核心接口：**
```python
class EnhancedTemplateManager:
    def validate_template_completion(task_id: str) -> ValidationResult
    def detect_anti_patterns(content: str) -> List[AntiPattern]
    def check_required_evidence(task_id: str) -> List[MissingEvidence]
```

#### 5. Command Loader（命令加载器）

**职责：** Slash Commands体系

**特性：**
- YAML定义命令规格
- 自动生成帮助文档
- 链式工作流建议
- 前后置钩子

**核心接口：**
```python
class CommandLoader:
    def load_commands() -> Dict[str, CommandSpec]
    def generate_help(command_name: str) -> str
    def suggest_next_steps(command_name: str, context: Dict) -> List[Suggestion]
```

## 🔄 工作流程设计

### 传统LRA流程

```
创建任务 → 认领 → 执行 → 完成 → 质量检查 → (失败) → 优化 → 完成
```

**问题：** 质量检查是后验的，可能导致多次无效迭代

### 融合后流程

```
┌─────────────────────────────────────────────────────────┐
│ 1. Constitution定义原则                                  │
│    ↓                                                     │
│ 2. 任务创建 (pre_task_creation gates检查)               │
│    ↓                                                     │
│ 3. 任务认领                                              │
│    ↓                                                     │
│ 4. 任务执行                                              │
│    ↓                                                     │
│ 5. 提交完成 (pre_completion gates检查)                  │
│    ↓                                                     │
│    ┌─ 全部通过 ──────────────→ 真正完成 ✓              │
│    │                                                      │
│    └─ 部分失败 ──→ Ralph Loop迭代                        │
│                      ↓                                    │
│                   pre_ralph_iteration gates检查          │
│                      ↓                                    │
│                   执行优化                                │
│                      ↓                                    │
│                   再次检查gates                           │
│                      ↓                                    │
│                   [循环或完成]                            │
└─────────────────────────────────────────────────────────┘
```

### 详细流程示例

#### 场景：创建代码模块任务

```bash
# Step 1: Constitution已定义质量原则
# .long-run-agent/constitution.yaml
core_principles:
  - id: "no_broken_tests"
    type: "NON_NEGOTIABLE"
    gates:
      - type: "command"
        command: "pytest tests/"
        expected: "exit_code == 0"

# Step 2: 创建任务（自动触发pre_task_creation gates）
$ lra create "实现用户登录" --template code-module
✓ 系统预检通过
✓ 依赖检查通过
✓ 任务创建成功: task_001

建议下一步:
  • 立即认领: lra claim task_001
  • 查看详情: lra show task_001

# Step 3: 认领任务
$ lra claim task_001
✓ 任务已认领

# Step 4: 执行任务
# ... 编写代码和测试 ...

# Step 5: 提交完成（触发pre_completion gates）
$ lra set task_001 completed

⚠️  质量门禁检查中...

门禁结果:
  ✗ test_gate: 测试未通过 (1 failed)
  ✓ evidence_gate: 证据完整
  ✓ acceptance_gate: 验收标准满足

❌ 完成失败 - 门禁未通过

💡 问题详情:
  - test_gate: test_login.py::test_invalid_password FAILED

🔧 建议操作:
  1. 查看测试失败详情
  2. 修复测试问题
  3. 重新运行测试

当前状态: optimizing (Ralph Loop 迭代 1/7)

# Step 6: Ralph Loop迭代
$ lra show task_001

## 🔄 Ralph Loop 状态

当前轮次: 1/7
已优化次数: 0次

### 质量检查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 测试通过 | ❌ | 1 failed |
| Lint检查 | ⏳ | 未检查 |
| 验收标准 | ✅ | 满足 |

╔═══════════════════════════════════════════════════════════╗
║                     🎯 迭代阶段引导                   ║
╠═══════════════════════════════════════════════════════════╣
║  当前迭代: 1/7                                        ║
║  阶段名称: 问题修复                                   ║
║                                                           ║
║  📌 本次重点:                                         ║
║     • 修复测试失败                                     ║
║     • 确保所有测试通过                                ║
║                                                           ║
║  ⏭️  可跳过:                                          ║
║     • 性能优化                                         ║
║     • 代码重构                                         ║
╚═══════════════════════════════════════════════════════════╝

# Step 7: 修复后再次提交
$ lra set task_001 completed

⚠️  质量门禁检查中...

门禁结果:
  ✓ test_gate: 测试通过 (5 passed)
  ✓ evidence_gate: 证据完整
  ✓ acceptance_gate: 验收标准满足

✅ 所有门禁通过！

🎉 恭喜！任务完成（迭代 1/7）
```

## 🎨 设计模式

### 1. 责任链模式（Quality Gates）

```python
# 门禁按顺序执行，任一门禁失败可中断流程
class QualityGateChain:
    def __init__(self, gates: List[Gate]):
        self.gates = gates
    
    def execute(self, context: Dict) -> GateResult:
        result = GateResult()
        for gate in self.gates:
            if not gate.check(context):
                if gate.required:
                    result.blocked = True
                    result.add_failure(gate)
                    break
                else:
                    result.add_warning(gate)
        return result
```

### 2. 策略模式（Principle Types）

```python
# 不同类型的原则使用不同的验证策略
class PrincipleValidator:
    validators = {
        "NON_NEGOTIABLE": NonNegotiableValidator(),
        "MANDATORY": MandatoryValidator(),
        "CONFIGURABLE": ConfigurableValidator(),
    }
    
    def validate(self, principle: Principle, context: Dict):
        validator = self.validators[principle.type]
        return validator.validate(principle, context)
```

### 3. 观察者模式（Hooks）

```python
# 生命周期钩子，扩展点
class HookManager:
    def register_hook(self, event: str, hook: Hook):
        self.hooks[event].append(hook)
    
    def trigger(self, event: str, context: Dict):
        for hook in self.hooks.get(event, []):
            if hook.should_execute(context):
                hook.execute(context)
```

### 4. 模板方法模式（Ralph Loop）

```python
# 迭代流程固定，具体检查可定制
class RalphLoopTemplate:
    def run_iteration(self, task_id: str):
        # 固定流程
        self.pre_check(task_id)      # 前置检查
        self.execute(task_id)        # 执行任务
        result = self.validate(task_id)  # 验证结果
        self.post_process(task_id, result)  # 后处理
        
        # 可定制部分
        self.custom_iteration_logic(task_id)
```

## 📦 数据结构设计

### Constitution配置结构

```yaml
# .long-run-agent/constitution.yaml
schema_version: "1.0"

project:
  name: string
  description: string
  ratified: datetime
  version: string

core_principles:
  - id: string
    type: enum[NON_NEGOTIABLE, MANDATORY, CONFIGURABLE]
    name: string
    description: string
    enabled: boolean  # 仅CONFIGURABLE类型有效
    gates:
      - type: enum[command, field_exists, custom]
        name: string
        required: boolean
        weight: float  # 0.0-1.0
        config: object  # 门禁特定配置

template_gates:
  <template_name>:
    pre_task_creation:
      - gate: string
        config: object
    pre_completion:
      - gate: string
        config: object

amendments:
  - id: string
    date: datetime
    description: string
    changes: object
```

### Quality Gate结构

```python
@dataclass
class Gate:
    id: str
    name: str
    type: str  # REQUIRED, RECOMMENDED, CONDITIONAL
    stage: str  # pre_task_creation, pre_completion, pre_ralph_iteration
    check: Callable[[Dict], bool]
    weight: float = 1.0
    description: str = ""
    config: Dict = field(default_factory=dict)

@dataclass
class GateResult:
    passed: bool = True
    blocked: bool = False
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 1.0  # 加权得分
```

### Ralph Loop增强结构

```python
@dataclass
class EnhancedRalphState:
    iteration: int
    max_iterations: int
    stage: str  # 问题修复, 质量提升, 优化改进, 验证测试
    
    # 门禁历史
    gate_history: List[GateResult]
    
    # 质量检查结果
    quality_checks: Dict[str, CheckResult]
    
    # 问题列表
    issues: List[Issue]
    
    # 改进建议
    suggestions: List[Suggestion]
    
    # 卡住检测
    stuck_count: int  # 同一阶段失败次数
    is_stuck: bool
    
    # 提前完成标记
    can_complete_early: bool
```

## 🔌 扩展性设计

### 1. 自定义门禁

```python
# 用户可自定义门禁类型
class CustomGate(Gate):
    def __init__(self, check_func: Callable, **kwargs):
        super().__init__(**kwargs)
        self.check_func = check_func
    
    def evaluate(self, context: Dict) -> bool:
        return self.check_func(context)

# 注册自定义门禁
@lra.gate("my_custom_gate")
def my_gate_check(context: Dict) -> bool:
    # 自定义逻辑
    return True
```

### 2. 自定义原则

```python
# 用户可定义新原则类型
class CustomPrinciple(Principle):
    def validate(self, context: Dict) -> ValidationResult:
        # 自定义验证逻辑
        pass

# 注册自定义原则
lra.register_principle_type("CUSTOM", CustomPrinciple)
```

### 3. 自定义模板验证器

```python
# 用户可为模板添加验证器
@lra.template_validator("code-module")
def validate_code_module(content: str) -> ValidationResult:
    # 自定义验证逻辑
    pass
```

### 4. Extension系统

```yaml
# .long-run-agent/extensions.yml
extensions:
  my-extension:
    enabled: true
    hooks:
      after_task_complete:
        command: "my-command"
        optional: true
```

## 🧪 测试策略

### 单元测试

```python
# 测试Constitution管理器
def test_constitution_validation():
    constitution = ConstitutionManager()
    
    # 测试不可协商原则
    principle = {
        "id": "test_principle",
        "type": "NON_NEGOTIABLE",
        "gates": [...]
    }
    
    result = constitution.validate_principle(principle, context)
    assert result.passed == expected_result

# 测试质量门禁
def test_quality_gates():
    gate_manager = QualityGateManager()
    
    result = gate_manager.run_gates("pre_completion", context)
    assert result.blocked == expected_blocked
```

### 集成测试

```python
# 测试完整工作流
def test_task_workflow_with_gates():
    # 1. 创建Constitution
    # 2. 创建任务
    # 3. 提交完成
    # 4. 验证门禁
    # 5. Ralph Loop迭代
    # 6. 最终完成
    pass
```

### 端到端测试

```bash
# 测试真实场景
$ lra init --name "Test Project"
$ lra create "Test Task" --template code-module
$ lra set task_001 completed
# 验证门禁触发
# 验证Ralph Loop启动
# 验证最终完成
```

## 📊 性能考量

### 1. 门禁执行优化

```python
# 并行执行独立门禁
async def run_gates_parallel(gates: List[Gate], context: Dict):
    tasks = [gate.check_async(context) for gate in gates]
    results = await asyncio.gather(*tasks)
    return results
```

### 2. 缓存机制

```python
# 缓存Constitution配置
@lru_cache(maxsize=128)
def get_constitution() -> Constitution:
    return load_constitution()

# 缓存门禁结果（相同上下文）
@cache(ttl=300)
def run_gates(stage: str, context_hash: str) -> GateResult:
    pass
```

### 3. 懒加载

```python
# 按需加载模板验证器
class TemplateManager:
    @property
    def validators(self):
        if self._validators is None:
            self._validators = self._load_validators()
        return self._validators
```

## 🛡️ 安全考量

### 1. Constitution不可篡改

```python
# Constitution文件只读权限
def load_constitution():
    path = Config.get_constitution_path()
    if not os.access(path, os.R_OK):
        raise PermissionError("Constitution file not readable")
    
    # 验证文件完整性
    verify_file_integrity(path)
```

### 2. 门禁命令注入防护

```python
# 沙箱执行命令
def execute_gate_command(command: str) -> Result:
    # 白名单允许的命令
    ALLOWED_COMMANDS = ["pytest", "ruff", "eslint"]
    
    cmd_name = command.split()[0]
    if cmd_name not in ALLOWED_COMMANDS:
        raise SecurityError(f"Command not allowed: {cmd_name}")
    
    # 沙箱执行
    return subprocess.run(command, sandbox=True)
```

### 3. 敏感信息保护

```python
# 脱敏日志输出
def log_gate_result(result: GateResult):
    safe_result = sanitize_result(result)
    logger.info(safe_result)

def sanitize_result(result: GateResult) -> Dict:
    # 移除敏感信息
    # 密码、token等
    pass
```

## 🚀 迁移策略

### 阶段1: 无缝引入（向后兼容）

```python
# Constitution可选，没有则使用默认
class TaskManager:
    def __init__(self):
        self.constitution = self._load_constitution_or_default()
    
    def _load_constitution_or_default(self):
        path = Config.get_constitution_path()
        if not path.exists():
            return self._get_default_constitution()
        return load_constitution(path)
```

### 阶段2: 渐进增强

```python
# 新功能可选启用
class TaskManager:
    def update_status(self, task_id: str, status: str, **kwargs):
        # 原有逻辑
        ...
        
        # 新增：门禁检查（可选）
        if kwargs.get("enable_gates", False):
            self._check_gates(task_id, status)
```

### 阶段3: 全面集成

```python
# 新功能成为默认
class TaskManager:
    def update_status(self, task_id: str, status: str, **kwargs):
        # 门禁检查默认启用
        if not kwargs.get("skip_gates", False):
            self._check_gates(task_id, status)
```

## 📈 成功指标

### 定量指标

- **迭代次数减少**：平均Ralph Loop迭代次数降低 30%
- **质量提升**：任务一次性完成率提升 40%
- **效率提升**：门禁前置检查减少无效工作 50%
- **用户满意度**：开发者体验评分 > 4.5/5

### 定性指标

- **理念融合**：规范驱动和任务驱动无缝结合
- **易用性**：新功能学习曲线平缓
- **灵活性**：可配置、可扩展、可定制
- **可靠性**：向后兼容，平滑迁移

## 🎯 下一步行动

### 短期（1-2周）

1. ✅ 创建设计文档
2. ⏳ 实现Constitution核心代码
3. ⏳ 实现质量门禁核心代码
4. ⏳ 编写单元测试

### 中期（3-4周）

1. ⏳ 与Ralph Loop深度集成
2. ⏳ 增强模板系统
3. ⏳ 实现Slash Commands
4. ⏳ 编写集成测试

### 长期（5-8周）

1. ⏳ Extension扩展系统
2. ⏳ 文档和教程
3. ⏳ 示例项目
4. ⏳ 社区推广

## 📚 参考资料

- [Spec-Kit官方文档](https://github.com/github/spec-kit)
- [LRA文档](./README.md)
- [Ralph Loop设计](./RALPH_LOOP_GUIDE.md)
- [质量保障系统](./QUALITY_CHECKER_UPDATE.md)

---

**文档版本**: v1.0  
**最后更新**: 2024-03-09  
**作者**: LRA Team