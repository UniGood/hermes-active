# v0.2.1 开发任务

## 目标
基于 docs/v0.2.1/implementation-plan.md 实施 hermes-active 主动意识升级。

## 核心原则
1. **增量开发**：不破坏现有功能，向后兼容
2. **配置优先**：所有阈值可配置，不硬编码
3. **测试验证**：每个 Phase 完成后运行测试

## Phase 1：情绪连续性（最高优先级）

### Task 1.1：扩展情绪存储
- 文件：`backend/models/active_consciousness.py`
- 新增 `EmotionState` 数据类（valence, arousal, dominant, social_need, updated_at）
- 文件：`backend/services/active_consciousness_service.py`
- 新增 `get_emotion_state()` 和 `update_emotion_state()` 函数
- 存储使用 configs 表，key: `active_consciousness.emotion_state`（JSON 格式）

### Task 1.2：情绪演化逻辑
- 文件：`backend/services/active_consciousness_service.py`
- 新增 `evolve_emotion(last_state, minutes_since_update)` 函数
- 新增 `calculate_dominant(valence, arousal, social_need)` 函数
- 演化规则：arousal 衰减、social_need 增长、valence 回归中性

### Task 1.3：心跳集成情绪演化
- 文件：`backend/services/active_consciousness_service.py`
- 修改 `run_heartbeat()`：读取上次情绪 → 演化 → LLM 评估 → 合并 → 保存
- LLM prompt 更新为输出 VA 值（valence, arousal, social_need）

## Phase 2：时间窗口决策

### Task 2.1：时间权重计算
- 文件：`backend/services/active_consciousness_service.py`
- 新增 `get_time_fitness()` 函数
- 权重表：早安1.0, 工作0.8, 午休0.9, 下班1.0, 睡前0.8, 深夜0.3

### Task 2.2：多维度决策公式
- 文件：`backend/services/active_consciousness_service.py`
- 新增 `make_decision_v2(config, status, emotion_state)` 函数
- 公式：score = intensity × time_fitness × silence_factor × frequency_limit
- 返回：(decision_type, reason, score)

## Phase 3：念头系统增强

### Task 3.1：念头类型分类
- 文件：`backend/models/active_consciousness.py`
- 新增 `ThoughtType` 枚举（time, silence, assoc, memory, emotion, env）
- 念头日志记录类型

### Task 3.2：念头存储到 Hindsight
- 文件：`backend/services/active_consciousness_service.py`
- 新增 `retain_thought(thought, emotion_state, thought_type)` 函数
- 条件：intensity > 0.5 或包含"曹凡"

## Phase 4：延迟发送队列

### Task 4.1：延迟队列存储
- 使用 configs 表存储延迟念头（JSON 数组）
- 新增 `DelayedThought` 数据结构

### Task 4.2：延迟念头重新评估
- 文件：`backend/services/active_consciousness_service.py`
- 新增 `reevaluate_delayed_thoughts()` 函数
- 心跳时调用，score > 阈值则发送

## 配置项新增

在 `_DEFAULTS` 中添加：
```python
# 情绪演化
"active_consciousness.emotion.decay_rate": "0.02",
"active_consciousness.emotion.social_need_growth": "0.01",
"active_consciousness.emotion.valence_regression": "0.1",

# 时间窗口
"active_consciousness.time.enabled": "true",
"active_consciousness.time.deep_night_fitness": "0.3",

# 延迟发送
"active_consciousness.delay.enabled": "true",
"active_consciousness.delay.max_retry": "3",

# 念头存储
"active_consciousness.thought.retain_enabled": "true",
"active_consciousness.thought.retain_threshold": "0.5",
```

## 验收标准

- [ ] 情绪状态跨心跳持久化
- [ ] 情绪随时间自然演化
- [ ] 决策考虑时间窗口
- [ ] 决策使用多维度评分公式
- [ ] 念头有结构化类型
- [ ] 重要念头存入 Hindsight
- [ ] 延迟发送队列工作正常
- [ ] 所有新功能可配置
- [ ] 现有测试全部通过
- [ ] 新增单元测试覆盖核心逻辑

## 注意事项

1. **不要破坏现有功能**：旧的 emotional_intensity 逻辑保留
2. **配置优先**：所有阈值从 configs 表读取
3. **state.db 只读**：只往 active.db 写数据
4. **向后兼容**：旧 API 保持可用
