# Feature Testing Guide

## Feature 1: 语言持久化 ✅
**测试步骤：**
1. 使用 `/language` 切换到任意语言（如英文）
2. 重启bot：停止Python进程，重新运行
3. 发送 `/help` 验证语言是否保持为英文
4. 检查数据库：`SELECT * FROM config WHERE key='user_language'`

**预期结果：**
- 重启后语言保持不变
- 数据库中正确存储语言设置

---

## Feature 2: 笔记模式后自动执行命令 ✅
**测试步骤：**
1. 进入笔记模式：`/note`
2. 记录几条笔记内容（如"测试内容1"、"测试内容2"）
3. 发送命令：`/search`
4. 点击按钮："🚪 立即退出并保存笔记，然后执行命令"
5. 观察bot行为

**预期结果：**
- 笔记自动保存成功
- `/search` 命令自动执行（显示"请提供搜索关键词"提示）
- 用户无需重新发送命令

---

## Feature 3: AI直接执行命令（三阶段）✅

### Phase 1: 安全只读操作
**测试步骤：**
1. 进入AI对话模式（发送问号"?"或复杂问题）
2. 发送："搜索python"
3. 观察AI是否直接返回搜索结果

**预期结果：**
- AI直接执行搜索并返回格式化结果
- 无需确认对话框

**其他可测试命令：**
- "查看统计信息" → stats
- "显示所有标签" → tags
- "查看我的笔记" → notes
- "随机抽取一个归档" → review

### Phase 2: 写操作需要确认
**测试步骤：**
1. 在AI对话模式下发送："给归档#123添加标签'重要'"
2. 观察是否显示确认对话框
3. 点击"✅ 确认执行"按钮
4. 验证标签是否成功添加

**预期结果：**
- 显示确认对话框包含操作详情
- 确认后正确执行
- 取消后清除pending_action

**其他可测试命令：**
- "创建一条笔记：xxx" → create_note
- "移除归档#123的标签'xxx'" → remove_tag
- "收藏归档#123" → toggle_favorite

### Phase 3: 禁止操作 + 审计日志
**测试步骤：**
1. 在AI对话模式下发送："删除归档#123"
2. 观察是否拒绝执行并说明原因

**预期结果：**
- 拒绝消息："🚫 出于安全考虑，此操作需要您手动执行"
- 日志中包含 `[AUDIT]` 记录：`{"event_type": "forbidden_attempt", ...}`

**查看审计日志：**
```bash
# 搜索所有审计日志
grep "\[AUDIT\]" logs/archivebot.log

# 查看最近的AI操作
tail -f logs/archivebot.log | grep "\[AUDIT\]"
```

**审计日志格式示例：**
```json
[AUDIT] {"timestamp": "2026-01-29T00:30:00", "event_type": "safe_executed", "operation": "search", "params": {"keyword": "python"}, "language": "zh-CN", "result": "✓ 找到5个结果"}
[AUDIT] {"timestamp": "2026-01-29T00:31:00", "event_type": "write_confirmed", "operation": "add_tag", "params": {"archive_id": 123, "tag": "重要"}, "language": "zh-CN", "result": "✓ 标签已添加"}
[AUDIT] {"timestamp": "2026-01-29T00:32:00", "event_type": "write_cancelled", "operation": "create_note", "params": {"content": "xxx"}, "language": "zh-CN", "result": "User cancelled operation"}
[AUDIT] {"timestamp": "2026-01-29T00:33:00", "event_type": "forbidden_attempt", "operation": "delete", "params": {"archive_id": 123}, "language": "zh-CN", "result": null}
```

---

## Feature 4: AI确认执行动作 ✅
**测试步骤：**
1. 在AI对话模式下发送："删除归档#123"（如果Phase 3未拦截）
2. AI会生成pending_action并请求确认
3. 点击确认按钮
4. 验证操作是否执行

**预期结果：**
- 确认对话框包含操作详情
- 确认后通过executor.py执行
- 执行结果反馈给用户

**支持的操作：**
- delete_archive (移动到回收站)
- clear_trash (清空回收站)
- create_note (创建笔记)
- add_tag (添加标签)
- remove_tag (移除标签)
- toggle_favorite (切换收藏)

---

## Feature 5: 笔记超时测试 ⏳

### 默认超时时间：15分钟

**测试方法1：完整测试（需要15分钟等待）**
1. 进入笔记模式：`/note`
2. 发送一条笔记内容："测试超时功能"
3. 等待15分钟不发送任何消息
4. 观察是否自动生成并保存笔记

**测试方法2：临时调整超时（推荐快速测试）**

修改代码临时降低超时时间为1分钟：

```python
# src/bot/handlers/note_mode.py, line ~46
from datetime import timedelta
job = context.job_queue.run_once(
    note_timeout_callback,
    when=timedelta(minutes=1),  # 改为1分钟，原值为15
    data={...}
)
```

**步骤：**
1. 修改超时时间为1分钟
2. 重启bot
3. 进入笔记模式并发送内容
4. 等待1分钟
5. 观察bot行为

**预期结果：**
- 超时后收到提示："⏰ 笔记模式已超时(15分钟无新消息)"
- 笔记自动保存
- 笔记模式退出
- 日志显示："Note mode timeout completed for user xxx"

### 超时重置测试
1. 进入笔记模式
2. 发送一条消息
3. 等待14分钟
4. 再发送一条消息（重置计时器）
5. 再等待14分钟
6. 再发送一条消息
7. 此时应该不会超时

**预期结果：**
- 每次发送消息都会重置15分钟计时器
- 只要持续活跃，就不会触发超时

---

## 笔记模式命令拦截测试 ✅
**测试步骤：**
1. 进入笔记模式：`/note`
2. 发送命令：`/search`（或其他任何命令，除了`/note`和`/cancel`）
3. 观察是否显示选择对话框

**预期结果：**
- 显示对话框："⚠️ 您正在笔记模式中"
- 命令未执行
- 后续消息不会被误记录为笔记内容

**按钮功能测试：**
- 点击"🚪 立即退出并保存笔记，然后执行命令" → 保存笔记并执行命令
- 点击"✍️ 继续记录笔记（忽略命令）" → 清除pending_command，继续笔记模式

---

## 回归测试清单

完成新功能测试后，应验证以下核心功能未受影响：

- [ ] 转发消息归档（单条、多条、媒体组）
- [ ] 搜索功能（关键词、标签过滤）
- [ ] 标签管理（添加、删除、查看）
- [ ] 笔记功能（添加、编辑、查看、删除）
- [ ] 回收站功能（删除、恢复、清空）
- [ ] 导出功能（Markdown、JSON、HTML）
- [ ] 备份功能（创建、恢复、删除）
- [ ] AI总结功能（手动、自动）
- [ ] 复习模式（随机抽取归档）
- [ ] 多语言切换

---

## 测试通过标准

- ✅ 所有功能按预期工作
- ✅ 无Python异常或错误日志
- ✅ 数据持久化正确
- ✅ 用户体验流畅
- ✅ 审计日志正确记录

---

## 已知限制

1. **Feature 3 Phase 2/3**: 目前executor只支持6种操作，未来可扩展更多操作
2. **笔记超时**: 超时时间硬编码为15分钟，未来可改为配置项
3. **审计日志**: 当前只输出到应用日志，未来可考虑独立的audit.log或数据库表

---

## 测试完成后

1. 恢复所有临时修改（如超时时间）
2. 运行完整回归测试
3. 检查日志无异常
4. Git commit并push到远程仓库
5. 更新README记录新功能
