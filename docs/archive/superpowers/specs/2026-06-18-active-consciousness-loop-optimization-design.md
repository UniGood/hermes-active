# 主动意识模块闭环优化设计

> 快速扫描分析结果 + 改进方案

---

## 一、分析范围

- **深度**：快速扫描
- **边界**：仅主动意识模块
- **维度**：逻辑完整性、数据一致性、异常处理、性能与资源

---

## 二、发现的问题

### 2.1 情绪闭环

#### 问题 1：情绪演化与 LLM 评估的权重固定

**现状**：演化权重 40% + LLM 评估 60% 是硬编码的

**问题**：
- 不同场景可能需要不同的权重（如长时间未聊天时应更信任演化）
- LLM 评估不稳定时，固定权重会导致情绪波动过大

**改进方案**：
```python
# 动态权重：根据 LLM 评估的置信度调整
def merge_emotion_dynamic(evolved, llm_assessed, llm_confidence):
    if llm_confidence < 0.3:
        # LLM 不可信，更信任演化
        weight_evolved, weight_llm = 0.7, 0.3
    elif llm_confidence > 0.8:
        # LLM 很可信，更信任 LLM
        weight_evolved, weight_llm = 0.3, 0.7
    else:
        # 默认权重
        weight_evolved, weight_llm = 0.4, 0.6
```

**影响**：P2（中期改进）

---

#### 问题 2：情绪状态持久化时机不明确

**现状**：每次心跳都保存情绪，但对话中的情绪变化没有实时保存

**问题**：
- 用户对话时情绪变化（如开心 → 焦虑），但心跳时才保存
- 下次心跳可能读取到过时的情绪状态

**改进方案**：
```python
# 在消息处理完成后立即保存情绪
async def on_message_sent(message, response):
    # 分析情绪变化
    new_emotion = analyze_emotion_from_message(message, response)
    # 立即保存
    update_emotion_state(new_emotion)
```

**影响**：P1（短期优化）

---

### 2.2 念头闭环

#### 问题 3：延迟队列的念头没有过期机制

**现状**：延迟队列只检查重试次数，没有时间过期

**问题**：
- 念头可能在队列中停留很久（如深夜生成的念头，早上才重试）
- 过时的念头发送出去会显得不自然

**改进方案**：
```python
# 添加过期时间检查
def is_thought_expired(thought, max_age_hours=4):
    created = datetime.fromisoformat(thought.created_at)
    age_hours = (datetime.now() - created).total_seconds() / 3600
    return age_hours > max_age_hours

# 在重评估时检查过期
for thought in delayed_thoughts:
    if is_thought_expired(thought):
        stats["discarded"] += 1
        continue
```

**影响**：P0（立即修复）

---

#### 问题 4：念头类型判断逻辑过于简单

**现状**：`determine_thought_type()` 使用简单的优先级判断

**问题**：
- 只要有 Hindsight 结果就返回 `memory` 类型，忽略了其他重要因素
- 天气信息传入但从未使用（weather_info 始终为 None）

**改进方案**：
```python
# 更智能的念头类型判断
def determine_thought_type_v2(status, emotion_state, hindsight_results, context):
    # 1. 检查时间特殊性（早安、晚安）
    if is_special_time():
        return ThoughtType.TIME
    
    # 2. 检查沉默时长
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes > 180:  # 3小时没聊天
        return ThoughtType.SILENCE
    
    # 3. 检查情绪强度
    if emotion_state.intensity() > 0.6:
        return ThoughtType.EMOTION
    
    # 4. 检查是否有相关回忆
    if hindsight_results and len(hindsight_results) > 0:
        return ThoughtType.MEMORY
    
    # 5. 默认关联念头
    return ThoughtType.ASSOCIATION
```

**影响**：P2（中期改进）

---

### 2.3 配置闭环

#### 问题 5：配置变更没有实时生效

**现状**：配置保存后，心跳调度器不会立即使用新配置

**问题**：
- 用户修改心跳间隔后，需要等待下次心跳才能生效
- 无法快速测试配置效果

**改进方案**：
```python
# 配置变更时重启调度器
async def on_config_updated(new_config):
    # 如果心跳间隔变化，重启调度器
    if new_config.heartbeat_interval != current_interval:
        stop_heartbeat_scheduler()
        start_heartbeat_scheduler(new_config.heartbeat_interval)
```

**影响**：P1（短期优化）

---

#### 问题 6：缺少配置验证

**现状**：配置直接保存，没有验证逻辑

**问题**：
- 用户可能输入无效值（如心跳间隔 0 秒）
- 阈值配置可能矛盾（send_threshold < delay_threshold）

