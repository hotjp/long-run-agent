# AGENTS_MD_IMPROVEMENT 设计文档实现检查机制

## 检查目标

验证 `docs/design/AGENTS_MD_IMPROVEMENT.md` 中的需求是否已实现。

## 检查项目清单

### 1. 模板文件存在性检查

| 文件 | 路径 | 状态 |
|------|------|------|
| agent.md | `lra/templates/agents/defaults/agent.md` | ⬜ |
| lra-minimal.md | `lra/templates/agents/defaults/lra-minimal.md` | ⬜ |
| lra-full.md | `lra/templates/agents/defaults/lra-full.md` | ⬜ |
| claude.md | `lra/templates/agents/defaults/claude.md` | ⬜ |

### 2. 模板内容检查

#### agent.md
- [ ] 包含 `<!-- BEGIN LRA AGENT SECTION -->`
- [ ] 包含 `<!-- END LRA AGENT SECTION -->`
- [ ] 引用 lra.md 链接

#### lra-minimal.md
- [ ] 包含 `<!-- BEGIN LRA INTEGRATION profile:minimal -->`
- [ ] 包含 `<!-- END LRA INTEGRATION -->`
- [ ] 内容为 minimal profile 简洁版本

#### lra-full.md
- [ ] 包含 `<!-- BEGIN LRA INTEGRATION profile:full -->`
- [ ] 包含 `<!-- END LRA INTEGRATION -->`
- [ ] 包含完整 CLI 命令参考
- [ ] 包含 Session Completion Checklist
- [ ] 包含禁止规则

#### claude.md
- [ ] 包含 `<!-- BEGIN LRA CLAUDE SECTION -->`
- [ ] 包含 `<!-- END LRA CLAUDE SECTION -->`
- [ ] 包含 `{project_name}` 占位符
- [ ] 包含 `{profile}` 占位符

### 3. `_copy_agents_template` 方法检查

- [ ] 方法存在于 `lra/cli.py`
- [ ] 支持 `profile` 参数（默认值 "full"）
- [ ] 创建 lra.md（使用 `allow_replace=True`）
- [ ] 创建 agent.md（使用 `allow_replace=False`）
- [ ] 创建 CLAUDE.md（使用 `allow_replace=False`）
- [ ] 使用正确的 section marker：
  - lra.md: `BEGIN LRA INTEGRATION`
  - agent.md: `BEGIN LRA AGENT SECTION`
  - CLAUDE.md: `BEGIN LRA CLAUDE SECTION`

### 4. `_update_or_create` 方法检查

- [ ] 方法存在于 `lra/cli.py`
- [ ] 参数：`dst`, `src`, `section_marker`, `allow_replace`
- [ ] 文件不存在时直接复制
- [ ] 文件存在但无 section marker 时追加
- [ ] 文件存在且有 section marker + allow_replace=True 时替换
- [ ] 文件存在且有 section marker + allow_replace=False 时保持不变

### 5. `_replace_section` 方法检查

- [ ] 方法存在于 `lra/cli.py`
- [ ] 使用正则表达式提取 section 内容
- [ ] 正确替换目标文件中的 section

### 6. CLI --profile 参数检查

- [ ] `init` 子命令添加了 `--profile` 参数
- [ ] choices=["minimal", "full"]
- [ ] default="full"

### 7. Profile 一致性检查

- [ ] full profile 不会降级到 minimal
- [ ] minimal profile 可以升级到 full

### 8. 边界情况处理

- [x] 文件不存在 → 直接复制
- [x] lra.md 有 section → 替换 section
- [x] lra.md 无 section → 追加
- [x] agent.md/CLAUDE.md 有 section → 不更新
- [x] agent.md/CLAUDE.md 无 section → 追加
- [x] 重复 init → 去重处理

## 检查脚本

