"""
Long-Running Agent - A powerful framework for managing long-running AI Agent tasks
"""

__version__ = "2.0.2"
__author__ = "Long-Running Agent Contributors"

from .config import Config, SafeJson
from .status_manager import StatusManager, FeatureStatus, VALID_TRANSITIONS
from .spec_manager import SpecManager
from .records_manager import RecordsManager
from .operation_logger import OperationLogger
from .upgrade_manager import UpgradeManager
from .code_checker import CodeChecker

# Functional exports
from .feature_manager import init_project, add_feature, list_features, get_next_feature, update_feature_status, get_feature_stats

__all__ = [
    "__version__",
    # Classes
    "Config",
    "SafeJson",
    "StatusManager",
    "FeatureStatus",
    "VALID_TRANSITIONS",
    "SpecManager",
    "RecordsManager",
    "OperationLogger",
    "UpgradeManager",
    "CodeChecker",
    # Functions
    "init_project",
    "add_feature",
    "list_features",
    "get_next_feature",
    "update_feature_status",
    "get_feature_stats",
]
