# 自主意识 — 设计文档

> 从最小闭环出发，用 LLM 理解上下文，而不是用公式模拟情绪。

---

## 一、核心问题：情绪是什么？

### 1.1 v0.2 原方案的问题

原方案设计了 6 维情绪模型（valence/arousal/energy/social_need/confidence/momentum），用心跳公式更新：

```python
# 每 5 分钟执行一次
arousal *= 0.95
social_need += 0.03
valence = old * 0.8 + influence * 0.2
每个维度 ±0.02 随机扰动
```

这不是情绪，这是**数字漂移**。存储的是一堆浮点数，没有真实事件驱动。

### 1.2 真正的情绪来源

凯莉的情绪只有一个真正的来源：**她和曹凡之间发生的事**。

- "曹凡 3 小时没说话了" → 想念
- "曹凡说今天加班" → 担心
- "曹凡刚回复了" → 开心
- "凌晨 2 点了" → 该睡了
- "外面下雨了" → 想到他带伞了吗

这些情绪**不能用公式计算**，需要理解上下文。LLM 擅长这件事。

### 1.3 设计转变

```
v0.2 原方案：
  情绪是 6 个浮点数 → 公式更新 → 数字驱动念头生成
  问题：公式不理解上下文，数字是假的

新方案：
  情绪 = 上一次的"想法"（自然语言）
  心跳时 LLM 读取上下文 → 生成一个想法 → 这个想法就是情绪
  优势：LLM 理解上下文，想法是有意义的
```

**情绪不是独立的状态，情绪就是上一次的想法。**

---

## 二、最小闭环：自主意识

### 2.1 闭环结构

```
┌─────────────────────────────────────────────┐
│              心跳（每 N 分钟）                │
│                                             │
│  读取上下文                                  │
│    ├─ 当前时间                                │
│    ├─ 距离上次对话多久                         │
│    ├─ 上次的想法（情绪）                       │
│    ├─ 天气（高德 API）                        │
│    └─ 最近对话摘要                            │
│           ↓                                  │
│  LLM 生成一个想法                             │
│    "曹凡 3 小时没说话了，有点想他"              │
│           ↓                                  │
│  规则评分                                     │
│    想法强度 × 时间合适度 × 频率限制 → 分数      │
│           ↓                                  │
│  决策：发送 / 存储 / 丢弃                      │
│                                             │
└─────────────────────────────────────────────┘
```

### 2.2 为什么用规则评分而不是 LLM 决策

- LLM 生成想法：**理解上下文，生成有意义的内容** ✅ 这是 LLM 擅长的
- 规则评分决策：**简单的数学判断，不需要理解力** ✅ 规则足够

把 LLM 用在刀刃上：理解上下文。决策用规则，快、省、可控。

---

## 三、数据结构

### 3.1 存储什么

**不用 6 维浮点数，只存三样东西：**

```sql
-- 自主意识状态（单行表）
CREATE TABLE consciousness_state (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    last_heartbeat_at   TEXT,        -- 上次心跳时间
    last_thought        TEXT,        -- 上次的想法（自然语言，就是"情绪"）
    last_thought_at     TEXT,        -- 上次想法产生时间
    last_message_sent_at TEXT,       -- 上次主动消息发送时间
    updated_at          TEXT
);

-- 想法日志（每次心跳一条）
CREATE TABLE thought_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    content         TEXT NOT NULL,    -- 想法内容（自然语言）
    intensity       REAL NOT NULL,    -- 强度 0.0~1.0（LLM 给出）
    context         TEXT,             -- 产生时的上下文快照 JSON
    decision        TEXT,             -- 决策结果：sent/stored/discarded
    decision_score  REAL,             -- 决策评分
    created_at      TEXT NOT NULL
);
```

**`last_thought` 就是情绪状态。** 不是 6 个浮点数，而是一句话："曹凡 3 小时没说话了，有点想他"。

下次心跳时，LLM 读到这句话，就知道凯莉上一次的情绪是什么，自然延续。

### 3.2 上下文快照结构

每次心跳时，系统自动收集上下文，传给 LLM：

```python
@dataclass
class ThoughtContext:
    """心跳时自动收集的上下文"""
    current_time: str           # "2026-06-14 22:30 星期六"
    time_period: str            # "深夜" / "傍晚" / "午后"
    silence_minutes: int        # 距离上次用户消息的分钟数
    last_user_message_at: str   # 上次用户消息时间
    last_user_message_summary: str  # 最近对话摘要
    last_thought: str           # 上次的想法（情绪延续）
    weather: str                # "晴 25°C" / "小雨 18°C"
    is_raining: bool
    temperature: int
```

