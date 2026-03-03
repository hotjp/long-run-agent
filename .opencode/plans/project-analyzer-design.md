# ProjectAnalyzer 模块设计文档

## 问题背景

从 Agent 使用日志分析发现两个核心问题：

1. **`analyze-module` 命令功能偏离设计意图**
   - 现状：仅搜索已存在任务的描述字段
   - 预期：分析代码模块结构、生成文档
   - 原因：实现不完整，只做了简单搜索

2. **`init` 命令 `--template` 参数必填**
   - 现状：`required=True`
   - 预期：设置默认值减少初始化阻力

## 设计目标

1. Agent 初始化项目后，执行 `lra analyze-project` 即可获得完整的项目分析
2. 生成的文档可供 Agent 后续开发中快速使用
3. 文档与代码逻辑一致，可维护，供人类查阅

## 核心设计

### 1. 新增文件

```
long_run_agent/
├── project_analyzer.py           # 项目分析核心模块
├── parsers/                      # 语言解析器
│   ├── __init__.py
│   ├── base.py                   # 解析器基类
│   ├── python_parser.py          # Python 解析器
│   ├── javascript_parser.py      # JS/TS 解析器
│   └── go_parser.py              # Go 解析器
└── templates/
    └── module-analysis.yaml      # 模块分析文档模板
```

### 2. 修改文件

| 文件 | 修改内容 |
|------|----------|
| `cli.py:1001-1007` | init 命令 `--template` 改为默认值 `task` |
| `cli.py:886-910` | 重构 `analyze-module` 调用 ProjectAnalyzer |
| `cli.py:1192-1194` | 新增 `analyze-project` 命令 |
| `config.py` | 新增 `get_analysis_dir()` 方法 |
| `README.md` | 更新命令说明 |

### 3. 核心类设计

```python
# project_analyzer.py

class ProjectAnalyzer:
    """项目代码分析器"""
    
    SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "go", "java"]
    
    def __init__(self, project_path: str = None, config: Dict = None):
        self.project_path = project_path or os.getcwd()
        self.config = config or self._load_config()
        self.parsers = self._init_parsers()
    
    def analyze_project(self) -> Dict[str, Any]:
        """分析整个项目"""
        pass
    
    def analyze_module(self, module_name: str) -> Dict[str, Any]:
        """分析指定模块"""
        pass
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """分析单个文件"""
        pass
    
    def detect_modules(self) -> List[str]:
        """检测项目模块"""
        pass
    
    def detect_language(self) -> str:
        """检测主语言"""
        pass
    
    def generate_module_doc(self, module_name: str, output_dir: str = "docs") -> str:
        """生成模块文档"""
        pass
    
    def generate_project_doc(self, output_dir: str = "docs") -> Dict[str, str]:
        """生成项目文档"""
        pass
    
    def generate_summary_json(self) -> str:
        """生成摘要 JSON"""
        pass
```

### 4. 语言解析器基类

```python
# parsers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

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
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    imports: List[str]
    exports: List[str]
    docstring: Optional[str]

class LanguageParser(ABC):
    """语言解析器基类"""
    
    @property
    @abstractmethod
    def language(self) -> str:
        """语言名称"""
        pass
    
    @property
    @abstractmethod
    def extensions(self) -> List[str]:
        """支持的文件扩展名"""
        pass
    
    @abstractmethod
    def parse_file(self, file_path: str) -> FileInfo:
        """解析文件"""
        pass
    
    @abstractmethod
    def detect_modules(self, project_path: str) -> List[str]:
        """检测模块结构"""
        pass
    
    def can_parse(self, file_path: str) -> bool:
        """检查是否能解析该文件"""
        return any(file_path.endswith(ext) for ext in self.extensions)
```

### 5. Python 解析器实现

