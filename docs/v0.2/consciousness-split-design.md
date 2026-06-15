# 自主意识拆分方案 — 被动意识 + 主动意识

## 拆分背景

原"自主意识"功能包含两个独立的意识模式：
1. **被动意识**：用户消息时注入上下文（情绪、热度、记忆、想法等）
2. **主动意识**：心跳触发，主动发送消息

这两个模式功能独立、配置独立、日志独立，拆分为两个菜单更清晰。

---

## 功能对比

| 功能 | 被动意识 | 主动意识 |
|------|----------|----------|
| **触发时机** | 用户消息到达时 | 心跳定时触发 |
| **核心功能** | 注入上下文到系统提示词 | 生成想法并决定是否发送 |
| **LLM 调用** | 不直接调用（注入上下文） | 调用 LLM 生成想法 |
| **配置重点** | 注入开关、Hindsight、天气 | 心跳间隔、决策阈值、通知目标 |
| **日志类型** | 聊天记录 | 想法日志、心跳日志 |

---

## 表结构设计

### 1. 配置表（configs）

配置数据存储在 `configs` 表中，使用不同的 key 前缀区分：

#### 被动意识配置（前缀：`passive_consciousness.`）

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `passive_consciousness.enabled` | bool | false | 总开关 |
| `passive_consciousness.llm.mode` | string | hermes | LLM 模式（hermes/custom） |
| `passive_consciousness.llm.provider` | string | openai | LLM 提供商 |
| `passive_consciousness.llm.model` | string | deepseek-chat | 模型名称 |
| `passive_consciousness.llm.api_key` | string | "" | API Key |
| `passive_consciousness.llm.base_url` | string | "" | Base URL |
| `passive_consciousness.passive.enabled` | bool | true | 启用注入 |
| `passive_consciousness.passive.inject_emotion` | bool | true | 注入情绪 |
| `passive_consciousness.passive.inject_heat` | bool | true | 注入热度 |
| `passive_consciousness.passive.inject_memory` | bool | true | 注入记忆 |
| `passive_consciousness.passive.inject_thought` | bool | true | 注入想法 |
| `passive_consciousness.passive.thought_max_chars` | int | 200 | 想法最大字符 |
| `passive_consciousness.passive.vibe_max_chars` | int | 50 | Vibe 最大字符 |
| `passive_consciousness.passive.inject_tag` | string | [CONSCIOUSNESS_CONTEXT] | 注入标记 |
| `passive_consciousness.passive.time_format` | string | %H:%M | 时间格式 |
| `passive_consciousness.session.sources` | json | ["weixin"] | Session 来源 |
| `passive_consciousness.session.time_range_hours` | int | 24 | 时间范围（小时） |
| `passive_consciousness.session.max_messages_per_session` | int | 15 | 每个 Session 最大消息数 |
| `passive_consciousness.session.filter_tool_messages` | bool | true | 过滤 tool 消息 |
| `passive_consciousness.hindsight.enabled` | bool | true | 启用 Hindsight |
| `passive_consciousness.hindsight.recall_limit` | int | 5 | Recall 结果数 |
| `passive_consciousness.hindsight.reflect_enabled` | bool | true | 启用 Reflect |
| `passive_consciousness.weather.enabled` | bool | false | 启用天气感知 |
| `passive_consciousness.weather.adcode` | string | 370100 | 城市编码 |
| `passive_consciousness.weather.amap_key` | string | "" | 高德 API Key |
| `passive_consciousness.weather.cache_ttl` | int | 600 | 缓存时长（秒） |

#### 主动意识配置（前缀：`active_consciousness.`）

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `active_consciousness.enabled` | bool | false | 总开关 |
| `active_consciousness.llm.mode` | string | hermes | LLM 模式（hermes/custom） |
| `active_consciousness.llm.provider` | string | openai | LLM 提供商 |
| `active_consciousness.llm.model` | string | deepseek-chat | 模型名称 |
| `active_consciousness.llm.api_key` | string | "" | API Key |
| `active_consciousness.llm.base_url` | string | "" | Base URL |
| `active_consciousness.active.enabled` | bool | true | 启用心跳 |
| `active_consciousness.active.heartbeat_interval` | int | 600 | 心跳间隔（秒） |
| `active_consciousness.active.send_tag` | string | [凯莉主动发送] | 发送标记 |
| `active_consciousness.active.time_format` | string | %H:%M | 时间格式 |
| `active_consciousness.active.no_send_after_user_msg_minutes` | int | 10 | 禁止窗口（用户消息后分钟） |
| `active_consciousness.active.no_send_while_heat_above` | float | 0.5 | 热度阈值（超过则不发送） |
| `active_consciousness.active.no_send_while_vibe_below` | float | 0.3 | Vibe 阈值（低于则不发送） |
| `active_consciousness.session.sources` | json | ["weixin"] | Session 来源 |
| `active_consciousness.session.time_range_hours` | int | 24 | 时间范围（小时） |
| `active_consciousness.session.max_messages_per_session` | int | 15 | 每个 Session 最大消息数 |
| `active_consciousness.session.filter_tool_messages` | bool | true | 过滤 tool 消息 |
| `active_consciousness.decision.send_threshold` | float | 0.6 | 发送阈值 |
| `active_consciousness.decision.delay_threshold` | float | 0.3 | 延迟发送阈值 |
| `active_consciousness.decision.memory_threshold` | float | 0.1 | 存为记忆阈值 |
| `active_consciousness.decision.max_per_hour` | int | 2 | 每小时最大消息 |
| `active_consciousness.decision.max_per_day` | int | 5 | 每日最大消息 |
| `active_consciousness.notify.platform` | string | weixin | 通知平台 |
| `active_consciousness.notify.chat_id` | string | "" | 通知 Chat ID |

