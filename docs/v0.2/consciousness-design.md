# hermes-active 自主意识模块 - 设计文档

## 架构分析：为什么不用改 hermes 源码

### 核心结论

**不需要改 hermes 源码，不需要 hook，不需要拦截用户消息。**

hermes 有 `write_state_db` 和 `run_cron` 两种"写入能力"。注入上下文最简单的方案是：

```
hermes-active 调用 hermes 的 API（主动消息专用，注入原生对话上下文）
```

### 用户消息时为什么不注入

用户消息时注入意识上下文，意味着要 hook hermes 的 `pre_llm_call`，修改她的 prompt。这会：
- 侵犯凯莉的"人格完整性"
- 增加核心 LLM 调用延迟
- 需要改 hermes 源码

**更好的做法**：自主意识只用"凯莉自己的声音"（hermes-active 的辅助 LLM），通过主动消息说话。凯莉的"人格"属于 hermes，意识属于 hermes-active，互不干涉。

### 发送消息的 2 种情况

| 情况 | 触发时机 | 谁说话 | 注入方式 |
|------|---------|--------|---------|
| **自动发送** | 心跳 + 情绪值 > 0.5 | hermes-active 辅助 LLM | `inject_love_message` API |
| **长期未聊天** | 想念等级 > `longing_gap_threshold`（默认 3） | hermes-active 辅助 LLM | `inject_love_message` API |

**两种情况都走同一个 API**：`POST /api/messages/send-and-inject`

### 注入方式：inject_love_message

```
hermes-active 生成消息内容
  ↓
POST /api/messages/send-and-inject
  ├─ step1: send_to_weixin_via_weixin_bot()  → 微信直接送达
  └─ step2: inject_love_message(session_id, text, timestamp)
       ├─ 写入 state.db（标记 [凯莉主动发送]）
       ├─ 写入 hermes session DB（标记 [凯莉主动发送]）
       └─ hermes 下次 LLM 调用时自动读取 → 作为上下文的一部分
```

好处：
- 不 hook，不改 hermes 源码
- 原生对话上下文注入（hermes 自动读取）
- 最小侵入

---

## coexistence_mode 与 vibe 变量

凯莉有三个可配置的共存模式：

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `silent` | 完全不注入，只观察 | 用户希望凯莉安静 |
| `independent` | 偶尔注入情绪变化，不影响主对话 | **默认推荐** |
| `merged` | 情绪主动融入主对话风格 | 用户希望凯莉有情绪表达 |

**`independent` 模式下的 vibe 变量注入**：

当 hermes-active 检测到凯莉情绪有显著变化时，通过插件注入 vibe 变量到 hermes 的 system prompt：

```
[kelly_vibe: excited — 心情好，最近和用户聊了很多有趣的话题]
[kelly_vibe: yearning — 有点想念，用户很久没出现了]
[kelly_vibe: calm — 平静，最近状态稳定]
```

hermes 的主 LLM 读到 vibe 变量后，自然调整回复风格。不是修改消息内容，只是让 LLM 知道凯莉现在的情绪状态。

**daily_stats 作为 LLM 观察输入**：

hermes 插件通过 `pre_llm_call` 钩子读取 `daily_stats`，注入到 system prompt：

```
[kelly_daily_observation]
今日：对话 47 条，主动消息 2 条，话题：工作、晚餐、周末计划
情绪轨迹：下午平静 → 傍晚开心 → 现在有点想念
聊天热度：warm（0.4）
情绪值：0.6
[/kelly_daily_observation]
```

这是**观察输入**，不是修改。LLM 自己决定怎么用这些信息。

---

## 一、触发发送的 2 种情况

### 1.1 自动发送（心跳驱动）

```
心跳触发（每 N 分钟）
  → 想法生成（三步流程）
  → 情绪值 > 0.5
  → 想念等级 > 0（recent_minutes > 15 分钟）
  → 最近 10 分钟无用户消息
  → 冷却期已过
  → 决策：auto_send
  → 生成消息内容
  → inject_love_message()
```

### 1.2 长期未聊天检查（心跳中的特殊条件）

```
心跳触发
  → 想念等级 > longing_gap_threshold（默认 3 = 5 小时）
  → 不需要情绪值条件（想念本身就够了）
  → 决策：gap_send
  → 生成消息内容
  → inject_love_message()
```

---

