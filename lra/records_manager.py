#!/usr/bin/env python3
"""
代码变更记录管理器
v3.0 - Git 自动同步、精简输出
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, List

from lra.config import Config, SafeJson, GitHelper


class RecordsManager:
    def __init__(self):
        self.records_dir = Config.get_records_dir()
        self.index_path = Config.get_records_index_path()
        os.makedirs(self.records_dir, exist_ok=True)

    def _get_path(self, feature_id: str) -> str:
        return os.path.join(self.records_dir, f"{feature_id}.json")

    def _load(self, feature_id: str) -> Optional[Dict[str, Any]]:
        return SafeJson.read(self._get_path(feature_id))

    def _save(self, feature_id: str, data: Dict[str, Any]) -> bool:
        return SafeJson.write(self._get_path(feature_id), data)

    def _init_record(self, feature_id: str) -> Dict[str, Any]:
        return {
            "feature_id": feature_id,
            "created_at": datetime.now().isoformat(),
            "records": [],
        }

    def add(
        self,
        feature_id: str,
        commit: str = "",
        branch: str = "",
        files: List[Dict] = None,
        desc: str = "",
    ) -> bool:
        record_data = self._load(feature_id)
        if not record_data:
            record_data = self._init_record(feature_id)

        entry = {
            "ts": datetime.now().isoformat(),
            "commit": commit,
            "branch": branch,
            "files": files or [],
            "desc": desc,
        }

        if commit:
            existing = any(r.get("commit") == commit for r in record_data.get("records", []))
            if existing:
                return True

        record_data["records"].append(entry)
        return self._save(feature_id, record_data)

    def auto_record(self, feature_id: str, desc: str = "") -> Dict[str, Any]:
        commit_info = GitHelper.get_current_commit()
        files = GitHelper.get_diff_files() or GitHelper.get_staged_files()

        self.add(
            feature_id,
            commit=commit_info.get("hash", ""),
            branch=commit_info.get("branch", ""),
            files=files,
            desc=desc or commit_info.get("message", "")[:50],
        )

        return {
            "feature_id": feature_id,
            "commit": commit_info.get("hash", ""),
            "branch": commit_info.get("branch", ""),
            "files_count": len(files),
        }

    def get(self, feature_id: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        record_data = self._load(feature_id)
        if not record_data:
            return None

        records = record_data.get("records", [])[-limit:]
        return {
            "feature_id": feature_id,
            "total": len(record_data.get("records", [])),
            "records": records,
        }

    def get_brief(self, feature_id: str) -> Optional[Dict[str, Any]]:
        record_data = self._load(feature_id)
        if not record_data:
            return None

        records = record_data.get("records", [])
        all_files = set()
        for r in records:
            for f in r.get("files", []):
                all_files.add(f.get("path", ""))

        return {
            "feature_id": feature_id,
            "commits": len(records),
            "files": list(all_files)[:10],
        }

    def get_timeline(self, feature_id: str) -> List[Dict[str, Any]]:
        record_data = self._load(feature_id)
        if not record_data:
            return []

        return record_data.get("records", [])

    def analyze(self, feature_id: str) -> Optional[Dict[str, Any]]:
        record_data = self._load(feature_id)
        if not record_data:
            return None

        records = record_data.get("records", [])
        total_added = 0
        total_deleted = 0
        file_stats = {}

        for r in records:
            for f in r.get("files", []):
                path = f.get("path", "")
                added = f.get("added", 0)
                deleted = f.get("deleted", 0)
                total_added += added
                total_deleted += deleted
                if path:
                    if path not in file_stats:
                        file_stats[path] = {"added": 0, "deleted": 0, "changes": 0}
                    file_stats[path]["added"] += added
                    file_stats[path]["deleted"] += deleted
                    file_stats[path]["changes"] += 1

        hot_files = sorted(file_stats.items(), key=lambda x: x[1]["changes"], reverse=True)[:5]

        return {
            "feature_id": feature_id,
            "commits": len(records),
            "lines_added": total_added,
            "lines_deleted": total_deleted,
            "files_changed": len(file_stats),
            "hot_files": [{"path": p, **stats} for p, stats in hot_files],
        }

    def list_features(self) -> List[str]:
        features = []
        if os.path.exists(self.records_dir):
            for f in os.listdir(self.records_dir):
                if f.endswith(".json") and f != "index.json":
                    features.append(f[:-5])
        return features
