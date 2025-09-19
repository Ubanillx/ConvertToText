# ConvertToText Ubuntu 24 部署指南

## 📋 概述

本指南详细说明如何在Ubuntu 24.04 LTS系统上部署ConvertToText智能文档文字提取系统。该系统基于FastAPI构建，集成了多种AI服务，支持PDF、DOC、图片等多种格式的文档处理。

## 🎯 系统要求

### 硬件要求
- **CPU**: 2核心以上（推荐4核心）
- **内存**: 最小4GB，推荐8GB+
- **存储**: 最小20GB可用空间
- **网络**: 稳定的互联网连接（用于AI服务调用）

### 软件要求
- **操作系统**: Ubuntu 24.04 LTS
- **Python**: 3.8+ （推荐3.9或3.10）
- **Conda**: Miniconda或Anaconda
- **Git**: 用于代码管理

## 🚀 部署步骤

### 第一步：系统环境准备

#### 1.1 更新系统包
```bash
# 更新包列表
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git vim build-essential
```

#### 1.2 安装Python和Conda
```bash
# 安装Python开发工具
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3-pip

# 下载并安装Miniconda
cd /tmp
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# 初始化Conda
$HOME/miniconda3/bin/conda init bash
source ~/.bashrc
```

#### 1.3 安装系统级依赖
```bash
# 安装Tesseract OCR
sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# 安装图像处理依赖
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# 安装OpenCV依赖
sudo apt install -y libopencv-dev python3-opencv

# 安装其他必要依赖
sudo apt install -y libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev
```

### 第二步：项目部署

#### 2.1 克隆项目代码
```bash
# 创建项目目录
sudo mkdir -p /opt/convert-to-text
sudo chown $USER:$USER /opt/convert-to-text
cd /opt/convert-to-text

# 克隆项目（替换为实际仓库地址）
git clone https://github.com/your-username/ConvertToText.git .
# 或者如果已有代码，直接复制到该目录
```

#### 2.2 创建Conda环境
```bash
# 创建专用环境
conda create -n convert-to-text python=3.10 -y
conda activate convert-to-text

# 验证环境
python --version
which python
```

#### 2.3 安装Python依赖
```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证关键依赖安装
python -c "import fastapi, uvicorn, dashscope, cv2, pytesseract; print('核心依赖安装成功')"
```

### 第三步：配置设置

#### 3.1 创建环境配置文件
```bash
# 创建.env配置文件
cat > .env << 'EOF'
# 应用配置
APP_NAME=ConvertToText
APP_VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=8000

# 百炼平台配置 (必需)
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_MODEL=qwen-plus

# 百度OCR配置 (必需)
BAIDU_OCR_API_KEY=your_baidu_ocr_api_key_here
BAIDU_OCR_SECRET_KEY=your_baidu_ocr_secret_key_here

# OpenAI配置 (可选)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# 文件存储配置
STORAGE_PATH=/opt/convert-to-text/storage
MAX_FILE_SIZE=104857600
FILE_RETENTION_DAYS=7
AUTO_CLEANUP_ENABLED=true

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/opt/convert-to-text/logs/app.log
EOF
```

#### 3.2 创建必要目录
```bash
# 创建存储目录
mkdir -p storage/{uploads,temp,results}
mkdir -p logs

# 设置权限
chmod 755 storage storage/* logs
```

#### 3.3 配置系统服务（可选）
```bash
# 创建systemd服务文件
sudo tee /etc/systemd/system/convert-to-text.service > /dev/null << 'EOF'
[Unit]
Description=ConvertToText Document Processing Service
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/convert-to-text
Environment=PATH=/home/ubuntu/miniconda3/envs/convert-to-text/bin
ExecStart=/home/ubuntu/miniconda3/envs/convert-to-text/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd配置
sudo systemctl daemon-reload
```

### 第四步：启动和验证

#### 4.1 手动启动测试
```bash
# 激活环境
conda activate convert-to-text

# 启动服务
python main.py
```

#### 4.2 验证服务运行
```bash
# 在另一个终端测试服务
curl http://localhost:8000/api/v1/health

# 检查API文档
curl http://localhost:8000/docs
```

#### 4.3 使用systemd服务（推荐生产环境）
```bash
# 启动服务
sudo systemctl start convert-to-text

# 设置开机自启
sudo systemctl enable convert-to-text

# 检查服务状态
sudo systemctl status convert-to-text

# 查看日志
sudo journalctl -u convert-to-text -f
```

## 🔧 配置说明

