# Constitution 机制设计文档

## 📖 概述

Constitution（宪法）是LRA融合spec-kit理念的核心机制，定义项目的**不可协商原则**和**质量标准**，确保所有任务遵循统一的质量基线。

## 🎯 设计目标

### 核心目标

1. **明确质量标准**：显式定义项目的质量红线
2. **前置约束**：在任务完成前强制检查，而非事后验证
3. **分层原则**：区分不可协商、强制、可配置三类原则
4. **可追溯性**：所有质量决策有据可查

### 设计原则

1. **宪法优先**：Constitution是项目的最高准则
2. **不可妥协**：NON_NEGOTIABLE原则不得绕过
3. **灵活可配**：CONFIGURABLE原则支持定制
4. **向后兼容**：没有Constitution时使用默认原则

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                   Constitution File                      │
│              (.long-run-agent/constitution.yaml)        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Constitution Manager                    │
│  • 加载和解析Constitution                               │
│  • 验证原则完整性                                       │
│  • 提供原则查询接口                                     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Principle Types                        │
│  ┌─────────────────┬─────────────────┬──────────────┐  │
│  │ NON_NEGOTIABLE  │   MANDATORY     │ CONFIGURABLE │  │
│  │   (不可协商)    │    (强制)       │   (可配置)   │  │
│  └─────────────────┴─────────────────┴──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      Gate System                         │
│  • 命令门禁                                             │
│  • 字段门禁                                             │
│  • 自定义门禁                                           │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. ConstitutionManager

**职责：** 管理Constitution配置的加载、解析、验证

**核心方法：**

```python
class ConstitutionManager:
    def __init__(self):
        """初始化Constitution管理器"""
        self.constitution_path = Config.get_constitution_path()
        self.constitution = self._load_constitution()
        self._validate_constitution()
    
    def _load_constitution(self) -> Dict:
        """加载Constitution配置"""
        if not self.constitution_path.exists():
            return self._get_default_constitution()
        
        with open(self.constitution_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _validate_constitution(self):
        """验证Constitution配置的完整性和正确性"""
        required_fields = ['schema_version', 'core_principles']
        for field in required_fields:
            if field not in self.constitution:
                raise ValueError(f"Constitution missing required field: {field}")
    
    def get_principle(self, principle_id: str) -> Optional[Dict]:
        """获取指定原则"""
        for principle in self.constitution.get('core_principles', []):
            if principle['id'] == principle_id:
                return principle
        return None
    
    def get_principles_by_type(self, principle_type: str) -> List[Dict]:
        """获取指定类型的所有原则"""
        return [
            p for p in self.constitution.get('core_principles', [])
            if p.get('type') == principle_type
        ]
    
    def get_non_negotiable_principles(self) -> List[Dict]:
        """获取所有不可协商原则"""
        return self.get_principles_by_type('NON_NEGOTIABLE')
    
    def get_template_gates(self, template: str, stage: str) -> List[Dict]:
        """获取模板特定门禁"""
        template_gates = self.constitution.get('template_gates', {})
        return template_gates.get(template, {}).get(stage, [])
```

#### 2. PrincipleValidator

**职责：** 验证任务是否符合原则

**核心方法：**

```python
class PrincipleValidator:
    def __init__(self, constitution_manager: ConstitutionManager):
        self.constitution = constitution_manager
        self.validators = {
            'NON_NEGOTIABLE': self._validate_non_negotiable,
            'MANDATORY': self._validate_mandatory,
            'CONFIGURABLE': self._validate_configurable,
        }
    
    def validate_principle(
        self, 
        principle: Dict, 
        task_id: str, 
        task: Dict
    ) -> ValidationResult:
        """验证单个原则"""
        principle_type = principle.get('type')
        validator = self.validators.get(principle_type)
        
        if not validator:
            return ValidationResult(
                passed=True,
                message=f"Unknown principle type: {principle_type}"
            )
        
        return validator(principle, task_id, task)
    
    def _validate_non_negotiable(
        self, 
        principle: Dict, 
        task_id: str, 
        task: Dict
    ) -> ValidationResult:
        """验证不可协商原则 - 所有门禁必须通过"""
        gates = principle.get('gates', [])
        failures = []
        
        for gate in gates:
            result = self._evaluate_gate(gate, task_id, task)
            if not result.passed:
                failures.append(result.message)
        
        return ValidationResult(
            passed=len(failures) == 0,
            message=f"门禁失败: {failures}" if failures else "通过",
            failures=failures
        )
    
    def _validate_mandatory(
        self, 
        principle: Dict, 
        task_id: str, 
        task: Dict
    ) -> ValidationResult:
        """验证强制原则 - 必需门禁必须通过"""
        gates = principle.get('gates', [])
        failures = []
        
        for gate in gates:
            if gate.get('required', True):
                result = self._evaluate_gate(gate, task_id, task)
                if not result.passed:
                    failures.append(result.message)
        
        return ValidationResult(
            passed=len(failures) == 0,
            message=f"必需门禁失败: {failures}" if failures else "通过",
            failures=failures
        )
    
    def _validate_configurable(
        self, 
        principle: Dict, 
        task_id: str, 
        task: Dict
    ) -> ValidationResult:
        """验证可配置原则 - 根据enabled字段决定"""
        if not principle.get('enabled', False):
            return ValidationResult(passed=True, message="原则未启用")
        
        return self._validate_mandatory(principle, task_id, task)
```

