#!/usr/bin/env python3
"""
模板管理器
v3.2 - Jinja2 模板引擎支持
"""

import os
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from lra.config import Config, SafeJson

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class TemplateManager:
    def __init__(self):
        self.templates_dir = Config.get_templates_dir()
        os.makedirs(self.templates_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._ensure_builtin_templates()

    def _ensure_builtin_templates(self):
        builtin = {
            "task": self._get_task_template(),
            "novel-chapter": self._get_novel_chapter_template(),
            "code-module": self._get_code_module_template(),
            "data-pipeline": self._get_data_pipeline_template(),
            "doc-update": self._get_doc_update_template(),
        }
        for name in builtin.keys():
            path = os.path.join(self.templates_dir, f"{name}.yaml")
            if not os.path.exists(path):
                self._save_template(path, builtin[name])
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = yaml.safe_load(f)
                    existing_version = existing.get("version", "1.0") if existing else "1.0"
                    builtin_version = builtin[name].get("version", "1.0")
                    if self._compare_versions(builtin_version, existing_version) > 0:
                        self._save_template(path, builtin[name])
                        self.logger.info(
                            f"Updated template {name} from v{existing_version} to v{builtin_version}"
                        )
                except Exception:
                    pass

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号，返回 1: v1 > v2, 0: v1 == v2, -1: v1 < v2"""
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0

    def _get_task_template(self) -> Dict[str, Any]:
        return {
            "name": "task",
            "description": "通用任务模板",
            "version": "2.1",
            "template_engine": "jinja2",
            "keywords": [],
            "structure": """# {{ id }}

## ⚠️ 重要提示（Agent 必读）

**当前位置**: `.long-run-agent/tasks/{{id}}.md`（任务描述文件）

**工作目录**: 项目根目录（`.long-run-agent` 的同级目录）

**产出物**: 请在项目根目录或适当子目录创建交付物

**这是配置文件**，不是最终产出！

## 描述

{{ description }}

{% if requirements %}
## 需求 (requirements)

{{ requirements }}
{% else %}
## 需求 (requirements)

<!-- 在此填写具体需求描述 -->
{% endif %}

{% if acceptance %}
## 验收标准 (acceptance)

{% for item in acceptance %}
- {{ item }}
{% endfor %}
{% else %}
## 验收标准 (acceptance)

<!-- 在此填写验收标准，每行一个条件 -->
{% endif %}

{% if deliverables %}
## 交付物 (deliverables)

{% for item in deliverables %}
- {{ item }}
{% endfor %}
{% else %}
## 交付物 (deliverables)

<!-- 在此填写交付物文件路径 -->
{% endif %}

{% if design %}
## 设计方案 (design)

{{ design }}
{% else %}
## 设计方案 (design)

<!-- 在此填写架构设计、技术选型、实现思路 -->
{% endif %}

## 验证证据（完成前必填）

<!-- 标记完成前，请提供以下证据： -->

- [ ] **实现证明**: 简要说明如何实现
- [ ] **测试验证**: 如何验证功能正常（测试步骤/截图/命令输出）
- [ ] **影响范围**: 是否影响其他功能

### 测试步骤
1. 
2. 
3. 

### 验证结果
<!-- 粘贴验证截图、命令输出或测试结果 -->
""",
            "states": ["pending", "in_progress", "completed"],
            "transitions": {
                "pending": ["in_progress"],
                "in_progress": ["completed"],
                "completed": [],
            },
            "acceptance": [],
            "validation": {
                "required_for_completion": {
                    "test_evidence": True,
                    "verification_steps": True,
                },
                "evidence_fields": ["实现证明", "测试验证", "影响范围"],
            },
        }

    def _get_novel_chapter_template(self) -> Dict[str, Any]:
        return {
            "name": "novel-chapter",
            "description": "小说章节模板",
            "version": "2.0",
            "template_engine": "jinja2",
            "keywords": ["小说", "章节", "故事", "叙述", "chapter", "novel", "写作", "情节"],
            "structure": """# {{ title }}

## ⚠️ 重要提示（Agent 必读）

**当前位置**: `.long-run-agent/tasks/{{id}}.md`（任务描述文件）

**工作目录**: 项目根目录（`.long-run-agent` 的同级目录）

**产出物位置**: 请在 `novel/` 或项目根目录创建章节文件

**不要**将作品内容写在这个文件里！

## 场景

<!-- 描述本章发生的场景 -->

## 人物

<!-- 涉及的人物 -->

## 正文

<!-- 章节内容 -->

## 伏笔

<!-- 埋下的伏笔 -->
""",
            "states": ["drafting", "revising", "finalized"],
            "transitions": {
                "drafting": ["revising"],
                "revising": ["drafting", "finalized"],
                "finalized": [],
            },
            "acceptance": ["字数 >= 2000", "包含场景描写", "人物对话完整"],
        }

    def _get_code_module_template(self) -> Dict[str, Any]:
        return {
            "name": "code-module",
            "description": "代码模块开发模板",
            "version": "2.1",
            "template_engine": "jinja2",
            "keywords": [
                "接口",
                "函数",
                "模块",
                "API",
                "function",
                "module",
                "实现",
                "开发",
                "代码",
                "code",
            ],
            "structure": """# {{ id }}

## ⚠️ 重要提示（Agent 必读）

**当前位置**: `.long-run-agent/tasks/{{id}}.md`（任务描述文件）

**工作目录**: 项目根目录（`.long-run-agent` 的同级目录）

**产出物位置**: 请在 `src/`、`tests/` 或适当位置创建代码文件

**这是配置文件**，不是最终产出！

## 概述

{{ description }}

## 技术栈

{% if tech_stack %}
{{ tech_stack }}
{% else %}
<!-- 请指定技术栈 -->
{% endif %}

## 输入输出

### 输入
```
{% if input_params %}
{{ input_params }}
{% else %}
<!-- 参数定义 -->
{% endif %}
```

### 输出
```
{% if output_return %}
{{ output_return }}
{% else %}
<!-- 返回值定义 -->
{% endif %}
```

## 实现方案

<!-- 详细实现思路 -->

## 测试用例
<!-- 测试场景 -->

## 验证证据（完成前必填）

**⚠️ 标记 completed 前必须提供以下证据！**

- [ ] **代码实现**: 核心功能已实现
- [ ] **测试通过**: 单元测试/集成测试通过
- [ ] **无语法错误**: 代码可正常导入/编译
- [ ] **回归测试**: 未破坏已有功能

### 测试命令
```bash
# 粘贴测试命令
pytest tests/test_xxx.py -v
```

### 测试输出
```
# 粘贴测试输出
```

### 截图（如适用）
<!-- UI任务请提供截图路径，如：verification/screenshot.png -->

### 代码片段
```python
# 关键代码片段（可选）
```
""",
            "states": ["pending", "in_progress", "pending_test", "test_failed", "completed"],
            "transitions": {
                "pending": ["in_progress"],
                "in_progress": ["pending_test"],
                "pending_test": ["test_failed", "completed"],
                "test_failed": ["in_progress"],
                "completed": [],
            },
            "acceptance": ["接口可调用", "测试通过", "无语法错误"],
            "validation": {
                "required_for_completion": {
                    "test_evidence": True,
                    "screenshot": False,
                    "test_output": True,
                    "verification_steps": True,
                },
                "evidence_fields": ["代码实现", "测试通过", "无语法错误", "回归测试"],
                "test_commands": True,
            },
        }

    def _get_data_pipeline_template(self) -> Dict[str, Any]:
        return {
            "name": "data-pipeline",
            "description": "数据处理流程模板",
            "version": "2.0",
            "template_engine": "jinja2",
            "keywords": ["数据", "采集", "清洗", "分析", "ETL", "pipeline", "data", "处理", "转换"],
            "structure": """# {{ id }}

## ⚠️ 重要提示（Agent 必读）

**当前位置**: `.long-run-agent/tasks/{{id}}.md`（任务描述文件）

**工作目录**: 项目根目录（`.long-run-agent` 的同级目录）

**产出物位置**: 请在 `data/`、`notebooks/`、`src/` 或适当位置创建

**这是配置文件**，不是最终产出！

## 数据源

{% if data_source %}
{{ data_source }}
{% else %}
<!-- 数据来源说明 -->
{% endif %}

## 处理步骤
1. 
2. 
3. 

## 输出格式

<!-- 输出数据格式 -->

## 异常处理

<!-- 异常情况处理 -->
""",
            "states": ["pending", "running", "failed", "success"],
            "transitions": {
                "pending": ["running"],
                "running": ["failed", "success"],
                "failed": ["running"],
                "success": [],
            },
            "acceptance": ["数据完整性校验通过", "处理完成"],
        }

    def _get_doc_update_template(self) -> Dict[str, Any]:
        return {
            "name": "doc-update",
            "description": "文档更新任务模板",
            "version": "1.0",
            "template_engine": "jinja2",
            "keywords": ["文档", "更新", "docs", "documentation", "readme", "api"],
            "structure": """# {{ id }}

## ⚠️ 重要提示（Agent 必读）

**当前位置**: `.long-run-agent/tasks/{{id}}.md`（任务描述文件）

**工作目录**: 项目根目录（`.long-run-agent` 的同级目录）

**产出物位置**: 请在项目适当位置更新文档（如 `README.md`, `docs/`, 或代码文件中的 docstring）

**这是配置文件**，不是最终产出！

## 关联业务任务
{% if dependencies %}
{% for dep in dependencies %}
- {{ dep }}
{% endfor %}
{% else %}
<!-- 无关联业务任务 -->
{% endif %}

## 模块名称
{{ module }}

## 更新范围
{{ update_scope }}

## 用户需求
{{ user_demand }}

## 需更新的文档列表
<!-- Agent 自动定位 -->
- [ ] {{ module }}/README.md
- [ ] docs/{{ module }}/API.md
- [ ] src/{{ module }}/__init__.py (docstring)

## 更新内容
<!-- 增量更新，仅修改相关片段 -->

## 更新说明
<!-- 记录更新原因和内容 -->
""",
            "states": ["pending", "in_progress", "completed"],
            "transitions": {
                "pending": ["in_progress"],
                "in_progress": ["completed"],
                "completed": [],
            },
            "acceptance": ["文档已更新", "更新内容与业务需求一致", "格式规范"],
        }

    def _save_template(self, path: str, data: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def list_templates(self) -> List[Dict[str, Any]]:
        templates = []
        if os.path.exists(self.templates_dir):
            for f in os.listdir(self.templates_dir):
                if f.endswith(".yaml"):
                    template = self.load_template(f[:-5])
                    if template:
                        templates.append(
                            {
                                "name": template.get("name"),
                                "description": template.get("description", ""),
                                "states": template.get("states", []),
                                "keywords": template.get("keywords", []),
                            }
                        )

        # v3.3.3: 模板排序（task 放最后）
        from lra.tips import TEMPLATE_PRIORITY

        def sort_key(t):
            priority = TEMPLATE_PRIORITY.get(t["name"], 99)
            return (priority, t["name"])

        return sorted(templates, key=sort_key)

    def load_template(self, name: Optional[str]) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.templates_dir, f"{name}.yaml")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except:
            return None

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        return self.load_template(name)

    def create_template(self, name: str, from_template: Optional[str] = None) -> Tuple[bool, str]:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            return False, "invalid_name"

        path = os.path.join(self.templates_dir, f"{name}.yaml")
        if os.path.exists(path):
            return False, "exists"

        if from_template:
            source = self.load_template(from_template)
            if not source:
                return False, "source_template_not_found"
            data = source.copy()
            data["name"] = name
            data["description"] = f"Based on {from_template}"
        else:
            data = {
                "name": name,
                "description": "自定义模板",
                "version": "2.0",
                "template_engine": "jinja2",
                "keywords": [],
                "structure": f"# {{{{ id }}}}\n\n## 描述\n\n{{{{ description }}}}\n\n## 交付物\n",
                "states": ["pending", "in_progress", "completed"],
                "transitions": {
                    "pending": ["in_progress"],
                    "in_progress": ["completed"],
                    "completed": [],
                },
                "acceptance": [],
            }

        self._save_template(path, data)
        return True, path

    def delete_template(self, name: str) -> Tuple[bool, str]:
        if name == "task":
            return False, "cannot_delete_default"

        path = os.path.join(self.templates_dir, f"{name}.yaml")
        if not os.path.exists(path):
            return False, "not_found"

        os.remove(path)
        return True, "deleted"

    def validate_template(self, name: str) -> Tuple[bool, List[str]]:
        template = self.load_template(name)
        if not template:
            return False, ["template_not_found"]

        errors = []

        if not template.get("name"):
            errors.append("missing_name")
        if not template.get("states"):
            errors.append("missing_states")
        if not template.get("transitions"):
            errors.append("missing_transitions")
        if not template.get("structure"):
            errors.append("missing_structure")

        return len(errors) == 0, errors

    def get_states_for_template(self, name: str) -> List[str]:
        template = self.load_template(name)
        if not template:
            return ["pending", "in_progress", "completed"]
        return template.get("states", ["pending", "in_progress", "completed"])

    def get_transitions_for_template(self, name: Optional[str]) -> Dict[str, List[str]]:
        template = self.load_template(name)
        if not template:
            return {"pending": ["in_progress"], "in_progress": ["completed"]}
        return template.get(
            "transitions", {"pending": ["in_progress"], "in_progress": ["completed"]}
        )

    def validate_transition(self, template_name: str, from_state: str, to_state: str) -> bool:
        transitions = self.get_transitions_for_template(template_name)
        allowed = transitions.get(from_state, [])
        return to_state in allowed

    def create_task_file(
        self,
        task_id: str,
        template_name: str,
        title: str = "",
        variables: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        template = self.load_template(template_name)
        if not template:
            template = self.load_template("task")

        if not template:
            return False, "template_not_found"

        engine = template.get("template_engine", "jinja2")
        structure = template.get("structure", "# {{ id }}\n\n## 描述\n")

        if engine == "jinja2":
            if not JINJA2_AVAILABLE:
                return False, "jinja2_not_installed"
            structure = self._render_jinja2(structure, task_id, title, variables)
        else:
            structure = self._render_simple(structure, task_id, title)

        tasks_dir = Config.get_tasks_dir()
        os.makedirs(tasks_dir, exist_ok=True)

        path = os.path.join(tasks_dir, f"{task_id}.md")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(structure)
            return True, path
        except Exception as e:
            return False, str(e)

    def _render_jinja2(
        self, template_str: str, task_id: str, title: str, variables: Dict[str, Any] = None
    ) -> str:
        """使用 Jinja2 渲染模板"""
        env = jinja2.Environment()
        tpl = env.from_string(template_str)

        context = {
            "id": task_id,
            "title": title or task_id,
            "description": title,
            "created_at": datetime.now().isoformat(),
            "variables": variables or {},
        }

        # 支持直接访问 variables 中的字段
        if variables:
            context.update(variables)

        return tpl.render(**context)

    def _render_simple(self, template_str: str, task_id: str, title: str) -> str:
        """简单字符串替换（向后兼容）"""
        return template_str.replace("{id}", task_id).replace("{title}", title or task_id)

    def load_iteration_stages(self, template_name: str) -> List[Dict[str, Any]]:
        """
        从模板配置文件加载迭代阶段定义

        参数:
            template_name: 模板名称

        返回:
            迭代阶段列表，每个元素是一个字典:
            {
                "iteration": 1,
                "name": "阶段名称",
                "focus": ["重点1", "重点2"],
                "priority_checks": ["test", "lint"],
                "ignore_checks": ["performance"],
                "suggestion": "详细建议...",
                "safety_checks": [...]  # 可选
            }
        """
        template_file = os.path.join(self.templates_dir, f"{template_name}.yaml")
        if not os.path.exists(template_file):
            return self._get_default_stages()

        try:
            with open(template_file, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载模板失败: {e}")
            return self._get_default_stages()

        ralph_config = template_data.get("ralph", {})
        stages = ralph_config.get("iteration_stages", [])

        if not stages:
            return self._get_default_stages()

        validated_stages = []
        for stage in stages:
            if self._validate_stage(stage):
                validated_stages.append(stage)

        return validated_stages

    def _validate_stage(self, stage: Dict[str, Any]) -> bool:
        """
        验证阶段配置是否完整有效

        必需字段:
        - iteration: 整数 1-7
        - name: 字符串
        - focus: 列表
        - suggestion: 字符串

        可选字段:
        - priority_checks: 列表
        - ignore_checks: 列表
        - safety_checks: 列表
        """
        if not isinstance(stage, dict):
            return False

        required_fields = ["iteration", "name", "focus", "suggestion"]
        for field in required_fields:
            if field not in stage:
                self.logger.warning(f"阶段缺少必需字段: {field}")
                return False

        iteration = stage.get("iteration")
        if not isinstance(iteration, int) or iteration < 1 or iteration > 7:
            self.logger.warning(f"无效的迭代次数: {iteration}")
            return False

        focus = stage.get("focus")
        if not isinstance(focus, list):
            self.logger.warning("focus 必须是列表")
            return False

        return True

    def _get_default_stages(self) -> List[Dict[str, Any]]:
        """
        获取默认的7阶段配置（当模板没有配置时使用）

        返回通用的7阶段配置
        """
        return [
            {
                "iteration": 1,
                "name": "基础实现",
                "focus": ["完成核心功能", "确保可运行"],
                "suggestion": "🎯 首次迭代：专注于让功能跑起来",
            },
            {
                "iteration": 2,
                "name": "功能完善",
                "focus": ["补充功能", "处理边界"],
                "suggestion": "🎯 第2次迭代：完善功能细节",
            },
            {
                "iteration": 3,
                "name": "代码优化",
                "focus": ["重构代码", "提升性能"],
                "suggestion": "🎯 第3次迭代：优化代码结构和性能",
            },
            {
                "iteration": 4,
                "name": "测试增强",
                "focus": ["补充测试", "提升覆盖率"],
                "suggestion": "🎯 第4次迭代：完善测试用例",
            },
            {
                "iteration": 5,
                "name": "文档完善",
                "focus": ["补充文档", "优化注释"],
                "suggestion": "🎯 第5次迭代：完善文档和注释",
            },
            {
                "iteration": 6,
                "name": "安全审查",
                "focus": ["安全检查", "漏洞修复"],
                "suggestion": "🎯 第6次迭代：进行安全审查",
            },
            {
                "iteration": 7,
                "name": "最终验证",
                "focus": ["全面测试", "集成验证"],
                "suggestion": "🎯 第7次迭代：最终验证和确认",
            },
        ]

    def get_stage_by_iteration(
        self, template_name: str, iteration: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定迭代的阶段配置

        参数:
            template_name: 模板名称
            iteration: 迭代次数

        返回:
            阶段配置字典，如果找不到则返回 None
        """
        stages = self.load_iteration_stages(template_name)

        for stage in stages:
            if stage.get("iteration") == iteration:
                return stage

        return stages[-1] if stages else None