### 必需配置项

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `DASHSCOPE_API_KEY` | 阿里云百炼平台API密钥 | [百炼平台控制台](https://dashscope.aliyun.com/) |
| `BAIDU_OCR_API_KEY` | 百度OCR API密钥 | [百度智能云控制台](https://cloud.baidu.com/) |
| `BAIDU_OCR_SECRET_KEY` | 百度OCR Secret密钥 | [百度智能云控制台](https://cloud.baidu.com/) |

### 可选配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | None | OpenAI API密钥（备用） |
| `HOST` | 0.0.0.0 | 服务监听地址 |
| `PORT` | 8000 | 服务端口 |
| `MAX_FILE_SIZE` | 100MB | 最大文件大小 |
| `FILE_RETENTION_DAYS` | 7 | 文件保留天数 |

## 🧪 功能测试

### 基础功能测试
```bash
# 1. 健康检查
curl -X GET "http://localhost:8000/api/v1/health"

# 2. PDF文字提取测试
curl -X POST "http://localhost:8000/api/v1/pdf/extract-text" \
  -F "file=@test.pdf" \
  -F "use_ocr=true" \
  -F "use_vision=true" \
  -F "ocr_engine=baidu"

# 3. 图片文字提取测试
curl -X POST "http://localhost:8000/api/image/extract-text" \
  -F "file=@test.png" \
  -F "processing_type=extract" \
  -F "ocr_engine=baidu" \
  -F "use_vision=true"
```

### 性能测试
```bash
# 使用ab进行简单性能测试
sudo apt install -y apache2-utils

# 测试健康检查接口
ab -n 100 -c 10 http://localhost:8000/api/v1/health
```

## 🔍 监控和日志

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看systemd服务日志
sudo journalctl -u convert-to-text -f

# 查看系统资源使用
htop
```

### 服务监控
```bash
# 检查服务状态
sudo systemctl status convert-to-text

# 检查端口占用
sudo netstat -tlnp | grep 8000

# 检查进程
ps aux | grep python
```

## 🛠️ 故障排除

### 常见问题及解决方案

#### 1. Conda环境激活失败
```bash
# 问题：conda activate命令不识别
# 解决：重新初始化conda
$HOME/miniconda3/bin/conda init bash
source ~/.bashrc
```

#### 2. Python依赖安装失败
```bash
# 问题：某些包安装失败
# 解决：使用conda安装系统级依赖
conda install -c conda-forge opencv tesseract

# 或者使用系统包管理器
sudo apt install -y python3-opencv python3-tesseract
```

#### 3. Tesseract OCR不可用
```bash
# 问题：pytesseract找不到tesseract
# 解决：安装tesseract并配置路径
sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim
# 检查安装
tesseract --version
```

#### 4. 内存不足
```bash
# 问题：处理大文件时内存不足
# 解决：增加swap空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 5. 端口被占用
```bash
# 问题：8000端口被占用
# 解决：修改配置或杀死占用进程
sudo lsof -i :8000
sudo kill -9 <PID>
# 或修改.env文件中的PORT配置
```

### 日志分析
```bash
# 查看错误日志
grep -i error logs/app.log

# 查看警告日志
grep -i warning logs/app.log

# 查看特定时间段的日志
grep "2024-01-01" logs/app.log
```

## 🔒 安全配置

### 防火墙设置
```bash
# 安装ufw防火墙
sudo apt install -y ufw

# 配置防火墙规则
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8000/tcp

# 启用防火墙
sudo ufw enable
```

### SSL/TLS配置（生产环境）
```bash
# 使用nginx作为反向代理
sudo apt install -y nginx

# 配置nginx
sudo tee /etc/nginx/sites-available/convert-to-text > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/convert-to-text /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📊 性能优化

### 系统优化
```bash
# 调整文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化内核参数
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 应用优化
```bash
# 使用gunicorn作为WSGI服务器（生产环境）
pip install gunicorn

# 创建gunicorn配置文件
cat > gunicorn.conf.py << 'EOF'
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
EOF

# 使用gunicorn启动
gunicorn -c gunicorn.conf.py main:app
```

## 🔄 更新和维护

### 代码更新
```bash
# 停止服务
sudo systemctl stop convert-to-text

# 备份当前版本
cp -r /opt/convert-to-text /opt/convert-to-text.backup.$(date +%Y%m%d)

# 更新代码
cd /opt/convert-to-text
git pull origin main

# 更新依赖
conda activate convert-to-text
pip install -r requirements.txt

# 重启服务
sudo systemctl start convert-to-text
```

### 定期维护
```bash
# 创建维护脚本
cat > /opt/convert-to-text/maintenance.sh << 'EOF'
#!/bin/bash
# 清理临时文件
find /opt/convert-to-text/storage/temp -type f -mtime +1 -delete

# 清理日志文件
find /opt/convert-to-text/logs -name "*.log" -mtime +30 -delete

# 重启服务
sudo systemctl restart convert-to-text
EOF

chmod +x /opt/convert-to-text/maintenance.sh

# 添加到crontab
echo "0 2 * * * /opt/convert-to-text/maintenance.sh" | crontab -
```

## 📞 技术支持

如果在部署过程中遇到问题，请：

1. 检查日志文件：`logs/app.log`
2. 查看系统服务状态：`sudo systemctl status convert-to-text`
3. 验证环境配置：`conda list` 和 `python -c "import app"`
4. 检查网络连接和API密钥配置

## 📝 总结

通过以上步骤，您应该能够在Ubuntu 24.04系统上成功部署ConvertToText服务。系统将提供：

- ✅ 完整的文档处理能力
- ✅ 高可用的API服务
- ✅ 自动化的文件管理
- ✅ 完善的监控和日志
- ✅ 生产级的安全配置

部署完成后，您可以通过 `http://your-server:8000/docs` 访问API文档，开始使用ConvertToText的智能文档处理功能。