#### 3. GateEvaluator

**职责：** 执行具体的门禁检查

**门禁类型：**

```python
class GateEvaluator:
    def evaluate_gate(self, gate: Dict, task_id: str, task: Dict) -> GateResult:
        """评估单个门禁"""
        gate_type = gate.get('type')
        
        if gate_type == 'command':
            return self._evaluate_command_gate(gate, task_id, task)
        elif gate_type == 'field_exists':
            return self._evaluate_field_gate(gate, task_id, task)
        elif gate_type == 'custom':
            return self._evaluate_custom_gate(gate, task_id, task)
        else:
            return GateResult(
                passed=False,
                message=f"Unknown gate type: {gate_type}"
            )
    
    def _evaluate_command_gate(
        self, 
        gate: Dict, 
        task_id: str, 
        task: Dict
    ) -> GateResult:
        """执行命令门禁"""
        command = gate.get('command')
        expected = gate.get('expected')
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # 评估期望结果
            if expected == 'exit_code == 0':
                passed = result.returncode == 0
            else:
                # 自定义评估逻辑
                passed = self._evaluate_expected(expected, result)
            
            return GateResult(
                passed=passed,
                message=f"命令执行: {command}",
                output=result.stdout,
                exit_code=result.returncode
            )
        
        except subprocess.TimeoutExpired:
            return GateResult(
                passed=False,
                message=f"命令超时: {command}"
            )
        except Exception as e:
            return GateResult(
                passed=False,
                message=f"命令执行失败: {str(e)}"
            )
    
    def _evaluate_field_gate(
        self, 
        gate: Dict, 
        task_id: str, 
        task: Dict
    ) -> GateResult:
        """检查字段是否存在"""
        field = gate.get('field')
        task_file = Config.get_task_path(task_id)
        
        if not task_file.exists():
            return GateResult(
                passed=False,
                message=f"任务文件不存在: {task_id}"
            )
        
        content = task_file.read_text(encoding='utf-8')
        
        # 检查字段是否存在
        if field in content:
            return GateResult(
                passed=True,
                message=f"字段存在: {field}"
            )
        else:
            return GateResult(
                passed=False,
                message=f"字段缺失: {field}"
            )
    
    def _evaluate_custom_gate(
        self, 
        gate: Dict, 
        task_id: str, 
        task: Dict
    ) -> GateResult:
        """执行自定义门禁"""
        check_func = gate.get('check_func')
        
        if not check_func:
            return GateResult(
                passed=False,
                message="自定义门禁缺少check_func"
            )
        
        try:
            result = check_func(task_id, task)
            return GateResult(
                passed=result.get('passed', False),
                message=result.get('message', '')
            )
        except Exception as e:
            return GateResult(
                passed=False,
                message=f"自定义门禁执行失败: {str(e)}"
            )
```

## 📝 数据结构

### Constitution配置结构

