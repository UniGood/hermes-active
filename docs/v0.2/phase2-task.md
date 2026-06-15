# Task: 自主意识 Phase 2 — 前端开发

## 目标
开发独立的「自主意识」管理页面，包含配置、状态、日志、测试、聊天记录。

## 必读文件
1. `docs/v0.2/consciousness-design.md` — 核心设计
2. `docs/v0.2/consciousness-path-a.md` — 被动意识设计
3. `frontend/src/views/Consciousness.vue` — 当前占位页面
4. `frontend/src/views/Config.vue` — 参考布局和样式
5. `frontend/src/views/CronJobs.vue` — 参考日志展示
6. `frontend/src/views/SessionDetail.vue` — 参考聊天记录展示
7. `frontend/src/api/consciousness.js` — 已有的 API 封装

## 严格规则
- 只修改 `frontend/src/views/Consciousness.vue` 和 `frontend/src/api/consciousness.js`
- 不要修改后端文件
- 不要运行 git 命令
- 不要修改配置文件
- 样式参考 Config.vue 的卡片风格

## Consciousness.vue 页面结构

页面分为 5 个 Tab（用 n-tabs）：

### Tab 1: 配置
- 总开关 (n-switch)
- 被动意识配置（提示词模板、注入标记、是否注入情绪/热度/记忆/想法）
- 主动意识配置（心跳间隔、发送标记、时间格式、禁止窗口）
- 想法生成配置（session 来源、时间范围、消息限制、Tool 过滤）
- 决策阈值（send/delay/memory threshold、最大消息数）
- Hindsight 配置（开关、recall limit、reflect）
- 天气感知配置（开关、adcode、API key、缓存时长）
- 通知目标（平台、chat_id）
- 保存按钮

每个配置项用 n-form-item，label 左侧，控件右侧。
API Key 类字段用 n-input type="password" show-password-on="mousedown"。

### Tab 2: 状态
- 心跳状态卡片（count、活跃状态）
- 想念分数卡片（score + 进度条 + 等级标签）
- 聊天热度卡片（heat + 进度条 + 等级标签）
- 情绪值卡片（value + 进度条）
- 活跃 session 数
- 上次发送时间
- 今日消息数 / 每小时消息数

### Tab 3: 日志
- 念头日志表（n-data-table）：时间、类型、内容、强度、决策、来源
- 心跳日志表：时间、耗时、更新情绪、触发召回、召回数量、生成想法数、发送消息
- 操作列：删除、重试（发送）

### Tab 4: 测试
- 天气测试按钮 + 结果弹窗
- Hindsight Recall 测试 + 结果弹窗
- Hindsight Reflect 测试 + 结果弹窗
- 想法生成测试 + 结果弹窗

### Tab 5: 聊天记录
- 最近 50 条聊天记录（n-list）
- 每条显示：时间、来源标记、角色标签（用户蓝色/凯莉粉色）、内容
- 用户消息右对齐，凯莉消息左对齐

## 样式要求
- 卡片：白色背景、圆角、阴影
- 标签颜色：用户=蓝色(#18a058)、凯莉粉色(#ff9a9e)
- 进度条颜色：低=绿、中=黄、高=红
- 弹窗：宽度 800px
- 参考 Config.vue 的整体风格

## 完成后
确认页面能正确渲染，API 调用正确。
