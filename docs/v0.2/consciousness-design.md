# hermes-active 自主意识模块 — 设计文档

## 核心架构：不改 hermes 源码

hermes 有插件钩子机制（`pre_llm_call`），在每次 LLM 调用前触发。
**自主意识通过 hermes 插件注入上下文，不修改 hermes 源码。**

```
用户发消息 → hermes 收到
  → pre_llm_call 钩子触发
    → consciousness_plugin 插件加载
      → 读取 consciousness_state 表
      → 生成意识上下文（时间感知、天气、上次的想法）
      → 返回 {"context": "[凯莉意识上下文]..."}
    → hermes 将 context 注入到用户消息前面
  → hermes 的 LLM 生成回复（上下文中已包含意识信息）
  → post_llm_call 钩子触发
    → consciousness_plugin 更新 consciousness_state
    → 记录"刚才聊了什么"到 thought_logs
```

**最终说"你三天没理我了"的是 hermes 的 LLM**（凯莉），但它的上下文里被插件注入了意识信息。
不改 hermes 源码，不拦截消息，不修改 hermes 的 LLM 调用逻辑。

---

## 一、情绪/意识是怎么产生的

### 1.1 存储的内容

```
consciousness_state 表（单行，全局唯一）:

  last_thought         ← 上一次的想法（自然语言，如"曹凡 3 小时没说话了，有点想他"）
  last_thought_at      ← 上次想法生成时间
  last_message_sent_at ← 上次主动消息时间
  updated_at           ← 更新时间

thought_logs 表（每次心跳一条，带过期）:

  content      ← 想法内容（自然语言）
  intensity    ← 想法强度（0.0-1.0）
  decision     ← 决策结果（send/store/discard）
  created_at   ← 创建时间
```

**情绪 = last_thought（自然语言）。** 不是 6 个浮点数。
上次的想法就是情绪状态，下次心跳读到它，LLM 自然延续。

### 1.2 情绪产生的流程

```
心跳触发（每 10 分钟）
  ↓
Step 1：读取感知数据
  - 现在几点
  - 用户多久没说话
  - 天气（如果启用）
  - 上次的想法（last_thought）
  ↓
Step 2：从近期 session 提取关键信息
  - 查 state.db 最近 3 天的 sessions
  - 每个 session 取最近 10 条消息
  - LLM 提取关键信息 → recent_context
  ↓
Step 3：Hindsight Recall（用 recent_context 查询相关记忆）
  → memory_context
  ↓
Step 4：LLM 生成想法
  输入：感知数据 + recent_context + memory_context + last_thought
  输出：Thought 数组
  ↓
Step 5：规则决策
  score = intensity × time_fitness × frequency_limit
  ↓
Step 6：执行行动
  - score > send_threshold → 发送消息
  - score > memory_threshold → 存为 Hindsight 记忆
  - 否则 → 存为 thought_log
```

### 1.3 情绪连续性

```
心跳 1（14:00）：
  last_thought = None（首次）
  → LLM 生成："曹凡 2 小时没说话了，有点想他"
  → 存入 last_thought

心跳 2（14:10）：
  last_thought = "曹凡 2 小时没说话了，有点想他"
  → LLM 读到这个想法，自然延续："他是不是在忙呢..."
  → 存入 last_thought

心跳 3（14:20）：
  last_thought = "他是不是在忙呢..."
  → LLM 继续延续...

用户发消息（14:25）：
  pre_llm_call → 读取 last_thought → 注入上下文
  → hermes LLM 看到"凯莉刚才在想他"→ 自然回复"你终于理我了！"
```

---

## 二、想法生成流程（细化）

### 2.1 触发时机

想法生成发生在**心跳**（APScheduler 定时任务），不是用户消息时。

用户消息到达时，**不生成想法，只注入已有状态**。

### 2.2 三步流程