```python
# parsers/python_parser.py

import ast
from typing import List, Optional
from .base import LanguageParser, FileInfo, ClassInfo, FunctionInfo

class PythonParser(LanguageParser):
    """Python 代码解析器"""
    
    @property
    def language(self) -> str:
        return "python"
    
    @property
    def extensions(self) -> List[str]:
        return [".py"]
    
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
                docstring=None
            )
        
        classes = []
        functions = []
        imports = []
        exports = []
        module_docstring = ast.get_docstring(tree)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(ClassInfo(
                    name=node.name,
                    file=file_path,
                    line=node.lineno,
                    docstring=ast.get_docstring(node),
                    methods=[n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    bases=[self._get_name(b) for b in node.bases]
                ))
            elif isinstance(node, ast.FunctionDef):
                # 排除类方法
                if not any(isinstance(p, ast.ClassDef) for p in ast.walk(tree)):
                    pass
                functions.append(FunctionInfo(
                    name=node.name,
                    file=file_path,
                    line=node.lineno,
                    docstring=ast.get_docstring(node),
                    parameters=[arg.arg for arg in node.args.args],
                    return_type=self._get_annotation(node.returns)
                ))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                else:
                    for alias in node.names:
                        imports.append(alias.name)
        
        # 检测 __all__ 导出
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            exports = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
        
        return FileInfo(
            path=file_path,
            language="python",
            lines=content.count("\n") + 1,
            classes=classes,
            functions=functions,
            imports=imports,
            exports=exports,
            docstring=module_docstring
        )
    
    def detect_modules(self, project_path: str) -> List[str]:
        """检测 Python 模块（包含 __init__.py 的目录）"""
        modules = []
        for root, dirs, files in os.walk(project_path):
            if "__init__.py" in files:
                rel_path = os.path.relpath(root, project_path)
                if rel_path != "." and not rel_path.startswith("."):
                    modules.append(rel_path.replace(os.sep, "."))
        return modules
    
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
```

### 6. JavaScript/TypeScript 解析器

```python
# parsers/javascript_parser.py

import re
from typing import List
from .base import LanguageParser, FileInfo, ClassInfo, FunctionInfo

class JavaScriptParser(LanguageParser):
    """JavaScript/TypeScript 代码解析器（基于正则，简化实现）"""
    
    @property
    def language(self) -> str:
        return "javascript"
    
    @property
    def extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs"]
    
    def parse_file(self, file_path: str) -> FileInfo:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        # 使用正则提取（简化版，生产环境建议使用 tree-sitter）
        classes = self._extract_classes(content, file_path)
        functions = self._extract_functions(content, file_path)
        imports = self._extract_imports(content)
        exports = self._extract_exports(content)
        
        return FileInfo(
            path=file_path,
            language="typescript" if file_path.endswith((".ts", ".tsx")) else "javascript",
            lines=content.count("\n") + 1,
            classes=classes,
            functions=functions,
            imports=imports,
            exports=exports,
            docstring=self._extract_jsdoc(content)
        )
    
    def detect_modules(self, project_path: str) -> List[str]:
        """检测 JS/TS 模块"""
        modules = []
        
        # 检查 package.json 的 exports/workspaces
        package_json = os.path.join(project_path, "package.json")
        if os.path.exists(package_json):
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                # exports 字段
                if "exports" in pkg:
                    for name in pkg["exports"].keys():
                        if name != ".":
                            modules.append(name.lstrip("./"))
                # workspaces
                if "workspaces" in pkg:
                    modules.extend(pkg["workspaces"])
            except:
                pass
        
        # src/ 目录结构
        src_dir = os.path.join(project_path, "src")
        if os.path.exists(src_dir):
            for item in os.listdir(src_dir):
                item_path = os.path.join(src_dir, item)
                if os.path.isdir(item_path):
                    modules.append(item)
        
        return modules
    
    def _extract_classes(self, content: str, file_path: str) -> List[ClassInfo]:
        """提取类定义"""
        classes = []
        pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(pattern, content):
            classes.append(ClassInfo(
                name=match.group(1),
                file=file_path,
                line=content[:match.start()].count("\n") + 1,
                docstring=None,  # TODO: 提取 JSDoc
                methods=[],
                bases=[match.group(2)] if match.group(2) else []
            ))
        return classes
    
    def _extract_functions(self, content: str, file_path: str) -> List[FunctionInfo]:
        """提取函数定义"""
        functions = []
        # 匹配 function 声明和箭头函数
        patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
            r'(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                functions.append(FunctionInfo(
                    name=match.group(1),
                    file=file_path,
                    line=content[:match.start()].count("\n") + 1,
                    docstring=None,
                    parameters=match.group(2).split(",") if match.lastindex >= 2 else [],
                    return_type=None
                ))
        return functions
    
    def _extract_imports(self, content: str) -> List[str]:
        """提取导入"""
        imports = []
        pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(pattern, content):
            imports.append(match.group(1))
        return imports
    
    def _extract_exports(self, content: str) -> List[str]:
        """提取导出"""
        exports = []
        patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const|let)\s+(\w+)',
            r'export\s+\{\s*([^}]+)\s*\}',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                exports.append(match.group(1))
        return exports
    
    def _extract_jsdoc(self, content: str) -> Optional[str]:
        """提取文件顶部的 JSDoc"""
        match = re.search(r'^/\*\*[\s\S]*?\*/', content)
        return match.group(0) if match else None
```

