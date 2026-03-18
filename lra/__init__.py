"""
LRA - AI Agent Task Manager with Quality Assurance v5.0.0
"""

__version__ = "5.0.0"
__author__ = "LRA Contributors"

from lra.config import Config, SafeJson, GitHelper, CURRENT_VERSION
from lra.task_manager import TaskManager
from lra.template_manager import TemplateManager
from lra.records_manager import RecordsManager
from lra.locks_manager import LocksManager, LockStatus

__all__ = [
    "__version__",
    "Config",
    "SafeJson",
    "GitHelper",
    "CURRENT_VERSION",
    "TaskManager",
    "TemplateManager",
    "RecordsManager",
    "LocksManager",
    "LockStatus",
]
