#!/usr/bin/env python3
"""
项目注册表
管理所有 LRA 项目的注册和发现
"""

import os
import json
import fcntl
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any


class ProjectRegistry:
    """项目注册表"""

    def __init__(self):
        self.lra_home = os.path.expanduser("~/.lra")
        self.registry_path = os.path.join(self.lra_home, "registry.json")

        # 确保目录存在
        os.makedirs(self.lra_home, exist_ok=True)

    def _generate_project_id(self, path: str) -> str:
        """生成项目 ID（基于路径的哈希）"""
        abs_path = os.path.abspath(path)
        hash_obj = hashlib.md5(abs_path.encode())
        hash_str = hash_obj.hexdigest()[:8]
        name = os.path.basename(abs_path.rstrip("/"))
        return f"{name}_{hash_str}"

    def _load(self) -> Dict[str, Any]:
        """加载注册表"""
        if not os.path.exists(self.registry_path):
            return {"projects": {}, "version": "1.0"}

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # 如果文件损坏，返回空注册表
            return {"projects": {}, "version": "1.0"}

    def _save(self, data: Dict[str, Any]) -> bool:
        """保存注册表"""
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ 保存注册表失败: {str(e)}")
            return False

    def _lock(self):
        """获取文件锁"""
        lock_path = os.path.join(self.lra_home, "registry.lock")
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        return lock_file

    def register(self, project_path: str, name: Optional[str] = None) -> Optional[str]:
        """注册项目"""
        project_path = os.path.abspath(project_path)
        project_id = self._generate_project_id(project_path)

        # 验证项目存在
        LRA_METADATA_DIR = ".long-run-agent"
        if not os.path.exists(os.path.join(project_path, LRA_METADATA_DIR)):
            print(f"❌ 错误: 项目路径 '{project_path}' 不是有效的 LRA 项目")
            print(f"   请确保项目已初始化 (存在 {LRA_METADATA_DIR} 目录)")
            return None

        # 如果没有提供名称，使用目录名
        if not name:
            name = os.path.basename(project_path.rstrip("/"))

        # 获取项目配置
        config_path = os.path.join(project_path, LRA_METADATA_DIR, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    spec = config.get("spec", "")
            except:
                spec = ""
        else:
            spec = ""

        project_data = {
            "project_id": project_id,
            "path": project_path,
            "name": name,
            "spec": spec,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "status": "active"
        }

        # 获取锁并保存
        lock_file = self._lock()
        try:
            registry = self._load()
            registry["projects"][project_id] = project_data
            self._save(registry)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

        print(f"✓ 项目已注册: {name} ({project_id})")
        print(f"  路径: {project_path}")
        return project_id

    def unregister(self, project_id: str) -> bool:
        """注销项目"""
        lock_file = self._lock()
        try:
            registry = self._load()

            if project_id not in registry["projects"]:
                print(f"❌ 错误: 项目 '{project_id}' 不存在")
                return False

            project = registry["projects"][project_id]
            del registry["projects"][project_id]
            self._save(registry)

            print(f"✓ 项目已注销: {project['name']} ({project_id})")
            return True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    def list_projects(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有项目"""
        registry = self._load()
        projects = list(registry["projects"].values())

        if status:
            projects = [p for p in projects if p["status"] == status]

        return projects

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目信息"""
        registry = self._load()
        return registry["projects"].get(project_id)

    def find_project_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """通过路径查找项目"""
        abs_path = os.path.abspath(path)
        project_id = self._generate_project_id(abs_path)
        return self.get_project(project_id)

    def update_last_active(self, project_id: str) -> bool:
        """更新项目最后活跃时间"""
        lock_file = self._lock()
        try:
            registry = self._load()

            if project_id not in registry["projects"]:
                return False

            registry["projects"][project_id]["last_active"] = datetime.now().isoformat()
            self._save(registry)
            return True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        projects = self.list_projects()
        return {
            "total": len(projects),
            "active": len([p for p in projects if p["status"] == "active"]),
            "inactive": len([p for p in projects if p["status"] == "inactive"])
        }


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="项目注册表管理")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # register 命令
    register_parser = subparsers.add_parser("register", help="注册项目")
    register_parser.add_argument("--path", required=True, help="项目路径")
    register_parser.add_argument("--name", help="项目名称")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有项目")
    list_parser.add_argument("--status", help="筛选状态 (active|inactive)")

    # info 命令
    info_parser = subparsers.add_parser("info", help="查看项目详情")
    info_parser.add_argument("--project-id", help="项目 ID")

    # unregister 命令
    unregister_parser = subparsers.add_parser("unregister", help="注销项目")
    unregister_parser.add_argument("--project-id", required=True, help="项目 ID")

    # stats 命令
    subparsers.add_parser("stats", help="显示统计信息")

    args = parser.parse_args()

    registry = ProjectRegistry()

    if args.command == "register":
        registry.register(args.path, args.name)

    elif args.command == "list":
        projects = registry.list_projects(args.status)

        if not projects:
            print("没有找到项目")
        else:
            print(f"\n📋 已注册项目 ({len(projects)} 个):\n")
            for p in projects:
                status_emoji = "✅" if p["status"] == "active" else "⏸️"
                print(f"{status_emoji} {p['name']} ({p['project_id']})")
                print(f"   路径: {p['path']}")
                print(f"   创建: {p['created_at']}")
                print(f"   最后活跃: {p['last_active']}")
                print()

    elif args.command == "info":
        if not args.project_id:
            # 列出所有项目
            projects = registry.list_projects()
            if projects:
                args.project_id = projects[0]["project_id"]

        if args.project_id:
            project = registry.get_project(args.project_id)
            if project:
                print(f"\n📊 项目详情:\n")
                print(f"  ID: {project['project_id']}")
                print(f"  名称: {project['name']}")
                print(f"  路径: {project['path']}")
                print(f"  描述: {project.get('spec', 'N/A')}")
                print(f"  创建时间: {project['created_at']}")
                print(f"  最后活跃: {project['last_active']}")
                print(f"  状态: {project['status']}")
            else:
                print(f"❌ 项目 '{args.project_id}' 不存在")
        else:
            print("没有找到项目")

    elif args.command == "unregister":
        registry.unregister(args.project_id)

    elif args.command == "stats":
        stats = registry.get_stats()
        print(f"\n📊 注册表统计:\n")
        print(f"  总项目数: {stats['total']}")
        print(f"  活跃项目: {stats['active']}")
        print(f"  非活跃项目: {stats['inactive']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
