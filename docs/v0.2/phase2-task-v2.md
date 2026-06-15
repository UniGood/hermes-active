# Task: 自主意识前端页面开发（Vue 3 + Naive UI）

## ⚠️ 关键约束
- 这是 **Vue 3 + Naive UI** 项目，**不是 React**
- 只修改 `frontend/src/views/Consciousness.vue`
- 只修改 `frontend/src/api/consciousness.js`
- **不要创建任何 React/TypeScript 文件**
- **不要创建 web/src/ 目录**
- 参考 `frontend/src/views/Config.vue` 的布局和样式

## 必读文件
1. `docs/v0.2/consciousness-design.md` — 核心设计（参数表、API 端点）
2. `frontend/src/views/Config.vue` — 参考布局（n-card、n-form-item、n-switch、n-input 等）
3. `frontend/src/api/consciousness.js` — 已有 API 封装（需扩展）

## Consciousness.vue 结构

用 `n-tabs` 分 5 个 Tab：

### Tab 1: 配置
- 总开关 (n-switch)
- 被动意识（提示词模板 textarea、注入标记 input、是否注入情绪/热度/记忆/想法）
- 主动意识（心跳间隔 number input、发送标记 input、时间格式 input、禁止窗口 number input）
- 想法生成（时间范围 number input、消息限制 number input、Tool 过滤 switch）
- 决策阈值（send/delay/memory threshold number input、最大消息数 number input）
- Hindsight（开关 switch、recall limit number input、reflect switch）
- 天气感知（开关 switch、adcode input、API key password input、缓存时长 number input）
- 通知目标（平台 select、chat_id input）
- 保存按钮

### Tab 2: 状态
- 心跳状态卡片（count、活跃状态）
- 想念分数卡片（score + 进度条）
- 聊天热度卡片（heat + 进度条）
- 情绪值卡片（value + 进度条）
- 活跃 session 数、上次发送时间、今日消息数

### Tab 3: 日志
- 念头日志表（n-data-table）：时间、类型、内容、强度、决策、来源
- 心跳日志表：时间、耗时、触发召回、召回数量、生成想法数、发送消息

### Tab 4: 测试
- 天气测试按钮 + 结果弹窗
- Hindsight Recall 测试 + 结果弹窗
- Hindsight Reflect 测试 + 结果弹窗
- 想法生成测试 + 结果弹窗

### Tab 5: 聊天记录
- 最近 50 条聊天记录（n-list）
- 时间、来源标记、角色标签（用户蓝色/凯莉粉色）、内容

## consciousness.js 扩展

在现有基础上添加：
- `loadConfig()` — GET /config/consciousness
- `saveConfig(data)` — PUT /config/consciousness
- `getStatus()` — GET /consciousness/status
- `getThoughtLogs()` — GET /consciousness/thought-logs
- `getHeartbeatLogs()` — GET /consciousness/heartbeat-logs
- `getChatHistory()` — GET /consciousness/chat-history
- `retryThought(id)` — POST /consciousness/thought-logs/{id}/retry
- `deleteThought(id)` — DELETE /consciousness/thought-logs/{id}
- `testWeather()` — GET /consciousness/test/weather
- `testRecall(query)` — POST /consciousness/test/recall
- `testReflect(query)` — POST /consciousness/test/reflect
- `testThought()` — POST /consciousness/test/generate-thought

## 完成后验证
```bash
cd ~/.hermes/hermes-active/frontend && npm run dev
```
在浏览器中打开 /consciousness，确认 5 个 Tab 都能正常渲染。
