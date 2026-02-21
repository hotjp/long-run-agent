#!/usr/bin/env python3
"""
需求文档管理器
v2.0 - 支持模板、校验、状态管理
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

try:
    from .config import Config, SafeJson
    from .status_manager import SpecStatus, SPEC_STATUS_INFO
except ImportError:
    print("警告: 无法导入模块")


SPEC_TEMPLATE = """# Feature {id} - {title}

## 元信息
- **优先级**: P1（必填，P0核心，P1重要，P2一般）
- **负责人**: （必填，填写负责人姓名/工号）
- **预计工时**: （可选，填写预计开发时长）
- **创建时间**: {created_at}

## 功能描述
<!-- 简要描述功能目标、应用场景，100字以内为宜 -->


## 功能设计方案
<!-- 详细的设计方案，包含核心逻辑、接口设计、数据流向等，可附加示意图 -->


## 开发步骤
- [ ] 步骤 1：（如：搭建xxx模块基础结构）
- [ ] 步骤 2：（如：开发xxx接口，实现xxx功能）
- [ ] 步骤 3：（如：单元测试）

## 测试用例
| 用例编号 | 场景 | 操作步骤 | 预期结果 |
|----------|------|----------|----------|
| TC-001 | ... | ... | ... |
| TC-002 | ... | ... | ... |

## 验收标准
- [ ] 标准 1：（如：接口调用成功，返回状态码200）
- [ ] 标准 2：（如：功能符合设计方案，无异常报错）

