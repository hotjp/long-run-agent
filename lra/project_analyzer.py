#!/usr/bin/env python3
"""
Project Analyzer - 项目代码分析器
v1.0 - 多语言支持

核心功能:
- 扫描项目结构
- 识别模块
- 分析代码元素（类、函数、依赖）
- 生成结构化文档
"""

import os
import re
import json
import ast
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from lra.config import Config


@dataclass
class ClassInfo:
    name: str
    file: str
    line: int
    docstring: Optional[str]
    methods: List[str]
    bases: List[str]


@dataclass
class FunctionInfo:
    name: str
    file: str
    line: int
    docstring: Optional[str]
    parameters: List[str]
    return_type: Optional[str]


@dataclass
class FileInfo:
    path: str
    language: str
    lines: int
    classes: List[Dict]
    functions: List[Dict]
    imports: List[str]
    exports: List[str]
    docstring: Optional[str]


@dataclass
class ModuleInfo:
    name: str
    path: str
    file_count: int
    line_count: int
    main_classes: List[str]
    main_functions: List[str]
    dependencies: List[str]
    doc_file: Optional[str]
    doc_coverage: float


class PythonParser:
    """Python 代码解析器"""

    @property
    def language(self) -> str:
        return "python"

    @property
    def extensions(self) -> List[str]:
        return [".py"]

    def can_parse(self, file_path: str) -> bool:
        return any(file_path.endswith(ext) for ext in self.extensions)

    def parse_file(self, file_path: str) -> FileInfo:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return FileInfo(
                path=file_path,
                language="python",
                lines=content.count("\n") + 1,
                classes=[],
                functions=[],
                imports=[],
                exports=[],
                docstring=None,
            )

        classes = []
        functions = []
        imports = []
        exports = []
        module_docstring = ast.get_docstring(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for n in node.body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_info = {
                            "name": n.name,
                            "parameters": self._extract_params(n),
                            "return_type": self._get_annotation(n.returns),
                            "docstring": ast.get_docstring(n),
                        }
                        methods.append(method_info)

                classes.append(
                    {
                        "name": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node),
                        "methods": methods,
                        "method_names": [m["name"] for m in methods],
                        "bases": [self._get_name(b) for b in node.bases],
                    }
                )
            elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                parent_check = False
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        if node in parent.body:
                            parent_check = True
                            break
                if not parent_check:
                    functions.append(
                        {
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "docstring": ast.get_docstring(node),
                            "parameters": [arg.arg for arg in node.args.args],
                            "return_type": self._get_annotation(node.returns),
                        }
                    )

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            exports = [
                                e.value for e in node.value.elts if isinstance(e, ast.Constant)
                            ]

        return FileInfo(
            path=file_path,
            language="python",
            lines=content.count("\n") + 1,
            classes=classes,
            functions=functions,
            imports=imports,
            exports=exports,
            docstring=module_docstring,
        )

    def detect_modules(self, project_path: str, ignore_dirs: List[str]) -> List[str]:
        modules = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            if "__init__.py" in files:
                rel_path = os.path.relpath(root, project_path)
                if rel_path != "." and not rel_path.startswith("."):
                    modules.append(rel_path.replace(os.sep, "."))
        return sorted(modules)

    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _get_annotation(self, node) -> Optional[str]:
        if node is None:
            return None
        return self._get_name(node)

    def _extract_params(self, node) -> List[Dict[str, str]]:
        """提取函数参数及其类型注解"""
        params = []
        for arg in node.args.args:
            param = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation) if arg.annotation else None,
            }
            params.append(param)
        return params


