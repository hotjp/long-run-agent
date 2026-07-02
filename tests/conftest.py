"""Shared pytest fixtures and test-isolation safety nets."""

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_cwd():
    """Ensure every test leaves the working directory as it found it.

    Several script-style tests (e.g. test_cli_force_next_stage) call
    ``os.chdir(tmpdir)`` inside a ``TemporaryDirectory`` block without
    restoring cwd. When the tempdir is deleted on block exit, the process
    cwd becomes stale and the next test's ``os.getcwd()`` raises
    ``FileNotFoundError`` — cascading failures across the whole suite.

    This fixture snapshots cwd before each test and restores it after,
    so one test can never pollute another via the process cwd.
    """
    try:
        cwd = os.getcwd()
    except OSError:
        # cwd already stale (shouldn't happen with this fixture active,
        # but be defensive) — fall back to the tests directory.
        cwd = os.path.dirname(os.path.abspath(__file__))

    yield

    try:
        os.chdir(cwd)
    except OSError:
        pass
