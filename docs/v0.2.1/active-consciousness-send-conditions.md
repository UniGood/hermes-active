# 主动意识发送消息条件

> v0.2.1 版本 - 主动意识模块消息触发条件详解

---

## 一、心跳触发流程

```
心跳调度器（每 N 秒触发一次，默认 600 秒）
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. 前置检查                                                 │
│    ✓ config.enabled = true                                  │
│    ✓ config.active.enabled = true                           │
│    任一不满足 → 跳过心跳                                     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 情绪演化（时间驱动）                                      │
│    读取上次情绪状态 → 计算时间间隔 → 演化                     │
│    - arousal 自然衰减（越久越平静）                          │
│    - social_need 自然增长（越久越想聊天）                    │
│    - valence 回归中性（0.5）                                │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 上下文获取                                               │
│    - Session 上下文（最近对话）                              │
│    - Hindsight 记忆召回（如果启用）                          │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM 情绪评估                                             │
│    输入：上下文 + 当前状态                                   │
│    输出：VA 值（valence, arousal, social_need, dominant）    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 情绪合并                                                 │
│    merged = evolved × (1 - confidence) + llm × confidence   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 决策评分                                                 │
│    score = intensity × time_fitness × silence × frequency   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. 根据分数决策                                             │
│    - score > send_threshold (0.6)   → auto_send             │
│    - score > delay_threshold (0.3)  → delay_send            │
│    - score > memory_threshold (0.1) → memory                │
│    - score ≤ memory_threshold       → skip                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、决策公式

```
score = intensity × time_fitness × silence_factor × frequency_limit
```

### 2.1 情绪强度（intensity）

```
intensity = (valence + arousal + social_need) / 3
```

| 值 | 含义 |
|------|------|
| valence（效价） | 情感正负性，0=消极，1=积极 |
| arousal（唤醒度） | 情感激活程度，0=平静，1=激动 |
| social_need（社交需求） | 想聊天的程度，0=不需要，1=非常想 |

### 2.2 时间窗口权重（time_fitness）

| 时间段 | 权重 | 标签 |
|--------|------|------|
| 7:00-9:00 | 1.0 | 早安窗口 |
| 9:00-12:00 | 0.8 | 工作时间 |
| 12:00-14:00 | 0.9 | 午休时间 |
| 14:00-18:00 | 0.7 | 工作时间 |
| 18:00-22:00 | 1.0 | 下班时间 |
| 22:00-23:30 | 0.8 | 睡前时间 |
| 23:30-7:00 | 0.3 | 深夜 |

### 2.3 沉默因子（silence_factor）

| 沉默时长 | 因子 | 说明 |
|----------|------|------|
| < 60 分钟 | 0.3 | 刚聊过天 |
| 60-180 分钟 | 0.5 | 1-3 小时没聊 |
| 180-360 分钟 | 0.5 | 3-6 小时没聊 |
| > 360 分钟 | 0.9 | 6 小时以上没聊 |

### 2.4 频率限制（frequency_limit）

```python
frequency_limit = max(0.1, 1.0 - (本小时已发送数 / 每小时最大数))
```

- 默认每小时最多 2 条
- 已发送 1 条 → factor = 0.5
- 已发送 2 条 → factor = 0.1（最低）

---

## 三、决策阈值

| 分数范围 | 决策类型 | 行动 |
|----------|----------|------|
| > 0.6 | **auto_send** | 立即生成念头并发送消息 |
| 0.3 - 0.6 | **delay_send** | 生成念头，加入延迟队列 |
| 0.1 - 0.3 | **memory** | 生成念头，存入 Hindsight 记忆 |
| ≤ 0.1 | **skip** | 跳过，什么都不做 |

---

## 四、发送保护机制（待实现）

配置中有以下保护参数，但**当前未在决策中生效**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `no_send_after_user_msg_minutes` | 10 | 用户消息后 N 分钟内不发送 |
| `no_send_while_heat_above` | 0.5 | 聊天热度高于此值时不发送 |
| `no_send_while_vibe_below` | 0.3 | 情绪值低于此值时不发送 |

### 4.1 建议的保护逻辑

```python
# 在 make_decision_v2 之前检查
def check_send_protection(config, status):
    active_config = config.get("active", {})
    
    # 1. 用户消息后不发送
    no_send_minutes = active_config.get("no_send_after_user_msg_minutes", 10)
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < no_send_minutes:
        return "skip", f"用户最近 {no_send_minutes} 分钟内有消息"
    
    # 2. 热度过高不发送
    heat_threshold = active_config.get("no_send_while_heat_above", 0.5)
    current_heat = status.get("chat_heat", {}).get("heat", 0)
    if current_heat > heat_threshold:
        return "skip", f"聊天热度 {current_heat} 超过阈值 {heat_threshold}"
    
    # 3. 情绪过低不发送
    vibe_threshold = active_config.get("no_send_while_vibe_below", 0.3)
    current_vibe = status.get("emotional_intensity", {}).get("intensity", 0)
    if current_vibe < vibe_threshold:
        return "skip", f"情绪值 {current_vibe} 低于阈值 {vibe_threshold}"
    
    return None, None  # 通过检查
