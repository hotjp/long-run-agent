#!/usr/bin/env python3
"""
LRA 安装初始化向导
支持语言选择、PATH 配置、AI 引导提示
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional

# 版本信息
VERSION = "2.0.1"

# ============== 多语言配置 ==============

LANGUAGES = {
    "zh": {
        # 交互提示
        "welcome": """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     📦 LRA - Long-Running Agent v{version}                    ║
║                                                              ║
║     一个强大的长时 AI Agent 任务管理框架                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""",
        "lang_select": """
┌──────────────────────────────────────────────────────────────┐
│  🌐 请选择语言 / Select Language                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│    1. 中文（默认）                                            │
│    2. English                                                │
│                                                              │
│  请输入选择 [1/2]，回车默认选择中文:                           │
└──────────────────────────────────────────────────────────────┘
""",
        "lang_prompt": "请输入选择",
        "path_title": """
┌──────────────────────────────────────────────────────────────┐
│  🔧 PATH 环境变量配置                                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  自动注册 lra 到 PATH 后，可在任意目录执行命令。              │
│                                                              │
│  支持系统: macOS / Linux / Windows                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "path_prompt": "是否自动注册 lra 到 PATH?",
        "path_options": "[Y/n]",
        "path_yes": "是（默认）",
        "path_no": "否",
        "path_registering": "正在配置 PATH...",
        "path_success": "✅ PATH 配置成功！",
        "path_manual": """
┌──────────────────────────────────────────────────────────────┐
│  📋 手动配置 PATH 指南                                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  请将以下路径添加到系统 PATH：                                │
│                                                              │
│  {path}                                                      │
│                                                              │
│  方法：                                                      │
│  1. 打开终端配置文件（~/.zshrc 或 ~/.bashrc）                 │
│  2. 添加: export PATH="$PATH:{path}"                         │
│  3. 执行: source ~/.zshrc                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "path_windows_manual": """
┌──────────────────────────────────────────────────────────────┐
│  📋 Windows 手动配置 PATH 指南                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 右键「此电脑」→「属性」                                   │
│  2. 「高级系统设置」→「环境变量」                             │
│  3. 在「系统变量」中找到 Path →「编辑」                       │
│  4.「新建」→ 添加路径: {path}                                 │
│  5. 确定保存，重启终端                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "path_no_permission": """
❌ 权限不足，无法自动配置 PATH

解决方案：
• macOS/Linux: 请以 sudo 权限重新运行: sudo lra init
• 或按照上方手动配置指南操作
""",
        "success": """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🎉 LRA 安装初始化完成！                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""",
        "ai_prompt_title": """
┌──────────────────────────────────────────────────────────────┐
│  🤖 AI Agent 引导提示词（可直接复制使用）                     │
├──────────────────────────────────────────────────────────────┤
""",
        "ai_prompt": """
你现在可以使用 LRA 工具来管理长期开发任务。

## 核心命令

| 命令 | 说明 |
|------|------|
| lra version | 查看版本 |
| lra project create --name "项目名" | 初始化项目 |
| lra feature create "功能名" | 创建功能 |
| lra feature list | 查看功能列表 |
| lra feature status <id> --set <状态> | 更新状态 |
| lra stats | 项目统计 |

## 使用方式

1. 在项目目录运行: lra project create --name "我的项目"
2. 这会创建 .long-run-agent/ 目录，包含 feature_list.json
3. 每次工作时，先读取 .long-run-agent/feature_list.json 了解进度
4. 完成功能后更新状态: lra feature status <id> --set completed

## 最佳实践

- 每个会话开始时先读取 feature_list.json
- 开发前先创建 Feature 并设置优先级
- 完成后及时更新状态
- 定期运行 lra stats 查看整体进度

## 支持的 AI 工具

OpenClaw, OpenCode, Claude Code, Cursor, Trae, ChatGPT, Claude, Gemini, 通义千问, 讯飞星火 等
""",
        "next_steps": """
┌──────────────────────────────────────────────────────────────┐
│  📌 下一步                                                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 重新打开终端（或运行 source ~/.zshrc）                    │
│  2. 运行: lra --help 查看所有命令                             │
│  3. 在项目目录运行: lra project create --name "我的项目"      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "log_saved": "安装日志已保存到",
    },
    "en": {
        "welcome": """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     📦 LRA - Long-Running Agent v{version}                    ║
║                                                              ║
║     A powerful framework for managing long-running AI tasks  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""",
        "lang_select": """
