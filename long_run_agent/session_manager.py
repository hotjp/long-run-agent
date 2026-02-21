#!/usr/bin/env python3
"""
会话管理器
管理 LRA 会话的生命周期
"""

import os
import json
import fcntl
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

# 导入项目注册表
try:
    from .registry import ProjectRegistry
except ImportError:
    print("错误: 无法导入 registry 模块")
    ProjectRegistry = None


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.lra_home = os.path.expanduser("~/.lra")
        self.sessions_dir = os.path.join(self.lra_home, "sessions")
        self.active_dir = os.path.join(self.sessions_dir, "active")
        self.completed_dir = os.path.join(self.sessions_dir, "completed")

        # 确保目录存在
        os.makedirs(self.active_dir, exist_ok=True)
        os.makedirs(self.completed_dir, exist_ok=True)

        if ProjectRegistry:
            self.registry = ProjectRegistry()
        else:
            self.registry = None

    def _generate_session_id(self) -> str:
        """生成会话 ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid4())[:8]
        return f"sess_{timestamp}_{short_uuid}"

    def _get_session_path(self, session_id: str, active: bool = True) -> str:
        """获取会话文件路径"""
        if active:
            return os.path.join(self.active_dir, f"{session_id}.json")
        else:
            return os.path.join(self.completed_dir, f"{session_id}.json")

    def _load_session(self, session_id: str, active: bool = True) -> Optional[Dict[str, Any]]:
        """加载会话数据"""
        session_path = self._get_session_path(session_id, active)

        if not os.path.exists(session_path):
            return None

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def _save_session(self, session_data: Dict[str, Any], active: bool = True) -> bool:
        """保存会话数据"""
        session_id = session_data["session_id"]
        session_path = self._get_session_path(session_id, active)

        try:
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ 保存会话失败: {str(e)}")
            return False

    def create_session(self, project_id: str, agent_id: Optional[str] = None) -> Optional[str]:
        """创建新会话"""
        if not self.registry:
            print("❌ 错误: 项目注册表不可用")
            return None

        # 验证项目存在
        project = self.registry.get_project(project_id)
        if not project:
            print(f"❌ 错误: 项目 '{project_id}' 不存在")
            return None

        # 生成会话 ID
        session_id = self._generate_session_id()

        # 创建会话数据
        session_data = {
            "session_id": session_id,
            "project_id": project_id,
            "project_path": project["path"],
            "project_name": project["name"],
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "status": "in_progress",
            "agent_id": agent_id or "unknown",
            "current_feature": None,
            "metadata": {}
        }

        # 保存会话
        if not self._save_session(session_data, active=True):
            return None

        # 更新项目活跃时间
        self.registry.update_last_active(project_id)

        print(f"✓ 会话已创建: {session_id}")
        print(f"  项目: {project['name']} ({project_id})")
        print(f"  Agent: {session_data['agent_id']}")

        return session_id

    def complete_session(self, session_id: str, notes: Optional[str] = None) -> bool:
        """完成会话"""
        # 加载活跃会话
        session_data = self._load_session(session_id, active=True)

        if not session_data:
            # 尝试加载已完成会话
            session_data = self._load_session(session_id, active=False)
            if session_data and session_data["status"] == "completed":
                print(f"⚠️  会话 {session_id} 已经完成")
                return False
            else:
                print(f"❌ 错误: 会话 '{session_id}' 不存在")
                return False

        # 更新状态
        session_data["ended_at"] = datetime.now().isoformat()
        session_data["status"] = "completed"
        if notes:
            session_data["metadata"]["completion_notes"] = notes

        # 保存到已完成目录
        if not self._save_session(session_data, active=False):
            return False

        # 删除活跃会话
        active_path = self._get_session_path(session_id, active=True)
        if os.path.exists(active_path):
            os.remove(active_path)

        print(f"✓ 会话已完成: {session_id}")

        return True

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话数据"""
        session_data = self._load_session(session_id, active=True)

        if not session_data:
            print(f"❌ 错误: 会话 '{session_id}' 不存在")
            return False

        # 更新字段
        for key, value in kwargs.items():
            session_data[key] = value

        # 保存
        if not self._save_session(session_data, active=True):
            return False

        return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        # 先尝试活跃会话
        session_data = self._load_session(session_id, active=True)

        if not session_data:
            # 尝试已完成会话
            session_data = self._load_session(session_id, active=False)

        return session_data

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出活跃会话"""
        sessions = []

        try:
            for filename in os.listdir(self.active_dir):
                if filename.endswith(".json"):
                    session_id = filename[:-5]  # 移除 .json
                    session_data = self._load_session(session_id, active=True)
                    if session_data:
                        sessions.append(session_data)
        except Exception as e:
            print(f"❌ 读取活跃会话失败: {str(e)}")

        return sessions

    def list_completed_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出已完成会话"""
        sessions = []

        try:
            files = os.listdir(self.completed_dir)
            # 按修改时间排序（最新的在前）
            files.sort(key=lambda f: os.path.getmtime(os.path.join(self.completed_dir, f)), reverse=True)

            for filename in files[:limit]:
                if filename.endswith(".json"):
                    session_id = filename[:-5]
                    session_data = self._load_session(session_id, active=False)
                    if session_data:
                        sessions.append(session_data)
        except Exception as e:
            print(f"❌ 读取已完成会话失败: {str(e)}")

        return sessions

    def get_project_active_session(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目的活跃会话"""
        active_sessions = self.list_active_sessions()

        for session in active_sessions:
            if session["project_id"] == project_id:
                return session

        return None

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        active_sessions = self.list_active_sessions()
        completed_sessions = self.list_completed_sessions()

        return {
            "active": len(active_sessions),
            "completed": len(completed_sessions),
            "total": len(active_sessions) + len(completed_sessions)
        }


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="会话管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建新会话")
    create_parser.add_argument("--project-id", required=True, help="项目 ID")
    create_parser.add_argument("--agent-id", help="Agent ID")

    # complete 命令
    complete_parser = subparsers.add_parser("complete", help="完成会话")
    complete_parser.add_argument("--session-id", required=True, help="会话 ID")
    # list 命令
    list_parser = subparsers.add_parser("list", help="列会话")
    list_parser.add_argument("--status", choices=["active", "completed", "all"], default="active", help="会话状态")

    # info 命令
    info_parser = subparsers.add_parser("info", help="查看会话详情")
    info_parser.add_argument("--session-id", help="会话 ID")

    # project-session 命令
    project_parser = subparsers.add_parser("project-session", help="获取项目的活跃会话")
    project_parser.add_argument("--project-id", required=True, help="项目 ID")

    # stats 命令
    subparsers.add_parser("stats", help="显示统计信息")

    args = parser.parse_args()

    manager = SessionManager()

    if args.command == "create":
        manager.create_session(args.project_id, args.agent_id)

    elif args.command == "complete":
        manager.complete_session(args.session_id)

    elif args.command == "list":
        if args.status == "active":
            sessions = manager.list_active_sessions()
            status_text = "活跃"
        elif args.status == "completed":
            sessions = manager.list_completed_sessions()
            status_text = "已完成"
        else:
            sessions = manager.list_active_sessions() + manager.list_completed_sessions()
            status_text = "所有"

        if not sessions:
            print(f"没有{status_text}会话")
        else:
            print(f"\n📋 {status_text}会话 ({len(sessions)} 个):\n")
            for s in sessions:
                status_emoji = "🔄" if s["status"] == "in_progress" else "✅"
                print(f"{status_emoji} {s['session_id']}")
                print(f"   项目: {s['project_name']} ({s['project_id']})")
                print(f"   Agent: {s['agent_id']}")
                print(f"   开始: {s['started_at']}")
                if s['ended_at']:
                    print(f"   结束: {s['ended_at']}")
                if s['current_feature']:
                    print(f"   当前功能: {s['current_feature']}")
                print()

    elif args.command == "info":
        if not args.session_id:
            # 列出第一个活跃会话
            active_sessions = manager.list_active_sessions()
            if active_sessions:
                args.session_id = active_sessions[0]["session_id"]

        if args.session_id:
            session = manager.get_session(args.session_id)
            if session:
                print(f"\n📊 会话详情:\n")
                print(f"  会话 ID: {session['session_id']}")
                print(f"  项目: {session['project_name']} ({session['project_id']})")
                print(f"  Agent: {session['agent_id']}")
                print(f"  开始时间: {session['started_at']}")
                print(f"  结束时间: {session.get('ended_at', 'N/A')}")
                print(f"  状态: {session['status']}")
                print(f"  当前功能: {session.get('current_feature', 'N/A')}")
                if session.get('metadata'):
                    print(f"  元数据: {json.dumps(session['metadata'], indent=4)}")
            else:
                print(f"❌ 会话 '{args.session_id}' 不存在")
        else:
            print("没有找到会话")

    elif args.command == "project-session":
        session = manager.get_project_active_session(args.project_id)
        if session:
            print(f"\n📊 项目活跃会话:\n")
            print(f"  会话 ID: {session['session_id']}")
            print(f"  Agent: {session['agent_id']}")
            print(f"  开始时间: {session['started_at']}")
            print(f"  当前功能: {session.get('current_feature', 'N/A')}")
        else:
            print(f"项目 '{args.project_id}' 没有活跃会话")

    elif args.command == "stats":
        stats = manager.get_stats()
        print(f"\n📊 会话统计:\n")
        print(f"  活跃会话: {stats['active']}")
        print(f"  已完成会话: {stats['completed']}")
        print(f"  总会话数: {stats['total']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
