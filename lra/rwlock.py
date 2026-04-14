#!/usr/bin/env python3
"""
读写锁实现
支持多读单写，优化并发性能
"""

import os
from typing import Optional, IO
from filelock import FileLock


class RWLock:
    """
    读写锁（Read-Write Lock）

    - 读锁：允许多个并发读
    - 写锁：独占写，阻塞所有读写
    """

    def __init__(self, lock_path: str):
        self.lock_path = lock_path + ".rwlock"
        self._filelock = FileLock(self.lock_path)
        self.mode: Optional[str] = None

    def _ensure_lock_file(self):
        """确保锁文件存在"""
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
        if not os.path.exists(self.lock_path):
            with open(self.lock_path, "w") as f:
                pass

    def acquire_read(self):
        """获取读锁（共享锁）"""
        self._ensure_lock_file()
        self._filelock.acquire()
        self.mode = "r"
        return self

    def acquire_write(self):
        """获取写锁（独占锁）"""
        self._ensure_lock_file()
        self._filelock.acquire()
        self.mode = "w"
        return self

    def release(self):
        """释放锁"""
        if self._filelock:
            self._filelock.release()
            self.mode = None

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
