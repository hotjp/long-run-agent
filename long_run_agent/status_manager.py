#!/usr/bin/env python3
"""
Feature 状态管理器
v2.0 - 支持7种状态及状态流转校验
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

try:
    from .config import Config, SafeJson
except ImportError:
    print("警告: 无法导入 config 模块")


class FeatureStatus(str, Enum):
    """Feature 状态枚举"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    PENDING_TEST = "pending_test"
    TEST_FAILED = "test_failed"
    COMPLETED = "completed"
    SKIPPED = "skipped"


VALID_TRANSITIONS = {
    FeatureStatus.PENDING.value: [
        FeatureStatus.IN_PROGRESS.value,
        FeatureStatus.SKIPPED.value,
    ],
    FeatureStatus.IN_PROGRESS.value: [
        FeatureStatus.BLOCKED.value,
        FeatureStatus.PENDING_TEST.value,
    ],
    FeatureStatus.BLOCKED.value: [FeatureStatus.IN_PROGRESS.value],
    FeatureStatus.PENDING_TEST.value: [
        FeatureStatus.TEST_FAILED.value,
        FeatureStatus.COMPLETED.value,
    ],
    FeatureStatus.TEST_FAILED.value: [FeatureStatus.IN_PROGRESS.value],
    FeatureStatus.COMPLETED.value: [],
    FeatureStatus.SKIPPED.value: [],
}

STATUS_INFO = {
    FeatureStatus.PENDING.value: {
        "name": "待开发",
        "description": "需求已确认，未启动开发工作",
        "emoji": "⏳",
    },
    FeatureStatus.IN_PROGRESS.value: {
        "name": "进行中",
        "description": "开发工作正在执行中",
        "emoji": "🔄",
    },
    FeatureStatus.BLOCKED.value: {
        "name": "阻塞中",
        "description": "开发中遇到无法解决的问题，暂停开发",
        "emoji": "🚫",
    },
    FeatureStatus.PENDING_TEST.value: {
        "name": "待测试",
        "description": "开发工作已完成，等待测试验证",
        "emoji": "🧪",
    },
    FeatureStatus.TEST_FAILED.value: {
        "name": "测试失败",
        "description": "测试未通过，需返回开发修改",
        "emoji": "❌",
    },
    FeatureStatus.COMPLETED.value: {
        "name": "已完成",
        "description": "测试通过，Feature 开发全流程闭环",
        "emoji": "✅",
    },
    FeatureStatus.SKIPPED.value: {
        "name": "已跳过",
        "description": "无需开发，直接跳过（如废弃需求）",
        "emoji": "⏭️",
    },
}


class SpecStatus(str, Enum):
    """需求文档状态"""

    DRAFT = "draft"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"


SPEC_STATUS_INFO = {
    SpecStatus.DRAFT.value: {"name": "草稿", "emoji": "📝"},
    SpecStatus.REVIEWING.value: {"name": "评审中", "emoji": "👀"},
    SpecStatus.APPROVED.value: {"name": "已确认", "emoji": "✅"},
    SpecStatus.REJECTED.value: {"name": "已驳回", "emoji": "❌"},
}


def validate_transition(current_status: str, target_status: str) -> Dict[str, Any]:
    """
    验证状态流转是否合法
    返回: {"valid": bool, "error": str, "suggestion": str}
    """
    if current_status == target_status:
        return {"valid": True}

    allowed_transitions = VALID_TRANSITIONS.get(current_status, [])

    if target_status not in allowed_transitions:
        return {
            "valid": False,
            "error": f"不允许从 '{current_status}' 直接变更为 '{target_status}'",
            "suggestion": f"可流转到: {allowed_transitions}",
        }

    return {"valid": True}


def get_status_info(status: str) -> Dict[str, str]:
    """获取状态信息"""
    return STATUS_INFO.get(status, {"name": status, "description": "", "emoji": "❓"})


def get_all_statuses() -> List[Dict[str, str]]:
    """获取所有状态列表"""
    return [
        {"id": status.value, **STATUS_INFO[status.value]} for status in FeatureStatus
    ]


def get_valid_transitions_for_status(status: str) -> List[str]:
    """获取指定状态的可流转状态列表"""
    return VALID_TRANSITIONS.get(status, [])


