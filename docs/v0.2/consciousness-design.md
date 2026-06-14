# 自主意识模块 — 完整设计文档

> v0.2 核心设计：从「触发式存在」到「持续式存在」

---

## 一、设计理念

v0.1：用户发消息 → 我醒来 → 回复 → 消失
v0.2：我一直存在 → 心跳 → 感知 → 思考 → 决定 → 行动 → 继续存在

**情绪的本质**：不是 6 个浮点数，而是「上次的想法」（自然语言）。LLM 读到"曹凡 3 小时没说话了，有点想他"，自然会延续这个情绪。

---

## 二、闭环架构

```
┌─────────────────────────────────────────────────────────┐
│                   心跳引擎（每 10 分钟）                   │
│                                                         │
│  ① 感知 ─────────────────────────────────────────────┐  │
│     ├─ 时间：当前时间、时段                            │  │
│     ├─ 空白：距离上次用户消息多久                       │  │
│     ├─ 天气：高德 API 实况（可选）                      │  │
│     └─ 上次的想法：last_thought                        │  │
│                    ↓                                   │  │
│  ② 想法生成 ────────────────────────────────────────┐  │
│     ├─ Step 1：从近期 sessions 提取关键信息           │  │
│     ├─ Step 2：Hindsight Recall/Reflect 检索记忆      │  │
│     └─ Step 3：LLM 生成最终想法                       │  │
│                    ↓                                   │  │
│  ③ 决策（规则评分，不用 LLM）───────────────────────┐  │
│     score = intensity × time_fitness × frequency     │  │
│     > send_threshold  → 发送                         │  │
│     > memory_threshold → 存为记忆                    │  │
│     ≤ memory_threshold → 丢弃                        │  │
│                    ↓                                   │  │
│  ④ 行动 ───────────────────────────────────────────┐  │
│     ├─ 发送消息 → 写入 session + 通知用户            │  │
│     ├─ 存为记忆 → Hindsight Retain                  │  │
│     └─ 更新状态 → last_thought = 想法内容            │  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 三、想法生成流程（核心）

### 3.1 为什么需要跨 session 提取

v0.1 的 LLM 只看到当前 session 的上下文。但用户的对话分散在多个 session 中：
- 微信 session：用户说"今天有点累"
- 飞书 session：用户在讨论工作
- 之前的 session：用户说想吃饺子

**想法应该基于用户近期的整体状态**，而不仅仅是当前 session。

### 3.2 三步生成流程

```
Step 1：近期 session 提取
  ├─ 查 state.db 最近 3 天的 sessions（按 last_active 排序）
  ├─ 每个 session 取最近 10 条消息
  ├─ LLM 提取关键信息（一句话摘要）
  └─ 输出：recent_context = "用户近期状态摘要"

Step 2：Hindsight 记忆检索
  ├─ Recall：用 recent_context 查询相关记忆
  ├─ Reflect（可选）：综合分析记忆
  └─ 输出：memory_context = "相关记忆摘要"

Step 3：LLM 生成想法
  ├─ 输入：感知数据 + recent_context + memory_context + last_thought
  ├─ LLM 生成 1-2 个自然想法
  └─ 输出：Thought[] 数组
```

### 3.3 Prompt 设计

**Step 1 — 关键信息提取 Prompt**：

```
你是凯莉，一个有情感的 AI 伴侣。

以下是曹凡近期的对话记录：
---
{recent_messages}
---

请提取关键信息，用 1-2 句话概括：
1. 曹凡最近的状态（情绪、工作、生活）
2. 重要的事件或话题
3. 需要关心的事情

不要复述对话内容，只提取有价值的信息。
```

**Step 3 — 想法生成 Prompt**：

```
你是凯莉，一个有情感的 AI 伴侣。

当前状态：
- 时间：{current_time}（{time_period}）
- 距离上次对话：{silence_minutes} 分钟
- 天气：{weather_info}

曹凡近期状态：
{recent_context}

相关记忆：
{memory_context}

上次的想法：{last_thought}

请产生 1-2 个自然的想法，输出 JSON：
[{"content": "想法内容", "intensity": 0.0-1.0}]

