#!/usr/bin/env python3
"""
LRA CLI v5.0
AI Agent 任务管理 + 质量保障
"""

import os
import sys
import json
import argparse
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from lra.config import CURRENT_VERSION, Config, validate_project_initialized, get_agent_id
from lra.task_manager import TaskManager
from lra.template_manager import TemplateManager
from lra.records_manager import RecordsManager
from lra.locks_manager import LocksManager
from lra.batch_lock_manager import BatchLockManager
from lra.tips import TIPS_CONFIG
from lra.cli_extensions import CLIExtensions
from lra.quality_checker import QualityChecker

try:
    from lra.system_check import SystemCheckTask, ConfigManager

    HAS_SYSTEM_CHECK = True
except:
    HAS_SYSTEM_CHECK = False


AGENT_GUIDE = """
LRA v5.0 | AI Agent 任务管理 + 质量保障 + Constitution

🚀 快速开始
   lra start                           # 智能启动（推荐）
   lra init --name <项目名>             # 初始化项目
   lra new "任务描述"                   # 快速创建+认领（推荐）
   lra new "复杂任务" --auto-split      # 创建+拆分+认领第一个子任务

📂 常用命令（按工作流）
   快速: new | context | status | orientation
   任务: list | create | show | set | split | decompose | search
   执行: claim | heartbeat | checkpoint | pause | resume | publish
   测试: regression-test | browser-test | quality-check
   依赖: deps | check-blocked
   批量: batch set|delete|claim

🔀 任务拆分
   lra decompose <id>                 # 分析任务并建议如何拆分
   lra split <id> --auto             # 使用建议自动拆分

🔐 锁机制: claim → heartbeat → publish
🧪 质量保障: regression-test → browser-test → quality-check
🏛️  Constitution: init → create → completed (自动验证)
💡 提示: list自动显示下一步，show显示状态流转

📚 帮助
   lra <cmd> --help        命令详情
   lra orientation         Agent上下文重建
   lra status-guide        状态流转图
   lra template list       模板列表
   cat lra/prompts/agent_prompt.md  # 完整指南
   lra where               文件位置
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
        self._template_manager = None
        self._records_manager = None
        self._locks_manager = None
        self._batch_lock_manager = None
        self.system_check_available = HAS_SYSTEM_CHECK
        self.extensions = CLIExtensions(self)  # v5.0: 初始化扩展

    @property
    def template_manager(self):
        if self._template_manager is None:
            self._template_manager = TemplateManager()
        return self._template_manager

    @property
    def records_manager(self):
        if self._records_manager is None:
            self._records_manager = RecordsManager()
        return self._records_manager

    @property
    def locks_manager(self):
        if self._locks_manager is None:
            self._locks_manager = LocksManager()
        return self._locks_manager

    @property
    def batch_lock_manager(self):
        if self._batch_lock_manager is None:
            self._batch_lock_manager = BatchLockManager()
        return self._batch_lock_manager

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
        from lra.config import Config, SafeJson

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

            # 🆕 自动创建Constitution
            from lra.constitution import init_constitution
            from lra.guide import NextStepGuide

            success, msg = init_constitution(name)
            if success:
                print(f"\n{NextStepGuide.after_init(name)}")

    def cmd_constitution(self, action: str, json_mode: bool = False):
        """Constitution管理命令"""
        from lra.constitution import ConstitutionManager, init_constitution
        from lra.guide import NextStepGuide

        if action == "init":
            # 初始化Constitution
            config = self.task_manager._load_config()
            project_name = config.get("project_name", "My Project") if config else "My Project"

            success, msg = init_constitution(project_name)

            if json_mode:
                output({"ok": success, "message": msg}, json_mode)
            else:
                if success:
                    print(f"✅ {msg}")
                    print(NextStepGuide.after_constitution_init())
                else:
                    print(f"⚠️  {msg}")

        elif action == "validate":
            # 验证Constitution
            try:
                manager = ConstitutionManager()
                principles = manager.get_all_applicable_principles()

                if json_mode:
                    output(
                        {"ok": True, "valid": True, "principles_count": len(principles)}, json_mode
                    )
                else:
                    print("✅ Constitution有效\n")
                    print(f"   Schema版本: {manager.constitution['schema_version']}")
                    print(f"   项目名: {manager.constitution['project']['name']}")
                    print(f"   原则数: {len(principles)}")

                    non_negotiable = manager.get_non_negotiable_principles()
                    mandatory = manager.get_mandatory_principles()
                    configurable = manager.get_enabled_configurable_principles()

                    print(f"\n   不可协商: {len(non_negotiable)}个")
                    print(f"   强制: {len(mandatory)}个")
                    print(f"   可配置: {len(configurable)}个")

            except Exception as e:
                if json_mode:
                    output({"ok": False, "error": str(e)}, json_mode)
                else:
                    print(f"❌ Constitution验证失败: {e}")

        elif action == "show":
            # 显示Constitution详情
            try:
                manager = ConstitutionManager()
                constitution = manager.constitution

                if json_mode:
                    output({"ok": True, "constitution": constitution}, json_mode)
                else:
                    print("🏛️  Constitution配置\n")
                    print(f"Schema版本: {constitution['schema_version']}")
                    print(f"项目: {constitution['project']['name']}")
                    print(f"版本: {constitution['project']['version']}")
                    print(f"批准日期: {constitution['project']['ratified']}")

                    print("\n📋 核心原则:\n")

                    for i, principle in enumerate(constitution.get("core_principles", []), 1):
                        principle_type = principle.get("type", "UNKNOWN")
                        type_emoji = {
                            "NON_NEGOTIABLE": "🔴",
                            "MANDATORY": "🟡",
                            "CONFIGURABLE": "🟢",
                        }.get(principle_type, "⚪")

                        enabled = principle.get("enabled", True)
                        enabled_str = (
                            "" if enabled or principle_type != "CONFIGURABLE" else " (已禁用)"
                        )

                        print(f"{i}. {type_emoji} {principle['name']}{enabled_str}")
                        print(f"   类型: {principle_type}")
                        print(f"   描述: {principle['description']}")

                        gates = principle.get("gates", [])
                        if gates:
                            print(f"   门禁: {len(gates)}个")
                            for gate in gates:
                                gate_type = gate.get("type", "unknown")
                                gate_name = gate.get("name", "unnamed")
                                print(f"     • {gate_name} ({gate_type})")
                        print()

                    template_gates = constitution.get("template_gates", {})
                    if template_gates:
                        print("📦 模板特定门禁:\n")
                        for template, gates in template_gates.items():
                            print(f"  {template}: {len(gates)}个门禁")
                        print()

                    print("💡 提示:")
                    print("   • 编辑配置: .long-run-agent/constitution.yaml")
                    print("   • 验证配置: lra constitution validate")
                    print("   • 查看帮助: lra constitution --help")

            except Exception as e:
                if json_mode:
                    output({"ok": False, "error": str(e)}, json_mode)
                else:
                    print(f"❌ 读取Constitution失败: {e}")

        elif action == "reload":
            # 重新加载Constitution
            try:
                manager = ConstitutionManager()
                manager.reload()

                if json_mode:
                    output({"ok": True, "message": "Constitution reloaded"}, json_mode)
                else:
                    print("✅ Constitution已重新加载")

            except Exception as e:
                if json_mode:
                    output({"ok": False, "error": str(e)}, json_mode)
                else:
                    print(f"❌ 重新加载失败: {e}")

        elif action == "help":
            # 显示帮助
            if json_mode:
                output({"ok": True, "help": NextStepGuide.constitution_help()}, json_mode)
            else:
                print(NextStepGuide.constitution_help())

        else:
            if json_mode:
                output({"ok": False, "error": f"Unknown action: {action}"}, json_mode)
            else:
                print(f"❌ 未知操作: {action}")
                print("   支持的操作: init, validate, show, reload, help")

    def cmd_context(self, output_limit: str = "8k", json_mode: bool = False, full: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        context = self.task_manager.get_context(output_limit)

        if full:
            context_full = self.task_manager.get_context("128k")
            context["in_progress"] = context_full.get("in_progress", [])
            context["can_take"] = context_full.get("can_take", [])

        locks = self.locks_manager.get_all_locks()

        for task in context.get("can_take", []):
            lock = locks.get(task["id"])
            if lock:
                task["lock_status"] = lock.get("status", "free")
            else:
                task["lock_status"] = "free"

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

        if not json_mode:
            self._display_optimizing_tasks()

        output(context, json_mode)

    def _display_optimizing_tasks(self):
        """显示优化中的任务"""
        all_tasks = self.task_manager.list_all()
        optimizing_tasks = []

        for task in all_tasks:
            ralph = task.get("ralph", {})
            iteration = ralph.get("iteration", 0)
            max_iterations = ralph.get("max_iterations", 7)
            quality_checks = ralph.get("quality_checks", {})
            issues = ralph.get("issues", [])

            real_status = self.task_manager.get_real_status(task["id"])

            if real_status == "optimizing" or (
                iteration > 0
                and task.get("status") not in ["completed", "truly_completed", "force_completed"]
            ):
                optimizing_tasks.append(
                    {
                        "task": task,
                        "ralph": ralph,
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                        "quality_checks": quality_checks,
                        "issues": issues,
                        "real_status": real_status,
                    }
                )

        if optimizing_tasks:
            print("\n⚠️  优化中任务（优先处理）\n")
            for item in optimizing_tasks:
                task = item["task"]
                ralph = item["ralph"]
                iteration = item["iteration"]
                max_iterations = item["max_iterations"]
                issues = item["issues"]
                quality_checks = item["quality_checks"]

                task_id = task.get("id", "")
                desc = task.get("description", "")[:50]

                print(f"【{task_id}】{desc}")
                print(f"  状态: 🟡 需要优化 (优化轮次: {iteration}/{max_iterations})")

                if issues:
                    print("\n  ❌ 质量问题:")
                    for issue in issues[-5:]:
                        issue_type = issue.get("type", "unknown")
                        message = issue.get("message", "")
                        print(f"    • {issue_type}: {message}")

                quality_hints = self._generate_quality_hints(quality_checks)
                if quality_hints:
                    print(f"\n  💡 建议: {quality_hints[0]}")

                print(f"\n  📂 相关文件: tasks/{task_id}.md")
                print()

    def _generate_quality_hints(self, quality_checks: Dict[str, bool]) -> List[str]:
        """根据质量检查结果生成建议"""
        hints = []
        if not quality_checks.get("tests_passed", False):
            hints.append("检查测试用例，确保测试通过")
        if not quality_checks.get("lint_passed", False):
            hints.append("运行代码风格检查并修复问题")
        if not quality_checks.get("acceptance_met", False):
            hints.append("完善验收标准，填写测试命令和输出")
        return hints

    def cmd_list(
        self,
        status: Optional[str] = None,
        template: Optional[str] = None,
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
                        from lra.config import current_time_ms, iso_to_ms

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
        template: Optional[str] = None,
        priority: str = "P1",
        output_req: str = "8k",
        parent: Optional[str] = None,
        dependencies: Optional[str] = None,
        dependency_type: str = "all",
        deadline: Optional[str] = None,
        variables: Optional[str] = None,
        requirements: Optional[str] = None,
        acceptance: Optional[str] = None,
        design: Optional[str] = None,
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

        # 短参数 (-r, -a, -d) 覆盖或添加到 variables
        if requirements:
            vars_dict["requirements"] = requirements
        if acceptance:
            # 支持逗号分隔的列表
            vars_dict["acceptance"] = [a.strip() for a in acceptance.split(",")]
        if design:
            vars_dict["design"] = design

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
                # 如果没有提供设计，显示警告
                if not vars_dict:
                    print(f"⚠️ 警告: 未填写设计，其他 agent 无法认领")
                    print(f"   请用以下命令重新创建并填写设计:")
                    print(
                        f'   lra create "{description}" -var \'{{"requirements":"...","acceptance":["..."],"design":"..."}}\''
                    )

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
                template = result.get("template", "task") or "task"
                status = result.get("status", "pending")
                task_id = result.get("id", "")

                # 获取状态流转信息
                transitions = self.template_manager.get_transitions_for_template(template)
                available_transitions = transitions.get(status, [])

                # 🆕 使用引导系统
                from lra.guide import NextStepGuide

                print(NextStepGuide.after_create(task_id, template, bool(vars_dict)))

                # v3.3.3: 智能提示系统
                tip = self._get_tip_for_command("create", description)
                if tip:
                    print(f"{tip}")
        else:
            # v3.3.3: 严重错误才显示
            if result.get("error") == "cycle_dependency":
                print(f"❌ 错误：循环依赖")
                print(f"   依赖路径：{' → '.join(result.get('path', []))}")
                print(f"\n✅ 解决方案：")
                print(f"   请检查依赖关系，避免循环")
            else:
                output(result, json_mode)

    def cmd_new(self, description: str, auto_split: bool = False, json_mode: bool = False):
        """快速创建并认领任务"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        # 自动填充最小字段
        vars_dict = {
            "requirements": description,
            "acceptance": ["完成"],
            "deliverables": [f"src/{description[:20].replace(' ', '_')}.py"],
            "design": "快速任务",
        }

        # 创建任务
        success, result = self.task_manager.create(
            description=description,
            template=self.task_manager.get_default_template(),
            priority="P1",
            output_req="8k",
            parent_id=None,
            dependencies=[],
            deadline=None,
            dependency_type="all",
            variables=vars_dict,
        )

        if not success:
            output(result, json_mode)
            return

        task_id = result.get("id")
        if not task_id:
            output({"error": "create_failed_no_id"}, json_mode)
            return

        if auto_split:
            # 分解并自动拆分
            decomp_success, decomp_result = self.task_manager.suggest_decomposition(task_id)
            if decomp_success and decomp_result.get("subtasks"):
                split_plan = decomp_result.get("subtasks", [])
                self.task_manager.split_task(task_id, split_plan)
                # 发布子任务
                self.locks_manager.publish_children(task_id)
                # 认领第一个子任务
                children = self.task_manager.get_children(task_id)
                if children:
                    first_child = children[0]
                    child_id = first_child.get("id")
                    # 检查子任务是否可以认领
                    can_claim, reason = self.locks_manager.can_claim(child_id)
                    if can_claim:
                        lock_result = self.locks_manager.claim(child_id)
                        if json_mode:
                            output({
                                "ok": True,
                                "task_id": child_id,
                                "parent_id": task_id,
                                "message": f"Created and claimed first subtask {child_id}",
                                "all_subtasks": [c.get("id") for c in children],
                            }, json_mode)
                        else:
                            print(f"✅ 任务已创建并拆分")
                            print(f"📋 父任务: {task_id}")
                            print(f"🎯 已认领第一个子任务: {child_id}")
                            print(f"📦 所有子任务: {', '.join([c.get('id') for c in children])}")
                        return

            # 分解失败，回退到直接认领父任务
            can_claim, reason = self.locks_manager.can_claim(task_id)
            if not can_claim:
                output({"error": "cannot_claim", "reason": reason}, json_mode)
                return
            lock_result = self.locks_manager.claim(task_id)
            if json_mode:
                output({"ok": True, "task_id": task_id, "message": "Created and claimed (auto-split skipped)"}, json_mode)
            else:
                print(f"✅ 任务已创建并认领: {task_id}")
        else:
            # 直接认领父任务
            can_claim, reason = self.locks_manager.can_claim(task_id)
            if not can_claim:
                output({"error": "cannot_claim", "reason": reason}, json_mode)
                return
            lock_result = self.locks_manager.claim(task_id)
            if json_mode:
                output({"ok": True, "task_id": task_id, "message": "Created and claimed"}, json_mode)
            else:
                print(f"✅ 任务已创建并认领: {task_id}")
                print(f"💡 下一步: lra set {task_id} in_progress")

    def cmd_show(self, task_id: str, include_records: bool = False, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        task = self.task_manager.show(task_id)
        if not task:
            output({"error": "not_found"}, json_mode)
            return

        lock = self.locks_manager.get_lock(task_id)
        if lock:
            task["lock_status"] = lock.get("status", "free")
            task["lock_info"] = {
                "claimed_at": lock.get("claimed_at"),
                "last_heartbeat": lock.get("last_heartbeat"),
                "session_id": lock.get("session_id"),
            }

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

        if include_records:
            records = self.records_manager.get(task_id)
            if records:
                task["records"] = records

        template = task.get("template", "task")
        current_status = task.get("status", "pending")
        transitions = self.template_manager.get_transitions_for_template(template)
        available = transitions.get(current_status, [])

        task["available_transitions"] = available
        if available and not json_mode:
            task["_next_commands"] = [f"lra set {task_id} {s}" for s in available]

        ralph_state = self.task_manager.get_ralph_state(task_id)
        if ralph_state:
            task["ralph_state"] = ralph_state

        if not json_mode:
            if ralph_state and ralph_state.get("iteration", 0) > 0:
                self._display_iteration_guidance(task_id, task)
            self._display_ralph_loop_status(task_id, ralph_state)

        output(task, json_mode)

    def _display_iteration_guidance(self, task_id: str, task: Dict[str, Any]):
        """显示迭代阶段引导"""
        ralph = task.get("ralph", {})
        iteration = ralph.get("iteration", 1)
        max_iterations = ralph.get("max_iterations", 7)

        self._display_progress_bar(task_id, iteration, max_iterations)

        stage = ralph.get("current_stage") or self.task_manager.get_iteration_stage(task_id)
        if stage:
            self._display_stage_box(stage)

            if "safety_checks" in stage:
                self._display_safety_checks(stage["safety_checks"])

    def _display_progress_bar(self, task_id: str, current: int, total: int):
        """显示迭代进度条"""
        print("\n📊 迭代进度\n")

        percentage = int(current / total * 100)
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}] {current}/{total} ({percentage}%)")
        print()

        task = self.task_manager.get(task_id)
        if task:
            template = task.get("template", "task")
            stages = self.template_manager.load_iteration_stages(template)

            for stage in stages:
                iter_num = stage.get("iteration", 0)
                stage_name = stage.get("name", "未知阶段")

                if iter_num < current:
                    print(f"✓ 迭代{iter_num}: {stage_name} ✓")
                elif iter_num == current:
                    print(f"● 迭代{iter_num}: {stage_name} (当前)")
                else:
                    print(f"○ 迭代{iter_num}: {stage_name}")

    def _display_stage_box(self, stage: Dict[str, Any]):
        """显示阶段引导框"""
        iteration = stage.get("iteration", 1)
        name = stage.get("name", "未知阶段")
        focus = stage.get("focus", [])
        ignore = stage.get("ignore_checks", [])
        suggestion = stage.get("suggestion", "")

        print("\n╔═══════════════════════════════════════════════════════════╗")
        print("║                     🎯 迭代阶段引导                        ║")
        print("╠═══════════════════════════════════════════════════════════╣")
        print("║                                                           ║")
        print(f"║  当前迭代: {iteration}/7                                            ║")

        name_padded = f"{name:<44}"
        print(f"║  阶段名称: {name_padded}║")
        print("║                                                           ║")

        if focus:
            print("║  📌 本次重点:                                             ║")
            for item in focus[:3]:
                item_padded = f"{item:<48}"
                print(f"║     • {item_padded}║")
            print("║                                                           ║")

        if ignore:
            print("║  ⚠️  应该忽略:                                            ║")
            for item in ignore[:2]:
                item_text = f"{item} 检查 (暂时)"
                item_padded = f"{item_text:<46}"
                print(f"║     • {item_padded}║")
            print("║                                                           ║")

        print("╚═══════════════════════════════════════════════════════════╝")

        if suggestion:
            print(f"\n{suggestion}\n")

    def _display_safety_checks(self, safety_checks: List[Dict[str, Any]]):
        """显示安全检查提示"""
        print("\n⚠️  **重构前安全检查**\n")
        print("重构可能带来风险，请确保：\n")

        for check in safety_checks[:3]:
            check_type = check.get("type", "")
            description = check.get("description", "")
            items = check.get("items", [])

            if check_type and description:
                print(f"✅ **{description}**：")
                for item in items[:3]:
                    print(f"- {item}")
                print()

    def _display_ralph_loop_status(self, task_id: str, ralph_state: Optional[Dict[str, Any]]):
        """显示 Ralph Loop 状态"""
        if not ralph_state:
            return

        iteration = ralph_state.get("iteration", 0)
        max_iterations = ralph_state.get("max_iterations", 7)
        quality_checks = ralph_state.get("quality_checks", {})
        issues = ralph_state.get("issues", [])
        optimization_history = ralph_state.get("optimization_history", [])

        print("\n## 🔄 Ralph Loop 状态\n")
        print(f"当前轮次: {iteration}/{max_iterations}")
        print(f"已优化次数: {len(optimization_history)}次")

        print("\n### 质量检查结果\n")
        print("| 检查项 | 状态 | 详情 |")
        print("|--------|------|------|")

        tests_status = "✅" if quality_checks.get("tests_passed") else "❌"
        tests_detail = "通过" if quality_checks.get("tests_passed") else "失败"
        print(f"| 测试通过 | {tests_status} | {tests_detail} |")

        lint_status = "✅" if quality_checks.get("lint_passed") else "❌"
        lint_detail = "通过" if quality_checks.get("lint_passed") else "失败"
        print(f"| Lint检查 | {lint_status} | {lint_detail} |")

        acceptance_status = "✅" if quality_checks.get("acceptance_met") else "⚠️"
        acceptance_detail = "通过" if quality_checks.get("acceptance_met") else "未满足"
        print(f"| 验收标准 | {acceptance_status} | {acceptance_detail} |")

        failed_items = []
        if not quality_checks.get("tests_passed"):
            test_issues = [i for i in issues if i.get("type") == "test_failure"]
            if test_issues:
                failed_items.append(("测试", test_issues))
        if not quality_checks.get("lint_passed"):
            lint_issues = [i for i in issues if i.get("type") == "lint_error"]
            if lint_issues:
                failed_items.append(("Lint", lint_issues))
        if not quality_checks.get("acceptance_met"):
            acceptance_issues = [i for i in issues if i.get("type") == "acceptance_incomplete"]
            if acceptance_issues:
                failed_items.append(("验收", acceptance_issues))

        if failed_items:
            print("\n### ❌ 失败的检查项\n")
            for check_type, check_issues in failed_items:
                print(f"**{check_type}检查失败**:")
                for issue in check_issues[-3:]:
                    print(f"  - {issue.get('message', '未知问题')}")
                print()

        if optimization_history:
            print("\n### 📝 优化历史\n")
            for i, entry in enumerate(optimization_history[-5:], 1):
                desc = entry.get("description", entry.get("changes", "优化操作"))
                timestamp = entry.get("timestamp", "")
                if timestamp:
                    timestamp = timestamp[11:16]
                print(f"{i}. [{timestamp}] {desc[:60]}")
            print()

        real_status = self.task_manager.get_real_status(task_id)
        print(f"\n### 下一步操作\n")
        if real_status == "completed":
            print("质量检查未通过，需要优化代码")
            print(f"建议: lra quality-check {task_id}  # 查看详细质量报告")
        elif real_status == "optimizing":
            if iteration < max_iterations:
                remaining = max_iterations - iteration
                print(f"继续优化 (剩余 {remaining} 次迭代)")
                print(f"建议: 根据上述失败项进行修复")
            else:
                print("已达到优化上限")
                print(f"建议: 人工审核后执行 lra set {task_id} force_completed")
        elif real_status == "truly_completed":
            print("✅ 质量检查通过，任务完成")
        print()

    def cmd_set(self, task_id: str, status: str, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        if status == "force_next_stage":
            self._force_next_stage(task_id, json_mode)
            return

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
                new_transitions = transitions.get(status, [])
                print(f"✅ 状态已更新：{task_id}")
                print(f"   新状态：{status}")
                if new_transitions:
                    print(f"   可用状态流转：→ {', '.join(new_transitions)}")
                else:
                    print(f"   已到达终态")

                if status == "completed":
                    self._run_quality_check_on_complete(task_id, template, json_mode)

        else:
            # 🆕 处理Constitution验证失败
            if not json_mode and "constitution_failed" in msg:
                print(f"\n❌ Constitution验证失败\n")
                print(f"   任务: {task_id}")
                print(f"   状态: 自动进入 optimizing (优化中)\n")

                # 解析失败原因
                failures_str = msg.replace("constitution_failed:", "")
                failures = [f.strip() for f in failures_str.split(";") if f.strip()]

                print("📋 失败项:\n")
                for i, failure in enumerate(failures[:5], 1):  # 只显示前5个
                    print(f"   {i}. {failure}")

                if len(failures) > 5:
                    print(f"   ... 还有 {len(failures) - 5} 项未显示\n")
                else:
                    print()

                print("💡 修复建议:\n")
                print("   1. 查看任务详情: lra show", task_id)
                print("   2. 修复上述问题")
                print("   3. 重新标记完成: lra set", task_id, "completed")
                print("   4. 查看Constitution: lra constitution show\n")

                print("📚 帮助: lra constitution help\n")

            elif not json_mode and "constitution_non_negotiable_violation" in msg:
                print(f"\n❌ 违反不可协商原则\n")
                print(f"   任务: {task_id}\n")

                failures_str = msg.replace("constitution_non_negotiable_violation:", "")
                failures = [f.strip() for f in failures_str.split(";") if f.strip()]

                print("🔴 不可协商原则违反:\n")
                for i, failure in enumerate(failures, 1):
                    print(f"   {i}. {failure}")

                print("\n⚠️  不可协商原则不能绕过，必须修复问题\n")
                print("💡 修复建议:\n")
                print("   1. 查看任务详情: lra show", task_id)
                print("   2. 修复上述问题")
                print("   3. 重新标记完成: lra set", task_id, "completed\n")

            else:
                output({"ok": success, "status": msg}, json_mode)

        output({"ok": success, "status": msg}, json_mode)

    def _run_quality_check_on_complete(self, task_id: str, template: str, json_mode: bool):
        """完成任务时自动运行质量检查"""
        print(f"\n🔍 自动运行质量检查...\n")

        try:
            qc = QualityChecker()
            result = qc.check_quality_by_template(task_id, template)

            score = result.get("score", 0)
            max_score = result.get("max_score", 100)
            checks = result.get("checks", [])
            failed_required = result.get("failed_required", [])

            self._record_quality_check_result(task_id, result)

            can_complete_early, early_details = self.task_manager.can_complete_early(task_id)

            if can_complete_early:
                iteration = early_details.get("iteration", 1)
                max_iterations = early_details.get("max_iterations", 7)

                print(f"✅ 质量检查全部通过")
                print(f"   得分: {score}/{max_score}")

                if iteration < max_iterations:
                    print(f"\n🎉 恭喜！任务可提前完成（迭代 {iteration}/{max_iterations}）")
                    print(f"\n💡 你已完成所有必需的质量检查，可以选择：")
                    print(f"   1. 提前完成（推荐）")
                    print(f"   2. 继续优化（可选）")
                    print()
                else:
                    print()

                success, _ = self.task_manager.update_status(task_id, "truly_completed", force=True)
                if success:
                    print(f"✅ 状态已自动更新为: truly_completed")
                    if iteration < max_iterations:
                        print(f"   任务已提前完成！")
            elif failed_required:
                print(f"❌ 质量检查未通过:")
                for check in checks:
                    if not check.get("passed") and check.get("required"):
                        check_type = check.get("type", "unknown")
                        issues = check.get("issues", [])
                        if issues:
                            for issue in issues[:3]:
                                print(f"  • {check_type}: {issue.get('message', '未知问题')}")
                        else:
                            print(f"  • {check_type}: 检查未通过")

                ralph_state = self.task_manager.get_ralph_state(task_id) or {}
                iteration = ralph_state.get("iteration", 0)
                max_iterations = ralph_state.get("max_iterations", 7)

                is_stuck, stuck_count = self.task_manager.check_stage_stuck(task_id, threshold=3)

                if is_stuck:
                    current_stage = ralph_state.get("current_stage", {})
                    stage_name = current_stage.get("name", "未知阶段")

                    print(f"\n⚠️  警告：在【{stage_name}】阶段已尝试 {stuck_count} 次")
                    print(f"   当前迭代: {iteration}/{max_iterations}")
                    print(f"\n❌ 质量检查仍未通过:")
                    for check in failed_required:
                        print(f"   • {check}")

                    print(f"\n💡 建议选项：")
                    print(f"   1. 强制进入下一阶段（放弃当前阶段目标）")
                    print(f"      执行: lra set {task_id} force_next_stage")
                    print(f"   2. 继续尝试当前阶段")
                    print(f"      继续工作并提交: lra set {task_id} completed")

                success, new_iter = self.task_manager.increment_iteration(task_id)
                if success:
                    self._record_quality_check_result(task_id, result)
                    print(f"\n进入优化循环 ({new_iter}/{max_iterations})")
                    print(f"\n💡 建议操作:")
                    print(f"   lra show {task_id}          # 查看详细优化状态")
                    print(f"   lra quality-check {task_id} # 查看完整质量报告")

                    success, _ = self.task_manager.update_status(task_id, "optimizing", force=True)
                    if success:
                        print(f"\n状态已自动更新为: optimizing")
                else:
                    print(f"\n⚠️  已达到优化上限 ({max_iterations} 次)")
                    print(f"建议人工审核后执行: lra set {task_id} force_completed")
            else:
                print(f"✅ 质量检查通过")
                print(f"   得分: {score}/{max_score}")
                self._record_quality_check_result(task_id, result)

                success, _ = self.task_manager.update_status(task_id, "truly_completed", force=True)
                if success:
                    print(f"\n状态已自动更新为: truly_completed")

        except Exception as e:
            print(f"⚠️  质量检查失败: {str(e)}")
            print(f"   任务状态保持: completed")

    def _record_quality_check_result(self, task_id: str, result: Dict[str, Any]):
        """记录质量检查结果到任务的 ralph 状态"""
        checks = result.get("checks", [])

        tests_passed = False
        lint_passed = False
        acceptance_met = False

        for check in checks:
            check_type = check.get("type")
            if check_type == "test":
                tests_passed = check.get("passed", False)
            elif check_type == "lint":
                lint_passed = check.get("passed", False)
            elif check_type == "acceptance":
                acceptance_met = check.get("passed", False)

        self.task_manager.record_quality_check(
            task_id,
            {
                "tests_passed": tests_passed,
                "lint_passed": lint_passed,
                "acceptance_met": acceptance_met,
            },
        )

        for check in checks:
            if not check.get("passed"):
                check_type = check.get("type", "unknown")
                issues = check.get("issues", [])
                for issue in issues[:2]:
                    self.task_manager.add_ralph_issue(
                        task_id,
                        f"{check_type}_issue",
                        issue.get("message", "检查未通过"),
                    )

    def _force_next_stage(self, task_id: str, json_mode: bool):
        """强制进入下一阶段"""
        if not json_mode:
            print(f"\n🚀 强制进入下一阶段...\n")

        task = self.task_manager.get(task_id)
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return

        ralph = task.get("ralph", {})
        current_iteration = ralph.get("iteration", 1)
        max_iterations = ralph.get("max_iterations", 7)

        if current_iteration >= max_iterations:
            print(f"❌ 已达到最大迭代次数 ({max_iterations})，无法进入下一阶段")
            print(f"   建议: lra set {task_id} force_completed")
            return

        success, new_iteration = self.task_manager.increment_iteration(task_id)

        if success:
            next_stage = self.task_manager.get_iteration_stage(task_id, new_iteration)
            stage_name = next_stage.get("name", "未知阶段") if next_stage else "未知阶段"

            print(f"✅ 已进入迭代 {new_iteration}/{max_iterations}")
            print(f"   新阶段: {stage_name}\n")

            # 运行迭代阶段门禁检查
            gate_result = self.task_manager.run_iteration_gates(task_id, new_iteration)
            if gate_result.get("gates"):
                print("🔍 阶段质量检查:")
                for gr in gate_result.get("gates", []):
                    status = "✅" if gr["passed"] else "❌"
                    print(f"   {status} {gr['name']}: {gr.get('description', '')}")
                    if gr.get("output"):
                        output_preview = gr["output"][:100] + "..." if len(gr.get("output", "")) > 100 else gr.get("output", "")
                        if output_preview.strip():
                            print(f"      输出: {output_preview}")
                print()

            suggestion = self.task_manager.get_stage_suggestion(task_id)
            print(suggestion)

            self.task_manager.update_status(task_id, "optimizing", force=True)

            print(f"\n💡 提示: 查看完整引导: lra show {task_id}")
        else:
            print(f"❌ 强制进入下一阶段失败")

    def _get_final_states_for_task(self, task_id: str) -> List[str]:
        task = self.task_manager.get(task_id)
        if not task:
            return []
        template = task.get("template", "task")
        transitions = self.template_manager.get_transitions_for_template(template)
        all_states = self.template_manager.get_states_for_template(template)
        return [s for s in all_states if not transitions.get(s)]

    def _check_task_filled(self, task_id: str) -> tuple:
        """检查任务文件是否已填充业务细节"""
        task = self.task_manager.get(task_id)
        if not task:
            return False, []

        task_file = task.get("task_file")
        if not task_file:
            return False, []

        task_dir = Config.get_tasks_dir()
        task_path = os.path.join(task_dir, f"{task_id}.md")

        if not os.path.exists(task_path):
            return False, []

        try:
            with open(task_path, "r", encoding="utf-8") as f:
                content = f.read()
        except:
            return False, []

        missing = []
        if "## 需求" in content or "## requirements" in content.lower():
            if "<!-- 在此填写具体需求描述 -->" in content or "<!-- 请在" in content:
                missing.append("requirements")
        else:
            missing.append("requirements")

        if "## 验收标准" in content or "## acceptance" in content.lower():
            if "<!-- 在此填写验收标准" in content or "<!-- 请在" in content:
                missing.append("acceptance")
        else:
            missing.append("acceptance")

        if "## 交付物" in content or "## deliverables" in content.lower():
            if "<!-- 在此填写交付物" in content or "<!-- 请在" in content:
                missing.append("deliverables")
        else:
            missing.append("deliverables")

        return len(missing) == 0, missing

    def cmd_split(
        self,
        task_id: str,
        count: Optional[int] = None,
        plan: Optional[str] = None,
        plan_file: Optional[str] = None,
        auto: bool = False,
        json_mode: bool = False,
    ):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        # 如果提供了 count，直接报错（不再支持）
        if count:
            output(
                {
                    "error": "count_not_supported",
                    "message": "--count is deprecated. Please use --plan or --plan-file with detailed specifications.",
                    "hint": 'Example: lra split task_001 --plan \'[{"desc":"Subtask 1","requirements":"...","acceptance":["..."],"deliverables":["..."]}]\'',
                },
                json_mode,
            )
            return

        # --auto 模式：使用上一次 decompose 的建议
        if auto:
            suggestion = self.task_manager.get_last_decomposition(task_id)
            if not suggestion:
                output(
                    {
                        "error": "no_decomposition_suggestion",
                        "message": "没有可用的拆分建议，请先运行 lra decompose <task_id>",
                        "hint": "lra decompose task_001  # 生成分解建议",
                    },
                    json_mode,
                )
                return
            if suggestion.get("task_id") != task_id:
                output(
                    {
                        "error": "suggestion_task_mismatch",
                        "message": f"上一次分解建议是针对 {suggestion.get('task_id')}，不是 {task_id}",
                        "hint": "lra decompose task_id  # 重新生成分解建议",
                    },
                    json_mode,
                )
                return
            split_plan = suggestion.get("subtasks", [])
            if not split_plan:
                output({"error": "empty_suggestion", "message": "分解建议为空"}, json_mode)
                return
        elif plan_file:
            # 如果提供了 plan_file，读取文件内容
            if not os.path.exists(plan_file):
                output({"error": "plan_file_not_found", "file": plan_file}, json_mode)
                return
            try:
                with open(plan_file, "r", encoding="utf-8") as f:
                    plan_content = f.read()
                split_plan = json.loads(plan_content)
            except json.JSONDecodeError as e:
                output({"error": "invalid_json_in_file", "detail": str(e)}, json_mode)
                return
            except Exception as e:
                output({"error": "read_plan_file_failed", "detail": str(e)}, json_mode)
                return
        elif plan:
            # 原有的 plan 逻辑
            try:
                split_plan = json.loads(plan)
            except:
                output({"error": "invalid_json_plan"}, json_mode)
                return
        else:
            # 没有提供 plan，显示任务信息
            task = self.task_manager.get(task_id)
            if task:
                output(
                    {
                        "task_id": task_id,
                        "desc": task.get("description", ""),
                        "output_req": task.get("output_req", "8k"),
                        "hint": "Use --plan or --plan-file to provide detailed specifications, or --auto to use decompose suggestion",
                    },
                    json_mode,
                )
            else:
                output({"error": "not_found"}, json_mode)
            return

        success, result = self.task_manager.split_task(task_id, split_plan)

        if success:
            output(result if success else {"error": "split_failed", "detail": result}, json_mode)
            if not json_mode and result.get("tasks"):
                self._print_split_hints(result["tasks"])
        else:
            output({"error": "split_failed", "detail": result}, json_mode)

    def cmd_decompose(self, task_id: str, json_mode: bool = False):
        """分析任务并建议如何拆分"""
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        success, result = self.task_manager.suggest_decomposition(task_id)

        if not success:
            output({"error": result.get("error", "unknown")}, json_mode)
            return

        if json_mode:
            output(result, json_mode)
            return

        # 格式化输出
        print("\n" + "=" * 50)
        print(f"📊 任务分解分析: {task_id}")
        print("=" * 50)
        print(f"\n📝 任务描述: {result['description']}")
        print(f"📏 需求规模: ~{result['requirements_tokens']} tokens")
        print(f"⚡ 复杂度: {result['complexity']}")
        print(f"💡 建议拆分为 {result['suggested_count']} 个子任务")

        print("\n" + "-" * 50)
        print("📋 拆分建议:")
        print("-" * 50)

        for i, subtask in enumerate(result["subtasks"], 1):
            print(f"\n  [{i}] {subtask['desc']}")
            print(f"      需求: {subtask.get('requirements', 'N/A')[:50]}...")

        print("\n" + "-" * 50)
        print("🚀 执行拆分:")
        print(f"   lra split {task_id} --auto")
        print("-" * 50 + "\n")

    def _print_split_hints(self, tasks: list):
        """打印子任务详情填充提示"""
        print("\n" + "=" * 50)
        print("💡 建议下一步: 填充子任务详情")
        print("=" * 50)
        print("\n📝 请为每个子任务编辑详情文件，填充以下字段:")
        print("   - requirements: 具体需求描述")
        print("   - acceptance: 验收标准（每行一个条件）")
        print("   - deliverables: 交付物文件路径")

        # 添加示例
        print("\n📋 填写示例:")
        print("""
## requirements
实现用户注册API，支持邮箱和手机号注册，包含验证码功能

## acceptance
- POST /api/register 返回200和用户信息
- 验证码5分钟内有效
- 重复注册返回友好错误提示

## deliverables
- src/api/auth/register.py
- src/utils/sms.py
- tests/test_register.py
""")

        print("\n📄 子任务详情文件:")
        from lra.config import Config
        import os

        metadata_dir = Config.get_metadata_dir()
        project_root = os.getcwd()
        rel_path = metadata_dir.replace(project_root, "")
        if rel_path.startswith("/"):
            rel_path = "." + rel_path
        for task in tasks:
            task_id = task.get("id", "")
            task_file = f"{rel_path}/tasks/{task_id}.md"
            print(f"   • {task_id}: {task_file}")
        print("\n💡 提示: 使用 lra show <task_id> 查看任务详情")
        print("=" * 50)

    def cmd_claim(self, task_id: str, json_mode: bool = False):
        can_claim, reason = self.locks_manager.can_claim(task_id)
        if not can_claim:
            output({"error": "cannot_claim", "reason": reason}, json_mode)
            return

        filled, missing = self._check_task_filled(task_id)
        if not filled:
            task = self.task_manager.get(task_id)
            # 使用相对于项目根目录的路径
            from lra.config import Config

            metadata_dir = Config.get_metadata_dir()
            task_file = f".{metadata_dir}/tasks/{task_id}.md"

            if json_mode:
                output(
                    {
                        "error": "task_not_filled",
                        "task_id": task_id,
                        "missing": missing,
                        "task_file": task_file,
                        "hint": "请先填充任务详情",
                    },
                    json_mode,
                )
                return

            print("⚠️ 任务尚未填充详情，无法认领\n")
            print(f"📝 请先编辑任务文件补充以下内容:\n")
            print(f"File: {task_file}\n")

            if "requirements" in missing:
                print("## requirements")
                print("[在此填写具体需求...]")
                print()

            if "acceptance" in missing:
                print("## acceptance")
                print("- [验收标准1]")
                print("- [验收标准2]")
                print()

            if "deliverables" in missing:
                print("## deliverables")
                print("- [交付物文件路径]")
                print()

            print("💡 提示: 填写完成后再次执行 lra claim 即可")
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

    def cmd_record(self, args, json_mode: bool = False):
        """记录变更"""
        if not hasattr(args, "record_cmd") or args.record_cmd is None:
            output(
                {"error": "No subcommand specified. Use: add, list, show, timeline, or analyze"},
                json_mode,
            )
            return

        if args.record_cmd == "add":
            if args.auto:
                result = self.records_manager.auto_record(args.feature_id, args.desc)
            else:
                self.records_manager.add(
                    args.feature_id,
                    commit=args.commit or "",
                    branch=args.branch or "",
                    files=[],
                    desc=args.desc or "",
                )
                result = {"feature_id": args.feature_id, "recorded": True}
            output(result, json_mode)

        elif args.record_cmd == "list":
            if args.feature_id:
                brief = self.records_manager.get_brief(args.feature_id)
                if brief:
                    if json_mode:
                        output({"feature_id": args.feature_id, "brief": brief}, json_mode)
                    else:
                        print(f"Feature: {args.feature_id}")
                        print(f"  Commits: {brief.get('commits', 0)}")
                        print(f"  Files: {len(brief.get('files', []))}")
                else:
                    output({"error": f"Feature '{args.feature_id}' not found"}, json_mode)
            else:
                features = self.records_manager.list_features()
                if json_mode:
                    output({"features": features, "count": len(features)}, json_mode)
                else:
                    if features:
                        print("Features with records:")
                        for f in features:
                            brief = self.records_manager.get_brief(f)
                            if brief:
                                print(
                                    f"  - {f}: {brief.get('commits', 0)} commits, {len(brief.get('files', []))} files"
                                )
                    else:
                        print("No features with records yet.")

        elif args.record_cmd == "show":
            result = self.records_manager.get(args.feature_id, args.limit)
            if result:
                output(result, json_mode)
            else:
                output({"error": f"Feature '{args.feature_id}' not found"}, json_mode)

        elif args.record_cmd == "timeline":
            timeline = self.records_manager.get_timeline(args.feature_id)
            if timeline:
                output(
                    {"feature_id": args.feature_id, "timeline": timeline, "count": len(timeline)},
                    json_mode,
                )
            else:
                output({"error": f"Feature '{args.feature_id}' not found"}, json_mode)

        elif args.record_cmd == "analyze":
            result = self.records_manager.analyze(args.feature_id)
            if result:
                output(result, json_mode)
            else:
                output({"error": f"Feature '{args.feature_id}' not found"}, json_mode)

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

    def cmd_template_create(
        self, name: str, from_template: Optional[str] = None, json_mode: bool = False
    ):
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

        # 获取所有被阻塞的任务
        blocked_tasks = []
        data = self.task_manager._load()
        all_tasks = data.get("tasks", []) if data else []

        for task in all_tasks:
            if task.get("status") == "blocked":
                # 获取依赖信息
                dependencies = task.get("dependencies", [])
                dep_type = task.get("dependency_type", "all")

                # 检查每个依赖的状态
                blocking_deps = []
                for dep_id in dependencies:
                    dep_task = self.task_manager.get(dep_id)
                    if dep_task and dep_task.get("status") != "completed":
                        blocking_deps.append(
                            {
                                "id": dep_id,
                                "status": dep_task.get("status"),
                                "description": dep_task.get("description", ""),
                            }
                        )

                if blocking_deps:
                    blocked_tasks.append(
                        {
                            "id": task["id"],
                            "description": task.get("description", ""),
                            "dependency_type": dep_type,
                            "blocking_dependencies": blocking_deps,
                        }
                    )

        # 解除阻塞的任务
        unblocked = self.task_manager.check_blocked_tasks()

        output(
            {
                "ok": True,
                "blocked_tasks": blocked_tasks,
                "blocked_count": len(blocked_tasks),
                "unblocked": unblocked,
                "unblocked_count": len(unblocked),
            },
            json_mode,
        )

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
        # 优先使用保存的 agent_id
        last_agent_id = self.batch_lock_manager._get_last_agent_id()
        agent_id = get_agent_id()

        # 如果锁的持有者是上次保存的 agent_id，使用它
        status = self.batch_lock_manager.status()
        if status.get("locked") and last_agent_id and status.get("holder") == last_agent_id:
            agent_id = last_agent_id

        success, reason = self.batch_lock_manager.release(agent_id)

        if not success and reason == "not_lock_holder":
            # 提供更友好的错误信息
            if status.get("locked"):
                output(
                    {
                        "ok": False,
                        "message": "not_lock_holder",
                        "your_agent_id": agent_id,
                        "lock_holder": status.get("holder"),
                        "hint": f"Lock is held by {status.get('holder')}. "
                        + f"Your agent_id is {agent_id}. "
                        + f"Set LRA_AGENT_ID={status.get('holder')} to release it.",
                    },
                    json_mode,
                )
                return

        output({"ok": success, "message": reason, "agent_id": agent_id}, json_mode)

    def cmd_batch_lock_heartbeat(self, extend: int = 30000, json_mode: bool = False):
        """心跳续期"""
        agent_id = get_agent_id()
        success, reason = self.batch_lock_manager.heartbeat(agent_id, extend)

        if not success and reason == "not_lock_holder":
            # 提供更友好的错误信息
            status = self.batch_lock_manager.status()
            if status.get("locked"):
                output(
                    {
                        "ok": False,
                        "message": "not_lock_holder",
                        "your_agent_id": agent_id,
                        "lock_holder": status.get("holder"),
                        "hint": f"Lock is held by {status.get('holder')}. "
                        + f"Your agent_id is {agent_id}. "
                        + f"Set LRA_AGENT_ID={status.get('holder')} to manage it.",
                    },
                    json_mode,
                )
                return

        output({"ok": success, "message": reason, "agent_id": agent_id}, json_mode)

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
            from lra.project_analyzer import ProjectAnalyzer

            analyzer = ProjectAnalyzer(os.getcwd())
            result = analyzer.analyze_module(module_name)

            if not result:
                output(
                    {
                        "error": "module_not_found",
                        "module": module_name,
                        "hint": "analyze-module需要在有代码的项目中使用。建议: 1) 在包含Python/JS代码的目录运行; 2) 先运行 'lra analyze-project' 分析项目结构",
                    },
                    json_mode,
                )
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
            from lra.project_analyzer import ProjectAnalyzer

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
        from lra.config import Config

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

    # ==================== v5.0 新增命令 ====================

    def cmd_status(self, json_mode: bool = False):
        """项目进度可视化"""
        self.extensions.cmd_status(json_mode)

    def cmd_orientation(self, json_mode: bool = False):
        """Agent上下文重建"""
        self.extensions.cmd_orientation(json_mode)

    def cmd_regression_test(
        self,
        task_id: Optional[str] = None,
        template: Optional[str] = None,
        report: bool = False,
        json_mode: bool = False,
    ):
        """回归测试"""
        self.extensions.cmd_regression_test(task_id, template, report, json_mode)

    def cmd_browser_test(
        self, task_id: Optional[str] = None, generate_script: bool = False, json_mode: bool = False
    ):
        """浏览器自动化测试"""
        self.extensions.cmd_browser_test(task_id, generate_script, json_mode)

    def cmd_quality_check(
        self, task_id: Optional[str] = None, report: bool = False, json_mode: bool = False
    ):
        """代码质量检查"""
        self.extensions.cmd_quality_check(task_id, report, json_mode)

    def cmd_start(
        self,
        task_desc: Optional[str] = None,
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
            from lra.project_analyzer import ProjectAnalyzer

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
        description="LRA v5.0 - AI Agent Task Manager with Quality Assurance",
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

    # constitution
    const_p = subparsers.add_parser(
        "constitution",
        help="Constitution management",
        description="Manage project Constitution (quality principles and gates). "
        "Constitution defines non-negotiable quality standards that are automatically validated before task completion.",
    )
    const_p.add_argument(
        "action",
        choices=["init", "validate", "show", "reload", "help"],
        help="Action: init (create), validate (check), show (display), reload (reload), help (guide)",
    )

    # context
    ctx_p = subparsers.add_parser("context", help="Get project context")
    ctx_p.add_argument("--output-limit", default="8k", choices=["4k", "8k", "16k", "32k", "128k"])
    ctx_p.add_argument(
        "--full", action="store_true", help="Show full context including in_progress tasks"
    )

    # list
    list_p = subparsers.add_parser("list", help="List tasks")
    list_p.add_argument("--status")
    list_p.add_argument("--template")
    list_p.add_argument("--compact", action="store_true", help="Compact output")

    # create
    create_p = subparsers.add_parser(
        "create",
        help="Create task",
        description="Create a new task with specified description and options. "
        "Task ID is auto-generated (e.g., task_001).",
    )
    create_p.add_argument("description", help="Task description (required)")

    # 任务详情
    create_p.add_argument(
        "--requirements",
        default=None,
        help="Task requirements",
    )
    create_p.add_argument(
        "--acceptance",
        default=None,
        help="Acceptance criteria, comma-separated",
    )
    create_p.add_argument(
        "--design",
        default=None,
        help="Design solution",
    )

    # 常用参数
    create_p.add_argument(
        "--template",
        default=None,
        help="Task template. Use 'lra template list' to see available templates",
    )
    create_p.add_argument(
        "--dependencies", default=None, help="Comma-separated task IDs that this task depends on"
    )

    # 高级参数
    create_p.add_argument(
        "-var",
        "--variables",
        default=None,
        help='[必填] JSON: \'{"requirements":"...","acceptance":["..."],"design":"..."}\'',
    )
    create_p.add_argument(
        "--priority",
        default="P1",
        choices=["P0", "P1", "P2", "P3"],
        help="Task priority: P0/P1/P2/P3 (default: P1)",
    )
    create_p.add_argument(
        "--output-req", default="8k", help="Output size: 4k/8k/16k/32k/128k (default: 8k)"
    )
    create_p.add_argument("--parent", default=None, help="Parent task ID for subtasks")
    create_p.add_argument(
        "--dependency-type",
        default="all",
        choices=["all", "any"],
        help="Dependency type: all or any (default: all)",
    )
    create_p.add_argument("--deadline", default=None, help="Task deadline (ISO: YYYY-MM-DD)")

    # show
    show_p = subparsers.add_parser("show", help="Show task")
    show_p.add_argument("task_id")
    show_p.add_argument("--include-records", action="store_true", help="Include task records")

    # set
    set_p = subparsers.add_parser("set", help="Update status")
    set_p.add_argument("task_id")
    set_p.add_argument("status")

    # split
    split_p = subparsers.add_parser(
        "split",
        help="Split task into subtasks",
        description="""Split a task into subtasks. Agent should use --plan or --plan-file to provide
detailed subtask specifications including requirements, acceptance criteria, and deliverables.

Recommended workflow:
  1. Read parent task file: lra show <parent_id>
  2. Create plan file with detailed specs
  3. Split with: lra split <parent_id> --plan-file /path/to/plan.json
""",
    )
    split_p.add_argument("task_id", help="Parent task ID to split")
    split_p.add_argument(
        "--count",
        type=int,
        default=None,
        help="(Deprecated) 已废弃，请使用 --plan 或 --plan-file 参数",
    )
    split_p.add_argument(
        "--plan",
        default=None,
        help="""JSON array of detailed subtask specs. Format:
[
  {
    "desc": "子任务描述",
    "output_req": "4k",
    "requirements": "具体需求描述",
    "acceptance": ["验收标准1", "验收标准2"],
    "deliverables": ["交付物1", "交付物2"]
  }
]""",
    )
    split_p.add_argument(
        "--plan-file",
        default=None,
        help="Read plan from file (recommended for detailed specs). Example: --plan-file .long-run-agent/split_plan.json",
    )
    split_p.add_argument(
        "--auto",
        action="store_true",
        default=False,
        help="使用上一次 lra decompose 的建议自动拆分",
    )

    # decompose
    decomp_p = subparsers.add_parser(
        "decompose",
        help="分析任务并建议如何拆分",
        description="""分析任务需求，自动建议如何拆分成子任务。

推荐工作流:
  1. lra create "复杂任务"
  2. lra decompose task_001  # 查看拆分建议
  3. lra split task_001 --auto  # 使用建议自动拆分
""",
    )
    decomp_p.add_argument("task_id", help="要分析的任务ID")

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
    record_sub = record_p.add_subparsers(dest="record_cmd")

    # record add
    record_add_p = record_sub.add_parser("add", help="Add a record")
    record_add_p.add_argument("feature_id")
    record_add_p.add_argument("--desc", default="")
    record_add_p.add_argument("--commit", default="")
    record_add_p.add_argument("--branch", default="")
    record_add_p.add_argument("--auto", action="store_true")

    # record list
    record_list_p = record_sub.add_parser("list", help="List all features")
    record_list_p.add_argument("feature_id", nargs="?", default=None)

    # record show
    record_show_p = record_sub.add_parser("show", help="Show feature records")
    record_show_p.add_argument("feature_id")
    record_show_p.add_argument("--limit", type=int, default=10)

    # record timeline
    record_timeline_p = record_sub.add_parser("timeline", help="Show feature timeline")
    record_timeline_p.add_argument("feature_id")

    # record analyze
    record_analyze_p = record_sub.add_parser("analyze", help="Analyze feature changes")
    record_analyze_p.add_argument("feature_id")

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
    batch_set_p.add_argument("task_ids", nargs="+")
    batch_set_p.add_argument("status")
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
    ap_p = subparsers.add_parser(
        "analyze-project",
        help="Analyze entire project structure",
        description="Analyze project code structure, generate documentation and agent index. "
        "Creates MODULES.md and index.json for fast code navigation.",
    )
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
    ap_p.add_argument(
        "--force",
        action="store_true",
        help="Force re-analysis even if analysis already exists",
    )

    # v3.4.0: where - 显示文件位置
    subparsers.add_parser("where", help="Show key file locations")

    # v3.4.0: index - 输出 Agent 索引
    idx_p = subparsers.add_parser("index", help="Output agent index path or content")
    idx_p.add_argument("--content", action="store_true", help="Output full index content")

    # v3.3.0: status-guide
    subparsers.add_parser("status-guide", help="Show state transition guide for all templates")

    # v3.4.1: recover - 恢复任务列表
    subparsers.add_parser("recover", help="Recover task list from tasks/ directory")

    # ==================== v5.0 新增命令 ====================

    # status - 项目进度可视化
    subparsers.add_parser("status", help="Visualize project progress")

    # orientation - Agent上下文重建
    subparsers.add_parser(
        "orientation", help="Agent context reconstruction protocol - 快速了解项目状态"
    )

    # regression-test - 回归测试
    regression_p = subparsers.add_parser("regression-test", help="Run regression tests")
    regression_p.add_argument("task_id", nargs="?", help="Task ID (optional)")
    regression_p.add_argument("--template", help="Template filter")
    regression_p.add_argument("--report", action="store_true", help="Show test report")

    # browser-test - 浏览器自动化测试
    browser_p = subparsers.add_parser("browser-test", help="Browser automation testing")
    browser_p.add_argument("task_id", nargs="?", help="Task ID (optional)")
    browser_p.add_argument(
        "--script", action="store_true", dest="generate_script", help="Generate test script"
    )

    # quality-check - 代码质量检查
    quality_p = subparsers.add_parser("quality-check", help="Code quality check")
    quality_p.add_argument("task_id", nargs="?", help="Task ID (optional)")
    quality_p.add_argument("--report", action="store_true", help="Show quality report")

    # v3.4.1: start - 智能启动
    start_p = subparsers.add_parser(
        "start", help="Smart start - auto-detect project state and guide"
    )
    start_p.add_argument("--task", dest="task_desc", help="First task description")
    start_p.add_argument("--name", help="Project name (for new projects)")
    start_p.add_argument("--auto", action="store_true", help="Auto mode, skip all prompts")

    # new - quick create and claim
    new_p = subparsers.add_parser(
        "new",
        help="Quick create + claim in one command",
        description="""Create a task and immediately claim it.
Useful for quick tasks without needing to fill in details manually.

Examples:
  lra new "Fix bug"                    # Create and claim immediately
  lra new "Feature" --auto-split       # Create, decompose, split, and claim first subtask
""",
    )
    new_p.add_argument("description", help="Task description")
    new_p.add_argument("--auto-split", action="store_true", help="Auto decompose and split before claiming")

    args = parser.parse_args()
    json_mode = getattr(args, "json", False)
    cli = LRACLI()

    if args.command == "init":
        cli.cmd_init(args.name, args.template, json_mode)
    elif args.command == "constitution":
        cli.cmd_constitution(args.action, json_mode)
    elif args.command == "context":
        cli.cmd_context(args.output_limit, json_mode, getattr(args, "full", False))
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
            args.requirements,
            args.acceptance,
            args.design,
            json_mode,
        )
    elif args.command == "show":
        cli.cmd_show(args.task_id, args.include_records, json_mode)
    elif args.command == "set":
        cli.cmd_set(args.task_id, args.status, json_mode)
    elif args.command == "split":
        cli.cmd_split(args.task_id, args.count, args.plan, args.plan_file, args.auto, json_mode)
    elif args.command == "decompose":
        cli.cmd_decompose(args.task_id, json_mode)
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
        cli.cmd_record(args, json_mode)
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
        cli.cmd_analyze_project(
            getattr(args, "output_dir", None),
            getattr(args, "create_tasks", True),
            getattr(args, "force", False),
            json_mode,
        )
    elif args.command == "where":
        cli.cmd_where(json_mode)
    elif args.command == "index":
        cli.cmd_index(getattr(args, "content", False), json_mode)
    elif args.command == "status-guide":
        cli.cmd_status_guide(json_mode)
    elif args.command == "recover":
        cli.cmd_recover(json_mode)

    # ==================== v5.0 新增命令分发 ====================

    elif args.command == "status":
        cli.cmd_status(json_mode)

    elif args.command == "orientation":
        cli.cmd_orientation(json_mode)

    elif args.command == "regression-test":
        cli.cmd_regression_test(
            getattr(args, "task_id", None), getattr(args, "template", None), args.report, json_mode
        )

    elif args.command == "browser-test":
        cli.cmd_browser_test(
            getattr(args, "task_id", None), getattr(args, "generate_script", False), json_mode
        )

    elif args.command == "quality-check":
        cli.cmd_quality_check(getattr(args, "task_id", None), args.report, json_mode)

    elif args.command == "new":
        cli.cmd_new(args.description, args.auto_split, json_mode)
    elif args.command == "start":
        cli.cmd_start(args.task_desc, args.name, args.auto, json_mode)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
