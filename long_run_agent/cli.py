#!/usr/bin/env python3
"""
LRA CLI v3.1
通用任务管理框架 - AI Agent 优化版
"""

import os
import sys
import json
import argparse
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import CURRENT_VERSION, Config, validate_project_initialized, get_agent_id
from .task_manager import TaskManager
from .template_manager import TemplateManager
from .records_manager import RecordsManager
from .locks_manager import LocksManager
from .batch_lock_manager import BatchLockManager
from .tips import TIPS_CONFIG

try:
    from .system_check import SystemCheckTask, ConfigManager

    HAS_SYSTEM_CHECK = True
except:
    HAS_SYSTEM_CHECK = False


AGENT_GUIDE = """
LRA v3.4.1 | AI Agent 任务管理 + 项目分析

🚀 Agent 快速开始
1. lra start [--auto] [--task "<描述>"]      # 智能启动（推荐）
2. lra init --name <项目名>                  # 初始化项目
3. lra analyze-project                       # 生成项目文档 + Agent 索引

📁 文档输出
   docs/                               # 人类可读文档
   .long-run-agent/analysis/index.json # Agent 快速索引（类/函数/文件）

🤖 Agent 索引使用
   lra where                           # 查看所有关键文件位置
   lra index                           # 输出索引文件路径
   lra index --content                 # 输出完整索引内容

📋 模板：task|code-module|doc-update|data-pipeline|novel-chapter
   详情：lra template list | lra status-guide

📊 核心命令
lra start [--auto]                # 智能启动（自动检测状态）
lra create "<描述>" [--template X]  # 创建任务（默认项目模板）
lra list [--status X]             # 列表（显示下一步建议）
lra show <id>                     # 详情（显示可用状态流转）
lra set <id> <status>             # 更新状态

✨ 增强功能
   • lra list 自动显示下一步建议（claim/heartbeat/completed）
   • lra show 显示可用状态流转和推荐命令
   • 超时时自动提醒心跳（>45 分钟）

🔐 锁机制：claim → publish → heartbeat
💡 增量模式：自动添加"-模块"后缀，永不失败

🛡️  容错功能
lra recover                       # 从 tasks/目录恢复任务列表
lra start --auto                  # 自动处理各种项目状态

📚 帮助索引
lra --help              # 完整帮助
lra guide               # 详细指南
lra where               # 文件位置
lra template list       # 模板列表
lra status-guide        # 状态流转
lra start --help        # 智能启动帮助
lra <cmd> --help        # 命令帮助
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

    def _get_tip_for_command(self, cmd: str, description: str = "") -> Optional[str]:
        """获取命令相关提示（v3.3.3 新增）"""
        # 1. 关键字匹配（优先级最高）
        for kw, tip in TIPS_CONFIG["keywords"].items():
            if kw in description:
                return tip

        # 2. 心理暗示（10% 独立概率）
        if random.random() < TIPS_CONFIG.get("psychological_probability", 0.10):
            tips = TIPS_CONFIG.get("psychological_tips", [])
            if tips:
                return random.choice(tips)

        # 3. 轮换提示（25% 概率）
        if random.random() < TIPS_CONFIG["probability"]:
            return random.choice(TIPS_CONFIG["rotating"])

        return None

    def _check_project(self) -> bool:
        """检查项目是否初始化，智能检测常见问题"""
        import os
        from .config import Config, SafeJson

        ok, _ = validate_project_initialized()
        if not ok:
            # 智能检测：task_list.json 不存在但 tasks/ 目录有文件
            task_list_path = Config.get_task_list_path()
            tasks_dir = Config.get_tasks_dir()

            if os.path.exists(tasks_dir):
                try:
                    task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".md")]
                    if task_files:
                        print(f"⚠️  检测到任务文件但索引损坏")
                        print(f"   发现 {len(task_files)} 个任务文件")
                        print(f"💡 建议运行：lra recover")
                        print()
                except:
                    pass

        return ok

    def cmd_init(self, name: str, template: str, json_mode: bool = False):
        success, msg = self.task_manager.init_project(name, template)

        if json_mode:
            output({"ok": success, "message": msg}, json_mode)
            return

        if success:
            print(f"✅ 项目已初始化：{name}\n")
            print(f"默认模板：{template}")
            print(f"\n📋 下一步:")
            print(f"   lra analyze-project        # 生成项目文档（推荐）")
            print(f"   lra context                # 查看项目状态")
            print(f'   lra create "任务描述"      # 创建第一个任务')
            print(f"\n🤖 Agent 索引: .long-run-agent/analysis/index.json")

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

    def cmd_list(
        self,
        status: str = None,
        template: str = None,
        compact: bool = False,
        json_mode: bool = False,
    ):
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
            # 普通模式：显示下一步建议
            locks = self.locks_manager.get_all_locks()
            for t in tasks:
                status = t.get("status", "pending")
                task_id = t["id"]
                template = t.get("template", "task")
                desc = t.get("description", "")[:40]

                print(f"{task_id}: {status} [{template}] {desc}")

                # 根据状态显示下一步建议
                if status == "pending":
                    print(f"{' ' * 14}→ lra claim {task_id}")
                elif status == "in_progress":
                    # 检查心跳时间
                    lock = locks.get(task_id)
                    if lock:
                        from .config import current_time_ms, iso_to_ms

                        last_hb = lock.get("last_heartbeat")
                        if last_hb:
                            try:
                                last_hb_ms = (
                                    iso_to_ms(last_hb) if isinstance(last_hb, str) else last_hb
                                )
                                elapsed_ms = current_time_ms() - last_hb_ms
                                elapsed_min = elapsed_ms // 60000
                            except (ValueError, TypeError):
                                elapsed_min = 0
                            if elapsed_min > 45:
                                print(
                                    f"{' ' * 14}⚠️ 已进行{elapsed_min}分钟 | → lra heartbeat {task_id}"
                                )
                            else:
                                print(f"{' ' * 14}→ lra set {task_id} completed")
                        else:
                            print(f"{' ' * 14}→ lra set {task_id} completed")
                    else:
                        print(f"{' ' * 14}→ lra set {task_id} completed")

    def cmd_create(
        self,
        description: str,
        template: str = None,
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

        # 如果未指定模板，使用项目默认模板
        if template is None:
            template = self.task_manager.get_default_template()

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
            if json_mode:
                output({"ok": True, "task": result}, json_mode)
            else:
                # v3.3.3: 自动降级提示（仅在首次显示）
                if result.get("_auto_adjusted"):
                    # 检查当前项目是否已经有过增量模式任务（排除刚创建的这个）
                    tasks = self.task_manager.list_all()
                    other_incremental = [
                        t
                        for t in tasks
                        if "-模块" in t.get("description", "") and t.get("id") != result.get("id")
                    ]
                    if len(other_incremental) == 0:
                        # 首次创建，显示详细提示
                        print(f"💡 增量模式：'-模块'自动添加")

                # 显示任务创建成功信息
                template = result.get("template", "task")
                status = result.get("status", "pending")

                # 获取状态流转信息
                transitions = self.template_manager.get_transitions_for_template(template)
                available_transitions = transitions.get(status, [])

                print(f"✅ 任务已创建：{result.get('id')}")
                print(f"   描述：{result.get('description', '')[:60]}")
                print(f"   状态：{status}")
                print(f"   模板：{template}")
                if available_transitions:
                    print(f"   可用状态流转：→ {', '.join(available_transitions)}")
                print(f"   使用：lra set {result.get('id')} <status> 更新状态")

                # v3.3.3: 智能提示系统
                tip = self._get_tip_for_command("create", description)
                if tip:
                    print(f"\n{tip}")
        else:
            # v3.3.3: 严重错误才显示
            if result.get("error") == "cycle_dependency":
                print(f"❌ 错误：循环依赖")
                print(f"   依赖路径：{' → '.join(result.get('path', []))}")
                print(f"\n✅ 解决方案：")
                print(f"   请检查依赖关系，避免循环")
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
                    dep_details.append(
                        {
                            "id": dep_id,
                            "status": dep_task.get("status"),
                            "desc": dep_task.get("description", "")[:50],
                        }
                    )
            task["dependency_details"] = dep_details

        # 添加任务记录（如果请求）
        if include_records:
            records = self.records_manager.get(task_id)
            if records:
                task["records"] = records

        # 添加状态流转建议
        template = task.get("template", "task")
        current_status = task.get("status", "pending")
        transitions = self.template_manager.get_transitions_for_template(template)
        available = transitions.get(current_status, [])

        task["available_transitions"] = available
        if available and not json_mode:
            task["_next_commands"] = [f"lra set {task_id} {s}" for s in available]

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
            output(
                {
                    "ok": True,
                    "message": "already_in_target_status",
                    "current_status": status,
                    "task_id": task_id,
                },
                json_mode,
            )
            return

        # 检查状态流转是否合法
        template = current_task.get("template", "task")
        transitions = self.template_manager.get_transitions_for_template(template)
        available_transitions = transitions.get(current_status, [])

        if status not in available_transitions and not json_mode:
            print(f"❌ 错误：无效的状态流转")
            print(f"   当前状态：{current_status}")
            print(f"   目标状态：{status}")
            print(f"   模板：{template}")
            print(
                f"   可用状态流转：→ {', '.join(available_transitions) if available_transitions else '无（终态）'}"
            )
            return

        success, msg = self.task_manager.update_status(task_id, status)
        if success:
            final_states = self._get_final_states_for_task(task_id)
            if status in final_states:
                self.locks_manager.release(task_id)

            if not json_mode:
                # 显示新的可用流转
                new_transitions = transitions.get(status, [])
                print(f"✅ 状态已更新：{task_id}")
                print(f"   新状态：{status}")
                if new_transitions:
                    print(f"   可用状态流转：→ {', '.join(new_transitions)}")
                else:
                    print(f"   已到达终态")
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

    def cmd_batch(
        self,
        operation: str,
        status: str = None,
        task_ids: List[str] = None,
        auto_lock: bool = True,
        wait: bool = False,
        json_mode: bool = False,
    ):
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
                    output(
                        {
                            "error": "lock_held_by_other",
                            "hint": "使用 --wait 选项等待或使用 batch-lock 命令手动管理锁",
                            "holder": lock_info["holder"],
                            "remaining_ms": lock_info["remaining_ms"],
                        },
                        json_mode,
                    )
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
                        results.append(
                            {
                                "task_id": task_id,
                                "message": "already_in_target_status",
                                "current_status": status,
                            }
                        )
                    else:
                        # 验证状态流转
                        template = current_task.get("template", "task")
                        if not self.template_manager.validate_transition(
                            template, current_status, status
                        ):
                            results.append(
                                {
                                    "task_id": task_id,
                                    "error": "invalid_transition",
                                    "from": current_status,
                                    "to": status,
                                    "template": template,
                                }
                            )
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
                        results.append(
                            {"task_id": task_id, "error": "cannot_claim", "reason": reason}
                        )
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
                matched.append(
                    {
                        "id": task["id"],
                        "status": task.get("status"),
                        "desc": task.get("description", "")[:80],
                        "priority": task.get("priority", "P1"),
                    }
                )

        output(
            {"query": query, "status_filter": status, "results": matched, "count": len(matched)},
            json_mode,
        )

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
        json_mode: bool = False,
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
            output({"ok": True, "message": reason, "lock": info, "agent_id": agent_id}, json_mode)
        else:
            if reason == "lock_held_by_other":
                output(
                    {
                        "ok": False,
                        "error": reason,
                        "hint": "等待其他 Agent 完成操作，或使用 --wait 选项",
                        "holder": info["holder"],
                        "remaining_ms": info["remaining_ms"],
                        "operation_type": info["operation_type"],
                    },
                    json_mode,
                )
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

    def cmd_system_check(
        self, full: bool = False, report: bool = False, force: bool = False, json_mode: bool = False
    ):
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
                if json_mode:
                    output(tm_report, json_mode)
                else:
                    self._print_formatted_report(tm_report)
            else:
                output({"error": "no_report", "hint": "run 'lra system-check' first"}, json_mode)
        else:
            # 执行预检
            if full or force or not self.task_manager.has_system_check():
                try:
                    project_path = os.getcwd()
                    checker = SystemCheckTask(project_path=project_path)
                    report_data = checker.run(force_full=force)
                    if json_mode:
                        output({"ok": True, "report": report_data}, json_mode)
                    else:
                        print("✅ 系统检查完成\n")
                        self._print_formatted_report(report_data)
                except Exception as e:
                    output({"error": str(e)}, json_mode)
            else:
                output(
                    {
                        "info": "report_exists",
                        "hint": "use --report to view or --full/--force to re-run",
                    },
                    json_mode,
                )

    def _print_formatted_report(self, report: dict):
        """格式化输出系统检查报告"""
        project_id = report.get("project_id", "unknown")
        decision = report.get("decision", "unknown")
        reason = report.get("reason", "")

        # 决策标识
        if decision == "full":
            print(f"📊 决策：✅ 全量模式")
        else:
            print(f"📊 决策：⚠️ 增量模式")
        print(f"📁 项目：{project_id}")
        print(f"📝 原因：{reason}\n")

        # 指标表格
        print("📈 检测指标:")
        print(f"{'指标':<20} {'当前值':<15} {'阈值':<15} {'状态':<10}")
        print("-" * 60)

        # 代码体积
        code_size = report.get("code_total_size_mb", 0)
        code_threshold = 5.0
        code_status = "✅" if code_size <= code_threshold else "❌"
        print(
            f"{'代码体积 (MB)':<20} {code_size:<15.2f} {'≤' if code_size <= code_threshold else '>'} {code_threshold:<12} {code_status}"
        )

        # Git 规范提交
        git_ratio = report.get("git_valid_ratio", 0)
        git_threshold = 0.3
        git_status = "✅" if git_ratio >= git_threshold else "❌"
        print(
            f"{'Git 规范提交':<20} {git_ratio:<15.0%} {'≥' if git_ratio >= git_threshold else '<'} {git_threshold:<12.0%} {git_status}"
        )

        # 文档覆盖率
        doc_ratio = report.get("doc_coverage_ratio", 0)
        doc_threshold = 0.4
        doc_status = "✅" if doc_ratio >= doc_threshold else "❌"
        print(
            f"{'文档覆盖率':<20} {doc_ratio:<15.0%} {'≥' if doc_ratio >= doc_threshold else '<'} {doc_threshold:<12.0%} {doc_status}"
        )

        # 函数注释率
        func_ratio = report.get("func_comment_ratio", 0)
        func_threshold = 0.2
        func_status = "✅" if func_ratio >= func_threshold else "❌"
        print(
            f"{'函数注释占比':<20} {func_ratio:<15.0%} {'≥' if func_ratio >= func_threshold else '<'} {func_threshold:<12.0%} {func_status}"
        )

        print()

        # 建议
        suggestions = report.get("suggestions", [])
        if suggestions:
            print("💡 建议:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion}")
            print()

    def cmd_analyze_module(
        self, module_name: str, output_doc: bool = False, json_mode: bool = False
    ):
        """分析指定模块的代码结构"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        try:
            from .project_analyzer import ProjectAnalyzer

            analyzer = ProjectAnalyzer(os.getcwd())
            result = analyzer.analyze_module(module_name)

            if not result:
                output({"error": "module_not_found", "module": module_name}, json_mode)
                return

            if output_doc:
                doc_path = analyzer.generate_module_doc(module_name)
                result["doc_path"] = doc_path

            output(result, json_mode)

        except Exception as e:
            output({"error": str(e)}, json_mode)

    def cmd_analyze_project(
        self,
        output_dir: str = "docs",
        create_tasks: bool = True,
        force: bool = False,
        json_mode: bool = False,
    ):
        """分析整个项目结构"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        try:
            from .project_analyzer import ProjectAnalyzer

            analyzer = ProjectAnalyzer(os.getcwd())

            summary_path = os.path.join(".long-run-agent", "analysis", "summary.json")
            if os.path.exists(summary_path) and not force:
                output(
                    {"info": "analysis_exists", "hint": "use --force to re-analyze"},
                    json_mode,
                )
                return

            result = analyzer.analyze_project()

            docs = analyzer.generate_project_doc(output_dir)
            result["docs"] = docs

            summary = analyzer.generate_summary_json()
            result["summary_path"] = summary

            if create_tasks:
                created_tasks = []
                for module in result.get("modules", []):
                    success, task = self.task_manager.create(
                        description=f"完善 {module['name']} 模块文档",
                        template="doc-update",
                        priority="P2",
                        skip_system_check=True,
                        variables={
                            "module": module["name"],
                            "update_scope": "full",
                            "doc_coverage": module.get("doc_coverage", 0),
                        },
                    )
                    if success:
                        created_tasks.append(task["id"])
                result["created_tasks"] = created_tasks

            if not json_mode:
                print("✅ 项目分析完成")
                print(f"   模块数：{len(result.get('modules', []))}")
                print(f"   总文件：{result.get('total_files', 0)}")
                print(f"   总代码行：{result.get('total_lines', 0)}")
                print(f"   文档目录：{output_dir}/")
                if create_tasks:
                    print(f"   创建任务：{len(result.get('created_tasks', []))}")
                print(f"\n📁 文档已生成:")
                print(f"   docs/MODULES.md                    # 项目总览")
                print(f"   .long-run-agent/analysis/index.json # Agent 快速索引")
                print(f"\n🤖 Agent 使用:")
                print(f'   类查找: index["classes"]["类名"]')
                print(f'   函数查找: index["functions"]["函数名"]')

            output(result, json_mode)

        except Exception as e:
            output({"error": str(e)}, json_mode)

    def cmd_where(self, json_mode: bool = False):
        """显示所有关键文件位置"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        project_name = os.path.basename(os.getcwd())
        config_path = os.path.join(".long-run-agent", "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if config and "project" in config:
                        project_name = config["project"].get("name", project_name)
            except:
                pass

        locations = {
            "project": project_name,
            "agent_index": ".long-run-agent/analysis/index.json",
            "summary": ".long-run-agent/analysis/summary.json",
            "docs": "docs/",
            "task_list": ".long-run-agent/task_list.json",
            "config": ".long-run-agent/config.yaml",
            "locks": ".long-run-agent/locks.json",
        }

        if json_mode:
            output(locations, json_mode)
        else:
            print("📁 LRA 文件位置\n")
            print(f"   Agent 索引:  {locations['agent_index']}")
            print(f"   分析报告:    {locations['summary']}")
            print(f"   文档目录:    {locations['docs']}")
            print(f"   任务列表:    {locations['task_list']}")
            print(f"   配置文件:    {locations['config']}")
            print(f"   锁文件:      {locations['locks']}")

    def cmd_index(self, show_content: bool = False, json_mode: bool = False):
        """输出 Agent 索引路径或内容"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        index_path = ".long-run-agent/analysis/index.json"

        if not os.path.exists(index_path):
            output(
                {"error": "index_not_found", "hint": "run 'lra analyze-project' first"}, json_mode
            )
            return

        if show_content:
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                output(content, json_mode)
            except Exception as e:
                output({"error": str(e)}, json_mode)
        else:
            if json_mode:
                output({"index_path": index_path}, json_mode)
            else:
                print(index_path)

    def cmd_status_guide(self, json_mode: bool = False):
        """显示状态流转指南"""
        templates = {
            "task": {
                "description": "通用任务模板",
                "states": ["pending", "in_progress", "completed"],
                "transitions": {
                    "pending": ["in_progress"],
                    "in_progress": ["completed"],
                    "completed": [],
                },
            },
            "code-module": {
                "description": "代码模块开发模板",
                "states": [
                    "pending",
                    "in_progress",
                    "pending_test",
                    "test_failed",
                    "completed",
                ],
                "transitions": {
                    "pending": ["in_progress"],
                    "in_progress": ["pending_test"],
                    "pending_test": ["completed", "test_failed"],
                    "test_failed": ["in_progress"],
                    "completed": [],
                },
            },
            "novel-chapter": {
                "description": "小说章节模板",
                "states": ["drafting", "revising", "finalized"],
                "transitions": {
                    "drafting": ["revising"],
                    "revising": ["finalized", "drafting"],
                    "finalized": [],
                },
            },
            "data-pipeline": {
                "description": "数据处理流程模板",
                "states": ["pending", "running", "failed", "success"],
                "transitions": {
                    "pending": ["running"],
                    "running": ["success", "failed"],
                    "failed": ["running"],
                    "success": [],
                },
            },
            "doc-update": {
                "description": "文档更新任务模板",
                "states": ["pending", "in_progress", "completed"],
                "transitions": {
                    "pending": ["in_progress"],
                    "in_progress": ["completed"],
                    "completed": [],
                },
            },
        }

        if json_mode:
            output(templates, json_mode)
        else:
            print("📊 LRA 状态流转指南\n")
            print("=" * 70)
            for name, info in templates.items():
                print(f"\n📁 {name} - {info['description']}")
                print(f"   状态：{' → '.join(info['states'])}")
                print(f"   流转:")
                for state, next_states in info["transitions"].items():
                    if next_states:
                        print(f"     {state} → {', '.join(next_states)}")
                    else:
                        print(f"     {state} ✅ (终态)")
            print("\n" + "=" * 70)
            print("\n💡 提示：使用 'lra set <task_id> <status>' 更新状态")
            print("   系统会自动提示可用的状态流转选项")

    def cmd_recover(self, json_mode: bool = False):
        """从 tasks/目录恢复任务列表"""
        import os
        from .config import Config

        tasks_dir = Config.get_tasks_dir()
        if not os.path.exists(tasks_dir):
            output({"error": "tasks_dir_not_found"}, json_mode)
            return

        success, result = self.task_manager.recover_task_list()

        if json_mode:
            output({"ok": success, **result}, json_mode)
            return

        if success:
            print(f"✅ 任务列表已恢复")
            print(f"   恢复数量：{result.get('recovered_count', 0)}")
            recovered = result.get("recovered_tasks", [])
            if recovered:
                print(f"   任务列表：{', '.join(recovered)}")
        else:
            error = result.get("error", "unknown_error")
            print(f"❌ 恢复失败")
            print(f"   错误：{error}")
            if error == "no_task_files_found":
                print(f"\n💡 提示：tasks/ 目录中没有任务文件")
            elif error == "tasks_dir_not_found":
                print(f"\n💡 提示：请确保项目已初始化")

    def cmd_start(
        self,
        task_desc: str = None,
        project_name: str = None,
        auto: bool = False,
        json_mode: bool = False,
    ):
        """智能启动 - 根据项目状态自动引导"""

        # 检测项目状态
        state = self.task_manager.detect_project_state()

        if json_mode:
            output(state, json_mode)
            return

        # 场景 1: 全新项目
        if state["state"] == "new_project":
            self._start_new_project(project_name, task_desc, auto)

        # 场景 2: 需要恢复
        elif state["state"] == "needs_recovery":
            self._start_needs_recovery(state, auto)

        # 场景 2.5: 部分初始化
        elif state["state"] == "partial_init":
            self._start_partial_init(project_name, task_desc, auto)

        # 场景 3: 有待执行任务
        elif state["state"] == "has_pending_tasks":
            self._start_has_pending_tasks(state, auto)

        # 场景 4: 已初始化但无待执行任务
        else:
            self._start_initialized(state, auto, task_desc)

    def _start_new_project(
        self,
        project_name: str = None,
        task_desc: str = None,
        auto: bool = False,
    ):
        """场景 1: 全新项目"""
        print("📦 检测到新项目，正在初始化...\n")

        # 自动推断项目名称
        if not project_name:
            project_name = os.path.basename(os.getcwd()) or "my-project"

        # 执行初始化
        success, msg = self.task_manager.init_project(project_name, "task")
        if not success:
            print(f"❌ 初始化失败：{msg}")
            return

        print(f"✅ 项目已初始化：{project_name}")
        print(f"默认模板：task\n")

        # 自动分析项目
        print("📊 正在分析项目结构...")
        try:
            from .project_analyzer import ProjectAnalyzer

            analyzer = ProjectAnalyzer(os.getcwd())
            result = analyzer.analyze_project()
            docs = analyzer.generate_project_doc("docs")
            print("✅ 分析完成\n")
        except Exception as e:
            print(f"⚠️  分析失败：{e}")
            print("   可以稍后手动运行：lra analyze-project\n")

        # 创建第一个任务
        if task_desc:
            print(f"📋 创建第一个任务...")
            self.cmd_create(task_desc)
        else:
            print("📋 下一步:")
            print(f'   lra create "任务描述"      # 创建第一个任务')
            print(f"   lra context                # 查看项目状态")

        print()

    def _start_needs_recovery(self, state: Dict[str, Any], auto: bool = False):
        """场景 2: 需要恢复"""
        print("⚠️  检测到项目索引损坏\n")
        print(f"发现 {state.get('task_count', 0)} 个任务文件")
        print("但 task_list.json 已损坏\n")

        if auto:
            print("🔄 自动模式：正在恢复...\n")
            self.cmd_recover()
        else:
            print("💡 建议运行：lra recover")
            print("   将恢复任务到索引中\n")

    def _start_partial_init(
        self,
        project_name: str = None,
        task_desc: str = None,
        auto: bool = False,
    ):
        """场景 2.5: 部分初始化（.long-run-agent 存在但 task_list.json 不存在）"""
        print("⚠️  检测到项目部分初始化\n")
        print(".long-run-agent 目录存在，但 task_list.json 缺失")
        print()

        # 重新初始化
        if not project_name:
            project_name = os.path.basename(os.getcwd()) or "my-project"

        if auto:
            print(f"🔄 自动模式：重新初始化项目为 {project_name}...\n")
            success, msg = self.task_manager.init_project(project_name, "task")
            if success:
                print(f"✅ 项目已初始化：{project_name}")

                if task_desc:
                    print()
                    self.cmd_create(task_desc)
        else:
            print("💡 建议运行：lra init --name {project_name}")
            print()

    def _start_has_pending_tasks(self, state: Dict[str, Any], auto: bool = False):
        """场景 3: 有待执行任务"""
        pending = state.get("pending_count", 0)
        in_progress = state.get("in_progress_count", 0)

        print("📊 当前项目状态\n")

        if pending > 0:
            print(f"待执行：{pending}")

        if in_progress > 0:
            print(f"进行中：{in_progress}")

        print()

        # 获取可执行任务
        context = self.task_manager.get_context()
        can_take = context.get("can_take", [])

        if can_take:
            print("🎯 可执行任务:")
            for task in can_take[:5]:  # 只显示前 5 个
                priority = task.get("priority", "P1")
                desc = task.get("desc", "")[:50]
                print(f"   {task['id']}: {desc} ({priority})")

            if len(can_take) > 5:
                print(f"   ... 还有 {len(can_take) - 5} 个任务")

            print()
            print("📋 推荐操作:")
            print(f"   lra claim {can_take[0]['id']}     # 领取最高优先级任务")
            print(f"   lra context                # 查看详细上下文")
        else:
            print("💡 没有可领取的任务")
            print("   lra list                   # 查看所有任务")
            print('   lra create "新任务"         # 添加新任务')

        print()

    def _start_initialized(self, state: Dict[str, Any], auto: bool = False, task_desc: str = None):
        """场景 4: 已初始化但无待执行任务"""
        print("📊 当前项目状态\n")
        print(f"总任务：{state.get('task_count', 0)}")
        print(f"进行中：{state.get('in_progress_count', 0)}")
        print()

        if task_desc:
            print("📋 创建新任务...\n")
            self.cmd_create(task_desc)
        else:
            print("💡 所有任务都在进行中或已完成")
            print("   lra list                   # 查看所有任务")
            print('   lra create "新任务"         # 添加新任务')
            print("   lra context                # 查看上下文")
            print()


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
    init_p.add_argument("--name", required=True, help="Project name")
    init_p.add_argument(
        "--template",
        default="task",
        help="Default template (default: task)",
    )

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
    create_p.add_argument("--template", default=None)
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
    deps_p.add_argument(
        "--dependents", action="store_true", help="Show tasks that depend on this task"
    )

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
    batch_set_p.add_argument(
        "--auto-lock",
        action="store_true",
        dest="auto_lock",
        default=True,
        help="Auto acquire batch lock",
    )
    batch_set_p.add_argument(
        "--no-auto-lock", action="store_false", dest="auto_lock", help="Disable auto lock"
    )
    batch_set_p.add_argument("--wait", action="store_true", help="Wait for lock if held")

    # batch delete
    batch_del_p = batch_sub.add_parser("delete", help="Batch delete tasks")
    batch_del_p.add_argument("task_ids", nargs="+")
    batch_del_p.add_argument(
        "--auto-lock",
        action="store_true",
        dest="auto_lock",
        default=True,
        help="Auto acquire batch lock",
    )
    batch_del_p.add_argument("--wait", action="store_true", help="Wait for lock if held")

    # batch claim
    batch_claim_p = batch_sub.add_parser("claim", help="Batch claim tasks")
    batch_claim_p.add_argument("task_ids", nargs="+")
    batch_claim_p.add_argument(
        "--auto-lock",
        action="store_true",
        dest="auto_lock",
        default=True,
        help="Auto acquire batch lock",
    )
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
    bl_acquire.add_argument(
        "--operation", required=True, choices=["batch_claim", "batch_set", "batch_delete"]
    )
    bl_acquire.add_argument("--tasks", required=True, help="Comma-separated task IDs")
    bl_acquire.add_argument("--timeout", type=int, default=30000, help="Lock timeout in ms")
    bl_acquire.add_argument("--wait", action="store_true", help="Wait for lock if held by others")
    bl_acquire.add_argument(
        "--max-wait", type=int, default=60000, dest="max_wait", help="Max wait time in ms"
    )

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
    sc_p.add_argument(
        "--force", action="store_true", help="Force full analysis mode (ignore thresholds)"
    )

    # v3.3.0: analyze-module
    am_p = subparsers.add_parser("analyze-module", help="Analyze specific module code structure")
    am_p.add_argument("module_name", help="Module name to analyze")
    am_p.add_argument("--output-doc", action="store_true", help="Generate module documentation")

    # v3.3.0: analyze-project
    ap_p = subparsers.add_parser("analyze-project", help="Analyze entire project structure")
    ap_p.add_argument("--output-dir", default="docs", help="Documentation output directory")
    ap_p.add_argument(
        "--create-tasks",
        action="store_true",
        default=True,
        dest="create_tasks",
        help="Create module analysis tasks (default)",
    )
    ap_p.add_argument(
        "--no-create-tasks",
        action="store_false",
        dest="create_tasks",
        help="Do not create tasks",
    )
    ap_p.add_argument("--force", action="store_true", help="Force re-analysis")

    # v3.4.0: where - 显示文件位置
    subparsers.add_parser("where", help="Show key file locations")

    # v3.4.0: index - 输出 Agent 索引
    idx_p = subparsers.add_parser("index", help="Output agent index path or content")
    idx_p.add_argument("--content", action="store_true", help="Output full index content")

    # v3.3.0: status-guide
    subparsers.add_parser("status-guide", help="Show state transition guide for all templates")

    # v3.4.1: recover - 恢复任务列表
    subparsers.add_parser("recover", help="Recover task list from tasks/ directory")

    # v3.4.1: start - 智能启动
    start_p = subparsers.add_parser(
        "start", help="Smart start - auto-detect project state and guide"
    )
    start_p.add_argument("--task", dest="task_desc", help="First task description")
    start_p.add_argument("--name", help="Project name (for new projects)")
    start_p.add_argument("--auto", action="store_true", help="Auto mode, skip all prompts")

    args = parser.parse_args()
    json_mode = getattr(args, "json", False)
    cli = LRACLI()

    if args.command == "init":
        cli.cmd_init(args.name, args.template, json_mode)
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
                args.operation, args.tasks, args.timeout, args.wait, json_mode
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
        cli.cmd_system_check(args.full, args.report, args.force, json_mode)
    elif args.command == "analyze-module":
        cli.cmd_analyze_module(args.module_name, getattr(args, "output_doc", False), json_mode)
    elif args.command == "analyze-project":
        cli.cmd_analyze_project(args.output_dir, args.create_tasks, args.force, json_mode)
    elif args.command == "where":
        cli.cmd_where(json_mode)
    elif args.command == "index":
        cli.cmd_index(getattr(args, "content", False), json_mode)
    elif args.command == "status-guide":
        cli.cmd_status_guide(json_mode)
    elif args.command == "recover":
        cli.cmd_recover(json_mode)
    elif args.command == "start":
        cli.cmd_start(args.task_desc, args.name, args.auto, json_mode)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