## 变更记录
| 日期 | 变更内容 | 变更人 |
|------|----------|--------|
| {date} | 初始创建 | - |
"""

REQUIRED_SECTIONS = {"元信息": ["优先级", "负责人"], "功能描述": [], "验收标准": []}


class SpecManager:
    """需求文档管理器"""

    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)
        self.specs_dir = Config.get_specs_dir()
        self._ensure_dir()

    def _ensure_dir(self):
        """确保目录存在"""
        os.makedirs(self.specs_dir, exist_ok=True)

    def _get_spec_path(self, feature_id: str) -> str:
        """获取需求文档路径"""
        return os.path.join(self.specs_dir, f"{feature_id}.md")

    def create_spec(
        self,
        feature_id: str,
        title: str = "待补充标题",
        priority: str = "P1",
        assignee: str = "",
    ) -> Tuple[bool, str]:
        """创建需求文档"""
        spec_path = self._get_spec_path(feature_id)

        if os.path.exists(spec_path):
            return False, f"需求文档已存在: {spec_path}"

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.now().strftime("%Y-%m-%d")

        content = SPEC_TEMPLATE.format(
            id=feature_id, title=title, created_at=created_at, date=date
        )

        try:
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, spec_path
        except Exception as e:
            return False, str(e)

    def get_spec(self, feature_id: str) -> Optional[str]:
        """获取需求文档内容"""
        spec_path = self._get_spec_path(feature_id)
        if not os.path.exists(spec_path):
            return None

        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return None

    def update_spec(self, feature_id: str, content: str) -> Tuple[bool, str]:
        """更新需求文档"""
        spec_path = self._get_spec_path(feature_id)

        try:
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, spec_path
        except Exception as e:
            return False, str(e)

    def validate_spec(self, feature_id: str) -> Dict[str, Any]:
        """校验需求文档完整性"""
        content = self.get_spec(feature_id)
        if not content:
            return {
                "valid": False,
                "missing": ["需求文档不存在"],
                "spec_status": SpecStatus.DRAFT.value,
            }

        missing = []

        for section, fields in REQUIRED_SECTIONS.items():
            section_pattern = rf"##\s*{section}"
            if not re.search(section_pattern, content, re.IGNORECASE):
                missing.append(f"缺失章节: {section}")
            else:
                section_match = re.search(
                    rf"##\s*{section}(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE
                )
                if section_match:
                    section_content = section_match.group(1)
                    for field in fields:
                        field_pattern = rf"\*\*{field}\*\*"
                        if not re.search(field_pattern, section_content):
                            missing.append(f"缺失字段: {section}/{field}")

        checklist_pattern = r"- \[x\].*验收标准"
        checklists = re.findall(r"- \[x\].*", content)
        if "验收标准" in content and len(checklists) == 0:
            missing.append("验收标准: 至少需要 1 条已勾选的标准")

        status = SpecStatus.DRAFT.value
        if len(missing) == 0:
            status = SpecStatus.REVIEWING.value
        elif len(missing) < 3:
            status = SpecStatus.DRAFT.value

        return {"valid": len(missing) == 0, "missing": missing, "spec_status": status}

    def get_spec_status(self, feature_id: str) -> str:
        """获取需求文档状态"""
        feature_list_path = Config.get_feature_list_path()
        feature_list = SafeJson.read(feature_list_path)

        if feature_list:
            for f in feature_list.get("features", []):
                if f.get("id") == feature_id:
                    return f.get("spec_status", SpecStatus.DRAFT.value)

        return SpecStatus.DRAFT.value

    def set_spec_status(
        self, feature_id: str, status: str, operator: str = "system"
    ) -> Tuple[bool, str]:
        """设置需求文档状态"""
        feature_list_path = Config.get_feature_list_path()
        feature_list = SafeJson.read(feature_list_path)

        if not feature_list:
            return False, "无法读取功能清单"

        for f in feature_list.get("features", []):
            if f.get("id") == feature_id:
                f["spec_status"] = status
                f["spec_status_updated_at"] = datetime.now().isoformat()
                break
        else:
            return False, f"未找到 Feature: {feature_id}"

        if SafeJson.write(feature_list_path, feature_list):
            return True, f"状态已更新为: {status}"
        return False, "保存失败"

    def list_specs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出需求文档"""
        feature_list_path = Config.get_feature_list_path()
        feature_list = SafeJson.read(feature_list_path)

        if not feature_list:
            return []

        specs = []
        for f in feature_list.get("features", []):
            spec_file = f.get("spec_file", f"{f['id']}.md")
            spec_path = os.path.join(self.specs_dir, spec_file)

            spec_info = {
                "feature_id": f.get("id"),
                "title": f.get("description", ""),
                "spec_status": f.get("spec_status", SpecStatus.DRAFT.value),
                "spec_exists": os.path.exists(spec_path),
                "priority": f.get("priority", "P1"),
                "assignee": f.get("assignee", ""),
            }

            if status is None or spec_info["spec_status"] == status:
                specs.append(spec_info)

        return specs

    def extract_checklist_progress(self, feature_id: str) -> Dict[str, Any]:
        """提取验收标准完成进度"""
        content = self.get_spec(feature_id)
        if not content:
            return {"total": 0, "completed": 0, "percentage": 0}

        total = len(re.findall(r"- \[[ x]\].*", content))
        completed = len(re.findall(r"- \[x\].*", content))

        return {
            "total": total,
            "completed": completed,
            "percentage": int(completed / total * 100) if total > 0 else 0,
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="需求文档管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    create_parser = subparsers.add_parser("create", help="创建需求文档")
    create_parser.add_argument("--feature-id", required=True, help="Feature ID")
    create_parser.add_argument("--title", default="待补充标题", help="标题")

    validate_parser = subparsers.add_parser("validate", help="校验需求文档")
    validate_parser.add_argument("--feature-id", required=True, help="Feature ID")

    get_parser = subparsers.add_parser("get", help="获取需求文档")
    get_parser.add_argument("--feature-id", required=True, help="Feature ID")

    list_parser = subparsers.add_parser("list", help="列出需求文档")
    list_parser.add_argument("--status", help="按状态筛选")

    status_parser = subparsers.add_parser("status", help="设置需求文档状态")
    status_parser.add_argument("--feature-id", required=True, help="Feature ID")
    status_parser.add_argument("--status", required=True, help="新状态")

    progress_parser = subparsers.add_parser("progress", help="获取验收标准进度")
    progress_parser.add_argument("--feature-id", required=True, help="Feature ID")

    args = parser.parse_args()

    manager = SpecManager()

    if args.command == "create":
        success, message = manager.create_spec(args.feature_id, args.title)
        if success:
            print(f"✅ 需求文档创建成功: {message}")
        else:
            print(f"❌ 创建失败: {message}")

    elif args.command == "validate":
        result = manager.validate_spec(args.feature_id)
        if result["valid"]:
            print("✅ 需求文档校验通过")
        else:
            print(f"❌ 需求文档不完整:\n")
            for m in result["missing"]:
                print(f"  - {m}")
            print(f"\n状态: {result['spec_status']}")

    elif args.command == "get":
        content = manager.get_spec(args.feature_id)
        if content:
            print(content)
        else:
            print(f"❌ 未找到需求文档: {args.feature_id}")

    elif args.command == "list":
        specs = manager.list_specs(args.status)
        if not specs:
            print("没有找到需求文档")
        else:
            print(f"\n📋 需求文档列表 ({len(specs)} 个):\n")
            for s in specs:
                info = SPEC_STATUS_INFO.get(
                    s["spec_status"], {"emoji": "❓", "name": s["spec_status"]}
                )
                exists = "✅" if s["spec_exists"] else "❌"
                print(f"{info['emoji']} {s['feature_id']}: {s['title'][:40]}")
                print(
                    f"   状态: {info['name']} | 文件: {exists} | 优先级: {s['priority']}"
                )
                print()

    elif args.command == "status":
        success, message = manager.set_spec_status(args.feature_id, args.status)
        print(f"{'✅' if success else '❌'} {message}")

    elif args.command == "progress":
        progress = manager.extract_checklist_progress(args.feature_id)
        print(f"\n📊 验收标准进度:\n")
        print(f"  总数: {progress['total']}")
        print(f"  完成: {progress['completed']}")
        print(f"  进度: {progress['percentage']}%")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
