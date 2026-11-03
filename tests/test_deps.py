"""
Tests for lra/deps.py —— 运行时依赖的探测与修复。

背景（issue #4）：
- LRA 依赖 jinja2 / pyyaml / filelock，缺了会让 `lra create` 静默回滚。
- 报错文案里给的修复命令必须**真的能修好**：
  - PEP 668 环境（homebrew / 系统 Python）上裸 `pip install` 会被直接拒绝；
  - 裸 `pip` 可能绑到另一个解释器上，装完还是缺；
  - 依赖被同名文件遮蔽时（当前目录有个 inspect.py），装包根本没用。

所以这一层负责三件事：分清 missing / shadowed / broken、生成能跑的安装命令、
把"该装包"和"该挪文件"区分开。
"""

import os
import subprocess
import sys
import tempfile

from lra import deps
from lra.errors import get_error_with_action

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- 安装命令生成 ----------

def test_install_command_uses_current_interpreter(monkeypatch):
    """必须用 sys.executable -m pip：裸 pip 可能装到别的解释器里。"""
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    cmd = deps.pip_install_command(["jinja2"])
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "pip"]
    assert cmd[-1] == "jinja2"


def test_install_command_in_virtualenv_has_no_bypass_flags(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    cmd = deps.pip_install_command(["jinja2"])
    assert "--user" not in cmd
    assert "--break-system-packages" not in cmd


def test_install_command_outside_virtualenv_uses_user(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: False)
    monkeypatch.setattr(deps, "externally_managed", lambda: False)
    cmd = deps.pip_install_command(["jinja2"])
    assert "--user" in cmd
    assert "--break-system-packages" not in cmd


def test_install_command_handles_pep668(monkeypatch):
    """PEP 668 环境上 pip install 会被拒——必须自动补 --break-system-packages，
    否则给出的命令跑了也白跑。"""
    monkeypatch.setattr(deps, "in_virtualenv", lambda: False)
    monkeypatch.setattr(deps, "externally_managed", lambda: True)
    cmd = deps.pip_install_command(["jinja2"])
    assert "--user" in cmd
    assert "--break-system-packages" in cmd


def test_missing_install_hint_lists_only_missing_packages(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    monkeypatch.setattr(deps, "missing_packages", lambda: ["pyyaml"])
    hint = deps.missing_install_hint()
    assert "pyyaml" in hint
    assert "jinja2" not in hint
    assert "pip" in hint


def test_missing_install_hint_when_nothing_missing(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    monkeypatch.setattr(deps, "missing_packages", lambda: [])
    hint = deps.missing_install_hint()
    assert "long-run-agent" in hint


# ---------- 探测 ----------

def test_probe_detects_ok(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    status = deps.probe_dependency("json", "json", "标准库")
    assert status.state == "ok"
    assert status.ok
    assert status.error_code == ""
    assert status.fix_command


def test_probe_detects_missing(monkeypatch):
    import importlib

    real = importlib.import_module

    def fake(name, *a, **kw):
        if name == "jinja2":
            raise ModuleNotFoundError("No module named 'jinja2'", name="jinja2")
        return real(name, *a, **kw)

    monkeypatch.setattr(importlib, "import_module", fake)
    status = deps.probe_dependency("jinja2", "jinja2", "渲染任务书模板")
    assert status.state == "missing"
    assert status.error_code == "jinja2_not_installed"
    assert "jinja2" in status.detail


def test_probe_detects_shadowing(monkeypatch, tmp_path):
    """依赖在，但被同名文件顶替了 —— 装包没用，得挪文件。"""
    import importlib

    real = importlib.import_module
    culprit = tmp_path / "inspect.py"
    culprit.write_text("raise ImportError('shadowed')\n", encoding="utf-8")

    def fake(name, *a, **kw):
        if name == "jinja2":
            # 模拟 jinja2 内部 import 被同名文件遮蔽
            raise ModuleNotFoundError("No module named 'bpy'", name="bpy")
        return real(name, *a, **kw)

    monkeypatch.setattr(importlib, "import_module", fake)
    status = deps.probe_dependency("jinja2", "jinja2", "渲染任务书模板")
    assert status.state == "shadowed"
    assert status.error_code == "jinja2_import_failed"
    assert "遮蔽" in status.detail


def test_probe_detects_broken_import(monkeypatch):
    import importlib

    real = importlib.import_module

    def fake(name, *a, **kw):
        if name == "jinja2":
            raise ValueError("版本不兼容")
        return real(name, *a, **kw)

    monkeypatch.setattr(importlib, "import_module", fake)
    status = deps.probe_dependency("jinja2", "jinja2", "渲染任务书模板")
    assert status.state == "broken"
    assert status.error_code == "jinja2_import_failed"
    assert "版本不兼容" in status.detail


def test_probe_detects_module_loaded_from_wrong_origin(monkeypatch, tmp_path):
    """import 成功，但加载的不是 site-packages 里那份 —— 也是被顶替了。"""
    import types

    fake_mod = types.ModuleType("jinja2")
    fake_mod.__file__ = str(tmp_path / "jinja2.py")
    monkeypatch.setattr(deps.importlib, "import_module", lambda name, *a, **kw: fake_mod)
    status = deps.probe_dependency("jinja2", "jinja2", "渲染任务书模板")
    assert status.state == "shadowed"
    assert status.error_code == "jinja2_import_failed"


def test_probe_all_covers_every_required_dep():
    statuses = deps.probe_all()
    assert {s.module for s in statuses} == {m for m, _p, _u in deps.REQUIRED_DEPS}


# ---------- 修复 ----------

def test_install_missing_dry_run_reports_command(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    monkeypatch.setattr(
        deps,
        "probe_all",
        lambda: [deps.DepStatus("jinja2", "jinja2", "渲染", "missing", "No module named")],
    )
    result = deps.install_missing(dry_run=True)
    assert result["ok"] is True
    assert result["command"]
    assert "jinja2" in result["command"]
    assert result["installed"] == []


def test_install_missing_skips_shadowed(monkeypatch):
    """shadowed 的依赖装包没用 —— 不能把它当成待安装项。"""
    monkeypatch.setattr(
        deps,
        "probe_all",
        lambda: [deps.DepStatus("jinja2", "jinja2", "渲染", "shadowed", "被遮蔽")],
    )
    result = deps.install_missing(dry_run=True)
    assert result["command"] == ""
    assert result["installed"] == []
    assert result["unfixable"]


def test_install_missing_dedupes_same_culprit(monkeypatch):
    """同一个遮蔽文件会连累多个依赖 —— 报一遍就够。"""
    monkeypatch.setattr(
        deps,
        "probe_all",
        lambda: [
            deps.DepStatus("jinja2", "jinja2", "渲染", "shadowed", "被 /x/inspect.py 遮蔽"),
            deps.DepStatus("filelock", "filelock", "加锁", "shadowed", "被 /x/inspect.py 遮蔽"),
        ],
    )
    result = deps.install_missing(dry_run=True)
    assert len(result["unfixable"]) == 1


# ---------- 修复指引分诊 ----------

def test_fix_hint_for_missing_gives_install_command(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    monkeypatch.setattr(
        deps,
        "probe_dependency",
        lambda *a, **kw: deps.DepStatus("jinja2", "jinja2", "渲染", "missing", "No module named"),
    )
    hint = deps.fix_hint_for("jinja2")
    assert "pip install" in hint
    assert "jinja2" in hint


def test_fix_hint_for_shadowed_says_move_the_file(monkeypatch):
    """被遮蔽时装包没用 —— 指引必须说"挪文件"。"""
    monkeypatch.setattr(
        deps,
        "probe_dependency",
        lambda *a, **kw: deps.DepStatus("jinja2", "jinja2", "渲染", "shadowed", "被遮蔽"),
    )
    hint = deps.fix_hint_for("jinja2")
    assert "装包无用" in hint
    assert "pip install" not in hint


def test_fix_hint_for_broken_forces_reinstall(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    monkeypatch.setattr(
        deps,
        "probe_dependency",
        lambda *a, **kw: deps.DepStatus("jinja2", "jinja2", "渲染", "broken", "boom"),
    )
    hint = deps.fix_hint_for("jinja2")
    assert "--force-reinstall" in hint


def test_install_missing_reports_pip_failure(monkeypatch):
    monkeypatch.setattr(deps, "in_virtualenv", lambda: True)
    monkeypatch.setattr(
        deps,
        "probe_all",
        lambda: [deps.DepStatus("jinja2", "jinja2", "渲染", "missing", "No module named")],
    )

    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "error: externally-managed-environment"

    monkeypatch.setattr(deps.subprocess, "run", lambda *a, **kw: _Proc())
    result = deps.install_missing()
    assert result["ok"] is False
    assert "externally-managed" in result["failed"]


# ---------- 错误文案 ----------

def test_jinja2_import_failed_message_is_actionable():
    err = get_error_with_action(
        "jinja2_import_failed",
        {
            "detail": "ModuleNotFoundError: No module named 'bpy'",
            "install_cmd": "python -m pip install",
        },
    )
    assert "Jinja2" in err["message"]
    assert "原始错误" in err["hint"]
    assert "bpy" in err["hint"]


def test_jinja2_import_failed_has_no_bare_placeholders():
    err = get_error_with_action(
        "jinja2_import_failed",
        {"detail": "boom", "install_cmd": "python -m pip install"},
    )
    assert "{" not in err["message"]
    assert "{" not in err["hint"]
    assert "{" not in err["action"]


def test_error_formatting_survives_missing_context():
    """报错路径本身不能因为少传字段就崩 —— 那等于把问题藏得更深。"""
    err = get_error_with_action("jinja2_not_installed", {})
    assert "{" not in err["message"]
    assert err["action"]
    assert err["hint"]


# ---------- 端到端：遮蔽环境 ----------

def _run(args, cwd, python=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [python or sys.executable, "-m", "lra.cli"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


def test_shadowed_env_create_reports_culprit_not_install_command():
    """被同名文件遮蔽时，create 必须点名那个文件，且不能让人去装包。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = os.path.join(tmpdir, "proj")
        os.makedirs(proj)
        # 用一个会失败的同名文件遮蔽标准库 inspect（dataclasses/jinja2 都会 import 它）
        with open(os.path.join(proj, "inspect.py"), "w", encoding="utf-8") as f:
            f.write("raise ModuleNotFoundError(\"No module named 'bpy'\")\n")

        rc, _, _ = _run(["init", "--name", "t"], proj)
        assert rc == 0

        rc, out, _ = _run(["create", "遮蔽环境下的任务"], proj)
        assert rc != 0
        assert "Jinja2" in out
        # 原始错误透传（issue 建议 2）
        assert "bpy" in out
        # 修复动作必须是"挪文件"，不是"装包"
        assert "遮蔽" in out
        assert "install" not in out.split("建议")[-1]


def test_shadowed_env_doctor_points_at_the_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = os.path.join(tmpdir, "proj")
        os.makedirs(proj)
        with open(os.path.join(proj, "inspect.py"), "w", encoding="utf-8") as f:
            f.write("raise ModuleNotFoundError(\"No module named 'bpy'\")\n")

        rc, out, _ = _run(["doctor", "--check", "runtime_dependencies"], proj)
        assert rc == 0
        assert "inspect.py" in out
        assert "遮蔽" in out
