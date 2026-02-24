#!/usr/bin/env python3
"""
任务管理器
v3.1 - 通用任务管理，支持模板驱动
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
    ) -> Tuple[bool, Dict[str, Any]]:
        data = self._load()
        if not data:
            return False, {"error": "not_initialized"}

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

        task = {
            "id": task_id,
            "description": description,
            "template": template,
            "priority": priority,
            "status": self._get_initial_status(template),
            "parent_id": parent_id,
            "output_req": output_req,
            "task_file": f"tasks/{task_id}.md",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        data["tasks"].append(task)
        self._save(data)

        self.template_manager.create_task_file(task_id, template, description)

        return True, task

    def _get_initial_status(self, template: str) -> str:
        states = self.template_manager.get_states_for_template(template)
        return states[0] if states else "pending"

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
                template = t.get("template", "task")
                current = t.get("status", "pending")

                if not self.template_manager.validate_transition(template, current, status):
                    return False, f"invalid_transition:{current}->{status}"

                t["status"] = status
                t["updated_at"] = datetime.now().isoformat()

                states = self.template_manager.get_states_for_template(template)
                final_states = [
                    s
                    for s in states
                    if not self.template_manager.get_transitions_for_template(template).get(s)
                ]
                if status in final_states:
                    t["completed_at"] = datetime.now().isoformat()

                self._save(data)
                return True, status
        return False, "not_found"

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
        need_split = []

        for t in tasks:
            task_status = t.get("status", "pending")
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
                        }
                    )
                else:
                    need_split.append(
                        {
                            "id": t["id"],
                            "desc": t.get("description", "")[:50],
                            "output_req": req,
                            "can_split": True,
                        }
                    )

        result = {
            "project": data.get("project_name", ""),
            "stats": stats,
            "can_take": can_take,
        }

        if need_split:
            result["need_split"] = need_split

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
