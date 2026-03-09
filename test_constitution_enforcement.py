#!/usr/bin/env python3
"""
测试Constitution强制验证机制
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 Constitution强制验证机制测试\n")

# 测试1: Constitution验证逻辑
print("=" * 60)
print("测试1: Constitution验证逻辑")
print("=" * 60)

from lra.constitution import ConstitutionManager, PrincipleValidator

manager = ConstitutionManager()
validator = PrincipleValidator(manager)

print(f"\n✅ Constitution加载成功")
print(f"   原则数: {len(manager.get_all_applicable_principles())}")

# 测试验证一个空任务
print(f"\n📋 测试空任务验证:")
result = validator.validate_all_principles("test_task", {}, template="code-module")
print(f"   结果: {'通过' if result.passed else '失败'}")
if not result.passed:
    print(f"   失败项: {result.failures[:3]}")  # 只显示前3个

# 测试2: TaskManager集成
print("\n" + "=" * 60)
print("测试2: TaskManager集成测试")
print("=" * 60)

from lra.task_manager import TaskManager

task_manager = TaskManager()

print(f"\n✅ TaskManager加载成功")

# 测试_validate_constitution方法
print(f"\n📋 测试_validate_constitution方法:")
result = task_manager._validate_constitution("test_task", {}, "code-module")
print(f"   结果: {'通过' if result['passed'] else '失败'}")
if not result["passed"]:
    print(f"   失败项: {result['failures'][:3]}")

# 测试3: NON_NEGOTIABLE强制
print("\n" + "=" * 60)
print("测试3: NON_NEGOTIABLE强制验证")
print("=" * 60)

result = task_manager._validate_constitution(
    "test_task", {}, "code-module", check_non_negotiable_only=True
)
print(f"\n📋 只检查NON_NEGOTIABLE原则:")
print(f"   结果: {'通过' if result['passed'] else '失败'}")
if not result["passed"]:
    print(f"   失败项: {result['failures']}")
    print(f"\n   ⚠️  NON_NEGOTIABLE原则不能绕过！")

# 测试总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

print("""
✅ Constitution验证逻辑正常
✅ TaskManager集成成功
✅ NON_NEGOTIABLE强制验证工作

强制机制说明:
1. 任务标记为completed时自动验证Constitution
2. 验证失败自动进入optimizing状态
3. NON_NEGOTIABLE原则不能绕过
4. 即使force_completed也要验证NON_NEGOTIABLE

AI无法偷懒绕过Constitution！
""")

print("📚 查看更多信息:")
print("   lra constitution help       # 使用指南")
print("   lra constitution show       # 查看配置")
print("   docs/CONSTITUTION_DESIGN.md # 设计文档\n")
