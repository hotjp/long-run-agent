#!/usr/bin/env python3
"""
LRA 安装初始化向导 v2.0.6
简洁现代风格 - 无边框 + 方向键交互
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Optional

# Windows 兼容
IS_WINDOWS = platform.system() == "Windows"
if not IS_WINDOWS:
    import tty
    import termios

# ============== 终端检测 ==============

def get_terminal_width() -> int:
    """获取终端宽度"""
    try:
        return min(os.get_terminal_size().columns, 60)
    except:
        return 60

def supports_color() -> bool:
    """检测是否支持颜色"""
    return (
        hasattr(sys.stdout, 'isatty') and 
        sys.stdout.isatty() and 
        os.environ.get('TERM') != 'dumb'
    )

# ============== 颜色定义 ==============

HAS_COLOR = supports_color()

class C:
    """颜色常量"""
    RESET = '\033[0m' if HAS_COLOR else ''
    BOLD = '\033[1m' if HAS_COLOR else ''
    DIM = '\033[2m' if HAS_COLOR else ''
    GREEN = '\033[32m' if HAS_COLOR else ''
    BLUE = '\033[34m' if HAS_COLOR else ''
    YELLOW = '\033[33m' if HAS_COLOR else ''
    RED = '\033[31m' if HAS_COLOR else ''
    CYAN = '\033[36m' if HAS_COLOR else ''
    WHITE = '\033[37m' if HAS_COLOR else ''
    MAGENTA = '\033[35m' if HAS_COLOR else ''
    # 高亮背景
    BG_SELECTED = '\033[7m' if HAS_COLOR else ''  # 反色作为选中


# ============== 键盘输入处理 ==============

class KeyInput:
    """处理键盘输入，支持方向键"""
    
    # 方向键代码
    UP = '\x1b[A'
    DOWN = '\x1b[B'
    ENTER = '\r'
    ENTER_ALT = '\n'
    
    @classmethod
    def is_tty(cls) -> bool:
        """检查是否是 TTY"""
        return hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()
    
    @classmethod
    def get_key(cls) -> str:
        """获取单个按键"""
        if IS_WINDOWS:
            # Windows 使用 msvcrt
            import msvcrt
            ch = msvcrt.getch()
            if ch == b'\xe0':  # 方向键前缀
                ch = msvcrt.getch()
                if ch == b'H':
                    return cls.UP
                elif ch == b'P':
                    return cls.DOWN
            return ch.decode('utf-8', errors='ignore')
        
        # Unix/Linux/macOS
        if not cls.is_tty():
            # 非 TTY 环境，使用普通输入
            return input() or cls.ENTER
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            
            # 处理方向键 (ESC [ A/B)
            if ch == '\x1b':
                ch += sys.stdin.read(2)
            
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    @classmethod
    def select_option(cls, options: List[str], default: int = 0, 
                      prompt: str = "选择") -> int:
        """
        交互式选项选择（仅选项区域）
        返回选中的索引
        """
        # 非 TTY 环境，使用简单输入
        if not cls.is_tty():
            while True:
                try:
                    choice = input(f"  请输入选择 [1-{len(options)}]: ").strip()
                    if not choice:
                        return default
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        return idx
                except (ValueError, EOFError):
                    return default
        
        selected = default
        width = get_terminal_width()
        options_lines = len(options) + 2  # 选项 + 空行 + 提示
        
        # 首次绘制选项
        cls._draw_options(options, selected, width)
        
        while True:
            key = cls.get_key()
            
            if key == cls.UP:
                selected = (selected - 1) % len(options)
            elif key == cls.DOWN:
                selected = (selected + 1) % len(options)
            elif key in [cls.ENTER, cls.ENTER_ALT]:
                return selected
            elif key in ['1', '2', '3', '4', '5']:
                idx = int(key) - 1
                if 0 <= idx < len(options):
                    return idx
            elif key.lower() == 'q':
                raise KeyboardInterrupt()
            
            # 重绘选项区域
            if HAS_COLOR:
                print(f"\033[{options_lines}A\033[J", end='')
                cls._draw_options(options, selected, width)
    
    @classmethod
    def _draw_options(cls, options: List[str], selected: int, width: int):
        """绘制选项"""
        for i, opt in enumerate(options):
            display_opt = opt[:width-8] if len(opt) > width-8 else opt
            if i == selected:
                print(f"    {C.GREEN}➜{C.RESET}  {C.BOLD}{C.GREEN}{display_opt}{C.RESET}")
            else:
                print(f"       {display_opt}")
        
        print()
        print(f"  {C.DIM}↑↓ 切换选项  |  回车确认{C.RESET}")


# ============== UI 组件（无边框版） ==============

class UI:
    """简洁的终端 UI"""
    
    @staticmethod
    def divider(char: str = "─", width: int = 50) -> None:
        """分隔线"""
        print(f"{C.DIM}{char * width}{C.RESET}")
    
    @staticmethod
    def blank() -> None:
        """空行"""
        print()
    
    @staticmethod
    def title(text: str) -> None:
        """标题"""
        print(f"{C.BOLD}{C.CYAN}{text}{C.RESET}")
    
    @staticmethod
    def subtitle(text: str) -> None:
        """副标题"""
        print(f"  {C.BOLD}{C.WHITE}{text}{C.RESET}")
    
    @staticmethod
    def success(text: str) -> None:
        """成功信息"""
        print(f"  {C.GREEN}✅ {text}{C.RESET}")
    
    @staticmethod
    def warning(text: str) -> None:
        """警告信息"""
        print(f"  {C.YELLOW}⚠️  {text}{C.RESET}")
    
    @staticmethod
    def error(text: str) -> None:
        """错误信息"""
        print(f"  {C.RED}❌ {text}{C.RESET}")
    
    @staticmethod
    def info(text: str) -> None:
        """信息"""
        print(f"  {C.BLUE}ℹ️  {text}{C.RESET}")
    
    @staticmethod
    def code(text: str) -> str:
        """代码样式"""
        return f"{C.CYAN}{text}{C.RESET}"
    
    @staticmethod
    def dim(text: str) -> str:
        """灰色文字"""
        return f"{C.DIM}{text}{C.RESET}"
    
    @staticmethod
    def progress(text: str) -> None:
        """进度"""
        print(f"  {C.CYAN}⏳ {text}{C.RESET}")


# ============== 版本和语言配置 ==============

VERSION = "2.0.6"

LANGUAGES = {
    "zh": {
        "welcome": "欢迎使用 LRA (Long Run Agent) 安装向导",
        "version": f"版本 {VERSION}",
        "tagline": "长时 AI Agent 任务管理框架",
        
        "lang_title": "请选择语言",
        "lang_zh": "中文",
        "lang_en": "English",
        
        "path_title": "PATH 环境变量配置",
        "path_desc": "自动配置后可在任意目录使用 lra 命令",
        "path_yes": "是，自动配置 (推荐)",
        "path_no": "否，稍后手动配置",
        "path_working": "正在配置...",
        "path_success": "PATH 配置成功",
        "path_fail": "权限不足，请手动配置",
        
        "manual_title": "手动配置方法",
        "manual_step1": "打开 ~/.zshrc 或 ~/.bashrc",
        "manual_step2": "添加以下内容到文件末尾",
        "manual_step3": "运行 source ~/.zshrc 生效",
        
        "done_title": "安装完成",
        "done_msg": "LRA 已准备就绪",
        "next_title": "下一步操作",
        "next_1": "运行 source ~/.zshrc",
        "next_2": "运行 lra --help 查看命令",
        "next_3": "在项目中运行 lra project create",
        
        "ai_title": "AI Agent 提示词",
        "ai_hint": "👇 复制以下内容给 AI Agent",
        
        "log_title": "安装日志",
    },
    "en": {
        "welcome": "Welcome to LRA (Long Run Agent) Installer",
        "version": f"Version {VERSION}",
        "tagline": "Long-Running AI Agent Task Manager",
        
        "lang_title": "Select Language",
        "lang_zh": "中文",
        "lang_en": "English",
        
        "path_title": "PATH Configuration",
        "path_desc": "Configure PATH to use lra from anywhere",
        "path_yes": "Yes, auto configure (recommended)",
        "path_no": "No, manual setup later",
        "path_working": "Configuring...",
        "path_success": "PATH configured successfully",
        "path_fail": "Permission denied, please configure manually",
        
        "manual_title": "Manual Setup",
        "manual_step1": "Open ~/.zshrc or ~/.bashrc",
        "manual_step2": "Add this line to the end",
        "manual_step3": "Run source ~/.zshrc to apply",
        
        "done_title": "Installation Complete",
        "done_msg": "LRA is ready to use",
        "next_title": "Next Steps",
        "next_1": "Run source ~/.zshrc",
        "next_2": "Run lra --help for commands",
        "next_3": "Run lra project create in your project",
        
        "ai_title": "AI Agent Prompt",
        "ai_hint": "👇 Copy below to your AI Agent",
        
        "log_title": "Installation Log",
    }
}

AI_PROMPTS = {
    "zh": """你现在可以使用 LRA 管理长期开发任务。