```yaml
# .long-run-agent/constitution.yaml
schema_version: "1.0"

project:
  name: "My Project"
  description: "项目描述"
  ratified: "2024-03-09T00:00:00Z"
  version: "1.0.0"

core_principles:
  # 不可协商原则
  - id: "no_broken_tests"
    type: "NON_NEGOTIABLE"
    name: "测试必须通过"
    description: "所有测试必须通过才能标记任务完成"
    gates:
      - type: "command"
        name: "test_gate"
        command: "pytest tests/ -v"
        expected: "exit_code == 0"
        weight: 0.4
        description: "执行测试套件"
  
  - id: "evidence_required"
    type: "NON_NEGOTIABLE"
    name: "证据必需"
    description: "完成前必须提供验证证据"
    gates:
      - type: "field_exists"
        name: "test_evidence_gate"
        field: "test_evidence"
        weight: 0.3
        description: "测试证据字段"
      - type: "field_exists"
        name: "verification_steps_gate"
        field: "verification_steps"
        weight: 0.2
        description: "验证步骤字段"
  
  # 强制原则
  - id: "no_syntax_errors"
    type: "MANDATORY"
    name: "无语法错误"
    description: "代码必须无语法错误"
    gates:
      - type: "command"
        name: "syntax_check_gate"
        command: "python -m py_compile src/"
        expected: "exit_code == 0"
        weight: 0.1
        description: "语法检查"
  
  # 可配置原则
  - id: "documentation_sync"
    type: "CONFIGURABLE"
    name: "文档同步"
    description: "代码变更需同步更新文档"
    enabled: true  # 可关闭
    gates:
      - type: "field_exists"
        name: "doc_update_gate"
        field: "doc_updated"
        weight: 0.0
        description: "文档更新标记"

template_gates:
  code-module:
    pre_completion:
      - gate: "lint_check"
        type: "command"
        command: "ruff check ."
        expected: "exit_code == 0"
        required: false
        description: "代码风格检查"
  
  novel-chapter:
    pre_completion:
      - gate: "word_count"
        type: "custom"
        check_func: "check_word_count"
        required: true
        min_words: 1000
        description: "字数要求"

amendments:
  - id: "amendment_001"
    date: "2024-03-10T00:00:00Z"
    description: "新增性能测试门禁"
    changes:
      - type: "add_principle"
        principle:
          id: "performance_test"
          type: "MANDATORY"
          name: "性能测试"
          gates: [...]
```

### 数据模型

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class PrincipleType(Enum):
    NON_NEGOTIABLE = "NON_NEGOTIABLE"
    MANDATORY = "MANDATORY"
    CONFIGURABLE = "CONFIGURABLE"

class GateType(Enum):
    COMMAND = "command"
    FIELD_EXISTS = "field_exists"
    CUSTOM = "custom"

@dataclass
class Gate:
    type: GateType
    name: str
    required: bool = True
    weight: float = 1.0
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Principle:
    id: str
    type: PrincipleType
    name: str
    description: str
    gates: List[Gate] = field(default_factory=list)
    enabled: bool = True  # 仅CONFIGURABLE类型有效

@dataclass
class ValidationResult:
    passed: bool
    message: str = ""
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class GateResult:
    passed: bool
    message: str = ""
    output: str = ""
    exit_code: int = 0
    weight: float = 1.0

@dataclass
class Constitution:
    schema_version: str
    project: Dict[str, Any]
    core_principles: List[Principle]
    template_gates: Dict[str, Dict[str, List[Gate]]] = field(default_factory=dict)
    amendments: List[Dict[str, Any]] = field(default_factory=list)
```

## 🔄 工作流程

### Constitution验证流程

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: 加载Constitution                                 │
│   ↓                                                       │
│   ├─ 文件存在 → 解析YAML                                 │
│   └─ 文件不存在 → 使用默认Constitution                   │
│                                                           │
│ Step 2: 验证Constitution完整性                           │
│   ↓                                                       │
│   ├─ 检查必需字段                                        │
│   ├─ 验证原则类型                                        │
│   └─ 验证门禁配置                                        │
│                                                           │
│ Step 3: 获取适用原则                                     │
│   ↓                                                       │
│   ├─ 获取NON_NEGOTIABLE原则                              │
│   ├─ 获取MANDATORY原则                                   │
│   └─ 获取启用的CONFIGURABLE原则                          │
│                                                           │
│ Step 4: 执行门禁检查                                     │
│   ↓                                                       │
│   ├─ 命令门禁 → 执行命令                                 │
│   ├─ 字段门禁 → 检查字段                                 │
│   └─ 自定义门禁 → 执行函数                               │
│                                                           │
│ Step 5: 汇总验证结果                                     │
│   ↓                                                       │
│   ├─ 全部通过 → ValidationResult(passed=True)            │
│   └─ 存在失败 → ValidationResult(passed=False, failures) │
└─────────────────────────────────────────────────────────┘
```

### 与TaskManager集成流程

