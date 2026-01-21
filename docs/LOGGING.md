# 日志功能使用指南

## 📋 日志功能概述

ArchiveBot 内置了完整的日志系统，记录所有操作、错误和调试信息。

## 📍 日志文件位置

- **日志文件**: `data/bot.log`
- **日志级别**: INFO, WARNING, ERROR
- **编码**: UTF-8
- **自动轮转**: 需手动清理

## 🔍 查看日志的方式

### 1. 使用日志查看工具（推荐）

```bash
# 交互式菜单
python view_logs.py

# 查看最新日志
python view_logs.py view 50

# 只看错误
python view_logs.py errors

# 查看统计
python view_logs.py stats

# 清空日志
python view_logs.py clear
```

### 2. 使用命令行工具

**Windows PowerShell**:
```powershell
# 查看最新50行
Get-Content data\bot.log -Tail 50

# 实时跟踪日志
Get-Content data\bot.log -Wait -Tail 20

# 只看错误
Select-String -Path data\bot.log -Pattern "ERROR"

# 只看警告
Select-String -Path data\bot.log -Pattern "WARNING"

# 统计日志
(Get-Content data\bot.log | Measure-Object -Line).Lines
```

**Linux/Mac**:
```bash
# 查看最新50行
tail -n 50 data/bot.log

# 实时跟踪日志
tail -f data/bot.log

# 只看错误
grep ERROR data/bot.log

# 只看警告
grep WARNING data/bot.log
```

### 3. 直接打开文件

使用文本编辑器打开 `data/bot.log`：
- VS Code
- Notepad++
- Sublime Text
- 记事本

## 📊 日志内容说明

### 日志格式
```
时间戳 - 模块名 - 级别 - 消息内容
```

示例:
```
2026-01-21 15:20:33 - __main__ - INFO - ArchiveBot Starting...
2026-01-21 15:20:33 - src.models.database - INFO - Connected to database
2026-01-21 15:20:35 - src.bot.handlers - WARNING - Rate limit approaching
2026-01-21 15:20:40 - __main__ - ERROR - Failed to archive content
```

### 日志级别说明

| 级别 | 说明 | 示例 |
|------|------|------|
| **INFO** | 正常操作信息 | Bot启动、归档成功、命令执行 |
| **WARNING** | 警告信息 | 速率限制、存储降级、配置缺失 |
| **ERROR** | 错误信息 | 归档失败、数据库错误、网络异常 |

### 关键日志事件

#### 启动日志
```
ArchiveBot Starting...
Language: 简体中文
Database stats: X archives, Y tags
Telegram storage enabled
Bot is ready! Starting polling...
```

#### 归档操作
```
INFO - Message archived: user=12345, type=text
INFO - Successfully archived content: archive_id=1
```

#### 错误日志
```
ERROR - Failed to archive message: type=image
ERROR - Error archiving content: [详细错误信息]
```

## 🔒 安全特性

### 敏感信息过滤

日志系统自动过滤敏感信息：
- ✅ Bot Token 自动替换为 `[REDACTED]`
- ✅ User ID 自动替换为 `[REDACTED]`
- ✅ Owner ID 自动替换为 `[REDACTED]`

示例:
```
# 原始: Bot token: 8088186748:AAFaibz024o...
# 过滤后: Bot token: [REDACTED]
```

## 🛠️ 日志管理

### 查看日志统计
```bash
python view_logs.py stats
```

输出示例:
```
📊 日志统计
================================================================================
总行数: 1634
INFO:       141 (8.6%)
WARNING:      2 (0.1%)
ERROR:       31 (1.9%)

文件大小: 70.99 KB
文件路径: G:\Github\ArchiveBot\data\bot.log
```

### 清理日志

**方法1：使用工具脚本**
```bash
python view_logs.py clear
```

**方法2：手动删除**
```bash
# Windows
del data\bot.log

# Linux/Mac
rm data/bot.log
```

### 日志备份

建议定期备份日志：
```bash
# Windows
Copy-Item data\bot.log -Destination "data\backups\bot.log.$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# Linux/Mac
cp data/bot.log data/backups/bot.log.$(date +%Y%m%d-%H%M%S)
```

## 📈 日志监控

### 实时监控错误

**Windows**:
```powershell
Get-Content data\bot.log -Wait -Tail 10 | Where-Object { $_ -match "ERROR" }
```

**Linux/Mac**:
```bash
tail -f data/bot.log | grep ERROR
```

### 定时统计脚本

创建 `monitor.ps1`:
```powershell
while ($true) {
    Clear-Host
    Write-Host "ArchiveBot 日志监控 - $(Get-Date)" -ForegroundColor Green
    Write-Host "="*80
    
    $errors = (Select-String -Path data\bot.log -Pattern "ERROR" | Measure-Object).Count
    $warnings = (Select-String -Path data\bot.log -Pattern "WARNING" | Measure-Object).Count
    
    Write-Host "错误数: $errors" -ForegroundColor Red
    Write-Host "警告数: $warnings" -ForegroundColor Yellow
    
    Write-Host "`n最新10条日志:"
    Get-Content data\bot.log -Tail 10
    
    Start-Sleep -Seconds 5
}
```

## 🎯 常见问题

### 1. 日志文件太大怎么办？

定期清理或归档：
```bash
# 归档旧日志
python view_logs.py clear
```

### 2. 如何只看今天的日志？

**Windows**:
```powershell
$today = Get-Date -Format "yyyy-MM-dd"
Select-String -Path data\bot.log -Pattern $today
```

### 3. 如何导出错误日志？

```bash
python view_logs.py errors > errors.txt
```

### 4. 日志级别如何调整？

编辑 `config/config.yaml`:
```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
  file: "data/bot.log"
  console: true
```

## 📝 最佳实践

1. **定期检查日志** - 每天查看一次错误日志
2. **定期清理** - 每周或每月清理一次旧日志
3. **备份重要日志** - 出现问题时保存相关日志
4. **监控错误率** - 使用统计功能监控系统健康
5. **及时响应错误** - ERROR 日志需要立即处理

## 🔗 相关文档

- [SECURITY.md](SECURITY.md) - 安全最佳实践
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署和运维指南
- [TESTING.md](TESTING.md) - 测试清单

---

**提示**: 日志是诊断问题的重要工具，请妥善保管和利用！
