# 2026-06-23 修复：发送失败不写 state.db + 心跳/念头详情显示真实失败原因

## 背景

weixin session `20260623_040146_0ffdaa1f` 在 04:01 ~ 10:30 之间，凯莉发起 40+ 条主动消息，task_logs 全是 `send_message failed`，错误一致：

```
Weixin send failed: iLink sendmessage rate limited; cooldown active for 30.0s
```

但 state.db 的 messages 表里这些消息**全部入库成功**。同时心跳日志/念头日志详情页里"是否发送"标签判断逻辑错（基于 `message_sent` 字段，但语义不明），导致：
- 后续读取上下文（包括 hermes 主 agent loop）看到这批"幽灵消息"，污染 LLM 决策
- task_logs 显示"失败"但消息"看似存在"，状态语义冲突
- 前端心跳/念头详情页无法准确展示发送是否真正成功、失败原因不明

## 根因

### Bug 1：state.db 写入与平台发送未耦合

`backend/services/message_service.py::send_message`（L331-L349）：

```python
# 1. 真正发送消息到平台（可能失败）
send_result = await _send_to_weixin(user_id, message)

# 2. 写入 state.db（无条件执行，未看 send_result）
if write_to_db:
    _write_to_state_db(session_id, db_content)
```

**后果**：微信限速时，messages 表被污染，污染消息进入后续 agent loop 上下文，污染 LLM 决策。

### Bug 2：心跳详情"是否发送"标签误判

`frontend/src/views/ActiveConsciousness.vue` L880-L882：

```vue
<n-descriptions-item label="是否发送">
  <n-tag :type="sendDetailData.message_sent ? 'success' : 'default'" size="small">
    {{ sendDetailData.message_sent ? '已发送' : '未发送' }}
  </n-tag>
</n-descriptions-item>
```

**问题**：`message_sent` 仅表示 active.db active_heartbeat_logs 列字段（来自 `actual_sent` = `MessageService.send_message` 返回的 `success`），间接反映真实发送——但**失败原因（error 字符串）没有展示**。

### Bug 3：念头详情/念头列表展示问题

`frontend/src/views/ActiveConsciousness.vue`：

- **L1600**：`thoughtDetailsData` 加载逻辑里 `message_sent: detail.message_sent`——但 `active_thought_logs` 表**没有这个字段**！永远是 undefined
- **L2034**：念头列表"发送消息"列用 `row.message_sent`——后端念头列表 API 不返回该字段，永远是 undefined，显示"否"误导

真实状态存在 `details.message_sending.success` 里（`generate_and_send_thought_with_emotion` 写入），但前端没读取。

## 修复方案

### 改动 1：message_service.py — 发送失败时跳过 state.db 写入

**位置**：`backend/services/message_service.py` L347-L349（_write_to_state_db 调用处）

**当前**：
```python
# 2. 写入 state.db（带标记或不带标记）
db_content = message
if write_to_db:
    if send_mark:
        # ... 构造 db_content
    _write_to_state_db(session_id, db_content)
```

**改为**：
```python
# 2. 只有发送成功才写入 state.db，避免污染 messages 表和后续 agent loop
db_content = message
sent_ok = send_result and send_result.get("success")
if write_to_db and sent_ok:
    if send_mark:
        now = datetime.now()
        time_str = time_format.replace("{weekday}", weekday_name(now)) if time_format else ""
        time_str = now.strftime(time_str) if time_str else ""
        if time_str:
            db_content = f"[{send_mark} {time_str}]: {message}"
        else:
            db_content = f"[{send_mark}]: {message}"
    _write_to_state_db(session_id, db_content)
elif write_to_db and not sent_ok:
    logger.warning(
        "send failed for session %s, skipping state.db write. platform=%s, reason=%s",
        session_id, platform, send_result.get("message") if send_result else "no_result"
    )
```

### 改动 2：前端心跳详情 — 显示真实发送状态 + 失败原因

**位置**：`frontend/src/views/ActiveConsciousness.vue` L880-L882（心跳详情"是否发送"标签）

**当前**：
```vue
<n-descriptions-item label="是否发送">
  <n-tag :type="sendDetailData.message_sent ? 'success' : 'default'" size="small">
    {{ sendDetailData.message_sent ? '已发送' : '未发送' }}
  </n-tag>
</n-descriptions-item>
```

