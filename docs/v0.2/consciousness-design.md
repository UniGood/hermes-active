# 自主意识 — 设计文档

> 让凯莉从"闹钟式存在"变为"持续存在"
> 
> 一个闭环：**心跳感知 → 念头 → 决策 → 行动**

---

## 一、这是什么

当前的凯莉：闹钟响了 → 醒来 → 说话 → 消失

自主意识：一直在运行 → 感知环境 → 产生想法 → 决定要不要说话

**核心闭环只有 4 步**：

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   心跳（每 N 分钟）                              │
│      ↓                                          │
│   感知：现在几点？他多久没说话了？天气怎样？       │
│      ↓                                          │
│   念头：基于感知产生 1-2 个想法                   │
│      ↓                                          │
│   决策：这个想法值得发消息吗？                    │
│      ├── 值得 → 发送消息                         │
│      ├── 不太值得 → 存为记忆                     │
│      └── 不值得 → 忽略                           │
│      ↓                                          │
│   回到心跳                                       │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 二、功能菜单

在 hermes-active 的 Web 管理页面新增「自主意识」菜单，包含：

### 2.1 总开关

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| enabled | 是否启用自主意识 | false |
| heartbeat_interval_seconds | 心跳间隔（秒） | 300（5分钟） |

### 2.2 感知配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| weather_enabled | 是否启用天气感知 | true |
| weather_adcode | 高德天气城市编码 | "370100"（济南） |
| weather_cache_ttl | 天气缓存时长（秒） | 600 |
| amap_key | 高德 API Key | "" |

### 2.3 念头配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| thought_silence_enabled | 是否产生"空白想念"类念头 | true |
| thought_weather_enabled | 是否产生天气相关念头 | true |
| thought_max_per_heartbeat | 每次心跳最多产生几个念头 | 2 |
| thought_intensity_base | 念头基础强度 | 0.4 |

### 2.4 决策配置（所有阈值可调）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| score_threshold_send | 立即发送阈值 | 0.6 |
| score_threshold_delay | 延迟发送阈值 | 0.3 |
| score_threshold_memory | 存为记忆阈值 | 0.1 |
| delay_window_minutes | 延迟发送等待窗口（分钟） | 60 |
| max_messages_per_hour | 每小时最多发几条主动消息 | 2 |
| max_messages_per_day | 每天最多发几条主动消息 | 8 |

### 2.5 时间窗口配置

每个时段的「合适度」可调：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| time_fitness_morning | 07:00-09:00 合适度 | 1.0 |
| time_fitness_work_am | 09:00-12:00 合适度 | 0.8 |
| time_fitness_noon | 12:00-14:00 合适度 | 0.9 |
| time_fitness_work_pm | 14:00-18:00 合适度 | 0.7 |
| time_fitness_evening | 18:00-22:00 合适度 | 1.0 |
| time_fitness_late | 22:00-23:30 合适度 | 0.8 |
| time_fitness_night | 23:30-07:00 合适度 | 0.3 |

### 2.6 空白阶段配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| silence_phase_1_minutes | 进入"轻微想念"的分钟数 | 30 |
| silence_phase_2_minutes | 进入"明显想念"的分钟数 | 120 |
| silence_phase_3_minutes | 进入"强烈想念"的分钟数 | 360 |
| silence_phase_4_minutes | 进入"担心"的分钟数 | 720 |

### 2.7 天气念头规则

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| weather_thought_rain_intensity | 下雨念头强度 | 0.5 |
| weather_thought_snow_intensity | 下雪念头强度 | 0.6 |
| weather_thought_cold_threshold | 寒冷触发温度（°C） | 5 |
| weather_thought_hot_threshold | 炎热触发温度（°C） | 35 |
| weather_thought_fog_intensity | 雾霾念头强度 | 0.4 |

---

## 三、数据流

