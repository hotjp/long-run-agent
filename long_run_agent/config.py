#!/usr/bin/env python3
"""
共享配置模块
提供统一的配置和工具函数
v2.0 - 支持版本管理和自动升级
"""

import os
import json
import fcntl
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


CURRENT_VERSION = "2.0.6"
SCHEMA_VERSION = "2026-02-21"


class Config:
    """配置类"""

    METADATA_DIR = ".long-run-agent"
    FEATURE_LIST_FILE = "feature_list.json"
    PROGRESS_FILE = "progress.log"
    CONFIG_FILE = "config.json"
    SESSION_STATE_FILE = "session_state.json"
    LOCK_FILE = ".lra_lock"
    OPERATION_LOG_FILE = "operation_log.json"
    RECORDS_DIR = "records"
    RECORDS_INDEX_FILE = "index.json"
    SPECS_DIR = "specs"
    BACKUP_DIR = "backup"
    PROJECTS_DIR = "projects"

    @classmethod
    def get_metadata_dir(cls) -> str:
        return os.path.abspath(cls.METADATA_DIR)

    @classmethod
    def get_feature_list_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.FEATURE_LIST_FILE)

    @classmethod
    def get_progress_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.PROGRESS_FILE)

    @classmethod
    def get_config_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.CONFIG_FILE)

    @classmethod
    def get_session_state_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.SESSION_STATE_FILE)

    @classmethod
    def get_lock_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.LOCK_FILE)

    @classmethod
    def get_operation_log_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.OPERATION_LOG_FILE)

    @classmethod
    def get_records_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.RECORDS_DIR)

    @classmethod
    def get_records_index_path(cls) -> str:
        return os.path.join(cls.get_records_dir(), cls.RECORDS_INDEX_FILE)

    @classmethod
    def get_specs_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.SPECS_DIR)

    @classmethod
    def get_backup_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.BACKUP_DIR)

    @classmethod
    def get_projects_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.PROJECTS_DIR)

    @classmethod
    def get_spec_path(cls, feature_id: str) -> str:
        return os.path.join(cls.get_specs_dir(), f"{feature_id}.md")

    @classmethod
    def get_record_path(cls, feature_id: str) -> str:
        return os.path.join(cls.get_records_dir(), f"{feature_id}.json")

    @classmethod
    def ensure_dirs(cls) -> None:
        dirs = [
            cls.get_metadata_dir(),
            cls.get_records_dir(),
            cls.get_specs_dir(),
            cls.get_backup_dir(),
            cls.get_projects_dir(),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)


class FileLock:
    """文件锁，用于并发控制"""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self.lock_file = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        self.lock_file = open(self.lock_path, "w")
        try:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)
            return self
        except Exception as e:
            self.lock_file.close()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_file:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            self.lock_file.close()
            try:
                os.unlink(self.lock_path)
            except:
                pass


class SafeJson:
    """安全的 JSON 操作"""

    @staticmethod
    def read(path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析错误: {path}")
            print(f"   错误: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 读取文件错误: {path}")
            print(f"   错误: {str(e)}")
            return None

    @staticmethod
    def write(path: str, data: Dict[str, Any]) -> bool:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ 写入文件错误: {path}")
            print(f"   错误: {str(e)}")
            return False

    @staticmethod
    def read_with_lock(path: str, lock_path: str) -> Optional[Dict[str, Any]]:
        with FileLock(lock_path):
            return SafeJson.read(path)

    @staticmethod
    def write_with_lock(path: str, data: Dict[str, Any], lock_path: str) -> bool:
        with FileLock(lock_path):
            return SafeJson.write(path, data)


class GitHelper:
    """Git 操作助手"""

    @staticmethod
    def is_initialized() -> bool:
        return os.path.exists(".git")

    @staticmethod
    def is_configured() -> bool:
        try:
            import subprocess

            result = subprocess.run(
                ["git", "config", "user.email"], capture_output=True, text=True
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except:
            return False

    @staticmethod
    def commit(message: str) -> tuple:
        if not GitHelper.is_initialized():
            return False, "Git 仓库未初始化"

        if not GitHelper.is_configured():
            return (
                False,
                "Git 未配置用户信息 (运行 git config user.email 和 git config user.name)",
            )

        try:
            import subprocess

            result = subprocess.run(
                ["git", "commit", "-am", message], capture_output=True, text=True
            )

            if result.returncode == 0:
                return True, "提交成功"
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_current_commit() -> Dict[str, str]:
        result = {"hash": "", "branch": "", "message": "", "author": ""}
        try:
            import subprocess

            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True
            )
            if hash_result.returncode == 0:
                result["hash"] = hash_result.stdout.strip()[:7]

            branch_result = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True
            )
            if branch_result.returncode == 0:
                result["branch"] = branch_result.stdout.strip()

            msg_result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True
            )
            if msg_result.returncode == 0:
                result["message"] = msg_result.stdout.strip()

            author_result = subprocess.run(
                ["git", "log", "-1", "--pretty=%an"], capture_output=True, text=True
            )
            if author_result.returncode == 0:
                result["author"] = author_result.stdout.strip()
        except:
            pass
        return result

    @staticmethod
    def get_current_branch() -> str:
        try:
            import subprocess

            result = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return ""

    @staticmethod
    def validate_branch_name(feature_id: str) -> Dict[str, Any]:
        expected_pattern = f"feature/{feature_id}"
        current_branch = GitHelper.get_current_branch()

        if not current_branch:
            return {"valid": True, "warning": "无法获取当前分支名"}

        if not current_branch.startswith(expected_pattern):
            return {
                "valid": False,
                "warning": f"当前分支 '{current_branch}' 与 Feature '{feature_id}' 不匹配",
                "suggestion": f"建议创建分支: {expected_pattern}",
            }
        return {"valid": True}

    @staticmethod
    def get_changed_files() -> List[Dict[str, Any]]:
        files = []
        try:
            import subprocess

            result = subprocess.run(
                ["git", "diff", "--numstat", "HEAD~1", "HEAD"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            files.append(
                                {
                                    "path": parts[2],
                                    "lines_added": int(parts[0])
                                    if parts[0] != "-"
                                    else 0,
                                    "lines_deleted": int(parts[1])
                                    if parts[1] != "-"
                                    else 0,
                                }
                            )
        except:
            pass
        return files


def validate_feature_id(feature_id: str) -> bool:
    if not feature_id:
        return False
    if not feature_id.startswith("feature_"):
        return False
    try:
        num = int(feature_id.split("_")[1])
        return num > 0
    except:
        return False


def validate_project_initialized() -> tuple:
    feature_list_path = Config.get_feature_list_path()
    config_path = Config.get_config_path()

    if not os.path.exists(feature_list_path):
        return False, f"未找到功能清单: {feature_list_path}"

    if not os.path.exists(config_path):
        return False, f"未找到配置文件: {config_path}"

    return True, "项目已初始化"


def get_version_info() -> Dict[str, str]:
    return {"version": CURRENT_VERSION, "schema_version": SCHEMA_VERSION}
