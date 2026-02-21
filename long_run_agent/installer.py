#!/usr/bin/env python3
"""
LRA 安装初始化向导 v2.0.3
现代化终端 UI 设计
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime

# ============== 终端 UI 工具 ==============

class Color:
    """ANSI 颜色支持"""
    # 检测是否支持颜色
    SUPPORTS_COLOR = (
        hasattr(sys.stdout, 'isatty') and 
        sys.stdout.isatty() and 
        os.environ.get('TERM') != 'dumb'
    )
    
    # 颜色代码
    RESET = '\033[0m' if SUPPORTS_COLOR else ''
    BOLD = '\033[1m' if SUPPORTS_COLOR else ''
    DIM = '\033[2m' if SUPPORTS_COLOR else ''
    
    GREEN = '\033[32m' if SUPPORTS_COLOR else ''
    BLUE = '\033[34m' if SUPPORTS_COLOR else ''
    YELLOW = '\033[33m' if SUPPORTS_COLOR else ''
    RED = '\033[31m' if SUPPORTS_COLOR else ''
    CYAN = '\033[36m' if SUPPORTS_COLOR else ''
    WHITE = '\033[37m' if SUPPORTS_COLOR else ''
    MAGENTA = '\033[35m' if SUPPORTS_COLOR else ''
    
    # 背景色
    BG_GREEN = '\033[42m' if SUPPORTS_COLOR else ''
    BG_BLUE = '\033[44m' if SUPPORTS_COLOR else ''


class UI:
    """终端 UI 组件"""
    
    BOX_H = '─'
    BOX_V = '│'
    BOX_TL = '╭'
    BOX_TR = '╮'
    BOX_BL = '╰'
    BOX_BR = '╯'
    
    @classmethod
    def clear_screen(cls):
        """清屏"""
        if Color.SUPPORTS_COLOR:
            print('\033[2J\033[H', end='')
    
    @classmethod
    def box(cls, title: str = "", content: str = "", style: str = "default") -> str:
        """绘制带边框的内容框"""
        lines = content.split('\n') if content else []
        width = max(60, max(len(line) for line in lines) + 4 if lines else 60)
        width = max(width, len(title) + 4 if title else 60)
        
        # 边框颜色
        if style == "success":
            border_color = Color.GREEN
        elif style == "warning":
            border_color = Color.YELLOW
        elif style == "info":
            border_color = Color.CYAN
        elif style == "primary":
            border_color = Color.BLUE
        else:
            border_color = Color.WHITE
        
        result = []
        
        # 顶部边框
        if title:
            title_pad = (width - len(title) - 2) // 2
            top = f"{border_color}{cls.BOX_TL}{cls.BOX_H * title_pad}{Color.RESET} {Color.BOLD}{title}{Color.RESET} {border_color}{cls.BOX_H * (width - title_pad - len(title) - 3)}{cls.BOX_TR}{Color.RESET}"
        else:
            top = f"{border_color}{cls.BOX_TL}{cls.BOX_H * (width - 2)}{cls.BOX_TR}{Color.RESET}"
        result.append(top)
        
        # 内容
        for line in lines:
            padded = f"  {line}"
            padding = width - len(padded) - 1
            result.append(f"{border_color}{cls.BOX_V}{Color.RESET}{padded}{' ' * padding}{border_color}{cls.BOX_V}{Color.RESET}")
        
        # 如果没有内容，添加空行
        if not lines:
            result.append(f"{border_color}{cls.BOX_V}{Color.RESET}{' ' * (width - 2)}{border_color}{cls.BOX_V}{Color.RESET}")
        
        # 底部边框
        result.append(f"{border_color}{cls.BOX_BL}{cls.BOX_H * (width - 2)}{cls.BOX_BR}{Color.RESET}")
        
        return '\n'.join(result)
    
    @classmethod
    def title(cls, text: str) -> str:
        """大标题"""
        return f"\n{Color.BOLD}{Color.CYAN}{text}{Color.RESET}\n"
    
    @classmethod
    def subtitle(cls, text: str) -> str:
        """副标题"""
        return f"{Color.BOLD}{Color.WHITE}{text}{Color.RESET}"
    
    @classmethod
    def success(cls, text: str) -> str:
        """成功信息"""
        return f"{Color.GREEN}✅ {text}{Color.RESET}"
    
    @classmethod
    def warning(cls, text: str) -> str:
        """警告信息"""
        return f"{Color.YELLOW}⚠️  {text}{Color.RESET}"
    
    @classmethod
    def error(cls, text: str) -> str:
        """错误信息"""
        return f"{Color.RED}❌ {text}{Color.RESET}"
    
    @classmethod
    def info(cls, text: str) -> str:
        """普通信息"""
        return f"{Color.BLUE}ℹ️  {text}{Color.RESET}"
    
    @classmethod
    def dim(cls, text: str) -> str:
        """灰色文字"""
        return f"{Color.DIM}{text}{Color.RESET}"
    
    @classmethod
    def highlight(cls, text: str) -> str:
        """高亮文字"""
        return f"{Color.BOLD}{Color.GREEN}{text}{Color.RESET}"
    
    @classmethod
    def code(cls, text: str) -> str:
        """代码/命令样式"""
        return f"{Color.CYAN}`{text}`{Color.RESET}"
    
    @classmethod
    def menu_item(cls, index: int, text: str, selected: bool = False, default: bool = False) -> str:
        """菜单项"""
        if selected:
            return f"    {Color.GREEN}→{Color.RESET}  {Color.BOLD}{Color.GREEN}{index}.{text}{Color.RESET} {Color.DIM}(默认){Color.RESET}" if default else f"    {Color.GREEN}→{Color.RESET}  {Color.BOLD}{Color.GREEN}{index}.{text}{Color.RESET}"
        else:
            return f"       {index}.{text} {Color.DIM}(默认){Color.RESET}" if default else f"       {index}.{text}"
    
    @classmethod
    def divider(cls, char: str = "─", color: str = Color.DIM) -> str:
        """分隔线"""
        width = 60
        return f"{color}{char * width}{Color.RESET}"
    
    @classmethod
    def progress(cls, text: str) -> str:
        """进度提示"""
        return f"{Color.CYAN}⏳ {text}{Color.RESET}"


# ============== 版本信息 ==============

VERSION = "2.0.3"

# ============== 多语言配置 ==============

LANGUAGES = {
    "zh": {
        "app_name": "LRA - Long-Running Agent",
        "tagline": "一个强大的长时 AI Agent 任务管理框架",
        
        "lang_title": "语言选择",
        "lang_prompt": "请选择语言",
        "lang_zh": "中文",
        "lang_en": "English",
        "lang_default": "(默认)",
        "lang_hint": "输入数字或按回车选择默认",
        
        "path_title": "PATH 配置",
        "path_desc": "自动注册 lra 到系统 PATH 后，可在任意目录执行命令",
        "path_supported": "支持系统: macOS / Linux / Windows",
        "path_prompt": "是否自动配置 PATH?",
        "path_yes": "是，自动配置",
        "path_no": "否，手动配置",
        "path_configuring": "正在配置 PATH...",
        "path_success": "PATH 配置成功！",
        "path_failed": "权限不足，需要手动配置",
        "path_manual_title": "手动配置指南",
        "path_manual_hint": "将以下路径添加到系统 PATH",
        "path_manual_step1": "打开终端配置文件 (~/.zshrc 或 ~/.bashrc)",
        "path_manual_step2": "添加以下内容",
        "path_manual_step3": "执行 source ~/.zshrc 生效",
        
        "success_title": "安装完成",
        "success_message": "LRA 已准备就绪！",
        "success_next": "下一步",
        "success_step1": "运行 source ~/.zshrc 或重新打开终端",
        "success_step2": "运行 lra --help 查看所有命令",
        "success_step3": "在项目目录运行 lra project create --name \"项目名\"",
        
        "ai_title": "AI Agent 引导提示词",
        "ai_copy_hint": "👇 复制以下内容给 AI Agent",
        "ai_commands": "核心命令",
        "ai_usage": "使用方式",
        "ai_best_practice": "最佳实践",
        "ai_tools": "支持的工具",
        
        "log_saved": "安装日志",
    },
    "en": {
        "app_name": "LRA - Long-Running Agent",
        "tagline": "A powerful framework for managing long-running AI Agent tasks",
        
        "lang_title": "Language Selection",
        "lang_prompt": "Select Language",
        "lang_zh": "中文",
        "lang_en": "English",
        "lang_default": "(default)",
        "lang_hint": "Enter number or press Enter for default",
        
        "path_title": "PATH Configuration",
        "path_desc": "Register lra to PATH to run commands from anywhere",
        "path_supported": "Supported: macOS / Linux / Windows",
        "path_prompt": "Auto-configure PATH?",
        "path_yes": "Yes, auto configure",
        "path_no": "No, manual setup",
        "path_configuring": "Configuring PATH...",
        "path_success": "PATH configured successfully!",
        "path_failed": "Permission denied, manual setup required",
        "path_manual_title": "Manual Setup Guide",
        "path_manual_hint": "Add the following path to system PATH",
        "path_manual_step1": "Open shell config (~/.zshrc or ~/.bashrc)",
        "path_manual_step2": "Add the following line",
        "path_manual_step3": "Run source ~/.zshrc to apply",
        
        "success_title": "Installation Complete",
        "success_message": "LRA is ready to use!",
        "success_next": "Next Steps",
        "success_step1": "Run source ~/.zshrc or restart terminal",
        "success_step2": "Run lra --help to see all commands",
        "success_step3": "In project directory: lra project create --name \"MyProject\"",
        
        "ai_title": "AI Agent Prompt",
        "ai_copy_hint": "👇 Copy below to your AI Agent",
        "ai_commands": "Core Commands",
        "ai_usage": "How to Use",
        "ai_best_practice": "Best Practices",
        "ai_tools": "Supported Tools",
        
        "log_saved": "Installation Log",
    }
}

# AI 提示词模板
AI_PROMPTS = {
    "zh": """
