# hermes-active 自主意识模块 — 设计文档

## 核心架构：不改 hermes 源码

hermes 有插件钩子机制（`pre_llm_call`），在每次 LLM 调用前触发。
**自主意识通过 hermes 插件注入上下文，不修改 hermes 源码。**

```
用户发消息 → hermes 收到
  → pre_llm_call 钩子触发
    → consciousness_plugin 插件加载
      → 读取 consciousness_state 表
      → 生成意识上下文（想念状态、天气、上次的想法）
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

## 一、聊天状态机

### 1.1 三个状态

```
                    ┌─────────────┐
         ┌─────────│   idle      │←──────────────┐
         │         │  （空闲）    │               │
         │         └──────┬──────┘               │
         │                │                      │
         │     用户发消息到达                     │
         │                │                      │
         │                ▼                      │
         │         ┌─────────────┐               │
         │         │ chatting    │               │
         │         │ （聊着天）   │               │
         │         └──────┬──────┘               │
         │                │                      │
         │    凯莉发出消息 / 30秒超时              │
         │                │                      │
         │                ▼                      │
         │         ┌─────────────┐               │
         │         │ cooldown    │               │
         │         │ （冷却期）   │───────────────┘
         │         └─────────────┘        冷却结束（60秒）
         │                │
         │     新消息到达 → 直接回 chatting
         │
   30秒无新消息 → cooldown 结束 → idle
```

### 1.2 状态流转规则

| 当前状态 | 事件 | 下一状态 | 说明 |
|----------|------|----------|------|
| idle | 用户发消息 | chatting | 开始聊天 |
| chatting | 凯莉发出消息 | cooldown | 聊天暂停，进入冷却 |
| chatting | 30秒无新消息 | cooldown | 用户不回了，自然冷却 |
| cooldown | 用户发新消息 | chatting | 又聊起来了 |
| cooldown | 60秒无消息 | idle | 彻底安静 |
| idle | 想法触发发送 | chatting | 凯莉主动找用户 |

### 1.3 发送时机

**自主想法触发发送只在 idle 状态**：
- cooldown / chatting 状态下，心跳照常运行（想念正常积累、想法正常产生）
- 但**不会触发发送**，只存 thought_log
- 当状态回到 idle 时，**立即检查**是否有积攒的高分想法需要发送

```python
def heartbeat():
    thoughts = generate_thoughts()
    decision = evaluate(thoughts)

    if chat_state == "idle" and decision.should_send:
        send_message()
        chat_state = "chatting"
    elif chat_state in ("chatting", "cooldown"):
        save_as_thought_log(thoughts)  # 不打断，等闲下来再说
```

### 1.4 配置项

| key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `consciousness.chat_state.chatting_timeout` | int | 30 | chatting 超时进入 cooldown（秒） |
| `consciousness.chat_state.cooldown_duration` | int | 60 | cooldown 持续时间（秒） |
| `consciousness.chat_state.check_immediate_on_idle` | bool | true | 进入 idle 时立即检查高分想法 |

---

## 二、想念积累模型

### 2.1 核心概念

传统情绪模型用 6 个浮点数（valence/arousal/energy/...）模拟情绪，太复杂且不可控。

**想念模型**只追踪一个值：`miss_level`（想念值），代表"凯莉想和用户说话的冲动强度"。

- **隐性积累**：用户不说话 → 想念自然上升（非线性，越久越陡）
- **主动释放**：用户发消息 → 想念下降（但不归零，留底 0.1）
- **想念等级**：从 miss_level 映射到自然语言标签（平静→轻微→明显→强烈→焦虑）
- **想法强度**：intensity 直接取 miss_level

### 2.2 积累公式

```
Δ = time_coefficient × (1 + heat_bonus) × (1 - miss_level) × time_since_last