**改进方案**：
```python
# 配置验证
def validate_config(config):
    errors = []
    
    # 验证心跳间隔
    heartbeat_interval = config.get("active", {}).get("heartbeat_interval", 600)
    if heartbeat_interval < 60:
        errors.append("心跳间隔不能小于 60 秒")
    
    # 验证阈值关系
    send_threshold = config.get("decision", {}).get("send_threshold", 0.6)
    delay_threshold = config.get("decision", {}).get("delay_threshold", 0.3)
    if send_threshold <= delay_threshold:
        errors.append("发送阈值必须大于延迟阈值")
    
    return errors
```

**影响**：P1（短期优化）

---

### 2.4 数据一致性

#### 问题 7：情绪状态与日志不一致

**现状**：心跳日志记录的情绪值可能与实际保存的不一致

**问题**：
- `run_heartbeat()` 中先记录日志，再保存情绪
- 如果保存失败，日志中的情绪值是错误的

**改进方案**：
```python
# 先保存情绪，再记录日志
update_emotion_state(merged_state)  # 先保存
heartbeat_id = write_heartbeat_log(..., emotional_intensity=merged_state.intensity())  # 后记录
```

**影响**：P1（短期优化）

---

#### 问题 8：延迟队列的状态没有同步到前端

**现状**：前端显示的延迟队列数量可能不准确

**问题**：
- 延迟队列存储在 configs 表的 JSON 中
- 前端读取的是 `status.delayed_count`，但这个值没有实时更新

**改进方案**：
```python
# 在状态查询时实时计算延迟队列数量
def get_status():
    # ... 其他状态 ...
    delayed_thoughts = get_delayed_thoughts()
    status["delayed_count"] = len(delayed_thoughts)
    return status
```

**影响**：P3（长期规划）

---

### 2.5 异常处理

#### 问题 9：LLM 调用失败时的降级策略不完善

**现状**：LLM 情绪评估失败时，使用演化值作为 fallback

**问题**：
- 只检查了"返回全0"的情况，其他异常（如超时、格式错误）没有处理
- 没有记录 LLM 失败的次数和原因

**改进方案**：
```python
# 完善的 LLM 调用包装
async def call_llm_with_fallback(prompt, fallback_value):
    try:
        result = await call_llm(prompt)
        if not result or is_invalid(result):
            logger.warning("LLM 返回无效结果，使用 fallback")
            return fallback_value, False
        return result, True
    except TimeoutError:
        logger.error("LLM 调用超时")
        return fallback_value, False
    except Exception as e:
        logger.error("LLM 调用异常: %s", e)
        return fallback_value, False
```

**影响**：P0（立即修复）

---

#### 问题 10：Hindsight 客户端没有重连机制

**现状**：Hindsight 客户端是全局单例，连接失败后不会自动重连

**问题**：
- 如果 Hindsight 服务重启，客户端会一直失败
- 需要手动重启 hermes-active 才能恢复

**改进方案**：
```python
# 添加重连逻辑
async def call_hindsight_with_retry(query, max_retries=3):
    for attempt in range(max_retries):
        try:
            client = get_hindsight_client()
            return await client.arecall(query)
        except ConnectionError:
            logger.warning("Hindsight 连接失败，尝试重连 (%d/%d)", attempt+1, max_retries)
            await reset_hindsight_client()
            continue
        except Exception as e:
            logger.error("Hindsight 调用失败: %s", e)
            return []
    return []
```

**影响**：P3（长期规划）

---

### 2.6 性能与资源

#### 问题 11：延迟队列没有大小限制

**现状**：`add_to_delay_queue()` 有队列大小限制，但检查逻辑有问题

**问题**：
- 队列大小限制是软限制，超过时只是移除最旧的
- 如果念头生成速度大于消费速度，队列会一直满

**改进方案**：
```python
# 硬限制 + 拒绝策略
def add_to_delay_queue_v2(content, thought_type, score, emotion_state):
    thoughts = get_delayed_thoughts()
    max_queue_size = get_config("delay.max_queue_size", 10)
    
    # 硬限制：队列满时拒绝新念头
    if len(thoughts) >= max_queue_size:
        logger.warning("延迟队列已满，拒绝新念头: %s", content[:50])
        return False
    
    # 添加新念头
    new_thought = DelayedThought(...)
    thoughts.append(new_thought)
    save_delayed_thoughts(thoughts)
    return True
```

**影响**：P2（中期改进）

---

#### 问题 12：心跳日志没有清理机制

**现状**：心跳日志会无限增长

**问题**：
- 长期运行会占用大量数据库空间
- 查询日志会越来越慢

