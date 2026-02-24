#!/usr/bin/env python3
"""
LRA CLI v3.1
通用任务管理框架 - AI Agent 优化版
"""

import os
import sys
import json
import argparse
from typing import Any, Dict, List

from .config import CURRENT_VERSION, Config, validate_project_initialized
from .task_manager import TaskManager
from .template_manager import TemplateManager
from .records_manager import RecordsManager
from .locks_manager import LocksManager


AGENT_GUIDE = """
LRA - AI Agent Task Manager v3.1

## QUICK START
$ lra context --output-limit 8k

## CORE COMMANDS
lra init --name <name>         Initialize project
lra context [--output-limit 4k|8k|16k|32k|128k]
lra list [--status X] [--template X]
lra create <desc> --template <name> [--output-req 8k]
lra show <id>                  Task details
lra set <id> <status>          Update status (constrained by template)
lra split <id> --plan '<json>' Split task (model provides plan)

## LOCK COMMANDS
lra claim <id>                 Claim task (locks self + children)
lra publish <id>               Release children for others to claim
lra pause <id> [--note]        Pause + checkpoint
lra resume <id>                View checkpoint
lra checkpoint <id> [--note]   Save progress
lra heartbeat <id>             Keep-alive (every 5min)

## TEMPLATE COMMANDS
lra template list              List templates
lra template show <name>       Template details
lra template create <name> [--from <template>]

## RECORD COMMANDS
lra record <id> [--auto]       Record changes

## STATUS FLOW
Status transitions are defined by template.
Use 'lra template show <name>' to see allowed transitions.

## MULTI-AGENT
- claim = exclusive lock on task + children
- publish = release children locks for parallel work
- orphaned (no heartbeat 15min) = can be claimed

## OUTPUT LIMIT
Match your model's output capability:
--output-limit 4k   (GPT-4o-mini)
--output-limit 8k   (Claude 3.5)
--output-limit 16k  (Claude 3.5 Sonnet)
--output-limit 128k (Claude 3.5 Sonnet max)

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
        resumable = self.locks_manager.get_resumable()
        if resumable:
            context["resumable"] = resumable
        output(context, json_mode)

    def cmd_list(self, status: str = None, template: str = None, json_mode: bool = False):
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
        json_mode: bool = False,
    ):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        success, result = self.task_manager.create(
            description=description,
            template=template,
            priority=priority,
            parent_id=parent,
            output_req=output_req,
        )
        if success:
            output({"ok": True, "task": result}, json_mode)
        else:
            output(result, json_mode)

    def cmd_show(self, task_id: str, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
            return

        task = self.task_manager.show(task_id)
        if task:
            output(task, json_mode)
        else:
            output({"error": "not_found"}, json_mode)

    def cmd_set(self, task_id: str, status: str, json_mode: bool = False):
        if not self._check_project():
            output({"error": "not_initialized"}, json_mode)
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

    # create
    create_p = subparsers.add_parser("create", help="Create task")
    create_p.add_argument("description")
    create_p.add_argument("--template", default="task")
    create_p.add_argument("--priority", default="P1", choices=["P0", "P1", "P2"])
    create_p.add_argument("--output-req", default="8k")
    create_p.add_argument("--parent", default=None)

    # show
    subparsers.add_parser("show", help="Show task").add_argument("task_id")

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

    args = parser.parse_args()
    json_mode = getattr(args, "json", False)
    cli = LRACLI()

    if args.command == "init":
        cli.cmd_init(args.name, json_mode)
    elif args.command == "context":
        cli.cmd_context(args.output_limit, json_mode)
    elif args.command == "list":
        cli.cmd_list(args.status, args.template, json_mode)
    elif args.command == "create":
        cli.cmd_create(
            args.description, args.template, args.priority, args.output_req, args.parent, json_mode
        )
    elif args.command == "show":
        cli.cmd_show(args.task_id, json_mode)
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