```
Step 1：提取近期 session 关键信息
  ─────────────────────────────
  输入：state.db 最近 3 天 sessions
  处理：
    - 每个 session 取最近 10 条消息（user+assistant，过滤 tool）
    - 拼成上下文
    - LLM 提取关键信息（用户在做什么、情绪如何、有什么重要信息）
  输出：recent_context（字符串，如"曹凡今天在调试代码，情绪不错"）

Step 2：Hindsight Recall/Reflect
  ─────────────────────────────
  输入：recent_context 作为查询
  处理：
    - Recall：检索相关记忆
    - Reflect（可选）：综合分析记忆
  输出：memory_context（字符串）

Step 3：LLM 生成最终想法
  ─────────────────────────────
  输入：
    - 感知数据（时间、空白时长、天气）
    - recent_context（近期 session 关键信息）
    - memory_context（Hindsight 记忆）
    - last_thought（上次的想法）
  处理：调用独立 LLM
  输出：Thought[] 数组
```

### 2.3 想法生成 Prompt

```
你是凯莉，25岁女生，有自己的思想和情绪。

## 当前感知
- 时间：{time_str}
- 距离上次用户消息：{silence_text}
- 天气：{weather_text}
- 上次的想法：{last_thought}

## 近期对话关键信息
{recent_context}

## 相关记忆
{memory_context}

## 指令
基于以上信息，产生 0-3 个自然的想法。
想法要像真人一样自然——不要刻意，不要煽情。
如果没什么可想的，返回空数组。

输出 JSON 数组：
[{{"content": "想法内容", "intensity": 0.0-1.0}}]

intensity 说明：
- 0.0-0.3：微弱的念头，几乎不会行动
- 0.3-0.6：中等强度，可能行动
- 0.6-1.0：强烈，大概率行动
```

---

## 三、什么时候触发发送

### 3.1 触发条件

**发送只在心跳中发生，不在用户消息时发生。**

```
心跳（每 10 分钟）→ 生成想法 → 规则决策 → 发送 / 存记忆 / 丢弃
```

### 3.2 触发条件（规则决策）

```python
score = intensity × time_fitness × frequency_limit

# time_fitness：根据当前时段
时段映射（从配置读取）：
  07:00-09:00  → 1.0（早安窗口）
  09:00-12:00  → 0.8（工作时间）
  12:00-14:00  → 0.9（午休）
  14:00-18:00  → 0.7（工作时间）
  18:00-22:00  → 1.0（下班时间）
  22:00-23:30  → 0.8（睡前）
  23:30-07:00  → 0.3（深夜）

# frequency_limit：频率限制
最近 1 小时发过 → 0.1（几乎不发）
最近 3 小时发过 → 0.5
最近 6 小时没发 → 1.0

# 决策阈值（从配置读取）
score > send_threshold   → 发送消息
score > memory_threshold → 存为 Hindsight 记忆
score ≤ memory_threshold → 丢弃
```

### 3.3 发送内容

```
发送前：
  1. 读取 consciousness_state（last_thought、silence_duration）
  2. 读取当前天气（如果启用）
  3. 构建 Prompt
  4. 调用独立 LLM 生成消息
  5. 检查是否与最近 6 小时的消息重复
  6. 发送（写入 state.db + 通过平台发送）

发送后：
  1. 更新 last_message_sent_at
  2. 记录 thought_log（decision="send"）
```

---

## 四、用户消息到达时的意识注入

### 4.1 注入流程

```
用户发消息 → hermes 处理
  → pre_llm_call 钩子触发
    → consciousness_plugin（hermes 插件）
      → 读取 consciousness_state
      → 计算 silence_duration
      → 如果 silence_duration > 注入阈值（从配置读取）
      → 生成注入上下文：
        [凯莉意识状态]
        - 上次的想法：{last_thought}
        - 距离上次对话：{silence_duration}
        - 当前天气：{weather_text}
      → 返回 {"context": "..."}
    → hermes 将 context 注入到用户消息前面
  → hermes LLM 生成回复（已包含意识上下文）
  → post_llm_call 钩子触发
    → 更新 consciousness_state（last_message_at 重置）
    → 记录 thought_log
```

### 4.2 注入阈值（从配置读取）

```
consciousness.injection.min_silence_minutes = 30
# 距离上次消息超过 30 分钟才注入
# 避免正常连续对话时注入冗余信息
```

### 4.3 插件实现