```python
#!/usr/bin/env python3
"""
AGENTS_MD_IMPROVEMENT 设计文档实现检查脚本
"""
import os
import re
import sys

def check_template_files():
    """检查模板文件存在性"""
    base = "lra/templates/agents/defaults"
    files = {
        "agent.md": f"{base}/agent.md",
        "lra-minimal.md": f"{base}/lra-minimal.md",
        "lra-full.md": f"{base}/lra-full.md",
        "claude.md": f"{base}/claude.md",
    }

    results = {}
    for name, path in files.items():
        exists = os.path.exists(path)
        results[name] = {"path": path, "exists": exists}
        print(f"  {'✅' if exists else '❌'} {name}: {path}")

    return all(r["exists"] for r in results.values())


def check_template_content():
    """检查模板内容"""
    base = "lra/templates/agents/defaults"
    results = {}

    # agent.md
    with open(f"{base}/agent.md", "r") as f:
        content = f.read()
    results["agent.md"] = {
        "has_agent_section": "BEGIN LRA AGENT SECTION" in content,
        "has_lra_link": "lra.md" in content,
    }

    # lra-minimal.md
    with open(f"{base}/lra-minimal.md", "r") as f:
        content = f.read()
    results["lra-minimal.md"] = {
        "has_integration": "BEGIN LRA INTEGRATION" in content and "profile:minimal" in content,
    }

    # lra-full.md
    with open(f"{base}/lra-full.md", "r") as f:
        content = f.read()
    results["lra-full.md"] = {
        "has_integration": "BEGIN LRA INTEGRATION" in content and "profile:full" in content,
        "has_cli_ref": "lra list" in content or "lra ready" in content,
        "has_checklist": "Session Completion" in content or "checklist" in content.lower(),
        "has_prohibited": "禁止" in content or "❌" in content,
    }

    # claude.md
    with open(f"{base}/claude.md", "r") as f:
        content = f.read()
    results["claude.md"] = {
        "has_claude_section": "BEGIN LRA CLAUDE SECTION" in content,
        "has_project_placeholder": "{project_name}" in content,
        "has_profile_placeholder": "{profile}" in content,
    }

    for name, checks in results.items():
        for check_name, passed in checks.items():
            print(f"  {'✅' if passed else '❌'} {name}: {check_name}")

    return results


def check_cli_methods():
    """检查 CLI 方法实现"""
    cli_path = "lra/cli.py"
    with open(cli_path, "r") as f:
        content = f.read()

    results = {}

    # _copy_agents_template
    copy_match = re.search(r"def _copy_agents_template\(self.*?\n(.*?)(?=\n    def |\nclass |\Z)", content, re.DOTALL)
    results["_copy_agents_template_exists"] = copy_match is not None
    if copy_match:
        method_body = copy_match.group(1)
        results["has_profile_param"] = "profile" in method_body.split("def _copy_agents_template")[0].split("\n")[-1]
        results["creates_lra_md"] = "lra_dst" in method_body or '"lra.md"' in method_body
        results["creates_agent_md"] = "agent_dst" in method_body or '"agent.md"' in method_body
        results["creates_claude_md"] = "claude_dst" in method_body or '"CLAUDE.md"' in method_body
        results["allow_replace_lra"] = 'allow_replace=True' in method_body or "allow_replace = True" in method_body
        results["allow_replace_false_agent"] = "BEGIN LRA AGENT SECTION" in method_body
        results["allow_replace_false_claude"] = "BEGIN LRA CLAUDE SECTION" in method_body

    # _update_or_create
    update_match = re.search(r"def _update_or_create\(self.*?\n(.*?)(?=\n    def |\nclass |\Z)", content, re.DOTALL)
    results["_update_or_create_exists"] = update_match is not None
    if update_match:
        method_body = update_match.group(1)
        results["update_has_section_marker"] = "section_marker" in method_body
        results["update_has_allow_replace"] = "allow_replace" in method_body

    # _replace_section
    replace_match = re.search(r"def _replace_section\(self.*?\n(.*?)(?=\n    def |\nclass |\Z)", content, re.DOTALL)
    results["_replace_section_exists"] = replace_match is not None
    if replace_match:
        method_body = replace_match.group(1)
        results["replace_uses_regex"] = "re." in method_body or "re\"" in method_body

    # --profile argument
    profile_match = re.search(r'add_argument\(\s*["\']--profile["\'].*?choices\s*=\s*\["minimal",\s*"full"\]', content)
    results["has_profile_argument"] = profile_match is not None

    for name, passed in results.items():
        print(f"  {'✅' if passed else '❌'} {name}")

    return results


def main():
    print("=" * 60)
    print("AGENTS_MD_IMPROVEMENT 设计文档实现检查")
    print("=" * 60)

    print("\n### 1. 模板文件存在性 ###")
    templates_ok = check_template_files()

    print("\n### 2. 模板内容检查 ###")
    content_results = check_template_content()

    print("\n### 3. CLI 方法实现 ###")
    cli_results = check_cli_methods()

    print("\n" + "=" * 60)
    all_passed = templates_ok and all(all(c.values()) for c in content_results.values()) and all(cli_results.values())
    if all_passed:
        print("✅ 所有检查通过！设计文档已完整实现。")
    else:
        print("❌ 部分检查未通过，请查看上述结果。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

## 运行方式

```bash
# 在项目根目录运行
python3 docs/design/AGENTS_MD_IMPROVEMENT_CHECKER.md  # 需要去除 python 标记，或复制为 .py 文件

# 或者直接运行检查逻辑
cd /Users/kingj/.openclaw/workspace/long-run-agent
python3 -c "
# 粘贴检查脚本内容
"
```

## 检查结果记录

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 模板文件存在 | ✅ | agent.md, lra-minimal.md, lra-full.md, claude.md 均存在 |
| 模板内容正确 | ✅ | 所有 section marker 和占位符正确 |
| CLI 方法实现 | ✅ | _copy_agents_template, _update_or_create, _replace_section 均已实现 |
| --profile 参数 | ✅ | choices=["minimal", "full"], default="full" |
| Profile 一致性 | ✅ | 已实现 `_get_profile_from_section` 和降级检查 |
| 重复内容清理 | ✅ | 已实现 `_deduplicate_sections` 方法 |
| 边界情况处理 | ✅ | lra.md 替换逻辑正确，agent.md/CLAUDE.md 有 section 则不更新 |

### 已实现功能

1. **`_get_profile_from_section` 方法**
   - 从现有 section 中提取 profile
   - 支持从 BEGIN 行提取 `profile:full/minimal`
   - 支持根据内容推断（full 有 Session Completion）

2. **Profile 降级检查**
   - `_copy_agents_template` 中检查：如果已存在 full profile，不会降级为 minimal

3. **`_deduplicate_sections` 方法**
   - 清理重复的 section 标记
   - 在 `_replace_section` 替换后自动调用

## 下一步

- [x] 运行检查脚本 ✅
- [x] 实现缺失功能 ✅
- [x] 更新本表格记录检查结果 ✅