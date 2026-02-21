#!/usr/bin/env python3
"""
自动升级管理器
v2.0 - 支持版本检测、自动升级、数据迁移
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

try:
    from .config import Config, SafeJson, CURRENT_VERSION, SCHEMA_VERSION, FileLock
except ImportError:
    print("警告: 无法导入 config 模块")
    CURRENT_VERSION = "2.0.0"
    SCHEMA_VERSION = "2026-02-21"


class UpgradeManager:
    """自动升级管理器"""

    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)
        self.metadata_dir = os.path.join(self.project_path, Config.METADATA_DIR)
        self.config_path = os.path.join(self.metadata_dir, Config.CONFIG_FILE)
        self.backup_dir = os.path.join(self.metadata_dir, Config.BACKUP_DIR)

    def check_version(self) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        检查版本状态
        返回: (需要升级, 当前版本, 配置数据)
        """
        if not os.path.exists(self.config_path):
            return True, None, None

        config = SafeJson.read(self.config_path)
        if not config:
            return True, None, None

        current_version = config.get("version", "1.0")
        if current_version != CURRENT_VERSION:
            return True, current_version, config

        return False, current_version, config

    def create_backup(self, reason: str = "upgrade") -> Optional[str]:
        """
        创建备份
        返回备份目录路径
        """
        if not os.path.exists(self.metadata_dir):
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{timestamp}_{reason}"
        backup_path = os.path.join(self.backup_dir, backup_name)

        os.makedirs(self.backup_dir, exist_ok=True)

        try:
            files_to_backup = [
                Config.FEATURE_LIST_FILE,
                Config.CONFIG_FILE,
                Config.PROGRESS_FILE,
                Config.OPERATION_LOG_FILE,
            ]
            dirs_to_backup = [
                Config.RECORDS_DIR,
                Config.SPECS_DIR,
            ]

            os.makedirs(backup_path, exist_ok=True)

            for filename in files_to_backup:
                src = os.path.join(self.metadata_dir, filename)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(backup_path, filename))

            for dirname in dirs_to_backup:
                src = os.path.join(self.metadata_dir, dirname)
                if os.path.exists(src):
                    dst = os.path.join(backup_path, dirname)
                    shutil.copytree(src, dst)

            print(f"✓ 备份创建成功: {backup_path}")
            return backup_path

        except Exception as e:
            print(f"❌ 创建备份失败: {str(e)}")
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """从备份恢复"""
        if not os.path.exists(backup_path):
            print(f"❌ 备份不存在: {backup_path}")
            return False

        try:
            files_to_restore = [
                Config.FEATURE_LIST_FILE,
                Config.CONFIG_FILE,
                Config.PROGRESS_FILE,
                Config.OPERATION_LOG_FILE,
            ]
            dirs_to_restore = [
                Config.RECORDS_DIR,
                Config.SPECS_DIR,
            ]

            for filename in files_to_restore:
                src = os.path.join(backup_path, filename)
                if os.path.exists(src):
                    dst = os.path.join(self.metadata_dir, filename)
                    shutil.copy2(src, dst)

            for dirname in dirs_to_restore:
                src = os.path.join(backup_path, dirname)
                if os.path.exists(src):
                    dst = os.path.join(self.metadata_dir, dirname)
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)

            print(f"✓ 备份恢复成功: {backup_path}")
            return True

        except Exception as e:
            print(f"❌ 恢复备份失败: {str(e)}")
            return False

    def migrate_feature_list(self) -> bool:
        """
        迁移 feature_list.json 到新格式
        增加状态相关字段
        """
        feature_list_path = os.path.join(self.metadata_dir, Config.FEATURE_LIST_FILE)
        if not os.path.exists(feature_list_path):
            return True

        feature_list = SafeJson.read(feature_list_path)
        if not feature_list:
            return False

        needs_migration = False
        features = feature_list.get("features", [])

        for feature in features:
            if "status" not in feature:
                if feature.get("passes"):
                    feature["status"] = "completed"
                else:
                    feature["status"] = "pending"
                needs_migration = True

            if "status_updated_at" not in feature:
                if feature.get("completed_at"):
                    feature["status_updated_at"] = feature["completed_at"]
                else:
                    feature["status_updated_at"] = feature.get(
                        "created_at", datetime.now().isoformat()
                    )
                needs_migration = True

            if "progress_percentage" not in feature:
                if feature.get("passes"):
                    feature["progress_percentage"] = 100
                else:
                    feature["progress_percentage"] = 0
                needs_migration = True

            if "assignee" not in feature:
                feature["assignee"] = ""
                needs_migration = True

            if "priority" in feature and not isinstance(feature["priority"], str):
                p = feature["priority"]
                if p == 1:
                    feature["priority"] = "P0"
                elif p == 2:
                    feature["priority"] = "P1"
                else:
                    feature["priority"] = "P2"
                needs_migration = True

        if needs_migration:
            return SafeJson.write(feature_list_path, feature_list)

        return True

    def migrate_config(self) -> bool:
        """
        迁移 config.json 到新格式
        增加版本标识
        """
        if not os.path.exists(self.config_path):
            return self._create_new_config()

        config = SafeJson.read(self.config_path)
        if not config:
            return self._create_new_config()

        old_version = config.get("version", "1.0")

        if "version" not in config or not config["version"].startswith("2."):
            config["version"] = CURRENT_VERSION
            config["schema_version"] = SCHEMA_VERSION
            config["upgraded_at"] = datetime.now().isoformat()

            if "upgrade_history" not in config:
                config["upgrade_history"] = []

            config["upgrade_history"].append(
                {
                    "from_version": old_version,
                    "to_version": CURRENT_VERSION,
                    "upgraded_at": datetime.now().isoformat(),
                    "status": "success",
                }
            )

            return SafeJson.write(self.config_path, config)

        return True

    def _create_new_config(self) -> bool:
        """创建新的配置文件"""
        config = {
            "project_name": os.path.basename(self.project_path),
            "spec": "",
            "created_at": datetime.now().isoformat(),
            "version": CURRENT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "upgraded_at": datetime.now().isoformat(),
            "upgrade_history": [],
        }
        return SafeJson.write(self.config_path, config)

    def create_records_structure(self) -> bool:
        """创建 records 目录结构"""
        records_dir = os.path.join(self.metadata_dir, Config.RECORDS_DIR)
        index_path = os.path.join(records_dir, Config.RECORDS_INDEX_FILE)

        os.makedirs(records_dir, exist_ok=True)

        if not os.path.exists(index_path):
            index_data = {
                "by_feature": {},
                "by_file": {},
                "last_updated": datetime.now().isoformat(),
            }
            return SafeJson.write(index_path, index_data)

        return True

    def create_operation_log(self) -> bool:
        """创建 operation_log.json"""
        op_log_path = os.path.join(self.metadata_dir, Config.OPERATION_LOG_FILE)

        if not os.path.exists(op_log_path):
            op_log_data = {
                "logs": [],
                "index": {"by_operator": {}, "by_action": {}, "by_feature": {}},
            }
            return SafeJson.write(op_log_path, op_log_data)

        return True

    def upgrade(self, auto_confirm: bool = True) -> Tuple[bool, str]:
        """
        执行升级
        返回: (成功, 消息)
        """
        needs_upgrade, current_version, config = self.check_version()

        if not needs_upgrade:
            return True, f"当前版本已是最新: {CURRENT_VERSION}"

        print(
            f"\n🔄 检测到需要升级: {current_version or '旧版本'} -> {CURRENT_VERSION}"
        )

        if not auto_confirm:
            try:
                response = input("是否执行升级? [Y/n] (10秒后自动确认): ")
                if response.lower() == "n":
                    return False, "用户取消升级"
            except:
                pass

        backup_path = self.create_backup("pre_upgrade")
        if not backup_path:
            print("⚠️  警告: 创建备份失败，继续升级...")

        os.makedirs(self.metadata_dir, exist_ok=True)

        try:
            self.migrate_config()
            self.migrate_feature_list()
            self.create_records_structure()
            self.create_operation_log()

            os.makedirs(
                os.path.join(self.metadata_dir, Config.SPECS_DIR), exist_ok=True
            )
            os.makedirs(
                os.path.join(self.metadata_dir, Config.PROJECTS_DIR), exist_ok=True
            )

            is_major_upgrade = current_version and not current_version.startswith("2.")

            if is_major_upgrade:
                print(f"\n✅ LRA 已升级到 v{CURRENT_VERSION}")
                print("   新增功能: 历史项目兼容、Git集成、代码语法检查、状态管理")

            return True, f"升级成功: {current_version or '旧版本'} -> {CURRENT_VERSION}"

        except Exception as e:
            if backup_path:
                print(f"\n❌ 升级失败，正在恢复备份...")
                self.restore_backup(backup_path)
            return False, f"升级失败: {str(e)}"

    def get_upgrade_info(self) -> Dict[str, Any]:
        """获取升级信息"""
        needs_upgrade, current_version, config = self.check_version()

        info = {
            "current_version": current_version or "未知",
            "target_version": CURRENT_VERSION,
            "needs_upgrade": needs_upgrade,
            "schema_version": SCHEMA_VERSION,
        }

        if config:
            info["upgraded_at"] = config.get("upgraded_at")
            info["upgrade_history"] = config.get("upgrade_history", [])

        return info

    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []

        if not os.path.exists(self.backup_dir):
            return backups

        try:
            for name in sorted(os.listdir(self.backup_dir), reverse=True):
                backup_path = os.path.join(self.backup_dir, name)
                if os.path.isdir(backup_path):
                    stat = os.stat(backup_path)
                    backups.append(
                        {
                            "name": name,
                            "path": backup_path,
                            "created_at": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "size": sum(
                                os.path.getsize(os.path.join(backup_path, f))
                                for f in os.listdir(backup_path)
                                if os.path.isfile(os.path.join(backup_path, f))
                            ),
                        }
                    )
        except Exception as e:
            print(f"❌ 读取备份列表失败: {str(e)}")

        return backups