你现在可以使用 LRA 工具来管理长期开发任务。

## 核心命令

| 命令 | 说明 |
|------|------|
| `lra version` | 查看版本 |
| `lra project create --name "项目名"` | 初始化项目 |
| `lra feature create "功能名"` | 创建功能 |
| `lra feature list` | 查看功能列表 |
| `lra feature status <id> --set <状态>` | 更新状态 |
| `lra stats` | 项目统计 |

## 使用方式

1. 在项目目录运行: `lra project create --name "我的项目"`
2. 这会创建 `.long-run-agent/` 目录
3. 每次工作时，先读取 `.long-run-agent/feature_list.json`
4. 完成功能后更新状态: `lra feature status <id> --set completed`

## 最佳实践

- 每个会话开始时先读取 feature_list.json
- 开发前先创建 Feature 并设置优先级
- 完成后及时更新状态
- 定期运行 lra stats 查看进度

## 支持的 AI 工具

OpenClaw, OpenCode, Claude Code, Cursor, Trae, ChatGPT, Claude, Gemini, 通义千问, 讯飞星火 等
""",
    "en": """
You can now use LRA to manage long-running development tasks.

## Core Commands

| Command | Description |
|---------|-------------|
| `lra version` | Show version |
| `lra project create --name "MyProject"` | Initialize project |
| `lra feature create "Feature name"` | Create feature |
| `lra feature list` | List features |
| `lra feature status <id> --set <status>` | Update status |
| `lra stats` | Project statistics |

