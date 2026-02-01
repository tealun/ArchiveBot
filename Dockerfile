# ArchiveBot Dockerfile
# 使用官方轻量 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件先安装（利用 Docker 缓存层）
COPY requirements.txt .

# 安装依赖（--no-cache-dir 节省空间）
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录（如果不存在）
RUN mkdir -p /app/data /app/data/backups /app/data/cache /app/data/temp /app/data/temp/ai_sessions

# 创建非 root 用户并设置权限（安全最佳实践）
RUN adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 环境变量
ENV PYTHONUNBUFFERED=1

# 运行 Bot
CMD ["python", "main.py"]
