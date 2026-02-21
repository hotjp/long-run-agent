#!/usr/bin/env python3
"""
代码变更记录管理器
v2.0 - 按 Feature 分文件存储，支持索引检索
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from .config import Config, SafeJson
except ImportError:
    print("警告: 无法导入 config 模块")


class RecordsManager:
    """代码变更记录管理器"""

    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)
        self.records_dir = Config.get_records_dir()
        self.index_path = Config.get_records_index_path()
        self._ensure_structure()

    def _ensure_structure(self):
        """确保目录结构存在"""
        os.makedirs(self.records_dir, exist_ok=True)
        if not os.path.exists(self.index_path):
            self._init_index()

    def _init_index(self) -> bool:
        """初始化索引文件"""
        index_data = {
            "by_feature": {},
            "by_file": {},
            "last_updated": datetime.now().isoformat(),
        }
        return SafeJson.write(self.index_path, index_data)

    def _load_index(self) -> Optional[Dict[str, Any]]:
        """加载索引"""
        return SafeJson.read(self.index_path)

    def _save_index(self, index_data: Dict[str, Any]) -> bool:
        """保存索引"""
        index_data["last_updated"] = datetime.now().isoformat()
        return SafeJson.write(self.index_path, index_data)

    def _get_record_path(self, feature_id: str) -> str:
        """获取 Feature 记录文件路径"""
        return os.path.join(self.records_dir, f"{feature_id}.json")

    def _load_record(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """加载 Feature 记录"""
        path = self._get_record_path(feature_id)
        return SafeJson.read(path)

    def _save_record(self, feature_id: str, record_data: Dict[str, Any]) -> bool:
        """保存 Feature 记录"""
        path = self._get_record_path(feature_id)
        return SafeJson.write(path, record_data)

    def _init_record(self, feature_id: str) -> Dict[str, Any]:
        """初始化 Feature 记录"""
        return {
            "feature_id": feature_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "records": [],
        }

    def add_record(
        self,
        feature_id: str,
        commit_hash: str = "",
        branch: str = "",
        files: Optional[List[Dict[str, Any]]] = None,
        description: str = "",
    ) -> bool:
        """
        添加代码变更记录
        """
        record_data = self._load_record(feature_id)
        if not record_data:
            record_data = self._init_record(feature_id)

        new_record = {
            "timestamp": datetime.now().isoformat(),
            "commit_hash": commit_hash,
            "branch": branch,
            "files": files or [],
            "description": description,
        }

        existing = False
        for r in record_data["records"]:
            if r.get("commit_hash") and r["commit_hash"] == commit_hash:
                existing = True
                break

        if not existing:
            record_data["records"].append(new_record)
            record_data["updated_at"] = datetime.now().isoformat()

            if not self._save_record(feature_id, record_data):
                return False

            self._update_index(feature_id, files or [])

        return True

    def _update_index(self, feature_id: str, files: List[Dict[str, Any]]):
        """更新索引"""
        index = self._load_index()
        if not index:
            index = {"by_feature": {}, "by_file": {}, "last_updated": ""}

        record_file = f"records/{feature_id}.json"

        if feature_id not in index["by_feature"]:
            index["by_feature"][feature_id] = []
        if record_file not in index["by_feature"][feature_id]:
            index["by_feature"][feature_id].append(record_file)

        for file_info in files:
            file_path = file_info.get("path", "")
            if file_path:
                if file_path not in index["by_file"]:
                    index["by_file"][file_path] = []
                entry = {"feature_id": feature_id, "record_file": record_file}
                if entry not in index["by_file"][file_path]:
                    index["by_file"][file_path].append(entry)

        self._save_index(index)

    def get_records_by_feature(
        self, feature_id: str, format: str = "detail"
    ) -> Optional[Dict[str, Any]]:
        """按 Feature ID 获取记录"""
        record_data = self._load_record(feature_id)
        if not record_data:
            return None

        if format == "brief":
            return {
                "feature_id": feature_id,
                "total_changes": len(record_data.get("records", [])),
                "files": list(
                    set(
                        f["path"]
                        for r in record_data.get("records", [])
                        for f in r.get("files", [])
                    )
                ),
            }

        return record_data

    def get_records_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """按文件路径获取关联记录"""
        index = self._load_index()
        if not index:
            return []

        results = []
        file_entries = index.get("by_file", {}).get(file_path, [])

        for entry in file_entries:
            feature_id = entry.get("feature_id")
            if feature_id:
                record = self._load_record(feature_id)
                if record:
                    filtered_records = [
                        r
                        for r in record.get("records", [])
                        if any(f.get("path") == file_path for f in r.get("files", []))
                    ]
                    results.append(
                        {"feature_id": feature_id, "records": filtered_records}
                    )

        return results

    def get_all_features_with_records(self) -> List[str]:
        """获取所有有记录的 Feature ID"""
        index = self._load_index()
        if not index:
            return []
        return list(index.get("by_feature", {}).keys())

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        index = self._load_index()
        if not index:
            return {"total_features": 0, "total_records": 0, "total_files": 0}

        total_features = len(index.get("by_feature", {}))
        total_files = len(index.get("by_file", {}))

        total_records = 0
        for feature_id in index.get("by_feature", {}).keys():
            record = self._load_record(feature_id)
            if record:
                total_records += len(record.get("records", []))

        return {
            "total_features": total_features,
            "total_records": total_records,
            "total_files": total_files,
            "last_updated": index.get("last_updated"),
        }

    def cleanup_old_records(self, days: int = 365) -> int:
        """清理超过指定天数的记录（归档）"""
        archive_dir = os.path.join(self.records_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)

        count = 0
        cutoff = datetime.now().timestamp() - (days * 86400)

        for filename in os.listdir(self.records_dir):
            if filename.endswith(".json") and filename != "index.json":
                path = os.path.join(self.records_dir, filename)
                stat = os.stat(path)

                if stat.st_mtime < cutoff:
                    archive_path = os.path.join(archive_dir, filename)
                    os.rename(path, archive_path)
                    count += 1

        return count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="代码变更记录管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    add_parser = subparsers.add_parser("add", help="添加记录")
    add_parser.add_argument("--feature-id", required=True, help="Feature ID")
    add_parser.add_argument("--commit", default="", help="Commit hash")
    add_parser.add_argument("--branch", default="", help="分支名")
    add_parser.add_argument("--files", help="文件列表(JSON格式)")
    add_parser.add_argument("--description", default="", help="描述")

    feature_parser = subparsers.add_parser("feature", help="按 Feature 查询")
    feature_parser.add_argument("--feature-id", required=True, help="Feature ID")
    feature_parser.add_argument(
        "--format", choices=["brief", "detail"], default="detail"
    )

    file_parser = subparsers.add_parser("file", help="按文件查询")
    file_parser.add_argument("--path", required=True, help="文件路径")

    subparsers.add_parser("list", help="列出所有有记录的 Features")
    subparsers.add_parser("stats", help="显示统计")

    args = parser.parse_args()

    manager = RecordsManager()

    if args.command == "add":
        import json

        files = json.loads(args.files) if args.files else []
        if manager.add_record(
            args.feature_id, args.commit, args.branch, files, args.description
        ):
            print("✅ 记录添加成功")
        else:
            print("❌ 记录添加失败")

    elif args.command == "feature":
        result = manager.get_records_by_feature(args.feature_id, args.format)
        if result:
            print(f"\n📋 {args.feature_id} 变更记录:\n")
            if args.format == "brief":
                print(f"  总变更数: {result['total_changes']}")
                print(f"  涉及文件: {len(result['files'])}")
            else:
                for r in result.get("records", []):
                    print(f"  [{r['timestamp']}]")
                    print(f"    Commit: {r.get('commit_hash', 'N/A')}")
                    print(f"    Branch: {r.get('branch', 'N/A')}")
                    if r.get("files"):
                        print(f"    Files:")
                        for f in r["files"]:
                            print(
                                f"      - {f.get('path')} (+{f.get('lines_added', 0)}/-{f.get('lines_deleted', 0)})"
                            )
                    print()
        else:
            print(f"❌ 未找到 {args.feature_id} 的记录")

    elif args.command == "file":
        results = manager.get_records_by_file(args.path)
        if results:
            print(f"\n📁 {args.path} 关联记录:\n")
            for r in results:
                print(f"  Feature: {r['feature_id']}")
                for rec in r["records"]:
                    print(f"    [{rec['timestamp']}] {rec.get('description', '')}")
        else:
            print(f"❌ 未找到 {args.path} 的关联记录")

    elif args.command == "list":
        features = manager.get_all_features_with_records()
        if features:
            print(f"\n📋 有记录的 Features ({len(features)} 个):\n")
            for f in features:
                record = manager.get_records_by_feature(f, "brief")
                if record:
                    print(
                        f"  {f}: {record['total_changes']} 次变更, {len(record['files'])} 个文件"
                    )
        else:
            print("暂无记录")

    elif args.command == "stats":
        stats = manager.get_statistics()
        print(f"\n📊 记录统计:\n")
        print(f"  Features: {stats['total_features']}")
        print(f"  变更记录: {stats['total_records']}")
        print(f"  涉及文件: {stats['total_files']}")
        if stats.get("last_updated"):
            print(f"  最后更新: {stats['last_updated']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