```python
# 在task_manager.py中集成
class TaskManager:
    def __init__(self):
        # ... 原有初始化 ...
        self.constitution_manager = ConstitutionManager()
        self.principle_validator = PrincipleValidator(self.constitution_manager)
    
    def update_status(self, task_id: str, status: str, force: bool = False) -> Tuple[bool, str]:
        """更新任务状态"""
        # ... 原有逻辑 ...
        
        # 新增：完成前Constitution验证
        if status == "completed" and not force:
            # 获取任务
            t = self._get_task(data, task_id)
            if not t:
                return False, "task_not_found"
            
            # 获取适用的原则
            principles = self._get_applicable_principles(t)
            
            # 验证所有原则
            validation_results = []
            for principle in principles:
                result = self.principle_validator.validate_principle(
                    principle, task_id, t
                )
                validation_results.append(result)
                
                # 不可协商原则失败，立即返回
                if not result.passed and principle['type'] == 'NON_NEGOTIABLE':
                    return False, f"constitution_violation: {result.message}"
            
            # 汇总结果
            failures = [r for r in validation_results if not r.passed]
            if failures:
                # 部分门禁失败，进入优化状态
                t['status'] = 'optimizing'
                t['ralph']['issues'] = [f.message for f in failures]
                self._save(data)
                return False, f"quality_gates_failed: {len(failures)} gates failed"
        
        # ... 继续原有状态转换 ...
    
    def _get_applicable_principles(self, task: Dict) -> List[Dict]:
        """获取适用于任务的原则"""
        principles = []
        
        # 1. 全局原则
        principles.extend(
            self.constitution_manager.get_non_negotiable_principles()
        )
        principles.extend(
            self.constitution_manager.get_principles_by_type('MANDATORY')
        )
        
        # 2. 启用的可配置原则
        configurable = self.constitution_manager.get_principles_by_type('CONFIGURABLE')
        principles.extend([p for p in configurable if p.get('enabled', False)])
        
        # 3. 模板特定原则
        template = task.get('template', 'task')
        template_gates = self.constitution_manager.get_template_gates(template, 'pre_completion')
        if template_gates:
            principles.append({
                'id': f'template_{template}',
                'type': 'MANDATORY',
                'name': f'{template}模板门禁',
                'gates': template_gates
            })
        
        return principles
```

## 🎨 设计模式应用

### 1. 策略模式（Principle Validators）

```python
# 不同类型原则使用不同验证策略
class PrincipleValidator:
    def __init__(self):
        self.validators = {
            'NON_NEGOTIABLE': NonNegotiableValidator(),
            'MANDATORY': MandatoryValidator(),
            'CONFIGURABLE': ConfigurableValidator(),
        }
    
    def validate(self, principle: Principle, context: Dict) -> ValidationResult:
        validator = self.validators[principle.type]
        return validator.validate(principle, context)

class NonNegotiableValidator:
    def validate(self, principle: Principle, context: Dict) -> ValidationResult:
        # 所有门禁必须通过
        failures = []
        for gate in principle.gates:
            if not self._check_gate(gate, context):
                failures.append(gate.name)
        
        return ValidationResult(
            passed=len(failures) == 0,
            failures=failures
        )
```

### 2. 责任链模式（Gate Chain）

```python
# 门禁按顺序执行，可中断
class GateChain:
    def __init__(self, gates: List[Gate]):
        self.gates = gates
    
    def execute(self, context: Dict) -> ChainResult:
        results = []
        
        for gate in self.gates:
            result = gate.evaluate(context)
            results.append(result)
            
            # 必需门禁失败，中断执行
            if not result.passed and gate.required:
                break
        
        return ChainResult(results=results, completed=len(results) == len(self.gates))
```

### 3. 工厂模式（Gate Factory）

```python
# 根据类型创建不同的门禁
class GateFactory:
    @staticmethod
    def create_gate(gate_config: Dict) -> Gate:
        gate_type = gate_config['type']
        
        if gate_type == 'command':
            return CommandGate(**gate_config)
        elif gate_type == 'field_exists':
            return FieldGate(**gate_config)
        elif gate_type == 'custom':
            return CustomGate(**gate_config)
        else:
            raise ValueError(f"Unknown gate type: {gate_type}")
```

## 🔌 扩展性设计

### 自定义门禁类型

```python
# 用户可注册自定义门禁类型
class ConstitutionManager:
    def __init__(self):
        self.custom_gate_types = {}
    
    def register_gate_type(self, type_name: str, evaluator: Callable):
        """注册自定义门禁类型"""
        self.custom_gate_types[type_name] = evaluator
    
    def evaluate_custom_gate(self, gate: Dict, context: Dict):
        """评估自定义门禁"""
        evaluator = self.custom_gate_types.get(gate['type'])
        if evaluator:
            return evaluator(gate, context)
        raise ValueError(f"Unknown custom gate type: {gate['type']}")

# 使用示例
def my_custom_checker(gate: Dict, context: Dict) -> GateResult:
    # 自定义检查逻辑
    return GateResult(passed=True, message="Custom check passed")

constitution_manager.register_gate_type('my_custom', my_custom_checker)
```

### 动态原则加载