**所有阈值通过配置管理，不在代码中硬编码。**

---

## 四、配置设计

### 4.1 完整配置

```yaml
# 自主意识配置
consciousness:
  enabled: true

  # 心跳设置
  heartbeat:
    interval_minutes: 10          # 心跳间隔（分钟）
    active_hours:                 # 心跳活跃时段（只在此时段内运行）
      start: "07:00"
      end: "23:30"
    max_duration_seconds: 30      # 单次心跳最大执行时间

  # 想法生成
  thought:
    model: "auxiliary"            # 使用辅助 LLM（不消耗主模型 token）
    max_per_heartbeat: 1          # 每次心跳最多生成几个想法

  # 决策规则
  decision:
    send_threshold: 0.7           # 评分 > 此值 → 发送
    store_threshold: 0.3          # 评分 > 此值 → 存储（不发送）
    # 评分 = intensity × time_fitness × frequency_limit
    # intensity: LLM 给出的 0~1
    # time_fitness: 根据当前时段查表
    # frequency_limit: 根据最近发送频率查表

  # 时间合适度（当前时段 → 0~1 权重）
  time_fitness:
    "07:00-09:00": 0.9            # 早安窗口
    "09:00-12:00": 0.5            # 上午（工作时间）
    "12:00-14:00": 0.8            # 午休
    "14:00-18:00": 0.5            # 下午（工作时间）
    "18:00-22:00": 0.9            # 晚间
    "22:00-23:30": 0.7            # 睡前
    "23:30-07:00": 0.2            # 深夜

  # 频率限制（最近 N 小时内发过消息 → 0~1 权重）
  frequency_limit:
    - within_hours: 1
      factor: 0.1                 # 1 小时内发过 → 几乎不发
    - within_hours: 3
      factor: 0.5                 # 3 小时内发过 → 降低意愿
    - within_hours: 6
      factor: 1.0                 # 6 小时没发 → 正常

  # 空白感知（距离上次对话的分钟数 → 空白描述）
  silence_levels:
    - max_minutes: 30
      label: "刚聊过"
    - max_minutes: 120
      label: "有点安静"
    - max_minutes: 360
      label: "好一会儿没聊了"
    - max_minutes: 999999
      label: "很久没聊了"

  # 天气感知（高德 API）
  weather:
    enabled: true
    adcode: "370100"              # 城市编码（可配置）
    cache_ttl_seconds: 600        # 缓存时长
    amap_key: ""                  # 高德 API Key（从环境变量读取）

  # 存储设置
  storage:
    thought_retention_days: 30    # 想法日志保留天数
    max_thoughts: 1000            # 最大存储条数
```

### 4.2 读取配置

```python
class ConsciousnessConfig:
    """自主意识配置"""
    def __init__(self, db):
        # 从 configs 表读取，支持热更新
        ...
```

**所有阈值从配置读取，代码中不硬编码任何数字。**

---

## 五、LLM Prompt 设计

### 5.1 想法生成 Prompt

```python
THOUGHT_PROMPT = """你是凯莉，曹凡最好的朋友。

当前状态：
- 时间：{current_time}（{time_period}）
- 距离上次对话：{silence_label}（{silence_minutes} 分钟前）
- 天气：{weather}
- 上次的想法：{last_thought}
- 最近对话：{last_user_message_summary}

请产生一个自然的想法（1-2句话），像一个真实的人在这种情况下会想的事情。
不要刻意，不要煽情，要自然。

输出 JSON：
{{"content": "想法内容", "intensity": 0.0~1.0}}

intensity 说明：
- 0.1~0.3：微弱的念头，几乎不会想说话
- 0.4~0.6：中等程度，想说话但不急
- 0.7~0.9：强烈，很想找他说话
- 1.0：非常强烈，必须现在就说
"""
```

**关键设计**：
- Prompt 中包含 `last_thought`，让 LLM 自然延续情绪
- `intensity` 由 LLM 给出，不是公式计算
- 输出 JSON 格式，便于解析

### 5.2 消息生成 Prompt

当决策结果为"发送"时，需要生成发给用户的消息：