## How to Use

1. In project directory: `lra project create --name "My Project"`
2. This creates `.long-run-agent/` directory
3. Read `.long-run-agent/feature_list.json` at each session start
4. Update status when done: `lra feature status <id> --set completed`

## Best Practices

- Read feature_list.json at start of each session
- Create features with priority before development
- Update status promptly after completion
- Run lra stats regularly to track progress

## Supported AI Tools

OpenClaw, OpenCode, Claude Code, Cursor, Trae, ChatGPT, Claude, Gemini, Qwen, iFlytek Spark, etc.
"""
}


class LRAInstaller:
    """LRA 安装向导"""
    
    def __init__(self):
        self.system = platform.system()
        self.lang = "zh"
        self.lra_bin_path = self._get_lra_bin_path()
        self.log_path = self._get_log_path()
        self.T = LANGUAGES["zh"]  # 当前语言的文本
    
    def _get_lra_bin_path(self) -> str:
        """获取 lra 可执行文件路径"""
        home = Path.home()
        if self.system == "Windows":
            # 尝试多个可能的 Python 路径
            for py_ver in ["312", "311", "310", "39", "38"]:
                path = home / "AppData" / "Local" / "Programs" / "Python" / f"Python{py_ver}" / "Scripts"
                if path.exists():
                    return str(path)
            return str(home / "AppData" / "Roaming" / "Python" / "Python39" / "Scripts")
        else:
            # macOS/Linux
            for py_ver in ["3.9", "3.10", "3.11", "3.12"]:
                path = home / "Library" / "Python" / py_ver / "bin"
                if path.exists():
                    return str(path)
            return str(home / "Library" / "Python" / "3.9" / "bin")
    
    def _get_log_path(self) -> str:
        """获取日志路径"""
        log_dir = Path.home() / ".lra"
        log_dir.mkdir(exist_ok=True)
        return str(log_dir / "install.log")
    
    def _input(self, prompt: str, default: str = "") -> str:
        """获取用户输入"""
        try:
            result = input(f"{prompt}: ").strip()
            return result if result else default
        except (EOFError, KeyboardInterrupt):
            print()
            return default
    
    def show_welcome(self):
        """显示欢迎界面"""
        print()
        print(UI.box(
            "LRA Installer",
            f"""
{Color.BOLD}{Color.CYAN}     ██████╗  █████╗ ██████╗ ██╗      ██████╗ ██████╗ ██████╗ ███████╗{Color.RESET}
{Color.BOLD}{Color.CYAN}     ██╔══██╗██╔══██╗██╔══██╗██║     ██╔════╝██╔═══██╗██╔══██╗██╔════╝{Color.RESET}
{Color.BOLD}{Color.CYAN}     ██║  ██║███████║██████╔╝██║     ██║     ██║   ██║██║  ██║█████╗  {Color.RESET}
{Color.BOLD}{Color.CYAN}     ██║  ██║██╔══██║██╔══██╗██║     ██║     ██║   ██║██║  ██║██╔══╝  {Color.RESET}
{Color.BOLD}{Color.CYAN}     ██████╔╝██║  ██║██║  ██║███████╗╚██████╗╚██████╔╝██████╔╝███████╗{Color.RESET}
{Color.BOLD}{Color.CYAN}     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝{Color.RESET}

