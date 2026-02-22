#!/usr/bin/env python3
"""
LRA - Long-Running Agent 工具
统一命令行接口 v2.0
"""

import os
import sys
import argparse

from .registry import ProjectRegistry
from .session_manager import SessionManager
from .resource_coordinator import ResourceCoordinator, ResourceLockError
from .config import CURRENT_VERSION, SCHEMA_VERSION, Config, GitHelper
from .upgrade_manager import UpgradeManager, check_and_upgrade
from .status_manager import StatusManager, FeatureStatus, get_status_info, get_all_statuses, STATUS_INFO
from .records_manager import RecordsManager
from .operation_logger import OperationLogger, ACTION_INFO
from .spec_manager import SpecManager
from .code_checker import CodeChecker


class LRACLI:
    """LRA 命令行接口 v2.0"""

    def __init__(self):
        self.registry = ProjectRegistry()
        self.session_manager = SessionManager()
        self.resource_coordinator = ResourceCoordinator()
        self.status_manager = StatusManager()
        self.records_manager = RecordsManager()
        self.operation_logger = OperationLogger()
        self.spec_manager = SpecManager()

        self.working_project_id = os.environ.get("LRA_WORKING_PROJECT")

    def _check_project(self):
        """检查项目是否初始化"""
        if not os.path.exists(Config.get_feature_list_path()):
            print("❌ 项目未初始化，请先运行: lra project create --name <名称>")
            return False
        return True

    # ==================== 版本管理 ====================

    def version(self):
        """显示版本信息"""
        print(f"\n📦 LRA - Long-Running Agent v{CURRENT_VERSION}")
        print(f"   Schema 版本: {SCHEMA_VERSION}\n")

        if os.path.exists(Config.get_metadata_dir()):
            manager = UpgradeManager()
            info = manager.get_upgrade_info()
            if info.get("upgraded_at"):
                print(f"   上次升级: {info['upgraded_at']}")

    def upgrade(self, auto_confirm=True):
        """执行升级"""
        if not os.path.exists(Config.get_metadata_dir()):
            print("❌ 未检测到 LRA 项目目录")
            return

        manager = UpgradeManager()
        success, message = manager.upgrade(auto_confirm=auto_confirm)
        print(f"{'✅' if success else '❌'} {message}")

    def rollback(self, backup_name=None):
        """回滚到指定备份"""
        manager = UpgradeManager()

        if backup_name:
            backup_path = os.path.join(manager.backup_dir, backup_name)
            if manager.restore_backup(backup_path):
                print("✅ 回滚成功")
            else:
                print("❌ 回滚失败")
        else:
            backups = manager.list_backups()
            if not backups:
                print("没有可用的备份")
                return

            print("\n📦 可用备份:\n")
            for i, b in enumerate(backups[:10], 1):
                print(f"  {i}. {b['name']} ({b['created_at']})")

            print("\n使用: lra rollback --backup <备份名>")

    # ==================== Feature 管理 ====================

    def feature_create(self, title, category="general", priority="P1", assignee=""):
        """创建 Feature"""
        if not self._check_project():
            return

        from .feature_manager import add_feature
        add_feature(category, title, steps=None, priority=priority, assignee=assignee)

    def feature_status(self, feature_id, new_status=None):
        """查看或修改 Feature 状态"""
        if not self._check_project():
            return

        if new_status:
            validation = self.status_manager.change_status(feature_id, new_status, "cli")
            if validation[0]:
                self.operation_logger.log_status_change(
                    feature_id,
                    self.status_manager.get_feature_status(feature_id) or "unknown",
                    new_status,
                    "CLI 操作",
                    "cli"
                )
                print(f"✅ {validation[1]}")
            else:
                print(f"❌ {validation[1]}")
        else:
            status = self.status_manager.get_feature_status(feature_id)
            if status:
                info = get_status_info(status)
                print(f"\n{info['emoji']} {feature_id}: {info['name']}")
                print(f"   {info['description']}")
                transitions = self.status_manager.get_valid_transitions_for_status(status)
                print(f"   可流转到: {', '.join(transitions) if transitions else '无'}")
            else:
                print(f"❌ 未找到 Feature: {feature_id}")

    def feature_list(self, status=None, show_all=False):
        """列出 Features"""
        if not self._check_project():
            return

        from .feature_manager import list_features
        list_features(show_all=show_all, status_filter=status)

    # ==================== 需求文档管理 ====================

    def spec_create(self, feature_id, title=""):
        """创建需求文档"""
        if not self._check_project():
            return

        success, message = self.spec_manager.create_spec(feature_id, title or f"Feature {feature_id}")
        if success:
            self.operation_logger.log_spec_create(feature_id, message, "cli")
            print(f"✅ 需求文档创建成功: {message}")
        else:
            print(f"❌ {message}")

    def spec_validate(self, feature_id):
        """校验需求文档"""
        if not self._check_project():
            return

        result = self.spec_manager.validate_spec(feature_id)
        if result["valid"]:
            print("✅ 需求文档校验通过")
        else:
            print("❌ 需求文档不完整:\n")
            for m in result["missing"]:
                print(f"  - {m}")
            print(f"\n状态: {result['spec_status']}")

    def spec_list(self, status=None):
        """列出需求文档"""
        if not self._check_project():
            return

        specs = self.spec_manager.list_specs(status)
        if not specs:
            print("没有找到需求文档")
        else:
            from .status_manager import SPEC_STATUS_INFO
            print(f"\n📋 需求文档列表 ({len(specs)} 个):\n")
            for s in specs:
                info = SPEC_STATUS_INFO.get(s["spec_status"], {"emoji": "❓", "name": s["spec_status"]})
                exists = "✅" if s["spec_exists"] else "❌"
                print(f"{info['emoji']} {s['feature_id']}: {s['title'][:40]}")
                print(f"   状态: {info['name']} | 文件: {exists}")
                print()

    # ==================== 代码变更记录 ====================

    def records_show(self, feature_id=None, file_path=None, format="detail"):
        """显示代码变更记录"""
        if not self._check_project():
            return

        if feature_id:
            result = self.records_manager.get_records_by_feature(feature_id, format)
            if result:
                if format == "brief":
                    print(f"\n📋 {feature_id} 变更摘要:\n")
                    print(f"  总变更数: {result['total_changes']}")
                    print(f"  涉及文件: {len(result['files'])}")
                    for f in result['files'][:10]:
                        print(f"    - {f}")
                else:
                    print(f"\n📋 {feature_id} 变更记录:\n")
                    for r in result.get("records", []):
                        print(f"  [{r['timestamp'][:19]}]")
                        print(f"    Commit: {r.get('commit_hash', 'N/A')}")
                        print(f"    Branch: {r.get('branch', 'N/A')}")
                        for f in r.get('files', [])[:5]:
                            print(f"      - {f.get('path')} (+{f.get('lines_added', 0)}/-{f.get('lines_deleted', 0)})")
                        print()
            else:
                print(f"❌ 未找到 {feature_id} 的记录")

        elif file_path:
            results = self.records_manager.get_records_by_file(file_path)
            if results:
                print(f"\n📁 {file_path} 关联记录:\n")
                for r in results:
                    print(f"  Feature: {r['feature_id']}")
                    for rec in r['records']:
                        print(f"    [{rec['timestamp'][:19]}] {rec.get('description', '')}")
            else:
                print(f"❌ 未找到 {file_path} 的关联记录")
        else:
            features = self.records_manager.get_all_features_with_records()
            print(f"\n📋 有记录的 Features ({len(features)} 个):\n")
            for f in features[:20]:
                record = self.records_manager.get_records_by_feature(f, "brief")
                if record:
                    print(f"  {f}: {record['total_changes']} 次变更")

    # ==================== 项目管理 ====================

    def project_create(self, name, path=None):
        """创建新项目"""
        from .feature_manager import init_project

        if path:
            os.makedirs(path, exist_ok=True)
            os.chdir(path)

        init_project(name, f"项目: {name}")
        print(f"\n✓ 项目 '{name}' 创建成功")

    def project_switch(self, project_id):
        """切换项目"""
        project = self.registry.get_project(project_id)
        if not project:
            print(f"❌ 项目 '{project_id}' 不存在")
            return

        self.working_project_id = project_id
        os.chdir(project['path'])
        print(f"✓ 切换到项目: {project['name']} ({project_id})")
        print(f"  路径: {project['path']}")

    # ==================== 操作日志 ====================

    def logs_show(self, action=None, operator=None, feature=None, limit=20):
        """显示操作日志"""
        logs = self.operation_logger.get_logs(
            action_type=action,
            operator=operator,
            feature_id=feature,
            limit=limit
        )

        if not logs:
            print("没有找到日志")
        else:
            print(f"\n📋 操作日志 ({len(logs)} 条):\n")
            for log in logs:
                info = ACTION_INFO.get(log["action_type"], {"emoji": "📄", "name": log["action_type"]})
                target = log.get("target", {})
                print(f"{info['emoji']} [{log['timestamp'][:19]}] {log['operator']}")
                print(f"   类型: {info['name']}")
                print(f"   目标: {target.get('type', '')}/{target.get('id', '')}")
                print()

    # ==================== 代码检查 ====================

    def code_check(self, path, verbose=False):
        """代码语法检查"""
        checker = CodeChecker()

        if os.path.isfile(path):
            results = [checker.check_file(path)]
        elif os.path.isdir(path):
            results = checker.check_directory(path)
        else:
            print(f"❌ 路径不存在: {path}")
            return

        for r in results:
            if r["valid"]:
                print(f"✅ {r['file']} ({r['language']})")
            else:
                print(f"❌ {r['file']} ({r['language']})")
                for err in r["errors"][:3]:
                    print(f"   {err[:100]}")

        summary = checker.get_summary(results)
        print(f"\n📊 检查结果: {summary['passed']}/{summary['total']} 通过 ({summary['pass_rate']:.1f}%)")

    # ==================== Git 集成 ====================

    def git_info(self, feature_id=None):
        """显示 Git 信息"""
        commit = GitHelper.get_current_commit()
        branch = GitHelper.get_current_branch()

        print(f"\n📦 Git 信息:\n")
        print(f"  Commit: {commit.get('hash', 'N/A')}")
        print(f"  Branch: {branch or 'N/A'}")
        print(f"  Author: {commit.get('author', 'N/A')}")
        print(f"  Message: {commit.get('message', 'N/A')[:50]}")

        if feature_id:
            validation = GitHelper.validate_branch_name(feature_id)
            if not validation["valid"]:
                print(f"\n⚠️  {validation['warning']}")
                print(f"   {validation.get('suggestion', '')}")

    # ==================== LLM 上下文 ====================

    def llm_context(self):
        """输出 AI 上下文（精简版，供 LLM 使用）"""
        print(f"""# LRA (Long-Running Agent) v{CURRENT_VERSION} - AI Context

## 核心概念
- **Feature**: 一个开发任务，ID 格式 `feature_N` (N 为数字)
- **Spec**: 需求文档，存放在 `.long-run-agent/specs/feature_N.md`
- **Status**: Feature 状态流转

## 状态流转
```
pending → in_progress → testing → completed
                  ↘ blocked → in_progress
```

## 命令速查
| 命令 | 用途 |
|------|------|
| `lra init` | 初始化项目（交互式） |
| `lra feature create "标题"` | 创建 Feature |
| `lra feature list` | 列出 Features |
| `lra feature status <id> --set <status>` | 修改状态 |
| `lra spec create <id>` | 创建需求文档 |
| `lra spec validate <id>` | 校验需求完整性 |
| `lra records --feature <id>` | 查看代码变更记录 |
| `lra code check <path>` | 语法检查 |
| `lra git --feature <id>` | Git 信息+分支校验 |

## 最佳实践（必读）

### 1. 开发流程
```
lra feature create "功能描述"
lra spec create feature_N --title "详细标题"
# 编辑 .long-run-agent/specs/feature_N.md 填写需求
lra spec validate feature_N  # 校验完整性
lra feature status feature_N --set in_progress
# ... 编码 ...
lra records --feature feature_N  # 记录变更
lra feature status feature_N --set testing
# ... 测试 ...
lra feature status feature_N --set completed
```

### 2. 需求文档结构
Spec 文件必须包含以下章节：
- **背景**: 为什么需要这个功能
- **目标**: 要达成什么效果
- **方案**: 具体实现思路
- **步骤**: 分步实施计划

### 3. 禁止操作
- ❌ 不要跳过 spec 直接编码
- ❌ 不要跳过状态直接标记 completed
- ❌ 不要创建不符合 `feature_N` 格式的 ID
- ❌ 不要在 testing 状态前标记 completed

### 4. 每次提交后
```bash
lra records --feature <id> --format brief
```

### 5. 状态含义
| 状态 | 含义 |
|------|------|
| pending | 待处理，未开始 |
| in_progress | 开发中 |
| blocked | 被阻塞，需外部依赖 |
| testing | 测试中 |
| completed | 已完成 |

## 常见错误
1. **项目未初始化**: 先运行 `lra init`
2. **Feature ID 格式错误**: 必须是 `feature_N` 格式
3. **状态跳过**: 不能直接从 pending → completed
4. **Spec 不完整**: 运行 `lra spec validate` 检查

## 数据位置
```
.long-run-agent/
├── config.json          # 项目配置
├── feature_list.json    # Feature 列表
├── specs/               # 需求文档
│   └── feature_N.md
├── records/             # 代码变更记录
└── operation_log.json   # 操作日志
```
""")

    # ==================== 原有命令 ====================

    def project_register(self, path: str, name: str = None):
        print("\n📝 注册项目...\n")
        project_id = self.registry.register(path, name)
        if project_id:
            print(f"\n✓ 项目注册成功!")
            print(f"  项目 ID: {project_id}")

    def project_list(self, status: str = None):
        print("\n📋 项目列表\n")
        projects = self.registry.list_projects(status)
        if not projects:
            print("没有找到项目")
        else:
            for p in projects:
                is_working = " 🔧" if self.working_project_id == p["project_id"] else ""
                print(f"✅{is_working} {p['name']} ({p['project_id']})")
                print(f"   路径: {p['path']}")

    def stats(self):
        """显示统计信息"""
        print("\n📊 LRA 统计信息\n")

        project_stats = self.registry.get_stats()
        print(f"📁 项目: {project_stats['total']} 个")

        session_stats = self.session_manager.get_stats()
        print(f"🔄 会话: {session_stats['total']} 个")

        if os.path.exists(Config.get_metadata_dir()):
            status_stats = self.status_manager.get_status_statistics()
            if status_stats:
                print(f"\n📋 Feature 状态:")
                for status, count in status_stats.items():
                    if count > 0:
                        info = get_status_info(status)
                        print(f"   {info['emoji']} {info['name']}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description=f"LRA - Long-Running Agent 工具 v{CURRENT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ========== 初始化 ==========
    subparsers.add_parser("init", help="安装初始化向导")

    # ========== 版本管理 ==========
    subparsers.add_parser("version", help="显示版本信息")
    subparsers.add_parser("upgrade", help="执行升级")
    rollback_parser = subparsers.add_parser("rollback", help="回滚到备份")
    rollback_parser.add_argument("--backup", help="备份名称")

    # ========== Feature 管理 ==========
    feature_parser = subparsers.add_parser("feature", help="Feature 管理")
    feature_subparsers = feature_parser.add_subparsers(dest="subcommand")

    fc_parser = feature_subparsers.add_parser("create", help="创建 Feature")
    fc_parser.add_argument("title", help="Feature 标题")
    fc_parser.add_argument("--category", default="general", help="类别")
    fc_parser.add_argument("--priority", default="P1", choices=["P0", "P1", "P2"], help="优先级")
    fc_parser.add_argument("--assignee", default="", help="负责人")

    fs_parser = feature_subparsers.add_parser("status", help="查看/修改状态")
    fs_parser.add_argument("feature_id", help="Feature ID")
    fs_parser.add_argument("--set", dest="new_status", help="设置新状态")

    fl_parser = feature_subparsers.add_parser("list", help="列出 Features")
    fl_parser.add_argument("--status", help="按状态筛选")
    fl_parser.add_argument("--all", action="store_true", help="显示所有")

    # ========== 需求文档管理 ==========
    spec_parser = subparsers.add_parser("spec", help="需求文档管理")
    spec_subparsers = spec_parser.add_subparsers(dest="subcommand")

    sc_parser = spec_subparsers.add_parser("create", help="创建需求文档")
    sc_parser.add_argument("feature_id", help="Feature ID")
    sc_parser.add_argument("--title", default="", help="标题")

    sv_parser = spec_subparsers.add_parser("validate", help="校验需求文档")
    sv_parser.add_argument("feature_id", help="Feature ID")

    sl_parser = spec_subparsers.add_parser("list", help="列出需求文档")
    sl_parser.add_argument("--status", help="按状态筛选")

    # ========== 代码变更记录 ==========
    records_parser = subparsers.add_parser("records", help="代码变更记录")
    records_parser.add_argument("--feature", help="按 Feature ID 检索")
    records_parser.add_argument("--file", help="按文件路径检索")
    records_parser.add_argument("--format", choices=["brief", "detail"], default="detail")

    # ========== 项目管理 ==========
    project_parser = subparsers.add_parser("project", help="项目管理")
    project_subparsers = project_parser.add_subparsers(dest="subcommand")

    pc_parser = project_subparsers.add_parser("create", help="创建项目")
    pc_parser.add_argument("--name", required=True, help="项目名称")
    pc_parser.add_argument("--path", help="项目路径")

    ps_parser = project_subparsers.add_parser("switch", help="切换项目")
    ps_parser.add_argument("--project-id", required=True, help="项目 ID")

    project_subparsers.add_parser("list", help="列出项目")

    # ========== 操作日志 ==========
    logs_parser = subparsers.add_parser("logs", help="操作日志")
    logs_parser.add_argument("--action", help="按操作类型筛选")
    logs_parser.add_argument("--operator", help="按操作人筛选")
    logs_parser.add_argument("--feature", help="按 Feature 筛选")
    logs_parser.add_argument("--limit", type=int, default=20, help="限制数量")

    # ========== 代码检查 ==========
    code_parser = subparsers.add_parser("code", help="代码管理")
    code_subparsers = code_parser.add_subparsers(dest="subcommand")

    cc_parser = code_subparsers.add_parser("check", help="语法检查")
    cc_parser.add_argument("path", help="文件或目录路径")
    cc_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    # ========== Git 集成 ==========
    git_parser = subparsers.add_parser("git", help="Git 集成")
    git_parser.add_argument("--feature", help="关联的 Feature ID")

    # ========== 其他 ==========
    subparsers.add_parser("stats", help="显示统计")
    subparsers.add_parser("statuses", help="列出所有状态")
    subparsers.add_parser("llm-context", help="输出 AI 上下文（供 LLM 使用）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = LRACLI()

    if args.command == "init":
        from .installer import main as installer_main
        installer_main()
        return

    if args.command == "version":
        cli.version()

    elif args.command == "upgrade":
        cli.upgrade(auto_confirm=False)

    elif args.command == "rollback":
        cli.rollback(args.backup)

    elif args.command == "feature":
        if args.subcommand == "create":
            cli.feature_create(args.title, args.category, args.priority, args.assignee)
        elif args.subcommand == "status":
            cli.feature_status(args.feature_id, args.new_status)
        elif args.subcommand == "list":
            cli.feature_list(args.status, args.all)
        else:
            feature_parser.print_help()

    elif args.command == "spec":
        if args.subcommand == "create":
            cli.spec_create(args.feature_id, args.title)
        elif args.subcommand == "validate":
            cli.spec_validate(args.feature_id)
        elif args.subcommand == "list":
            cli.spec_list(args.status)
        else:
            spec_parser.print_help()

    elif args.command == "records":
        cli.records_show(args.feature, args.file, args.format)

    elif args.command == "project":
        if args.subcommand == "create":
            cli.project_create(args.name, args.path)
        elif args.subcommand == "switch":
            cli.project_switch(args.project_id)
        elif args.subcommand == "list":
            cli.project_list()
        else:
            project_parser.print_help()

    elif args.command == "logs":
        cli.logs_show(args.action, args.operator, args.feature, args.limit)

    elif args.command == "code":
        if args.subcommand == "check":
            cli.code_check(args.path, args.verbose)
        else:
            code_parser.print_help()

    elif args.command == "git":
        cli.git_info(args.feature)

    elif args.command == "stats":
        cli.stats()

    elif args.command == "statuses":
        print("\n📋 可用状态:\n")
        for status in get_all_statuses():
            print(f"{status['emoji']} {status['id']}: {status['name']}")
            print(f"   {status['description']}")
            print()

    elif args.command == "llm-context":
        cli.llm_context()


if __name__ == "__main__":
    main()
