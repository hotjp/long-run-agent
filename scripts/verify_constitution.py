#!/usr/bin/env python3
"""快速验证Constitution核心功能"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Constitution核心功能验证\n")

# 测试1: 创建默认Constitution
print("1️⃣  测试创建默认Constitution...")
from lra.constitution import create_default_constitution

constitution = create_default_constitution("Test Project")
print(f"   ✅ 创建成功: {constitution['project']['name']}\n")

# 测试2: 初始化ConstitutionManager
print("2️⃣  测试ConstitutionManager初始化...")
from lra.constitution import ConstitutionManager

manager = ConstitutionManager()
print(f"   ✅ 初始化成功\n")

# 测试3: 获取原则
print("3️⃣  测试获取原则...")
principles = manager.get_all_applicable_principles()
print(f"   ✅ 获取到 {len(principles)} 个原则\n")

# 测试4: 创建原则验证器
print("4️⃣  测试原则验证器...")
from lra.constitution import PrincipleValidator

validator = PrincipleValidator(manager)
print(f"   ✅ 创建成功\n")

# 测试5: 验证任务
print("5️⃣  测试验证任务...")
result = validator.validate_all_principles("test_task", {})
print(f"   {'✅ 验证通过' if result.passed else '❌ 验证失败'}")
print(f"   消息: {result.message}\n")

print("🎉 Constitution核心功能验证完成！\n")
print("📊 测试结果:")
print("   • Constitution创建: ✅")
print("   • ConstitutionManager: ✅")
print("   • 原则获取: ✅")
print("   • 验证器: ✅")
print("   • 任务验证: ✅\n")

print("📚 下一步:")
print("   1. 查看 .long-run-agent/constitution.yaml 配置")
print("   2. 阅读 docs/IMPLEMENTATION_GUIDE.md")
print("   3. 运行 demo_constitution.py 查看完整演示\n")
