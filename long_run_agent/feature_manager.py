#!/usr/bin/env python3
"""
功能清单管理器
v2.0 - 集成状态管理和新字段
"""

import json

import os
import sys
import argparse
from datetime import datetime

try:
    from .config import (
        Config,
        SafeJson,
        validate_feature_id,
        validate_project_initialized,
    )
    from .status_manager import (
        StatusManager,
        FeatureStatus,
        get_status_info,
        validate_transition,
        STATUS_INFO,
    )
    from .operation_logger import OperationLogger
    from .records_manager import RecordsManager
    from .spec_manager import SpecManager
    from .upgrade_manager import check_and_upgrade
except ImportError as e:
    print(f"警告: 无法导入模块: {e}")
    METADATA_DIR = ".long-run-agent"
    FEATURE_LIST_FILE = os.path.join(METADATA_DIR, "feature_list.json")
    CONFIG_FILE = os.path.join(METADATA_DIR, "config.json")

    def validate_project_initialized():
        if not os.path.exists(FEATURE_LIST_FILE):
            return False, f"未找到功能清单: {FEATURE_LIST_FILE}"
        return True, "项目已初始化"


def init_project(project_name, spec):
    """初始化新项目"""
    check_and_upgrade()

    try:
        from .config import Config, SafeJson
        from .upgrade_manager import UpgradeManager

        metadata_dir = Config.get_metadata_dir()
        config_path = Config.get_config_path()
        feature_list_path = Config.get_feature_list_path()

        Config.ensure_dirs()

        config = {
            "project_name": project_name,
            "spec": spec,
            "created_at": datetime.now().isoformat(),
            "version": "2.0.0",
            "schema_version": "2026-02-21",
            "upgraded_at": datetime.now().isoformat(),
            "upgrade_history": [],
        }

        if not SafeJson.write(config_path, config):
            print("❌ 创建配置文件失败")
            return

        feature_list = {
            "project_name": project_name,
            "created_at": datetime.now().isoformat(),
            "features": [],
        }

        if not SafeJson.write(feature_list_path, feature_list):
            print("❌ 创建功能清单失败")
            return

        print(f"✓ 项目 '{project_name}' 初始化成功")
        print(f"✓ 创建配置文件: {config_path}")
        print(f"✓ 创建功能清单: {feature_list_path}")
        print(f"\n下一步: 使用 'lra feature create' 添加功能")

    except ImportError:
        pass


def add_feature(category, description, steps=None, priority="P1", assignee=""):
    """添加功能到清单"""
    check_and_upgrade()

    try:
        from .config import Config, SafeJson

        feature_list_path = Config.get_feature_list_path()
        lock_path = Config.get_lock_path()

        ok, msg = validate_project_initialized()
        if not ok:
            print(f"❌ 错误: {msg}")
            print("请先运行 'lra init' 命令初始化项目")
            sys.exit(1)

        feature_list = SafeJson.read_with_lock(feature_list_path, lock_path)
        if not feature_list:
            print("❌ 读取功能清单失败")
            sys.exit(1)

        feature_id = f"feature_{len(feature_list['features']) + 1:03d}"

        if steps:
            step_list = [s.strip() for s in steps.split(";")]
        else:
            step_list = [
                f"实现 {description}",
                f"测试 {description}",
                f"验证 {description}",
            ]

        feature = {
            "id": feature_id,
            "category": category,
            "description": description,
            "steps": step_list,
            "priority": priority,
            "status": FeatureStatus.PENDING.value,
            "status_updated_at": datetime.now().isoformat(),
            "progress_percentage": 0,
            "assignee": assignee,
            "passes": False,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "spec_file": f"specs/{feature_id}.md",
        }

        feature_list["features"].append(feature)

        if not SafeJson.write_with_lock(feature_list_path, feature_list, lock_path):
            print("❌ 保存功能清单失败")
            return

        try:
            logger = OperationLogger()
            logger.log_spec_create(feature_id, feature["spec_file"], "system")
        except:
            pass

        print(f"✓ 添加功能: {feature_id}")
        print(f"  类别: {category}")
        print(f"  描述: {description}")
        print(f"  优先级: {priority}")
        print(f"  状态: {FeatureStatus.PENDING.value}")

    except ImportError:
        pass


def list_features(show_all=False, status_filter=None):
    """列出所有功能"""
    check_and_upgrade()

    try:
        from .config import Config, SafeJson

        feature_list_path = Config.get_feature_list_path()

        ok, msg = validate_project_initialized()
        if not ok:
            print(f"❌ 错误: {msg}")
            sys.exit(1)

        feature_list = SafeJson.read(feature_list_path)
        if not feature_list:
            print("❌ 读取功能清单失败")
            sys.exit(1)

        project_name = feature_list.get("project_name", "Unknown")
        features = feature_list["features"]

        if status_filter:
            features = [
                f for f in features if f.get("status", "pending") == status_filter
            ]

        print(f"\n📋 项目: {project_name}")
        print(f"   总功能数: {len(features)}")

        status_counts = {}
        for f in feature_list["features"]:
            s = f.get("status", "pending")
            status_counts[s] = status_counts.get(s, 0) + 1

        for s, count in status_counts.items():
            info = get_status_info(s)
            print(f"   {info['emoji']} {info['name']}: {count}")
        print()

        if show_all:
            for feature in features:
                status = feature.get("status", "pending")
                info = get_status_info(status)
                progress = feature.get("progress_percentage", 0)
                print(f"{info['emoji']} {feature['id']}: {feature['description']}")
                print(f"   类别: {feature['category']}")
                print(f"   优先级: {feature.get('priority', 'P1')}")
                print(f"   状态: {info['name']} ({progress}%)")
                print(f"   负责人: {feature.get('assignee', '-')}")
                print()
        else:
            pending = [
                f
                for f in features
                if f.get("status", "pending") not in ["completed", "skipped"]
            ]
            for feature in pending:
                status = feature.get("status", "pending")
                info = get_status_info(status)
                print(f"{info['emoji']} {feature['id']}: {feature['description']}")
                print(
                    f"   类别: {feature['category']}, 优先级: {feature.get('priority', 'P1')}"
                )
                print()

    except ImportError:
        pass


