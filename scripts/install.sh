#!/bin/bash
# LRA 一键安装脚本
# 使用方法：bash scripts/install.sh

set -e

echo "🚀 LRA v3.2.0 一键安装"
echo "======================================"
echo

# 检查 Python
echo "1️⃣ 检查 Python..."
python3 --version || { echo "❌ Python3 未安装，请先安装 Python 3.8+"; exit 1; }
echo

# 升级 pip（可选）
echo "2️⃣ 升级 pip..."
python3 -m pip install --upgrade pip --quiet || echo "   ⚠️ pip 升级失败，继续安装..."
echo

# 安装 LRA
echo "3️⃣ 安装 long-run-agent..."
pip install long-run-agent
echo

# 验证安装
echo "4️⃣ 验证安装..."
if [ -f "scripts/verify-install.sh" ]; then
    bash scripts/verify-install.sh
else
    echo "✅ 安装完成！"
    echo
    echo "📚 快速开始："
    echo "  cd /your/project"
    echo "  lra init --name 'My Project'"
    echo "  lra context"
fi

echo
echo "======================================"
echo "🎉 安装成功！"
echo "======================================"