### 7. Go 解析器

```python
# parsers/go_parser.py

import re
from typing import List
from .base import LanguageParser, FileInfo, ClassInfo, FunctionInfo

class GoParser(LanguageParser):
    """Go 代码解析器"""
    
    @property
    def language(self) -> str:
        return "go"
    
    @property
    def extensions(self) -> List[str]:
        return [".go"]
    
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
            docstring=self._extract_package_doc(content)
        )
    
    def detect_modules(self, project_path: str) -> List[str]:
        """检测 Go 模块"""
        modules = []
        
        # go.mod 文件
        go_mod = os.path.join(project_path, "go.mod")
        if os.path.exists(go_mod):
            try:
                with open(go_mod) as f:
                    for line in f:
                        if line.startswith("module "):
                            modules.append(line.split()[1].strip())
                            break
            except:
                pass
        
        # 内部包
        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)
            if os.path.isdir(item_path):
                for f in os.listdir(item_path):
                    if f.endswith(".go"):
                        modules.append(item)
                        break
        
        return modules
    
    def _extract_structs(self, content: str, file_path: str) -> List[ClassInfo]:
        """提取结构体"""
        structs = []
        pattern = r'type\s+(\w+)\s+struct'
        for match in re.finditer(pattern, content):
            structs.append(ClassInfo(
                name=match.group(1),
                file=file_path,
                line=content[:match.start()].count("\n") + 1,
                docstring=None,
                methods=[],
                bases=[]
            ))
        return structs
    
    def _extract_functions(self, content: str, file_path: str) -> List[FunctionInfo]:
        """提取函数"""
        functions = []
        # func Name(...) 或 func (receiver) Name(...)
        pattern = r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)(?:\s*\([^)]+\))?'
        for match in re.finditer(pattern, content):
            name = match.group(1)
            # 跳过私有函数
            if name[0].islower():
                continue
            functions.append(FunctionInfo(
                name=name,
                file=file_path,
                line=content[:match.start()].count("\n") + 1,
                docstring=None,
                parameters=[p.strip() for p in match.group(2).split(",") if p.strip()],
                return_type=None
            ))
        return functions
    
    def _extract_imports(self, content: str) -> List[str]:
        """提取导入"""
        imports = []
        # 单行导入
        for match in re.finditer(r'import\s+"([^"]+)"', content):
            imports.append(match.group(1))
        # 多行导入
        match = re.search(r'import\s*\(([\s\S]*?)\)', content)
        if match:
            for line in match.group(1).strip().split("\n"):
                line = line.strip()
                if line and line.startswith('"'):
                    imports.append(line.strip('"'))
        return imports
    
    def _extract_exports(self, content: str) -> List[str]:
        """Go 中大写开头的都是导出的"""
        exports = []
        for f in self._extract_functions(content, ""):
            exports.append(f.name)
        for s in self._extract_structs(content, ""):
            exports.append(s.name)
        return exports
    
    def _extract_package_doc(self, content: str) -> Optional[str]:
        """提取包文档"""
        match = re.search(r'^//\s*[\s\S]*?^package', content, re.MULTILINE)
        return match.group(0) if match else None
```