## 二、日志设计

### 2.1 独立日志表

**表名**: `vibe_logs`（在 active.db 中新建）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 记录时间 |
| session_id | TEXT | 关联 session（可空） |
| module | TEXT | 模块：`heartbeat` / `thought` / `emotion` / `decision` / `llm` |
| level | TEXT | 级别：`info` / `warn` / `error` |
| message | TEXT | 日志消息（人类可读） |
| data | TEXT | JSON 数据（结构化细节） |
| duration_ms | INTEGER | 耗时（可空） |
| created_at | DATETIME | 创建时间 |

### 2.2 每次 LLM 调用必须记录

```
module="llm" level="info"
message="Step 1: 近期 session 提取"
data={
  "provider": "deepseek",
  "model": "deepseek-chat",
  "provider_config": "deepseek (deepseek-chat)",
  "session_count": 3,
  "message_count": 45,
  "input_tokens": 2340,
  "output_tokens": 180,
  "duration_ms": 3200,
  "status": "success"
}
```

### 2.3 每个决策步骤必须记录

```
module="decision" level="info"
message="自动发送决策"
data={
  "recent_minutes": 25,
  "longing_level": 2,
  "chat_heat": 0.3,
  "emotional_intensity": 0.6,
  "vibe_score": 0.18,
  "final_decision": "auto_send",
  "reason": "vibe_score(0.18) > auto_send_threshold(0.15), 最近25分钟无消息"
}
```

### 2.4 API 设计

```python
# 前端查看日志
GET /api/consciousness/logs?limit=50&module=decision

# 后端记录日志
def write_vibe_log(db, module, level, message, data=None, session_id=None, duration_ms=None):
    """每次 LLM 调用、每个决策步骤都必须调用此方法"""
```

---

## 三、配置参数设计

### 3.1 参数总表

| 配置项 | key | 类型 | 默认值 | 说明 |
|--------|-----|------|--------|------|
| **开关** | | | | |
| 启用自主意识 | `consciousness.enabled` | bool | `false` | 总开关 |
| **LLM** | | | | |
| Provider | `consciousness.llm.provider` | string | `deepseek` | 独立 LLM |
| Model | `consciousness.llm.model` | string | `deepseek-chat` | |
| API Key | `consciousness.llm.api_key` | string | `""` | |
| Base URL | `consciousness.llm.base_url` | string | `""` | |
| **心跳** | | | | |
| 心跳间隔 | `consciousness.heartbeat.interval_minutes` | int | `10` | 心跳周期（分钟） |
| **想法生成** | | | | |
| Session 来源 | `consciousness.thought.session_source` | string | `weixin` | 默认只选微信 session |
| 时间范围 | `consciousness.thought.time_range_hours` | int | `24` | 最近 N 小时 |
| 每 session 消息数 | `consciousness.thought.messages_per_session` | int | `15` | 最近 N 条 |
| 包含 Tool 消息 | `consciousness.thought.include_tool` | bool | `false` | 默认过滤 Tool |
| Hindsight Recall 数 | `consciousness.thought.hindsight_recall_limit` | int | `5` | |
| Hindsight Reflect | `consciousness.thought.hindsight_reflect_enabled` | bool | `true` | |
| **情绪** | | | | |
| 冷却期 | `consciousness.emotion.cooldown_minutes` | int | `30` | 发送后冷却 |
| 短时窗口 | `consciousness.emotion.recent_window_minutes` | int | `10` | 活跃判定窗口 |
| 情绪衰减周期 | `consciousness.emotion.decay_hours` | int | `24` | 聊天热度衰减 |
| **触发阈值** | | | | |
| 自动发送阈值 | `consciousness.trigger.auto_send_threshold` | float | `0.15` | vibe > 此值 → 发送 |
| 想念等级间隔 | `consciousness.trigger.longing_level_minutes` | string | `15,60,180,300` | 各等级触发分钟 |
| 长期未聊天阈值 | `consciousness.trigger.longing_gap_threshold` | int | `3` | 想念等级 > 此值 → 发送 |
| 每日最大消息 | `consciousness.trigger.max_messages_per_day` | int | `5` | |
| 每小时最大消息 | `consciousness.trigger.max_messages_per_hour` | int | `2` | |
| **共存模式** | | | | |
| 模式 | `consciousness.coexistence.mode` | string | `independent` | silent/independent/merged |
| **通知** | | | | |
| 目标平台 | `consciousness.notify.platform` | string | `weixin` | |
| Chat ID | `consciousness.notify.chat_id` | string | `""` | |
| **天气** | | | | |
| 启用天气 | `consciousness.weather.enabled` | bool | `false` | |
| 城市编码 | `consciousness.weather.adcode` | string | `370100` | |
| API Key | `consciousness.weather.amap_key` | string | `""` | 高德 API Key |