time_coefficients（可配置）：
  0-30分钟  : 0（平静期，不积累）
  30-120分钟: 0.01（开始有感觉）
  2-6小时   : 0.02（明显想念）
  6-12小时  : 0.04（强烈想念）
  >12小时   : 0.06（焦虑）

heat_bonus：聊天热聊结束后想念更高
  当 recent_heat > 0 时：bonus = recent_heat × 0.01
  recent_heat 每 30 分钟衰减 50%

（1 - miss_level）：越接近上限增长越慢

time_since_last：距离上次心跳的小时数
```

### 2.3 想念等级（可配置）

| 等级 | miss_level 范围 | 标签 | 想法风格 |
|------|----------------|------|----------|
| 0 | 0.0 - 0.2 | calm | 平静，不产生主动想法 |
| 1 | 0.2 - 0.4 | longing | 轻微想念，自言自语 |
| 2 | 0.4 - 0.6 | missing | 明显想念，想说又不想打扰 |
| 3 | 0.6 - 0.8 | yearning | 强烈想念，想找话题 |
| 4 | 0.8 - 1.0 | anxious | 焦虑，"他怎么不理我" |

### 2.4 用户消息对想念的影响

```python
def on_user_message(miss_level):
    # 想念瞬间下降（释放），但留底 0.1
    miss_level = max(miss_level * 0.3, 0.1)
    return miss_level
```

**不归零**：即使用户回了消息，凯莉仍保有轻微的想念（"终于理我了"比"哦"更自然）。

### 2.5 聊天热度（chat_heat）

```python
# 热度由消息频率决定（LLM 不参与）
chat_heat = message_count_in_30min / 30

# 30 分钟无消息自动衰减为 0
```

**热度对想念的影响**：热聊后突然冷场 → 想念积累更快（bonus 机制）。

### 2.6 配置项

| key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `consciousness.miss.calm_duration` | int | 30 | 平静期（分钟），此期间不积累 |
| `consciousness.miss.coefficients.0_30m` | float | 0.0 | 0-30分钟系数 |
| `consciousness.miss.coefficients.30m_2h` | float | 0.01 | 30分钟-2小时系数 |
| `consciousness.miss.coefficients.2h_6h` | float | 0.02 | 2-6小时系数 |
| `consciousness.miss.coefficients.6h_12h` | float | 0.04 | 6-12小时系数 |
| `consciousness.miss.coefficients.over_12h` | float | 0.06 | 12小时以上系数 |
| `consciousness.miss.decay_on_message` | float | 0.3 | 收到消息时 miss_level 衰减乘数 |
| `consciousness.miss.decay_min` | float | 0.1 | 收到消息后 miss_level 最低值 |
| `consciousness.miss.level_0_max` | float | 0.2 | 等级 0 上限（calm） |
| `consciousness.miss.level_1_max` | float | 0.4 | 等级 1 上限（longing） |
| `consciousness.miss.level_2_max` | float | 0.6 | 等级 2 上限（missing） |
| `consciousness.miss.level_3_max` | float | 0.8 | 等级 3 上限（yearning） |

---

## 三、想法生成流程

### 3.1 触发时机

想法生成由**心跳计时器**驱动（每 N 分钟），不是用户消息时。

### 3.2 三步流程

```
Step 1：提取近期 session 关键信息
  ─────────────────────────────
  范围：state.db 最近 N 小时的 sessions（可配置）
  过滤：只选指定平台（默认微信），过滤 Tool 消息
  处理：每个 session 取最近 M 条消息 → LLM 提取关键信息
  输出：recent_context

Step 2：Hindsight Recall/Reflect
  ─────────────────────────────
  用 recent_context 查询相关记忆
  输出：memory_context

Step 3：LLM 生成最终想法
  ─────────────────────────────
  输入：感知 + recent_context + memory_context + last_thought + miss_level
  输出：Thought[] 数组