class StatusManager:
    """Feature 状态管理器"""

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.feature_list_path = Config.get_feature_list_path()
        self.lock_path = Config.get_lock_path()

    def _load_feature_list(self) -> Optional[Dict[str, Any]]:
        """加载功能清单"""
        return SafeJson.read(self.feature_list_path)

    def _save_feature_list(self, data: Dict[str, Any]) -> bool:
        """保存功能清单"""
        return SafeJson.write(self.feature_list_path, data)

    def _find_feature(
        self, feature_list: Dict[str, Any], feature_id: str
    ) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        """查找 Feature"""
        for idx, feature in enumerate(feature_list.get("features", [])):
            if feature.get("id") == feature_id:
                return idx, feature
        return None, None

    def get_feature_status(self, feature_id: str) -> Optional[str]:
        """获取 Feature 当前状态"""
        feature_list = self._load_feature_list()
        if not feature_list:
            return None

        _, feature = self._find_feature(feature_list, feature_id)
        if feature:
            return feature.get("status", FeatureStatus.PENDING.value)
        return None

    def change_status(
        self,
        feature_id: str,
        new_status: str,
        operator: str = "unknown",
        reason: str = "",
        progress_percentage: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        变更 Feature 状态
        返回: (成功, 消息)
        """
        feature_list = self._load_feature_list()
        if not feature_list:
            return False, "无法读取功能清单"

        idx, feature = self._find_feature(feature_list, feature_id)
        if feature is None:
            return False, f"未找到 Feature: {feature_id}"

        current_status = feature.get("status", FeatureStatus.PENDING.value)

        validation = validate_transition(current_status, new_status)
        if not validation["valid"]:
            return False, validation["error"]

        feature["status"] = new_status
        feature["status_updated_at"] = datetime.now().isoformat()

        if progress_percentage is not None:
            feature["progress_percentage"] = min(100, max(0, progress_percentage))
        elif new_status == FeatureStatus.COMPLETED.value:
            feature["progress_percentage"] = 100
        elif new_status == FeatureStatus.PENDING.value:
            feature["progress_percentage"] = 0

        if new_status == FeatureStatus.COMPLETED.value:
            feature["completed_at"] = datetime.now().isoformat()
            feature["passes"] = True
        elif new_status == FeatureStatus.IN_PROGRESS.value:
            feature["passes"] = False

        feature_list["features"][idx] = feature

        if not self._save_feature_list(feature_list):
            return False, "保存失败"

        status_info = get_status_info(new_status)
        message = f"状态变更: {current_status} -> {new_status}"
        if reason:
            message += f" ({reason})"

        return True, message

    def update_progress(
        self, feature_id: str, progress_percentage: int, note: str = ""
    ) -> Tuple[bool, str]:
        """更新 Feature 进度"""
        feature_list = self._load_feature_list()
        if not feature_list:
            return False, "无法读取功能清单"

        idx, feature = self._find_feature(feature_list, feature_id)
        if feature is None:
            return False, f"未找到 Feature: {feature_id}"

        current_status = feature.get("status", FeatureStatus.PENDING.value)

        if current_status in [
            FeatureStatus.COMPLETED.value,
            FeatureStatus.SKIPPED.value,
        ]:
            return False, f"Feature 已处于终态: {current_status}"

        feature["progress_percentage"] = min(100, max(0, progress_percentage))
        feature["status_updated_at"] = datetime.now().isoformat()

        if note:
            if "notes" not in feature:
                feature["notes"] = []
            feature["notes"].append(
                {"timestamp": datetime.now().isoformat(), "note": note}
            )

        feature_list["features"][idx] = feature

        if not self._save_feature_list(feature_list):
            return False, "保存失败"

        return True, f"进度更新为: {progress_percentage}%"

    def assign_feature(self, feature_id: str, assignee: str) -> Tuple[bool, str]:
        """指派 Feature 负责人"""
        feature_list = self._load_feature_list()
        if not feature_list:
            return False, "无法读取功能清单"

        idx, feature = self._find_feature(feature_list, feature_id)
        if feature is None:
            return False, f"未找到 Feature: {feature_id}"

        feature["assignee"] = assignee
        feature["status_updated_at"] = datetime.now().isoformat()

        feature_list["features"][idx] = feature

        if not self._save_feature_list(feature_list):
            return False, "保存失败"

        return True, f"已指派给: {assignee}"

    def get_features_by_status(self, status: str) -> List[Dict[str, Any]]:
        """按状态获取 Features"""
        feature_list = self._load_feature_list()
        if not feature_list:
            return []

        return [
            f
            for f in feature_list.get("features", [])
            if f.get("status", FeatureStatus.PENDING.value) == status
        ]

    def get_status_statistics(self) -> Dict[str, int]:
        """获取状态统计"""
        feature_list = self._load_feature_list()
        if not feature_list:
            return {}

        stats = {status.value: 0 for status in FeatureStatus}

        for feature in feature_list.get("features", []):
            status = feature.get("status", FeatureStatus.PENDING.value)
            if status in stats:
                stats[status] += 1

        return stats

    def get_valid_transitions_for_status(self, status: str) -> List[str]:
        """获取指定状态的可流转状态列表（实例方法）"""
        return VALID_TRANSITIONS.get(status, [])


    def get_blocked_features(self) -> List[Dict[str, Any]]:
        """获取被阻塞的 Features"""
        return self.get_features_by_status(FeatureStatus.BLOCKED.value)

    def get_pending_features(self) -> List[Dict[str, Any]]:
        """获取待开发的 Features"""
        return self.get_features_by_status(FeatureStatus.PENDING.value)

    def get_in_progress_features(self) -> List[Dict[str, Any]]:
        """获取进行中的 Features"""
        return self.get_features_by_status(FeatureStatus.IN_PROGRESS.value)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Feature 状态管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    status_parser = subparsers.add_parser("status", help="查看 Feature 状态")
    status_parser.add_argument("--feature-id", required=True, help="Feature ID")

    change_parser = subparsers.add_parser("change", help="变更 Feature 状态")
    change_parser.add_argument("--feature-id", required=True, help="Feature ID")
    change_parser.add_argument("--status", required=True, help="新状态")
    change_parser.add_argument("--reason", default="", help="变更原因")
    change_parser.add_argument("--operator", default="cli", help="操作人")

    progress_parser = subparsers.add_parser("progress", help="更新 Feature 进度")
    progress_parser.add_argument("--feature-id", required=True, help="Feature ID")
    progress_parser.add_argument(
        "--percentage", type=int, required=True, help="进度百分比"
    )

    assign_parser = subparsers.add_parser("assign", help="指派 Feature 负责人")
    assign_parser.add_argument("--feature-id", required=True, help="Feature ID")
    assign_parser.add_argument("--assignee", required=True, help="负责人")

    subparsers.add_parser("stats", help="显示状态统计")

    list_parser = subparsers.add_parser("list", help="按状态列出 Features")
    list_parser.add_argument("--status", help="状态筛选")

    subparsers.add_parser("statuses", help="列出所有可用状态")

    transitions_parser = subparsers.add_parser("transitions", help="查看状态流转规则")
    transitions_parser.add_argument("--status", help="查看指定状态的可流转状态")

    args = parser.parse_args()

    manager = StatusManager()

    if args.command == "status":
        status = manager.get_feature_status(args.feature_id)
        if status:
            info = get_status_info(status)
            print(f"{info['emoji']} {args.feature_id}: {info['name']} ({status})")
        else:
            print(f"❌ 未找到 Feature: {args.feature_id}")

    elif args.command == "change":
        success, message = manager.change_status(
            args.feature_id, args.status, args.operator, args.reason
        )
        print(f"{'✅' if success else '❌'} {message}")

    elif args.command == "progress":
        success, message = manager.update_progress(args.feature_id, args.percentage)
        print(f"{'✅' if success else '❌'} {message}")

    elif args.command == "assign":
        success, message = manager.assign_feature(args.feature_id, args.assignee)
        print(f"{'✅' if success else '❌'} {message}")

    elif args.command == "stats":
        stats = manager.get_status_statistics()
        print("\n📊 状态统计:\n")
        for status, count in stats.items():
            info = get_status_info(status)
            print(f"  {info['emoji']} {info['name']}: {count}")

    elif args.command == "list":
        if args.status:
            features = manager.get_features_by_status(args.status)
        else:
            features = []
            feature_list = manager._load_feature_list()
            if feature_list:
                features = feature_list.get("features", [])

        if not features:
            print("没有找到 Features")
        else:
            print(f"\n📋 Features ({len(features)} 个):\n")
            for f in features:
                status = f.get("status", "pending")
                info = get_status_info(status)
                progress = f.get("progress_percentage", 0)
                print(f"{info['emoji']} {f['id']}: {f.get('description', 'N/A')}")
                print(f"   状态: {info['name']} | 进度: {progress}%")
                print()

    elif args.command == "statuses":
        print("\n📋 可用状态:\n")
        for status in get_all_statuses():
            transitions = get_valid_transitions_for_status(status["id"])
            print(f"{status['emoji']} {status['id']}: {status['name']}")
            print(f"   {status['description']}")
            print(f"   可流转到: {', '.join(transitions) if transitions else '无'}")
            print()

    elif args.command == "transitions":
        if args.status:
            transitions = get_valid_transitions_for_status(args.status)
            info = get_status_info(args.status)
            print(f"\n{info['emoji']} {info['name']} 可流转到:")
            for t in transitions:
                t_info = get_status_info(t)
                print(f"  -> {t_info['emoji']} {t_info['name']}")
        else:
            print("\n📋 状态流转规则:\n")
            for status, transitions in VALID_TRANSITIONS.items():
                info = get_status_info(status)
                targets = [get_status_info(t)["emoji"] + " " + t for t in transitions]
                print(
                    f"{info['emoji']} {status} -> {', '.join(targets) if targets else '(终态)'}"
                )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
