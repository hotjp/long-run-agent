#!/bin/bash
#
# Ralph Agent Loop 示例脚本
# 
# 这个脚本展示了 Agent 如何使用 LRA 实现 Ralph Loop 机制
# Agent 应该自己管理循环，每次循环清空上下文
#

set -e

PROJECT_DIR="${1:-.}"
MAX_ITERATIONS=7

echo "================================================"
echo "Ralph Agent Loop - 任务级循环优化"
echo "================================================"
echo "项目目录: $PROJECT_DIR"
echo "最大优化次数: $MAX_ITERATIONS"
echo ""

cd "$PROJECT_DIR"

# 函数：检查是否还有待处理或优化中的任务
has_pending_tasks() {
    local pending=$(lra list --status pending --json 2>/dev/null | jq 'length' 2>/dev/null || echo 0)
    local optimizing=$(lra list --status optimizing --json 2>/dev/null | jq 'length' 2>/dev/null || echo 0)
    echo $((pending + optimizing))
}

# 函数：获取下一个可处理的任务
get_next_task() {
    # 优先处理优化中的任务
    local optimizing_task=$(lra list --status optimizing --json 2>/dev/null | jq -r '.[0].id // empty' 2>/dev/null)
    if [ -n "$optimizing_task" ]; then
        echo "$optimizing_task"
        return
    fi
    
    # 然后处理待开始的任务
    local pending_task=$(lra list --status pending --json 2>/dev/null | jq -r '.[0].id // empty' 2>/dev/null)
    echo "$pending_task"
}

# 函数：检查任务的优化次数
check_iterations() {
    local task_id=$1
    local iteration=$(lra show "$task_id" --json 2>/dev/null | jq -r '.ralph.iteration // 0' 2>/dev/null)
    echo "$iteration"
}

# 主循环
iteration_count=0
while true; do
    iteration_count=$((iteration_count + 1))
    
    echo "------------------------------------------------"
    echo "循环轮次: $iteration_count"
    echo "------------------------------------------------"
    
    # 检查是否还有任务
    task_count=$(has_pending_tasks)
    if [ "$task_count" -eq 0 ]; then
        echo "✅ 所有任务已完成"
        break
    fi
    
    # 获取下一个任务
    task_id=$(get_next_task)
    if [ -z "$task_id" ]; then
        echo "❌ 无法获取任务"
        break
    fi
    
    echo "处理任务: $task_id"
    
    # 查看任务详情
    lra show "$task_id"
    
    # 检查优化次数
    iteration=$(check_iterations "$task_id")
    if [ "$iteration" -ge "$MAX_ITERATIONS" ]; then
        echo "⚠️  任务已达到优化上限 ($MAX_ITERATIONS 次)"
        echo "   建议人工审核"
        lra set "$task_id" force_completed
        continue
    fi
    
    # 领取任务（如果是新任务）
    status=$(lra show "$task_id" --json 2>/dev/null | jq -r '.status' 2>/dev/null)
    if [ "$status" = "pending" ]; then
        lra claim "$task_id"
    fi
    
    # ====== Agent 实际工作区域 ======
    # 这里是 Agent 真正工作的部分
    # Agent 应该：
    # 1. 读取任务文件
    # 2. 理解任务要求
    # 3. 实现功能或修复问题
    # 4. 编写测试
    # 5. 验证结果
    
    echo ""
    echo "💡 Agent 工作区域"
    echo "   1. 读取任务: cat .long-run-agent/tasks/${task_id}.md"
    echo "   2. 查看相关代码"
    echo "   3. 实现/优化功能"
    echo "   4. 运行测试"
    echo "   5. 提交任务: lra set $task_id completed"
    echo ""
    
    # 示例：如果是 Agent，这里会调用实际的 Agent
    # agent_execute --task "$task_id" --context "$(lra context --json)"
    
    # 为了演示，这里模拟 Agent 工作
    read -p "按回车继续（模拟 Agent 工作）..." </dev/tty
    
    # 提交任务（触发质量检查）
    echo ""
    echo "提交任务: lra set $task_id completed"
    lra set "$task_id" completed
    
    # 检查质量检查结果
    new_status=$(lra show "$task_id" --json 2>/dev/null | jq -r '.status' 2>/dev/null)
    if [ "$new_status" = "optimizing" ]; then
        echo ""
        echo "🔄 质量检查未通过，任务进入优化模式"
        echo "   当前优化轮次: $((iteration + 1))/$MAX_ITERATIONS"
        echo "   查看详情: lra show $task_id"
        echo ""
    elif [ "$new_status" = "truly_completed" ]; then
        echo ""
        echo "✅ 质量检查通过，任务真正完成"
        echo ""
    fi
    
    # 这里可以决定是否继续循环
    # 在实际使用中，Agent 可能会选择：
    # 1. 继续处理下一个任务
    # 2. 继续优化当前任务
    # 3. 退出循环
    
    read -p "继续下一轮循环？(y/n) " -n 1 -r </dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "退出循环"
        break
    fi
    
    # 清空上下文（在实际使用中，这可能是启动新的 Agent 实例）
    echo ""
    echo "🔄 清空上下文，准备下一轮..."
    echo ""
done

echo ""
echo "================================================"
echo "Ralph Loop 完成"
echo "================================================"
echo "总轮次: $iteration_count"
lra status