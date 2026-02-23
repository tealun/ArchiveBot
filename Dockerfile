# ArchiveBot Dockerfile
# 使用官方轻量 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件先安装（利用 Docker 缓存层）
COPY requirements.txt .

# 安装依赖（--no-cache-dir 节省空间）以及 gosu（用于 entrypoint 中安全降权）
RUN apt-get update && apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建非 root 用户并设置权限（安全最佳实践）
RUN adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app

# 复制 entrypoint 脚本（在运行时创建数据目录并降权到 appuser）
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# 环境变量
ENV PYTHONUNBUFFERED=1

# 运行 Bot（entrypoint 会创建目录、修复权限，然后以 appuser 身份启动）
ENTRYPOINT ["/entrypoint.sh"]
