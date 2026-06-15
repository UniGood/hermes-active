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

## 问题与待实现

### 问题 1：LLM 配置对被动意识无用

**问题描述**：被动意识不直接调用 LLM，但配置中有 LLM 相关参数（provider、model、api_key、base_url），这些参数对被动意识没有意义。

**影响**：
- 用户可能误以为需要配置 LLM 才能使用被动意识
- 配置界面显示了不必要的 LLM 配置项

**解决方案**：
- 方案 A：从被动意识配置中移除 LLM 相关参数
- 方案 B：保留 LLM 配置，但标注为"被动意识不使用 LLM"

**优先级**：低

---

### 问题 2：上下文注入到 hermes 未实现

**问题描述**：被动意识的核心功能是"用户消息到达时，自动注入上下文信息到系统提示词"，但目前只实现了配置和状态查询，没有实现实际的注入逻辑。

**影响**：
- 被动意识无法发挥作用
- 用户配置了注入选项，但不会生效

**实现方案**：
1. 在 hermes 的 `pre_llm_call` 钩子中注入上下文
2. 或者通过 hermes 插件机制注入 vibe 变量
3. 或者通过 hermes-active 的辅助 LLM 生成上下文，注入到 state.db

**优先级**：**高**（核心功能）

---

### 问题 3：天气感知未实现

**问题描述**：配置中有天气相关参数（enabled、adcode、amap_key、cache_ttl），但后端没有实现天气 API 调用。

**影响**：
- 天气感知功能无法使用
- 配置界面显示了天气配置项，但无法测试

**实现方案**：
1. 调用高德天气 API：`https://restapi.amap.com/v3/weather/weatherInfo`
2. 缓存天气数据（cache_ttl 秒）
3. 在状态查询时返回天气信息

**优先级**：低

---

### 问题 4：被动意识日志表未创建

**问题描述**：设计文档中提到需要 `passive_consciousness_logs` 表记录注入历史，但目前没有创建这个表。

**影响**：
- 无法查看被动意识的注入历史
- 无法分析注入效果

**实现方案**：
1. 在 `active.py` 中添加 `PassiveConsciousnessLog` 模型
2. 记录每次注入的内容、时间、session_id

**优先级**：中