### 8. CLI 命令修改

```python
# cli.py

# 1. init 命令修改（第 1001-1007 行）
# OLD:
init_p.add_argument(
    "--template",
    required=True,
    help="Default template (task|code-module|doc-update|data-pipeline|novel-chapter)",
)

# NEW:
init_p.add_argument(
    "--template",
    default="task",
    help="Default template (default: task)",
)

# 2. 重构 analyze-module 命令（第 886-910 行）
def cmd_analyze_module(self, module_name: str, output_doc: bool = False, json_mode: bool = False):
    """分析指定模块"""
    if not self._check_project():
        output({"error": "not_initialized"}, json_mode)
        return
    
    try:
        from .project_analyzer import ProjectAnalyzer
        analyzer = ProjectAnalyzer(os.getcwd())
        result = analyzer.analyze_module(module_name)
        
        if output_doc:
            doc_path = analyzer.generate_module_doc(module_name)
            result["doc_path"] = doc_path
        
        output(result, json_mode)
    except Exception as e:
        output({"error": str(e)}, json_mode)

# 3. 新增 analyze-project 命令
def cmd_analyze_project(
    self, 
    output_dir: str = "docs",
    create_tasks: bool = True,
    force: bool = False,
    json_mode: bool = False
):
    """分析整个项目结构"""
    if not self._check_project():
        output({"error": "not_initialized"}, json_mode)
        return
    
    try:
        from .project_analyzer import ProjectAnalyzer
        
        analyzer = ProjectAnalyzer(os.getcwd())
        
        # 检查是否已有分析报告
        summary_path = os.path.join(".long-run-agent", "analysis", "summary.json")
        if os.path.exists(summary_path) and not force:
            output({"info": "analysis_exists", "hint": "use --force to re-analyze"}, json_mode)
            return
        
        # 执行分析
        result = analyzer.analyze_project()
        
        # 生成文档
        docs = analyzer.generate_project_doc(output_dir)
        result["docs"] = docs
        
        # 生成摘要
        summary = analyzer.generate_summary_json()
        result["summary_path"] = summary
        
        # 创建模块文档任务
        if create_tasks:
            created_tasks = []
            for module in result.get("modules", []):
                success, task = self.task_manager.create(
                    description=f"完善 {module['name']} 模块文档",
                    template="doc-update",
                    priority="P2",
                    skip_system_check=True,
                    variables={
                        "module": module["name"],
                        "update_scope": "full",
                        "doc_coverage": module.get("doc_coverage", 0)
                    }
                )
                if success:
                    created_tasks.append(task["id"])
            result["created_tasks"] = created_tasks
        
        if not json_mode:
            print(f"✅ 项目分析完成")
            print(f"   模块数：{len(result.get('modules', []))}")
            print(f"   总文件：{result.get('total_files', 0)}")
            print(f"   总代码行：{result.get('total_lines', 0)}")
            print(f"   文档目录：{output_dir}/")
            if create_tasks:
                print(f"   创建任务：{len(result.get('created_tasks', []))}")
        
        output(result, json_mode)
        
    except Exception as e:
        output({"error": str(e)}, json_mode)

# argparse 添加（第 1192 行后）
# analyze-project
ap_p = subparsers.add_parser("analyze-project", help="Analyze entire project structure")
ap_p.add_argument("--output-dir", default="docs", help="Documentation output directory")
ap_p.add_argument("--create-tasks", action="store_true", default=True, help="Create module analysis tasks")
ap_p.add_argument("--no-create-tasks", action="store_false", dest="create_tasks")
ap_p.add_argument("--force", action="store_true", help="Force re-analysis")

# analyze-module 参数修改
am_p.add_argument("--output-doc", action="store_true", help="Generate module documentation")

# 命令分发添加（第 1293 行后）
elif args.command == "analyze-project":
    cli.cmd_analyze_project(args.output_dir, args.create_tasks, args.force, json_mode)
```

### 9. 模块分析文档模板