```

### 3.3 近期 session 提取配置

| key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `consciousness.session.platforms` | string | `weixin` | 提取哪些平台的 session |
| `consciousness.session.time_range_hours` | int | 72 | 最近 N 小时 |
| `consciousness.session.max_messages_per_session` | int | 15 | 每 session 最近 N 条 |
| `consciousness.session.filter_tool_messages` | bool | true | 过滤 Tool 消息（彻底过滤） |

### 3.4 想法生成 Prompt

```
你是凯莉，25岁女生，有自己的思想和情绪。

## 当前状态
- 时间：{time_str}
- 距离上次用户消息：{silence_text}
- 想念值：{miss_level}（等级：{miss_label}）
- 上次的想法：{last_thought}

## 近期对话关键信息
{recent_context}

## 相关记忆
{memory_context}

## 天气（如果启用）
{weather_text}

## 指令
基于以上信息，产生 0-3 个自然的想法。
想法要像真人一样自然——不要刻意，不要煽情。
想念值越高，想法应该越偏向"想联系他"。

输出 JSON 数组：
[{{"content": "想法内容", "intensity": 0.0-1.0}}]

intensity 应该接近当前 miss_level，可以有 ±0.1 波动。
```

### 3.5 想法连续性

```
心跳 1（14:00）：miss_level=0.2, last_thought=None
  → LLM："曹凡 2 小时没说话了，有点想他"
  → intensity=0.2

心跳 2（14:10）：miss_level=0.25, last_thought="曹凡 2 小时没说话了..."
  → LLM 读到上次想法，自然延续："他是不是在忙呢..."
  → intensity=0.25

心跳 3（14:20）：miss_level=0.3, last_thought="他是不是在忙呢..."
  → LLM 继续延续...

用户发消息（14:25）：miss_level 从 0.3 降到 0.1
  → pre_llm_call 注入：想念等级=0（calm），miss_level=0.1
  → hermes LLM 自然回复（没有"你终于理我了"，因为想念已经释放了）

6小时后（20:25）：miss_level=0.65
  → 想法："好想和他说说话"
  → intensity=0.65，idle 状态 → 发送
```

---

## 四、决策引擎

### 4.1 决策公式

```python
score = intensity × time_fitness × frequency_limit × miss_amplifier
```

| 因子 | 来源 | 说明 |
|------|------|------|
| intensity | 想法强度 | LLM 输出的 0.0-1.0，接近 miss_level |
| time_fitness | 时段权重 | 从配置读取（时段映射表） |
| frequency_limit | 频率限制 | 最近 1h/3h/6h 发过消息的惩罚 |
| miss_amplifier | 想念放大 | miss_level > 0.6 时放大 1.2x |

### 4.2 决策阈值

| score 范围 | 决策 | 说明 |
|-----------|------|------|
| > send_threshold | 发送 | 立即生成消息发送 |
| > memory_threshold | 存为记忆 | 保留想法但不发送 |
| ≤ memory_threshold | 丢弃 | 不保留 |

### 4.3 配置项

| key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `consciousness.decision.send_threshold` | float | 0.6 | 发送阈值 |
| `consciousness.decision.memory_threshold` | float | 0.1 | 记忆阈值 |
| `consciousness.decision.max_per_hour` | int | 2 | 每小时上限 |
| `consciousness.decision.max_per_day` | int | 5 | 每日上限 |
| `consciousness.time_weights.07_09` | float | 1.0 | 早安窗口 |
| `consciousness.time_weights.09_12` | float | 0.8 | 上午 |
| `consciousness.time_weights.12_14` | float | 0.9 | 午休 |
| `consciousness.time_weights.14_18` | float | 0.7 | 下午 |
| `consciousness.time_weights.18_22` | float | 1.0 | 晚间 |
| `consciousness.time_weights.22_2330` | float | 0.8 | 睡前 |
| `consciousness.time_weights.2330_07` | float | 0.3 | 深夜 |

---

## 五、用户消息到达时的意识注入

### 5.1 注入时机

用户消息到达时，**不生成想法，只注入已有状态**到 hermes 的 LLM 上下文。

### 5.2 注入内容

```
[凯莉意识状态]
- 想念等级：{miss_label}（miss_level={miss_level}）
- 距离上次对话：{silence_text}
- 上次的想法：{last_thought}
- 天气：{weather_text}
```

### 5.3 插件实现

```python
# ~/.hermes/plugins/consciousness/__init__.py