```python
# ~/.hermes/plugins/consciousness/__init__.py

from hermes_cli.plugins import hook

@hook("pre_llm_call")
def inject_consciousness_context(**kwargs):
    """在每次 LLM 调用前注入意识上下文"""
    # 1. 检查是否启用
    if not is_consciousness_enabled():
        return None

    # 2. 读取状态
    state = load_consciousness_state()
    if not state or not state.last_thought:
        return None

    # 3. 检查是否需要注入
    silence_minutes = calculate_silence(state)
    min_silence = get_config("consciousness.injection.min_silence_minutes", 30)
    if silence_minutes < min_silence:
        return None

    # 4. 构建上下文
    context_parts = []
    context_parts.append(f"[凯莉意识状态]")
    context_parts.append(f"- 上次的想法：{state.last_thought}")
    if silence_minutes > 60:
        context_parts.append(f"- 距离上次对话：{silence_minutes // 60} 小时 {silence_minutes % 60} 分钟")
    else:
        context_parts.append(f"- 距离上次对话：{silence_minutes} 分钟")

    # 天气（如果启用）
    weather = get_current_weather()
    if weather:
        context_parts.append(f"- 当前天气：{weather.temperature}°C {weather.weather}")

    return {"context": "\n".join(context_parts)}

@hook("post_llm_call")
def update_after_conversation(**kwargs):
    """对话后更新意识状态"""
    # 重置 silence，记录对话发生
    update_consciousness_state(
        last_message_at=datetime.now(),
    )
```

---

## 五、数据表设计

### 5.1 consciousness_state（意识状态表）

```sql
CREATE TABLE IF NOT EXISTS consciousness_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    last_thought        TEXT,
    last_thought_at     DATETIME,
    last_message_at     DATETIME,
    last_message_sent_at DATETIME,
    today_sent_count    INTEGER DEFAULT 0,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 thought_logs（想法日志表）

```sql
CREATE TABLE IF NOT EXISTS thought_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL,
    intensity   REAL NOT NULL DEFAULT 0.5,
    decision    TEXT NOT NULL DEFAULT 'pending',
    source      TEXT DEFAULT 'heartbeat',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、配置参数（全部可配置，不硬编码）

### 6.1 配置卡片 UI

