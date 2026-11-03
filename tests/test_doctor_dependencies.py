"""
Tests for 运行环境依赖检查（doctor runtime_dependencies）+ 缺依赖时的错误文案。

背景：LRA 用 Jinja2 渲染任务书。缺依赖（或依赖被同名文件遮蔽）时，
症状是"任务书渲染不出来"，但真正的原因是环境——旧文案却让人去查模板，
给的修复命令（lra doctor）也修不好。

覆盖：
- doctor.runtime_dependencies：依赖齐全 → ok
- 依赖缺失 → error，且 fix 指向 pip install（不是"检查模板"）
- 依赖被同名文件遮蔽 → 报"被遮蔽"，并指出实际加载路径
- 缺 jinja2 时 lra create 报 jinja2_not_installed（而不是"模板损坏"），
  并且回滚（不留僵尸任务）
"""

import os
import subprocess
import sys
import tempfile

import pytest

from lra.doctor import check_runtime_dependencies
from lra.errors import get_error_with_action

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


# ---------- doctor 检查 ----------

def test_runtime_dependencies_ok_in_normal_env(tmp_path):
    check = check_runtime_dependencies(str(tmp_path))
    assert check.status == "ok", check.detail
    assert check.name == "runtime_dependencies"


def test_runtime_dependencies_detects_missing_jinja2(tmp_path, monkeypatch):
    import importlib

    real_import_module = importlib.import_module

    def fake_import_module(name, *args, **kwargs):
        if name == "jinja2":
            raise ModuleNotFoundError("No module named 'jinja2'", name="jinja2")
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    check = check_runtime_dependencies(str(tmp_path))

    assert check.status == "error"
    assert "jinja2" in check.detail
    # 修复建议必须真的能修好 —— 装依赖，而不是"检查模板"
    assert "pip install" in check.fix
    assert "doctor" not in check.fix


def test_runtime_dependencies_detects_shadowing(tmp_path, monkeypatch):
    """依赖被同名文件遮蔽时，报错要指向"被遮蔽"，而不是"没装"。"""
    import importlib

    real_import_module = importlib.import_module

    def fake_import_module(name, *args, **kwargs):
        if name == "jinja2":
            # 模拟 jinja2 内部 import inspect 被遮蔽的情形
            raise ModuleNotFoundError("No module named 'bpy'", name="bpy")
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    check = check_runtime_dependencies(str(tmp_path))

    assert check.status == "error"
    assert "遮蔽" in check.detail
    assert "bpy" in check.detail  # 指出真正缺的是哪个模块


# ---------- 错误文案 ----------

def test_jinja2_error_message_is_actionable():
    err = get_error_with_action("jinja2_not_installed", {"task_id": "task_001"})
    assert "Jinja2" in err["message"]
    assert "pip install" in err["action"]
    assert "doctor" not in err["action"]


def test_jinja2_error_message_has_no_format_placeholders():
    """文案里不能出现裸的花括号 —— get_error_with_action 会 .format() 它。"""
    err = get_error_with_action("jinja2_not_installed", {"task_id": "task_001"})
    assert "{" not in err["message"]
    assert "{" not in err["hint"]


# ---------- 端到端：缺 jinja2 时 create 失败且不留僵尸 ----------

@pytest.mark.skipif(
    not os.environ.get("LRA_TEST_NO_JINJA2_PYTHON"),
    reason="需要一个装了 filelock/pyyaml 但没装 jinja2 的解释器",
)
def test_create_without_jinja2_rolls_back():
    python = os.environ["LRA_TEST_NO_JINJA2_PYTHON"]
    with tempfile.TemporaryDirectory() as tmpdir:
        rc, _, err = _run(["init", "--name", "t"], tmpdir, python=python)
        assert rc == 0, err

        rc, out, _ = _run(["create", "缺 jinja2 的任务"], tmpdir, python=python)
        assert rc != 0
        assert "Jinja2" in out
        assert "pip install" in out

        # 没有留下"有元数据、无任务书"的僵尸任务
        import json

        task_list = os.path.join(tmpdir, ".long-run-agent", "task_list.json")
        with open(task_list, encoding="utf-8") as f:
            data = json.load(f)
        assert data["tasks"] == []
