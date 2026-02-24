#!/usr/bin/env python3
"""
任务管理器
v3.2 - 依赖关系 + 优先级支持
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

    def _load(self) -> Optional[Dict[str, Any]]:
        return SafeJson.read(self.task_list_path)

    def _save(self, data: Dict[str, Any]) -> bool:
        return SafeJson.write(self.task_list_path, data)

    def init_project(self, name: str) -> Tuple[bool, str]:
        Config.ensure_dirs()

        config = {
            "project_name": name,
            "created_at": datetime.now().isoformat(),
            "version": "3.1.0",
        }
        SafeJson.write(Config.get_config_path(), config)

        task_list = {
            "project_name": name,
            "created_at": datetime.now().isoformat(),
            "tasks": [],
        }
        self._save(task_list)
        return True, "initialized"

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
    ) -> Tuple[bool, Dict[str, Any]]:
        data = self._load()
        if not data:
            return False, {"error": "not_initialized"}

        # 循环依赖检测
        if dependencies:
            has_cycle, cycle_path = self._detect_cycle(dependencies)
            if has_cycle:
                return False, {"error": "cycle_dependency", "path": cycle_path}

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

        return True, task

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

    def _check_dependencies_satisfied(self, dependencies: List[str], dependency_type: str) -> bool:
        """检查依赖是否满足"""
        if not dependencies:
            return True

        completed = []
        for dep_id in dependencies:
            dep_task = self.get(dep_id)
            if not dep_task:
                continue

            status = dep_task.get("status", "pending")
            template = dep_task.get("template", "task")
            final_states = self._get_final_states(template)

            if status in final_states:
                completed.append(dep_id)

        if dependency_type == "all":
            return len(completed) == len(dependencies)
        else:  # any
            return len(completed) > 0

    def _get_final_states(self, template_name: str) -> List[str]:
        """获取模板终态"""
        states = self.template_manager.get_states_for_template(template_name)
        transitions = self.template_manager.get_transitions_for_template(template_name)
        return [s for s in states if not transitions.get(s, [])]

    def _unblock_dependents(self, completed_task_id: str):
        """自动解锁依赖此任务的其他任务"""
        data = self._load()
        if not data:
            return

        changed = False
        for task in data.get("tasks", []):
            if task.get("status") != "blocked":
                continue

            deps = task.get("dependencies", [])
            if completed_task_id not in deps:
                continue

            # 重新检查依赖
            satisfied = self._check_dependencies_satisfied(deps, task.get("dependency_type", "all"))

            if satisfied:
                task["status"] = self._get_initial_status(task.get("template", "task"))
                task["updated_at"] = datetime.now().isoformat()
                changed = True

        if changed:
            self._save(data)

    def check_blocked_tasks(self) -> int:
        """手动检查并解锁 blocked 任务"""
        data = self._load()
        if not data:
            return 0

        unblocked = 0
        for task in data.get("tasks", []):
            if task.get("status") != "blocked":
                continue

            dependencies = task.get("dependencies", [])
            dependency_type = task.get("dependency_type", "all")

            if self._check_dependencies_satisfied(dependencies, dependency_type):
                task["status"] = self._get_initial_status(task.get("template", "task"))
                task["updated_at"] = datetime.now().isoformat()
                unblocked += 1

        if unblocked > 0:
            self._save(data)
        return unblocked

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

    def get_context(self, output_limit: str = "8k") -> Dict[str, Any]:
        data = self._load()
        if not data:
            return {"error": "not_initialized"}

        tasks = data.get("tasks", [])
        limit_map = {"4k": 4, "8k": 8, "16k": 16, "32k": 32, "128k": 128}
        limit_num = limit_map.get(output_limit, 8)

        stats = self._calc_stats(tasks)

        can_take = []
        blocked_tasks = []

        for t in tasks:
            task_status = t.get("status", "pending")

            # blocked 状态不可领取
            if task_status == "blocked":
                blocked_tasks.append(
                    {
                        "id": t["id"],
                        "desc": t.get("description", "")[:50],
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
                            "desc": t.get("description", "")[:50],
                            "template": t.get("template", "task"),
                            "output_req": req,
                            "priority": t.get("priority", "P1"),
                            "deadline": t.get("deadline"),
                            "dependencies": t.get("dependencies", []),
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