{Color.DIM}                    Long-Running Agent for AI Development{Color.RESET}
{Color.DIM}                           Version {VERSION}{Color.RESET}

""",
            style="primary"
        ))
        print()
    
    def select_language(self):
        """语言选择界面"""
        self.T = LANGUAGES["zh"]  # 先用中文显示选项
        
        content = f"""
{Color.DIM}──────────────────────────────────────────────────────────────{Color.RESET}

{UI.subtitle('🌐 ' + self.T['lang_prompt'])}

{UI.menu_item(1, self.T['lang_zh'], selected=True, default=True)}
{UI.menu_item(2, self.T['lang_en'])}

{Color.DIM}──────────────────────────────────────────────────────────────{Color.RESET}

{Color.DIM}💡 {self.T['lang_hint']}{Color.RESET}
"""
        print(UI.box(self.T['lang_title'], content, style="info"))
        
        choice = self._input(f"{Color.CYAN}❯{Color.RESET} 选择", "1")
        
        if choice == "2":
            self.lang = "en"
        else:
            self.lang = "zh"
        
        self.T = LANGUAGES[self.lang]
        print()
        print(UI.success(f"{'已选择中文' if self.lang == 'zh' else 'English selected'}"))
        print()
    
    def configure_path(self) -> bool:
        """PATH 配置界面"""
        content = f"""
{Color.DIM}──────────────────────────────────────────────────────────────{Color.RESET}

{UI.info(self.T['path_desc'])}
{Color.DIM}{self.T['path_supported']}{Color.RESET}

{Color.DIM}──────────────────────────────────────────────────────────────{Color.RESET}

{UI.subtitle('🔧 ' + self.T['path_prompt'])}

{UI.menu_item(1, self.T['path_yes'], selected=True, default=True)}
{UI.menu_item(2, self.T['path_no'])}

{Color.DIM}──────────────────────────────────────────────────────────────{Color.RESET}