**改为**：
```vue
<n-descriptions-item label="是否发送">
  <n-tag :type="getHeartbeatSendTagType(detailsData)" size="small">
    {{ getHeartbeatSendLabel(detailsData) }}
  </n-tag>
</n-descriptions-item>
```

新增辅助函数（script 段）：
```javascript
// 心跳详情：读 send_result.success（MessageService 返回值），失败时显示原因
function getHeartbeatSendLabel(detail) {
  if (!detail) return '未发送'
  const sendResult = detail.send_result
  if (!sendResult) {
    return detail.message_sent ? '✅ 已发送' : '未发送'
  }
  if (sendResult.success) return '✅ 已发送'
  return `❌ ${sendResult.message || '发送失败'}`
}
function getHeartbeatSendTagType(detail) {
  if (!detail) return 'default'
  const sendResult = detail.send_result
  if (!sendResult) return detail.message_sent ? 'success' : 'default'
  return sendResult.success ? 'success' : 'error'
}
```

**注**：心跳 details JSON 里通常不直接有 send_result 字段，需要先从 details JSON 中提取——但 active_heartbeat_logs 的 details 是 `all_details` 字典（在 L1730-1740 写入），其中 `message_sending` 子字典已包含 success/message。修改方案：心跳详情弹窗顶部增加从 `details.message_sending` 提取 `send_result`：

```javascript
// loadHeartbeatDetail 加载逻辑里追加
const sendResult = parsed.message_sending
  ? { success: parsed.message_sending.success, message: parsed.message_sending.thought ? '已发送' : (parsed.message_sending.success ? '已发送' : '失败') }
  : (parsed.actual_sent ? { success: true, message: '已发送' } : null)
detailsData.value = {
  ...parsed,
  send_result: sendResult,
  // ...其他字段
}
```

### 改动 3：前端念头详情 — 显示真实发送状态 + 失败原因

**位置**：`frontend/src/views/ActiveConsciousness.vue` L1648-1662（showThoughtDetails 函数）

**当前**：
```javascript
thoughtDetailsData.value = {
  ...parsed,
  // 顶层字段覆盖，确保弹窗能正确读取
  id: detail.id,
  thought: parsed.thought || detail.content || '',
  thought_type: parsed.thought_type || detail.type || '',
  decision: parsed.decision || detail.decision || '',
  score: parsed.score || detail.score || 0,
  emotion_state: parsed.emotion_state || null,
  hindsight_tags: parsed.hindsight_tags || [],
  hindsight_stored: parsed.hindsight_stored ?? false,
  llm_call: parsed.llm_call || null,
  context_bundle: parsed.context_bundle || null,
  created_at: detail.created_at,
}
```

**改为**（增加 send_result 字段提取）：
```javascript
thoughtDetailsData.value = {
  ...parsed,
  id: detail.id,
  thought: parsed.thought || detail.content || '',
  thought_type: parsed.thought_type || detail.type || '',
  decision: parsed.decision || detail.decision || '',
  score: parsed.score || detail.score || 0,
  emotion_state: parsed.emotion_state || null,
  hindsight_tags: parsed.hindsight_tags || [],
  hindsight_stored: parsed.hindsight_stored ?? false,
  llm_call: parsed.llm_call || null,
  context_bundle: parsed.context_bundle || null,
  created_at: detail.created_at,
  // 发送状态（从 details.message_sending 提取）
  send_result: parsed.message_sending
    ? { success: !!parsed.message_sending.success, message: parsed.message_sending.thought ? '消息已发送' : '失败' }
    : null,
}
```

**念头详情弹窗模板**：在 `thoughtDetailsData` 顶部增加"发送结果"卡片：

```vue
<n-card v-if="thoughtDetailsData.send_result" size="small" style="margin-bottom: 16px;">
  <div style="display: flex; align-items: center; gap: 12px;">
    <n-tag :type="thoughtDetailsData.send_result.success ? 'success' : 'error'" size="large">
      {{ thoughtDetailsData.send_result.success ? '✅ 已发送' : '❌ 发送失败' }}
    </n-tag>
    <span style="font-size: 14px; color: #666;">{{ thoughtDetailsData.send_result.message }}</span>
  </div>
</n-card>
```

