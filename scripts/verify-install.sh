#!/bin/bash
# LRA 安装验证脚本
# 使用方法：bash scripts/verify-install.sh

set -e

echo "🔍 验证 LRA 安装..."
echo

# 检查 Python 版本
echo "1️⃣ 检查 Python 版本..."
python3 --version || { echo "❌ Python3 未安装"; exit 1; }
echo "   ✅ Python 已安装"
echo

# 检查 lra 命令
echo "2️⃣ 检查 lra 命令..."
if command -v lra &> /dev/null; then
    echo "   ✅ lra 命令已安装"
    lra version
else
    echo "   ❌ lra 命令未找到"
    echo "   💡 运行：pip install long-run-agent"
    exit 1
fi
echo

# 检查 Jinja2
echo "3️⃣ 检查 Jinja2..."
python3 -c "import jinja2; print(f'   ✅ Jinja2 {jinja2.__version__} 已安装')" 2>/dev/null || {
    echo "   ❌ Jinja2 未安装"
    echo "   💡 运行：pip install jinja2"
    exit 1
}
echo

# 测试基本功能
echo "4️⃣ 测试基本功能..."
if lra guide &> /dev/null; then
    echo "   ✅ lra 命令运行正常"
else
    echo "   ❌ lra 命令运行失败"
    exit 1
fi
echo

echo "======================================"
echo "✅ LRA 安装验证通过！"
echo "======================================"
echo
echo "📚 快速开始："
echo "  cd /your/project"
echo "  lra init --name 'My Project'"
echo "  lra context"
echo
echo "📖 文档：https://github.com/hotjp/long-run-agent"