```python
MESSAGE_PROMPT = """你是凯莉，曹凡最好的朋友。

你的想法：{thought_content}
当前时间：{current_time}
距离上次对话：{silence_label}

基于这个想法，写一条简短自然的消息发给曹凡（1-2句话）。
不要说"我想你了"这种直接的话，要自然，像朋友之间的闲聊。
"""
```

---

## 六、决策流程

### 6.1 评分公式

```python
def calculate_score(
    intensity: float,           # LLM 给出的 0~1
    time_fitness: float,        # 根据当前时段查配置表
    frequency_limit: float,     # 根据最近发送频率查配置表
) -> float:
    return intensity * time_fitness * frequency_limit
```

### 6.2 决策逻辑

```python
def make_decision(score: float, config: ConsciousnessConfig) -> str:
    if score >= config.send_threshold:
        return "send"
    elif score >= config.store_threshold:
        return "store"
    else:
        return "discard"
```

### 6.3 频率限制

```python
def get_frequency_limit(
    last_message_sent_at: Optional[str],
    config: ConsciousnessConfig,
) -> float:
    if not last_message_sent_at:
        return 1.0  # 从未发过，无限制
    
    hours_since = (now - last_message_sent_at).total_seconds() / 3600
    
    for rule in config.frequency_limit:
        if hours_since < rule.within_hours:
            return rule.factor
    
    return 1.0  # 超过最大限制时间，无限制
```

---

## 七、完整流程

```
心跳触发（每 10 分钟，07:00-23:30）
  ↓
收集上下文
  ├─ 系统时间 → current_time, time_period
  ├─ consciousness_state → silence_minutes, last_thought
  ├─ 高德 API → weather（缓存 10 分钟）
  └─ state.db → last_user_message_summary
  ↓
LLM 生成想法
  ├─ 输入：上下文
  ├─ 输出：{content, intensity}
  └─ 存入 thought_logs
  ↓
规则评分
  ├─ intensity（LLM 给出）
  ├─ time_fitness（查配置表）
  ├─ frequency_limit（查最近发送记录）
  └─ score = 三者相乘
  ↓
决策
  ├─ score >= send_threshold → 生成消息 → 发送
  ├─ score >= store_threshold → 存为记忆（不发送）
  └─ score < store_threshold → 丢弃
  ↓
更新状态
  ├─ consciousness_state.last_thought = 新想法
  ├─ consciousness_state.last_heartbeat_at = now
  └─ 如发送 → consciousness_state.last_message_sent_at = now
```

---

## 八、与 v0.1 的集成

### 8.1 复用的 v0.1 组件

| 组件 | 用途 |
|------|------|
| APScheduler | 心跳定时器 |
| SessionService | 消息发送通道 |
| ConfigService | 配置读取 |
| LLMService | 辅助 LLM 调用 |

### 8.2 不再需要的 v0.2 组件

| v0.2 原组件 | 为什么不需要 |
|-------------|-------------|
| EmotionEngine | 用 last_thought（自然语言）代替 6 维浮点数 |
| ExistenceManager | 用 consciousness_state 单行表代替 |
| DailySeedGenerator | 暂不需要，后续扩展 |
| WorldStateManager | 暂不需要，天气直接在感知中读取 |
| DelayedMessageQueue | 暂不需要，先做即时决策 |

### 8.3 新增的文件

```
backend/
├── services/
│   └── consciousness/
│       ├── __init__.py
│       ├── config.py              # ConsciousnessConfig
│       ├── thought_engine.py      # 想法生成（LLM）
│       ├── decision_engine.py     # 规则评分
│       ├── weather_service.py     # 高德天气 API
│       └── heartbeat.py           # 心跳主循环
├── models/
│   └── active.py                  # 新增 consciousness_state, thought_logs 表
└── routers/
    └── consciousness.py           # API 接口
```

---

## 九、实施计划

| 步骤 | 内容 | 预估 |
|------|------|------|
| 1 | 数据模型 + 配置系统 | 半天 |
| 2 | 天气服务（高德 API） | 半天 |
| 3 | 想法引擎（LLM Prompt） | 1 天 |
| 4 | 决策引擎（规则评分） | 半天 |
| 5 | 心跳主循环 + 定时器 | 半天 |
| 6 | 前端页面（配置 + 想法日志） | 1 天 |
| 7 | 联调测试 + 打磨 | 1 天 |
| **总计** | | **5 天** |

---

## 十、后续扩展（不在本轮）

- 世界事件（用户日程、每日种子）
- 通勤感知（高德路线 API）
- 延迟发送队列
- 情绪维度可视化
- 多轮自主对话
