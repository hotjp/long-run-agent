#!/usr/bin/env python3
"""
LRA CLI v3.1
通用任务管理框架 - AI Agent 优化版
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List

from .config import CURRENT_VERSION, Config, validate_project_initialized, get_agent_id
from .task_manager import TaskManager
from .template_manager import TemplateManager
from .records_manager import RecordsManager
from .locks_manager import LocksManager
from .batch_lock_manager import BatchLockManager

try:
    from .system_check import SystemCheckTask, ConfigManager
    HAS_SYSTEM_CHECK = True
except:
    HAS_SYSTEM_CHECK = False


AGENT_GUIDE = """
LRA - AI Agent Task Manager v3.3

## QUICK START
$ lra context --output-limit 8k

## CORE COMMANDS
lra init --name <name>         Initialize project
lra context [--output-limit 4k|8k|16k|32k|128k]
lra list [--status X] [--template X] [--compact]
lra create <desc> --template <name> [opts]
lra show <id> [--include-records]
lra set <id> <status>          Update status
lra split <id> --plan '<json>' Split task
lra search <keyword>           Search tasks

## LOCK COMMANDS
lra claim <id>                 Claim task
lra publish <id>               Release children
lra pause <id> [--note]        Pause + checkpoint
lra resume <id>                View checkpoint
lra checkpoint <id> [--note]   Save progress
lra heartbeat <id>             Keep-alive (every 5min)

## TEMPLATE COMMANDS
lra template list              List templates
lra template show <name>       Template details
lra template create <name>     Create template

## DEPENDENCY COMMANDS
lra deps <id>                  View task dependencies
lra deps <id> --dependents     View dependent tasks
lra check-blocked              Check and unblock tasks

## PRIORITY COMMANDS
lra set-priority <id> <P0|P1|P2|P3>

## BATCH COMMANDS (v3.3.1)
lra batch set <status> <ids...> [--auto-lock] [--wait]    Batch update status
lra batch claim <ids...> [--auto-lock] [--wait]           Batch claim tasks
lra batch delete <ids...> [--auto-lock]                   Batch delete tasks

## BATCH LOCK MANAGEMENT
lra batch-lock status                           View lock status
lra batch-lock acquire --operation X --tasks X  Acquire lock
lra batch-lock release                          Release lock
lra batch-lock heartbeat [--extend 30000]       Extend lock
lra batch-lock recover                          Recover expired lock
lra batch-lock logs [--limit 20]                View operation logs

## MULTI-AGENT CONCURRENCY
- 批量操作自动获取锁（--auto-lock 默认启用）
- 锁超时 30 秒自动释放
- 使用 --wait 等待其他 Agent 完成
- 单次批量操作建议 ≤5 个任务（50ms 延迟保证）

## V3.3.0 SYSTEM CHECK
lra system-check               Run system preflight check
lra system-check --report      View check report
lra system-check --full        Force re-run check
lra analyze-module <name>      Analyze specific module

## CREATE TASK OPTIONS
--dependencies task_001,task_002  Depend on other tasks
--dependency-type all|any        All or any dependency
--deadline 2026-02-25T12:00:00   Deadline
--priority P0|P1|P2|P3          Priority
--variables '{"key": "val"}'     Template variables

## STATUS FLOW
- blocked: Waiting for dependencies
- pending: Ready to claim
- in_progress: Being worked on
- completed: Done (final state)

## MULTI-AGENT (Basic)
- claim = exclusive lock
- publish = release children
- orphaned (no heartbeat 15min) = can be claimed