┌──────────────────────────────────────────────────────────────┐
│  🌐 Select Language                                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│    1. 中文                                                   │
│    2. English (Default)                                      │
│                                                              │
│  Enter choice [1/2], press Enter for English:                │
└──────────────────────────────────────────────────────────────┘
""",
        "lang_prompt": "Enter choice",
        "path_title": """
┌──────────────────────────────────────────────────────────────┐
│  🔧 PATH Environment Configuration                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Register lra to PATH to run commands from anywhere.         │
│                                                              │
│  Supported: macOS / Linux / Windows                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "path_prompt": "Register lra to PATH?",
        "path_options": "[Y/n]",
        "path_yes": "Yes (default)",
        "path_no": "No",
        "path_registering": "Configuring PATH...",
        "path_success": "✅ PATH configured successfully!",
        "path_manual": """
┌──────────────────────────────────────────────────────────────┐
│  📋 Manual PATH Configuration Guide                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Add the following path to your system PATH:                 │
│                                                              │
│  {path}                                                      │
│                                                              │
│  Steps:                                                      │
│  1. Open your shell config (~/.zshrc or ~/.bashrc)           │
│  2. Add: export PATH="$PATH:{path}"                          │
│  3. Run: source ~/.zshrc                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "path_windows_manual": """
┌──────────────────────────────────────────────────────────────┐
│  📋 Windows Manual PATH Configuration                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Right-click "This PC" → "Properties"                     │
│  2. "Advanced system settings" → "Environment Variables"     │
│  3. Find "Path" in System variables → "Edit"                 │
│  4. "New" → Add path: {path}                                 │
│  5. Save and restart terminal                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "path_no_permission": """
❌ Permission denied, cannot configure PATH automatically

Solution:
• macOS/Linux: Run with sudo: sudo lra init
• Or follow the manual configuration guide above
""",
        "success": """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🎉 LRA Installation Complete!                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""",
        "ai_prompt_title": """
┌──────────────────────────────────────────────────────────────┐
│  🤖 AI Agent Prompt (Ready to Copy)                          │
├──────────────────────────────────────────────────────────────┤
""",
        "ai_prompt": """
You can now use LRA to manage long-running development tasks.

## Core Commands

| Command | Description |
|---------|-------------|
| lra version | Show version |
| lra project create --name "MyProject" | Initialize project |
| lra feature create "Feature name" | Create feature |
| lra feature list | List features |
| lra feature status <id> --set <status> | Update status |
| lra stats | Project statistics |

## How to Use

1. In your project directory, run: lra project create --name "My Project"
2. This creates .long-run-agent/ directory with feature_list.json
3. Read .long-run-agent/feature_list.json at the start of each session
4. Update status when done: lra feature status <id> --set completed

## Best Practices

- Read feature_list.json at the start of each session
- Create features with priority before development
- Update status promptly after completion
- Run lra stats regularly to track progress

## Supported AI Tools

OpenClaw, OpenCode, Claude Code, Cursor, Trae, ChatGPT, Claude, Gemini, Qwen, iFlytek Spark, etc.
""",
        "next_steps": """
┌──────────────────────────────────────────────────────────────┐
│  📌 Next Steps                                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Restart terminal (or run: source ~/.zshrc)               │
│  2. Run: lra --help to see all commands                      │
│  3. In your project: lra project create --name "My Project"  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""",
        "log_saved": "Installation log saved to",
    }
}


