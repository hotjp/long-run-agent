#!/usr/bin/env python3
"""
LRA v5.0 配置模块
通用任务管理框架
"""

import os
import json
import subprocess
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from filelock import FileLock as _FileLock

CURRENT_VERSION = "5.1.1"
LRA_VERSION = "5.1.1"
SCHEMA_VERSION = "2026-02-25"


def current_time_ms() -> int:
    """获取当前 Unix 时间戳（毫秒）"""
    return int(time.time() * 1000)


def ms_to_iso(ms: int) -> str:
    """毫秒时间戳转 ISO 格式"""
    return datetime.fromtimestamp(ms / 1000).isoformat()


def iso_to_ms(iso_str: str) -> int:
    """ISO 格式转毫秒时间戳"""
    return int(datetime.fromisoformat(iso_str).timestamp() * 1000)


HEARTBEAT_INTERVAL_MINUTES = 5
ORPHAN_THRESHOLD_MINUTES = 15

# 优先级权重
PRIORITY_WEIGHTS = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


_agent_id_cache = None


def get_agent_id() -> str:
    """
    获取 Agent ID

    优先级:
    1. 环境变量 LRA_AGENT_ID
    2. 进程全局缓存
    3. 生成新的 UUID 并缓存到进程和环境变量
    """
    global _agent_id_cache

    import uuid

    env_id = os.environ.get("LRA_AGENT_ID")
    if env_id:
        return env_id

    if _agent_id_cache:
        return _agent_id_cache

    _agent_id_cache = f"agent_{uuid.uuid4().hex[:8]}"
    os.environ["LRA_AGENT_ID"] = _agent_id_cache

    return _agent_id_cache


class Config:
    METADATA_DIR = ".long-run-agent"
    TASK_LIST_FILE = "task_list.json"
    CONFIG_FILE = "config.json"
    LOCKS_FILE = "locks.json"
    TEMPLATES_DIR = "templates"
    TASKS_DIR = "tasks"
    RECORDS_DIR = "records"
    RECORDS_INDEX_FILE = "index.json"
    BACKUP_DIR = "backup"
    LRA_VERSION_FILE = ".lra_version"

    @classmethod
    def get_metadata_dir(cls) -> str:
        return os.path.abspath(cls.METADATA_DIR)

    @classmethod
    def get_config_dir(cls) -> str:
        """获取配置目录路径（与metadata_dir相同）"""
        return cls.get_metadata_dir()

    @classmethod
    def get_task_list_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.TASK_LIST_FILE)

    @classmethod
    def get_config_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.CONFIG_FILE)

    @classmethod
    def get_locks_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.LOCKS_FILE)

    @classmethod
    def get_templates_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.TEMPLATES_DIR)

    @classmethod
    def get_template_path(cls, name: str) -> str:
        return os.path.join(cls.get_templates_dir(), f"{name}.yaml")

    @classmethod
    def get_tasks_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.TASKS_DIR)

    @classmethod
    def get_task_path(cls, task_id: str) -> str:
        return os.path.join(cls.get_tasks_dir(), f"{task_id}.md")

    @classmethod
    def get_records_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.RECORDS_DIR)

    @classmethod
    def get_records_index_path(cls) -> str:
        return os.path.join(cls.get_records_dir(), cls.RECORDS_INDEX_FILE)

    @classmethod
    def get_backup_dir(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.BACKUP_DIR)

    @classmethod
    def get_lra_version_path(cls) -> str:
        return os.path.join(cls.get_metadata_dir(), cls.LRA_VERSION_FILE)

    @classmethod
    def ensure_dirs(cls) -> None:
        dirs = [
            cls.get_metadata_dir(),
            cls.get_tasks_dir(),
            cls.get_templates_dir(),
            cls.get_records_dir(),
            cls.get_backup_dir(),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

        cls._copy_default_templates()

    @classmethod
    def _copy_default_templates(cls) -> None:
        """从全局模板目录复制默认模板到项目目录"""
        import shutil

        project_templates = cls.get_templates_dir()

        # 获取全局模板目录（lra包所在目录的上级/.long-run-agent/templates）
        lra_dir = os.path.dirname(os.path.abspath(__file__))
        global_templates = os.path.join(lra_dir, "..", ".long-run-agent", "templates")
        global_templates = os.path.normpath(global_templates)

        if not os.path.exists(global_templates):
            return

        # 复制全局模板到项目目录
        for f in os.listdir(global_templates):
            if f.endswith(".yaml"):
                src = os.path.join(global_templates, f)
                dst = os.path.join(project_templates, f)
                # 只复制不存在的或全局模板更新的文件
                if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                    shutil.copy2(src, dst)


class FileLock:
    def __init__(self, lock_path: str):
        self._lock_path = lock_path + ".lock"
        self._filelock = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self._lock_path) or ".", exist_ok=True)
        self._filelock = _FileLock(self._lock_path)
        self._filelock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._filelock:
            self._filelock.release()
            try:
                os.unlink(self._lock_path)
            except:
                pass


class SafeJson:
    @staticmethod
    def read(path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
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
        except:
            return False


class GitHelper:
    @staticmethod
    def is_repo() -> bool:
        return os.path.exists(".git")

    @staticmethod
    def get_current_commit() -> Dict[str, str]:
        result = {"hash": "", "branch": "", "message": "", "author": ""}
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
            if r.returncode == 0:
                result["hash"] = r.stdout.strip()[:7]
            r = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
            if r.returncode == 0:
                result["branch"] = r.stdout.strip()
            r = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True)
            if r.returncode == 0:
                result["message"] = r.stdout.strip()[:100]
            r = subprocess.run(["git", "log", "-1", "--pretty=%an"], capture_output=True, text=True)
            if r.returncode == 0:
                result["author"] = r.stdout.strip()
        except:
            pass
        return result

    @staticmethod
    def get_diff_files() -> List[Dict[str, Any]]:
        files = []
        try:
            r = subprocess.run(
                ["git", "diff", "--numstat", "HEAD~1", "HEAD"], capture_output=True, text=True
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n"):
                    if line:
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            files.append(
                                {
                                    "path": parts[2],
                                    "added": int(parts[0]) if parts[0] != "-" else 0,
                                    "deleted": int(parts[1]) if parts[1] != "-" else 0,
                                }
                            )
        except:
            pass
        return files

    @staticmethod
    def get_staged_files() -> List[Dict[str, Any]]:
        files = []
        try:
            r = subprocess.run(
                ["git", "diff", "--numstat", "--cached"], capture_output=True, text=True
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n"):
                    if line:
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            files.append(
                                {
                                    "path": parts[2],
                                    "added": int(parts[0]) if parts[0] != "-" else 0,
                                    "deleted": int(parts[1]) if parts[1] != "-" else 0,
                                }
                            )
        except:
            pass
        return files


def validate_project_initialized() -> Tuple[bool, str]:
    if not os.path.exists(Config.get_task_list_path()):
        return False, "not_initialized"
    return True, "ok"


def is_initialized() -> bool:
    """Check if project is initialized (simpler version of validate_project_initialized)."""
    return os.path.exists(Config.get_task_list_path())


def check_existing_data(path: str) -> int:
    """Returns task count if initialized, 0 otherwise."""
    from lra.task_manager import TaskManager

    tm = TaskManager()
    data = tm._load()
    if not data:
        return 0
    tasks = data.get("tasks", [])
    return len(tasks)