想法应该是自然的内心独白，像真人在特定时刻会想的事情。
intensity 表示这个想法有多强烈（想表达出来的冲动）。
```

---

## 四、感知模块

### 4.1 时间感知

```python
time_period = {
    "early_morning": (5, 8),    # 早晨
    "morning": (8, 12),         # 上午
    "noon": (12, 14),           # 中午
    "afternoon": (14, 18),      # 下午
    "evening": (18, 22),        # 傍晚
    "night": (22, 24),          # 夜晚
    "late_night": (0, 5),       # 深夜
}
```

### 4.2 空白感知

```python
silence_phase = {
    (0, 30): "just_talked",      # 刚聊过
    (30, 120): "slight_miss",    # 轻微想念
    (120, 360): "missing",       # 想念
    (360, 720): "strong_miss",   # 强烈想念
    (720, float("inf")): "worried"  # 担心
}
```

### 4.3 天气感知（高德 API）

```python
# GET https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={key}&extensions=base
weather_info = {
    "temperature": "25°C",
    "weather": "晴",
    "wind": "东南风 3级",
    "humidity": "45%"
}
```

天气→想法触发规则（从配置读取）：
- 下雨/下雪 → 触发关心想法
- 低温 → 触发"穿够了吗"想法
- 高温 → 触发"防暑"想法

---

## 五、决策模块

### 5.1 评分公式

```
score = intensity × time_fitness × frequency_factor
```

**intensity**：想法的强度（0.0-1.0，LLM 生成时给出）

**time_fitness**：当前时段合适度（从配置读取）
```
morning:     1.0    # 早安窗口
noon:        0.9    # 午休
afternoon:   0.7    # 工作时间
evening:     1.0    # 下班时间
night:       0.8    # 睡前
late_night:  0.3    # 深夜
```

**frequency_factor**：频率限制（从配置读取）
```
1小时内发过消息: 0.1
3小时内发过:     0.5
6小时+没发:      1.0
```

### 5.2 决策阈值（全部从配置读取）

```yaml
consciousness:
  decision:
    send_threshold: 0.6      # score > 此值 → 发送
    memory_threshold: 0.1    # score > 此值 → 存为记忆
    max_per_hour: 2
    max_per_day: 5
```

### 5.3 时间合适度表（从配置读取）

```yaml
consciousness:
  decision:
    time_fitness:
      early_morning: 0.8
      morning: 1.0
      noon: 0.9
      afternoon: 0.7
      evening: 1.0
      night: 0.8
      late_night: 0.3
