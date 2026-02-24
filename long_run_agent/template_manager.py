#!/usr/bin/env python3
"""
模板管理器
v3.1 - 可配置模板系统
"""

import os
import yaml
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .config import Config, SafeJson


class TemplateManager:
    def __init__(self):
        self.templates_dir = Config.get_templates_dir()
        os.makedirs(self.templates_dir, exist_ok=True)
        self._ensure_builtin_templates()

    def _ensure_builtin_templates(self):
        builtin = {
            "task": self._get_task_template(),
            "novel-chapter": self._get_novel_chapter_template(),
            "code-module": self._get_code_module_template(),
            "data-pipeline": self._get_data_pipeline_template(),
        }
        for name in builtin.keys():
            path = os.path.join(self.templates_dir, f"{name}.yaml")
            if not os.path.exists(path):
                self._save_template(path, builtin[name])

    def _get_task_template(self) -> Dict[str, Any]:
        return {
            "name": "task",
            "description": "通用任务模板",
            "version": "1.0",
            "keywords": [],
            "structure": """# {id}

## 描述

## 交付物
""",
            "states": ["pending", "in_progress", "completed"],
            "transitions": {
                "pending": ["in_progress"],
                "in_progress": ["completed"],
                "completed": [],
            },
            "acceptance": [],
        }

    def _get_novel_chapter_template(self) -> Dict[str, Any]:
        return {
            "name": "novel-chapter",
            "description": "小说章节模板",
            "version": "1.0",
            "keywords": ["小说", "章节", "故事", "叙述", "chapter", "novel", "写作", "情节"],
            "structure": """# {title}

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
            "version": "1.0",
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
            "structure": """# {id}

## 概述

<!-- 功能概述 -->

## 输入输出

### 输入
```
<!-- 参数定义 -->
```

### 输出
```
<!-- 返回值定义 -->
```

## 实现方案

<!-- 详细实现思路 -->

## 测试用例
<!-- 测试场景 -->
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
        }

    def _get_data_pipeline_template(self) -> Dict[str, Any]:
        return {
            "name": "data-pipeline",
            "description": "数据处理流程模板",
            "version": "1.0",
            "keywords": ["数据", "采集", "清洗", "分析", "ETL", "pipeline", "data", "处理", "转换"],
            "structure": """# {id}

## 数据源

<!-- 数据来源说明 -->

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
        return templates

    def load_template(self, name: str) -> Optional[Dict[str, Any]]:
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

    def create_template(self, name: str, from_template: str = None) -> Tuple[bool, str]:
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
                "version": "1.0",
                "keywords": [],
                "structure": f"# {{id}}\n\n## 描述\n\n## 交付物\n",
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

    def get_transitions_for_template(self, name: str) -> Dict[str, List[str]]:
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
        self, task_id: str, template_name: str, title: str = ""
    ) -> Tuple[bool, str]:
        template = self.load_template(template_name)
        if not template:
            template = self.load_template("task")

        structure = template.get("structure", "# {id}\n\n## 描述\n")
        structure = structure.replace("{id}", task_id)
        structure = structure.replace("{title}", title or task_id)

        tasks_dir = Config.get_tasks_dir()
        os.makedirs(tasks_dir, exist_ok=True)

        path = os.path.join(tasks_dir, f"{task_id}.md")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(structure)
            return True, path
        except Exception as e:
            return False, str(e)
