# hermes-active v0.2.1 实现状态

> 主动意识模块功能细化 - 实现情况总结

---

## 一、功能实现总览

| Phase | 功能模块 | 状态 | 说明 |
|-------|---------|------|------|
| Phase 1 | 情绪连续性 | ✅ 已完成 | VA 模型、情绪演化、心跳集成 |
| Phase 2 | 时间窗口决策 | ✅ 已完成 | 时间权重、多维度决策公式 |
| Phase 3 | 念头系统增强 | ✅ 已完成 | 类型分类、Hindsight 存储 |
| Phase 4 | 延迟发送队列 | ✅ 已完成 | 队列存储、重新评估 |

---

## 二、Phase 1：情绪连续性

### 2.1 扩展情绪存储 ✅

**实现文件**：
- `backend/models/active_consciousness.py` — `EmotionState` 数据类
- `backend/services/active_consciousness_service.py` — `get_emotion_state()` / `update_emotion_state()`

**数据结构**：
```python
class EmotionState:
    valence: float = 0.5       # 情感效价 0-1
    arousal: float = 0.3       # 唤醒度 0-1
    dominant: str = "calm"     # 主导情绪标签
    social_need: float = 0.3   # 社交需求 0-1
    updated_at: str = ""       # 上次更新时间
```

**主导情绪标签**：calm, content, happy, longing, missing, yearning, anxious, bored, concerned

**验收标准**：
- [x] EmotionState 数据类定义完成
- [x] get_emotion_state() 能读取当前情绪
- [x] update_emotion_state() 能更新情绪
- [x] 向后兼容：旧的 emotional_intensity 仍可读取

---

### 2.2 情绪惯性/演化逻辑 ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `evolve_emotion()` 函数

**演化规则**：
1. arousal 自然衰减（越久越平静）
2. social_need 自然上升（越久越想聊天）
3. valence 轻微回归中性（0.5）

**配置项**：
```python
"active_consciousness.emotion.decay_rate": "0.02",           # 每分钟衰减率
"active_consciousness.emotion.social_need_growth": "0.01",   # 社交需求增长率
"active_consciousness.emotion.valence_regression": "0.1",    # valence 回归中性系数
```

**验收标准**：
- [x] evolve_emotion() 函数实现
- [x] calculate_dominant() 函数实现
- [x] 心跳时自动调用演化逻辑
- [x] 演化结果持久化到存储

---

### 2.3 心跳集成情绪演化 ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `run_heartbeat()` 函数

**流程**：
1. 读取上次情绪状态（EmotionState）
2. 计算距离上次更新多久（minutes_since_update）
3. 调用 evolve_emotion() 演化
4. LLM 评估当前情绪（基于 session 上下文 + Hindsight）
5. 合并：取演化值和 LLM 评估的加权平均（40% 演化 + 60% LLM）
6. 更新情绪状态到存储

**验收标准**：
- [x] run_heartbeat() 调用 evolve_emotion()
- [x] LLM prompt 更新为输出 VA 值
- [x] 情绪状态正确持久化
- [x] 心跳日志记录演化前后的情绪值

---

### 2.4 对话结束时保存情绪 ✅

**实现方式**：
- 每次心跳都保存情绪
- 对话中的情绪变化由 LLM 评估实时更新

**验收标准**：
- [x] 对话中的情绪变化能被捕获
- [x] 情绪状态在对话结束后仍保持

---

## 三、Phase 2：时间窗口决策

### 3.1 时间段权重计算 ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `get_time_fitness()` 函数

**权重表**：
| 时间段 | 权重 | 标签 |
|--------|------|------|
| 7:00-9:00 | 1.0 | 早安窗口 |
| 9:00-12:00 | 0.8 | 工作时间 |
| 12:00-14:00 | 0.9 | 午休时间 |
| 14:00-18:00 | 0.7 | 工作时间 |
| 18:00-22:00 | 1.0 | 下班时间 |
| 22:00-23:30 | 0.8 | 睡前时间 |
| 23:30-7:00 | 0.3 | 深夜 |

**验收标准**：
- [x] get_time_fitness() 函数实现
- [x] 返回 (fitness_score, time_label)
- [x] 边界时间处理正确

