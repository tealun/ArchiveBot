# Docker 部署测试检查清单

## 📋 部署前检查

- [ ] Docker 已安装：`docker --version`
- [ ] Docker Compose 已安装：`docker-compose --version`
- [ ] 配置文件已复制：`config/config.yaml` 存在
- [ ] 配置文件已填写：bot_token、owner_id、channel_id

## 🧪 功能测试

### 1. 构建测试
```bash
docker-compose build
```
预期：成功构建，无报错

### 2. 启动测试
```bash
docker-compose up -d
```
预期：容器正常启动

### 3. 日志检查
```bash
docker-compose logs -f
```
预期：
- ✅ "Configuration loaded"
- ✅ "Database initialized"
- ✅ "Bot started successfully"
- ❌ 无错误信息

### 4. 容器状态
```bash
docker-compose ps
```
预期：archivebot 状态为 "Up"

### 5. 配置加载测试
```bash
# 检查环境变量是否生效
docker-compose exec archivebot python -c "import os; print(os.getenv('BOT_TOKEN', 'Not set'))"
```

### 6. 数据持久化测试
```bash
# 停止容器
docker-compose down

# 检查数据目录
ls -la data/

# 重新启动
docker-compose up -d

# 数据应该保留
```

### 7. 配置方式测试

#### 方式一：YAML 配置
- [ ] 编辑 `config/config.yaml`
- [ ] 不设置环境变量
- [ ] 启动并验证配置生效

#### 方式二：环境变量覆盖
- [ ] 复制 `.env.example` 为 `.env`
- [ ] 设置环境变量
- [ ] 在 `docker-compose.yml` 中添加 `env_file: - .env`
- [ ] 启动并验证环境变量优先级

### 8. Bot 功能测试
- [ ] Telegram 发送 `/start` - 收到欢迎消息
- [ ] 转发一条消息 - 成功归档
- [ ] 发送 `/search` - 搜索功能正常
- [ ] 发送 `/tags` - 标签功能正常

### 9. 更新测试
```bash
git pull
docker-compose down
docker-compose up -d --build
```
预期：平滑更新，数据保留

### 10. 安全性检查
- [ ] `config/config.yaml` 在 .gitignore 中
- [ ] `.env` 在 .gitignore 中
- [ ] `docker-compose.override.yml` 在 .gitignore 中
- [ ] 镜像中不包含敏感信息：`docker-compose exec archivebot cat config/config.yaml`（应该找不到文件或为模板）

## 🔧 故障排查

### 容器无法启动
```bash
# 查看详细日志
docker-compose logs archivebot

# 检查配置文件
cat config/config.yaml

# 检查 Dockerfile
docker-compose config
```

### 配置不生效
```bash
# 进入容器检查
docker-compose exec archivebot bash
cd /app
ls -la config/
cat config/config.yaml
```

### 数据丢失
```bash
# 检查挂载
docker inspect archivebot | grep -A 10 Mounts

# 检查宿主机数据目录
ls -la data/
```

## ✅ 验证完成标准

- [x] 所有测试通过
- [x] Bot 正常响应
- [x] 数据持久化正常
- [x] 配置方式灵活
- [x] 安全性符合要求
- [x] 文档完整准确

## 📝 注意事项

1. **首次部署**：必须先配置 `config/config.yaml`
2. **环境变量**：优先级高于 YAML，用于覆盖敏感信息
3. **数据备份**：定期备份 `data/` 目录
4. **更新流程**：`git pull` → `docker-compose up -d --build`
5. **安全性**：不要提交包含真实密钥的文件到 Git