```

---

## 五、决策后的行动

### 5.1 auto_send（立即发送）

```
1. 获取上下文（Session + Hindsight）
2. LLM 生成念头
3. 记录念头日志
4. 发送消息到目标平台
5. 存入 Hindsight（如果配置启用）
```

### 5.2 delay_send（延迟发送）

```
1. 生成念头
2. 记录念头日志
3. 加入延迟队列（active_delayed_thoughts 表）
4. 下次心跳时重新评估
   - 分数 > 0.6 → 升级为发送
   - 分数 < 0.1 → 降级为丢弃
   - 否则保持延迟
```

### 5.3 memory（存为记忆）

```
1. 生成念头
2. 记录念头日志
3. 存入 Hindsight（带标签）
4. 不发送消息
```

### 5.4 skip（跳过）

```
1. 记录心跳日志
2. 不生成念头
3. 不发送消息
```

---

## 六、延迟队列机制

### 6.1 队列结构

```python
class DelayedThought:
    id: int
    content: str          # 念头内容
    thought_type: str     # 念头类型
    score: float          # 入队时的分数
    created_at: str       # 创建时间
    retry_count: int      # 重试次数
    next_retry_at: str    # 下次重试时间
    emotion_snapshot: dict # 入队时的情绪快照
```

### 6.2 队列限制

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `max_queue_size` | 10 | 队列最大容量 |
| `max_retry` | 3 | 最大重试次数 |
| `retry_interval_minutes` | 30 | 重试间隔（分钟） |
| `max_age_hours` | 4 | 最大存活时间（小时） |

### 6.3 重评估逻辑

```
每次心跳时：
1. 遍历延迟队列中的每个念头
2. 检查是否过期（超过 max_age_hours）→ 丢弃
3. 检查是否超过最大重试次数 → 丢弃
4. 使用当前情绪状态重新计算分数
5. 根据新分数决定：
   - score > send_threshold → 升级为发送
   - score < memory_threshold → 降级为丢弃
   - 否则 → 保持延迟
```

---

## 七、增强念头生成

### 7.1 触发条件

- `config.thought_enhanced.enabled = true`

### 7.2 生成流程

```
1. 根据 arousal 选择时间范围
   - arousal < 0.3 → 查看 15 天聊天记录
   - arousal < 0.7 → 查看 7 天聊天记录
   - arousal ≥ 0.7 → 查看 1 天聊天记录

2. 确定生成数量
   - 15 天 → 3 个念头
   - 7 天 → 2 个念头
   - 1 天 → 1 个念头

3. 获取上下文
   - 聊天记录
   - 旧念头（用于去重）
   - 天气信息（如果启用）

4. LLM 生成念头

5. 存储
   - 存入 active_thought_logs 表
   - 存入 Hindsight（如果满足条件）
