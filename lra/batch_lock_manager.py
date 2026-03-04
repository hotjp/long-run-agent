#!/usr/bin/env python3
"""
批量操作分布式锁管理器
v3.3 - 50ms 延迟保证 + 多 Agent 并发控制
"""

import os
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from lra.config import SafeJson, FileLock

BATCH_LOCK_TIMEOUT_MS = 30000  # 30 秒超时
LOCK_HEARTBEAT_INTERVAL_MS = 10000  # 10 秒心跳
MAX_WAIT_MS = 60000  # 最多等待 60 秒
MAX_BATCH_SIZE = 5  # 推荐最大批量任务数


class BatchLockManager:
    def __init__(self):
        self.lock_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".long-run-agent", "batch_lock.json"
        )
        self.log_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".long-run-agent",
            "logs",
            "batch_operations.jsonl",
        )
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _current_time_ms(self) -> int:
        """获取当前 Unix 时间戳（毫秒）"""
        return int(time.time() * 1000)

    def _load_lock(self) -> Optional[Dict[str, Any]]:
        """加载锁文件"""
        return SafeJson.read(self.lock_path)

    def _save_lock(self, data: Dict[str, Any]) -> bool:
        """保存锁文件（使用文件锁保证原子性）"""
        with FileLock(self.lock_path + ".lock"):
            return SafeJson.write(self.lock_path, data)

    def _delete_lock(self):
        """删除锁文件"""
        with FileLock(self.lock_path + ".lock"):
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)

    def _save_agent_id(self, agent_id: str):
        """保存 agent_id 到文件，用于跨进程保持一致性"""
        agent_file = os.path.join(os.path.dirname(self.lock_path), ".batch_lock_agent")
        try:
            with open(agent_file, "w") as f:
                f.write(agent_id)
        except:
            pass  # 忽略写入失败

    def _get_last_agent_id(self) -> Optional[str]:
        """从文件读取最后的 agent_id"""
        agent_file = os.path.join(os.path.dirname(self.lock_path), ".batch_lock_agent")
        try:
            if os.path.exists(agent_file):
                with open(agent_file, "r") as f:
                    return f.read().strip()
        except:
            pass
        return None

    def acquire(
        self,
        agent_id: str,
        operation: str,
        task_ids: List[str],
        timeout_ms: int = BATCH_LOCK_TIMEOUT_MS,
        wait: bool = False,
        max_wait_ms: int = MAX_WAIT_MS,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        获取批量操作锁

        Args:
            agent_id: Agent 唯一标识
            operation: 操作类型 (batch_claim|batch_set|batch_delete)
            task_ids: 任务 ID 列表
            timeout_ms: 锁超时时间（毫秒）
            wait: 是否等待锁释放
            max_wait_ms: 最大等待时间

        Returns:
            (success, reason, lock_info)
        """
        start_ms = self._current_time_ms()

        while True:
            result = self._try_acquire(agent_id, operation, task_ids, timeout_ms)
            success, reason, lock_info = result

            if success:
                self._log_operation("acquire", agent_id, operation, task_ids, True)
                return result

            if not wait:
                return result

            # 检查等待超时
            elapsed = self._current_time_ms() - start_ms
            if elapsed >= max_wait_ms:
                return (False, "wait_timeout", None)

            # 等待 100ms 后重试
            time.sleep(0.1)

    def _try_acquire(
        self, agent_id: str, operation: str, task_ids: List[str], timeout_ms: int
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """尝试获取锁（不等待）"""
        current_ms = self._current_time_ms()
        lock = self._load_lock()

        if lock is None:
            # 无锁，创建新锁
            new_lock = {
                "lock_holder": agent_id,
                "acquired_at_ms": current_ms,
                "expires_at_ms": current_ms + timeout_ms,
                "operation_type": operation,
                "task_ids": task_ids,
                "status": "acquired",
                "last_heartbeat_ms": current_ms,
            }
            self._save_lock(new_lock)
            self._save_agent_id(agent_id)
            return (True, "lock_acquired", new_lock)

        # 检查锁是否过期
        if lock["expires_at_ms"] < current_ms:
            # 锁过期，回收
            self._log_operation(
                "recover_expired",
                lock["lock_holder"],
                lock["operation_type"],
                lock["task_ids"],
                False,
            )

            new_lock = {
                "lock_holder": agent_id,
                "acquired_at_ms": current_ms,
                "expires_at_ms": current_ms + timeout_ms,
                "operation_type": operation,
                "task_ids": task_ids,
                "status": "acquired",
                "last_heartbeat_ms": current_ms,
                "recovered_from": lock["lock_holder"],
            }
            self._save_lock(new_lock)
            self._save_agent_id(agent_id)
            return (True, "lock_recovered", new_lock)

        # 检查是否是自己持有
        if lock["lock_holder"] == agent_id:
            # 续期
            lock["expires_at_ms"] = current_ms + timeout_ms
            lock["last_heartbeat_ms"] = current_ms
            lock["status"] = "extended"
            self._save_lock(lock)
            return (True, "lock_extended", lock)

        # 其他 Agent 持有
        remaining_ms = lock["expires_at_ms"] - current_ms
        return (
            False,
            "lock_held_by_other",
            {
                "holder": lock["lock_holder"],
                "remaining_ms": max(0, remaining_ms),
                "operation_type": lock["operation_type"],
                "task_count": len(lock["task_ids"]),
            },
        )

    def release(self, agent_id: str) -> Tuple[bool, str]:
        """释放锁"""
        lock = self._load_lock()

        if lock is None:
            return (False, "lock_not_exists")

        if lock["lock_holder"] != agent_id:
            return (False, "not_lock_holder")

        # 记录日志
        self._log_operation("release", agent_id, lock["operation_type"], lock["task_ids"], True)

        # 删除锁
        self._delete_lock()
        return (True, "lock_released")

    def heartbeat(self, agent_id: str, extend_ms: int = BATCH_LOCK_TIMEOUT_MS) -> Tuple[bool, str]:
        """心跳续期"""
        lock = self._load_lock()

        if lock is None:
            return (False, "lock_not_exists")

        if lock["lock_holder"] != agent_id:
            return (False, "not_lock_holder")

        current_ms = self._current_time_ms()
        lock["expires_at_ms"] = current_ms + extend_ms
        lock["last_heartbeat_ms"] = current_ms
        self._save_lock(lock)

        return (True, "heartbeat_ok")

    def status(self) -> Dict[str, Any]:
        """查看锁状态"""
        lock = self._load_lock()

        if lock is None:
            return {"locked": False}

        current_ms = self._current_time_ms()
        is_expired = lock["expires_at_ms"] < current_ms

        return {
            "locked": True,
            "holder": lock["lock_holder"],
            "operation_type": lock["operation_type"],
            "task_count": len(lock["task_ids"]),
            "acquired_at_ms": lock["acquired_at_ms"],
            "expires_at_ms": lock["expires_at_ms"],
            "remaining_ms": max(0, lock["expires_at_ms"] - current_ms),
            "is_expired": is_expired,
            "status": lock.get("status", "unknown"),
        }

    def recover(self, agent_id: str) -> Tuple[bool, str]:
        """强制回收获期锁"""
        lock = self._load_lock()

        if lock is None:
            return (False, "lock_not_exists")

        current_ms = self._current_time_ms()
        if lock["expires_at_ms"] >= current_ms:
            return (False, "lock_not_expired")

        # 回收
        self._log_operation(
            "force_recover", lock["lock_holder"], lock["operation_type"], lock["task_ids"], False
        )

        self._delete_lock()
        return (True, "lock_recovered")

    def _log_operation(
        self, action: str, agent_id: str, operation: str, task_ids: List[str], success: bool
    ):
        """记录操作日志"""
        log_entry = {
            "timestamp_ms": self._current_time_ms(),
            "action": action,
            "agent_id": agent_id,
            "operation": operation,
            "task_ids": task_ids,
            "success": success,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取操作日志"""
        if not os.path.exists(self.log_path):
            return []

        logs = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        return logs[-limit:]

    def check_batch_size(self, task_ids: List[str]) -> Tuple[bool, Optional[str]]:
        """检查批量大小，返回 (是否允许，警告信息)"""
        if len(task_ids) <= MAX_BATCH_SIZE:
            return (True, None)

        warning = f"批量操作 {len(task_ids)} 个任务，建议 ≤{MAX_BATCH_SIZE} 个以保证性能"
        return (True, warning)  # 警告但允许