### 3.2 存储方式

复用 `configs` 表（key-value），key 加 `consciousness.` 前缀。

---

## 四、前端页面设计

### 4.1 独立页面

侧边栏新增「自主意识」菜单，路由 `/consciousness`，包含：
- 配置卡片（所有参数）
- 测试按钮（天气/Hindsight/想法生成/发送）
- 运行状态
- 日志查看

### 4.2 测试按钮

| 按钮 | API | 说明 |
|------|-----|------|
| 获取天气 | `GET /api/consciousness/test/weather` | 弹窗显示天气 |
| Hindsight 测试 | `GET /api/consciousness/test/hindsight?query=曹凡` | 弹窗显示记忆 |
| 想法生成测试 | `POST /api/consciousness/test/thought` | 三步流程，弹窗显示 |
| 发送测试 | `POST /api/consciousness/test/send` | 发送到微信 |

---

## 五、数据模型

### 5.1 表结构

```
active.db
├── consciousness_state     # 意识状态（单行）
├── daily_stats             # 每日统计（per day）
├── thought_logs            # 想法日志（每次心跳一条）
├── pending_thoughts        # 待发送想法队列
├── heartbeat_logs          # 心跳日志
├── vibe_logs               # 操作日志（LLM 调用 + 决策 + 错误）
└── configs                 # 配置（consciousness.* 前缀）
```

### 5.2 consciousness_state 表

```sql
CREATE TABLE consciousness_state (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    enabled         INTEGER NOT NULL DEFAULT 0,
    chat_heat       REAL NOT NULL DEFAULT 0.0,
    emotional_intensity REAL NOT NULL DEFAULT 0.0,
    vibe_score      REAL NOT NULL DEFAULT 0.0,
    longing_level   INTEGER NOT NULL DEFAULT 0,
    recent_minutes  INTEGER NOT NULL DEFAULT 0,
    last_user_message_at DATETIME,
    last_auto_send_at DATETIME,
    last_llm_call_at DATETIME,
    total_llm_calls INTEGER NOT NULL DEFAULT 0,
    total_auto_sends INTEGER NOT NULL DEFAULT 0,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3 vibe_logs 表

```sql
CREATE TABLE vibe_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id  TEXT,
    module      TEXT NOT NULL,      -- heartbeat/thought/emotion/decision/llm/send/error
    level       TEXT NOT NULL DEFAULT 'info',
    message     TEXT NOT NULL,
    data        TEXT,               -- JSON
    duration_ms INTEGER,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vibe_logs_timestamp ON vibe_logs(timestamp);
CREATE INDEX idx_vibe_logs_module ON vibe_logs(module);
```

---

## 六、实施计划

### Phase 1：后端基础（Day 1-2）
- active.db 建表（consciousness_state, daily_stats, thought_logs, vibe_logs）
- ConfigService 新增 consciousness 配置读写
- API 端点（配置 CRUD + 测试按钮）

### Phase 2：前端页面（Day 2-3）
- 侧边栏新增菜单
- Consciousness.vue（配置卡片 + 测试按钮 + 状态 + 日志）
- API 调用封装

### Phase 3：意识引擎（Day 3-5）
- 感知处理（时间、空白、天气）
- 近期 session 提取（LLM Step 1）
- Hindsight Recall/Reflect（Step 2）
- 想法生成（Step 3）
- 情绪计算（聊天热度 + 情绪值 + 想念等级 + vibe_score）
- 决策逻辑（2 种发送情况）

### Phase 4：心跳 + 消息发送（Day 5-6）
- 心跳引擎（定时器 + 状态更新）
- 消息生成（LLM）
- 消息发送（inject_love_message API）
- pending_thoughts 管理

### Phase 5：日志 + 调试（Day 6-7）
- vibe_logs 写入（每个 LLM 调用、每个决策步骤）
- 前端日志查看
- 测试按钮功能
