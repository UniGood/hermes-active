# 2026-06-24 去掉延迟发送 + LLM 调用前置过滤

## 背景

凯莉的延迟发送机制存在两个问题：
1. **延迟念头可能过时**——"中午吃饭了吗"这种话如果 2 小时后才发，情境完全错位
2. **每次心跳都调 LLM**——即使预评分已知很低（情绪平稳、时间不匹配），仍然消耗 LLM token

## 目标

- **删除延迟发送**功能（6 个函数 + 1 个配置块）
- **预评分前置过滤**：低于 `memory_threshold` 的心跳直接跳过，不调 LLM
- 保持决策矩阵的 **auto_send / memory / skip** 三档
- 决策依然基于**真实 score**（LLM 调用后用真实内容算分）

## 现状

### LLM 调用时机（改造前）

```python
def run_heartbeat():
    context = collect_context()
    decision, reason, score = make_decision(...)  # 不调 LLM
    if decision == "auto_send":
        thought = await llm_generate()            # 调 LLM
        send(thought)
    elif decision == "delay_send":
        thought = await llm_generate()            # 调 LLM
        enqueue(thought)                          # 入延迟队列
    elif decision == "memory":
        thought = await llm_generate()            # 调 LLM
        store_hindsight(thought)
    # skip 不调 LLM
```

**问题**：auto_send / delay_send / memory 三种决策都会调 LLM。即使预评分已知很低，仍然消耗 token。

### 延迟队列当前状态（删除前）

- 队列里 5 条延迟念头
- 重评估机制：每 30 分钟重算 score，超过 send_threshold 就发送
- 累计升级过 N 条 → 入 `active_thought_logs` 表，`recall_source="delay_queue"`

## 改造方案

### 阶段 1：删除延迟发送

**删除 6 个函数**：
- `add_to_delay_queue`
- `add_to_delay_queue_v2`
- `generate_thought_for_delay`
- `get_delayed_thoughts`
- `reevaluate_delayed_thoughts`
- `save_delayed_thoughts`

**修改决策矩阵**：
```python
# 改造前
if score > send_threshold:  return "auto_send"
elif score > delay_threshold: return "delay_send"   # ← 删除
elif score > memory_threshold: return "memory"
else: return "skip"

# 改造后
if score > send_threshold:  return "auto_send"
elif score > memory_threshold: return "memory"
else: return "skip"
```

**修改决策分支**（`decide_and_execute`）：
```python
# 删除 elif decision_type == "delay_send": 分支
```

**清理配置**：
- 删除 `decision.delay_threshold` 字段（默认值 0.15）
- 删除 `active_consciousness.delay.*` 整个配置块（enabled/max_retry/retry_interval/max_queue_size/max_age_hours）
- 前端配置页面删除对应字段

**清理数据库**：
- `active_consciousness.delayed_thoughts` 队列内容清空

### 阶段 2：LLM 调用前置预评分过滤

**新增 `should_call_llm(pre_score, memory_threshold)` 函数**：
```python
def should_call_llm(pre_score: float, memory_threshold: float) -> bool:
    """根据预评分判断是否值得调 LLM

    预评分（基于情绪、时间、沉默、频率）足够高 → 调 LLM 生成念头
    否则 → 直接 skip，节省 token
    """
    return pre_score >= memory_threshold
```

**预评分公式**（复用现有 `make_decision` 的算法）：
```python
def pre_calculate_score(status, emotion_state, decision_config) -> float:
    """在不调 LLM 的情况下估算 score"""
    intensity = emotion_state.intensity()
    time_fitness, _ = get_time_fitness()
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    silence_factor = calc_silence_factor(silence_minutes)
    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = decision_config.get("max_per_hour", 100)
    frequency_limit = 1.0 if hour_sent < max_per_hour else 0.0
    return intensity * time_fitness * silence_factor * frequency_limit
```

**改造后流程**：
```python
def run_heartbeat():
    context = collect_context()
    
    # 阶段 1：预评分过滤（不调 LLM）
    pre_score = pre_calculate_score(status, emotion_state, decision_config)
    memory_threshold = decision_config.get("memory_threshold", 0.05)
    
    if pre_score < memory_threshold:
        # 预评分太低，直接 skip，节省 LLM 调用
        skip_and_log(pre_score)
        return
    
    # 阶段 2：调 LLM 生成念头（值得消耗 token）
    thought = await llm_generate_thought()
    
    # 阶段 3：用真实 score 做最终决策
    real_score = calculate_real_score(thought, ...)
    decision = make_decision_from_score(real_score)
    
    if decision == "auto_send":
        send(thought)
    elif decision == "memory":
        store_hindsight(thought)
    # skip（LLM 后判断 score 不够）
```

### 边界 case 处理

| 预评分 | LLM 调用 | 真实 score | 最终决策 | 说明 |
|--------|---------|-----------|---------|------|
| < memory | 否 | - | skip | 节省 token |
| >= memory | 是 | >= send | auto_send | 正常发送 |
| >= memory | 是 | >= memory | memory | 存 Hindsight |
| >= memory | 是 | < memory | skip | LLM 生成但分数低 |

### 不在范围

- 念头类型预判（`thought_type` 是 LLM 输出的一部分，调 LLM 前不知道）
- 改 `make_decision` 公式
- 改 Hindsight 存储逻辑
- 改保护机制

## 影响范围

### 后端
- `backend/services/active_consciousness_service.py`：删除 6 函数 + 改决策分支 + 新增预评分函数
- `backend/routers/active_consciousness.py`：删除 delay 相关 API 端点（如有）
- 数据库 `active_consciousness.delayed_thoughts` 队列清空

### 前端
- `frontend/src/views/ActiveConsciousness.vue`：决策阈值配置删除 `delay_threshold` 字段
- 前端测试接口删除 delay 相关（如果有）

### 配置
- `decision.delay_threshold` 默认值删除
- `active_consciousness.delay.*` 整个块删除
- 用户现有配置迁移：自动忽略这两个块（兼容旧配置不报错）

## 风险

1. **历史数据**：delay_queue 升级过的念头会保留（`recall_source="delay_queue"`），不清理（保留历史可追溯）
2. **决策变化**：中间分数（0.15~0.35）的念头行为变化：
   - 之前：入延迟队列 → 30 分钟后重评可能发送
   - 现在：调 LLM 后判断 < send_threshold → 存 memory 或 skip
3. **保护机制**：LLM 前置过滤可能错过"沉默后立即发送"等保护机制触发的时机（保留 LLM 调用当预评分 >= memory_threshold，避免此风险）

## 验收

- [ ] 后端语法检查通过
- [ ] 前端 build 成功
- [ ] 数据库迁移：delay_queue 清空、delay 相关配置块被忽略
- [ ] 心跳模拟：预评分 < memory_threshold → 不调 LLM，记 skip 日志
- [ ] 心跳模拟：预评分 >= memory_threshold → 调 LLM，决策正确
- [ ] decision.delay_threshold 配置项不再出现
- [ ] 前端配置界面不再有 delay_threshold 字段
- [ ] 历史 `recall_source="delay_queue"` 数据保留（不清理）

## 不在范围

- 念头类型预判
- 改 `make_decision` 公式
- 改 Hindsight 存储逻辑