```
┌──────────────────────────────────────────────────────────────┐
│                    hermes-active                              │
│                                                              │
│  ┌─────────────────┐                                        │
│  │  Web 管理页面    │                                        │
│  │  「自主意识」菜单 │ ← 用户在这里配置所有参数               │
│  └────────┬────────┘                                        │
│           │ 配置写入 configs 表                               │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              心跳引擎（APScheduler 驱动）             │    │
│  │                                                     │    │
│  │  每 N 分钟执行一次：                                  │    │
│  │                                                     │    │
│  │  1. 读取配置（configs 表）                           │    │
│  │  2. 感知                                             │    │
│  │     ├─ 读 existence_state → 空白时长                 │    │
│  │     ├─ 读 emotion_states → 当前情绪                  │    │
│  │     └─ 调高德天气 API → 天气状况                      │    │
│  │  3. 产生念头                                         │    │
│  │     ├─ 空白念头："好久没说话了"                       │    │
│  │     └─ 天气念头："外面下雨了"                         │    │
│  │  4. 决策                                             │    │
│  │     ├─ 计算分数 = 强度 × 时间合适度 × 频率限制       │    │
│  │     └─ 分数 > 阈值 → 发送                            │    │
│  │  5. 发送消息（如果决策是发送）                        │    │
│  │     └─ 调 MessageService → 写入 session              │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  数据存储：                                                  │
│  ├─ configs 表：所有配置项                                   │
│  ├─ active.db：心跳日志、念头日志                            │
│  └─ state.db：消息写入（通过 MessageService）                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 四、模块拆分

### 4.1 后端模块

```
backend/
├── services/
│   └── consciousness/
│       ├── __init__.py
│       ├── heartbeat.py          # 心跳引擎（主循环）
│       ├── perception.py         # 感知处理（空白 + 天气）
│       ├── thought.py            # 念头生成（规则模板）
│       ├── decision.py           # 决策引擎（评分 + 阈值）
│       └── config_provider.py    # 配置读取（从 configs 表）
├── routers/
│   └── consciousness.py          # API：CRUD 配置 + 手动触发心跳
└── models/
    └── consciousness.py          # 数据模型（心跳日志、念头日志）
```

### 4.2 前端页面

```
frontend/src/views/
└── Consciousness.vue             # 「自主意识」管理页面
```

---

## 五、核心流程（伪代码）

### 5.1 心跳引擎

```python
async def heartbeat():
    """每次心跳执行一次"""
    config = ConfigProvider.get_consciousness_config()
    
    if not config.enabled:
        return
    
    # 1. 感知
    perception = await PerceptionProcessor.process(config)
    # perception 包含：
    #   - silence_minutes: int（空白时长）
    #   - silence_phase: str（空白阶段）
    #   - time_period: str（当前时段）
    #   - weather: dict | None（天气状况）
    
    # 2. 产生念头
    thoughts = ThoughtGenerator.generate(perception, config)
    # thoughts = [
    #   {"type": "silence", "content": "...", "intensity": 0.6},
    #   {"type": "weather", "content": "...", "intensity": 0.5},
    # ]
    
    # 3. 决策
    decisions = DecisionEngine.evaluate(thoughts, perception, config)
    # decisions = [
    #   {"thought": ..., "action": "send_now", "score": 0.72},
    #   {"thought": ..., "action": "store_as_memory", "score": 0.15},
    # ]
    
    # 4. 执行
    for decision in decisions:
        if decision.action == "send_now":
            await ActionExecutor.send_message(decision, config)
        elif decision.action == "store_as_memory":
            await ActionExecutor.store_memory(decision)
        # discard → 什么都不做
    
    # 5. 记录心跳日志
    await save_heartbeat_log(perception, thoughts, decisions)
```

### 5.2 决策评分

```python
def evaluate(thoughts, perception, config) -> list[Decision]:
    results = []
    
    for thought in thoughts:
        # 获取当前时段的时间合适度
        time_fitness = get_time_fitness(perception.time_period, config)
        
        # 获取频率限制
        recent_count = get_recent_message_count(hours=1)
        if recent_count >= config.max_messages_per_hour:
            frequency_limit = 0.1  # 已达上限，几乎不发
        else:
            frequency_limit = 1.0
        
        # 综合评分
        score = thought["intensity"] * time_fitness * frequency_limit
        
        # 决策
        if score >= config.score_threshold_send:
            action = "send_now"
        elif score >= config.score_threshold_delay:
            action = "send_delayed"
        elif score >= config.score_threshold_memory:
            action = "store_as_memory"
        else:
            action = "discard"
        
        results.append(Decision(thought=thought, action=action, score=score))
    
    return results