class LRAInstaller:
    """LRA 安装向导"""

    def __init__(self):
        self.system = platform.system()
        self.lang = "zh"  # 默认中文
        self.lra_bin_path = self._get_lra_bin_path()
        self.log_path = self._get_log_path()

    def _get_lra_bin_path(self) -> str:
        """获取 lra 可执行文件路径"""
        # 用户安装路径
        home = Path.home()
        if self.system == "Windows":
            return str(home / "AppData" / "Local" / "Programs" / "Python" / "Python39" / "Scripts")
        else:
            return str(home / "Library" / "Python" / "3.9" / "bin")

    def _get_log_path(self) -> str:
        """获取日志路径"""
        log_dir = Path.home() / ".lra"
        log_dir.mkdir(exist_ok=True)
        return str(log_dir / "install.log")

    def _print(self, key: str, **kwargs):
        """打印多语言文本"""
        text = LANGUAGES[self.lang].get(key, key)
        print(text.format(version=VERSION, **kwargs))

    def _input(self, prompt: str, default: str = "") -> str:
        """获取用户输入"""
        try:
            result = input(prompt).strip()
            return result if result else default
        except EOFError:
            return default

    def select_language(self):
        """语言选择"""
        print(LANGUAGES["zh"]["lang_select"])
        choice = self._input("请输入选择 [1/2]: ", "1")

        if choice == "2":
            self.lang = "en"
        else:
            self.lang = "zh"

    def configure_path(self) -> bool:
        """配置 PATH"""
        self._print("path_title")

        # 显示选项
        default_text = LANGUAGES[self.lang]["path_yes"]
        print(f"\n  {LANGUAGES[self.lang]['path_prompt']}")
        print(f"  [{LANGUAGES[self.lang]['path_options']}] {default_text}")

        choice = self._input("> ", "y").lower()

        if choice in ["n", "no", "2"]:
            self._show_manual_path_guide()
            return False

        return self._register_path()

    def _register_path(self) -> bool:
        """注册 PATH"""
        print(f"\n  {LANGUAGES[self.lang]['path_registering']}")

        if self.system == "Windows":
            return self._register_path_windows()
        else:
            return self._register_path_unix()

    def _register_path_unix(self) -> bool:
        """Unix 系统注册 PATH"""
        shell_config = self._get_shell_config()
        path_entry = f'export PATH="$PATH:{self.lra_bin_path}"'

        try:
            # 检查是否已存在
            if shell_config.exists():
                content = shell_config.read_text()
                if self.lra_bin_path in content:
                    print(f"\n  {LANGUAGES[self.lang]['path_success']}")
                    return True

            # 添加到配置文件
            with open(shell_config, "a") as f:
                f.write(f"\n# LRA - Long-Running Agent\n")
                f.write(f"{path_entry}\n")

            print(f"\n  {LANGUAGES[self.lang]['path_success']}")
            print(f"  已添加到: {shell_config}")
            return True

        except PermissionError:
            print(LANGUAGES[self.lang]["path_no_permission"])
            return False

    def _register_path_windows(self) -> bool:
        """Windows 系统注册 PATH"""
        try:
            # 使用 setx 命令
            current_path = os.environ.get("PATH", "")
            if self.lra_bin_path not in current_path:
                subprocess.run(
                    ["setx", "PATH", f"{current_path};{self.lra_bin_path}"],
                    check=True,
                    capture_output=True
                )
            print(f"\n  {LANGUAGES[self.lang]['path_success']}")
            return True
        except (subprocess.CalledProcessError, PermissionError):
            print(LANGUAGES[self.lang]["path_no_permission"])
            self._print("path_windows_manual", path=self.lra_bin_path)
            return False

    def _get_shell_config(self) -> Path:
        """获取 shell 配置文件路径"""
        shell = os.environ.get("SHELL", "/bin/zsh")

        if "zsh" in shell:
            return Path.home() / ".zshrc"
        elif "bash" in shell:
            return Path.home() / ".bashrc"
        else:
            return Path.home() / ".profile"

    def _show_manual_path_guide(self):
        """显示手动配置指南"""
        if self.system == "Windows":
            self._print("path_windows_manual", path=self.lra_bin_path)
        else:
            self._print("path_manual", path=self.lra_bin_path)

    def show_ai_prompt(self):
        """显示 AI 引导提示词"""
        self._print("ai_prompt_title")
        print(LANGUAGES[self.lang]["ai_prompt"])

    def save_log(self, path_configured: bool):
        """保存安装日志"""
        from datetime import datetime

        log_data = f"""LRA Installation Log
====================
Time: {datetime.now().isoformat()}
Version: {VERSION}
System: {self.system}
Language: {self.lang}
PATH Configured: {path_configured}
LRA Binary Path: {self.lra_bin_path}
Shell Config: {self._get_shell_config()}
"""
        try:
            with open(self.log_path, "w") as f:
                f.write(log_data)
        except Exception:
            pass

    def run(self):
        """运行安装向导"""
        # 欢迎
        self._print("welcome")

        # 语言选择
        self.select_language()

        # PATH 配置
        path_configured = self.configure_path()

        # 保存日志
        self.save_log(path_configured)

        # 成功提示
        self._print("success")

        # AI 提示词
        self.show_ai_prompt()

        # 下一步
        self._print("next_steps")

        # 日志路径
        print(f"\n  📄 {LANGUAGES[self.lang]['log_saved']}: {self.log_path}\n")


def main():
    """主入口"""
    installer = LRAInstaller()
    installer.run()


if __name__ == "__main__":
    main()
