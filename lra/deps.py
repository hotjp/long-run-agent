#!/usr/bin/env python3
"""
LRA 运行时依赖的探测与修复

jinja2 / pyyaml / filelock 是 LRA 的硬依赖：缺任何一个，LRA 都干不了活。
但症状很容易被误读成"模板坏了"或"环境坏了"，于是排查方向整个跑偏。

这里把判断集中在一处，让 lra doctor 和 lra create 给出**同一个结论、
同一个修复动作**——错误文案里引用的命令必须真能修好。

三种坏法必须分开报：
- missing  —— 真的没装：装上就好
- shadowed —— 装了，但被同名文件顶替了（当前目录有个 inspect.py 之类）
- broken   —— 装了但 import 本身报错（版本不兼容、缺 C 扩展等）

另外还要处理 PEP 668：externally-managed 的 Python（homebrew / 系统自带）
上 `pip install` 会被直接拒绝，给出修不好的命令等于没说。
"""

import importlib
import os
import subprocess
import sys
import sysconfig
from typing import Dict, List

# (import 名, pip 包名, 用途)
REQUIRED_DEPS = [
    ("jinja2", "jinja2", "渲染任务书模板（Jinja2 语法）"),
    ("yaml", "pyyaml", "读写模板与 constitution"),
    ("filelock", "filelock", "文件锁（多 worker 并发写 task_list）"),
]

_SITE_MARKERS = ("site-packages", "dist-packages")

# PEP 668 的标记文件名
_EXTERNALLY_MANAGED = "EXTERNALLY-MANAGED"


class DepStatus:
    """单个依赖的探测结果

    刻意用普通类而不是 dataclass：dataclasses 自己 import inspect，
    而 inspect 恰恰是最常被同名文件遮蔽的那个标准库模块——
    用 dataclass 会让本模块在遮蔽环境下直接 import 失败，
    连"诊断遮蔽问题"这件事本身都做不了。
    """

    __slots__ = ("module", "package", "purpose", "state", "detail", "origin")

    def __init__(
        self,
        module: str,
        package: str,
        purpose: str,
        state: str,
        detail: str = "",
        origin: str = "",
    ):
        self.module = module  # import 名，如 jinja2
        self.package = package  # pip 包名，如 pyyaml
        self.purpose = purpose  # 用途
        self.state = state  # ok | missing | shadowed | broken
        self.detail = detail  # 原始异常 / 诊断
        self.origin = origin  # 实际加载路径，或遮蔽它的文件

    @property
    def ok(self) -> bool:
        return self.state == "ok"

    @property
    def error_code(self) -> str:
        """对应的错误码，供 errors.py 查表"""
        if self.state == "missing":
            return f"{self.module}_not_installed"
        if self.state in ("shadowed", "broken"):
            return f"{self.module}_import_failed"
        return ""

    @property
    def fix_command(self) -> str:
        """装这个依赖的命令（PEP 668 环境已适配）"""
        return " ".join(pip_install_command([self.package]))

    def error_detail(self) -> str:
        """给 errors.py 的 detail：原始错误 + 诊断结论"""
        if self.state == "missing":
            return self.detail or f"No module named '{self.module}'"
        return self.detail

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"DepStatus({self.package}, {self.state})"


# ---------- 环境判定 ----------


def _stdlib_dirs() -> List[str]:
    dirs = []
    for key in ("stdlib", "platstdlib"):
        try:
            path = sysconfig.get_path(key)
        except Exception:  # pragma: no cover - 某些平台没有这两个 key
            continue
        if path:
            dirs.append(os.path.realpath(path))
    return dirs


def _is_site_or_stdlib(path: str) -> bool:
    """路径是否属于 site-packages / 标准库目录"""
    if not path:
        return True
    real = os.path.realpath(path)
    if any(marker in real for marker in _SITE_MARKERS):
        return True
    return any(real.startswith(d + os.sep) for d in _stdlib_dirs())


def externally_managed() -> bool:
    """这个 Python 是否受 PEP 668 保护（pip install 会被直接拒绝）"""
    for d in _stdlib_dirs():
        if os.path.exists(os.path.join(d, _EXTERNALLY_MANAGED)):
            return True
    return False


def in_virtualenv() -> bool:
    """是否跑在虚拟环境里"""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix) or hasattr(sys, "real_prefix")


def pip_install_command(packages: List[str]) -> List[str]:
    """生成"在这个解释器里装这些包"的命令。

    关键点：用 ``sys.executable -m pip`` 而不是裸 ``pip``——
    裸 pip 绑定的解释器可能和跑 lra 的不是同一个（PATH 上多个 Python 时
    极常见），装完还是缺。

    PEP 668 环境（homebrew / 系统自带 Python）上 pip install 会被拒，
    需要 ``--user --break-system-packages``。
    """
    exe = sys.executable or "python3"
    cmd = [exe, "-m", "pip", "install"]
    if in_virtualenv():
        # 虚拟环境里直接装进 venv，不需要任何绕过标记
        pass
    else:
        cmd += ["--user"]
        if externally_managed():
            cmd += ["--break-system-packages"]
    return cmd + list(packages)


# ---------- 探测 ----------


