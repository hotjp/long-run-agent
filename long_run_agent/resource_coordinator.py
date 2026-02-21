#!/usr/bin/env python3
"""
资源协调器
处理跨项目资源协调和锁
"""

import os
import fcntl
import json
from datetime import datetime
from typing import Optional, Dict, Any


class ResourceLockError(Exception):
    """资源锁定错误"""
    pass


class ProjectLock:
    """项目锁上下文管理器"""

    def __init__(self, project_id: str, session_id: str, timeout: int = 300):
        self.lra_home = os.path.expanduser("~/.lra")
        self.locks_dir = os.path.join(self.lra_home, "locks")
        self.lock_path = os.path.join(self.locks_dir, f"{project_id}.lock")
        self.project_id = project_id
        self.session_id = session_id
        self.timeout = timeout
        self.lock_file = None
        self.acquired = False

    def acquire(self, blocking: bool = True) -> bool:
        """获取锁"""
        os.makedirs(self.locks_dir, exist_ok=True)

        try:
            self.lock_file = open(self.lock_path, 'w')

            flags = fcntl.LOCK_EX
            if not blocking:
                flags |= fcntl.LOCK_NB

            try:
                fcntl.flock(self.lock_file.fileno(), flags)
            except IOError:
                if not blocking:
                    return False

                # 阻塞模式下，读取锁信息
                raise ResourceLockError(f"项目 {self.project_id} 被其他会话锁定")

            # 写入锁信息
            lock_info = {
                "project_id": self.project_id,
                "session_id": self.session_id,
                "acquired_at": datetime.now().isoformat(),
                "timeout": self.timeout
            }
            json.dump(lock_info, self.lock_file)
            self.lock_file.flush()

            self.acquired = True
            return True

        except Exception as e:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            raise ResourceLockError(f"获取锁失败: {str(e)}")

    def release(self) -> bool:
        """释放锁"""
        if not self.acquired or not self.lock_file:
            return False

        try:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            self.lock_file.close()
            self.lock_file = None

            # 删除锁文件
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)

            self.acquired = False
            return True
        except Exception as e:
            print(f"❌ 释放锁失败: {str(e)}")
            return False

    def is_locked(self) -> bool:
        """检查是否被锁定"""
        if not os.path.exists(self.lock_path):
            return False

        try:
            # 尝试非阻塞获取锁
            test_lock = open(self.lock_path, 'r')
            fcntl.flock(test_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # 如果成功，说明没有锁，立即释放
            fcntl.flock(test_lock.fileno(), fcntl.LOCK_UN)
            test_lock.close()
            return False
        except IOError:
            return True
        except Exception:
            return False

    def get_lock_info(self) -> Optional[Dict[str, Any]]:
        """获取锁信息"""
        if not os.path.exists(self.lock_path):
            return None

        try:
            with open(self.lock_path, 'r') as f:
                return json.load(f)
        except:
            return None

    def __enter__(self):
        """上下文管理器入口"""
        self.acquire(blocking=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()


class ResourceCoordinator:
    """资源协调器"""

    def __init__(self):
        self.lra_home = os.path.expanduser("~/.lra")
        self.locks_dir = os.path.join(self.lra_home, "locks")
        os.makedirs(self.locks_dir, exist_ok=True)

    def acquire_project_lock(self, project_id: str, session_id: str,
                            blocking: bool = True, timeout: int = 300) -> Optional[ProjectLock]:
        """获取项目锁"""
        project_lock = ProjectLock(project_id, session_id, timeout)

        try:
            if project_lock.acquire(blocking=blocking):
                return project_lock
            return None
        except ResourceLockError:
            return None

    def check_project_lock(self, project_id: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """检查项目锁状态"""
        project_lock = ProjectLock(project_id, "dummy")

        if project_lock.is_locked():
            lock_info = project_lock.get_lock_info()
            return True, lock_info
        else:
            return False, None

    def list_locked_projects(self) -> Dict[str, Dict[str, Any]]:
        """列出所有被锁定的项目"""
        locked = {}

        try:
            for filename in os.listdir(self.locks_dir):
                if filename.endswith(".lock"):
                    project_id = filename[:-5]  # 移除 .lock
                    is_locked, lock_info = self.check_project_lock(project_id)

                    if is_locked and lock_info:
                        locked[project_id] = lock_info
        except Exception as e:
            print(f"❌ 读取锁目录失败: {str(e)}")

        return locked

    def force_release_project_lock(self, project_id: str) -> bool:
        """强制释放项目锁（慎用）"""
        lock_path = os.path.join(self.locks_dir, f"{project_id}.lock")

        if not os.path.exists(lock_path):
            print(f"⚠️  项目 {project_id} 没有被锁定")
            return False

        try:
            os.remove(lock_path)
            print(f"✓ 已强制释放项目 {project_id} 的锁")
            return True
        except Exception as e:
            print(f"❌ 强制释放锁失败: {str(e)}")
            return False


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="资源协调器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # check 命令
    check_parser = subparsers.add_parser("check", help="检查项目锁状态")
    check_parser.add_argument("--project-id", required=True, help="项目 ID")

    # list-locked 命令
    subparsers.add_parser("list-locked", help="列出所有被锁定的项目")

    # force-release 命令
    force_parser = subparsers.add_parser("force-release", help="强制释放项目锁（慎用）")
    force_parser.add_argument("--project-id", required=True, help="项目 ID")

    # acquire 命令（测试用）
    acquire_parser = subparsers.add_parser("acquire", help="获取项目锁（测试用）")
    acquire_parser.add_argument("--project-id", required=True, help="项目 ID")
    acquire_parser.add_argument("--session-id", required=True, help="会话 ID")
    acquire_parser.add_argument("--timeout", type=int, default=300, help="超时时间（秒）")

    args = parser.parse_args()

    coordinator = ResourceCoordinator()

    if args.command == "check":
        is_locked, lock_info = coordinator.check_project_lock(args.project_id)

        if is_locked and lock_info:
            print(f"\n🔒 项目 {args.project_id} 被锁定:\n")
            print(f"  会话 ID: {lock_info['session_id']}")
            print(f"  获取时间: {lock_info['acquired_at']}")
            print(f"  超时: {lock_info['timeout']} 秒")
        else:
            print(f"✓ 项目 {args.project_id} 未被锁定")

    elif args.command == "list-locked":
        locked_projects = coordinator.list_locked_projects()

        if not locked_projects:
            print("没有项目被锁定")
        else:
            print(f"\n🔒 被锁定的项目 ({len(locked_projects)} 个):\n")
            for project_id, lock_info in locked_projects.items():
                print(f"  {project_id}")
                print(f"    会话: {lock_info['session_id']}")
                print(f"    获取时间: {lock_info['acquired_at']}")
                print()

    elif args.command == "force-release":
        coordinator.force_release_project_lock(args.project_id)

    elif args.command == "acquire":
        print(f"尝试获取项目 {args.project_id} 的锁...")
        lock = coordinator.acquire_project_lock(
            args.project_id,
args.session_id,
            blocking=False,
            timeout=args.timeout
        )

        if lock:
            print(f"✓ 成功获取锁")
            print(f"  项目: {args.project_id}")
            print(f"  会话: {args.session_id}")

            # 按回车释放
            input("\n按回车释放锁...")
            lock.release()
            print("✓ 锁已释放")
        else:
            print(f"❌ 获取锁失败（项目可能被锁定）")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