def check_and_upgrade(project_path: str = ".") -> Tuple[bool, str]:
    """
    检查并执行自动升级（工具启动时调用）
    返回: (成功, 消息)
    """
    manager = UpgradeManager(project_path)
    needs_upgrade, current_version, _ = manager.check_version()

    if not needs_upgrade:
        return True, "版本已是最新"

    return manager.upgrade(auto_confirm=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LRA 升级管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("check", help="检查版本状态")
    subparsers.add_parser("upgrade", help="执行升级")
    subparsers.add_parser("info", help="显示升级信息")

    rollback_parser = subparsers.add_parser("rollback", help="回滚到指定备份")
    rollback_parser.add_argument("--backup", required=True, help="备份名称")

    subparsers.add_parser("list-backups", help="列出所有备份")

    args = parser.parse_args()

    manager = UpgradeManager()

    if args.command == "check":
        needs_upgrade, current_version, _ = manager.check_version()
        if needs_upgrade:
            print(f"需要升级: {current_version or '旧版本'} -> {CURRENT_VERSION}")
        else:
            print(f"当前版本已是最新: {current_version}")

    elif args.command == "upgrade":
        success, message = manager.upgrade(auto_confirm=False)
        print(f"{'✅' if success else '❌'} {message}")

    elif args.command == "info":
        info = manager.get_upgrade_info()
        print(f"\n📊 LRA 版本信息:\n")
        print(f"  当前版本: {info['current_version']}")
        print(f"  目标版本: {info['target_version']}")
        print(f"  Schema版本: {info['schema_version']}")
        print(f"  需要升级: {'是' if info['needs_upgrade'] else '否'}")
        if info.get("upgraded_at"):
            print(f"  上次升级: {info['upgraded_at']}")
        if info.get("upgrade_history"):
            print(f"\n  升级历史:")
            for h in info["upgrade_history"]:
                print(
                    f"    - {h['from_version']} -> {h['to_version']} ({h['upgraded_at']})"
                )

    elif args.command == "rollback":
        backup_path = os.path.join(manager.backup_dir, args.backup)
        if manager.restore_backup(backup_path):
            print("✅ 回滚成功")
        else:
            print("❌ 回滚失败")

    elif args.command == "list-backups":
        backups = manager.list_backups()
        if not backups:
            print("没有备份")
        else:
            print(f"\n📦 备份列表 ({len(backups)} 个):\n")
            for b in backups:
                print(f"  {b['name']}")
                print(f"    创建时间: {b['created_at']}")
                print(f"    大小: {b['size']} bytes")
                print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