核心命令:
  lra version                    查看版本
  lra project create --name "项目名"    初始化
  lra feature create "功能名"    创建功能
  lra feature list               查看列表
  lra feature status <id> --set completed  标记完成
  lra stats                      项目统计

使用方式:
  1. 在项目目录运行 lra project create
  2. 每次会话先读取 .long-run-agent/feature_list.json
  3. 完成后更新状态: lra feature status <id> --set completed

支持: OpenClaw, OpenCode, Claude Code, Cursor, ChatGPT 等
""",
    "en": """You can now use LRA for long-running tasks.

Core Commands:
  lra version                    Show version
  lra project create --name "MyProject"  Initialize
  lra feature create "Feature"   Create feature
  lra feature list               List features
  lra feature status <id> --set completed  Mark done
  lra stats                      Statistics

How to Use:
  1. Run lra project create in project directory
  2. Read .long-run-agent/feature_list.json at each session
  3. Update status: lra feature status <id> --set completed

Supports: OpenClaw, OpenCode, Claude Code, Cursor, ChatGPT, etc.
"""
}


# ============== 安装器 ==============

class LRAInstaller:
    """LRA 安装向导"""
    
    def __init__(self):
        self.system = platform.system()
        self.lang = "zh"
        self.T = LANGUAGES["zh"]
        self.lra_bin_path = self._get_lra_bin_path()
        self.log_path = self._get_log_path()
    
    def _get_lra_bin_path(self) -> str:
        """获取 lra 路径"""
        home = Path.home()
        if self.system == "Windows":
            for v in ["312", "311", "310", "39", "38"]:
                p = home / "AppData" / "Local" / "Programs" / "Python" / f"Python{v}" / "Scripts"
                if p.exists():
                    return str(p)
            return str(home / ".local" / "bin")
        else:
            for v in ["3.12", "3.11", "3.10", "3.9"]:
                p = home / "Library" / "Python" / v / "bin"
                if p.exists():
                    return str(p)
            return str(home / ".local" / "bin")
    
    def _get_log_path(self) -> str:
        """日志路径"""
        d = Path.home() / ".lra"
        d.mkdir(exist_ok=True)
        return str(d / "install.log")
    
    def _get_shell_config(self) -> Path:
        """Shell 配置文件"""
        shell = os.environ.get("SHELL", "/bin/zsh")
        if "zsh" in shell:
            return Path.home() / ".zshrc"
        elif "bash" in shell:
            return Path.home() / ".bashrc"
        return Path.home() / ".profile"
    
    def show_welcome(self):
        """欢迎界面"""
        UI.blank()
        # LRA ASCII Art - 简洁版
        print(f"  {C.BOLD}{C.CYAN}██╗      ██████╗  █████╗ ██████╗ {C.RESET}")
        print(f"  {C.BOLD}{C.CYAN}██║     ██╔═══██╗██╔══██╗██╔══██╗{C.RESET}")
        print(f"  {C.BOLD}{C.CYAN}██║     ██║   ██║███████║██║  ██║{C.RESET}")
        print(f"  {C.BOLD}{C.CYAN}██║     ██║   ██║██╔══██║██║  ██║{C.RESET}")
        print(f"  {C.BOLD}{C.CYAN}███████╗╚██████╔╝██║  ██║██████╔╝{C.RESET}")
        print(f"  {C.BOLD}{C.CYAN}╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ {C.RESET}")
        UI.blank()
        print(f"  {C.BOLD}{self.T['welcome']}{C.RESET}")
        print(f"  {C.DIM}{self.T['tagline']}{C.RESET}")
        print(f"  {C.DIM}{self.T['version']}{C.RESET}")
        UI.blank()
        UI.divider()
    
    def select_language(self):
        """语言选择"""
        UI.blank()
        
        options = [self.T['lang_zh'], self.T['lang_en']]
        
        # 先绘制标题（不会被清除）
        print(f"  {C.BOLD}{C.CYAN}{self.T['lang_title']}{C.RESET}")
        print()
        
        try:
            selected = KeyInput.select_option(options, default=0)
            self.lang = "en" if selected == 1 else "zh"
            self.T = LANGUAGES[self.lang]
            
            print()
            UI.success(f"{'已选择中文' if self.lang == 'zh' else 'English selected'}")
        except KeyboardInterrupt:
            self.lang = "zh"
            self.T = LANGUAGES["zh"]
        
        UI.blank()
        UI.divider()
    
    def configure_path(self) -> bool:
        """PATH 配置"""
        UI.blank()
        print(f"  {C.BOLD}{C.CYAN}{self.T['path_title']}{C.RESET}")
        UI.blank()
        UI.info(self.T['path_desc'])
        UI.blank()
        
        options = [self.T['path_yes'], self.T['path_no']]
        
        try:
            selected = KeyInput.select_option(options, default=0)
        except KeyboardInterrupt:
            selected = 0
        
        if selected == 1:
            self._show_manual_guide()
            return False
        
        return self._register_path()
    
    def _register_path(self) -> bool:
        """注册 PATH"""
        UI.blank()
        UI.progress(self.T['path_working'])
        
        if self.system == "Windows":
            result = self._register_windows()
        else:
            result = self._register_unix()
        
        UI.blank()
        if result:
            UI.success(self.T['path_success'])
        else:
            UI.warning(self.T['path_fail'])
            self._show_manual_guide()
        
        return result
    
    def _register_unix(self) -> bool:
        """Unix PATH 注册"""
        config = self._get_shell_config()
        entry = f'export PATH="$PATH:{self.lra_bin_path}"'
        
        try:
            if config.exists() and self.lra_bin_path in config.read_text():
                return True
            
            with open(config, "a") as f:
                f.write(f"\n# LRA - Long-Running Agent\n{entry}\n")
            return True
        except PermissionError:
            return False
    
    def _register_windows(self) -> bool:
        """Windows PATH 注册"""
        try:
            current = os.environ.get("PATH", "")
            if self.lra_bin_path not in current:
                subprocess.run(
                    ["setx", "PATH", f"{current};{self.lra_bin_path}"],
                    check=True, capture_output=True
                )
            return True
        except:
            return False
    
    def _show_manual_guide(self):
        """手动配置指南"""
        UI.blank()
        UI.subtitle(self.T['manual_title'])
        UI.blank()
        print(f"    1. {self.T['manual_step1']}")
        print(f"    2. {self.T['manual_step2']}")
        print(f"       {C.CYAN}export PATH=\"$PATH:{self.lra_bin_path}\"{C.RESET}")
        print(f"    3. {self.T['manual_step3']}")
    
    def show_success(self, path_ok: bool):
        """成功界面"""
        UI.blank()
        UI.divider()
        UI.blank()
        print(f"  {C.GREEN}{C.BOLD}🎉 {self.T['done_msg']}{C.RESET}")
        UI.blank()
        UI.subtitle(self.T['next_title'])
        print(f"    1️⃣  {self.T['next_1']}")
        print(f"    2️⃣  {self.T['next_2']}")
        print(f"    3️⃣  {self.T['next_3']}")
    
    def show_ai_prompt(self):
        """AI 提示词"""
        UI.blank()
        UI.divider()
        UI.blank()
        UI.subtitle(f"🤖 {self.T['ai_title']}")
        print(f"  {C.DIM}{self.T['ai_hint']}{C.RESET}")
        UI.blank()
        
        for line in AI_PROMPTS[self.lang].strip().split('\n'):
            print(f"  {line}")
    
    def save_log(self, path_ok: bool):
        """保存日志"""
        log = f"""LRA Installation Log
Time: {datetime.now().isoformat()}
Version: {VERSION}
System: {self.system}
Language: {self.lang}
PATH Configured: {path_ok}
LRA Path: {self.lra_bin_path}
Shell Config: {self._get_shell_config()}
"""
        try:
            with open(self.log_path, "w") as f:
                f.write(log)
            UI.blank()
            print(f"  {C.DIM}📄 {self.T['log_title']}: {self.log_path}{C.RESET}")
        except:
            pass
    
    def run(self):
        """运行安装"""
        try:
            self.show_welcome()
            self.select_language()
            path_ok = self.configure_path()
            self.save_log(path_ok)
            self.show_success(path_ok)
            self.show_ai_prompt()
            UI.blank()
        except KeyboardInterrupt:
            print("\n\n  安装已取消\n")
            sys.exit(1)


def main():
    """入口"""
    installer = LRAInstaller()
    installer.run()


if __name__ == "__main__":
    main()