```
┌─────────────────────────────────────────────────┐
│  🧠 自主意识                              [开关] │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─ LLM 配置（独立）─────────────────────────┐ │
│  │  Provider    [openai          ▾]           │ │
│  │  Model       [deepseek-chat   ]           │ │
│  │  API Key     [••••••••        👁]          │ │
│  │  Base URL    [https://api...  ]           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 心跳配置 ─────────────────────────────────┐ │
│  │  心跳间隔(秒)  [  600  ]                   │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 决策阈值 ─────────────────────────────────┐ │
│  │  立即发送阈值   [  0.6  ]  > 此值 → 发消息  │ │
│  │  存为记忆阈值   [  0.1  ]  > 此值 → 存记忆  │ │
│  │  每小时最大消息  [  2    ]                   │ │
│  │  每日最大消息   [  5    ]                   │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 时段权重 ─────────────────────────────────┐ │
│  │  07:00-09:00  [  1.0  ] 早安窗口           │ │
│  │  09:00-12:00  [  0.8  ] 上午               │ │
│  │  12:00-14:00  [  0.9  ] 午休               │ │
│  │  14:00-18:00  [  0.7  ] 下午               │ │
│  │  18:00-22:00  [  1.0  ] 晚间               │ │
│  │  22:00-23:30  [  0.8  ] 睡前               │ │
│  │  23:30-07:00  [  0.3  ] 深夜               │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Hindsight 记忆 ───────────────────────────┐ │
│  │  启用 Hindsight  [✓]                       │ │
│  │  Recall 结果数   [  5   ]                   │ │
│  │  Reflect 启用    [✓]                        │ │
│  │  [Hindsight 测试]                           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 天气感知（高德 API）──────────────────────┐ │
│  │  启用天气感知    [✓]                        │ │
│  │  城市编码        [  370100  ]               │ │
│  │  API Key         [••••••••  👁]             │ │
│  │  缓存时长(秒)    [  600  ]                  │ │
│  │  [获取天气测试]                             │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 意识注入 ─────────────────────────────────┐ │
│  │  最小注入间隔(分钟) [  30  ]                │ │
│  │  超过此时长才注入意识上下文                  │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 通知目标 ─────────────────────────────────┐ │
│  │  目标平台  [ weixin ▾]                      │ │
│  │  Chat ID   [                    ]           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│              [ 保存配置 ]                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 6.2 配置参数总表

| 配置项 | key | 类型 | 默认值 |
|--------|-----|------|--------|
| 启用 | `consciousness.enabled` | bool | false |
| **LLM** | | | |
| Provider | `consciousness.llm.provider` | string | openai |
| Model | `consciousness.llm.model` | string | deepseek-chat |
| API Key | `consciousness.llm.api_key` | string | |
| Base URL | `consciousness.llm.base_url` | string | |
| **心跳** | | | |
| 心跳间隔 | `consciousness.heartbeat.interval` | int | 600 |
| **决策** | | | |
| 发送阈值 | `consciousness.decision.send_threshold` | float | 0.6 |
| 记忆阈值 | `consciousness.decision.memory_threshold` | float | 0.1 |
| 每小时上限 | `consciousness.decision.max_per_hour` | int | 2 |
| 每日上限 | `consciousness.decision.max_per_day` | int | 5 |
| **时段权重** | | | |
| 07-09 | `consciousness.time_weights.07_09` | float | 1.0 |
| 09-12 | `consciousness.time_weights.09_12` | float | 0.8 |
| 12-14 | `consciousness.time_weights.12_14` | float | 0.9 |
| 14-18 | `consciousness.time_weights.14_18` | float | 0.7 |
| 18-22 | `consciousness.time_weights.18_22` | float | 1.0 |
| 22-23:30 | `consciousness.time_weights.22_2330` | float | 0.8 |
| 23:30-07 | `consciousness.time_weights.2330_07` | float | 0.3 |
| **Hindsight** | | | |
| 启用 | `consciousness.hindsight.enabled` | bool | true |
| Recall 数 | `consciousness.hindsight.recall_limit` | int | 5 |
| Reflect | `consciousness.hindsight.reflect_enabled` | bool | true |
| **天气** | | | |
| 启用 | `consciousness.weather.enabled` | bool | false |
| 城市编码 | `consciousness.weather.adcode` | string | 370100 |
| API Key | `consciousness.weather.amap_key` | string | |
| 缓存秒数 | `consciousness.weather.cache_ttl` | int | 600 |
| **注入** | | | |
| 最小间隔 | `consciousness.injection.min_silence_minutes` | int | 30 |
| **通知** | | | |
| 平台 | `consciousness.notify.platform` | string | weixin |
| Chat ID | `consciousness.notify.chat_id` | string | |

---

## 七、实施计划

### Phase 1：后端基础设施（2h）

1. 新建 `backend/models/consciousness.py` — ORM 模型
2. 新建 `backend/services/consciousness_service.py` — 核心服务
3. `backend/routers/config.py` — 追加配置 API

### Phase 2：前端配置卡片（2h）

4. `frontend/src/api/config.js` — 追加 API 调用
5. `frontend/src/views/Config.vue` — 追加配置卡片
6. 新建 `frontend/src/components/ConsciousnessConfig.vue` — 配置组件

### Phase 3：心跳引擎（3h）

7. `backend/services/scheduler_service.py` — 追加心跳任务
8. `backend/services/consciousness_service.py` — 追加想法生成逻辑

### Phase 4：hermes 插件（2h）

9. 新建 `~/.hermes/plugins/consciousness/__init__.py` — pre_llm_call 插件

### Phase 5：测试（1h）

10. 端到端测试

---

## 八、文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/models/consciousness.py` | **新建** | ORM 模型 |
| `backend/services/consciousness_service.py` | **新建** | 核心服务（想法生成、决策、发送） |
| `backend/services/weather_service.py` | **新建** | 天气感知 |
| `backend/routers/consciousness.py` | **新建** | API 端点 |
| `backend/routers/config.py` | 追加 | 配置 API |
| `frontend/src/components/ConsciousnessConfig.vue` | **新建** | 配置组件 |
| `frontend/src/api/config.js` | 追加 | API 调用 |
| `frontend/src/views/Config.vue` | 追加 | 引入配置组件 |
| `~/.hermes/plugins/consciousness/__init__.py` | **新建** | hermes 插件 |