{Color.DIM}💡 按回车选择默认选项{Color.RESET}
"""
        print(UI.box(self.T['path_title'], content, style="info"))
        
        choice = self._input(f"{Color.CYAN}❯{Color.RESET} 选择", "1")
        
        if choice in ["2", "n", "no"]:
            self._show_manual_path_guide()
            return False
        
        return self._register_path()
    
    def _register_path(self) -> bool:
        """注册 PATH"""
        print()
        print(UI.progress(self.T['path_configuring']))
        
        if self.system == "Windows":
            result = self._register_path_windows()
        else:
            result = self._register_path_unix()
        
        if result:
            print()
            print(UI.success(self.T['path_success']))
        return result
    
    def _register_path_unix(self) -> bool:
        """Unix 系统注册 PATH"""
        shell_config = self._get_shell_config()
        path_entry = f'export PATH="$PATH:{self.lra_bin_path}"'
        
        try:
            # 检查是否已存在
            if shell_config.exists():
                content = shell_config.read_text()
                if self.lra_bin_path in content:
                    return True
            
            # 添加到配置文件
            with open(shell_config, "a") as f:
                f.write(f"\n# LRA - Long-Running Agent\n")
                f.write(f"{path_entry}\n")
            
            return True
        
        except PermissionError:
            print()
            print(UI.warning(self.T['path_failed']))
            self._show_manual_path_guide()
            return False
    
    def _register_path_windows(self) -> bool:
        """Windows 系统注册 PATH"""
        try:
            current_path = os.environ.get("PATH", "")
            if self.lra_bin_path not in current_path:
                subprocess.run(
                    ["setx", "PATH", f"{current_path};{self.lra_bin_path}"],
                    check=True,
                    capture_output=True
                )
            return True
        except (subprocess.CalledProcessError, PermissionError):
            print()
            print(UI.warning(self.T['path_failed']))
            self._show_manual_path_guide()
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
        content = f"""
{UI.info(self.T['path_manual_hint'])}

{Color.CYAN}  {self.lra_bin_path}{Color.RESET}

{Color.DIM}步骤:{Color.RESET}
  1. {self.T['path_manual_step1']}
  2. {self.T['path_manual_step2']}
     {Color.GREEN}export PATH=\"$PATH:{self.lra_bin_path}\"{Color.RESET}
  3. {self.T['path_manual_step3']}
"""
        print()
        print(UI.box(self.T['path_manual_title'], content, style="warning"))
    
    def show_success(self, path_configured: bool):
        """显示成功界面"""
        content = f"""
{Color.GREEN}     🎉 {self.T['success_message']}{Color.RESET}

{Color.DIM}──────────────────────────────────────────────────────────────{Color.RESET}

{UI.subtitle('📌 ' + self.T['success_next'])}

     1️⃣  {self.T['success_step1']}
     2️⃣  {UI.code('lra --help')} {Color.DIM}- {self.T['success_step2']}{Color.RESET}
     3️⃣  {UI.code('lra project create --name "项目名"')} {Color.DIM}- 初始化项目{Color.RESET}
"""
        print()
        print(UI.box(self.T['success_title'], content, style="success"))
    
    def show_ai_prompt(self):
        """显示 AI 引导提示词"""
        prompt = AI_PROMPTS[self.lang]
        
        print()
        print(UI.divider())
        print()
        print(UI.subtitle(f"🤖 {self.T['ai_title']}"))
        print()
        print(f"{Color.DIM}{self.T['ai_copy_hint']}{Color.RESET}")
        print()
        print(UI.box("", prompt.strip(), style="info"))
        print()
        print(UI.divider())
    
    def save_log(self, path_configured: bool):
        """保存安装日志"""
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
            print()
            print(UI.dim(f"📄 {self.T['log_saved']}: {self.log_path}"))
        except Exception:
            pass
    
    def run(self):
        """运行安装向导"""
        # 清屏
        # UI.clear_screen()
        
        # 欢迎界面
        self.show_welcome()
        
        # 语言选择
        self.select_language()
        
        # PATH 配置
        path_configured = self.configure_path()
        
        # 保存日志
        self.save_log(path_configured)
        
        # 成功界面
        self.show_success(path_configured)
        
        # AI 提示词
        self.show_ai_prompt()
        
        print()


def main():
    """主入口"""
    try:
        installer = LRAInstaller()
        installer.run()
    except KeyboardInterrupt:
        print("\n\n安装已取消。")
        sys.exit(1)


if __name__ == "__main__":
    main()
