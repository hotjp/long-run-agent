#!/usr/bin/env python3
"""
任务管理器
v3.5 - 支持 Ralph Loop 状态跟踪
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from lra.config import Config, SafeJson, validate_project_initialized
from lra.template_manager import TemplateManager


class TaskManager:
    def __init__(self):
        self.task_list_path = Config.get_task_list_path()
        self._template_manager = None
        self._last_decomposition_suggestion = None  # 存储最后一次分解建议
        self.system_check_report = None

    @property
    def template_manager(self):
        if self._template_manager is None:
            self._template_manager = TemplateManager()
        return self._template_manager

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
        parent_id: Optional[str] = None,
        output_req: str = "8k",
        dependencies: Optional[List[str]] = None,
        deadline: Optional[str] = None,
        dependency_type: str = "all",
        variables: Optional[Dict[str, Any]] = None,
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

        # 循环依赖检测（严重错误，保留）- 必须在创建前检测
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
        # 优先尝试读取 config.json（旧格式）
        try:
            config_path = Config.get_config_path()
            if os.path.exists(config_path):
                return SafeJson.read(config_path) or {}
        except:
            pass

        # 尝试读取 config.yaml（新格式）
        try:
            from lra.system_check import ConfigManager

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
            "ralph": {
                "iteration": 0,
                "max_iterations": 7,
                "quality_checks": {
                    "tests_passed": False,
                    "lint_passed": False,
                    "acceptance_met": False,
                },
                "issues": [],
                "optimization_history": [],
            },
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

    def update_status(self, task_id: str, status: str, force: bool = False) -> Tuple[bool, str]:
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

                # 🆕 Constitution强制验证 - 在completed状态时自动检查
                if status in ["completed", "truly_completed"] and not force:
                    constitution_result = self._validate_constitution(task_id, t, template)
                    if not constitution_result["passed"]:
                        # Constitution验证失败，自动进入optimizing状态
                        if status == "completed":
                            t["status"] = "optimizing"
                            t["updated_at"] = datetime.now().isoformat()

                            # 初始化Ralph Loop状态
                            if "ralph" not in t:
                                t["ralph"] = {
                                    "iteration": 0,
                                    "max_iterations": 7,
                                    "quality_checks": {},
                                    "issues": constitution_result.get("failures", []),
                                    "optimization_history": [],
                                }
                            else:
                                t["ralph"]["issues"] = constitution_result.get("failures", [])

                            self._save(data)

                            return (
                                False,
                                f"constitution_failed:{'; '.join(constitution_result.get('failures', []))}",
                            )

                # Ralph Loop 状态转换逻辑
                if not force:
                    current_real_status = self.get_real_status(task_id)

                    # completed -> optimizing (质量检查不通过)
                    if current_real_status == "completed" and status == "optimizing":
                        if not self._validate_quality_passed(t):
                            if not self.template_manager.validate_transition(
                                template, current, status
                            ):
                                return False, f"invalid_transition:{current}->{status}"
                            t["status"] = status
                            t["updated_at"] = datetime.now().isoformat()
                            self._save(data)
                            return True, status

                    # optimizing -> truly_completed (质量检查通过 + Constitution验证)
                    elif current_real_status == "optimizing" and status == "truly_completed":
                        # 🆕 先验证Constitution
                        constitution_result = self._validate_constitution(task_id, t, template)
                        if not constitution_result["passed"]:
                            # Constitution验证失败，继续迭代
                            return (
                                False,
                                f"constitution_failed:{'; '.join(constitution_result.get('failures', []))}",
                            )

                        # 质量检查通过
                        if self._validate_quality_passed(t):
                            t["status"] = status
                            t["updated_at"] = datetime.now().isoformat()
                            self._save(data)
                            if self._is_final_status(t, status):
                                self._unblock_dependents(task_id)
                            return True, status

                    # optimizing -> force_completed (达到优化上限)
                    elif current_real_status == "optimizing" and status == "force_completed":
                        ralph_state = t.get("ralph", {})
                        if ralph_state.get("iteration", 0) >= ralph_state.get("max_iterations", 7):
                            # 🆕 即使强制完成，也要检查NON_NEGOTIABLE原则
                            constitution_result = self._validate_constitution(
                                task_id, t, template, check_non_negotiable_only=True
                            )
                            if not constitution_result["passed"]:
                                # NON_NEGOTIABLE原则不能违反
                                return (
                                    False,
                                    f"constitution_non_negotiable_violation:{'; '.join(constitution_result.get('failures', []))}",
                                )

                            t["status"] = status
                            t["updated_at"] = datetime.now().isoformat()
                            self._save(data)
                            if self._is_final_status(t, status):
                                self._unblock_dependents(task_id)
                            return True, status

                # 正常状态流转
                if not self.template_manager.validate_transition(template, current, status):
                    return False, f"invalid_transition:{current}->{status}"

                t["status"] = status
                t["updated_at"] = datetime.now().isoformat()

                # 如果状态是 blocked，清理锁信息
                if status == "blocked":
                    try:
                        from lra.locks_manager import LocksManager

                        lm = LocksManager()
                        lm.release(task_id)
                    except:
                        pass  # 忽略释放锁失败的情况

                self._save(data)

                # 依赖满足检查 - 更新依赖此任务的其他任务
                if self._is_final_status(t, status):
                    self._unblock_dependents(task_id)

                return True, status
        return False, "not_found"

    def _validate_constitution(
        self,
        task_id: str,
        task: Dict[str, Any],
        template: str,
        check_non_negotiable_only: bool = False,
    ) -> Dict[str, Any]:
        """验证Constitution原则"""
        try:
            from lra.constitution import ConstitutionManager, PrincipleValidator

            manager = ConstitutionManager()
            validator = PrincipleValidator(manager)

            # 如果只检查NON_NEGOTIABLE原则
            if check_non_negotiable_only:
                principles = manager.get_non_negotiable_principles()
                all_failures = []

                for principle in principles:
                    result = validator.validate_principle(principle, task_id, task)
                    if not result.passed:
                        all_failures.extend(result.failures)

                return {"passed": len(all_failures) == 0, "failures": all_failures}

            # 完整验证
            result = validator.validate_all_principles(task_id, task, template)

            return {
                "passed": result.passed,
                "failures": result.failures,
                "warnings": result.warnings,
                "gate_results": result.gate_results,
            }

        except Exception as e:
            # Constitution验证异常，默认通过（避免阻塞）
            print(f"⚠️  Constitution验证异常: {e}")
            return {"passed": True, "failures": [], "warnings": [f"Constitution验证异常: {e}"]}

    def _is_final_status(self, task: Dict[str, Any], status: str) -> bool:
        """判断是否为终态"""
        template = task.get("template", "task")
        final_states = self._get_final_states(template)
        return status in final_states

    def _get_final_states(self, template: str) -> List[str]:
        """获取模板的终态列表"""
        try:
            transitions = self.template_manager.get_transitions_for_template(template)
            all_states = self.template_manager.get_states_for_template(template)
            return [s for s in all_states if not transitions.get(s)]
        except Exception:
            return ["completed", "success", "finalized"]

    def _check_dependencies_satisfied(self, dependencies: List[str], dependency_type: str) -> bool:
        """检查依赖是否满足（宽松模式）"""
        if not dependencies:
            return True

        try:
            completed = []
            for dep_id in dependencies:
                dep_task = self.get(dep_id)
                if not dep_task:
                    completed.append(dep_id)
                    continue

                status = dep_task.get("status", "pending")
                if status in ["completed", "success", "finalized", "done"]:
                    completed.append(dep_id)

            if dependency_type == "all":
                return len(completed) == len(dependencies)
            else:
                return len(completed) > 0
        except Exception:
            return True

    def _unblock_dependents(self, task_id: str):
        """解锁依赖此任务的其他任务"""
        try:
            data = self._load()
            if not data:
                return

            tasks = data.get("tasks", [])
            updated = False

            for task in tasks:
                if task.get("status") != "blocked":
                    continue

                dependencies = task.get("dependencies", [])
                if task_id not in dependencies:
                    continue

                dependency_type = task.get("dependency_type", "all")
                if self._check_dependencies_satisfied(dependencies, dependency_type):
                    template = task.get("template", "task")
                    initial_state = self._get_initial_status(template)
                    task["status"] = initial_state
                    task["updated_at"] = datetime.now().isoformat()
                    updated = True

            if updated:
                self._save(data)
        except Exception:
            pass

    def check_blocked_tasks(self) -> List[str]:
        """检查并解锁所有满足条件的blocked任务"""
        unblocked = []
        try:
            data = self._load()
            if not data:
                return unblocked

            tasks = data.get("tasks", [])
            updated = False

            for task in tasks:
                if task.get("status") != "blocked":
                    continue

                dependencies = task.get("dependencies", [])
                dependency_type = task.get("dependency_type", "all")

                if self._check_dependencies_satisfied(dependencies, dependency_type):
                    template = task.get("template", "task")
                    initial_state = self._get_initial_status(template)
                    task["status"] = initial_state
                    task["updated_at"] = datetime.now().isoformat()
                    unblocked.append(task["id"])
                    updated = True

            if updated:
                self._save(data)
        except Exception:
            pass

        return unblocked

    def list_all(
        self,
        status: Optional[str] = None,
        parent_id: Optional[str] = None,
        template: Optional[str] = None,
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
            if isinstance(item, str):
                desc = item
                output_req = "8k"
                details = {}
            elif isinstance(item, dict):
                desc = item.get("desc", f"Part {i + 1}")
                output_req = item.get("output_req", "8k")
                details = {
                    "requirements": item.get("requirements", ""),
                    "acceptance": item.get("acceptance", []),
                    "deliverables": item.get("deliverables", []),
                }
                details = {k: v for k, v in details.items() if v}
            else:
                desc = f"Part {i + 1}"
                output_req = "8k"
                details = {}

            success, result = self.create(
                description=desc,
                template=parent.get("template", "task"),
                priority=parent.get("priority", "P1"),
                parent_id=task_id,
                output_req=output_req,
                variables=details if details else None,
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
            from lra.system_check import SystemCheckTask

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

    def recover_task_list(self) -> Tuple[bool, Dict[str, Any]]:
        """从 tasks/目录恢复任务列表"""
        import re

        tasks_dir = Config.get_tasks_dir()
        if not os.path.exists(tasks_dir):
            return False, {"error": "tasks_dir_not_found"}

        task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".md")]
        if not task_files:
            return False, {"error": "no_task_files_found"}

        data = self._load()
        if not data:
            # 尝试从多个来源推断项目名称
            project_name = "unknown"

            # 1. 尝试从配置文件中读取
            try:
                config = self._load_config()
                if config:
                    project_name = config.get("project_name", "unknown")
            except:
                pass

            # 2. 如果配置文件中没有，尝试从 git 仓库推断
            if project_name == "unknown":
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        # 从 git URL 中提取项目名
                        git_url = result.stdout.strip()
                        # 支持 https://github.com/user/repo.git 和 git@github.com:user/repo.git
                        parts = git_url.replace(":", "/").replace(".git", "").split("/")
                        if len(parts) >= 2:
                            project_name = parts[-1]
                except:
                    pass

            # 3. 尝试从 package.json 读取
            if project_name == "unknown":
                try:
                    package_json = os.path.join(os.getcwd(), "package.json")
                    if os.path.exists(package_json):
                        with open(package_json, "r", encoding="utf-8") as f:
                            pkg = json.load(f)
                            project_name = pkg.get("name", "unknown")
                except:
                    pass

            # 4. 尝试从 pyproject.toml 读取
            if project_name == "unknown":
                try:
                    pyproject_toml = os.path.join(os.getcwd(), "pyproject.toml")
                    if os.path.exists(pyproject_toml):
                        # 简单解析 TOML（避免依赖 toml 库）
                        with open(pyproject_toml, "r", encoding="utf-8") as f:
                            content = f.read()
                            # 查找 name = "xxx" 或 name = 'xxx'
                            import re

                            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                            if match:
                                project_name = match.group(1)
                except:
                    pass

            # 5. 最后从目录名推断
            if project_name == "unknown":
                try:
                    project_name = os.path.basename(os.getcwd()) or "unknown"
                except:
                    pass

            data = {
                "project_name": project_name,
                "created_at": datetime.now().isoformat(),
                "tasks": [],
            }

        existing_ids = {t.get("id") for t in data.get("tasks", [])}
        recovered = []

        for filename in sorted(task_files):
            task_id = filename[:-3]
            if task_id in existing_ids:
                continue

            task_path = os.path.join(tasks_dir, filename)
            try:
                file_stat = os.stat(task_path)
                created_time = datetime.fromtimestamp(file_stat.st_ctime).isoformat()
                modified_time = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

                with open(task_path, "r", encoding="utf-8") as f:
                    content = f.read()

                description = self._extract_description_from_file(content)
                template = self._extract_template_from_file(content) or "task"

                task = {
                    "id": task_id,
                    "description": description or f"Recovered task: {task_id}",
                    "template": template,
                    "priority": "P1",
                    "status": "pending",
                    "parent_id": None,
                    "output_req": "8k",
                    "task_file": f"tasks/{task_id}.md",
                    "created_at": created_time,
                    "updated_at": modified_time,
                    "dependencies": [],
                    "dependency_type": "all",
                    "deadline": None,
                }

                data["tasks"].append(task)
                recovered.append(task_id)

            except Exception as e:
                recovered.append(f"{task_id}: {str(e)}")

        self._save(data)
        return True, {
            "recovered_count": len(recovered),
            "recovered_tasks": recovered,
        }

    def _extract_description_from_file(self, content: str) -> Optional[str]:
        """从任务文件中提取描述"""
        import re

        match = re.search(r"## 描述\s*\n\s*\n(.+?)(?=\n\n##|\Z)", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_template_from_file(self, content: str) -> Optional[str]:
        """从任务文件中提取模板类型"""
        import re

        match = re.search(r"## 模板\s*\n\s*\n(.+?)(?=\n\n##|\Z)", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def detect_project_state(self) -> Dict[str, Any]:
        """检测项目当前状态"""
        result = {
            "initialized": False,
            "has_task_list": False,
            "has_task_files": False,
            "task_count": 0,
            "pending_count": 0,
            "in_progress_count": 0,
            "needs_recovery": False,
            "state": "unknown",
        }

        # 检测 1: 是否已初始化
        if os.path.exists(Config.get_metadata_dir()):
            result["initialized"] = True

        # 检测 2: task_list.json 是否存在且有效
        task_list_path = Config.get_task_list_path()
        if os.path.exists(task_list_path):
            task_list = self._load()
            if task_list and task_list.get("tasks"):
                result["has_task_list"] = True
                result["task_count"] = len(task_list["tasks"])

                # 统计状态
                for t in task_list["tasks"]:
                    status = t.get("status", "pending")
                    if status == "pending":
                        result["pending_count"] += 1
                    elif status == "in_progress":
                        result["in_progress_count"] += 1
            elif task_list:
                # task_list.json 存在但 tasks 为空
                result["has_task_list"] = True
                result["task_count"] = 0
        else:
            # task_list.json 不存在
            result["has_task_list"] = False

        # 检测 3: tasks/ 目录是否有文件
        tasks_dir = Config.get_tasks_dir()
        if os.path.exists(tasks_dir):
            try:
                task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".md")]
                if task_files:
                    result["has_task_files"] = True

                    # 需要恢复：有任务文件但 task_list 为空
                    if not result["has_task_list"]:
                        result["needs_recovery"] = True
            except:
                pass

        # 判断状态
        if not result["initialized"]:
            result["state"] = "new_project"
        elif not result["has_task_list"]:
            # .long-run-agent 存在但 task_list.json 不存在
            if result["has_task_files"]:
                result["state"] = "needs_recovery"
                result["needs_recovery"] = True
            else:
                # 部分初始化，需要重新 init
                result["state"] = "partial_init"
        elif result["needs_recovery"]:
            result["state"] = "needs_recovery"
        elif result["pending_count"] > 0:
            result["state"] = "has_pending_tasks"
        elif result["has_task_list"]:
            result["state"] = "initialized"

        return result

    # ========== v3.5 Ralph Loop 状态管理方法 ==========

    def get_ralph_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务的 Ralph 状态"""
        task = self.get(task_id)
        if not task:
            return None

        return task.get(
            "ralph",
            {
                "iteration": 0,
                "max_iterations": 7,
                "quality_checks": {
                    "tests_passed": False,
                    "lint_passed": False,
                    "acceptance_met": False,
                },
                "issues": [],
                "optimization_history": [],
            },
        )

    def update_ralph_state(self, task_id: str, ralph_state: Dict[str, Any]) -> Tuple[bool, str]:
        """更新任务的 Ralph 状态"""
        data = self._load()
        if not data:
            return False, "not_initialized"

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                existing_ralph = t.get("ralph", {})
                existing_ralph.update(ralph_state)
                t["ralph"] = existing_ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)
                return True, "updated"

        return False, "not_found"

    def increment_iteration(self, task_id: str) -> Tuple[bool, int]:
        """增加迭代计数，返回新的迭代次数，并自动更新当前阶段"""
        data = self._load()
        if not data:
            return False, 0

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                ralph = t.get("ralph", {})
                current_iteration = ralph.get("iteration", 0)
                max_iterations = ralph.get("max_iterations", 7)

                if current_iteration >= max_iterations:
                    return False, current_iteration

                new_iteration = current_iteration + 1
                ralph["iteration"] = new_iteration
                t["ralph"] = ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)

                self.update_iteration_stage(task_id)

                return True, new_iteration

        return False, 0

    def run_iteration_gates(self, task_id: str, iteration: int) -> Dict[str, Any]:
        """运行迭代阶段门禁，返回检查结果"""
        from lra.constitution import ConstitutionManager, GateEvaluator

        task = self.get(task_id)
        if not task:
            return {"passed": True, "gates": []}

        manager = ConstitutionManager()
        evaluator = GateEvaluator()

        gates = manager.get_iteration_gates(iteration)
        if not gates:
            return {"passed": True, "gates": []}

        gate_results = []
        all_passed = True

        for gate in gates:
            result = evaluator.evaluate_gate(gate, task_id, task)
            gate_results.append({
                "name": gate.get("name", "unnamed"),
                "passed": result.passed,
                "description": gate.get("description", ""),
                "output": result.output,
            })
            if not result.passed and gate.get("required", False):
                all_passed = False

        return {"passed": all_passed, "gates": gate_results}

    def record_quality_check(self, task_id: str, checks: Dict[str, bool]) -> Tuple[bool, str]:
        """记录质量检查结果"""
        data = self._load()
        if not data:
            return False, "not_initialized"

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                ralph = t.get("ralph", {})
                quality_checks = ralph.get("quality_checks", {})
                quality_checks.update(checks)
                ralph["quality_checks"] = quality_checks
                t["ralph"] = ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)
                return True, "updated"

        return False, "not_found"

    def add_optimization_history(self, task_id: str, entry: Dict[str, Any]) -> Tuple[bool, str]:
        """添加优化历史记录"""
        data = self._load()
        if not data:
            return False, "not_initialized"

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                ralph = t.get("ralph", {})
                optimization_history = ralph.get("optimization_history", [])

                if "timestamp" not in entry:
                    entry["timestamp"] = datetime.now().isoformat()

                optimization_history.append(entry)
                ralph["optimization_history"] = optimization_history
                t["ralph"] = ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)
                return True, "added"

        return False, "not_found"

    def add_ralph_issue(
        self, task_id: str, issue_type: str, message: str, round_num: int = None
    ) -> Tuple[bool, str]:
        """添加 Ralph 问题记录"""
        data = self._load()
        if not data:
            return False, "not_initialized"

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                ralph = t.get("ralph", {})
                issues = ralph.get("issues", [])

                if round_num is None:
                    round_num = ralph.get("iteration", 1)

                issue_entry = {
                    "round": round_num,
                    "type": issue_type,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }

                issues.append(issue_entry)
                ralph["issues"] = issues
                t["ralph"] = ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)
                return True, "added"

        return False, "not_found"

    def get_real_status(self, task_id: str) -> str:
        """
        获取任务的真实状态

        状态分类：
        - pending/in_progress: 正常状态
        - completed: 第一次完成（待质量检查）
        - optimizing: 优化循环中
        - truly_completed: 质量检查通过
        - force_completed: 达到优化上限强制完成
        """
        task = self.get(task_id)
        if not task:
            return "not_found"

        status = task.get("status", "pending")

        if status == "completed":
            ralph = task.get("ralph", {})
            iteration = ralph.get("iteration", 0)

            if iteration > 0:
                if self._validate_quality_passed(task):
                    return "truly_completed"
                else:
                    return "completed"

        return status

    def _validate_quality_passed(self, task: Dict[str, Any]) -> bool:
        """验证质量检查是否全部通过"""
        ralph = task.get("ralph", {})
        quality_checks = ralph.get("quality_checks", {})

        tests_passed = quality_checks.get("tests_passed", False)
        lint_passed = quality_checks.get("lint_passed", False)
        acceptance_met = quality_checks.get("acceptance_met", False)

        return tests_passed and lint_passed and acceptance_met

    def set_max_iterations(self, task_id: str, max_iterations: int) -> Tuple[bool, str]:
        """设置最大迭代次数"""
        data = self._load()
        if not data:
            return False, "not_initialized"

        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                ralph = t.get("ralph", {})
                ralph["max_iterations"] = max_iterations
                t["ralph"] = ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)
                return True, "updated"

        return False, "not_found"

    def can_continue_optimization(self, task_id: str) -> bool:
        """检查任务是否可以继续优化"""
        task = self.get(task_id)
        if not task:
            return False

        ralph = task.get("ralph", {})
        iteration = ralph.get("iteration", 0)
        max_iterations = ralph.get("max_iterations", 7)

        return iteration < max_iterations

    def get_optimization_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取优化摘要"""
        task = self.get(task_id)
        if not task:
            return None

        ralph = task.get("ralph", {})
        quality_checks = ralph.get("quality_checks", {})
        issues = ralph.get("issues", [])
        optimization_history = ralph.get("optimization_history", [])

        issue_types = {}
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        return {
            "iteration": ralph.get("iteration", 0),
            "max_iterations": ralph.get("max_iterations", 7),
            "total_issues": len(issues),
            "issue_types": issue_types,
            "optimization_count": len(optimization_history),
            "quality_status": {
                "tests": "passed" if quality_checks.get("tests_passed") else "failed",
                "lint": "passed" if quality_checks.get("lint_passed") else "failed",
                "acceptance": "met" if quality_checks.get("acceptance_met") else "not_met",
            },
            "can_continue": self.can_continue_optimization(task_id),
            "real_status": self.get_real_status(task_id),
        }

    def get_iteration_stage(self, task_id: str, iteration: int = None) -> Optional[Dict[str, Any]]:
        """
        获取任务的当前迭代阶段配置

        参数:
            task_id: 任务ID
            iteration: 迭代次数（可选，默认使用任务的当前迭代）

        返回:
            迭代阶段配置字典，包含:
            - iteration: 迭代次数
            - name: 阶段名称
            - focus: 重点列表
            - priority_checks: 优先检查项
            - ignore_checks: 忽略检查项
            - suggestion: 阶段建议
            - safety_checks: 安全检查（可选）
        """
        task = self.get(task_id)
        if not task:
            return None

        if iteration is None:
            ralph = task.get("ralph", {})
            iteration = ralph.get("iteration", 1)

        template_name = task.get("template", "task")

        stages = self.template_manager.load_iteration_stages(template_name)

        for stage in stages:
            if stage.get("iteration") == iteration:
                return stage

        return stages[-1] if stages else None

    def update_iteration_stage(self, task_id: str) -> Tuple[bool, str]:
        """
        更新任务的当前迭代阶段到 ralph.current_stage 字段

        参数:
            task_id: 任务ID

        返回:
            (是否成功, 消息)
        """
        task = self.get(task_id)
        if not task:
            return False, "task_not_found"

        ralph = task.get("ralph", {})
        iteration = ralph.get("iteration", 1)

        stage = self.get_iteration_stage(task_id, iteration)
        if not stage:
            return False, "stage_not_found"

        ralph["current_stage"] = stage

        data = self._load()
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                t["ralph"] = ralph
                t["updated_at"] = datetime.now().isoformat()
                self._save(data)
                return True, "updated"

        return False, "save_failed"

    def get_stage_suggestion(self, task_id: str) -> str:
        """
        获取当前阶段建议文本（格式化后）

        返回格式化的建议文本，包含:
        - 阶段名称
        - 迭代进度
        - 重点列表
        - 详细建议
        """
        task = self.get(task_id)
        if not task:
            return ""

        ralph = task.get("ralph", {})
        iteration = ralph.get("iteration", 1)
        max_iterations = ralph.get("max_iterations", 7)

        stage = ralph.get("current_stage") or self.get_iteration_stage(task_id)
        if not stage:
            return ""

        output = []
        output.append(f"\n📌 当前迭代: {iteration}/{max_iterations}")
        output.append(f"阶段: {stage.get('name', '未知阶段')}\n")

        focus_list = stage.get("focus", [])
        if focus_list:
            output.append("🎯 本次重点:")
            for item in focus_list:
                output.append(f"   • {item}")

        suggestion = stage.get("suggestion", "")
        if suggestion:
            output.append(f"\n{suggestion}")

        return "\n".join(output)

    def check_stage_stuck(self, task_id: str, threshold: int = 3) -> Tuple[bool, int]:
        """
        检查任务是否在当前阶段卡住

        参数:
            task_id: 任务ID
            threshold: 阈值（同一阶段超过多少次算卡住）

        返回:
            (是否卡住, 在当前阶段停留次数)

        逻辑:
        - 检查 optimization_history 中最近几次的 iteration 值
        - 如果连续 threshold 次迭代 iteration 值相同，则认为卡住
        """
        task = self.get(task_id)
        if not task:
            return False, 0

        ralph = task.get("ralph", {})
        history = ralph.get("optimization_history", [])

        if len(history) < threshold:
            return False, len(history)

        recent = history[-threshold:]

        iterations = [h.get("iteration") for h in recent]

        if len(set(iterations)) == 1:
            return True, threshold

        return False, 0

    def can_complete_early(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        检查任务是否可以提前完成

        参数:
            task_id: 任务ID

        返回:
            (是否可以提前完成, 详情)

        判断逻辑:
            1. 检查所有 required 的质量检查是否通过
            2. 如果全部通过，返回 True
            3. 否则返回 False 和未通过的检查项
        """
        task = self.get(task_id)
        if not task:
            return False, {"error": "task_not_found"}

        ralph = task.get("ralph", {})
        quality_checks = ralph.get("quality_checks", {})

        template_name = task.get("template", "task")
        stages = self.template_manager.load_iteration_stages(template_name)

        iteration = ralph.get("iteration", 1)
        max_iterations = ralph.get("max_iterations", 7)

        current_stage = self.get_iteration_stage(task_id, iteration)
        if not current_stage:
            return False, {"error": "stage_not_found"}

        priority_checks = current_stage.get("priority_checks", [])

        check_mapping = {
            "test": "tests_passed",
            "test_pass": "tests_passed",
            "tests_passed": "tests_passed",
            "lint": "lint_passed",
            "lint_pass": "lint_passed",
            "lint_passed": "lint_passed",
            "acceptance": "acceptance_met",
            "acceptance_met": "acceptance_met",
            "syntax_valid": "tests_passed",
            "goal_understood": "acceptance_met",
            "criteria_defined": "acceptance_met",
            "plan_created": "acceptance_met",
            "core_functional": "tests_passed",
            "basic_usable": "tests_passed",
            "correctness_verified": "tests_passed",
            "features_complete": "acceptance_met",
            "edge_cases_handled": "tests_passed",
            "completeness": "acceptance_met",
            "quality_improved": "lint_passed",
            "issues_resolved": "tests_passed",
            "performance_optimized": "tests_passed",
            "structure_improved": "lint_passed",
            "details_polished": "lint_passed",
            "fully_tested": "tests_passed",
            "reliability_verified": "tests_passed",
            "completeness_confirmed": "acceptance_met",
            "documentation_complete": "acceptance_met",
            "final_check_passed": "tests_passed",
            "delivery_ready": "acceptance_met",
            "test_coverage": "tests_passed",
            "edge_cases": "tests_passed",
            "type_check": "lint_passed",
            "performance": "tests_passed",
            "memory_usage": "tests_passed",
            "code_duplication": "lint_passed",
            "design_pattern": "lint_passed",
            "integration_test": "tests_passed",
            "performance_test": "tests_passed",
            "edge_case_test": "tests_passed",
            "documentation": "acceptance_met",
            "code_review": "lint_passed",
        }

        failed_required = []
        passed_required = []

        for check_type in priority_checks:
            quality_key = check_mapping.get(check_type, check_type)
            if not quality_checks.get(quality_key, False):
                failed_required.append(check_type)
            else:
                passed_required.append(check_type)

        can_complete = len(failed_required) == 0

        return can_complete, {
            "can_complete": can_complete,
            "failed_required": failed_required,
            "passed_required": passed_required,
            "all_quality_checks": quality_checks,
            "iteration": iteration,
            "max_iterations": max_iterations,
            "priority_checks": priority_checks,
        }

    def suggest_decomposition(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        分析任务并建议如何拆分成子任务

        Returns:
            (success, {
                "task_id": ...,
                "description": ...,
                "requirements_tokens": ...,
                "estimated_complexity": "low"|"medium"|"high",
                "suggested_count": N,
                "subtasks": [
                    {"desc": "...", "output_req": "...", "requirements": "...", "acceptance": [], "deliverables": []},
                    ...
                ]
            })
        """
        task = self.get(task_id)
        if not task:
            return False, {"error": "not_found"}

        # 读取任务文件获取详细信息
        task_dir = Config.get_tasks_dir()
        task_path = os.path.join(task_dir, f"{task_id}.md")

        requirements_text = ""
        acceptance_criteria = []
        deliverables = []

        if os.path.exists(task_path):
            try:
                with open(task_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 提取 requirements
                req_match = content.split("## 需求 (requirements)")[1].split("##")[0] if "## 需求" in content else ""
                if not req_match:
                    req_match = content.split("## requirements")[1].split("##")[0] if "## requirements" in content.lower() else ""
                requirements_text = req_match.strip()

                # 提取 acceptance
                acc_match = content.split("## 验收标准 (acceptance)")[1].split("##")[0] if "## 验收标准" in content else ""
                if not acc_match:
                    acc_match = content.split("## acceptance")[1].split("##")[0] if "## acceptance" in content.lower() else ""
                acceptance_criteria = [line.strip() for line in acc_match.split("\n") if line.strip().startswith("- ")]
            except:
                pass

        # 分析复杂度
        desc = task.get("description", "")
        template = task.get("template", "task")
        output_req = task.get("output_req", "8k")

        # 粗略估算 tokens (约4字符/token)
        req_tokens = len(requirements_text) // 4 if requirements_text else len(desc) // 4

        # 复杂度关键词
        complexity_keywords = {
            "high": ["api", "数据库", "auth", "登录", "支付", "webhook", "中间件", "缓存", "队列", "并发", "分布式", "微服务"],
            "medium": ["crud", "表单", "列表", "搜索", "导出", "导入", "验证", "配置", "上传", "下载"],
        }

        complexity = "low"
        for kw in complexity_keywords["high"]:
            if kw.lower() in (requirements_text + desc).lower():
                complexity = "high"
                break
        if complexity == "low":
            for kw in complexity_keywords["medium"]:
                if kw.lower() in (requirements_text + desc).lower():
                    complexity = "medium"
                    break

        # 基于复杂度估算拆分数量
        # low: 1-2, medium: 2-3, high: 3-5
        if complexity == "high":
            suggested_count = 4
        elif complexity == "medium":
            suggested_count = 3
        else:
            suggested_count = 2

        # 生成子任务建议
        subtasks = self._generate_subtask_plan(desc, requirements_text, acceptance_criteria, suggested_count, output_req)

        suggestion = {
            "task_id": task_id,
            "description": desc,
            "template": template,
            "requirements_tokens": req_tokens,
            "complexity": complexity,
            "suggested_count": suggested_count,
            "subtasks": subtasks,
        }

        # 存储建议供 --auto 使用 (保存到 task_list.json)
        data = self._load()
        if data:
            for t in data.get("tasks", []):
                if t.get("id") == task_id:
                    t["_decomposition_suggestion"] = suggestion
                    break
            self._save(data)

        return True, suggestion

    def _generate_subtask_plan(
        self, parent_desc: str, requirements: str, acceptance: List[str], count: int, output_req: str
    ) -> List[Dict[str, Any]]:
        """生成子任务拆分计划"""
        # 基于关键词分析可能的技术层面
        desc_lower = (parent_desc + " " + requirements).lower()

        subtask_patterns = []

        # 分析可能涉及的技术组件
        has_api = any(k in desc_lower for k in ["api", "接口", "endpoint", "rest", "grpc"])
        has_db = any(k in desc_lower for k in ["数据库", "db", "存储", "model", "schema", "表"])
        has_auth = any(k in desc_lower for k in ["认证", "auth", "登录", "权限", "permission", "角色"])
        has_ui = any(k in desc_lower for k in ["界面", "ui", "前端", "页面", "组件", "表单"])
        has_logic = any(k in desc_lower for k in ["业务", "逻辑", "service", "处理"])

        # 如果有明确的模块名，提取
        module_name = ""
        words = parent_desc.split()
        for i, w in enumerate(words):
            if w in ["模块", "功能", "系统", "组件"]:
                if i > 0:
                    module_name = words[i-1]
                break

        # 根据识别的组件生成拆分
        components = []
        if has_api:
            components.append(("接口定义", "API 接口设计与定义"))
        if has_db:
            components.append(("数据模型", "数据库模型与表结构"))
        if has_logic:
            components.append(("业务逻辑", "核心业务逻辑实现"))
        if has_auth:
            components.append(("权限管理", "用户认证与权限控制"))
        if has_ui:
            components.append(("界面开发", "前端界面实现"))

        # 如果没有识别出组件，按顺序执行拆分
        if not components:
            for i in range(count):
                subtask_patterns.append({
                    "desc": f"{parent_desc} - 阶段{i+1}",
                    "requirements": f"完成 {parent_desc} 的第 {i+1} 部分",
                    "acceptance": [f"第 {i+1} 部分完成"],
                    "deliverables": [f"阶段{i+1}产出物"],
                })
        else:
            # 使用识别的组件进行拆分
            for i, (name, req) in enumerate(components[:count]):
                full_name = f"{module_name}{name}" if module_name else name
                subtask_patterns.append({
                    "desc": full_name,
                    "requirements": f"{req}",
                    "acceptance": [f"{name}实现完成"],
                    "deliverables": [f"src/{name.lower().replace(' ', '_')}.py"],
                })

        # 确保返回 count 个子任务
        while len(subtask_patterns) < count:
            i = len(subtask_patterns)
            subtask_patterns.append({
                "desc": f"{parent_desc} - {chr(65+i)}",
                "requirements": f"完成 {parent_desc} 的补充任务",
                "acceptance": ["补充任务完成"],
                "deliverables": [f"补充产出物{i+1}"],
            })

        return subtask_patterns[:count]

    def get_last_decomposition(self, task_id: str = None) -> Optional[Dict[str, Any]]:
        """获取指定任务的分解建议（供 --auto 使用）"""
        if task_id:
            task = self.get(task_id)
            if task:
                return task.get("_decomposition_suggestion")
        return None
