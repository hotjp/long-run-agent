# LRA v4.0 迁移指南

## 📋 概述

LRA v4.0 是一次重大更新，将包名从 `long-run-agent` 改为 `lra`，并新增了多项质量保障功能。

---

## 🔄 重大变更

### 1. 包名变更

| v3.x | v4.0+ |
|------|-------|
| `long-run-agent` | `lra` |
| `long_run_agent` | `lra` |

### 2. 目录结构变化

```
# v3.x
long_run_agent/
├── __init__.py
├── cli.py
├── task_manager.py
└── ...

# v4.0+
lra/
├── __init__.py
├── cli.py
├── cli_extensions.py      # 新增
├── browser_automation.py  # 新增
├── regression_test.py     # 新增
├── quality_checker.py     # 新增
├── prompts/               # 新增
│   └── agent_prompt.md
└── ...
```

### 3. 导入路径变化

```python
# v3.x
from long_run_agent import TaskManager
from long_run_agent.config import Config

# v4.0+
from lra import TaskManager
from lra.config import Config
```

---

## 🆕 新增功能

### 1. 质量保障系统

- ✅ 验证前置机制
- ✅ 回归测试
- ✅ 浏览器自动化测试
- ✅ 代码质量检查

### 2. Agent工作流优化

- ✅ 上下文重建协议
- ✅ 进度可视化增强
- ✅ 统一提示词模板

### 3. 新增命令

| 命令 | 说明 |
|------|------|
| `lra status` | 项目进度可视化 |
| `lra orientation` | Agent上下文重建 |
| `lra regression-test` | 回归测试 |
| `lra browser-test <id>` | 浏览器自动化测试 |
| `lra quality-check` | 代码质量检查 |

---

## 📦 安装迁移

### 卸载旧版本

```bash
pip uninstall long-run-agent -y
```

### 安装新版本

```bash
# 从源码安装
cd /path/to/long-run-agent
pip install -e .

# 或从 PyPI 安装（发布后）
pip install lra
```

---

## 🔧 项目迁移步骤

### 1. 更新 .long-run-agent 配置

```bash
# 检查配置文件
cat .long-run-agent/config.json
```

配置文件格式**保持不变**，无需修改。

### 2. 重新安装

```bash
# 卸载旧版本
pip uninstall long-run-agent -y

# 安装新版本
pip install -e .
```

### 3. 验证安装

```bash
# 检查版本
lra --version
# 输出: lra 4.0.0

# 测试命令
lra status
lra orientation
```

---

## 📚 API 变化

### 兼容的 API（无变化）

- `TaskManager` - 所有方法保持不变
- `TemplateManager` - 所有方法保持不变
- `Config` - 所有方法保持不变
- `LocksManager` - 所有方法保持不变

### 新增 API

```python
from lra.browser_automation import BrowserAutomation
from lra.regression_test import RegressionTestManager
from lra.quality_checker import QualityChecker
from lra.cli_extensions import CLIExtensions
```

---

## 🐛 常见问题

### Q1: 导入错误 `ModuleNotFoundError: No module named 'long_run_agent'`

**解决方案**: 更新导入语句

```python
# 旧代码
from long_run_agent import TaskManager

# 新代码
from lra import TaskManager
```

### Q2: 命令找不到 `lra: command not found`

**解决方案**: 重新安装

```bash
pip uninstall long-run-agent -y
pip install -e .
```

### Q3: 旧的项目能否继续使用？

**回答**: 可以。项目数据存储在 `.long-run-agent/` 目录，格式未变化。只需重新安装新版本 CLI 即可。

### Q4: 3.x 版本的数据会丢失吗？

**回答**: 不会。所有数据存储在 `.long-run-agent/` 目录，与代码包名无关。升级后可继续使用。

---

## 📊 兼容性矩阵

| 项目数据格式 | v3.x | v4.0+ |
|-------------|------|-------|
| `.long-run-agent/config.json` | ✅ | ✅ |
| `.long-run-agent/task_list.json` | ✅ | ✅ |
| `.long-run-agent/locks.json` | ✅ | ✅ |
| `.long-run-agent/templates/` | ✅ | ✅ |
| `.long-run-agent/tasks/` | ✅ | ✅ |
| `.long-run-agent/records/` | ✅ | ✅ |

**结论**: 项目数据100%兼容，无需迁移数据。

---

## 🚀 推荐工作流（v4.0）

### 新项目

```bash
# 1. 初始化
lra init --name "My Project"

# 2. 分析项目
lra analyze-project

# 3. 开始工作
lra orientation
lra status
```

### 现有项目

```bash
# 1. 继续工作
cd /path/to/existing/project

# 2. 查看进度
lra status

# 3. 运行回归测试（可选）
lra regression-test

# 4. 质量检查（可选）
lra quality-check
```

---

## 📝 注意事项

1. **Python 版本**: 仍然要求 Python ≥ 3.8
2. **依赖**: 新增可选依赖 `playwright>=1.40.0`
3. **配置**: 配置文件格式完全兼容
4. **数据**: 所有项目数据保持不变

---

## 🎯 总结

LRA v4.0 的主要变化：

✅ **包名简化**: `long-run-agent` → `lra`
✅ **功能增强**: 新增质量保障系统
✅ **向后兼容**: 项目数据100%兼容
✅ **无缝迁移**: 只需重新安装即可

**升级建议**: 所有用户建议升级到 v4.0，享受更强大的质量保障功能。

---

**迁移日期**: 2026-03-03
**版本**: LRA v4.0.0
**状态**: ✅ 完全兼容