class JavaScriptParser:
    """JavaScript/TypeScript 代码解析器（基于正则）"""

    @property
    def language(self) -> str:
        return "javascript"

    @property
    def extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs"]

    def can_parse(self, file_path: str) -> bool:
        return any(file_path.endswith(ext) for ext in self.extensions)

    def parse_file(self, file_path: str) -> FileInfo:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        classes = self._extract_classes(content, file_path)
        functions = self._extract_functions(content, file_path)
        imports = self._extract_imports(content)
        exports = self._extract_exports(content)

        lang = "typescript" if file_path.endswith((".ts", ".tsx")) else "javascript"

        return FileInfo(
            path=file_path,
            language=lang,
            lines=content.count("\n") + 1,
            classes=classes,
            functions=functions,
            imports=imports,
            exports=exports,
            docstring=self._extract_jsdoc(content),
        )

    def detect_modules(self, project_path: str, ignore_dirs: List[str]) -> List[str]:
        modules = []

        package_json = os.path.join(project_path, "package.json")
        if os.path.exists(package_json):
            try:
                with open(package_json, encoding="utf-8") as f:
                    pkg = json.load(f)
                if "exports" in pkg:
                    for name in pkg["exports"].keys():
                        if name != ".":
                            modules.append(name.lstrip("./"))
                if "workspaces" in pkg:
                    modules.extend(pkg["workspaces"])
            except:
                pass

        src_dir = os.path.join(project_path, "src")
        if os.path.exists(src_dir):
            for item in os.listdir(src_dir):
                item_path = os.path.join(src_dir, item)
                if os.path.isdir(item_path) and item not in ignore_dirs:
                    modules.append(item)

        return sorted(set(modules))

    def _extract_classes(self, content: str, file_path: str) -> List[Dict]:
        classes = []
        pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(pattern, content):
            classes.append(
                {
                    "name": match.group(1),
                    "file": file_path,
                    "line": content[: match.start()].count("\n") + 1,
                    "docstring": None,
                    "methods": [],
                    "bases": [match.group(2)] if match.group(2) else [],
                }
            )
        return classes

    def _extract_functions(self, content: str, file_path: str) -> List[Dict]:
        functions = []
        patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
            r"(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                params = []
                if match.lastindex and match.lastindex >= 2:
                    params = [p.strip() for p in match.group(2).split(",") if p.strip()]
                functions.append(
                    {
                        "name": match.group(1),
                        "file": file_path,
                        "line": content[: match.start()].count("\n") + 1,
                        "docstring": None,
                        "parameters": params,
                        "return_type": None,
                    }
                )
        return functions

    def _extract_imports(self, content: str) -> List[str]:
        imports = []
        pattern = r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(pattern, content):
            imports.append(match.group(1))
        return imports

    def _extract_exports(self, content: str) -> List[str]:
        exports = []
        patterns = [
            r"export\s+(?:default\s+)?(?:class|function|const|let)\s+(\w+)",
            r"export\s+\{\s*([^}]+)\s*\}",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                exports.append(match.group(1))
        return exports

    def _extract_jsdoc(self, content: str) -> Optional[str]:
        match = re.search(r"^/\*\*[\s\S]*?\*/", content)
        return match.group(0) if match else None


class GoParser:
    """Go 代码解析器"""

    @property
    def language(self) -> str:
        return "go"

    @property
    def extensions(self) -> List[str]:
        return [".go"]

    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith(".go")

    def parse_file(self, file_path: str) -> FileInfo:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        return FileInfo(
            path=file_path,
            language="go",
            lines=content.count("\n") + 1,
            classes=self._extract_structs(content, file_path),
            functions=self._extract_functions(content, file_path),
            imports=self._extract_imports(content),
            exports=self._extract_exports(content),
            docstring=self._extract_package_doc(content),
        )

    def detect_modules(self, project_path: str, ignore_dirs: List[str]) -> List[str]:
        modules = []

        go_mod = os.path.join(project_path, "go.mod")
        if os.path.exists(go_mod):
            try:
                with open(go_mod, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("module "):
                            modules.append(line.split()[1].strip())
                            break
            except:
                pass

        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)
            if os.path.isdir(item_path) and item not in ignore_dirs and not item.startswith("."):
                for f in os.listdir(item_path):
                    if f.endswith(".go"):
                        modules.append(item)
                        break

        return sorted(set(modules))

    def _extract_structs(self, content: str, file_path: str) -> List[Dict]:
        structs = []
        pattern = r"type\s+(\w+)\s+struct"
        for match in re.finditer(pattern, content):
            structs.append(
                {
                    "name": match.group(1),
                    "file": file_path,
                    "line": content[: match.start()].count("\n") + 1,
                    "docstring": None,
                    "methods": [],
                    "bases": [],
                }
            )
        return structs

    def _extract_functions(self, content: str, file_path: str) -> List[Dict]:
        functions = []
        pattern = r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)(?:\s*\([^)]+\))?"
        for match in re.finditer(pattern, content):
            name = match.group(1)
            if name[0].islower():
                continue
            params = [p.strip() for p in match.group(2).split(",") if p.strip()]
            functions.append(
                {
                    "name": name,
                    "file": file_path,
                    "line": content[: match.start()].count("\n") + 1,
                    "docstring": None,
                    "parameters": params,
                    "return_type": None,
                }
            )
        return functions

    def _extract_imports(self, content: str) -> List[str]:
        imports = []
        for match in re.finditer(r'import\s+"([^"]+)"', content):
            imports.append(match.group(1))
        match = re.search(r"import\s*\(([\s\S]*?)\)", content)
        if match:
            for line in match.group(1).strip().split("\n"):
                line = line.strip()
                if line and line.startswith('"'):
                    imports.append(line.strip('"'))
        return imports

    def _extract_exports(self, content: str) -> List[str]:
        exports = []
        for f in self._extract_functions(content, ""):
            exports.append(f["name"])
        for s in self._extract_structs(content, ""):
            exports.append(s["name"])
        return exports

    def _extract_package_doc(self, content: str) -> Optional[str]:
        match = re.search(r"^//\s*[\s\S]*?^package", content, re.MULTILINE)
        return match.group(0) if match else None


