#!/usr/bin/env python3
"""
任务管理器
v3.4 - 项目级模板固定
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from .config import Config, SafeJson, validate_project_initialized
from .template_manager import TemplateManager


class TaskManager:
    def __init__(self):
        self.task_list_path = Config.get_task_list_path()
        self.template_manager = TemplateManager()
        self.system_check_report = None

    def _load(self) -> Optional[Dict[str, Any]]:
        return SafeJson.read(self.task_list_path)

    def _save(self, data: Dict[str, Any]) -> bool:
        return SafeJson.write(self.task_list_path, data)

    def init_project(self, name: str, template: str) -> Tuple[bool, str]:
        Config.ensure_dirs()

        config = {
            "project_name": name,
            "created_at": datetime.now().isoformat(),
            "version": "3.4.0",
            "default_template": template,
        }
        SafeJson.write(Config.get_config_path(), config)

        task_list = {
            "project_name": name,
            "created_at": datetime.now().isoformat(),
            "tasks": [],
        }
        self._save(task_list)
        return True, "initialized"

    def get_default_template(self) -> str:
        """获取项目默认模板"""
        config = SafeJson.read(Config.get_config_path())
        if not config:
            return "task"
        return config.get("default_template", "task")

    def create(
        self,
        description: str,
        template: str = "task",
        priority: str = "P1",
        parent_id: str = None,
        output_req: str = "8k",
        dependencies: List[str] = None,
        deadline: str = None,
        dependency_type: str = "all",
        variables: Dict[str, Any] = None,
        skip_system_check: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        data = self._load()
        if not data:
            return False, {"error": "not_initialized"}

        # v3.3.0: 检查系统预检（除非跳过）
        if not skip_system_check:
            # 如果没有预检报告，自动创建
            if not self.has_system_check():
                self._auto_create_system_check()

            # v3.3.3: 增量模式自动降级 - 永不失败原则
            if self.is_incremental_mode():
                if not self._is_module_task(description) and not parent_id:
                    # 自动添加"-模块"后缀，而不是报错
                    adjusted_desc = f"{description}-模块"
                    # 返回调整后的描述，让 CLI 显示提示
                    return self._create_with_adjusted_desc(
                        data,
                        adjusted_desc,
                        template,
                        priority,
                        parent_id,
                        output_req,
                        dependencies,
                        deadline,
                        dependency_type,
                        variables,
                    )

        # 循环依赖检测（严重错误，保留）
        if dependencies:
            has_cycle, cycle_path = self._detect_cycle(dependencies)
            if has_cycle:
                return False, {"error": "cycle_dependency", "path": cycle_path}

        return self._do_create(
            data,
            description,
            template,
            priority,
            parent_id,
            output_req,
            dependencies,
            deadline,
            dependency_type,
            variables,
        )

    def _auto_create_doc_task(self, task: Dict[str, Any], variables: Dict[str, Any] = None):
        """为业务任务自动创建绑定的文档更新任务"""
        # 检查配置是否启用文档约束
        config = self._load_config()
        doc_enforcement = config.get("system_check", {}).get("doc_enforcement", "strict")

        if doc_enforcement == "disabled":
            return

        # 提取模块名
        module = self._extract_module_from_description(task["description"])
        if not module:
            return  # 无法提取模块名，不创建文档任务

        # 根据任务描述推断任务类型
        task_type = self._infer_task_type(task["description"])

        # 生成文档任务描述
        doc_templates = {
            "feat": f"更新{module}模块 README + 接口文档（需求：{task['description'][:50]}...）",
            "fix": f"更新{module}模块问题排查文档 + 修复说明（需求：{task['description'][:50]}...）",
            "refactor": f"更新{module}模块架构文档 + 依赖说明（需求：{task['description'][:50]}...）",
        }
        doc_desc = doc_templates.get(
            task_type, f"更新{module}模块文档（需求：{task['description'][:50]}...）"
        )

        # 创建文档任务
        doc_task_id = f"doc_update_{task['id'].split('_')[1]}"

        doc_task_vars = {
            "module": module,
            "update_scope": "auto",
            "user_demand": task["description"],
            **(variables or {}),
        }

        # 使用内部 create 方法，跳过系统检查
        self.create(
            description=doc_desc,
            template="doc-update",
            priority=task["priority"],
            dependencies=[task["id"]],
            dependency_type="all",
            variables=doc_task_vars,
            skip_system_check=True,
        )

    def _infer_task_type(self, description: str) -> str:
        """从任务描述推断任务类型"""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["bug", "修复", "fix", "错误", "问题"]):
            return "fix"
        elif any(kw in desc_lower for kw in ["重构", "refactor", "优化", "优化"]):
            return "refactor"
        elif any(kw in desc_lower for kw in ["功能", "feat", "新增", "开发", "实现"]):
            return "feat"

        return "feat"  # 默认

    def _load_config(self) -> Dict[str, Any]:
        """加载项目配置"""
        try:
            from .system_check import ConfigManager

            project_path = os.path.dirname(os.path.dirname(self.task_list_path))
            return ConfigManager.load_config(project_path)
        except:
            return {}

    def _get_initial_status(self, template: str) -> str:
        states = self.template_manager.get_states_for_template(template)
        return states[0] if states else "pending"

    def _detect_cycle(self, dependencies: List[str]) -> Tuple[bool, List[str]]:
        """DFS 检测循环依赖"""
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            task = self.get(node)
            if task:
                deps = task.get("dependencies", [])
                for dep in deps:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        path.append(dep)
                        return True

            path.pop()
            rec_stack.remove(node)
            return False

        for dep in dependencies:
            if dep not in visited:
                if dfs(dep):
                    return True, path
        return False, []

    def _do_create(
        self,
        data: Dict[str, Any],
        description: str,
        template: str,
        priority: str,
        parent_id: Optional[str],
        output_req: str,
        dependencies: Optional[List[str]],
        deadline: Optional[str],
        dependency_type: str,
        variables: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Dict[str, Any]]:
        """执行实际的任务创建"""
        existing = data.get("tasks", [])

        if parent_id:
            sibling_count = len([t for t in existing if t.get("parent_id") == parent_id])
            parts = parent_id.split("_")
            if len(parts) >= 3:
                task_id = f"{parent_id}_{sibling_count + 1:02d}"
            else:
                task_id = f"{parent_id}_{sibling_count + 1:02d}"
        else:
            num = len([t for t in existing if not t.get("parent_id")]) + 1
            task_id = f"task_{num:03d}"

        # 检查依赖是否满足
        initial_status = self._get_initial_status(template)
        if dependencies and not self._check_dependencies_satisfied(dependencies, dependency_type):
            initial_status = "blocked"

        task = {
            "id": task_id,
            "description": description,
            "template": template,
            "priority": priority,
            "status": initial_status,
            "parent_id": parent_id,
            "output_req": output_req,
            "task_file": f"tasks/{task_id}.md",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "dependencies": dependencies or [],
            "dependency_type": dependency_type,
            "deadline": deadline,
        }

        data["tasks"].append(task)
        self._save(data)

        self.template_manager.create_task_file(task_id, template, description, variables)

        # v3.3.0: 文档任务自动绑定
        if template != "doc-update":
            self._auto_create_doc_task(task, variables)

        return True, task

    def _create_with_adjusted_desc(
        self,
        data: Dict[str, Any],
        adjusted_desc: str,
        template: str,
        priority: str,
        parent_id: Optional[str],
        output_req: str,
        dependencies: Optional[List[str]],
        deadline: Optional[str],
        dependency_type: str,
        variables: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Dict[str, Any]]:
        """增量模式自动降级 - 创建调整后的任务并标记需要提示"""
        success, task = self._do_create(
            data,
            adjusted_desc,
            template,
            priority,
            parent_id,
            output_req,
            dependencies,
            deadline,
            dependency_type,
            variables,
        )

        if success:
            task["_auto_adjusted"] = True
            task["_original_desc"] = adjusted_desc[:-3]  # 移除"-模块"

        return success, task

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        if not data:
            return None
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                return t
        return None

    def update_status(self, task_id: str, status: str) -> Tuple[bool, str]:
        data = self._load()
        if not data:
            return False, "not_initialized"

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                # blocked 状态只能转移到初始状态
                if t.get("status") == "blocked":
                    template = t.get("template", "task")
                    initial_state = self._get_initial_status(template)
                    if status != initial_state:
                        return False, f"blocked_can_only_go_to_{initial_state}"

                # 原有状态流转验证
                template = t.get("template", "task")
                current = t.get("status", "pending")

                if not self.template_manager.validate_transition(template, current, status):
                    return False, f"invalid_transition:{current}->{status}"

                t["status"] = status
                t["updated_at"] = datetime.now().isoformat()

                # 依赖满足检查 - 更新依赖此任务的其他任务
                if self._is_final_status(t, status):
                    self._unblock_dependents(task_id)

                self._save(data)
                return True, status
        return False, "not_found"

    def _is_final_status(self, task: Dict[str, Any], status: str) -> bool:
        """判断是否为终态"""
        template = task.get("template", "task")
        final_states = self._get_final_states(template)
        return status in final_states

    def list_all(
        self, status: str = None, parent_id: str = None, template: str = None
    ) -> List[Dict[str, Any]]:
        data = self._load()
        if not data:
            return []

        tasks = data.get("tasks", [])

        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        if parent_id is not None:
            tasks = [t for t in tasks if t.get("parent_id") == parent_id]
        if template:
            tasks = [t for t in tasks if t.get("template") == template]

        return tasks

    def get_context(
        self, output_limit: str = "8k", include_full_desc: bool = False
    ) -> Dict[str, Any]:
        data = self._load()
        if not data:
            return {"error": "not_initialized"}

        tasks = data.get("tasks", [])
        limit_map = {"4k": 4, "8k": 8, "16k": 16, "32k": 32, "128k": 128}
        limit_num = limit_map.get(output_limit, 8)

        stats = self._calc_stats(tasks)

        can_take = []
        blocked_tasks = []
        in_progress_tasks = []

        for t in tasks:
            task_status = t.get("status", "pending")

            desc_limit = None if include_full_desc else 50
            desc = t.get("description", "")
            if desc_limit:
                desc = desc[:desc_limit]

            # blocked 状态不可领取
            if task_status == "blocked":
                blocked_tasks.append(
                    {
                        "id": t["id"],
                        "desc": desc,
                        "dependencies": t.get("dependencies", []),
                        "dependency_type": t.get("dependency_type", "all"),
                    }
                )
                continue

            states = self.template_manager.get_states_for_template(t.get("template", "task"))
            initial_state = states[0] if states else "pending"

            if task_status == initial_state:
                req = t.get("output_req", "8k")
                req_num = limit_map.get(req, 8)

                if req_num <= limit_num:
                    can_take.append(
                        {
                            "id": t["id"],
                            "desc": desc,
                            "template": t.get("template", "task"),
                            "output_req": req,
                            "priority": t.get("priority", "P1"),
                            "deadline": t.get("deadline"),
                            "dependencies": t.get("dependencies", []),
                        }
                    )
            elif task_status == "in_progress":
                in_progress_tasks.append(
                    {
                        "id": t["id"],
                        "desc": desc,
                        "template": t.get("template", "task"),
                        "priority": t.get("priority", "P1"),
                    }
                )

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        can_take.sort(key=lambda x: priority_order.get(x.get("priority", "P1"), 1))

        result = {
            "project": data.get("project_name", ""),
            "stats": stats,
            "can_take": can_take,
        }

        if in_progress_tasks:
            result["in_progress"] = in_progress_tasks

        if blocked_tasks:
            result["blocked"] = blocked_tasks

        if can_take:
            result["next"] = can_take[0]["id"]

        return result

    def _calc_stats(self, tasks: List[Dict]) -> Dict[str, int]:
        stats = {"total": len(tasks)}

        for t in tasks:
            status = t.get("status", "pending")
            stats[status] = stats.get(status, 0) + 1

        return stats

    def split_task(
        self, task_id: str, split_plan: List[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        parent = self.get(task_id)
        if not parent:
            return False, {"error": "not_found"}

        if not split_plan:
            return False, {"error": "no_split_plan", "hint": "provide split_plan"}

        created = []
        for i, item in enumerate(split_plan):
            desc = item.get("desc", f"Part {i + 1}")
            output_req = item.get("output_req", "8k")

            success, result = self.create(
                description=desc,
                template=parent.get("template", "task"),
                priority=parent.get("priority", "P1"),
                parent_id=task_id,
                output_req=output_req,
            )
            if success:
                created.append(result)

        return True, {"parent": task_id, "created": len(created), "tasks": created}

    def get_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get(task_id)
        if not task:
            return None

        return {
            "id": task["id"],
            "status": task.get("status", "pending"),
            "priority": task.get("priority", "P1"),
            "template": task.get("template", "task"),
            "desc": task.get("description", "")[:100],
            "output_req": task.get("output_req", "8k"),
            "task_file": task.get("task_file", ""),
            "parent_id": task.get("parent_id"),
        }

    def show(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get(task_id)
        if not task:
            return None

        return {
            "id": task["id"],
            "status": task.get("status", "pending"),
            "priority": task.get("priority", "P1"),
            "template": task.get("template", "task"),
            "desc": task.get("description", ""),
            "output_req": task.get("output_req", "8k"),
            "parent_id": task.get("parent_id"),
            "task_file": task.get("task_file", ""),
            "created_at": task.get("created_at", ""),
            "updated_at": task.get("updated_at", ""),
        }

    def delete(self, task_id: str) -> bool:
        data = self._load()
        if not data:
            return False

        tasks = data.get("tasks", [])
        for i, t in enumerate(tasks):
            if t.get("id") == task_id:
                tasks.pop(i)
                self._save(data)
                return True
        return False

    def get_children(self, task_id: str) -> List[Dict[str, Any]]:
        return self.list_all(parent_id=task_id)

    def get_parent(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get(task_id)
        if not task or not task.get("parent_id"):
            return None
        return self.get(task["parent_id"])

    # ========== v3.3.0 新增方法：系统预检集成 ==========

    def _load_system_check_report(self) -> Optional[Dict[str, Any]]:
        """加载系统预检报告"""
        if self.system_check_report:
            return self.system_check_report

        report_path = os.path.join(
            os.path.dirname(self.task_list_path), "reports", "sys_check_001.json"
        )

        if os.path.exists(report_path):
            try:
                import json

                with open(report_path, "r", encoding="utf-8") as f:
                    self.system_check_report = json.load(f)
                return self.system_check_report
            except:
                pass
        return None

    def has_system_check(self) -> bool:
        """检查是否有预检报告"""
        return self._load_system_check_report() is not None

    def is_incremental_mode(self) -> bool:
        """检查是否为增量模式"""
        report = self._load_system_check_report()
        if not report:
            return False
        return report.get("decision") == "incremental"

    def get_system_check_report(self) -> Optional[Dict[str, Any]]:
        """获取预检报告"""
        return self._load_system_check_report()

    def _extract_module_from_description(self, description: str) -> Optional[str]:
        """从任务描述中提取模块名（简单实现）"""
        # 简单匹配：查找"模块"、"module"等关键词
        import re

        patterns = [
            r"([a-zA-Z_]+) 模块",
            r"模块 ([a-zA-Z_]+)",
            r"([a-zA-Z_]+) module",
            r"module ([a-zA-Z_]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _is_module_task(self, description: str) -> bool:
        """检查是否是模块级任务"""
        module = self._extract_module_from_description(description)
        return module is not None

    def _auto_create_system_check(self):
        """自动创建系统预检任务"""
        try:
            from .system_check import SystemCheckTask

            project_path = os.path.dirname(os.path.dirname(self.task_list_path))
            checker = SystemCheckTask(project_path=project_path)
            checker.run()

            self.system_check_report = checker.get_report()
        except Exception as e:
            # 如果失败，创建一个默认的全量模式报告
            self.system_check_report = {
                "decision": "full",
                "reason": f"预检失败：{str(e)}",
            }
