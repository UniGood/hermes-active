# 主动意识设计文档

## 功能说明

主动意识通过心跳调度器定时触发，自动计算情绪状态、生成想法、决策是否发送消息。

**核心流程**：
```
心跳触发（每 N 分钟）
  → 计算情绪状态（聊天热度、情绪值、想念等级）
  → 想法生成（三步流程）
  → 决策逻辑（自动发送 / 长期未聊天 / 跳过）
  → 生成消息内容（LLM）
  → 发送消息到目标
```

---

## 实现状态

### ✅ 已实现

| 功能 | 文件 | 说明 |
|------|------|------|
| 配置读写 | `active_consciousness_service.py` | get_config / update_config |
| 状态查询 | `active_consciousness_service.py` | get_status（longing, chat_heat, emotional_intensity） |
| 想法日志查询 | `active_consciousness_service.py` | get_thoughts / delete_thought |
| 心跳日志查询 | `active_consciousness_service.py` | get_heartbeats / delete_heartbeat |
| 想法日志写入 | `active_consciousness_service.py` | write_thought_log |
| 心跳日志写入 | `active_consciousness_service.py` | write_heartbeat_log |
| Session 上下文提取 | `active_consciousness_service.py` | extract_session_context（Step 1） |
| Hindsight Recall | `active_consciousness_service.py` | call_hindsight_recall（Step 2） |
| Hindsight Reflect | `active_consciousness_service.py` | call_hindsight_reflect（Step 2） |
| 想法生成 | `active_consciousness_service.py` | generate_thought（Step 3，LLM 调用） |
| 决策逻辑 | `active_consciousness_service.py` | make_decision（检查上限、冷却期、条件） |
| 消息发送 | `active_consciousness_service.py` | send_message_to_target |
| 心跳调度器 | `active_consciousness_service.py` | start/stop/update_heartbeat_scheduler |
| 心跳执行 | `active_consciousness_service.py` | run_heartbeat（主循环） |
| LLM 模式支持 | `active_consciousness_service.py` | hermes 模式 + 自定义 LLM 模式 |
| 前端配置页面 | `ActiveConsciousness.vue` | LLM 配置、心跳配置、决策配置、通知目标 |
| 前端状态页面 | `ActiveConsciousness.vue` | 心跳状态、发送统计 |
| 前端日志页面 | `ActiveConsciousness.vue` | 想法日志、心跳日志 |
| 前端测试页面 | `ActiveConsciousness.vue` | 想法生成测试 |

### ❌ 未实现

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 重试想法 | retry_thought 函数返回 "待实现" | 中 |
| 消息内容优化 | 当前直接用想法作为消息，可以增加润色 | 低 |

---

## 配置参数

存储在 `configs` 表，key 前缀：`active_consciousness.`

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
| `active_consciousness.active.cooldown_minutes` | int | 30 | 冷却期（分钟） |
| `active_consciousness.session.sources` | json | ["weixin"] | Session 来源 |
| `active_consciousness.session.time_range_hours` | int | 24 | 时间范围（小时） |
| `active_consciousness.session.max_messages_per_session` | int | 15 | 每个 Session 最大消息数 |
| `active_consciousness.session.filter_tool_messages` | bool | true | 过滤 tool 消息 |
| `active_consciousness.decision.send_threshold` | float | 0.6 | 发送阈值 |
| `active_consciousness.decision.delay_threshold` | float | 0.3 | 延迟发送阈值 |
| `active_consciousness.decision.memory_threshold` | float | 0.1 | 存为记忆阈值 |
| `active_consciousness.decision.max_per_hour` | int | 2 | 每小时最大消息 |
| `active_consciousness.decision.max_per_day` | int | 5 | 每日最大消息 |
| `active_consciousness.decision.longing_gap_threshold` | int | 3 | 长期未聊天阈值 |
| `active_consciousness.hindsight.enabled` | bool | true | 启用 Hindsight |
| `active_consciousness.hindsight.recall_limit` | int | 5 | Recall 结果数 |
| `active_consciousness.hindsight.reflect_enabled` | bool | true | 启用 Reflect |
| `active_consciousness.notify.platform` | string | weixin | 通知平台 |
| `active_consciousness.notify.chat_id` | string | "" | 通知 Chat ID |

---

## API 接口

前缀：`/api/active-consciousness`

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | /config | 获取配置 | ✅ |
| PUT | /config | 更新配置 | ✅ |
| GET | /status | 获取状态 | ✅ |
| GET | /thoughts | 获取想法日志 | ✅ |
| DELETE | /thoughts/{id} | 删除想法 | ✅ |
| POST | /thoughts/{id}/retry | 重试想法 | ❌ 待实现 |
| GET | /heartbeats | 获取心跳日志 | ✅ |
| DELETE | /heartbeats/{id} | 删除心跳 | ✅ |
| POST | /test/thought-generation | 测试想法生成 | ✅ |

---

## 数据库表

### active_thought_logs（想法日志）

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

### active_heartbeat_logs（心跳日志）

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

---

## 决策逻辑

### 条件检查顺序

1. **检查每日上限**：today_sent_count >= max_per_day → skip
2. **检查每小时上限**：hour_sent_count >= max_per_hour → skip
3. **检查冷却期**：last_sent_at + cooldown_minutes > now → skip
4. **检查用户消息窗口**：recent_user_msg_at + no_send_after_user_msg_minutes > now → skip
5. **条件1：自动发送**：emotional_intensity > 0.5 且 longing_level > 0 → auto_send
6. **条件2：长期未聊天**：longing_level > longing_gap_threshold → gap_send
7. **不满足条件**：skip

---

## 心跳调度器

使用 APScheduler 的 IntervalTrigger：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

heartbeat_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 启动时添加任务
heartbeat_scheduler.add_job(
    run_heartbeat,
    trigger=IntervalTrigger(seconds=interval_seconds),
    id="active_consciousness_heartbeat",
    name="主动意识心跳",
    replace_existing=True
)

heartbeat_scheduler.start()
```

**应用启动时**：`start_heartbeat_scheduler()`
**应用停止时**：`stop_heartbeat_scheduler()`
**配置更新时**：`update_heartbeat_interval(interval_seconds)`

---

## 文件结构

```
backend/
├── models/active_consciousness.py     # 数据模型
├── models/active.py                   # 表定义（active_thought_logs, active_heartbeat_logs）
├── routers/active_consciousness.py    # API 路由
└── services/active_consciousness_service.py  # 业务逻辑

frontend/src/
├── views/ActiveConsciousness.vue      # 前端页面
└── api/active_consciousness.js        # API 封装
```

---

## 不合理之处

1. **retry_thought 未实现**：函数返回 "待实现"，需要补充重试逻辑
2. **情绪值计算简单**：当前直接用 chat_heat 作为 emotional_intensity，应该用 LLM 分析情绪
3. **消息发送依赖 inject_love_message API**：当前直接调用 HTTP API，如果 API 不可用会失败
4. **缺少发送失败重试**：消息发送失败后没有重试机制
5. **心跳间隔更新不重启调度器**：当前用 reschedule_job，但 APScheduler 的 IntervalTrigger 不支持动态更新间隔
