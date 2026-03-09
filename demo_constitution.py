#!/usr/bin/env python3
"""
Constitution 功能演示脚本
展示LRA v5.0的核心能力
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lra.constitution import (
    ConstitutionManager,
    PrincipleValidator,
    create_default_constitution,
    init_constitution,
)


def print_header(title):
    """打印标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_section(title):
    """打印小节标题"""
    print(f"\n## {title}\n")


def demo_constitution_basics():
    """演示Constitution基础功能"""
    print_header("Constitution 基础功能演示")

    # 1. 创建默认Constitution
    print_section("1. 创建默认Constitution")
    constitution = create_default_constitution("Demo Project")
    print(f"✅ Constitution创建成功")
    print(f"   项目名: {constitution['project']['name']}")
    print(f"   版本: {constitution['project']['version']}")
    print(f"   原则数量: {len(constitution['core_principles'])}")

    # 2. 初始化ConstitutionManager
    print_section("2. 初始化Constitution管理器")
    try:
        manager = ConstitutionManager()
        print(f"✅ ConstitutionManager初始化成功")
        print(f"   Schema版本: {manager.constitution['schema_version']}")
    except Exception as e:
        print(f"⚠️  使用默认Constitution: {e}")
        manager = ConstitutionManager()
        print(f"✅ 使用默认Constitution成功")

    # 3. 获取原则列表
    print_section("3. 获取原则列表")

    non_negotiable = manager.get_non_negotiable_principles()
    print(f"📋 不可协商原则 (NON_NEGOTIABLE): {len(non_negotiable)}个")
    for p in non_negotiable:
        print(f"   • {p['name']}: {p['description']}")

    mandatory = manager.get_mandatory_principles()
    print(f"\n📋 强制原则 (MANDATORY): {len(mandatory)}个")
    for p in mandatory:
        print(f"   • {p['name']}: {p['description']}")

    configurable = manager.get_enabled_configurable_principles()
    print(f"\n📋 启用的可配置原则 (CONFIGURABLE): {len(configurable)}个")
    for p in configurable:
        print(f"   • {p['name']}: {p['description']}")

    # 4. 获取所有适用原则
    print_section("4. 获取所有适用原则")
    all_principles = manager.get_all_applicable_principles()
    print(f"✅ 总共适用原则: {len(all_principles)}个")

    # 5. 验证原则
    print_section("5. 验证原则")
    validator = PrincipleValidator(manager)

    # 模拟任务
    mock_task = {
        "id": "demo_task",
        "description": "Demo task for testing",
        "template": "code-module",
    }

    # 验证所有原则
    result = validator.validate_all_principles("demo_task", mock_task)

    print(f"验证结果: {'✅ 通过' if result.passed else '❌ 失败'}")
    print(f"消息: {result.message}")

    if result.failures:
        print(f"\n失败项 ({len(result.failures)}):")
        for failure in result.failures:
            print(f"   ❌ {failure}")

    if result.warnings:
        print(f"\n警告项 ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   ⚠️  {warning}")

    if result.gate_results:
        print(f"\n门禁详情 ({len(result.gate_results)}个门禁):")
        for gate in result.gate_results[:5]:  # 只显示前5个
            status = "✅" if gate["passed"] else "❌"
            print(f"   {status} {gate['gate_name']}: {gate['message']}")


def demo_principle_types():
    """演示不同类型的原则"""
    print_header("原则类型演示")

    print("Constitution支持三种原则类型:\n")

    print("1. NON_NEGOTIABLE (不可协商)")
    print("   • 所有门禁必须通过")
    print("   • 违反则无法完成任务")
    print("   • 示例: 测试必须通过、证据必需\n")

    print("2. MANDATORY (强制)")
    print("   • 必需门禁必须通过")
    print("   • 可记录例外情况")
    print("   • 示例: 无语法错误、类型检查\n")

    print("3. CONFIGURABLE (可配置)")
    print("   • 可启用/禁用")
    print("   • 灵活调整项目需求")
    print("   • 示例: 文档同步、性能测试\n")


def demo_gate_types():
    """演示不同类型的门禁"""
    print_header("门禁类型演示")

    print("Constitution支持三种门禁类型:\n")

    print("1. command (命令门禁)")
    print("   • 执行shell命令")
    print("   • 检查退出码")
    print("   • 示例: pytest tests/ -v\n")

    print("2. field_exists (字段门禁)")
    print("   • 检查任务文件中是否存在字段")
    print("   • 支持Markdown格式")
    print("   • 示例: test_evidence, verification_steps\n")

    print("3. custom (自定义门禁)")
    print("   • 执行自定义检查函数")
    print("   • 支持内置和自定义函数")
    print("   • 示例: validate_constitution_yaml\n")


def demo_workflow():
    """演示完整工作流程"""
    print_header("完整工作流程演示")

    print("Constitution集成的完整工作流程:\n")

    print("1️⃣  定义Constitution")
    print("   创建constitution.yaml配置文件\n")

    print("2️⃣  创建任务")
    print('   lra create "实现新功能" --template code-module\n')

    print("3️⃣  执行任务")
    print("   编写代码、测试、文档...\n")

    print("4️⃣  提交完成")
    print("   lra set task_001 completed\n")

    print("5️⃣  Constitution验证")
    print("   • 自动执行所有门禁")
    print("   • 显示验证结果\n")

    print("6️⃣  结果处理")
    print("   ✅ 全部通过 → 任务完成")
    print("   ❌ 部分失败 → 进入Ralph Loop优化\n")


def demo_benefits():
    """演示核心价值"""
    print_header("核心价值演示")

    print("Constitution机制的核心价值:\n")

    print("✅ 规范驱动")
    print("   从任务驱动到规范驱动")
    print("   明确质量标准，前置约束\n")

    print("✅ 不可妥协")
    print("   NON_NEGOTIABLE原则强制执行")
    print("   确保底线质量\n")

    print("✅ 自我强化")
    print("   自举式开发验证设计")
    print("   持续改进循环\n")

    print("✅ 灵活可配")
    print("   支持三层原则体系")
    print("   适应不同项目需求\n")


def main():
    """主演示函数"""
    print("\n" + "=" * 60)
    print("  LRA v5.0 - Constitution 功能演示")
    print("=" * 60)

    try:
        # 1. 基础功能演示
        demo_constitution_basics()

        # 2. 原则类型演示
        demo_principle_types()

        # 3. 门禁类型演示
        demo_gate_types()

        # 4. 工作流程演示
        demo_workflow()

        # 5. 核心价值演示
        demo_benefits()

        print_header("演示完成")
        print("✅ Constitution核心功能验证成功！\n")
        print("📚 查看完整文档:")
        print("   • FUSION_DESIGN.md - 融合设计总览")
        print("   • docs/CONSTITUTION_DESIGN.md - 详细设计")
        print("   • docs/BOOTSTRAPPING.md - 自举开发流程")
        print("   • docs/IMPLEMENTATION_GUIDE.md - 实施指南\n")

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
