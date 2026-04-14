"""
下一步引导系统
为Agent提供友好的操作指引
"""

from typing import Optional, List


class NextStepGuide:
    """下一步引导系统"""

    @staticmethod
    def after_init(project_name: str) -> str:
        """初始化项目后引导"""
        return f"""
✅ 项目初始化成功: {project_name}

💡 建议下一步:
  • 查看Constitution: lra constitution show
  • 创建第一个任务: lra create "任务描述"
  • 查看项目状态: lra context

📚 帮助: lra --help
"""

    @staticmethod
    def after_create(task_id: str, template: str, has_design: bool = False) -> str:
        """创建任务后引导"""
        if has_design:
            return f"""
✅ 任务创建成功: {task_id}
   模板: {template}

💡 建议下一步:
    lra claim {task_id}

📚 帮助: lra --help
"""
        return f"""
✅ 任务创建成功: {task_id}
   模板: {template}

💡 建议下一步:
   lra create "xxx" -var '{{"requirements":"...","acceptance":["..."],"design":"..."}}'
   填好设计后才可认领: lra claim {task_id}

📚 帮助: lra --help
"""

    @staticmethod
    def after_claim(task_id: str) -> str:
        """认领任务后引导"""
        return f"""
✅ 任务已认领: {task_id}

💡 建议下一步:
  • 查看详情: lra show {task_id}
  • 开始执行: 编辑任务文件实现功能
  • 更新状态: lra set {task_id} in_progress
  • 提交心跳: lra heartbeat {task_id}

📚 帮助: lra --help
"""

    @staticmethod
    def after_complete(
        task_id: str, constitution_passed: bool, failures: Optional[List[str]] = None
    ) -> str:
        """完成任务后引导"""
        if constitution_passed:
            return f"""
✅ 任务完成: {task_id}
   Constitution验证: 通过

💡 建议下一步:
  • 查看其他任务: lra list
  • 创建新任务: lra create "描述"
  • 查看项目状态: lra context

📚 帮助: lra --help
"""
        else:
            failures_str = "\n".join([f"  • {f}" for f in (failures or [])])
            return f"""
⚠️  Constitution验证失败: {task_id}

失败项:
{failures_str}

💡 建议下一步:
  • 查看详情: lra show {task_id}
  • 修复问题后重新完成: lra set {task_id} completed
  • 查看Constitution: lra constitution show

📚 帮助: lra --help
"""

    @staticmethod
    def after_constitution_init() -> str:
        """初始化Constitution后引导"""
        return """
✅ Constitution初始化成功

💡 建议下一步:
  • 查看配置: lra constitution show
  • 编辑配置: 编辑 .long-run-agent/constitution.yaml
  • 验证配置: lra constitution validate
  • 创建任务: lra create "任务描述"

📚 帮助: lra --help
"""

    @staticmethod
    def constitution_help() -> str:
        """Constitution帮助信息"""
        return """
🏛️  Constitution - 项目质量宪法

概念:
  Constitution定义项目的不可协商原则和质量标准
  在任务完成前自动验证，确保质量底线

三层原则:
  • NON_NEGOTIABLE - 不可协商，所有门禁必须通过
  • MANDATORY - 强制，必需门禁必须通过
  • CONFIGURABLE - 可配置，可启用/禁用

门禁类型:
  • command - 执行shell命令检查
  • field_exists - 检查任务文件字段
  • custom - 自定义检查函数

工作流:
  1. lra constitution init          # 初始化
  2. 编辑配置文件                    # 自定义原则
  3. lra constitution validate      # 验证配置
  4. lra create "任务"              # 创建任务
  5. lra set task_001 completed     # 自动验证

示例配置:
  # .long-run-agent/constitution.yaml
  core_principles:
    - id: "no_broken_tests"
      type: "NON_NEGOTIABLE"
      name: "测试必须通过"
      gates:
        - type: "command"
          command: "pytest tests/"

详细文档:
  • docs/CONSTITUTION_DESIGN.md
  • docs/IMPLEMENTATION_GUIDE.md
"""
