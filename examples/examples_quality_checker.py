#!/usr/bin/env python3
"""
质量检查器使用示例
演示如何使用增强的质量检查系统
"""

from lra.quality_checker import QualityChecker


def example_code_module():
    """代码模块质量检查示例"""
    print("=" * 60)
    print("示例 1: 代码模块质量检查")
    print("=" * 60)

    qc = QualityChecker()

    result = qc.check_quality_by_template(task_id="code-task-001", template_name="code-module")

    print(f"\n任务ID: {result['task_id']}")
    print(f"模板: {result['template']}")
    print(f"质量评分: {result['score']}/{result['max_score']}")
    print(f"\n检查项详情:")

    for check in result["checks"]:
        status = "✅ 通过" if check["passed"] else "❌ 失败"
        required = "必需" if check["required"] else "可选"
        print(f"  - {check['type']}: {check['score']}分 [{required}] {status}")

    if result.get("failed_required"):
        print(f"\n⚠️  失败的必需项: {result['failed_required']}")

    print("\n优化建议:")
    hints = qc.generate_optimization_hints("code-task-001")
    for hint in hints:
        print(f"  • {hint.get('description', hint.get('message'))}")
        if "command" in hint:
            print(f"    命令: {hint['command']}")


def example_novel_chapter():
    """小说章节质量检查示例"""
    print("\n" + "=" * 60)
    print("示例 2: 小说章节质量检查")
    print("=" * 60)

    qc = QualityChecker()

    result = qc.check_quality_by_template(task_id="chapter-001", template_name="novel-chapter")

    print(f"\n任务ID: {result['task_id']}")
    print(f"模板: {result['template']}")
    print(f"质量评分: {result['score']}/{result['max_score']}")

    print(f"\n检查项详情:")
    for check in result["checks"]:
        status = "✅ 通过" if check["passed"] else "❌ 失败"
        print(f"  - {check['type']}: {check['score']}分 {status}")

        if check["type"] == "word_count" and "total_words" in check.get("details", {}):
            print(f"    字数: {check['details']['total_words']}/{check['details']['min_words']}")


def example_data_pipeline():
    """数据处理流程质量检查示例"""
    print("\n" + "=" * 60)
    print("示例 3: 数据处理流程质量检查")
    print("=" * 60)

    qc = QualityChecker()

    result = qc.check_quality_by_template(task_id="data-task-001", template_name="data-pipeline")

    print(f"\n任务ID: {result['task_id']}")
    print(f"模板: {result['template']}")
    print(f"质量评分: {result['score']}/{result['max_score']}")

    print(f"\n检查项详情:")
    for check in result["checks"]:
        status = "✅ 通过" if check["passed"] else "❌ 失败"
        print(f"  - {check['type']}: {check['score']}分 {status}")


def example_doc_update():
    """文档更新质量检查示例"""
    print("\n" + "=" * 60)
    print("示例 4: 文档更新质量检查")
    print("=" * 60)

    qc = QualityChecker()

    result = qc.check_quality_by_template(task_id="doc-task-001", template_name="doc-update")

    print(f"\n任务ID: {result['task_id']}")
    print(f"模板: {result['template']}")
    print(f"质量评分: {result['score']}/{result['max_score']}")

    print(f"\n检查项详情:")
    for check in result["checks"]:
        status = "✅ 通过" if check["passed"] else "❌ 失败"
        print(f"  - {check['type']}: {check['score']}分 {status}")


def example_calculate_score():
    """综合质量评分计算示例"""
    print("\n" + "=" * 60)
    print("示例 5: 综合质量评分计算")
    print("=" * 60)

    qc = QualityChecker()

    checks = [
        {"type": "test", "score": 100, "weight": 0.4, "required": True, "passed": True},
        {"type": "lint", "score": 85, "weight": 0.2, "required": False, "passed": True},
        {"type": "acceptance", "score": 70, "weight": 0.3, "required": True, "passed": True},
        {"type": "performance", "score": 100, "weight": 0.1, "required": False, "passed": True},
    ]

    score_info = qc.calculate_quality_score(checks)

    print(f"\n检查项:")
    for check in checks:
        print(f"  - {check['type']}: {check['score']}分 (权重: {check['weight']})")

    print(f"\n综合评分: {score_info['score']}/{score_info['max_score']}")
    print(f"通过必需项: {'是' if score_info['passed_required'] else '否'}")
    print(f"权重总和: {score_info['weight_sum']}")
    print(f"加权分数: {score_info['weighted_score']}")


def example_get_failed_checks():
    """获取失败检查项示例"""
    print("\n" + "=" * 60)
    print("示例 6: 获取失败检查项")
    print("=" * 60)

    qc = QualityChecker()

    qc.check_quality_by_template("task-001", "code-module")

    failed = qc.get_failed_checks("task-001")

    if failed:
        print(f"\n发现 {len(failed)} 个失败的检查项:")
        for item in failed:
            print(f"\n  检查类型: {item['type']}")
            print(f"  评分: {item['score']}")
            print(f"  是否必需: {'是' if item['required'] else '否'}")

            if item.get("issues"):
                print(f"  问题:")
                for issue in item["issues"]:
                    print(f"    - {issue.get('message', '未知问题')}")

            if item.get("suggestions"):
                print(f"  建议:")
                for suggestion in item["suggestions"]:
                    print(f"    - {suggestion}")
    else:
        print("\n✅ 所有检查项都通过!")


def main():
    """运行所有示例"""
    print("\n" + "█" * 60)
    print("质量检查器 v2.0 - 使用示例")
    print("█" * 60)

    example_code_module()
    example_novel_chapter()
    example_data_pipeline()
    example_doc_update()
    example_calculate_score()
    example_get_failed_checks()

    print("\n" + "█" * 60)
    print("示例演示完成!")
    print("█" * 60)
    print("\n支持的质量门禁:")

    qc = QualityChecker()
    for template in qc.get_supported_templates():
        gates = qc.get_quality_gates(template)
        print(f"\n  {template}:")
        for gate in gates:
            required = "必需" if gate.get("required") else "可选"
            print(f"    - {gate['type']} (权重: {gate['weight']}, {required})")


if __name__ == "__main__":
    main()
