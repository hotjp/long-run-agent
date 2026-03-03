# LRA v4.0 - 安装与使用指南

## 🎉 重命名完成！

LRA (Long-Run-Agent) v4.0 已成功从 `long-run-agent` 重命名为 `lra`。

---

## 📦 安装

### 方式1: 从源码安装（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/clawdbot-ai/long-run-agent.git
cd long-run-agent

# 2. 安装
pip install -e .

# 3. 验证安装
python3 -m lra --help
lra --help
```

### 方式2: 从 PyPI 安装（即将发布）

```bash
pip install lra
```

### 方式3: 使用 Node.js 包装器

```bash
npm install -g lra
lra --help
```

---

## ✅ 验证安装

```bash
# 查看版本
$ python3 -c "from lra import __version__; print(__version__)"
4.0.0

# 查看帮助
$ lra --help
LRA v4.0 - AI Agent Task Manager

# 测试命令
$ lra status
📊 项目进度: 0/0 (0.0%)
```

---

## 🚀 快速开始

### 1. 初始化项目

```bash
# 创建新项目
mkdir my-project && cd my-project

# 初始化 LRA
lra init --name "My Project"

# 查看项目结构
lra where
```

### 2. 分析项目

```bash
# 分析现有项目
lra analyze-project

# 查看生成的文档
cat docs/MODULES.md
```

### 3. 创建任务

```bash
# 创建任务
lra create "实现用户登录功能" --template code-module --priority P0

# 查看任务
lra show task_001
```

### 4. 工作流程

```bash
# Agent 专用：上下文重建
lra orientation

# 查看项目进度
lra status

# 领取任务
lra claim task_001

# ... 实现任务 ...

# 运行回归测试
lra regression-test

# 检查代码质量
lra quality-check

# 标记完成
lra set task_001 completed
```

---

## 🆕 v4.0 新功能

### 新增命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `status` | 项目进度可视化 | `lra status` |
| `orientation` | Agent上下文重建 | `lra orientation` |
| `regression-test` | 回归测试 | `lra regression-test` |
| `browser-test` | 浏览器自动化测试 | `lra browser-test task_001` |
| `quality-check` | 代码质量检查 | `lra quality-check` |

### 增强的模板

v4.0 的任务模板现在包含**验证证据**字段：

```markdown
## 验证证据（完成前必填）

- [ ] **实现证明**: [描述实现]
- [ ] **测试验证**: [如何测试]
- [ ] **影响范围**: [影响的功能]

### 测试步骤
1. [步骤1]
2. [步骤2]

### 验证结果
[测试输出/截图]
```

---

## 📚 文档

- **快速开始**: `QUICK_START.md`
- **迁移指南**: `MIGRATION_GUIDE.md`
- **实施报告**: `IMPLEMENTATION_REPORT.md`
- **重命名报告**: `RENAME_REPORT.md`
- **Agent指南**: `lra/prompts/agent_prompt.md`

---

## 🔄 从 v3.x 迁移

### 卸载旧版本

```bash
pip uninstall long-run-agent -y
```

### 安装新版本

```bash
cd /path/to/long-run-agent
pip install -e .
```

### 无需数据迁移

项目数据存储在 `.long-run-agent/` 目录，格式**完全兼容**：

```bash
# 现有项目可直接使用
cd /path/to/existing/project
lra status  # ✅ 正常工作
```

---

## 💡 使用示例

### 示例1: 新项目

```bash
mkdir my-app && cd my-app
lra init --name "My App"
lra create "搭建项目结构" --priority P0
lra create "实现核心功能" --priority P1
lra create "编写单元测试" --priority P1
lra status
```

### 示例2: Agent 工作流

```bash
# 1. 上下文重建
lra orientation

# 2. 领取任务
lra claim task_001

# 3. 实现任务
# ... 编码 ...

# 4. 验证
lra browser-test task_001 --script
lra regression-test

# 5. 质量检查
lra quality-check

# 6. 提交
git add . && git commit -m "feat: implement task_001"
```

### 示例3: 团队协作

```bash
# 大模型拆分任务
lra split task_001 --plan '[...]'

# 发布子任务
lra publish task_001

# 小模型领取子任务
lra context --output-limit 8k
lra claim task_001_01

# 完成子任务
lra set task_001_01 completed
```

---

## ⚙️ 配置

### Python 版本要求

- Python ≥ 3.8

### 依赖

**必需依赖**:
- `jinja2>=3.0`
- `pyyaml>=6.0`

**可选依赖**:
- `playwright>=1.40.0` (浏览器自动化测试)

```bash
# 安装可选依赖
pip install playwright>=1.40.0
playwright install
```

---

## 🐛 故障排除

### 问题1: 找不到命令

```bash
$ lra --help
bash: lra: command not found
```

**解决方案**:
```bash
# 重新安装
pip install -e .

# 或使用模块方式
python3 -m lra --help
```

### 问题2: 导入错误

```bash
ModuleNotFoundError: No module named 'long_run_agent'
```

**解决方案**:
```python
# 更新导入语句
# 旧: from long_run_agent import ...
# 新: from lra import ...
```

### 问题3: 旧项目兼容性

```bash
$ lra status
❌ 项目未初始化
```

**解决方案**:
```bash
# 检查配置文件
cat .long-run-agent/config.json

# 如果存在，直接使用
lra status  # ✅ 应该正常工作
```

---

## 📞 获取帮助

```bash
# 查看帮助
lra --help
lra <command> --help

# 查看文档
cat QUICK_START.md
cat lra/prompts/agent_prompt.md

# 查看版本
python3 -c "from lra import __version__; print(__version__)"
```

---

## ✨ 总结

LRA v4.0 主要变化：

✅ **包名简化**: `long-run-agent` → `lra`
✅ **版本升级**: v3.4.1 → v4.0.0
✅ **功能增强**: 新增7大质量保障功能
✅ **向后兼容**: 项目数据100%兼容
✅ **无缝迁移**: 只需重新安装

**开始使用 LRA v4.0 吧！** 🚀

---

**安装日期**: 2026-03-03
**版本**: LRA v4.0.0
**状态**: ✅ 生产就绪