---

### 3.2 多维度决策公式 ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `make_decision_v2()` 函数

**决策公式**：
```
score = intensity × time_fitness × silence_factor × frequency_limit
```

**因子说明**：
- intensity：情绪强度（valence + arousal + social_need 的综合）
- time_fitness：时间窗口权重
- silence_factor：空白时长因子（越久没聊天分越高）
- frequency_limit：频率限制因子（超频归零）

**决策阈值**：
- send_threshold > 0.6：立即发送
- delay_threshold > 0.3：延迟发送
- memory_threshold > 0.1：存为记忆
- ≤ 0.1：跳过

**验收标准**：
- [x] make_decision_v2() 函数实现
- [x] 计算公式正确
- [x] 返回 (decision_type, reason, score)
- [x] 向后兼容

---

### 3.3 集成新决策逻辑 ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `run_heartbeat()` 函数

**验收标准**：
- [x] run_heartbeat() 调用 make_decision_v2()
- [x] 决策结果记录到心跳日志
- [x] 延迟发送决策有对应处理逻辑

---

## 四、Phase 3：念头系统增强

### 4.1 念头类型分类 ✅

**实现文件**：
- `backend/models/active_consciousness.py` — `ThoughtType` 枚举

**类型定义**：
```python
class ThoughtType(str, Enum):
    TIME = "time"           # 时间念头："23:30了，该睡了"
    SILENCE = "silence"     # 空白念头："好久没说话了"
    ASSOCIATION = "assoc"   # 关联念头："今天周五，一般加班"
    MEMORY = "memory"       # 回忆念头："想起你说过..."
    EMOTION = "emotion"     # 情绪念头："现在有点兴奋"
    ENVIRONMENT = "env"     # 环境念头："外面下雨了"
```

**验收标准**：
- [x] ThoughtType 枚举定义
- [x] 念头日志记录类型
- [x] LLM prompt 输出包含类型

---

### 4.2 念头存储到 Hindsight ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `retain_thought_to_hindsight()` 函数

**存储条件**：
1. 情绪强度 > retain_threshold
2. 包含用户名字（如"曹凡"）
3. 分数 > retain_threshold

**标签设计**：
- "thought"：固定标签
- thought_type：念头类型
- emotion_state.dominant：当前主导情绪
- "active_consciousness"：来源标识

**验收标准**：
- [x] retain_thought_to_hindsight() 函数实现
- [x] 存储条件正确
- [x] 发送成功后自动触发存储

---

### 4.3 回忆念头触发 ✅

**实现方式**：
- 在念头生成 prompt 中加入 Hindsight recall 结果
- LLM 基于回忆生成关联念头

**验收标准**：
- [x] generate_thought() 包含 Hindsight 上下文
- [x] 能生成"想起你说过..."类型的念头
- [x] 回忆念头有较高强度

---

## 五、Phase 4：延迟发送队列

### 5.1 延迟队列存储 ✅

**实现文件**：
- `backend/models/active_consciousness.py` — `DelayedThought` 数据类
- `backend/services/active_consciousness_service.py` — 队列操作函数

**数据结构**：
```python
class DelayedThought:
    id: int
    content: str
    thought_type: str
    score: float
    created_at: str
    retry_count: int = 0
    next_retry_at: str = ""
    emotion_snapshot: dict = {}
```

**存储方式**：使用 configs 表，JSON 数组存储

**验收标准**：
- [x] DelayedThought 数据结构定义
- [x] 存储逻辑实现
- [x] 查询逻辑实现

---

### 5.2 延迟念头重新评估 ✅

**实现文件**：
- `backend/services/active_consciousness_service.py` — `reevaluate_delayed_thoughts()` 函数

**逻辑**：
1. 每次心跳时重新评估延迟队列中的念头
2. 重新计算 score
3. score > send_threshold → 升级为发送
4. score < 0.1 → 降级为丢弃
5. 否则保持延迟

**验收标准**：
- [x] reevaluate_delayed_thoughts() 函数实现
- [x] 心跳时自动调用
- [x] 升级/降级/保持逻辑正确
- [x] 发送后从队列移除