```

### 5.3 念头生成（规则模板，不调 LLM）

```python
def generate(perception, config) -> list[Thought]:
    thoughts = []
    
    # 空白念头
    if config.thought_silence_enabled:
        if perception.silence_phase == "longing":
            thoughts.append({
                "type": "silence",
                "content": "好久没说话了，有点想他",
                "intensity": 0.6,
            })
        elif perception.silence_phase == "concerned":
            thoughts.append({
                "type": "silence",
                "content": "很久没联系了，他还好吗",
                "intensity": 0.8,
            })
    
    # 天气念头
    if config.thought_weather_enabled and perception.weather:
        w = perception.weather
        if w.is_raining:
            thoughts.append({
                "type": "weather",
                "content": "外面下雨了",
                "intensity": config.weather_thought_rain_intensity,
            })
        if w.is_cold:
            thoughts.append({
                "type": "weather",
                "content": "今天好冷",
                "intensity": 0.4,
            })
    
    # 限制数量
    thoughts.sort(key=lambda t: t["intensity"], reverse=True)
    return thoughts[:config.thought_max_per_heartbeat]
```

---

## 六、配置存储

所有配置存在 `configs` 表，key 格式为 `consciousness.*`：

```sql
INSERT INTO configs (key, value) VALUES
('consciousness.enabled', 'false'),
('consciousness.heartbeat_interval_seconds', '300'),
('consciousness.weather_enabled', 'true'),
('consciousness.weather_adcode', '370100'),
('consciousness.score_threshold_send', '0.6'),
('consciousness.max_messages_per_hour', '2'),
('consciousness.time_fitness_morning', '1.0'),
('consciousness.time_fitness_night', '0.3'),
('consciousness.silence_phase_2_minutes', '120'),
-- ... 其他配置项
```

前端通过 `GET/PUT /api/config/consciousness` 读写。

---

## 七、API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/consciousness/config` | 获取所有自主意识配置 |
| PUT | `/api/consciousness/config` | 更新配置 |
| POST | `/api/consciousness/heartbeat` | 手动触发一次心跳（调试用） |
| GET | `/api/consciousness/logs` | 查看心跳日志 |
| GET | `/api/consciousness/status` | 查看当前状态（空白时长、情绪、最近念头） |

---

## 八、消息生成

当决策结果是 `send_now` 时，需要生成消息内容。

**方式：规则模板（不调 LLM，节省 token）**

```python
def generate_message(thought, perception, config) -> str:
    """根据念头类型选择消息模板"""
    
    templates = {
        "silence": {
            "longing": [
                "想你了，在忙什么呢",
                "好久没说话了，你还好吗",
            ],
            "concerned": [
                "很久没联系了，一切都好吗",
            ],
        },
        "weather": {
            "rain": [
                "外面下雨了，出门记得带伞",
                "下雨天路滑，小心点",
            ],
            "cold": [
                "今天好冷，多穿点",
                "降温了，注意保暖",
            ],
            "hot": [
                "今天好热，多喝水",
                "天热注意防暑",
            ],
            "snow": [
                "下雪了！好美",
                "雪天路滑，出门小心",
            ],
        },
    }
    
    category = templates.get(thought["type"], {})
    options = category.get(thought.get("subtype", ""), ["想你了"])
    return random.choice(options)
```

**后续可扩展**：接入 LLM 生成更自然的消息，但 v1 用模板就够了。

---

## 九、与现有系统的关系

| 现有组件 | 自主意识如何使用 |
|----------|----------------|
| APScheduler | 心跳引擎的驱动器 |
| configs 表 | 存储所有配置项 |
| existence_state 表 | 读取空白时长 |
| emotion_states 表 | 读取当前情绪 |
| MessageService | 发送主动消息 |
| state.db sessions 表 | 读取活跃 session |
| 前端 Vue + Naive UI | 「自主意识」管理页面 |

**不新增任何表**。心跳日志和念头日志可以先用 task_logs 表记录，后续需要再独立建表。

---

## 十、实施顺序

| 步骤 | 内容 | 预计时间 |
|------|------|---------|
| 1 | 配置模型 + configs 表初始化 + API | 1 小时 |
| 2 | 心跳引擎（APScheduler 集成） | 1 小时 |
| 3 | 感知处理（空白 + 天气） | 1.5 小时 |
| 4 | 念头生成（规则模板） | 1 小时 |
| 5 | 决策引擎（评分 + 阈值） | 1 小时 |
| 6 | 消息发送（调 MessageService） | 0.5 小时 |
| 7 | 前端「自主意识」页面 | 2 小时 |
| 8 | 联调 + 测试 | 1 小时 |

**总计约 9 小时**，比 v0.2 的 14 天精简了 90%+。