**改进方案**：
```python
# 定期清理旧日志
def cleanup_old_logs(days_to_keep=30):
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    
    with active_engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM active_heartbeat_logs 
            WHERE created_at < :cutoff
        """), {"cutoff": cutoff_date})
        conn.commit()
```

**影响**：P2（中期改进）

---

## 三、优先级排序

| 优先级 | 问题 | 影响 | 改进方案 |
|--------|------|------|----------|
| P0 | 延迟队列没有过期机制 | 过时念头被发送 | 添加时间过期检查 |
| P0 | LLM 调用失败降级不完善 | 情绪评估不准 | 完善异常处理和 fallback |
| P1 | 情绪状态持久化时机不明确 | 情绪状态过时 | 消息处理后立即保存 |
| P1 | 配置变更没有实时生效 | 用户体验差 | 配置变更时重启调度器 |
| P1 | 缺少配置验证 | 无效配置导致异常 | 添加配置验证逻辑 |
| P1 | 情绪状态与日志不一致 | 数据不一致 | 调整保存顺序 |
| P2 | 情绪演化权重固定 | 情绪波动大 | 动态权重调整 |
| P2 | 念头类型判断逻辑简单 | 念头类型不准确 | 更智能的判断逻辑 |
| P2 | 延迟队列大小限制软限制 | 队列积压 | 硬限制 + 拒绝策略 |
| P2 | 心跳日志没有清理机制 | 数据库膨胀 | 定期清理旧日志 |
| P3 | 延迟队列状态没有同步到前端 | 前端显示不准 | 实时计算队列数量 |
| P3 | Hindsight 客户端没有重连机制 | 服务重启后失败 | 添加重连逻辑 |

---

## 四、实施建议

### 4.1 立即修复（P0）

1. **延迟队列过期机制**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`reevaluate_delayed_thoughts()`
   - 添加 `is_thought_expired()` 函数

2. **LLM 调用降级完善**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`evaluate_emotion_with_llm()`
   - 添加 `call_llm_with_fallback()` 包装函数

### 4.2 短期优化（P1）

1. **情绪持久化时机**
   - 修改文件：`backend/services/message_service.py`
   - 添加 `on_message_sent()` 钩子

2. **配置实时生效**
   - 修改文件：`backend/routers/config.py`
   - 修改函数：`update_config()`
   - 添加调度器重启逻辑

3. **配置验证**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 添加 `validate_config()` 函数

4. **情绪与日志一致性**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`run_heartbeat()`
   - 调整保存顺序

### 4.3 中期改进（P2）

1. **动态权重调整**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`merge_emotion()`
   - 添加置信度参数

2. **念头类型判断优化**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`determine_thought_type()`

3. **延迟队列硬限制**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`add_to_delay_queue()`

4. **日志清理机制**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 添加 `cleanup_old_logs()` 函数
   - 在心跳调度器中添加定期清理任务

### 4.4 长期规划（P3）

1. **延迟队列状态同步**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`get_status()`

2. **Hindsight 重连机制**
   - 修改文件：`backend/services/active_consciousness_service.py`
   - 修改函数：`get_hindsight_client()`
   - 添加 `reset_hindsight_client()` 函数

---

## 五、验收标准

### 5.1 P0 修复验收

- [ ] 延迟队列中的念头超过 4 小时自动丢弃
- [ ] LLM 调用失败时有明确的 fallback 逻辑
- [ ] LLM 失败次数和原因被记录到日志

### 5.2 P1 优化验收

- [ ] 用户发送消息后，情绪状态立即更新
- [ ] 配置修改后，心跳调度器立即重启
- [ ] 无效配置被拒绝并返回错误信息
- [ ] 心跳日志中的情绪值与实际保存的一致

### 5.3 P2 改进验收

- [ ] 情绪合并权重根据 LLM 置信度动态调整
- [ ] 念头类型判断考虑更多因素（时间、沉默时长、情绪）
- [ ] 延迟队列满时拒绝新念头
- [ ] 30 天前的心跳日志被自动清理

### 5.4 P3 规划验收

- [ ] 前端显示的延迟队列数量准确
- [ ] Hindsight 服务重启后能自动重连

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 动态权重导致情绪不稳定 | 行为不可预测 | 设置边界值，添加日志 |
| 配置验证过严 | 用户无法保存配置 | 提供默认值和建议 |
| 日志清理导致数据丢失 | 无法追溯历史 | 保留清理日志，支持手动触发 |
| 延迟队列拒绝策略过于严格 | 念头丢失 | 记录拒绝原因，支持手动重试 |

---

**最后更新**：2026-06-18
**版本**：v1.0
**状态**：待审核
