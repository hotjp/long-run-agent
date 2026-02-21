#!/usr/bin/env python3
"""
操作日志审计管理器
v2.0 - 支持多种操作类型记录和筛选
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

try:
    from .config import Config, SafeJson
except ImportError:
    print("警告: 无法导入 config 模块")


class ActionType:
    """操作类型"""

    SPEC_CREATE = "spec_create"
    SPEC_UPDATE = "spec_update"
    STATUS_CHANGE = "status_change"
    CODE_COMMIT = "code_commit"
    LLM_CALL = "llm_call"
    FILE_UPDATE = "file_update"


ACTION_INFO = {
    ActionType.SPEC_CREATE: {"name": "创建需求文档", "emoji": "📝"},
    ActionType.SPEC_UPDATE: {"name": "修改需求文档", "emoji": "✏️"},
    ActionType.STATUS_CHANGE: {"name": "状态变更", "emoji": "🔄"},
    ActionType.CODE_COMMIT: {"name": "代码提交", "emoji": "📦"},
    ActionType.LLM_CALL: {"name": "大模型调用", "emoji": "🤖"},
    ActionType.FILE_UPDATE: {"name": "文件更新", "emoji": "📄"},
}


class OperationLogger:
    """操作日志管理器"""

    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)
        self.log_path = Config.get_operation_log_path()
        self._ensure_log_file()

    def _ensure_log_file(self):
        """确保日志文件存在"""
        if not os.path.exists(self.log_path):
            self._init_log_file()

    def _init_log_file(self) -> bool:
        """初始化日志文件"""
        log_data = {
            "logs": [],
            "index": {"by_operator": {}, "by_action": {}, "by_feature": {}},
        }
        return SafeJson.write(self.log_path, log_data)

    def _load_log(self) -> Optional[Dict[str, Any]]:
        """加载日志"""
        return SafeJson.read(self.log_path)

    def _save_log(self, log_data: Dict[str, Any]) -> bool:
        """保存日志"""
        return SafeJson.write(self.log_path, log_data)

    def _generate_log_id(self) -> str:
        """生成日志 ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid4())[:8]
        return f"log_{timestamp}_{short_uuid}"

    def _update_index(self, log_data: Dict[str, Any], log_entry: Dict[str, Any]):
        """更新索引"""
        log_id = log_entry["id"]
        operator = log_entry.get("operator", "unknown")
        action_type = log_entry.get("action_type")
        target = log_entry.get("target", {})
        target_id = target.get("id", "")

        index = log_data.get("index", {})

        if "by_operator" not in index:
            index["by_operator"] = {}
        if operator not in index["by_operator"]:
            index["by_operator"][operator] = []
        index["by_operator"][operator].append(log_id)

        if "by_action" not in index:
            index["by_action"] = {}
        if action_type not in index["by_action"]:
            index["by_action"][action_type] = []
        index["by_action"][action_type].append(log_id)

        if "by_feature" not in index:
            index["by_feature"] = {}
        if target.get("type") == "feature" and target_id:
            if target_id not in index["by_feature"]:
                index["by_feature"][target_id] = []
            index["by_feature"][target_id].append(log_id)

        log_data["index"] = index

    def log(
        self,
        action_type: str,
        target: Dict[str, Any],
        details: Dict[str, Any],
        operator: str = "system",
        operator_type: str = "system",
    ) -> Optional[str]:
        """
        记录操作日志
        返回日志 ID
        """
        log_data = self._load_log()
        if not log_data:
            log_data = {"logs": [], "index": {}}

        log_id = self._generate_log_id()

        log_entry = {
            "id": log_id,
            "timestamp": datetime.now().isoformat(),
            "operator": operator,
            "operator_type": operator_type,
            "action_type": action_type,
            "target": target,
            "details": details,
        }

        log_data["logs"].append(log_entry)

        self._update_index(log_data, log_entry)

        if self._save_log(log_data):
            return log_id
        return None

    def log_spec_create(
        self, feature_id: str, spec_path: str, operator: str = "system"
    ) -> Optional[str]:
        """记录创建需求文档"""
        return self.log(
            action_type=ActionType.SPEC_CREATE,
            target={"type": "feature", "id": feature_id},
            details={"spec_path": spec_path, "created_at": datetime.now().isoformat()},
            operator=operator,
            operator_type="human",
        )

    def log_spec_update(
        self,
        feature_id: str,
        spec_path: str,
        changes: str = "",
        operator: str = "system",
    ) -> Optional[str]:
        """记录修改需求文档"""
        return self.log(
            action_type=ActionType.SPEC_UPDATE,
            target={"type": "feature", "id": feature_id},
            details={
                "spec_path": spec_path,
                "changes": changes,
                "updated_at": datetime.now().isoformat(),
            },
            operator=operator,
            operator_type="human",
        )

    def log_status_change(
        self,
        feature_id: str,
        from_status: str,
        to_status: str,
        reason: str = "",
        operator: str = "system",
    ) -> Optional[str]:
        """记录状态变更"""
        return self.log(
            action_type=ActionType.STATUS_CHANGE,
            target={"type": "feature", "id": feature_id},
            details={
                "from_status": from_status,
                "to_status": to_status,
                "reason": reason,
            },
            operator=operator,
            operator_type="human",
        )

    def log_code_commit(
        self,
        feature_id: str,
        commit_hash: str,
        branch: str,
        message: str = "",
        files_count: int = 0,
        operator: str = "system",
    ) -> Optional[str]:
        """记录代码提交"""
        return self.log(
            action_type=ActionType.CODE_COMMIT,
            target={"type": "feature", "id": feature_id},
            details={
                "commit_hash": commit_hash,
                "branch": branch,
                "message": message,
                "files_count": files_count,
            },
            operator=operator,
            operator_type="human",
        )

    def log_llm_call(
        self,
        feature_id: str,
        scenario: str,
        success: bool,
        tokens_used: int = 0,
        operator: str = "system",
    ) -> Optional[str]:
        """记录大模型调用"""
        return self.log(
            action_type=ActionType.LLM_CALL,
            target={"type": "feature", "id": feature_id},
            details={
                "scenario": scenario,
                "success": success,
                "tokens_used": tokens_used,
            },
            operator=operator,
            operator_type="system",
        )

    def log_file_update(
        self,
        file_path: str,
        update_type: str,
        details: str = "",
        operator: str = "system",
    ) -> Optional[str]:
        """记录文件更新"""
        return self.log(
            action_type=ActionType.FILE_UPDATE,
            target={"type": "file", "id": file_path},
            details={"update_type": update_type, "details": details},
            operator=operator,
            operator_type="human",
        )

    def get_logs(
        self,
        action_type: Optional[str] = None,
        operator: Optional[str] = None,
        feature_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取日志（支持筛选）"""
        log_data = self._load_log()
        if not log_data:
            return []

        logs = log_data.get("logs", [])

        if feature_id:
            index = log_data.get("index", {})
            feature_log_ids = set(index.get("by_feature", {}).get(feature_id, []))
            logs = [l for l in logs if l["id"] in feature_log_ids]

        if action_type:
            logs = [l for l in logs if l.get("action_type") == action_type]

        if operator:
            logs = [l for l in logs if l.get("operator") == operator]

        if start_time:
            logs = [l for l in logs if l.get("timestamp", "") >= start_time]

        if end_time:
            logs = [l for l in logs if l.get("timestamp", "") <= end_time]

        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return logs[:limit]

    def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取日志"""
        log_data = self._load_log()
        if not log_data:
            return None

        for log in log_data.get("logs", []):
            if log.get("id") == log_id:
                return log
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        log_data = self._load_log()
        if not log_data:
            return {"total": 0, "by_action": {}, "by_operator": {}}

        logs = log_data.get("logs", [])

        stats = {"total": len(logs), "by_action": {}, "by_operator": {}}

        for log in logs:
            action = log.get("action_type", "unknown")
            stats["by_action"][action] = stats["by_action"].get(action, 0) + 1

            operator = log.get("operator", "unknown")
            stats["by_operator"][operator] = stats["by_operator"].get(operator, 0) + 1

        return stats

    def clear_old_logs(self, days: int = 90) -> int:
        """清理超过指定天数的日志"""
        log_data = self._load_log()
        if not log_data:
            return 0

        cutoff = datetime.now().timestamp() - (days * 86400)
        cutoff_str = datetime.fromtimestamp(cutoff).isoformat()

        original_count = len(log_data.get("logs", []))
        log_data["logs"] = [
            l for l in log_data.get("logs", []) if l.get("timestamp", "") >= cutoff_str
        ]
        new_count = len(log_data["logs"])

        log_data["index"] = {"by_operator": {}, "by_action": {}, "by_feature": {}}
        for log in log_data["logs"]:
            self._update_index(log_data, log)

        self._save_log(log_data)

        return original_count - new_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="操作日志管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    list_parser = subparsers.add_parser("list", help="列出日志")
    list_parser.add_argument("--action", help="按操作类型筛选")
    list_parser.add_argument("--operator", help="按操作人筛选")
    list_parser.add_argument("--feature", help="按 Feature ID 筛选")
    list_parser.add_argument("--limit", type=int, default=20, help="限制数量")

    info_parser = subparsers.add_parser("info", help="查看日志详情")
    info_parser.add_argument("--log-id", required=True, help="日志 ID")

    subparsers.add_parser("stats", help="显示统计")

    subparsers.add_parser("types", help="列出所有操作类型")

    args = parser.parse_args()

    logger = OperationLogger()

    if args.command == "list":
        logs = logger.get_logs(
            action_type=args.action,
            operator=args.operator,
            feature_id=args.feature,
            limit=args.limit,
        )
        if not logs:
            print("没有找到日志")
        else:
            print(f"\n📋 操作日志 ({len(logs)} 条):\n")
            for log in logs:
                action_info = ACTION_INFO.get(
                    log["action_type"], {"emoji": "📄", "name": log["action_type"]}
                )
                target = log.get("target", {})
                print(
                    f"{action_info['emoji']} [{log['timestamp'][:19]}] {log['operator']}"
                )
                print(f"   类型: {action_info['name']}")
                print(f"   目标: {target.get('type', '')}/{target.get('id', '')}")
                if log.get("details"):
                    details_str = str(log["details"])[:100]
                    print(f"   详情: {details_str}...")
                print()

    elif args.command == "info":
        log = logger.get_log_by_id(args.log_id)
        if log:
            import json

            print(f"\n📋 日志详情:\n")
            print(f"  ID: {log['id']}")
            print(f"  时间: {log['timestamp']}")
            print(f"  操作人: {log['operator']} ({log['operator_type']})")
            print(f"  操作类型: {log['action_type']}")
            print(f"  目标: {json.dumps(log['target'], ensure_ascii=False)}")
            print(
                f"  详情:\n{json.dumps(log['details'], indent=4, ensure_ascii=False)}"
            )
        else:
            print(f"❌ 未找到日志: {args.log_id}")

    elif args.command == "stats":
        stats = logger.get_statistics()
        print(f"\n📊 日志统计:\n")
        print(f"  总数: {stats['total']}")
        print(f"\n  按操作类型:")
        for action, count in stats.get("by_action", {}).items():
            info = ACTION_INFO.get(action, {"emoji": "📄", "name": action})
            print(f"    {info['emoji']} {info['name']}: {count}")
        print(f"\n  按操作人:")
        for operator, count in stats.get("by_operator", {}).items():
            print(f"    {operator}: {count}")

    elif args.command == "types":
        print("\n📋 操作类型:\n")
        for action_type, info in ACTION_INFO.items():
            print(f"  {info['emoji']} {action_type}: {info['name']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