---

### 2. 日志表

#### thought_logs（想法日志 — 主动意识使用）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| heartbeat_id | INTEGER | 关联的心跳 ID |
| type | VARCHAR | 类型（thought/reflection/recall） |
| content | TEXT | 内容 |
| intensity | FLOAT | 强度 |
| decision | VARCHAR | 决策（send/delay/memory/skip） |
| reason | TEXT | 决策原因 |
| score | FLOAT | 分数 |
| recall_count | INTEGER | Recall 结果数 |
| recall_source | VARCHAR | Recall 来源 |
| chat_heat | FLOAT | 聊天热度 |
| emotional_intensity | FLOAT | 情绪值 |
| created_at | DATETIME | 创建时间 |

#### heartbeat_logs（心跳日志 — 主动意识使用）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| started_at | DATETIME | 开始时间 |
| duration_ms | INTEGER | 持续时间（毫秒） |
| longing_before | FLOAT | 想念分数（前） |
| longing_after | FLOAT | 想念分数（后） |
| chat_heat | FLOAT | 聊天热度 |
| emotional_intensity | FLOAT | 情绪值 |
| recall_count | INTEGER | Recall 结果数 |
| reflect_count | INTEGER | Reflect 结果数 |
| thoughts_generated | INTEGER | 生成想法数 |
| message_sent | BOOLEAN | 是否发送消息 |
| error | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |

#### chat_records（聊天记录 — 被动意识使用）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| session_id | VARCHAR | Session ID |
| source | VARCHAR | 来源（weixin/feishu） |
| role | VARCHAR | 角色（user/assistant） |
| content | TEXT | 内容 |
| send_mark | VARCHAR | 发送标记 |
| timestamp | DATETIME | 时间戳 |

---

## API 接口

### 被动意识 API（前缀：`/api/passive-consciousness`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /config | 获取配置 |
| PUT | /config | 更新配置 |
| GET | /status | 获取状态 |
| GET | /chats | 获取聊天记录 |
| POST | /test/hindsight-recall | 测试 Hindsight Recall |
| POST | /test/hindsight-reflect | 测试 Hindsight Reflect |

### 主动意识 API（前缀：`/api/active-consciousness`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /config | 获取配置 |
| PUT | /config | 更新配置 |
| GET | /status | 获取状态 |
| GET | /thoughts | 获取想法日志 |
| DELETE | /thoughts/{id} | 删除想法 |
| POST | /thoughts/{id}/retry | 重试想法 |
| GET | /heartbeats | 获取心跳日志 |
| DELETE | /heartbeats/{id} | 删除心跳 |
| POST | /test/thought-generation | 测试想法生成 |

---

## 前端页面

### 被动意识页面（PassiveConsciousness.vue）

**3 个 Tab**：
1. **配置 Tab**：LLM 配置（mode 选择 hermes/custom）、被动意识配置、Hindsight 配置、天气感知
2. **状态 Tab**：想念分数、聊天热度、情绪值
3. **日志 Tab**：聊天记录

### 主动意识页面（ActiveConsciousness.vue）

**4 个 Tab**：
1. **配置 Tab**：LLM 配置（mode 选择 hermes/custom）、主动意识配置、决策配置、通知目标
2. **状态 Tab**：心跳状态、发送统计
3. **日志 Tab**：想法日志、心跳日志
4. **测试 Tab**：想法生成测试

---

## 文件结构

```
backend/
├── models/
│   ├── passive_consciousness.py    # 被动意识数据模型
│   └── active_consciousness.py     # 主动意识数据模型
├── routers/
│   ├── passive_consciousness.py    # 被动意识路由
│   └── active_consciousness.py     # 主动意识路由
└── services/
    ├── passive_consciousness_service.py  # 被动意识服务
    └── active_consciousness_service.py   # 主动意识服务

frontend/src/
├── views/
│   ├── PassiveConsciousness.vue    # 被动意识页面
│   └── ActiveConsciousness.vue     # 主动意识页面
└── api/
    ├── passive_consciousness.js    # 被动意识 API
    └── active_consciousness.js     # 主动意识 API
```

---

## 配置迁移

原 `consciousness.*` 配置需要迁移到新前缀：

| 原 Key | 新 Key |
|--------|--------|
| `consciousness.enabled` | `passive_consciousness.enabled` + `active_consciousness.enabled` |
| `consciousness.llm.*` | `passive_consciousness.llm.*` + `active_consciousness.llm.*` |
| `consciousness.passive.*` | `passive_consciousness.passive.*` |
| `consciousness.active.*` | `active_consciousness.active.*` |
| `consciousness.session.*` | `passive_consciousness.session.*` + `active_consciousness.session.*` |
| `consciousness.decision.*` | `active_consciousness.decision.*` |
| `consciousness.hindsight.*` | `passive_consciousness.hindsight.*` |
| `consciousness.weather.*` | `passive_consciousness.weather.*` |
| `consciousness.notify.*` | `active_consciousness.notify.*` |
