"""
LRA - AI Agent Task Manager with Quality Assurance v5.2.2
"""

__version__ = "5.2.2"
__author__ = "LRA Contributors"

from lra.config import CURRENT_VERSION, Config, GitHelper, SafeJson
from lra.locks_manager import LocksManager, LockStatus
from lra.records_manager import RecordsManager
from lra.task_manager import TaskManager
from lra.template_manager import TemplateManager

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