## JSON OUTPUT
All commands support --json flag
"""


def output(data: Any, json_mode: bool = False):
    if json_mode:
        print(json.dumps(data, ensure_ascii=False, indent=None))
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                print(f"{k}:")
                for item in v:
                    print(f"  - {item}")
            else:
                print(f"{k}: {v}")
    else:
        print(data)


class LRACLI:
    def __init__(self):
        self.task_manager = TaskManager()
        self.template_manager = TemplateManager()
        self.records_manager = RecordsManager()
        self.locks_manager = LocksManager()
        self.batch_lock_manager = BatchLockManager()
        self.system_check_available = HAS_SYSTEM_CHECK

    def _check_project(self) -> bool:
        ok, _ = validate_project_initialized()
        return ok

    def cmd_init(self, name: str, json_mode: bool = False):
        success, msg = self.task_manager.init_project(name)
        output({"ok": success, "message": msg}, json_mode)

    def cmd_context(self, output_limit: str = "8k", json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        context = self.task_manager.get_context(output_limit)
        locks = self.locks_manager.get_all_locks()
        
        # 添加锁状态信息到 can_take 任务
        for task in context.get("can_take", []):
            lock = locks.get(task["id"])
            if lock:
                task["lock_status"] = lock.get("status", "free")
            else:
                task["lock_status"] = "free"
        
        # 添加锁状态信息到 in_progress 任务
        for task in context.get("in_progress", []):
            lock = locks.get(task["id"])
            if lock:
                task["lock_status"] = lock.get("status", "free")
                task["last_heartbeat"] = lock.get("last_heartbeat")
            else:
                task["lock_status"] = "free"
        
        resumable = self.locks_manager.get_resumable()
        if resumable:
            context["resumable"] = resumable
        output(context, json_mode)

    def cmd_list(self, status: str = None, template: str = None, compact: bool = False, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        tasks = self.task_manager.list_all(status=status, template=template)
        if json_mode:
            output(
                [
                    {
                        "id": t["id"],
                        "status": t.get("status"),
                        "template": t.get("template"),
                        "desc": t.get("description", "")[:50],
                    }
                    for t in tasks
                ],
                json_mode,
            )
        elif compact:
            # 紧凑模式：单行显示所有关键信息
            for t in tasks:
                priority = t.get("priority", "P1")
                status = t.get("status", "pending")
                template = t.get("template", "task")
                desc = t.get("description", "")[:60]
                print(f"{t['id']:12} [{status:12}] [{priority}] [{template:15}] {desc}")
        else:
            for t in tasks:
                print(
                    f"{t['id']}: {t.get('status', 'pending')} [{t.get('template', 'task')}] {t.get('description', '')[:40]}"
                )

    def cmd_create(
        self,
        description: str,
        template: str = "task",
        priority: str = "P1",
        output_req: str = "8k",
        parent: str = None,
        dependencies: str = None,
        dependency_type: str = "all",
        deadline: str = None,
        variables: str = None,
        json_mode: bool = False,
    ):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        # 解析依赖
        deps = []
        if dependencies:
            deps = [d.strip() for d in dependencies.split(",")]

        # 解析变量
        vars_dict = {}
        if variables:
            try:
                vars_dict = json.loads(variables)
            except:
                output({"error": "invalid_variables_json"}, json_mode)
                return

        success, result = self.task_manager.create(
            description=description,
            template=template,
            priority=priority,
            parent_id=parent,
            output_req=output_req,
            dependencies=deps,
            deadline=deadline,
            dependency_type=dependency_type,
            variables=vars_dict if vars_dict else None,
        )
        if success:
            output({"ok": True, "task": result}, json_mode)
        else:
            output(result, json_mode)

    def cmd_show(self, task_id: str, include_records: bool = False, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        task = self.task_manager.show(task_id)
        if not task:
            output({"error": "not_found"}, json_mode)
            return
        
        # 添加锁状态信息
        lock = self.locks_manager.get_lock(task_id)
        if lock:
            task["lock_status"] = lock.get("status", "free")
            task["lock_info"] = {
                "claimed_at": lock.get("claimed_at"),
                "last_heartbeat": lock.get("last_heartbeat"),
                "session_id": lock.get("session_id"),
            }
        
        # 添加依赖关系
        dependencies = task.get("dependencies", [])
        if dependencies:
            dep_details = []
            for dep_id in dependencies:
                dep_task = self.task_manager.get(dep_id)
                if dep_task:
                    dep_details.append({
                        "id": dep_id,
                        "status": dep_task.get("status"),
                        "desc": dep_task.get("description", "")[:50],
                    })
            task["dependency_details"] = dep_details
        
        # 添加任务记录（如果请求）
        if include_records:
            records = self.records_manager.get(task_id)
            if records:
                task["records"] = records
        
        output(task, json_mode)

    def cmd_set(self, task_id: str, status: str, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        # 先检查当前状态
        current_task = self.task_manager.get(task_id)
        if not current_task:
            output({"error": "not_found"}, json_mode)
            return
        
        current_status = current_task.get("status", "pending")
        if current_status == status:
            output({"ok": True, "message": "already_in_target_status", "current_status": status, "task_id": task_id}, json_mode)
            return

        success, msg = self.task_manager.update_status(task_id, status)
        if success:
            final_states = self._get_final_states_for_task(task_id)
            if status in final_states:
                self.locks_manager.release(task_id)
        output({"ok": success, "status": msg}, json_mode)

    def _get_final_states_for_task(self, task_id: str) -> List[str]:
        task = self.task_manager.get(task_id)
        if not task:
            return []
        template = task.get("template", "task")
        transitions = self.template_manager.get_transitions_for_template(template)
        all_states = self.template_manager.get_states_for_template(template)
        return [s for s in all_states if not transitions.get(s)]

    def cmd_split(self, task_id: str, plan: str = None, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        if not plan:
            task = self.task_manager.get(task_id)
            if task:
                output(
                    {
                        "task_id": task_id,
                        "desc": task.get("description", ""),
                        "output_req": task.get("output_req", "8k"),
                        "hint": 'provide --plan as JSON array: [{"desc": "part1", "output_req": "4k"}, ...]',
                    },
                    json_mode,
                )
            else:
                output({"error": "not_found"}, json_mode)
            return

        try:
            split_plan = json.loads(plan)
        except:
            output({"error": "invalid_json_plan"}, json_mode)
            return

        success, result = self.task_manager.split_task(task_id, split_plan)
        output(result if success else {"error": "split_failed", "detail": result}, json_mode)

    def cmd_claim(self, task_id: str, json_mode: bool = False):
        can_claim, reason = self.locks_manager.can_claim(task_id)
        if not can_claim:
            output({"error": "cannot_claim", "reason": reason}, json_mode)
            return

        success, result = self.locks_manager.claim(task_id)
        output(result if success else {"error": "claim_failed", "detail": result}, json_mode)

    def cmd_publish(self, task_id: str, json_mode: bool = False):
        success, msg = self.locks_manager.publish_children(task_id)
        output({"ok": success, "message": msg}, json_mode)

    def cmd_pause(self, task_id: str, note: str = "", json_mode: bool = False):
        success, msg = self.locks_manager.pause(task_id, note=note)
        output({"ok": success, "message": msg}, json_mode)

    def cmd_checkpoint(self, task_id: str, note: str = "", json_mode: bool = False):
        success, msg = self.locks_manager.checkpoint(task_id, note=note)
        output({"ok": success, "message": msg}, json_mode)

    def cmd_resume(self, task_id: str, json_mode: bool = False):
        result = self.locks_manager.resume(task_id)
        if result:
            output(result, json_mode)
        else:
            output({"error": "not_resumable"}, json_mode)

    def cmd_heartbeat(self, task_id: str, json_mode: bool = False):
        success, msg = self.locks_manager.heartbeat(task_id)
        output({"ok": success, "message": msg}, json_mode)

    def cmd_record(self, task_id: str, auto: bool = False, desc: str = "", json_mode: bool = False):
        if auto:
            result = self.records_manager.auto_record(task_id, desc)
        else:
            self.records_manager.add(task_id, desc=desc)
            result = {"task_id": task_id, "recorded": True}
        output(result, json_mode)

    def cmd_template_list(self, json_mode: bool = False):
        templates = self.template_manager.list_templates()
        if json_mode:
            output(templates, json_mode)
        else:
            for t in templates:
                print(f"{t['name']}: {t.get('description', '')}")

    def cmd_template_show(self, name: str, json_mode: bool = False):
        template = self.template_manager.get_template(name)
        if template:
            if json_mode:
                output(template, json_mode)
            else:
                print(f"name: {template.get('name')}")
                print(f"description: {template.get('description', '')}")
                print(f"states: {template.get('states', [])}")
                print(f"transitions:")
                for k, v in template.get("transitions", {}).items():
                    print(f"  {k} -> {v}")
                print(f"\nstructure:")
                print(template.get("structure", ""))
        else:
            output({"error": "not_found"}, json_mode)

    def cmd_template_create(self, name: str, from_template: str = None, json_mode: bool = False):
        success, msg = self.template_manager.create_template(name, from_template)
        output({"ok": success, "path": msg} if success else {"ok": False, "error": msg}, json_mode)

    def cmd_template_delete(self, name: str, json_mode: bool = False):
        success, msg = self.template_manager.delete_template(name)
        output({"ok": success, "message": msg}, json_mode)

    def cmd_deps(self, task_id: str, dependents: bool = False, json_mode: bool = False):
        """查看任务依赖"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        task = self.task_manager.get(task_id)
        if not task:
            output({"error": "not_found"}, json_mode)
            return

        if dependents:
            # 查找依赖此任务的任务
            all_tasks = self.task_manager.list_all()
            dependents_list = [
                {"id": t["id"], "description": t.get("description", "")[:50]}
                for t in all_tasks
                if task_id in t.get("dependencies", [])
            ]
            output({"task_id": task_id, "dependents": dependents_list}, json_mode)
        else:
            # 查看此任务依赖的其他任务
            dependencies = task.get("dependencies", [])
            dep_details = []
            for dep_id in dependencies:
                dep_task = self.task_manager.get(dep_id)
                if dep_task:
                    dep_details.append(
                        {
                            "id": dep_id,
                            "status": dep_task.get("status", "unknown"),
                            "description": dep_task.get("description", "")[:50],
                        }
                    )
            output(
                {
                    "task_id": task_id,
                    "dependency_type": task.get("dependency_type", "all"),
                    "dependencies": dep_details,
                },
                json_mode,
            )

    def cmd_check_blocked(self, json_mode: bool = False):
        """检查并解锁 blocked 任务"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        unblocked = self.task_manager.check_blocked_tasks()
        output({"ok": True, "unblocked": unblocked}, json_mode)

    def cmd_set_priority(self, task_id: str, priority: str, json_mode: bool = False):
        """设置任务优先级"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return
        
        task = self.task_manager.get(task_id)
        if not task:
            output({"error": "not_found"}, json_mode)
            return
        
        # 直接更新任务数据
        data = self.task_manager._load()
        if not data:
            output({"error": "not_initialized"}, json_mode)
            return
        
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                t["priority"] = priority
                t["updated_at"] = datetime.now().isoformat()
                self.task_manager._save(data)
                output({"ok": True, "task_id": task_id, "priority": priority}, json_mode)
                return
        
        output({"error": "not_found"}, json_mode)
    

    def cmd_batch(self, operation: str, status: str = None, task_ids: List[str] = None, 
                  auto_lock: bool = True, wait: bool = False, json_mode: bool = False):
        """批量操作（支持自动锁）"""
        import sys
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return
        
        if not task_ids:
            output({"error": "no_task_ids"}, json_mode)
            return
        
        # 检查批量大小
        allowed, warning = self.batch_lock_manager.check_batch_size(task_ids)
        if warning:
            print(f"⚠️  WARNING: {warning}", file=sys.stderr)
        
        agent_id = get_agent_id()
        
        # 自动获取锁
        if auto_lock:
            acquired, reason, lock_info = self.batch_lock_manager.acquire(
                agent_id, f"batch_{operation}", task_ids, wait=wait
            )
            if not acquired:
                if reason == "lock_held_by_other":
                    output({
                        "error": "lock_held_by_other",
                        "hint": "使用 --wait 选项等待或使用 batch-lock 命令手动管理锁",
                        "holder": lock_info["holder"],
                        "remaining_ms": lock_info["remaining_ms"]
                    }, json_mode)
                else:
                    output({"error": reason}, json_mode)
                return
        
        try:
            results = []
            for task_id in task_ids:
                if operation == "set":
                    if not status:
                        results.append({"task_id": task_id, "error": "missing_status"})
                        continue
                    current_task = self.task_manager.get(task_id)
                    if not current_task:
                        results.append({"task_id": task_id, "error": "not_found"})
                        continue
                    
                    current_status = current_task.get("status", "pending")
                    if current_status == status:
                        results.append({"task_id": task_id, "message": "already_in_target_status", "current_status": status})
                    else:
                        # 验证状态流转
                        template = current_task.get("template", "task")
                        if not self.template_manager.validate_transition(template, current_status, status):
                            results.append({
                                "task_id": task_id,
                                "error": "invalid_transition",
                                "from": current_status,
                                "to": status,
                                "template": template
                            })
                            continue
                        
                        success, msg = self.task_manager.update_status(task_id, status)
                        results.append({"task_id": task_id, "ok": success, "status": msg})
                
                elif operation == "delete":
                    success = self.task_manager.delete(task_id)
                    results.append({"task_id": task_id, "ok": success})
                
                elif operation == "claim":
                    # 批量 claim
                    can_claim, reason = self.locks_manager.can_claim(task_id)
                    if not can_claim:
                        results.append({"task_id": task_id, "error": "cannot_claim", "reason": reason})
                        continue
                    
                    success, result = self.locks_manager.claim(task_id)
                    results.append({"task_id": task_id, "ok": success, "result": result})
            
            output({"operation": operation, "results": results, "total": len(results)}, json_mode)
        finally:
            # 自动释放锁
            if auto_lock:
                self.batch_lock_manager.release(agent_id)
    
    def cmd_search(self, query: str, status: str = None, json_mode: bool = False):
        """搜索任务"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return
        
        all_tasks = self.task_manager.list_all()
        query_lower = query.lower()
        
        matched = []
        for task in all_tasks:
            # 按状态过滤
            if status and task.get("status") != status:
                continue
            
            # 搜索标题和描述
            desc = task.get("description", "").lower()
            task_id = task.get("id", "").lower()
            
            if query_lower in desc or query_lower in task_id:
                matched.append({
                    "id": task["id"],
                    "status": task.get("status"),
                    "desc": task.get("description", "")[:80],
                    "priority": task.get("priority", "P1"),
                })
        
        output({"query": query, "status_filter": status, "results": matched, "count": len(matched)}, json_mode)


    
    # ========== 批量操作锁命令 ==========
    
    def cmd_batch_lock_status(self, json_mode: bool = False):
        """查看批量锁状态"""
        status = self.batch_lock_manager.status()
        output(status, json_mode)
    
    def cmd_batch_lock_acquire(
        self,
        operation: str,
        tasks: str,
        timeout: int = 30000,
        wait: bool = False,
        json_mode: bool = False
    ):
        """获取批量锁"""
        task_ids = [t.strip() for t in tasks.split(",")]
        agent_id = get_agent_id()
        
        # 检查批量大小
        allowed, warning = self.batch_lock_manager.check_batch_size(task_ids)
        if warning:
            print(f"⚠️  WARNING: {warning}", file=sys.stderr)
        
        success, reason, info = self.batch_lock_manager.acquire(
            agent_id, operation, task_ids, timeout, wait
        )
        
        if success:
            output({
                "ok": True,
                "message": reason,
                "lock": info,
                "agent_id": agent_id
            }, json_mode)
        else:
            if reason == "lock_held_by_other":
                output({
                    "ok": False,
                    "error": reason,
                    "hint": "等待其他 Agent 完成操作，或使用 --wait 选项",
                    "holder": info["holder"],
                    "remaining_ms": info["remaining_ms"],
                    "operation_type": info["operation_type"]
                }, json_mode)
            else:
                output({"ok": False, "error": reason}, json_mode)
    
    def cmd_batch_lock_release(self, json_mode: bool = False):
        """释放批量锁"""
        agent_id = get_agent_id()
        success, reason = self.batch_lock_manager.release(agent_id)
        output({"ok": success, "message": reason}, json_mode)
    
    def cmd_batch_lock_heartbeat(self, extend: int = 30000, json_mode: bool = False):
        """心跳续期"""
        agent_id = get_agent_id()
        success, reason = self.batch_lock_manager.heartbeat(agent_id, extend)
        output({"ok": success, "message": reason}, json_mode)
    
    def cmd_batch_lock_recover(self, json_mode: bool = False):
        """强制回收获期锁"""
        agent_id = get_agent_id()
        success, reason = self.batch_lock_manager.recover(agent_id)
        output({"ok": success, "message": reason}, json_mode)
    
    def cmd_batch_lock_logs(self, limit: int = 20, json_mode: bool = False):
        """查看操作日志"""
        logs = self.batch_lock_manager.get_logs(limit)
        output({"logs": logs, "count": len(logs)}, json_mode)


        # ========== v3.3.0 新增命令：系统预检 ==========
    
    def cmd_system_check(self, full: bool = False, report: bool = False, json_mode: bool = False):
        """执行或查看系统预检"""
        if not self.system_check_available:
            output({"error": "system_check_not_available"}, json_mode)
            return
        
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return
        
        if report:
            # 查看报告
            tm_report = self.task_manager.get_system_check_report()
            if tm_report:
                output(tm_report, json_mode)
            else:
                output({"error": "no_report", "hint": "run 'lra system-check' first"}, json_mode)
        else:
            # 执行预检
            if full or not self.task_manager.has_system_check():
                try:
                    project_path = os.getcwd()
                    checker = SystemCheckTask(project_path=project_path)
                    report_data = checker.run()
                    output({"ok": True, "report": report_data}, json_mode)
                except Exception as e:
                    output({"error": str(e)}, json_mode)
            else:
                output({"info": "report_exists", "hint": "use --report to view or --full to re-run"}, json_mode)
    
    def cmd_analyze_module(self, module_name: str, json_mode: bool = False):
        """分析指定模块"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return
        
        # 简单实现：查找包含模块名的任务
        tasks = self.task_manager.list_all()
        module_tasks = [
            t for t in tasks
            if module_name.lower() in t.get("description", "").lower()
        ]
        
        output({
            "module": module_name,
            "tasks": [
                {"id": t["id"], "desc": t.get("description", "")[:50], "status": t.get("status")}
                for t in module_tasks
            ],
            "count": len(module_tasks),
        }, json_mode)


