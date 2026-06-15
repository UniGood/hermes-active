# 被动意识设计文档

## 功能说明

被动意识在用户消息到达时，自动注入上下文信息到系统提示词中，让凯莉了解当前的情绪状态、聊天热度、记忆等信息。

**不直接调用 LLM**，只提供上下文信息供 hermes 主 LLM 参考。

---

## 实现状态

### ✅ 已实现

| 功能 | 文件 | 说明 |
|------|------|------|
| 配置读写 | `passive_consciousness_service.py` | get_config / update_config |
| 状态查询 | `passive_consciousness_service.py` | get_status（longing, chat_heat, emotional_intensity） |
| 聊天记录查询 | `passive_consciousness_service.py` | get_chats（从 state.db 读取） |
| Hindsight Recall 测试 | `passive_consciousness.py` (router) | 调用 Hindsight API |
| Hindsight Reflect 测试 | `passive_consciousness.py` (router) | 调用 Hindsight API |
| 前端配置页面 | `PassiveConsciousness.vue` | LLM 模式选择、注入配置、Hindsight、天气 |
| 前端状态页面 | `PassiveConsciousness.vue` | 想念分数、聊天热度、情绪值 |
| 前端日志页面 | `PassiveConsciousness.vue` | 聊天记录 |

### ❌ 未实现

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 上下文注入到 hermes | 用户消息时自动注入情绪/热度/记忆到系统提示词 | **高** |
| 天气感知 | 调用高德 API 获取天气信息 | 低 |
| 被动意识日志表 | `passive_consciousness_logs` 表，记录注入历史 | 中 |

---

## 配置参数

存储在 `configs` 表，key 前缀：`passive_consciousness.`

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

---

## API 接口

前缀：`/api/passive-consciousness`

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | /config | 获取配置 | ✅ |
| PUT | /config | 更新配置 | ✅ |
| GET | /status | 获取状态 | ✅ |
| GET | /chats | 获取聊天记录 | ✅ |
| POST | /test/hindsight-recall | 测试 Hindsight Recall | ✅ |
| POST | /test/hindsight-reflect | 测试 Hindsight Reflect | ✅ |

---

## 数据库

**不创建独立表**，使用：
- `configs` 表存储配置（`passive_consciousness.*` 前缀）
- `state.db` 的 `messages` 和 `sessions` 表读取聊天记录（只读）

---

## 文件结构

```
backend/
├── models/passive_consciousness.py     # 数据模型
├── routers/passive_consciousness.py    # API 路由
└── services/passive_consciousness_service.py  # 业务逻辑

frontend/src/
├── views/PassiveConsciousness.vue      # 前端页面
└── api/passive_consciousness.js        # API 封装
```

---

## 不合理之处

1. **LLM 配置对被动意识无用**：被动意识不直接调用 LLM，但配置中有 LLM 相关参数，可以考虑移除
2. **缺少上下文注入实现**：核心功能（注入到 hermes 系统提示词）未实现
3. **天气感知未实现**：配置中有天气相关参数，但后端没有实现天气 API 调用