---

## 六、配置项

### 6.1 已实现的配置项 ✅

```python
# 情绪演化
"active_consciousness.emotion.decay_rate": "0.02"
"active_consciousness.emotion.social_need_growth": "0.01"
"active_consciousness.emotion.valence_regression": "0.1"
"active_consciousness.emotion.weight_evolved": "0.4"
"active_consciousness.emotion.weight_llm": "0.6"

# 时间窗口
"active_consciousness.time.enabled": "true"
"active_consciousness.time.deep_night_start": "23.5"
"active_consciousness.time.deep_night_end": "7"
"active_consciousness.time.deep_night_fitness": "0.3"

# 延迟发送
"active_consciousness.delay.enabled": "true"
"active_consciousness.delay.max_retry": "3"
"active_consciousness.delay.retry_interval_minutes": "30"
"active_consciousness.delay.max_queue_size": "10"

# 念头存储
"active_consciousness.thought.retain_enabled": "false"
"active_consciousness.thought.retain_threshold": "0.5"
```

---

## 七、前端实现

### 7.1 状态面板 ✅

**实现文件**：`frontend/src/views/ActiveConsciousness.vue`

**展示内容**：
- 心跳状态（绿/红呼吸灯）
- 想念分数（进度条）
- 聊天热度（进度条）
- 情绪值（进度条）
- 今日/本小时发送数

### 7.2 日志面板 ✅

**展示内容**：
- 心跳日志（表格 + 详情弹窗）
- 念头日志（表格 + 详情弹窗）
- 按日期筛选

### 7.3 配置面板 ✅

**配置项**：
- LLM 配置（模式、Provider、Model、API Key）
- 心跳配置（间隔、发送标记、时间格式）
- Session 来源配置
- 决策阈值配置
- 通知目标配置

### 7.4 详情弹窗 ✅

**展示内容**：
- 情绪演化流程（初始 → 演化 → LLM → 合并）
- 决策计算详情
- Hindsight 召回内容
- 念头生成详情
- 消息发送详情
- 延迟队列重评估
- 情绪评估 LLM 调用

---

## 八、API 接口

### 8.1 已实现的接口 ✅

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/active-consciousness/config` | GET | 获取配置 |
| `/api/active-consciousness/config` | PUT | 更新配置 |
| `/api/active-consciousness/status` | GET | 获取状态 |
| `/api/active-consciousness/heartbeats` | GET | 心跳日志列表 |
| `/api/active-consciousness/thoughts` | GET | 念头日志列表 |
| `/api/active-consciousness/test/llm-connect` | POST | LLM 连通性测试 |
| `/api/active-consciousness/test/thought` | POST | 想法生成测试 |
| `/api/active-consciousness/test/session-context` | POST | Session 上下文测试 |

---

## 九、技术债务与待优化项

### 9.1 已知问题

1. **情绪演化过于激进**：衰减率可能需要根据实际使用调整
2. **LLM 输出不稳定**：情绪评估可能不准确，需要规则引擎兜底
3. **延迟队列积压**：需要定期清理过期念头

### 9.2 待优化项

1. **情绪可视化**：添加情绪趋势图表
2. **世界状态**：实现 v0.2 设计中的 World State 功能
3. **每日种子**：实现 Daily Seed 自动生成日程
4. **单元测试**：补充核心逻辑的单元测试

---

## 十、验收总结

### 已完成 ✅

- [x] 情绪状态跨心跳持久化
- [x] 情绪随时间自然演化
- [x] 决策考虑时间窗口
- [x] 决策使用多维度评分公式
- [x] 念头有结构化类型
- [x] 重要念头存入 Hindsight
- [x] 延迟发送队列工作正常
- [x] 所有新功能可配置
- [x] 前端界面完整
- [x] 详情弹窗展示完整

### 待完成

- [ ] 单元测试覆盖核心逻辑
- [ ] 世界状态功能（v0.2 设计）
- [ ] 每日种子功能（v0.2 设计）
- [ ] 情绪趋势可视化

---

**最后更新**：2026-06-18
**版本**：v0.2.1