def main():
    parser = argparse.ArgumentParser(
        description="LRA - AI Agent Task Manager v3.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=AGENT_GUIDE,
    )
    parser.add_argument("--json", action="store_true", help="JSON output")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_p = subparsers.add_parser("init", help="Initialize project")
    init_p.add_argument("--name", required=True)

    # context
    ctx_p = subparsers.add_parser("context", help="Get project context")
    ctx_p.add_argument("--output-limit", default="8k", choices=["4k", "8k", "16k", "32k", "128k"])

    # list
    list_p = subparsers.add_parser("list", help="List tasks")
    list_p.add_argument("--status")
    list_p.add_argument("--template")
    list_p.add_argument("--compact", action="store_true", help="Compact output")

    # create
    create_p = subparsers.add_parser("create", help="Create task")
    create_p.add_argument("description")
    create_p.add_argument("--template", default="task")
    create_p.add_argument("--priority", default="P1", choices=["P0", "P1", "P2", "P3"])
    create_p.add_argument("--output-req", default="8k")
    create_p.add_argument("--parent", default=None)
    create_p.add_argument("--dependencies", default=None, help="Comma-separated task IDs")
    create_p.add_argument("--dependency-type", default="all", choices=["all", "any"])
    create_p.add_argument("--deadline", default=None)
    create_p.add_argument("--variables", default=None, help="JSON string of template variables")

    # show
    show_p = subparsers.add_parser("show", help="Show task")
    show_p.add_argument("task_id")
    show_p.add_argument("--include-records", action="store_true", help="Include task records")

    # set
    set_p = subparsers.add_parser("set", help="Update status")
    set_p.add_argument("task_id")
    set_p.add_argument("status")

    # split
    split_p = subparsers.add_parser("split", help="Split task")
    split_p.add_argument("task_id")
    split_p.add_argument("--plan", help="JSON array of split parts")

    # claim
    subparsers.add_parser("claim", help="Claim task").add_argument("task_id")

    # publish
    subparsers.add_parser("publish", help="Publish children").add_argument("task_id")

    # pause
    pause_p = subparsers.add_parser("pause", help="Pause task")
    pause_p.add_argument("task_id")
    pause_p.add_argument("--note", default="")

    # checkpoint
    ckpt_p = subparsers.add_parser("checkpoint", help="Save checkpoint")
    ckpt_p.add_argument("task_id")
    ckpt_p.add_argument("--note", default="")

    # resume
    subparsers.add_parser("resume", help="Resume task").add_argument("task_id")

    # heartbeat
    subparsers.add_parser("heartbeat", help="Keep-alive").add_argument("task_id")

    # record
    record_p = subparsers.add_parser("record", help="Record changes")
    record_p.add_argument("task_id")
    record_p.add_argument("--auto", action="store_true")
    record_p.add_argument("--desc", default="")

    # template
    template_p = subparsers.add_parser("template", help="Template management")
    template_sub = template_p.add_subparsers(dest="template_cmd")
    template_sub.add_parser("list")
    template_sub.add_parser("show").add_argument("name")
    tc_p = template_sub.add_parser("create")
    tc_p.add_argument("name")
    tc_p.add_argument("--from", dest="from_template")
    template_sub.add_parser("delete").add_argument("name")

    # guide & version
    subparsers.add_parser("guide", help="Show agent guide")
    subparsers.add_parser("version", help="Show version")
    
    # deps
    deps_p = subparsers.add_parser("deps", help="View task dependencies")
    deps_p.add_argument("task_id")
    deps_p.add_argument("--dependents", action="store_true", help="Show tasks that depend on this task")
    
    # check-blocked
    subparsers.add_parser("check-blocked", help="Check and unblock blocked tasks")
    
    # set-priority
    sp_p = subparsers.add_parser("set-priority", help="Set task priority")
    sp_p.add_argument("task_id")
    sp_p.add_argument("priority", choices=["P0", "P1", "P2", "P3"])
    
    # batch
    batch_p = subparsers.add_parser("batch", help="Batch operations")
    batch_sub = batch_p.add_subparsers(dest="batch_cmd")
    
    # batch set
    batch_set_p = batch_sub.add_parser("set", help="Batch set status")
    batch_set_p.add_argument("status")
    batch_set_p.add_argument("task_ids", nargs="+")
    batch_set_p.add_argument("--auto-lock", action="store_true", dest="auto_lock", default=True, help="Auto acquire batch lock")
    batch_set_p.add_argument("--no-auto-lock", action="store_false", dest="auto_lock", help="Disable auto lock")
    batch_set_p.add_argument("--wait", action="store_true", help="Wait for lock if held")
    
    # batch delete
    batch_del_p = batch_sub.add_parser("delete", help="Batch delete tasks")
    batch_del_p.add_argument("task_ids", nargs="+")
    batch_del_p.add_argument("--auto-lock", action="store_true", dest="auto_lock", default=True, help="Auto acquire batch lock")
    batch_del_p.add_argument("--wait", action="store_true", help="Wait for lock if held")
    
    # batch claim
    batch_claim_p = batch_sub.add_parser("claim", help="Batch claim tasks")
    batch_claim_p.add_argument("task_ids", nargs="+")
    batch_claim_p.add_argument("--auto-lock", action="store_true", dest="auto_lock", default=True, help="Auto acquire batch lock")
    batch_claim_p.add_argument("--wait", action="store_true", help="Wait for lock if held")
    # search
    search_p = subparsers.add_parser("search", help="Search tasks")
    search_p.add_argument("query")
    search_p.add_argument("--status", help="Filter by status")
    

    # batch-lock
    bl_p = subparsers.add_parser("batch-lock", help="Batch lock management")
    bl_sub = bl_p.add_subparsers(dest="batch_lock_cmd")
    
    # batch-lock status
    bl_sub.add_parser("status")
    
    # batch-lock acquire
    bl_acquire = bl_sub.add_parser("acquire", help="Acquire batch lock")
    bl_acquire.add_argument("--operation", required=True, choices=["batch_claim", "batch_set", "batch_delete"])
    bl_acquire.add_argument("--tasks", required=True, help="Comma-separated task IDs")
    bl_acquire.add_argument("--timeout", type=int, default=30000, help="Lock timeout in ms")
    bl_acquire.add_argument("--wait", action="store_true", help="Wait for lock if held by others")
    bl_acquire.add_argument("--max-wait", type=int, default=60000, dest="max_wait", help="Max wait time in ms")
    
    # batch-lock release
    bl_sub.add_parser("release")
    
    # batch-lock heartbeat
    bl_heartbeat = bl_sub.add_parser("heartbeat", help="Extend lock timeout")
    bl_heartbeat.add_argument("--extend", type=int, default=30000, help="Extend timeout in ms")
    
    # batch-lock recover
    bl_sub.add_parser("recover", help="Recover expired lock")
    
    # batch-lock logs
    bl_logs = bl_sub.add_parser("logs", help="View operation logs")
    bl_logs.add_argument("--limit", type=int, default=20, help="Number of logs to show")


        # v3.3.0: system-check
    sc_p = subparsers.add_parser("system-check", help="System check and preflight")
    sc_p.add_argument("--full", action="store_true", help="Force full re-check")
    sc_p.add_argument("--report", action="store_true", help="View existing report")
    
    # v3.3.0: analyze-module
    am_p = subparsers.add_parser("analyze-module", help="Analyze specific module")
    am_p.add_argument("module_name", help="Module name to analyze")

    args = parser.parse_args()
    json_mode = getattr(args, "json", False)
    cli = LRACLI()

    if args.command == "init":
        cli.cmd_init(args.name, json_mode)
    elif args.command == "context":
        cli.cmd_context(args.output_limit, json_mode)
    elif args.command == "list":
        cli.cmd_list(args.status, args.template, args.compact, json_mode)
    elif args.command == "create":
        cli.cmd_create(
            args.description,
            args.template,
            args.priority,
            args.output_req,
            args.parent,
            args.dependencies,
            args.dependency_type,
            args.deadline,
            args.variables,
            json_mode,
        )
    elif args.command == "show":
        cli.cmd_show(args.task_id, args.include_records, json_mode)
    elif args.command == "set":
        cli.cmd_set(args.task_id, args.status, json_mode)
    elif args.command == "split":
        cli.cmd_split(args.task_id, args.plan, json_mode)
    elif args.command == "claim":
        cli.cmd_claim(args.task_id, json_mode)
    elif args.command == "publish":
        cli.cmd_publish(args.task_id, json_mode)
    elif args.command == "pause":
        cli.cmd_pause(args.task_id, args.note, json_mode)
    elif args.command == "checkpoint":
        cli.cmd_checkpoint(args.task_id, args.note, json_mode)
    elif args.command == "resume":
        cli.cmd_resume(args.task_id, json_mode)
    elif args.command == "heartbeat":
        cli.cmd_heartbeat(args.task_id, json_mode)
    elif args.command == "record":
        cli.cmd_record(args.task_id, args.auto, args.desc, json_mode)
    elif args.command == "template":
        if args.template_cmd == "list":
            cli.cmd_template_list(json_mode)
        elif args.template_cmd == "show":
            cli.cmd_template_show(args.name, json_mode)
        elif args.template_cmd == "create":
            cli.cmd_template_create(args.name, getattr(args, "from_template", None), json_mode)
        elif args.template_cmd == "delete":
            cli.cmd_template_delete(args.name, json_mode)
        else:
            template_p.print_help()
    elif args.command == "guide":
        print(AGENT_GUIDE)
    elif args.command == "version":
        output({"version": CURRENT_VERSION}, json_mode)
    elif args.command == "deps":
        cli.cmd_deps(args.task_id, args.dependents, json_mode)
    elif args.command == "check-blocked":
        cli.cmd_check_blocked(json_mode)
    elif args.command == "set-priority":
        cli.cmd_set_priority(args.task_id, args.priority, json_mode)
    elif args.command == "batch":
        if args.batch_cmd == "set":
            cli.cmd_batch("set", args.status, args.task_ids, args.auto_lock, args.wait, json_mode)
        elif args.batch_cmd == "delete":
            cli.cmd_batch("delete", None, args.task_ids, args.auto_lock, args.wait, json_mode)
        elif args.batch_cmd == "claim":
            cli.cmd_batch("claim", None, args.task_ids, args.auto_lock, args.wait, json_mode)
        else:
            batch_p.print_help()
    elif args.command == "batch-lock":
        if args.batch_lock_cmd == "status":
            cli.cmd_batch_lock_status(json_mode)
        elif args.batch_lock_cmd == "acquire":
            cli.cmd_batch_lock_acquire(
                args.operation,
                args.tasks,
                args.timeout,
                args.wait,
                json_mode
            )
        elif args.batch_lock_cmd == "release":
            cli.cmd_batch_lock_release(json_mode)
        elif args.batch_lock_cmd == "heartbeat":
            cli.cmd_batch_lock_heartbeat(args.extend, json_mode)
        elif args.batch_lock_cmd == "recover":
            cli.cmd_batch_lock_recover(json_mode)
        elif args.batch_lock_cmd == "logs":
            cli.cmd_batch_lock_logs(args.limit, json_mode)
        else:
            bl_p.print_help()
    elif args.command == "search":
        cli.cmd_search(args.query, args.status, json_mode)
    elif args.command == "system-check":
        cli.cmd_system_check(args.full, args.report, json_mode)
    elif args.command == "analyze-module":
        cli.cmd_analyze_module(args.module_name, json_mode)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
