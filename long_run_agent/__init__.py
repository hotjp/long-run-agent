"""
LRA - AI Agent Task Manager v3.4.0
"""

__version__ = "3.4.0"
__author__ = "LRA Contributors"

from .config import Config, SafeJson, GitHelper, CURRENT_VERSION
from .task_manager import TaskManager
from .template_manager import TemplateManager
from .records_manager import RecordsManager
from .locks_manager import LocksManager, LockStatus

__all__ = [
    "__version__",
    "CURRENT_VERSION",
    "Config",
    "SafeJson",
    "GitHelper",
    "TaskManager",
    "TemplateManager",
    "RecordsManager",
    "LocksManager",
    "LockStatus",
]
