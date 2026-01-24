# Git 推送说明

## 当前状态

已成功提交 Docker 支持的所有文件到本地仓库：

```
commit 3554a40 - feat: 添加 Docker 一键部署支持
```

## 推送问题

推送时遇到 GitHub Token 权限问题：

```
! [remote rejected] main -> main (refusing to allow a Personal Access Token 
  to create or update workflow `.github/workflows/deploy.yml` without `workflow` scope)
```

**原因**：之前的提交（860f281）修改了 `.github/workflows/deploy.yml`，但当前 Token 没有 `workflow` 权限。

## 解决方案

### 方案一：更新 GitHub Token（推荐）

1. 访问 GitHub Settings → Developer settings → Personal access tokens
2. 创建新 Token 或编辑现有 Token
3. 勾选 `workflow` 权限
4. 更新远程仓库 URL：
   ```bash
   git remote set-url origin https://NEW_TOKEN@github.com/tealun/ArchiveBot.git
   git push origin main
   ```

### 方案二：在 GitHub 网页端手动合并（最简单）

1. 创建新分支并推送：
   ```bash
   git checkout -b docker-support
   git push origin docker-support
   ```

2. 在 GitHub 网页端创建 Pull Request
3. 合并 PR 到 main 分支

### 方案三：跳过 workflow 修改

将 deploy.yml 的修改回退，单独推送：

```bash
# 回退到包含 workflow 修改之前
git rebase -i HEAD~12

# 在编辑器中，将包含 deploy.yml 的提交标记为 'drop' 或 'edit'
# 保存后继续 rebase

git push origin main
```

## 已提交的文件清单

✅ 核心 Docker 文件：
- Dockerfile
- docker-compose.yml
- .dockerignore
- .env.example

✅ 验证工具：
- verify_docker.py

✅ 文档：
- DOCKER_QUICK_START.md
- DOCKER_TEST.md

✅ 更新的文件：
- src/utils/config.py（环境变量支持）
- .gitignore（排除敏感文件）
- docs/DEPLOYMENT.md（Docker 章节）
- README.md（3 种语言）

⚠️ 未推送的文件：
- .github/workflows/docker-validate.yml（需要 workflow 权限）

## 当前建议

**推荐使用方案二（创建分支）**，最安全且不影响现有提交历史。

```bash
git checkout -b docker-support
git push origin docker-support
```

然后在 GitHub 网页端合并。