### 改动 4：前端念头列表 — 表格列读 send_result

**位置**：`frontend/src/views/ActiveConsciousness.vue` L2034（念头列表"发送消息"列）

**当前**：
```javascript
{ title: '发送消息', key: 'message_sent', width: 80, render(row) { const v = row.message_sent; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'warning', onClick: () => showSendDetail(row) }, { default: () => '是' }) : '否' } },
```

**改为**：
```javascript
{ title: '发送消息', key: 'message_sent', width: 80, render(row) {
  // 优先读 parsed.message_sending.success（念头详情真实字段）
  const sent = row.details_parsed?.message_sending?.success ?? row.message_sent ?? false
  return sent
    ? h(NButton, { size: 'tiny', quaternary: true, type: 'warning', onClick: () => showSendDetail(row) }, { default: () => '是' })
    : '否'
} },
```

**注**：念头列表 L2080-2091 已经解析 `item.details_parsed`，所以 `row.details_parsed` 一定有值。

### 改动 5（验证项，scheduler_service.py 已有）

`scheduler_service.run_cron_job` 失败路径 L583 已经传 `details.get("send_result")`，改动 1 之后自动受益——验证通过不需要改。

## 测试

### 单元验证（手动）

1. 启动 hermes-active 后端
2. 手动触发一次 cron（前端点"运行"）
3. 故意让微信限速触发（连续点 5 次以上，看 task_logs）
4. 检查 state.db messages 表：失败的那几条消息**不应该**出现
5. 检查 active.db task_logs：details.send_result.success=False，error 字段有内容
6. 检查 active.db active_heartbeat_logs：message_sent=False（来自 actual_sent）
7. 打开 ActiveConsciousness 心跳详情：标签显示 ❌ + 失败原因
8. 打开 ActiveConsciousness 念头详情：标签显示 ❌ + 失败原因
9. 查看念头列表"发送消息"列：失败念头显示"否"

### 集成验证

1. 触发心跳 → 自动发送消息 → 心跳列表显示 ✅ 是
2. 触发心跳 → 微信限速 → 心跳详情显示 ❌ + 失败原因 + 念头详情同步
3. 历史数据回看：之前失败的心跳日志详情仍能看到失败原因（从 details.message_sending 读取）

## 影响范围

| 改动 | 文件 | 影响 |
|------|------|------|
| 1 | backend/services/message_service.py | 失败时跳过 _write_to_state_db |
| 2 | frontend/src/views/ActiveConsciousness.vue | 心跳详情标签读 send_result |
| 3 | frontend/src/views/ActiveConsciousness.vue | 念头详情增加 send_result + 模板卡片 |
| 4 | frontend/src/views/ActiveConsciousness.vue | 念头列表列读 details_parsed.message_sending |

不涉及：
- scheduler_service.py（自动受益）
- 其他 message_service 内部方法（create_task_log 仍正常记录）
- hermes 源码

## 风险

1. **历史数据**：之前失败但已入库的消息仍会留在 state.db（不主动清理，避免数据丢失）
2. **Agent loop 上下文**：现有 session 上下文仍包含这批"幽灵消息"，可能让凯莉重复提及。需要用户手动清理 session 或重启
3. **念头详情 send_result 兼容**：旧念头日志的 details JSON 里可能没有 `message_sending` 字段——前端用 `?.message_sending?.success` 兜底，未读到时显示"未发送"

## 不在范围内

- 心跳 rate limit 防护（连续失败暂停）—— 后续单独 issue
- hermes session hygiene 修复 —— 之前已确认是 hermes 行为
- 历史污染消息清理 —— 手动处理
- 念头详情页面整体布局重构 —— 仅最小改动

## 验收标准

- [ ] 后端代码改动通过 `python -c "import ast; ast.parse(...)"` 语法检查
- [ ] 前端 build 成功
- [ ] 连续触发失败时，task_logs.details.send_result.success=False 准确反映
- [ ] 连续触发失败时，state.db messages 表不再增加新行
- [ ] 前端心跳详情"是否发送"标签根据 send_result.success 显示 + 失败时附原因
- [ ] 前端念头详情增加"发送结果"卡片，根据 message_sending.success 显示
- [ ] 前端念头列表"发送消息"列读 details_parsed.message_sending.success