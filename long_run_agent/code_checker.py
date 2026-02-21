#!/usr/bin/env python3
"""
代码语法检查器
v2.0 - 支持多种编程语言的基础语法检查
"""

import os
import subprocess
from typing import Dict, Any, Optional, List, Tuple


LANGUAGE_CONFIGS = {
    ".js": {
        "name": "JavaScript",
        "command": ["node", "-c"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".jsx": {
        "name": "JavaScript (JSX)",
        "command": ["node", "-c"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".ts": {
        "name": "TypeScript",
        "command": ["tsc", "--noEmit"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".tsx": {
        "name": "TypeScript (TSX)",
        "command": ["tsc", "--noEmit"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".py": {
        "name": "Python",
        "command": ["python", "-m", "py_compile"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".go": {
        "name": "Go",
        "command": ["go", "vet"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".rs": {
        "name": "Rust",
        "command": ["rustc", "--check"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".java": {
        "name": "Java",
        "command": ["javac", "-Xlint:all"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".c": {
        "name": "C",
        "command": ["gcc", "-fsyntax-only", "-Wall"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".cpp": {
        "name": "C++",
        "command": ["g++", "-fsyntax-only", "-Wall"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".rb": {
        "name": "Ruby",
        "command": ["ruby", "-c"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".php": {
        "name": "PHP",
        "command": ["php", "-l"],
        "success_pattern": "No syntax errors",
        "error_pattern": None,
    },
    ".sh": {
        "name": "Shell",
        "command": ["bash", "-n"],
        "success_pattern": None,
        "error_pattern": None,
    },
    ".lua": {
        "name": "Lua",
        "command": ["lua", "-c"],
        "success_pattern": None,
        "error_pattern": None,
    },
}


class CodeChecker:
    """代码语法检查器"""

    def __init__(self):
        self.results = []

    def _get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名"""
        _, ext = os.path.splitext(file_path)
        return ext.lower()

    def _get_language_config(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取语言配置"""
        ext = self._get_file_extension(file_path)
        return LANGUAGE_CONFIGS.get(ext)

    def _check_command_available(self, command: List[str]) -> bool:
        """检查命令是否可用"""
        try:
            result = subprocess.run(
                ["which", command[0]], capture_output=True, text=True
            )
            return result.returncode == 0
        except:
            return False

    def check_file(self, file_path: str) -> Dict[str, Any]:
        """
        检查单个文件
        返回: {
            "file": str,
            "language": str,
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
        """
        result = {
            "file": file_path,
            "language": "Unknown",
            "valid": False,
            "errors": [],
            "warnings": [],
            "raw_output": "",
        }

        if not os.path.exists(file_path):
            result["errors"].append(f"文件不存在: {file_path}")
            return result

        config = self._get_language_config(file_path)
        if not config:
            result["errors"].append(
                f"不支持的文件类型: {self._get_file_extension(file_path)}"
            )
            return result

        result["language"] = config["name"]

        if not self._check_command_available(config["command"]):
            result["errors"].append(f"命令不可用: {config['command'][0]}")
            return result

        try:
            cmd = config["command"] + [file_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            result["raw_output"] = proc.stdout + proc.stderr

            if proc.returncode == 0:
                if config.get("success_pattern"):
                    if config["success_pattern"] in result["raw_output"]:
                        result["valid"] = True
                    else:
                        result["valid"] = False
                        result["errors"].append(result["raw_output"].strip())
                else:
                    result["valid"] = True
            else:
                result["valid"] = False
                output = proc.stderr.strip() or proc.stdout.strip()
                if output:
                    lines = output.split("\n")
                    for line in lines:
                        line = line.strip()
                        if line:
                            if "warning" in line.lower():
                                result["warnings"].append(line)
                            else:
                                result["errors"].append(line)

        except subprocess.TimeoutExpired:
            result["errors"].append("检查超时")
        except Exception as e:
            result["errors"].append(str(e))

        return result

    def check_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """检查多个文件"""
        results = []
        for file_path in file_paths:
            results.append(self.check_file(file_path))
        return results

    def check_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """检查目录下的文件"""
        results = []

        if extensions is None:
            extensions = list(LANGUAGE_CONFIGS.keys())

        for root, dirs, files in os.walk(directory):
            if not recursive and root != directory:
                continue

            skip_dirs = [
                "node_modules",
                "vendor",
                ".git",
                "__pycache__",
                "build",
                "dist",
            ]
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    file_path = os.path.join(root, file)
                    results.append(self.check_file(file_path))

        return results

    def get_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取检查结果摘要"""
        total = len(results)
        passed = sum(1 for r in results if r["valid"])
        failed = total - passed

        by_language = {}
        for r in results:
            lang = r["language"]
            if lang not in by_language:
                by_language[lang] = {"total": 0, "passed": 0, "failed": 0}
            by_language[lang]["total"] += 1
            if r["valid"]:
                by_language[lang]["passed"] += 1
            else:
                by_language[lang]["failed"] += 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "by_language": by_language,
        }


def print_results(results: List[Dict[str, Any]], verbose: bool = False):
    """打印检查结果"""
    for r in results:
        if r["valid"]:
            print(f"✅ {r['file']} ({r['language']})")
        else:
            print(f"❌ {r['file']} ({r['language']})")
            for err in r["errors"]:
                print(f"   错误: {err}")
            if verbose:
                for warn in r["warnings"]:
                    print(f"   警告: {warn}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="代码语法检查器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    check_parser = subparsers.add_parser("check", help="检查文件")
    check_parser.add_argument("path", help="文件或目录路径")
    check_parser.add_argument("--extensions", nargs="+", help="文件扩展名")
    check_parser.add_argument(
        "--recursive", action="store_true", default=True, help="递归检查"
    )
    check_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    subparsers.add_parser("languages", help="列出支持的语言")

    args = parser.parse_args()

    checker = CodeChecker()

    if args.command == "check":
        if os.path.isfile(args.path):
            results = [checker.check_file(args.path)]
        elif os.path.isdir(args.path):
            results = checker.check_directory(
                args.path, args.extensions, args.recursive
            )
        else:
            print(f"❌ 路径不存在: {args.path}")
            return

        print_results(results, args.verbose)

        summary = checker.get_summary(results)
        print(f"\n📊 检查结果:")
        print(f"   总数: {summary['total']}")
        print(f"   通过: {summary['passed']}")
        print(f"   失败: {summary['failed']}")
        print(f"   通过率: {summary['pass_rate']:.1f}%")

    elif args.command == "languages":
        print("\n📋 支持的语言:\n")
        for ext, config in LANGUAGE_CONFIGS.items():
            print(f"  {ext}: {config['name']} ({config['command'][0]})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
