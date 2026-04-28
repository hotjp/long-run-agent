"""Safe git operations — no shell, subprocess.run([git, ...]) only."""

import subprocess
from pathlib import Path


class GitError(Exception):
    pass


class GitUtils:
    """Safe git operations using subprocess with arg list (no shell)."""

    @staticmethod
    def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
        """Execute git command, args as list, no shell."""
        try:
            return subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                check=check,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"git {' '.join(args)} failed: {e.stderr}") from e

    @staticmethod
    def is_repo(cwd: Path) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    @staticmethod
    def is_clean(cwd: Path) -> bool:
        """Check if working tree is clean (no modifications, no untracked)."""
        result = GitUtils._git(["status", "--porcelain"], cwd, check=False)
        if result.stdout.strip():
            return False
        return True

    @staticmethod
    def ensure_clean_working_tree(cwd: Path) -> None:
        """Raise GitError if working tree is not clean."""
        if not GitUtils.is_repo(cwd):
            raise GitError("Not a git repository")
        if not GitUtils.is_clean(cwd):
            result = GitUtils._git(["status", "--porcelain"], cwd, check=False)
            raise GitError(
                "Working tree is not clean. Commit or stash changes first.\n"
                f"Dirty files:\n{result.stdout}"
            )

    @staticmethod
    def get_current_branch(cwd: Path) -> str:
        result = GitUtils._git(["symbolic-ref", "--short", "HEAD"], cwd, check=False)
        if result.returncode != 0:
            result = GitUtils._git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        return result.stdout.strip()

    @staticmethod
    def create_branch(branch_name: str, cwd: Path) -> None:
        GitUtils._git(["checkout", "-b", branch_name], cwd)

    @staticmethod
    def checkout(branch_name: str, cwd: Path) -> None:
        GitUtils._git(["checkout", branch_name], cwd)

    @staticmethod
    def add_all(cwd: Path) -> None:
        GitUtils._git(["add", "-A"], cwd)

    @staticmethod
    def commit(message: str, cwd: Path) -> None:
        result = GitUtils._git(["commit", "-m", message], cwd, check=False)
        if result.returncode != 0 and "nothing to commit" not in result.stderr:
            raise GitError(f"git commit failed: {result.stderr}")

    @staticmethod
    def reset_hard(cwd: Path) -> None:
        """Reset --hard + clean -fd,彻底回滚到 HEAD."""
        GitUtils._git(["reset", "--hard", "HEAD"], cwd)
        GitUtils._git(["clean", "-fd"], cwd, check=False)

    @staticmethod
    def get_head_commit(cwd: Path) -> str:
        result = GitUtils._git(["rev-parse", "HEAD"], cwd)
        return result.stdout.strip()

    @staticmethod
    def delete_branch(branch_name: str, cwd: Path, force: bool = False) -> None:
        flag = "-D" if force else "-d"
        GitUtils._git(["branch", flag, branch_name], cwd, check=False)


def check_working_tree_clean(cwd: Path) -> tuple[bool, str]:
    """Verify working tree is clean before relay starts. Returns (ok, message)."""
    if not GitUtils.is_repo(cwd):
        return False, "Not a git repository"
    if not GitUtils.is_clean(cwd):
        return False, "Working tree is not clean. Commit or stash changes first."
    return True, "Working tree is clean"