```yaml
# templates/module-analysis.yaml
name: module-analysis
description: 模块分析文档模板
version: "1.0"
template_engine: jinja2

structure: |
  # {{ module_name }} 模块
  
  > 分析时间：{{ analyzed_at }}
  > 文件数：{{ file_count }} | 代码行数：{{ line_count }} | 文档覆盖：{{ doc_coverage }}%
  
  ## 概述
  
  {{ description or "（待补充模块概述）" }}
  
  ## 目录结构
  
  ```
  {{ directory_tree }}
  ```
  
  {% if classes %}
  ## 核心类
  
  | 类名 | 文件 | 说明 |
  |------|------|------|
  {% for cls in classes %}
  | `{{ cls.name }}` | `{{ cls.file }}` | {{ cls.docstring or "-" }} |
  {% endfor %}
  {% endif %}
  
  {% if functions %}
  ## 核心函数
  
  | 函数名 | 文件 | 参数 | 说明 |
  |--------|------|------|------|
  {% for func in functions %}
  | `{{ func.name }}` | `{{ func.file }}` | {{ func.parameters }} | {{ func.docstring or "-" }} |
  {% endfor %}
  {% endif %}
  
  ## 依赖关系
  
  ### 本模块依赖
  
  {% for dep in imports %}
  - {{ dep }}
  {% endfor %}
  
  ### 被依赖
  
  {% for dep in dependents %}
  - {{ dep }}
  {% endfor %}
  
  ## 使用示例
  
  ```{{ language }}
  # 待补充
  ```
  
  {% if suggestions %}
  ## 改进建议
  
  {% for suggestion in suggestions %}
  - {{ suggestion }}
  {% endfor %}
  {% endif %}
```

### 10. 输出文件结构

```
项目根目录/
├── docs/                           # 人类可读文档
│   ├── MODULES.md                  # 模块总览
│   ├── ARCHITECTURE.md             # 架构文档
│   └── modules/
│       ├── QAFetch.md
│       └── QAData.md
│
└── .long-run-agent/
    ├── config.json
    ├── task_list.json
    ├── analysis/                   # 机器可读摘要
    │   ├── summary.json            # 项目摘要
    │   ├── modules/                # 模块详情 JSON
    │   │   ├── QAFetch.json
    │   │   └── QAData.json
    │   └── dependencies.json       # 依赖图
    └── reports/
        └── sys_check_001.json
```

## 使用示例

```bash
# 1. 初始化项目
lra init --name QUANTAXIS

# 2. 执行完整项目分析
lra analyze-project

# 输出:
# ✅ 项目分析完成
#    模块数：15
#    总文件：245
#    总代码行：52340
#    文档目录：docs/
#    创建任务：15

# 3. 查看模块详情
lra analyze-module QAFetch --output-doc

# 4. 查看分析报告
lra system-check --report

# 5. Agent 读取生成的文档
# - .long-run-agent/analysis/summary.json  （快速查询）
# - docs/MODULES.md                         （人类可读）
```

## 实现优先级

| 优先级 | 任务 | 预计工作量 |
|--------|------|-----------|
| P0 | 修改 init 命令默认值 | 0.5h |
| P0 | 创建 ProjectAnalyzer 基础框架 | 2h |
| P0 | 实现 PythonParser | 3h |
| P0 | 重构 analyze-module 命令 | 1h |
| P0 | 新增 analyze-project 命令 | 2h |
| P1 | 实现 JavaScriptParser | 2h |
| P1 | 实现 GoParser | 2h |
| P1 | 创建文档模板 | 1h |
| P2 | 更新 README | 1h |
| P2 | 添加单元测试 | 3h |

## 风险与缓解

1. **大项目分析性能问题**
   - 缓解：增量分析，只分析变更文件
   - 缓解：并行处理多文件

2. **语言解析准确性**
   - 缓解：使用正则简化实现，接受 80% 准确率
   - 缓解：后续可引入 tree-sitter 提高准确性

3. **与现有功能兼容性**
   - 缓解：保持现有 API 不变，新增方法
   - 缓解：analyze-module 保持向后兼容