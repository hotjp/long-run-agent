#!/usr/bin/env python3
"""
读写锁实现
支持多读单写，优化并发性能
"""

import os
import fcntl
from typing import Optional


class RWLock:
    """
    读写锁（Read-Write Lock）

    - 读锁：允许多个并发读
    - 写锁：独占写，阻塞所有读写
    """

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self.lock_file: Optional[int] = None
        self.mode: Optional[str] = None  # 'r' or 'w'

    def _ensure_lock_file(self):
        """确保锁文件存在"""
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
        if not os.path.exists(self.lock_path):
            with open(self.lock_path, "w") as f:
                pass

    def acquire_read(self):
        """获取读锁（共享锁）"""
        self._ensure_lock_file()
        self.lock_file = open(self.lock_path, "r")
        try:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_SH)
            self.mode = "r"
            return self
        except Exception as e:
            self.lock_file.close()
            self.lock_file = None
            raise e

    def acquire_write(self):
        """获取写锁（独占锁）"""
        self._ensure_lock_file()
        self.lock_file = open(self.lock_path, "w")
        try:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)
            self.mode = "w"
            return self
        except Exception as e:
            self.lock_file.close()
            self.lock_file = None
            raise e

    def release(self):
        """释放锁"""
        if self.lock_file:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            self.lock_file.close()
            self.lock_file = None
            self.mode = None

        # 清理锁文件（可选）
        try:
            if os.path.exists(self.lock_path):
                os.unlink(self.lock_path)
        except:
            pass

    def __enter__(self):
        """默认获取写锁（安全起见）"""
        return self.acquire_write()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class ReadLock:
    """读锁上下文管理器"""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self.rwlock = RWLock(lock_path)

    def __enter__(self):
        return self.rwlock.acquire_read()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rwlock.release()


class WriteLock:
    """写锁上下文管理器"""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self.rwlock = RWLock(lock_path)

    def __enter__(self):
        return self.rwlock.acquire_write()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rwlock.release()