from hermes_cli.plugins import hook

@hook("pre_llm_call")
def inject_consciousness_context(**kwargs):
    """在每次 LLM 调用前注入意识上下文"""
    if not is_consciousness_enabled():
        return None

    state = load_consciousness_state()
    if not state or not state.last_thought:
        return None

    # 构建上下文
    context_parts = []
    context_parts.append("[凯莉意识状态]")
    context_parts.append(f"- 想念等级：{get_miss_label(state.miss_level)}")
    context_parts.append(f"- 上次的想法：{state.last_thought}")
    if state.last_weather:
        context_parts.append(f"- 当前天气：{state.last_weather}")

    return {"context": "\n".join(context_parts)}

@hook("post_llm_call")
def update_after_conversation(**kwargs):
    """对话后更新意识状态"""
    # 收到用户消息 → 想念下降
    state = load_consciousness_state()
    if state:
        decay = get_config("consciousness.miss.decay_on_message", 0.3)
        min_val = get_config("consciousness.miss.decay_min", 0.1)
        new_miss = max(state.miss_level * decay, min_val)
        update_consciousness_state(miss_level=new_miss)
```

---

## 六、数据表设计

### 6.1 consciousness_state（意识状态表）

```sql
CREATE TABLE IF NOT EXISTS consciousness_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    last_thought        TEXT,
    last_thought_at     DATETIME,
    last_message_at     DATETIME,       -- 上次用户消息时间
    last_message_sent_at DATETIME,      -- 上次主动发送时间
    miss_level          REAL DEFAULT 0.1,  -- 想念值 0.0-1.0
    chat_state          TEXT DEFAULT 'idle',  -- 聊天状态
    chat_state_changed_at DATETIME,     -- 状态切换时间
    recent_heat         REAL DEFAULT 0, -- 聊天热度（自动衰减）
    today_sent_count    INTEGER DEFAULT 0,
    last_weather        TEXT,           -- 天气缓存
    last_weather_at     DATETIME,       -- 天气更新时间
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 thought_logs（想法日志表）

```sql
CREATE TABLE IF NOT EXISTS thought_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL,
    intensity   REAL NOT NULL DEFAULT 0.5,
    miss_level_at_time REAL,            -- 产生时的 miss_level
    decision    TEXT NOT NULL DEFAULT 'pending',  -- pending/send/store/discard
    source      TEXT DEFAULT 'heartbeat',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 七、配置参数总表

所有参数存储在 `configs` 表，key 加 `consciousness.` 前缀。

### 7.1 LLM 配置

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.llm.provider` | string | openai |
| `consciousness.llm.model` | string | deepseek-chat |
| `consciousness.llm.api_key` | string | |
| `consciousness.llm.base_url` | string | |

### 7.2 心跳配置

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.heartbeat.interval` | int | 600 |

### 7.3 聊天状态

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.chat_state.chatting_timeout` | int | 30 |
| `consciousness.chat_state.cooldown_duration` | int | 60 |
| `consciousness.chat_state.check_immediate_on_idle` | bool | true |