def get_next_feature():
    """获取下一个待完成的功能（按优先级排序）"""
    check_and_upgrade()

    try:
        from .config import Config, SafeJson

        feature_list_path = Config.get_feature_list_path()

        ok, msg = validate_project_initialized()
        if not ok:
            return None

        feature_list = SafeJson.read(feature_list_path)
        if not feature_list:
            return None

        pending = [
            f
            for f in feature_list["features"]
            if f.get("status", "pending")
            in ["pending", "in_progress", "blocked", "test_failed"]
        ]
        if not pending:
            return None

        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        pending.sort(key=lambda x: priority_order.get(x.get("priority", "P1"), 1))
        return pending[0]

    except ImportError:
        return None


def update_feature_status(feature_id, passes, notes=None):
    """更新功能状态"""
    check_and_upgrade()

    try:
        from .config import Config, SafeJson
        from .status_manager import StatusManager, FeatureStatus

        status_manager = StatusManager()

        if passes:
            success, message = status_manager.change_status(
                feature_id, FeatureStatus.COMPLETED.value, "system", notes or "任务完成"
            )
        else:
            current_status = status_manager.get_feature_status(feature_id)
            if current_status == FeatureStatus.PENDING_TEST.value:
                success, message = status_manager.change_status(
                    feature_id,
                    FeatureStatus.TEST_FAILED.value,
                    "system",
                    notes or "测试失败",
                )
            else:
                success, message = True, "状态未变更"

        status = "完成" if passes else "未完成"
        print(f"✓ 更新功能 {feature_id} 状态为: {status}")

    except ImportError:
        pass


def get_feature_stats():
    """获取功能统计信息"""
    check_and_upgrade()

    try:
        from .config import Config, SafeJson

        feature_list_path = Config.get_feature_list_path()

        ok, msg = validate_project_initialized()
        if not ok:
            return None

        feature_list = SafeJson.read(feature_list_path)
        if not feature_list:
            return None

        features = feature_list["features"]
        total = len(features)
        completed = sum(1 for f in features if f.get("status") == "completed")
        pending = total - completed

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "progress": (completed / total * 100) if total > 0 else 0,
        }

    except ImportError:
        return None


def main():
    parser = argparse.ArgumentParser(description="功能清单管理器 v2.0")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    init_parser = subparsers.add_parser("init", help="初始化新项目")
    init_parser.add_argument("--project-name", required=True, help="项目名称")
    init_parser.add_argument("--spec", required=True, help="项目规格描述")

    add_parser = subparsers.add_parser("add", help="添加功能")
    add_parser.add_argument("--category", required=True, help="功能类别")
    add_parser.add_argument("--description", required=True, help="功能描述")
    add_parser.add_argument("--steps", help="步骤列表 (分号分隔)")
    add_parser.add_argument("--priority", default="P1", help="优先级 (P0/P1/P2)")
    add_parser.add_argument("--assignee", default="", help="负责人")

    list_parser = subparsers.add_parser("list", help="列出所有功能")
    list_parser.add_argument("--all", action="store_true", help="显示所有功能")
    list_parser.add_argument("--status", help="按状态筛选")

    subparsers.add_parser("next", help="获取下一个任务")

    complete_parser = subparsers.add_parser("complete", help="标记功能完成")
    complete_parser.add_argument("--feature-id", required=True, help="功能 ID")
    complete_parser.add_argument("--notes", help="完成说明")

    subparsers.add_parser("status", help="显示统计信息")

    args = parser.parse_args()

    if args.command == "init":
        init_project(args.project_name, args.spec)
    elif args.command == "add":
        add_feature(
            args.category, args.description, args.steps, args.priority, args.assignee
        )
    elif args.command == "list":
        list_features(args.all, args.status)
    elif args.command == "next":
        next_feature = get_next_feature()
        if next_feature:
            info = get_status_info(next_feature.get("status", "pending"))
            print(f"下一个任务:")
            print(f"  ID: {next_feature['id']}")
            print(f"  描述: {next_feature['description']}")
            print(f"  类别: {next_feature['category']}")
            print(f"  优先级: {next_feature.get('priority', 'P1')}")
            print(f"  状态: {info['name']}")
            print(f"  步骤: {'; '.join(next_feature['steps'])}")
        else:
            print("所有功能已完成！")
    elif args.command == "complete":
        update_feature_status(args.feature_id, True, args.notes)
    elif args.command == "status":
        stats = get_feature_stats()
        if stats:
            print(f"\n功能统计:")
            print(f"  总数: {stats['total']}")
            print(f"  已完成: {stats['completed']}")
            print(f"  待完成: {stats['pending']}")
            print(f"  进度: {stats['progress']:.1f}%")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