```

### 7.3 注意事项

⚠️ **当前问题**：增强念头只存储，**不参与发送决策**。增强念头的分数不会影响 `make_decision_v2` 的结果。

---

## 八、完整决策流程图

```
                    心跳触发
                        │
                        ▼
              ┌─────────────────┐
              │  前置检查通过？  │
              └────────┬────────┘
                       │ Yes
                       ▼
              ┌─────────────────┐
              │  情绪演化 + 合并 │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  获取上下文      │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  LLM 情绪评估   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  发送保护检查    │
              │  (待实现)        │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ 热度过高 │ │ 用户刚聊 │ │ 情绪过低 │
    │   skip   │ │   skip   │ │   skip   │
    └──────────┘ └──────────┘ └──────────┘
                       │
                       ▼ (通过保护检查)
              ┌─────────────────┐
              │  决策评分        │
              │  score = ...     │
              └────────┬────────┘
                       │
       ┌───────────────┼───────────────┬───────────────┐
       │               │               │               │
       ▼               ▼               ▼               ▼
  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
  │ > 0.6   │    │ > 0.3   │    │ > 0.1   │    │ ≤ 0.1   │
  │auto_send│    │delay    │    │memory   │    │  skip   │
  └────┬────┘    └────┬────┘    └────┬────┘    └─────────┘
       │               │               │
       ▼               ▼               ▼
  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │生成念头 │    │生成念头 │    │生成念头 │
  │发送消息 │    │入延迟队列│   │存Hindsight│
  │存Hindsight│  └─────────┘    └─────────┘
  └─────────┘
```

---

## 九、配置项汇总

### 9.1 基础配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enabled` | false | 总开关 |
| `active.enabled` | true | 主动发送开关 |
| `active.heartbeat_interval` | 600 | 心跳间隔（秒） |

### 9.2 决策阈值

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `decision.send_threshold` | 0.6 | 立即发送阈值 |
| `decision.delay_threshold` | 0.3 | 延迟发送阈值 |
| `decision.memory_threshold` | 0.1 | 存为记忆阈值 |
| `decision.max_per_hour` | 2 | 每小时最大发送数 |
| `decision.max_per_day` | 5 | 每天最大发送数 |

### 9.3 发送保护（待实现）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `active.no_send_after_user_msg_minutes` | 10 | 用户消息后 N 分钟内不发送 |
| `active.no_send_while_heat_above` | 0.5 | 热度高于此值不发送 |
| `active.no_send_while_vibe_below` | 0.3 | 情绪低于此值不发送 |

### 9.4 情绪演化

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `emotion.decay_rate` | 0.02 | arousal 每分钟衰减率 |
| `emotion.social_need_growth` | 0.01 | social_need 每分钟增长率 |
| `emotion.valence_regression` | 0.1 | valence 回归中性系数 |
| `emotion.weight_evolved` | 0.4 | 演化值权重 |
| `emotion.weight_llm` | 0.6 | LLM 值权重 |

### 9.5 延迟队列

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `delay.enabled` | true | 延迟发送开关 |
| `delay.max_retry` | 3 | 最大重试次数 |
| `delay.retry_interval_minutes` | 30 | 重试间隔 |
| `delay.max_queue_size` | 10 | 队列最大容量 |
| `delay.max_age_hours` | 4 | 最大存活时间 |

---

## 十、已知问题

### 10.1 发送保护未生效

**问题**：配置中有 `no_send_after_user_msg_minutes`、`no_send_while_heat_above`、`no_send_while_vibe_below`，但在 `make_decision_v2` 中没有使用这些配置进行检查。

**影响**：可能在用户正在聊天时发送消息，体验不佳。

### 10.2 延迟队列重评估不完整

**问题**：`reevaluate_delayed_thoughts` 函数存在但发送逻辑不完整。

**影响**：延迟队列中的念头可能无法正确升级为发送。

### 10.3 增强念头不参与发送

**问题**：增强念头生成后只存储，不参与发送决策。

**影响**：增强念头的质量可能很高，但无法触发发送。

---

**最后更新**：2026-06-19
**版本**：v0.2.1