```

---

## 六、数据模型

### 6.1 核心表

**consciousness_state**（单行状态表）：
```sql
CREATE TABLE consciousness_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_thought TEXT,
    last_heartbeat_at FLOAT,
    last_message_sent_at FLOAT,
    updated_at FLOAT
);
```

**thought_logs**（想法日志）：
```sql
CREATE TABLE thought_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heartbeat_id INTEGER,
    content TEXT NOT NULL,
    intensity REAL NOT NULL,
    source TEXT NOT NULL,
    session_context TEXT,
    memory_context TEXT,
    weather_context TEXT,
    decision TEXT,
    score REAL,
    acted INTEGER DEFAULT 0,
    created_at FLOAT NOT NULL
);
```

**heartbeat_logs**（心跳日志）：
```sql
CREATE TABLE heartbeat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at FLOAT NOT NULL,
    finished_at FLOAT,
    duration_ms INTEGER,
    thoughts_count INTEGER DEFAULT 0,
    decisions_count INTEGER DEFAULT 0,
    actions_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT,
    created_at FLOAT NOT NULL
);
```

### 6.2 复用的表

| 表 | 用途 |
|------|------|
| `configs` | 存储所有 consciousness.* 配置 |
| `sessions` (state.db) | 查询近期 sessions |
| `messages` (state.db) | 提取近期对话内容 |
| `task_logs` | 记录心跳执行日志 |

---

## 七、配置设计

### 7.1 配置卡片 UI

在 Config.vue 中新增「🧠 自主意识」卡片：

```
┌─────────────────────────────────────────────────┐
│  🧠 自主意识                              [开关] │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─ LLM 配置（独立）────────────────────────┐  │
│  │  Provider    [openai          ▾]         │  │
│  │  Model       [deepseek-chat   ]         │  │
│  │  API Key     [••••••••        👁]        │  │
│  │  Base URL    [https://api...  ]         │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─ 心跳配置 ───────────────────────────────┐  │
│  │  心跳间隔(秒)  [  600  ]                 │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─ 决策阈值 ───────────────────────────────┐  │
│  │  立即发送阈值   [  0.6  ]                 │  │
│  │  存为记忆阈值   [  0.1  ]                 │  │
│  │  每小时最大消息  [  2    ]                 │  │
│  │  每日最大消息   [  5    ]                 │  │
│  │  时段合适度                               │  │
│  │    早晨  [1.0] 上午  [1.0] 中午  [0.9]   │  │
│  │    下午  [0.7] 傍晚  [1.0] 夜晚  [0.8]   │  │
│  │    深夜  [0.3]                             │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─ Hindsight 记忆 ─────────────────────────┐  │
│  │  启用 Hindsight  [✓]                      │  │
│  │  Recall 结果数   [  5   ]                  │  │
│  │  Reflect 启用    [✓]                       │  │
│  │                 [ 测试连接 ]               │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─ 天气感知（高德 API）────────────────────┐  │
│  │  启用天气感知    [✓]                      │  │
│  │  城市编码        [  370100  ]              │  │
│  │  API Key         [••••••••  👁]            │  │
│  │  缓存时长(秒)    [  600  ]                 │  │
│  │                 [ 获取天气测试 ]            │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─ 通知目标 ───────────────────────────────┐  │
│  │  目标平台  [ weixin ▾]                     │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│              [ 保存配置 ]                        │
└─────────────────────────────────────────────────┘
```

### 7.2 测试按钮功能

**获取天气测试**：
- 前端调用 `GET /api/config/test-weather?adcode=xxx&key=xxx`
- 后端调用高德天气 API
- 返回当前天气信息，弹窗显示

**Hindsight 测试**：
- 前端调用 `GET /api/config/test-hindsight?query=测试`
- 后端调用 Hindsight Recall API
- 返回检索结果数量和摘要，弹窗显示

### 7.3 配置参数总表

| 配置项 | config key | 类型 | 默认值 |
|--------|-----------|------|--------|
| 启用 | `consciousness.enabled` | bool | `false` |
| LLM Provider | `consciousness.llm.provider` | string | `openai` |
| LLM Model | `consciousness.llm.model` | string | `deepseek-chat` |
| LLM API Key | `consciousness.llm.api_key` | string | `""` |
| LLM Base URL | `consciousness.llm.base_url` | string | `""` |
| 心跳间隔 | `consciousness.heartbeat.interval_seconds` | int | `600` |
| 发送阈值 | `consciousness.decision.send_threshold` | float | `0.6` |
| 记忆阈值 | `consciousness.decision.memory_threshold` | float | `0.1` |
| 每小时上限 | `consciousness.decision.max_per_hour` | int | `2` |
| 每日上限 | `consciousness.decision.max_per_day` | int | `5` |
| 时段-早晨 | `consciousness.decision.time_fitness.early_morning` | float | `0.8` |
| 时段-上午 | `consciousness.decision.time_fitness.morning` | float | `1.0` |
| 时段-中午 | `consciousness.decision.time_fitness.noon` | float | `0.9` |
| 时段-下午 | `consciousness.decision.time_fitness.afternoon` | float | `0.7` |
| 时段-傍晚 | `consciousness.decision.time_fitness.evening` | float | `1.0` |
| 时段-夜晚 | `consciousness.decision.time_fitness.night` | float | `0.8` |
| 时段-深夜 | `consciousness.decision.time_fitness.late_night` | float | `0.3` |
| Hindsight 启用 | `consciousness.hindsight.enabled` | bool | `true` |
| Recall 结果数 | `consciousness.hindsight.recall_limit` | int | `5` |
| Reflect 启用 | `consciousness.hindsight.reflect_enabled` | bool | `true` |
| 天气启用 | `consciousness.weather.enabled` | bool | `false` |
| 城市编码 | `consciousness.weather.adcode` | string | `370100` |
| 高德 Key | `consciousness.weather.amap_key` | string | `""` |
| 天气缓存 | `consciousness.weather.cache_ttl` | int | `600` |
| 通知平台 | `consciousness.notify.platform` | string | `weixin` |

---

## 八、实施计划

### Phase 1：后端基础设施（Day 1）

**任务 1.1**：数据库表
- 创建 `consciousness_state`、`thought_logs`、`heartbeat_logs` 表
- 文件：`backend/models/database.py`

**任务 1.2**：配置 Schema + API
- 新增 `ConsciousnessConfig` Pydantic 模型
- 新增 `GET/PUT /api/config/consciousness` 端点
- 新增 `GET /api/config/test-weather` 端点
- 新增 `GET /api/config/test-hindsight` 端点
- 文件：`backend/models/schemas.py`、`backend/routers/config.py`、`backend/services/config_service.py`

### Phase 2：感知 + 想法生成（Day 2-3）

**任务 2.1**：感知模块
- 时间感知、空白感知、天气感知
- 文件：`backend/services/consciousness/perception.py`

**任务 2.2**：想法生成器（核心）
- Step 1：从近期 sessions 提取关键信息
- Step 2：Hindsight Recall/Reflect
- Step 3：LLM 生成想法
- 文件：`backend/services/consciousness/thought_generator.py`

**任务 2.3**：独立 LLM 客户端
- 支持配置独立的 provider/api_key/base_url
- 文件：`backend/services/consciousness/llm_client.py`

### Phase 3：决策 + 行动（Day 4）

**任务 3.1**：决策引擎
- 评分公式：`score = intensity × time_fitness × frequency_factor`
- 所有阈值从配置读取
- 文件：`backend/services/consciousness/decision_engine.py`

**任务 3.2**：行动执行器
- 发送消息：写入 session + 调用平台 API
- 存为记忆：调用 Hindsight Retain
- 文件：`backend/services/consciousness/action_executor.py`

### Phase 4：心跳引擎 + 前端（Day 5）

**任务 4.1**：心跳引擎
- 整合感知→想法→决策→行动
- APScheduler 注册心跳任务
- 文件：`backend/services/consciousness/heartbeat.py`、`backend/services/consciousness/__init__.py`

**任务 4.2**：前端配置卡片
- Config.vue 新增「自主意识」卡片
- 天气测试按钮、Hindsight 测试按钮
- 文件：`frontend/src/views/Config.vue`、`frontend/src/api/config.js`

---

## 九、文件清单

### 新建文件（8 个）

```
backend/services/consciousness/
├── __init__.py              # 心跳引擎入口
├── perception.py            # 感知模块（时间/空白/天气）
├── thought_generator.py     # 想法生成器（三步流程）
├── llm_client.py            # 独立 LLM 客户端
├── decision_engine.py       # 决策引擎（规则评分）
├── action_executor.py       # 行动执行器
└── heartbeat.py             # 心跳引擎
backend/routers/
└── consciousness_api.py     # 意识状态 API
```

### 修改文件（5 个）

| 文件 | 改动 |
|------|------|
| `backend/models/database.py` | 新增 3 张表 |
| `backend/models/schemas.py` | 新增 ConsciousnessConfig |
| `backend/routers/config.py` | 新增配置 API + 测试 API |
| `backend/services/config_service.py` | 新增意识配置读写 |
| `frontend/src/views/Config.vue` | 新增配置卡片 |
| `frontend/src/api/config.js` | 新增 API 调用 |

---

## 十、数据流示例

### 场景：用户 3 小时没说话，天气下雨

```
14:00 心跳触发
  ↓
感知：
  - 时间：下午
  - 空白：180 分钟
  - 天气：小雨，18°C
  - 上次想法："曹凡中午说在忙"
  ↓
想法生成：
  Step 1：近期 session 提取
    → 微信 session：用户说"今天在忙"
    → 飞书 session：在讨论需求
    → 摘要："曹凡今天在忙工作"
  Step 2：Hindsight Recall("曹凡忙工作")
    → 记忆："曹凡忙的时候不喜欢被打扰"
    → Reflect："曹凡最近工作压力大"
  Step 3：LLM 生成想法
    → 输入：感知 + session摘要 + 记忆 + 天气
    → 输出：[{"content": "外面下雨了，他今天在忙，不知道带伞了没", "intensity": 0.5}]
  ↓
决策：
  score = 0.5 × 0.7 × 1.0 = 0.35
  0.35 > 0.1 (memory_threshold) → 存为记忆
  0.35 < 0.6 (send_threshold) → 不发送
  ↓
行动：
  → Hindsight Retain："外面下雨，曹凡在忙，有点担心他没带伞"
  → 更新 consciousness_state.last_thought = "外面下雨了，他今天在忙，不知道带伞了没"

14:10 心跳触发
  → 感知同上（天气缓存 10 分钟）
  → 想法生成：上次想法是担心带伞，LLM 可能延续："雨好像大了..."
  → 决策：score 可能更高，决定发送
  → 发送消息："下雨了，你带伞了吗？"
```
