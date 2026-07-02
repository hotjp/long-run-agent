"""Shared pytest fixtures and test-isolation safety nets."""

import contextlib
import os

import pytest


@contextlib.contextmanager
def chdir_to(path):
    """chdir into `path` and restore the original cwd on exit.

    Required on Windows: deleting a directory that is the current process
    cwd raises PermissionError (WinError 32), which breaks
    ``tempfile.TemporaryDirectory`` cleanup. Any test that chdirs into a
    tempdir must restore cwd *before* the tempdir is cleaned up — this
    helper does that, so ``with TemporaryDirectory() as d, chdir_to(d):``
    is Windows-safe.
    """
    orig = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(orig)


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
