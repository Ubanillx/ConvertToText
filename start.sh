#!/bin/bash

# ConvertToText 启动脚本
# 适用于 conda 环境

echo "🚀 启动 ConvertToText 系统..."

# 激活指定的 conda 环境
echo "🔄 激活 conda 环境: convert-to-text"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate convert-to-text

# 检查是否成功激活环境
if [[ "$CONDA_DEFAULT_ENV" == "convert-to-text" ]]; then
    echo "✅ 成功激活 conda 环境: $CONDA_DEFAULT_ENV"
else
    echo "❌ 错误: 无法激活 convert-to-text 环境"
    echo "请确保环境存在: conda env list"
    exit 1
fi

# 检查 Python 版本
python_version=$(python --version 2>&1 | cut -d' ' -f2)
echo "🐍 Python 版本: $python_version"

# 检查是否存在 requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 未找到 requirements.txt 文件"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖包..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo "✅ 依赖安装完成"

# 检查环境变量
echo "🔧 检查环境配置..."

# 检查必要的环境变量
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量"
    echo "LangChain 功能可能无法正常工作"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "ℹ️  信息: 未设置 OPENAI_API_KEY 环境变量 (可选)"
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs
mkdir -p docs

# 启动服务
echo "🌟 启动 FastAPI 服务..."
echo "📍 服务地址: http://localhost:8000"
echo "📚 API 文档: http://localhost:8000/docs"
echo "🔍 健康检查: http://localhost:8000/api/v1/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动 FastAPI 应用
python main.py
