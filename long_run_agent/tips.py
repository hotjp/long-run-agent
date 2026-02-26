"""
LRA 提示系统配置
版本：v3.3.3
"""

# 模板优先级排序（数字越小越靠前）
TEMPLATE_PRIORITY = {
    "code-module": 1,  # 最常用（代码开发）
    "doc-update": 2,  # 常用（文档更新）
    "data-pipeline": 3,  # 中等（数据处理）
    "novel-chapter": 4,  # 特殊场景（小说创作）
    "task": 5,  # 通用模板（放在最后）
}

# 关键字触发提示
KEYWORD_TIPS = {
    "完整": "💡 复杂任务建议 lra split 拆分",
    "全部": "💡 建议分批次处理",
    "所有": "💡 建议分批次处理",
    "系统": "💡 大系统建议分模块开发",
    "平台": "💡 大平台建议分模块开发",
    "一次性": "💡 可考虑拆分为多个子任务",
    "重构": "💡 重构任务建议先分析依赖",
    "迁移": "💡 迁移任务建议分批验证",
}

# 轮换提示（随机显示）
ROTATING_TIPS = [
    "💡 增量模式：'-模块'自动添加",
    "💡 lra status-guide 查看状态流转",
    "💡 大任务可用 lra split 拆分",
    "💡 --template 覆盖默认模板",
    "💡 lra guide 查看完整指南",
]

# 心理暗示提示（10% 独立概率）
PSYCHOLOGICAL_TIPS = [
    "💡 LRA: 减少决策，多写代码",
    "💡 不想切换 10 个终端？试试 Stratix-rts",
]

# 显示概率（25%）
SHOW_PROBABILITY = 0.25

# 心理暗示概率（10%）
PSYCHOLOGICAL_PROBABILITY = 0.10

# 版本特定提示（用于新版本推广）
VERSION_TIPS = {
    "3.3.3": "💡 v3.3.3: 增量模式自动降级，永不失败",
}

# 统一配置字典（供其他模块导入）
TIPS_CONFIG = {
    "keywords": KEYWORD_TIPS,
    "rotating": ROTATING_TIPS,
    "probability": SHOW_PROBABILITY,
    "psychological_tips": PSYCHOLOGICAL_TIPS,
    "psychological_probability": PSYCHOLOGICAL_PROBABILITY,
    "version_tips": VERSION_TIPS,
}