def _culprit_from_traceback(exc: BaseException) -> str:
    """从异常回溯里找出最深的帧文件——它就是"顶替了标准库的那个文件"

    例：当前目录有 inspect.py 遮蔽了标准库 inspect，jinja2 内部
    ``import inspect`` 会去执行它，于是报 ``No module named 'bpy'``。
    回溯最深帧的文件名就是 /tmp/inspect.py。
    """
    tb = exc.__traceback__
    last = None
    while tb is not None:
        last = tb
        tb = tb.tb_next
    if last is None:
        return ""
    return last.tb_frame.f_code.co_filename


def _shadow_name(path: str) -> str:
    """从被遮蔽的文件名推出它顶替了哪个标准库模块"""
    return os.path.splitext(os.path.basename(path))[0]


def probe_dependency(module: str, package: str, purpose: str) -> DepStatus:
    """探测单个依赖"""
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError as e:
        # e.name 是"真正缺失"的那个模块名
        # - 等于 module → 这个依赖压根没装
        # - 不等 → 依赖在，但中途被同名文件顶替了
        if e.name == module:
            return DepStatus(module, package, purpose, "missing", f"{type(e).__name__}: {e}")
        culprit = _culprit_from_traceback(e)
        if culprit and not _is_site_or_stdlib(culprit):
            return DepStatus(
                module,
                package,
                purpose,
                "shadowed",
                f"{type(e).__name__}: {e} —— 被 {culprit} 遮蔽了标准库 "
                f"{_shadow_name(culprit)}",
                culprit,
            )
        return DepStatus(module, package, purpose, "broken", f"{type(e).__name__}: {e}", culprit)
    except Exception as e:  # noqa: BLE001 - 任何导入失败都要报出来
        return DepStatus(module, package, purpose, "broken", f"{type(e).__name__}: {e}")

    # import 成功，但加载的不是 site-packages 里的那份 → 被人为顶替
    origin = getattr(mod, "__file__", "") or ""
    if origin and not _is_site_or_stdlib(origin):
        return DepStatus(
            module,
            package,
            purpose,
            "shadowed",
            f"实际加载自 {origin} —— 不是 site-packages 里的那份，"
            f"遮蔽了标准库 {_shadow_name(origin)}",
            origin,
        )
    return DepStatus(module, package, purpose, "ok", "", origin)


def probe_all() -> List[DepStatus]:
    """探测全部必需依赖"""
    return [probe_dependency(*dep) for dep in REQUIRED_DEPS]


def missing_packages() -> List[str]:
    """真的没装的依赖（pip 包名）"""
    return [s.package for s in probe_all() if s.state == "missing"]


def missing_install_hint() -> str:
    """给用户看的一行安装命令。

    必须真能跑通：
    - 用 sys.executable -m pip，保证装到**跑 lra 的那个解释器**里
      （PATH 上有多个 Python 时，裸 pip 经常装错地方）
    - PEP 668 环境自动补 --user --break-system-packages
    """
    packages = missing_packages()
    if not packages:
        return " ".join(pip_install_command(["long-run-agent"]))
    return " ".join(pip_install_command(packages))


def fix_hint_for(module: str) -> str:
    """针对某个依赖的修复指引——按"坏法"给不同的动作。

    三种坏法三种修法，给错就等于把人引到死路上：
    - missing  → 装
    - shadowed → 把顶替标准库的文件挪走（装包有用）
    - broken   → 强制重装
    """
    for dep_module, package, purpose in REQUIRED_DEPS:
        if dep_module == module:
            status = probe_dependency(dep_module, package, purpose)
            break
    else:
        return missing_install_hint()

    if status.state == "shadowed":
        return "把上面点名的文件改名或移出工作目录（装包无用）"
    if status.state == "missing":
        return " ".join(pip_install_command([status.package]))
    if status.state == "broken":
        return " ".join(pip_install_command(["--force-reinstall", status.package]))
    return " ".join(pip_install_command([status.package]))


# ---------- 修复 ----------


def install_missing(dry_run: bool = False, timeout: int = 180) -> Dict[str, object]:
    """装上缺失的依赖。

    只装 state == "missing" 的：shadowed / broken 装包没用，
    得先把那个顶替标准库的文件挪走（doctor 会给出具体是哪个文件）。
    """
    statuses = probe_all()
    missing = [s for s in statuses if s.state == "missing"]
    # 同一个遮蔽文件会连累多个依赖（jinja2 / filelock 都被 inspect.py 顶掉），
    # 报一遍就够，重复的只会让人以为有多个问题
    unfixable = list(dict.fromkeys(s.detail for s in statuses if s.state in ("shadowed", "broken")))
    result: Dict[str, object] = {
        "ok": True,
        "installed": [],
        "failed": "",
        "command": "",
        "unfixable": unfixable,
    }

    if not missing:
        return result

    packages = sorted({s.package for s in missing})
    cmd = pip_install_command(packages)
    result["command"] = " ".join(cmd)

    if dry_run:
        return result

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        result["ok"] = False
        result["failed"] = f"{type(e).__name__}: {e}"
        return result

    if proc.returncode != 0:
        result["ok"] = False
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        result["failed"] = "\n".join(tail[-8:]) or f"pip 退出码 {proc.returncode}"
        return result

    result["installed"] = packages
    return result