class ProjectAnalyzer:
    """项目代码分析器"""

    DEFAULT_IGNORE_DIRS = [
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        "vendor",
        ".idea",
        ".vscode",
        "egg-info",
    ]

    def __init__(self, project_path: str = "", config: Dict[str, Any] = None):
        self.project_path = os.path.abspath(project_path or os.getcwd())
        self.config = config if config is not None else {}
        self.ignore_dirs = self.config.get("ignore_dirs", self.DEFAULT_IGNORE_DIRS)
        self._parsers = self._init_parsers()
        self._file_cache: Dict[str, FileInfo] = {}
        self._module_cache: Optional[List[str]] = None

    def _init_parsers(self) -> List[Any]:
        return [PythonParser(), JavaScriptParser(), GoParser()]

    def _get_parser(self, file_path: str):
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(self.project_path, ".long-run-agent", "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except:
                pass
        return {}

    def analyze_project(self) -> Dict[str, Any]:
        result = {
            "project_name": os.path.basename(self.project_path),
            "project_path": self.project_path,
            "analyzed_at": datetime.now().isoformat(),
            "language": self.detect_language(),
            "total_files": 0,
            "total_lines": 0,
            "modules": [],
            "files": [],
            "dependencies": {},
            "entry_points": [],
            "doc_coverage": {"total": 0, "documented": 0, "ratio": 0.0},
            "description": self._extract_project_description(),
        }

        all_files = self._collect_code_files()
        result["total_files"] = len(all_files)

        total_lines = 0
        total_funcs = 0
        total_classes = 0
        documented_funcs = 0
        documented_classes = 0

        for file_path in all_files:
            file_info = self.analyze_file(file_path)
            total_lines += file_info.lines

            rel_path = os.path.relpath(file_path, self.project_path)
            file_summary = {
                "path": rel_path,
                "language": file_info.language,
                "lines": file_info.lines,
                "classes": len(file_info.classes),
                "functions": len(file_info.functions),
                "has_doc": file_info.docstring is not None,
            }
            result["files"].append(file_summary)

            for func in file_info.functions:
                total_funcs += 1
                if func.get("docstring"):
                    documented_funcs += 1

            for cls in file_info.classes:
                total_classes += 1
                if cls.get("docstring"):
                    documented_classes += 1

        result["total_lines"] = total_lines

        if total_funcs + total_classes > 0:
            total_doc = documented_funcs + documented_classes
            total_items = total_funcs + total_classes
            result["doc_coverage"] = {
                "total_functions": total_funcs,
                "documented_functions": documented_funcs,
                "total_classes": total_classes,
                "documented_classes": documented_classes,
                "ratio": round(total_doc / total_items, 2),
            }

        modules = self.detect_modules()
        for module_name in modules:
            module_info = self.analyze_module(module_name)
            if module_info:
                result["modules"].append(module_info)

        result["entry_points"] = self._detect_entry_points()

        result["dependencies"] = self._analyze_module_dependencies(result["modules"])

        return result

    def _analyze_module_dependencies(self, modules: List[Dict]) -> Dict[str, Any]:
        """分析模块间依赖关系"""
        module_names = {m["name"] for m in modules}
        dependencies = {}

        for module in modules:
            module_name = module["name"]
            deps = set()

            for imp in module.get("dependencies", []):
                for mn in module_names:
                    if imp.startswith(mn) or mn.startswith(imp):
                        deps.add(mn)

            if module_name not in dependencies:
                dependencies[module_name] = {"imports": [], "imported_by": []}

            dependencies[module_name]["imports"] = list(deps)

        for module_name, info in dependencies.items():
            for other, other_info in dependencies.items():
                if module_name in other_info["imports"]:
                    info["imported_by"].append(other)

        return dependencies

    def analyze_module(self, module_name: str) -> Optional[Dict[str, Any]]:
        module_files = self._find_module_files(module_name)

        if not module_files:
            return None

        file_count = len(module_files)
        line_count = 0
        all_classes = []
        all_functions = []
        all_imports = set()
        doc_count = 0
        module_docstring = None

        for file_path in module_files:
            file_info = self.analyze_file(file_path)
            line_count += file_info.lines
            all_classes.extend(file_info.classes)
            all_functions.extend(file_info.functions)
            all_imports.update(file_info.imports)
            if file_info.docstring:
                doc_count += 1
                if file_path.endswith("__init__.py") and not module_docstring:
                    module_docstring = file_info.docstring

        doc_coverage = doc_count / file_count if file_count > 0 else 0

        return {
            "name": module_name,
            "path": self._get_module_path(module_name),
            "file_count": file_count,
            "line_count": line_count,
            "main_classes": [c["name"] for c in all_classes[:10]],
            "main_functions": [f["name"] for f in all_functions[:10]],
            "dependencies": list(all_imports)[:20],
            "doc_file": self._find_doc_file(module_name),
            "doc_coverage": round(doc_coverage, 2),
            "classes": all_classes[:20],
            "functions": all_functions[:20],
            "docstring": module_docstring,
        }

    def analyze_file(self, file_path: str) -> FileInfo:
        abs_path = os.path.abspath(file_path)
        if abs_path in self._file_cache:
            return self._file_cache[abs_path]

        parser = self._get_parser(abs_path)
        if not parser:
            return FileInfo(
                path=abs_path,
                language="unknown",
                lines=0,
                classes=[],
                functions=[],
                imports=[],
                exports=[],
                docstring=None,
            )

        result = parser.parse_file(abs_path)
        self._file_cache[abs_path] = result
        return result

    def detect_modules(self) -> List[str]:
        if self._module_cache is not None:
            return self._module_cache

        modules = set()
        primary_lang = self.detect_language()

        if primary_lang == "python":
            parser = PythonParser()
            modules.update(parser.detect_modules(self.project_path, self.ignore_dirs))
        elif primary_lang in ("javascript", "typescript"):
            parser = JavaScriptParser()
            modules.update(parser.detect_modules(self.project_path, self.ignore_dirs))
        elif primary_lang == "go":
            parser = GoParser()
            modules.update(parser.detect_modules(self.project_path, self.ignore_dirs))
        else:
            for parser in self._parsers:
                modules.update(parser.detect_modules(self.project_path, self.ignore_dirs))

        self._module_cache = sorted(modules)
        return self._module_cache

    def detect_language(self) -> str:
        counts = {".py": 0, ".js": 0, ".ts": 0, ".go": 0, ".java": 0}

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith(".")]
            for f in files:
                for ext in counts:
                    if f.endswith(ext):
                        counts[ext] += 1

        if counts[".ts"] > counts[".js"]:
            return "typescript"
        if counts[".py"] > 0 and counts[".py"] >= max(counts.values()):
            return "python"
        if counts[".js"] > 0 and counts[".js"] >= max(counts.values()):
            return "javascript"
        if counts[".go"] > 0 and counts[".go"] >= max(counts.values()):
            return "go"
        if counts[".java"] > 0 and counts[".java"] >= max(counts.values()):
            return "java"

        return "unknown"

    def generate_module_doc(self, module_name: str, output_dir: str = "docs") -> str:
        module_info = self.analyze_module(module_name)
        if not module_info:
            return ""

        os.makedirs(os.path.join(output_dir, "modules"), exist_ok=True)

        content = self._render_module_doc(module_info)

        doc_path = os.path.join(output_dir, "modules", f"{module_name}.md")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(content)

        return doc_path

    def generate_project_doc(self, output_dir: str = "docs") -> Dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "modules"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "files"), exist_ok=True)

        result = {}
        project_info = self.analyze_project()

        modules_content = self._render_modules_doc(project_info)
        modules_path = os.path.join(output_dir, "MODULES.md")
        with open(modules_path, "w", encoding="utf-8") as f:
            f.write(modules_content)
        result["modules"] = modules_path

        for module_name in self.detect_modules():
            doc_path = self.generate_module_doc(module_name, output_dir)
            if doc_path:
                result[f"module_{module_name}"] = doc_path

        file_docs = self.generate_file_docs(output_dir)
        result["file_docs"] = list(file_docs.values())

        return result

    def generate_summary_json(self) -> str:
        result = self.analyze_project()

        analysis_dir = os.path.join(self.project_path, ".long-run-agent", "analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        os.makedirs(os.path.join(analysis_dir, "modules"), exist_ok=True)

        # 生成 Agent 友好的索引
        agent_index = self._generate_agent_index(result)
        index_path = os.path.join(analysis_dir, "index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(agent_index, f, indent=2, ensure_ascii=False)

        # 生成完整摘要
        summary_path = os.path.join(analysis_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        for module in result.get("modules", []):
            module_path = os.path.join(analysis_dir, "modules", f"{module['name']}.json")
            with open(module_path, "w", encoding="utf-8") as f:
                json.dump(module, f, indent=2, ensure_ascii=False)

        return summary_path

    def _generate_agent_index(self, project_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Agent 友好的快速查找索引"""
        index = {
            "project_name": project_info.get("project_name", ""),
            "language": project_info.get("language", ""),
            "description": project_info.get("description", ""),
            "entry_points": project_info.get("entry_points", []),
            "modules": [],
            "classes": {},
            "functions": {},
            "files": {},
        }

        for module in project_info.get("modules", []):
            index["modules"].append(module.get("name", ""))

        for module in project_info.get("modules", []):
            module_name = module.get("name", "")

            for cls in module.get("classes", []):
                cls_name = cls.get("name", "")
                if cls_name:
                    index["classes"][cls_name] = {
                        "module": module_name,
                        "file": os.path.relpath(cls.get("file", ""), self.project_path),
                        "line": cls.get("line", 0),
                        "docstring": cls.get("docstring", ""),
                        "methods": cls.get("method_names", []),
                    }

            for func in module.get("functions", []):
                func_name = func.get("name", "")
                if func_name:
                    index["functions"][func_name] = {
                        "module": module_name,
                        "file": os.path.relpath(func.get("file", ""), self.project_path),
                        "line": func.get("line", 0),
                        "docstring": func.get("docstring", ""),
                        "parameters": func.get("parameters", []),
                    }

        for f in project_info.get("files", []):
            path = f.get("path", "")
            if path:
                index["files"][path] = {
                    "language": f.get("language", ""),
                    "lines": f.get("lines", 0),
                    "classes": f.get("classes", 0),
                    "functions": f.get("functions", 0),
                }

        return index

    def _collect_code_files(self) -> List[str]:
        files = []
        extensions = [ext for p in self._parsers for ext in p.extensions]

        for root, dirs, filenames in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith(".")]
            for f in filenames:
                if any(f.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, f))

        return files

    def _find_module_files(self, module_name: str) -> List[str]:
        module_path = self._get_module_path(module_name)
        if not module_path or not os.path.exists(module_path):
            return []

        files = []
        extensions = [ext for p in self._parsers for ext in p.extensions]

        for root, dirs, filenames in os.walk(module_path):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for f in filenames:
                if any(f.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, f))

        return files

    def _get_module_path(self, module_name: str) -> Optional[str]:
        lang = self.detect_language()

        if lang == "python":
            path = os.path.join(self.project_path, module_name.replace(".", os.sep))
            if os.path.exists(path):
                return path
            for src_dir in ["src", "lib", ""]:
                path = os.path.join(self.project_path, src_dir, module_name.replace(".", os.sep))
                if os.path.exists(path):
                    return path

        elif lang in ("javascript", "typescript"):
            for src_dir in ["src", "lib", "packages", ""]:
                path = os.path.join(self.project_path, src_dir, module_name)
                if os.path.exists(path):
                    return path

        elif lang == "go":
            path = os.path.join(self.project_path, module_name)
            if os.path.exists(path):
                return path

        return None

    def _find_doc_file(self, module_name: str) -> Optional[str]:
        doc_dirs = ["docs", "doc", "documentation", ""]
        for doc_dir in doc_dirs:
            for ext in [".md", ".rst", ".txt"]:
                path = os.path.join(self.project_path, doc_dir, f"{module_name}{ext}")
                if os.path.exists(path):
                    return path
                path = os.path.join(self.project_path, doc_dir, "modules", f"{module_name}{ext}")
                if os.path.exists(path):
                    return path
        return None

    def _detect_entry_points(self) -> List[str]:
        entry_points = []
        candidates = [
            "__main__.py",
            "main.py",
            "app.py",
            "run.py",
            "index.js",
            "index.ts",
            "main.go",
            "main.java",
        ]

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith(".")]
            for f in files:
                if f in candidates:
                    rel_path = os.path.relpath(os.path.join(root, f), self.project_path)
                    entry_points.append(rel_path)

        return entry_points[:10]

    def _extract_project_description(self) -> str:
        """从 README 提取项目描述"""
        readme_paths = [
            os.path.join(self.project_path, "README.md"),
            os.path.join(self.project_path, "readme.md"),
            os.path.join(self.project_path, "README.rst"),
        ]

        for readme_path in readme_paths:
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, encoding="utf-8") as f:
                        content = f.read()

                    lines = content.split("\n")

                    # 提取标题（第一行 # 开头）
                    title = ""
                    for line in lines:
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break

                    # 提取描述（标题后的第一段非空非标题内容）
                    description_lines = []
                    in_code_block = False
                    found_title = False

                    for line in lines:
                        if line.startswith("```"):
                            in_code_block = not in_code_block
                            continue

                        if in_code_block:
                            continue

                        if line.startswith("# "):
                            found_title = True
                            continue

                        if found_title:
                            if line.startswith("##"):
                                break
                            if (
                                line.strip()
                                and not line.startswith("|")
                                and not line.startswith(">")
                            ):
                                description_lines.append(line.strip())
                            elif description_lines and not line.strip():
                                break

                    if description_lines:
                        desc = " ".join(description_lines)[:300]
                        return desc

                    if title:
                        return title

                except:
                    pass
        return ""

    def generate_file_docs(self, output_dir: str = "docs") -> Dict[str, str]:
        """为每个源文件生成文档"""
        os.makedirs(os.path.join(output_dir, "files"), exist_ok=True)

        result = {}
        all_files = self._collect_code_files()

        for file_path in all_files:
            file_info = self.analyze_file(file_path)
            rel_path = os.path.relpath(file_path, self.project_path)
            doc_name = rel_path.replace(os.sep, "_").replace(".", "_")

            content = self._render_file_doc(file_info, rel_path)
            doc_path = os.path.join(output_dir, "files", f"{doc_name}.md")

            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(content)

            result[rel_path] = doc_path

        return result

    def _render_file_doc(self, file_info: FileInfo, rel_path: str) -> str:
        """渲染单个文件的文档"""
        lines = [
            f"# {rel_path}",
            "",
            f"> 语言：{file_info.language} | 代码行数：{file_info.lines}",
            "",
            "## 概述",
            "",
            file_info.docstring if file_info.docstring else "（待补充）",
            "",
        ]

        if file_info.classes:
            lines.extend(
                [
                    "## 类",
                    "",
                    "| 类名 | 方法数 | 说明 |",
                    "|------|--------|------|",
                ]
            )
            for cls in file_info.classes[:20]:
                doc = cls.get("docstring", "-")[:50] if cls.get("docstring") else "-"
                methods_count = len(cls.get("methods", []))
                lines.append(f"| `{cls['name']}` | {methods_count} | {doc} |")
            lines.append("")

        if file_info.functions:
            lines.extend(
                [
                    "## 函数",
                    "",
                    "| 函数名 | 参数 | 说明 |",
                    "|--------|------|------|",
                ]
            )
            for func in file_info.functions[:20]:
                params = ", ".join(func.get("parameters", []))[:30]
                doc = func.get("docstring", "-")[:50] if func.get("docstring") else "-"
                lines.append(f"| `{func['name']}` | `{params}` | {doc} |")
            lines.append("")

        if file_info.imports:
            lines.extend(
                [
                    "## 依赖",
                    "",
                ]
            )
            for imp in file_info.imports[:20]:
                lines.append(f"- {imp}")
            lines.append("")

        return "\n".join(lines)

    def _format_method_sig(self, method: Dict[str, Any]) -> str:
        """格式化方法签名"""
        params = method.get("parameters", [])
        ret = method.get("return_type")

        param_strs = []
        for p in params:
            name = p.get("name", "")
            ptype = p.get("type")
            if ptype:
                param_strs.append(f"{name}: {ptype}")
            else:
                param_strs.append(name)

        sig = ", ".join(param_strs)
        if ret:
            sig = f"({sig}) -> {ret}"
        else:
            sig = f"({sig})"

        return sig

    def _render_module_doc(self, module_info: Dict[str, Any]) -> str:
        module_name = module_info.get("name", "")
        module_doc = module_info.get("docstring", "")

        lines = [
            f"# {module_name} 模块",
            "",
            f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 文件数：{module_info.get('file_count', 0)} | 代码行数：{module_info.get('line_count', 0)} | 文档覆盖：{module_info.get('doc_coverage', 0):.0%}",
            "",
            "## 概述",
            "",
            module_doc if module_doc else "（待补充模块概述）",
            "",
        ]

        if module_info.get("main_classes"):
            lines.extend(
                [
                    "## 核心类",
                    "",
                ]
            )
            for cls in module_info.get("classes", [])[:10]:
                doc = cls.get("docstring", "-")[:80] if cls.get("docstring") else "-"
                methods = cls.get("methods", [])
                bases = cls.get("bases", [])

                lines.append(f"### `{cls['name']}`")
                lines.append("")
                if bases:
                    lines.append(f"继承自：`{', '.join(bases)}`")
                    lines.append("")
                lines.append(f"> {doc}")
                lines.append("")

                if methods:
                    lines.append("**方法：**")
                    lines.append("")
                    lines.append("| 方法 | 签名 | 说明 |")
                    lines.append("|------|------|------|")
                    for m in methods[:10]:
                        sig = self._format_method_sig(m)
                        m_doc = m.get("docstring", "-")[:40] if m.get("docstring") else "-"
                        lines.append(f"| `{m['name']}` | `{sig}` | {m_doc} |")
                    lines.append("")

            lines.append("")

        if module_info.get("main_functions"):
            lines.extend(
                [
                    "## 核心函数",
                    "",
                    "| 函数名 | 参数 | 说明 |",
                    "|--------|------|------|",
                ]
            )
            for func in module_info.get("functions", [])[:10]:
                params = ", ".join(func.get("parameters", []))[:40]
                doc = func.get("docstring", "-")[:60] if func.get("docstring") else "-"
                lines.append(f"| `{func['name']}` | `{params}` | {doc} |")
            lines.append("")

        if module_info.get("dependencies"):
            lines.extend(
                [
                    "## 依赖关系",
                    "",
                    "### 本模块依赖",
                    "",
                ]
            )
            for dep in module_info.get("dependencies", [])[:15]:
                lines.append(f"- {dep}")
            lines.append("")

        lines.extend(
            [
                "## 使用示例",
                "",
                "```python",
                "# 待补充",
                "```",
                "",
            ]
        )

        suggestions = []
        if not module_doc:
            suggestions.append("- 补充模块概述文档")
        if not module_info.get("main_classes") and not module_info.get("main_functions"):
            suggestions.append("- 添加核心功能")
        total_doc = sum(1 for c in module_info.get("classes", []) if c.get("docstring"))
        total_doc += sum(1 for f in module_info.get("functions", []) if f.get("docstring"))
        if total_doc == 0:
            suggestions.append("- 完善核心函数/类注释")

        if suggestions:
            lines.extend(
                [
                    "## 改进建议",
                    "",
                ]
                + suggestions
            )
        else:
            lines.append("✅ 文档完善度良好")

        return "\n".join(lines)

    def _render_modules_doc(self, project_info: Dict[str, Any] = None) -> str:
        project_name = os.path.basename(self.project_path)
        modules = self.detect_modules()
        lang = self.detect_language()
        description = project_info.get("description", "") if project_info else ""
        total_files = project_info.get("total_files", 0) if project_info else 0
        total_lines = project_info.get("total_lines", 0) if project_info else 0
        doc_coverage = project_info.get("doc_coverage", {}) if project_info else {}

        lines = [
            f"# {project_name} 项目文档",
            "",
            f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 主语言：{lang}",
            f"> 文件数：{total_files} | 代码行数：{total_lines}",
            "",
        ]

        if description:
            lines.extend(
                [
                    "## 项目概述",
                    "",
                    description,
                    "",
                ]
            )

        lines.extend(
            [
                "## 文档覆盖率",
                "",
                f"- 函数总数：{doc_coverage.get('total_functions', 0)}",
                f"- 已文档化：{doc_coverage.get('documented_functions', 0)}",
                f"- 类总数：{doc_coverage.get('total_classes', 0)}",
                f"- 已文档化：{doc_coverage.get('documented_classes', 0)}",
                f"- **覆盖率：{doc_coverage.get('ratio', 0):.0%}**",
                "",
                "## 模块列表",
                "",
                "| 模块 | 文件数 | 代码行数 | 文档覆盖 | 说明 |",
                "|------|--------|----------|----------|------|",
            ]
        )

        for module_name in modules:
            info = self.analyze_module(module_name)
            if info:
                coverage = f"{info['doc_coverage']:.0%}"
                lines.append(
                    f"| [{module_name}](./modules/{module_name}.md) | {info['file_count']} | {info['line_count']} | {coverage} | - |"
                )

        lines.extend(
            [
                "",
                "## 文件列表",
                "",
                "| 文件 | 语言 | 行数 | 类 | 函数 |",
                "|------|------|------|----|------|",
            ]
        )

        if project_info and project_info.get("files"):
            for f in project_info["files"][:30]:
                lines.append(
                    f"| [{f['path']}](./files/{f['path'].replace(os.sep, '_').replace('.', '_')}.md) | {f['language']} | {f['lines']} | {f['classes']} | {f['functions']} |"
                )

        dependencies = project_info.get("dependencies", {}) if project_info else {}
        if dependencies:
            lines.extend(
                [
                    "",
                    "## 模块依赖关系",
                    "",
                    "```mermaid",
                    "graph LR",
                ]
            )

            for module_name, deps in dependencies.items():
                safe_name = module_name.replace(".", "_")
                for imp in deps.get("imports", []):
                    if imp != module_name:
                        safe_imp = imp.replace(".", "_")
                        lines.append(f"    {safe_name} --> {safe_imp}")

            lines.extend(
                [
                    "```",
                    "",
                ]
            )

        lines.extend(
            [
                "## 快速导航",
                "",
                "- [模块详情](./modules/)",
                "- [文件详情](./files/)",
                "",
                "---",
                "",
                "*本文档由 LRA ProjectAnalyzer 自动生成*",
            ]
        )

        return "\n".join(lines)
