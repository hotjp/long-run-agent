#!/usr/bin/env python3
"""
浏览器自动化测试支持
v1.0 - 集成 Puppeteer/Playwright 验证
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from lra.config import Config


class BrowserAutomation:
    """浏览器自动化测试工具集成"""

    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path or os.getcwd())
        self.screenshot_dir = self.project_path / ".long-run-agent" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.results_path = self.project_path / ".long-run-agent" / "browser_test_results.json"

    def verify_feature(
        self, task_id: str, test_steps: List[str], auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        执行浏览器自动化验证

        参数:
            task_id: 任务ID
            test_steps: 测试步骤列表
            auto_execute: 是否自动执行（需要浏览器工具已安装）

        返回:
            {
                "success": True/False,
                "screenshots": ["step1.png", "step2.png"],
                "console_errors": [],
                "verification_report": "...",
                "timestamp": "..."
            }
        """
        result = {
            "task_id": task_id,
            "success": False,
            "screenshots": [],
            "console_errors": [],
            "verification_report": "",
            "test_steps": test_steps,
            "timestamp": datetime.now().isoformat(),
        }

        if not auto_execute:
            # 手动模式：生成测试模板
            result["verification_report"] = self._generate_manual_test_guide(task_id, test_steps)
            result["success"] = False
            result["message"] = "请手动执行测试并上传截图"
            return result

        # 自动模式：需要集成浏览器工具
        # 这里提供接口，实际执行需要外部工具
        result["message"] = "自动执行需要安装 Playwright/Puppeteer"
        result["hint"] = "运行: pip install playwright && playwright install"

        return result

    def _generate_manual_test_guide(self, task_id: str, test_steps: List[str]) -> str:
        """生成手动测试指南"""
        guide = f"""# 浏览器自动化测试指南

## 任务: {task_id}

## 测试步骤

"""
        for i, step in enumerate(test_steps, 1):
            guide += f"{i}. {step}\n"

        guide += f"""
## 验证清单

- [ ] 每个步骤执行成功
- [ ] 无控制台错误
- [ ] UI 显示正常
- [ ] 功能符合预期

## 截图要求

请在每个关键步骤后截图，保存到:
- {self.screenshot_dir}/step1.png
- {self.screenshot_dir}/step2.png
- ...

## 提交验证

完成测试后，将以下内容添加到任务文件:

```markdown
### 测试证据
- 截图路径: {self.screenshot_dir}/
- 测试时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 测试结果: ✅ 通过 / ❌ 失败
```
"""
        return guide

    def record_screenshot(self, task_id: str, step_name: str, screenshot_data: bytes) -> str:
        """
        记录截图

        返回: 截图保存路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_id}_{step_name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        with open(filepath, "wb") as f:
            f.write(screenshot_data)

        return str(filepath)

    def check_test_evidence(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        检查任务是否有测试证据

        返回: (是否有证据, 证据详情)
        """
        evidence = {
            "has_screenshots": False,
            "screenshot_files": [],
            "has_manual_test": False,
            "test_report_exists": False,
        }

        # 检查截图
        if self.screenshot_dir.exists():
            screenshots = list(self.screenshot_dir.glob(f"{task_id}_*.png"))
            evidence["has_screenshots"] = len(screenshots) > 0
            evidence["screenshot_files"] = [str(s) for s in screenshots]

        # 检查任务文件中的测试证据
        task_file = Path(Config.get_tasks_dir()) / f"{task_id}.md"
        if task_file.exists():
            content = task_file.read_text()
            if "测试证据" in content or "验证证据" in content:
                evidence["has_manual_test"] = True
            if "测试结果" in content:
                evidence["test_report_exists"] = True

        has_evidence = (
            evidence["has_screenshots"]
            or evidence["has_manual_test"]
            or evidence["test_report_exists"]
        )

        return has_evidence, evidence

    def generate_verification_script(self, task_id: str, test_steps: List[str]) -> str:
        """
        生成 Playwright 验证脚本

        返回: Python 脚本内容
        """
        script = f'''#!/usr/bin/env python3
"""
Playwright 浏览器自动化测试脚本
任务: {task_id}
生成时间: {datetime.now().isoformat()}
"""

from playwright.sync_api import sync_playwright
import time

def test_{task_id}():
    """执行测试: {task_id}"""
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 截图计数器
        screenshot_num = 0
        
        def take_screenshot(name=""):
            nonlocal screenshot_num
            screenshot_num += 1
            filename = "{task_id}_" + (f"{{name}}_" if name else "") + f"{{screenshot_num}}.png"
            filepath = "{self.screenshot_dir}/" + filename
            page.screenshot(path=filepath)
            print(f"📸 截图保存: {{filepath}}")
        
        try:
            # TODO: 根据测试步骤生成代码
            # 示例：
            # page.goto("http://localhost:3000")
            # take_screenshot("homepage")
            
'''

        for i, step in enumerate(test_steps, 1):
            script += f"            # 步骤 {i}: {step}\n"
            script += f"            # TODO: 实现此步骤\n"
            script += f"            # take_screenshot('step{i}')\n\n"

        script += f"""            print("✅ 测试完成")
            
        except Exception as e:
            print(f"❌ 测试失败: {{e}}")
            take_screenshot("error")
            raise
        
        finally:
            browser.close()

if __name__ == "__main__":
    test_{task_id}()
"""

        return script

    def save_verification_script(self, task_id: str, test_steps: List[str]) -> str:
        """保存验证脚本到文件"""
        script = self.generate_verification_script(task_id, test_steps)

        scripts_dir = self.project_path / ".long-run-agent" / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        script_path = scripts_dir / f"test_{task_id}.py"
        script_path.write_text(script, encoding="utf-8")

        return str(script_path)

    def get_verification_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务的验证状态"""
        has_evidence, evidence = self.check_test_evidence(task_id)

        status = {
            "task_id": task_id,
            "has_evidence": has_evidence,
            "evidence_details": evidence,
            "ready_for_completion": has_evidence,
            "recommendations": [],
        }

        if not has_evidence:
            status["recommendations"] = [
                "在任务文件中添加测试证据章节",
                f"上传截图到 {self.screenshot_dir}/",
                "记录测试步骤和结果",
                "运行: lra browser-test " + task_id + " --generate-script",
            ]

        return status