```python
# 从外部源加载Constitution
class ConstitutionManager:
    def load_from_url(self, url: str):
        """从URL加载Constitution"""
        response = requests.get(url)
        self.constitution = yaml.safe_load(response.text)
    
    def load_from_database(self, db_connection: str):
        """从数据库加载Constitution"""
        # 数据库加载逻辑
        pass
```

## 🧪 测试策略

### 单元测试

```python
import pytest
from lra.constitution import ConstitutionManager, PrincipleValidator

def test_constitution_loading():
    """测试Constitution加载"""
    manager = ConstitutionManager()
    assert manager.constitution is not None
    assert 'schema_version' in manager.constitution

def test_non_negotiable_principle_validation():
    """测试不可协商原则验证"""
    validator = PrincipleValidator()
    
    principle = {
        'id': 'test',
        'type': 'NON_NEGOTIABLE',
        'gates': [
            {'type': 'command', 'command': 'echo test', 'expected': 'exit_code == 0'}
        ]
    }
    
    result = validator.validate_principle(principle, 'task_001', {})
    assert result.passed

def test_gate_evaluation():
    """测试门禁评估"""
    evaluator = GateEvaluator()
    
    gate = {
        'type': 'field_exists',
        'field': 'test_evidence'
    }
    
    # 模拟任务文件
    result = evaluator.evaluate_gate(gate, 'task_001', {})
    assert result.passed or not result.passed  # 根据实际情况
```

### 集成测试

```python
def test_task_completion_with_constitution():
    """测试任务完成时的Constitution验证"""
    # 1. 创建任务
    task_manager = TaskManager()
    task_manager.create("Test Task")
    
    # 2. 提交完成
    success, message = task_manager.update_status('task_001', 'completed')
    
    # 3. 验证Constitution检查触发
    assert 'constitution_violation' in message or success
```

## 📊 性能优化

### 1. 缓存机制

```python
from functools import lru_cache

class ConstitutionManager:
    @lru_cache(maxsize=128)
    def get_principle(self, principle_id: str) -> Optional[Dict]:
        """缓存原则查询"""
        for principle in self.constitution.get('core_principles', []):
            if principle['id'] == principle_id:
                return principle
        return None
```

### 2. 并行门禁检查

```python
import asyncio

async def evaluate_gates_parallel(gates: List[Gate], context: Dict):
    """并行执行门禁检查"""
    tasks = [gate.evaluate_async(context) for gate in gates]
    results = await asyncio.gather(*tasks)
    return results
```

## 🛡️ 安全考量

### 1. 命令注入防护

```python
class CommandGate(Gate):
    ALLOWED_COMMANDS = ['pytest', 'ruff', 'eslint', 'python']
    
    def evaluate(self, context: Dict) -> GateResult:
        command = self.config['command']
        cmd_name = command.split()[0]
        
        # 白名单检查
        if cmd_name not in self.ALLOWED_COMMANDS:
            return GateResult(
                passed=False,
                message=f"Command not allowed: {cmd_name}"
            )
        
        # 沙箱执行
        return self._execute_sandboxed(command)
```

### 2. Constitution文件完整性

```python
import hashlib

class ConstitutionManager:
    def verify_integrity(self):
        """验证Constitution文件完整性"""
        if not self.constitution_path.exists():
            return
        
        content = self.constitution_path.read_text()
        current_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # 检查存储的哈希
        stored_hash = self._get_stored_hash()
        if stored_hash and current_hash != stored_hash:
            raise SecurityError("Constitution file integrity compromised")
        
        # 更新哈希
        self._store_hash(current_hash)
```

## 🚀 实施路线图

### Phase 1: 核心实现（1周）

- [x] 创建Constitution数据模型
- [x] 实现ConstitutionManager
- [x] 实现PrincipleValidator
- [x] 实现GateEvaluator
- [ ] 编写单元测试

### Phase 2: 集成（1周）

- [ ] 与TaskManager集成
- [ ] 与Ralph Loop集成
- [ ] CLI命令支持
- [ ] 编写集成测试

### Phase 3: 增强（1周）

- [ ] 自定义门禁类型
- [ ] 模板特定门禁
- [ ] 性能优化
- [ ] 文档完善

### Phase 4: 扩展（可选）

- [ ] Extension系统
- [ ] 动态加载
- [ ] 可视化配置
- [ ] 社区贡献

## 📚 参考资料

- [Constitution示例](../templates/constitution.yaml)
- [API文档](./CONSTITUTION_API.md)
- [最佳实践](./CONSTITUTION_BEST_PRACTICES.md)
- [常见问题](./CONSTITUTION_FAQ.md)

---

**文档版本**: v1.0  
**最后更新**: 2024-03-09  
**作者**: LRA Team