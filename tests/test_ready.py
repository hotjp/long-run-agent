"""
Tests for the lra ready command and get_ready_tasks functionality.
"""

import os
import tempfile

import pytest

from lra.config import Config, SafeJson
from lra.task_manager import TaskManager


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_dir = os.getcwd()
        os.chdir(tmpdir)

        # Initialize project structure
        Config.METADATA_DIR = ".long-run-agent"
        Config.ensure_dirs()

        # Create a minimal project
        task_list = {
            "project_name": "test-project",
            "created_at": "2024-01-01T00:00:00",
            "tasks": [],
        }
        SafeJson.write(Config.get_task_list_path(), task_list)

        yield tmpdir

        os.chdir(orig_dir)


@pytest.fixture
def sample_tasks(temp_project):
    """Create sample tasks for testing."""
    tasks = [
        {
            "id": "task_001",
            "description": "First task - pending",
            "template": "task",
            "priority": "P1",
            "status": "pending",
            "parent_id": None,
            "dependencies": [],
            "dependency_type": "all",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
        {
            "id": "task_002",
            "description": "Second task - in_progress",
            "template": "task",
            "priority": "P0",
            "status": "in_progress",
            "parent_id": None,
            "dependencies": [],
            "dependency_type": "all",
            "created_at": "2024-01-01T01:00:00",
            "updated_at": "2024-01-01T01:00:00",
        },
        {
            "id": "task_003",
            "description": "Third task - completed",
            "template": "task",
            "priority": "P2",
            "status": "completed",
            "parent_id": None,
            "dependencies": [],
            "dependency_type": "all",
            "created_at": "2024-01-01T02:00:00",
            "updated_at": "2024-01-01T02:00:00",
        },
        {
            "id": "task_004",
            "description": "Fourth task - blocked by task_001",
            "template": "task",
            "priority": "P1",
            "status": "blocked",
            "parent_id": None,
            "dependencies": ["task_001"],
            "dependency_type": "all",
            "created_at": "2024-01-01T03:00:00",
            "updated_at": "2024-01-01T03:00:00",
        },
        {
            "id": "task_005",
            "description": "Fifth task - truly_completed",
            "template": "task",
            "priority": "P2",
            "status": "truly_completed",
            "parent_id": None,
            "dependencies": [],
            "dependency_type": "all",
            "created_at": "2024-01-01T04:00:00",
            "updated_at": "2024-01-01T04:00:00",
        },
        {
            "id": "task_006",
            "description": "Sixth task - no dependencies",
            "template": "task",
            "priority": "P3",
            "status": "pending",
            "parent_id": None,
            "dependencies": [],
            "dependency_type": "all",
            "created_at": "2024-01-01T05:00:00",
            "updated_at": "2024-01-01T05:00:00",
        },
    ]

    data = SafeJson.read(Config.get_task_list_path())
    data["tasks"] = tasks
    SafeJson.write(Config.get_task_list_path(), data)

    return tasks


def test_get_ready_tasks_excludes_completed(temp_project, sample_tasks):
    """Test that get_ready_tasks excludes completed tasks."""
    tm = TaskManager()

    ready = tm.get_ready_tasks()

    # Should not include completed, truly_completed, force_completed
    ready_ids = [t["id"] for t in ready]

    assert "task_003" not in ready_ids  # completed
    assert "task_005" not in ready_ids  # truly_completed


def test_get_ready_tasks_includes_pending(temp_project, sample_tasks):
    """Test that get_ready_tasks includes pending tasks."""
    tm = TaskManager()

    ready = tm.get_ready_tasks()

    ready_ids = [t["id"] for t in ready]

    assert "task_001" in ready_ids  # pending
    assert "task_002" in ready_ids  # in_progress
    assert "task_004" not in ready_ids  # blocked - has unmet dependency


def test_get_ready_tasks_excludes_blocked(temp_project, sample_tasks):
    """Test that get_ready_tasks excludes tasks with unmet dependencies."""
    tm = TaskManager()

    ready = tm.get_ready_tasks()

    ready_ids = [t["id"] for t in ready]

    # task_004 is blocked by task_001 which is pending (not completed)
    assert "task_004" not in ready_ids


def test_get_ready_tasks_sort_by_priority(temp_project, sample_tasks):
    """Test that get_ready_tasks sorts by priority by default."""
    tm = TaskManager()

    ready = tm.get_ready_tasks(sort="priority")

    # P0 should come before P1, P1 before P2, P2 before P3
    priorities = [t["priority"] for t in ready]
    assert priorities == sorted(priorities)


def test_get_ready_tasks_sort_by_oldest(temp_project, sample_tasks):
    """Test that get_ready_tasks sorts by oldest (task number) when specified."""
    tm = TaskManager()

    ready = tm.get_ready_tasks(sort="oldest")

    # Should be sorted by task number (oldest first)
    ids = [t["id"] for t in ready]
    # Filter out blocked task
    ready_ids = [i for i in ids if i != "task_004"]
    assert ready_ids == ["task_001", "task_002", "task_006"]


def test_get_ready_tasks_limit(temp_project, sample_tasks):
    """Test that get_ready_tasks respects the limit parameter."""
    tm = TaskManager()

    ready = tm.get_ready_tasks(limit=2)

    assert len(ready) == 2


def test_get_ready_tasks_priority_filter(temp_project, sample_tasks):
    """Test that get_ready_tasks filters by priority."""
    tm = TaskManager()

    ready = tm.get_ready_tasks(priority_filter="P0")

    assert len(ready) == 1
    assert ready[0]["id"] == "task_002"
    assert ready[0]["priority"] == "P0"


def test_get_ready_tasks_returns_correct_fields(temp_project, sample_tasks):
    """Test that get_ready_tasks returns correct fields."""
    tm = TaskManager()

    ready = tm.get_ready_tasks()

    assert len(ready) > 0
    task = ready[0]

    assert "id" in task
    assert "title" in task
    assert "priority" in task
    assert "status" in task
    assert "parent_id" in task
    assert "blocked_by" in task
    assert "assignee" in task


def test_get_ready_tasks_empty_project():
    """Test that get_ready_tasks handles empty project gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_dir = os.getcwd()
        os.chdir(tmpdir)

        try:
            Config.METADATA_DIR = ".long-run-agent"
            Config.ensure_dirs()

            task_list = {
                "project_name": "empty-project",
                "created_at": "2024-01-01T00:00:00",
                "tasks": [],
            }
            SafeJson.write(Config.get_task_list_path(), task_list)

            tm = TaskManager()
            ready = tm.get_ready_tasks()

            assert ready == []
        finally:
            os.chdir(orig_dir)


def test_get_blocked_tasks(temp_project, sample_tasks):
    """Test that get_blocked_tasks returns blocked tasks with reasons."""
    tm = TaskManager()

    blocked = tm.get_blocked_tasks()

    assert len(blocked) == 1
    assert blocked[0]["id"] == "task_004"
    assert len(blocked[0]["blocked_by"]) == 1
    assert blocked[0]["blocked_by"][0]["id"] == "task_001"


def test_get_ready_tasks_with_dependencies_satisfied(temp_project):
    """Test that tasks are ready when their dependencies are satisfied."""
    tasks = [
        {
            "id": "task_001",
            "description": "First task",
            "template": "task",
            "priority": "P1",
            "status": "completed",  # Will be treated as completed
            "parent_id": None,
            "dependencies": [],
            "dependency_type": "all",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
        {
            "id": "task_002",
            "description": "Second task - dep on task_001",
            "template": "task",
            "priority": "P1",
            "status": "blocked",  # Initially blocked
            "parent_id": None,
            "dependencies": ["task_001"],
            "dependency_type": "all",
            "created_at": "2024-01-01T01:00:00",
            "updated_at": "2024-01-01T01:00:00",
        },
    ]

    data = SafeJson.read(Config.get_task_list_path())
    data["tasks"] = tasks
    SafeJson.write(Config.get_task_list_path(), data)

    tm = TaskManager()

    # task_002 has dependency on task_001 (completed), so it should be ready
    # even though its status is "blocked" - get_ready_tasks checks dependencies
    ready = tm.get_ready_tasks()
    ready_ids = [t["id"] for t in ready]
    assert "task_002" in ready_ids


def test_get_ready_tasks_no_locks_manager(temp_project, sample_tasks):
    """Test that get_ready_tasks works without locks_manager."""
    tm = TaskManager()

    # Pass None as locks_manager
    ready = tm.get_ready_tasks(locks_manager=None)

    # Should still return ready tasks
    assert len(ready) > 0
