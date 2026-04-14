#!/usr/bin/env python3
"""
Tests for LRA Doctor module
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta

from lra.config import ORPHAN_THRESHOLD_MINUTES, Config, SafeJson
from lra.doctor import (
    DoctorResult,
    check_circular_deps,
    check_config_valid,
    check_constitution_valid,
    check_git_repo,
    check_installation,
    check_lock_file_valid,
    check_locks_valid,
    check_orphaned_locks,
    check_orphaned_tasks,
    check_stale_locks,
    check_task_files,
    check_task_list_valid,
    fix_orphaned_locks,
    run_diagnostics,
)


class TestDoctorChecks:
    """Test individual doctor checks"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_check_installation_not_initialized(self):
        """Test installation check when not initialized"""
        result = check_installation(self.test_dir)
        assert result.status == "error"
        assert result.name == "installation"
        assert "not initialized" in result.message.lower()

    def test_check_installation_initialized(self):
        """Test installation check when initialized"""
        Config.ensure_dirs()
        result = check_installation(self.test_dir)
        assert result.status == "ok"
        assert result.name == "installation"

    def test_check_task_list_valid_not_exists(self):
        """Test task_list check when not exists"""
        result = check_task_list_valid(self.test_dir)
        assert result.status == "error"
        assert result.name == "task_list"
        assert "not found" in result.message.lower()

    def test_check_task_list_valid_exists(self):
        """Test task_list check when exists"""
        Config.ensure_dirs()
        # Create task_list.json
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(task_list_path, {"tasks": []})
        result = check_task_list_valid(self.test_dir)
        assert result.status == "ok"
        assert result.name == "task_list"

    def test_check_locks_valid_not_exists(self):
        """Test locks check when file doesn't exist"""
        result = check_locks_valid(self.test_dir)
        assert result.status == "ok"  # No locks file is OK
        assert result.name == "locks_file"

    def test_check_locks_valid_invalid_json(self):
        """Test locks check with invalid JSON"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        with open(locks_path, "w") as f:
            f.write("invalid json{")

        result = check_locks_valid(self.test_dir)
        assert result.status == "error"

    def test_check_locks_valid_with_data(self):
        """Test locks check with valid locks"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        SafeJson.write(locks_path, {"locks": {"task_1": {"status": "claimed"}}})

        result = check_locks_valid(self.test_dir)
        assert result.status == "ok"
        assert "1 lock" in result.message

    def test_check_constitution_valid_not_exists(self):
        """Test constitution check when not exists"""
        result = check_constitution_valid(self.test_dir)
        assert result.status == "warning"
        assert result.name == "constitution"
        assert "not found" in result.message.lower()

    def test_check_constitution_valid_exists_valid_yaml(self):
        """Test constitution check with valid YAML"""
        Config.ensure_dirs()
        const_path = os.path.join(self.test_dir, Config.METADATA_DIR, "constitution.yaml")
        with open(const_path, "w") as f:
            f.write("schema_version: '1.0'\ncore_principles: []\n")

        result = check_constitution_valid(self.test_dir)
        assert result.status == "ok"

    def test_check_task_files_not_initialized(self):
        """Test task files check when not initialized"""
        result = check_task_files(self.test_dir)
        assert result.name == "task_files"

    def test_check_task_files_all_exist(self):
        """Test task files check when all exist"""
        Config.ensure_dirs()
        # Create a task
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(
            task_list_path, {"tasks": [{"id": "task_001", "task_file": "tasks/task_001.md"}]}
        )
        # Create task file
        tasks_dir = os.path.join(self.test_dir, Config.METADATA_DIR, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        with open(os.path.join(tasks_dir, "task_001.md"), "w") as f:
            f.write("# Task 1\n")

        result = check_task_files(self.test_dir)
        assert result.status == "ok"

    def test_check_task_files_missing(self):
        """Test task files check when files are missing"""
        Config.ensure_dirs()
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(
            task_list_path, {"tasks": [{"id": "task_001", "task_file": "tasks/task_001.md"}]}
        )
        # Don't create task file

        result = check_task_files(self.test_dir)
        assert result.status == "error"
        assert "missing" in result.message.lower()

    def test_check_orphaned_tasks_no_tasks_dir(self):
        """Test orphaned tasks check when no tasks dir"""
        result = check_orphaned_tasks(self.test_dir)
        assert result.status == "ok"

    def test_check_orphaned_tasks_none_orphaned(self):
        """Test orphaned tasks check when none orphaned"""
        Config.ensure_dirs()
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(task_list_path, {"tasks": [{"id": "task_001"}]})
        tasks_dir = os.path.join(self.test_dir, Config.METADATA_DIR, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        with open(os.path.join(tasks_dir, "task_001.md"), "w") as f:
            f.write("# Task\n")

        result = check_orphaned_tasks(self.test_dir)
        assert result.status == "ok"

    def test_check_orphaned_tasks_has_orphaned(self):
        """Test orphaned tasks check when orphaned exist"""
        Config.ensure_dirs()
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(task_list_path, {"tasks": [{"id": "task_001"}]})
        tasks_dir = os.path.join(self.test_dir, Config.METADATA_DIR, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        # Create task file
        with open(os.path.join(tasks_dir, "task_001.md"), "w") as f:
            f.write("# Task\n")
        # Create orphaned task file (not in index)
        with open(os.path.join(tasks_dir, "task_002.md"), "w") as f:
            f.write("# Orphaned\n")

        result = check_orphaned_tasks(self.test_dir)
        assert result.status == "warning"
        assert "orphaned" in result.message.lower()

    def test_check_circular_deps_no_cycle(self):
        """Test circular deps check when no cycle"""
        Config.ensure_dirs()
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(
            task_list_path,
            {
                "tasks": [
                    {"id": "task_001", "dependencies": []},
                    {"id": "task_002", "dependencies": ["task_001"]},
                ]
            },
        )

        result = check_circular_deps(self.test_dir)
        assert result.status == "ok"

    def test_check_circular_deps_has_cycle(self):
        """Test circular deps check when cycle exists"""
        Config.ensure_dirs()
        task_list_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.TASK_LIST_FILE)
        SafeJson.write(
            task_list_path,
            {
                "tasks": [
                    {"id": "task_001", "dependencies": ["task_002"]},
                    {"id": "task_002", "dependencies": ["task_001"]},
                ]
            },
        )

        result = check_circular_deps(self.test_dir)
        assert result.status == "error"
        assert "circular" in result.message.lower()

    def test_check_orphaned_locks_no_locks_file(self):
        """Test orphaned locks check when no locks file"""
        result = check_orphaned_locks(self.test_dir)
        assert result.status == "ok"

    def test_check_orphaned_locks_none_orphaned(self):
        """Test orphaned locks check when none orphaned"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        SafeJson.write(
            locks_path,
            {
                "locks": {
                    "task_001": {
                        "status": "claimed",
                        "last_heartbeat": datetime.now().isoformat(),
                    }
                }
            },
        )

        result = check_orphaned_locks(self.test_dir)
        assert result.status == "ok"

    def test_check_orphaned_locks_has_orphaned(self):
        """Test orphaned locks check when orphaned exist"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        old_time = (datetime.now() - timedelta(minutes=ORPHAN_THRESHOLD_MINUTES + 1)).isoformat()
        SafeJson.write(
            locks_path,
            {
                "locks": {
                    "task_001": {
                        "status": "claimed",
                        "last_heartbeat": old_time,
                    }
                }
            },
        )

        result = check_orphaned_locks(self.test_dir)
        assert result.status == "warning"
        assert "orphaned" in result.message.lower()

    def test_check_stale_locks_none_stale(self):
        """Test stale locks check when none stale"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        SafeJson.write(
            locks_path,
            {
                "locks": {
                    "task_001": {
                        "status": "claimed",
                        "claimed_at": datetime.now().isoformat(),
                    }
                }
            },
        )

        result = check_stale_locks(self.test_dir)
        assert result.status == "ok"

    def test_check_stale_locks_has_stale(self):
        """Test stale locks check when stale exist"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        old_time = (datetime.now() - timedelta(hours=3)).isoformat()
        SafeJson.write(
            locks_path,
            {
                "locks": {
                    "task_001": {
                        "status": "claimed",
                        "claimed_at": old_time,
                    }
                }
            },
        )

        result = check_stale_locks(self.test_dir)
        assert result.status == "warning"
        assert "stale" in result.message.lower()

    def test_check_lock_file_valid_structure(self):
        """Test lock structure check with valid structure"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        SafeJson.write(locks_path, {"locks": {}})

        result = check_lock_file_valid(self.test_dir)
        assert result.status == "ok"

    def test_check_lock_file_valid_invalid(self):
        """Test lock structure check with invalid structure"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        SafeJson.write(locks_path, {"locks": None})  # Should be dict

        result = check_lock_file_valid(self.test_dir)
        assert result.status == "error"

    def test_check_config_valid_not_exists(self):
        """Test config check when not exists"""
        result = check_config_valid(self.test_dir)
        assert result.status == "warning"

    def test_check_config_valid_exists(self):
        """Test config check when exists"""
        Config.ensure_dirs()
        # Create config.json
        config_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.CONFIG_FILE)
        SafeJson.write(config_path, {"project_name": "test"})
        result = check_config_valid(self.test_dir)
        assert result.status == "ok"

    def test_check_git_repo_not_git(self):
        """Test git repo check when not a git repo"""
        result = check_git_repo(self.test_dir)
        assert result.status == "warning"
        assert "git" in result.message.lower()

    def test_check_git_repo_is_git(self):
        """Test git repo check when is a git repo"""
        os.makedirs(os.path.join(self.test_dir, ".git"), exist_ok=True)
        result = check_git_repo(self.test_dir)
        assert result.status == "ok"


class TestRunDiagnostics:
    """Test run_diagnostics function"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_run_diagnostics_returns_result(self):
        """Test that run_diagnostics returns a DoctorResult"""
        result = run_diagnostics(self.test_dir)
        assert isinstance(result, DoctorResult)
        assert hasattr(result, "path")
        assert hasattr(result, "overall_ok")
        assert hasattr(result, "checks")

    def test_run_diagnostics_checks_all(self):
        """Test that run_diagnostics runs all checks"""
        result = run_diagnostics(self.test_dir)
        check_names = {c.name for c in result.checks}

        expected = {
            "installation",
            "task_list",
            "locks_file",
            "constitution",
            "task_files",
            "orphaned_tasks",
            "circular_deps",
            "orphaned_locks",
            "stale_locks",
            "lock_structure",
            "config_file",
            "version_tracking",
            "git_repo",
        }
        assert expected.issubset(check_names)


class TestFixOrphanedLocks:
    """Test fix_orphaned_locks function"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_fix_orphaned_locks_no_locks_file(self):
        """Test fix when no locks file"""
        result = fix_orphaned_locks(self.test_dir)
        assert result is True

    def test_fix_orphaned_locks_cleans_orphaned(self):
        """Test fix cleans orphaned locks"""
        Config.ensure_dirs()
        locks_path = os.path.join(self.test_dir, Config.METADATA_DIR, Config.LOCKS_FILE)
        old_time = (datetime.now() - timedelta(minutes=ORPHAN_THRESHOLD_MINUTES + 1)).isoformat()
        SafeJson.write(
            locks_path,
            {
                "locks": {
                    "task_001": {
                        "status": "claimed",
                        "last_heartbeat": old_time,
                    }
                }
            },
        )

        result = fix_orphaned_locks(self.test_dir)
        assert result is True

        # Verify lock was marked as orphaned
        data = SafeJson.read(locks_path)
        assert data["locks"]["task_001"]["status"] == "orphaned"