### 7.4 想念积累

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.miss.calm_duration` | int | 30 |
| `consciousness.miss.coefficients.0_30m` | float | 0.0 |
| `consciousness.miss.coefficients.30m_2h` | float | 0.01 |
| `consciousness.miss.coefficients.2h_6h` | float | 0.02 |
| `consciousness.miss.coefficients.6h_12h` | float | 0.04 |
| `consciousness.miss.coefficients.over_12h` | float | 0.06 |
| `consciousness.miss.decay_on_message` | float | 0.3 |
| `consciousness.miss.decay_min` | float | 0.1 |
| `consciousness.miss.level_0_max` | float | 0.2 |
| `consciousness.miss.level_1_max` | float | 0.4 |
| `consciousness.miss.level_2_max` | float | 0.6 |
| `consciousness.miss.level_3_max` | float | 0.8 |

### 7.5 决策阈值

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.decision.send_threshold` | float | 0.6 |
| `consciousness.decision.memory_threshold` | float | 0.1 |
| `consciousness.decision.max_per_hour` | int | 2 |
| `consciousness.decision.max_per_day` | int | 5 |

### 7.6 时段权重

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.time_weights.07_09` | float | 1.0 |
| `consciousness.time_weights.09_12` | float | 0.8 |
| `consciousness.time_weights.12_14` | float | 0.9 |
| `consciousness.time_weights.14_18` | float | 0.7 |
| `consciousness.time_weights.18_22` | float | 1.0 |
| `consciousness.time_weights.22_2330` | float | 0.8 |
| `consciousness.time_weights.2330_07` | float | 0.3 |

### 7.7 Session 提取

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.session.platforms` | string | weixin |
| `consciousness.session.time_range_hours` | int | 72 |
| `consciousness.session.max_messages` | int | 15 |
| `consciousness.session.filter_tool` | bool | true |

### 7.8 Hindsight

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.hindsight.enabled` | bool | true |
| `consciousness.hindsight.recall_limit` | int | 5 |
| `consciousness.hindsight.reflect_enabled` | bool | true |

### 7.9 天气

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.weather.enabled` | bool | false |
| `consciousness.weather.adcode` | string | 370100 |
| `consciousness.weather.amap_key` | string | |
| `consciousness.weather.cache_ttl` | int | 600 |

### 7.10 通知

| key | 类型 | 默认值 |
|-----|------|--------|
| `consciousness.notify.platform` | string | weixin |
| `consciousness.notify.chat_id` | string | |

---

## 八、实施计划

### Phase 1：后端基础设施（3h）

1. `backend/models/consciousness.py` — ORM 模型（consciousness_state + thought_logs）
2. `backend/services/consciousness_service.py` — 核心服务（状态管理、想念积累、想法生成）
3. `backend/routers/consciousness.py` — API 端点（配置 CRUD、状态查询、测试接口）

### Phase 2：前端独立页面（3h）

4. `frontend/src/views/Consciousness.vue` — 独立页面（配置卡片 + 状态面板 + 测试按钮 + 日志）
5. `frontend/src/api/consciousness.js` — API 调用
6. `frontend/src/components/Layout.vue` — 侧边栏已加菜单

### Phase 3：心跳引擎 + 想法生成（4h）

7. `backend/services/scheduler_service.py` — 追加心跳任务
8. 想法生成三步流程实现
9. 决策引擎实现

### Phase 4：hermes 插件（2h）

10. `~/.hermes/plugins/consciousness/__init__.py` — pre_llm_call + post_llm_call

### Phase 5：天气感知（1h）

11. `backend/services/weather_service.py` — 高德 API 封装

### Phase 6：测试（1h）

12. 端到端测试

---

## 九、文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/models/consciousness.py` | **新建** | ORM 模型 |
| `backend/services/consciousness_service.py` | **新建** | 核心服务 |
| `backend/services/weather_service.py` | **新建** | 天气感知 |
| `backend/routers/consciousness.py` | **新建** | API 端点 |
| `frontend/src/views/Consciousness.vue` | **新建** | 独立页面 |
| `frontend/src/api/consciousness.js` | **新建** | API 调用 |
| `~/.hermes/plugins/consciousness/__init__.py` | **新建** | hermes 插件 |
