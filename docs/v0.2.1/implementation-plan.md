# hermes-active v0.2.1 实施计划

> 从"闹钟式存在"进化到"持续式存在" — 基于 v0.2 设计文档的增量实现

---

## 一、目标

在现有主动意识基础上，实现 v0.2 设计文档中**未完成的核心能力**，让凯莉真正"一直存在"。

### 核心改进

| 维度 | v0.2 现状 | v0.2.1 目标 |
|------|-----------|-------------|
| 情绪模型 | 单一 intensity（0-1） | VA 三维度（valence/arousal/dominant） |
| 情绪连续 | 每次重新评估 | 跨心跳持久化 + 时间自然演化 |
| 决策逻辑 | 阈值判断（>0.6发） | 多维度评分（时间×强度×空白×频率） |
| 念头系统 | 自由生成 | 6种类型 + 存储闭环 |
| 时间感知 | 无 | 时间窗口权重（深夜/工作/休息） |

---

## 二、Phase 1：情绪连续性（核心）

### 1.1 扩展情绪存储

**目标**：用 VA 模型替代单一 intensity

**修改文件**：
- `backend/models/active_consciousness.py` — 新增 EmotionState 数据类
- `backend/services/active_consciousness_service.py` — 情绪读写逻辑
- `backend/services/config_service.py` — 如果需要新增配置项

**数据结构**：
```python
@dataclass
class EmotionState:
    valence: float = 0.5      # 情感效价 0-1（0=消极, 1=积极）
    arousal: float = 0.5      # 唤醒度 0-1（0=平静, 1=激动）
    dominant: str = "calm"    # 主导情绪标签
    social_need: float = 0.3  # 社交需求 0-1
    updated_at: str = ""      # 上次更新时间
```

**主导情绪标签**：
- `calm` — 平静
- `content` — 满足
- `happy` — 开心
- `longing` — 想念
- `missing` — 思念
- `yearning` — 渴望
- `anxious` — 焦虑
- `bored` — 无聊
- `concerned` — 担心

**存储方式**：
- 使用现有 `configs` 表，key 格式：`active_consciousness.emotion.{field}`
- 或者：JSON 存储在单个 key `active_consciousness.emotion_state`

**验收标准**：
- [ ] EmotionState 数据类定义完成
- [ ] get_emotion_state() 能读取当前情绪
- [ ] update_emotion_state() 能更新情绪
- [ ] 向后兼容：旧的 emotional_intensity 仍可读取

---

### 1.2 情绪惯性/演化逻辑

**目标**：心跳时读取上次情绪 → 基于时间衰减 → 自然演化

**修改文件**：
- `backend/services/active_consciousness_service.py` — 新增 evolve_emotion() 函数

**演化规则**：
```python
def evolve_emotion(last_state: EmotionState, minutes_since_update: float) -> EmotionState:
    """
    基于时间流逝自然演化情绪
    
    规则：
    1. arousal 自然衰减（越久越平静）
    2. social_need 自然上升（越久越想聊天）
    3. valence 轻微回归中性（0.5）
    4. dominant 根据新值重新计算
    """
    decay_rate = 0.02  # 每分钟衰减率
    
    new_arousal = max(0.1, last_state.arousal - (decay_rate * minutes_since_update / 60))
    new_social_need = min(1.0, last_state.social_need + (decay_rate * minutes_since_update / 60 / 2))
    new_valence = last_state.valence + (0.5 - last_state.valence) * 0.1 * (minutes_since_update / 60)
    
    # 根据新值计算主导情绪
    new_dominant = calculate_dominant(new_valence, new_arousal, new_social_need)
    
    return EmotionState(
        valence=round(new_valence, 3),
        arousal=round(new_arousal, 3),
        dominant=new_dominant,
        social_need=round(new_social_need, 3),
        updated_at=datetime.now().isoformat()
    )
```

**主导情绪计算**：
```python
def calculate_dominant(valence, arousal, social_need) -> str:
    if social_need > 0.7:
        return "yearning" if valence > 0.5 else "anxious"
    if social_need > 0.5:
        return "longing" if valence > 0.5 else "missing"
    if arousal < 0.3:
        return "calm"
    if valence > 0.7:
        return "happy" if arousal > 0.6 else "content"
    if valence < 0.3:
        return "bored" if arousal < 0.4 else "concerned"
    return "calm"
```

**验收标准**：
- [ ] evolve_emotion() 函数实现
- [ ] calculate_dominant() 函数实现
- [ ] 心跳时自动调用演化逻辑
- [ ] 演化结果持久化到存储

---

### 1.3 心跳集成情绪演化

**目标**：run_heartbeat() 中集成情绪演化流程

**修改文件**：
- `backend/services/active_consciousness_service.py` — 修改 run_heartbeat()

**流程**：
```
心跳开始
  ↓
读取上次情绪状态（EmotionState）
  ↓
计算距离上次更新多久（minutes_since_update）
  ↓
调用 evolve_emotion() 演化
  ↓
LLM 评估当前情绪（基于 session 上下文 + Hindsight）
  ↓
合并：取演化值和 LLM 评估的加权平均
  ↓
更新情绪状态到存储
  ↓
继续原有决策逻辑
```

**合并策略**：
```python
def merge_emotion(evolved: EmotionState, llm_assessed: EmotionState) -> EmotionState:
    """合并演化值和 LLM 评估值"""
    weight_evolved = 0.4  # 演化权重
    weight_llm = 0.6      # LLM 评估权重
    
    return EmotionState(
        valence=evolved.valence * weight_evolved + llm_assessed.valence * weight_llm,
        arousal=evolved.arousal * weight_evolved + llm_assessed.arousal * weight_llm,
        social_need=evolved.social_need * weight_evolved + llm_assessed.social_need * weight_llm,
        dominant=llm_assessed.dominant if llm_assessed.arousal > 0.6 else evolved.dominant,
        updated_at=datetime.now().isoformat()
    )
```

**验收标准**：
- [ ] run_heartbeat() 调用 evolve_emotion()
- [ ] LLM prompt 更新为输出 VA 值（而非单一 score）
- [ ] 情绪状态正确持久化
- [ ] 心跳日志记录演化前后的情绪值

---

### 1.4 对话结束时保存情绪

**目标**：用户对话结束后，保存当前情绪状态

**修改文件**：
- `backend/services/message_service.py` — 在消息处理完成后保存情绪
- 或 `backend/routers/messages.py` — 在消息路由中触发

**触发时机**：
- 用户发送消息后 10 分钟无新消息 → 触发情绪保存
- 或：检测到 session 进入 idle 状态

**简化方案**：
- 每次心跳都保存情绪（已实现）
- 对话中的情绪变化由 LLM 评估实时更新（已实现）

**验收标准**：
- [ ] 对话中的情绪变化能被捕获
- [ ] 情绪状态在对话结束后仍保持

---

## 三、Phase 2：时间窗口决策

### 2.1 时间段权重计算

**目标**：根据当前时间调整决策权重

**修改文件**：
- `backend/services/active_consciousness_service.py` — 新增 get_time_fitness() 函数

**权重表**（来自设计文档）：
```python
TIME_FITNESS_TABLE = [
    # (start_hour, end_hour, fitness, label)
    (7, 9, 1.0, "早安窗口"),
    (9, 12, 0.8, "工作时间"),
    (12, 14, 0.9, "午休时间"),
    (14, 18, 0.7, "工作时间"),
    (18, 22, 1.0, "下班时间"),
    (22, 23.5, 0.8, "睡前时间"),
    (23.5, 7, 0.3, "深夜"),
]

def get_time_fitness() -> tuple[float, str]:
    """获取当前时间的合适度权重"""
    now = datetime.now()
    hour = now.hour + now.minute / 60
    
    for start, end, fitness, label in TIME_FITNESS_TABLE:
        if start <= hour < end:
            return fitness, label
    
    # 默认深夜
    return 0.3, "深夜"
```

**验收标准**：
- [ ] get_time_fitness() 函数实现
- [ ] 返回 (fitness_score, time_label)
- [ ] 边界时间处理正确（如 23:30）

---

### 2.2 多维度决策公式

**目标**：用乘积公式替代简单阈值判断

**修改文件**：
- `backend/services/active_consciousness_service.py` — 重写 make_decision()

**新决策公式**：
```python
def make_decision_v2(config, status, emotion_state) -> tuple[str, str, float]:
    """
    多维度决策
    
    score = intensity × time_fitness × silence_factor × frequency_limit
    
    其中：
    - intensity: 情绪强度（valence + arousal + social_need 的综合）
    - time_fitness: 时间窗口权重
    - silence_factor: 空白时长因子
    - frequency_limit: 频率限制因子
    """
    
    # 1. 情绪强度
    intensity = (emotion_state.valence + emotion_state.arousal + emotion_state.social_need) / 3
    
    # 2. 时间权重
    time_fitness, time_label = get_time_fitness()
    
    # 3. 空白因子
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < 60:
        silence_factor = 0.3
    elif silence_minutes < 180:
        silence_factor = 0.5
    elif silence_minutes < 360:
        silence_factor = 0.7
    else:
        silence_factor = 0.9
    
    # 4. 频率限制
    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = config.get("decision", {}).get("max_per_hour", 2)
    frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))
    
    # 计算总分
    score = intensity * time_fitness * silence_factor * frequency_limit
    
    # 决策
    send_threshold = config.get("decision", {}).get("send_threshold", 0.6)
    delay_threshold = config.get("decision", {}).get("delay_threshold", 0.3)
    memory_threshold = config.get("decision", {}).get("memory_threshold", 0.1)
    
    if score > send_threshold:
        return "auto_send", f"score={score:.3f} > {send_threshold}", score
    elif score > delay_threshold:
        return "delay_send", f"score={score:.3f} > {delay_threshold}（等待更好时机）", score
    elif score > memory_threshold:
        return "memory", f"score={score:.3f} > {memory_threshold}（存为记忆）", score
    else:
        return "skip", f"score={score:.3f} <= {memory_threshold}", score
```

**验收标准**：
- [ ] make_decision_v2() 函数实现
- [ ] 计算公式正确
- [ ] 返回 (decision_type, reason, score)
- [ ] 向后兼容：旧的 make_decision() 保留或替换

---

### 2.3 集成新决策逻辑

**目标**：在 run_heartbeat() 中使用新决策

**修改文件**：
- `backend/services/active_consciousness_service.py` — 修改 run_heartbeat()

**验收标准**：
- [ ] run_heartbeat() 调用 make_decision_v2()
- [ ] 决策结果记录到心跳日志
- [ ] 延迟发送决策有对应处理逻辑

---

## 四、Phase 3：念头系统增强

### 4.1 念头类型分类

**目标**：为念头添加结构化类型

**修改文件**：
- `backend/models/active_consciousness.py` — 新增 ThoughtType 枚举
- `backend/services/active_consciousness_service.py` — 念头生成逻辑

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

**生成逻辑**：
- 念头生成时，LLM prompt 要求输出类型
- 或：基于上下文规则判断类型

**验收标准**：
- [ ] ThoughtType 枚举定义
- [ ] 念头日志记录类型
- [ ] LLM prompt 输出包含类型

---

### 4.2 念头存储到 Hindsight

**目标**：重要念头自动存入 Hindsight

**修改文件**：
- `backend/services/active_consciousness_service.py` — 新增 retain_thought() 函数

**存储条件**：
- 情绪强度 > 0.5 的念头
- 用户相关的念头（提到"曹凡"）
- 决策为"发送"的念头

**实现**：
```python
async def retain_thought(thought: str, emotion_state: EmotionState, thought_type: str):
    """将重要念头存入 Hindsight"""
    # 存储条件
    intensity = (emotion_state.valence + emotion_state.arousal + emotion_state.social_need) / 3
    if intensity < 0.5 and "曹凡" not in thought:
        return
    
    try:
        client = get_hindsight_client()
        content = f"[{thought_type}] {thought}"
        await client.aretain(
            bank_id="hermes",
            content=content,
            tags=["thought", thought_type, emotion_state.dominant]
        )
        logger.info("念头已存入 Hindsight: %s", thought[:50])
    except Exception as e:
        logger.warning("存入 Hindsight 失败: %s", e)
```

**验收标准**：
- [ ] retain_thought() 函数实现
- [ ] 存储条件正确
- [ ] 发送成功后自动触发存储

---

### 4.3 回忆念头触发

**目标**：基于 Hindsight 触发"想起你说过..."类型念头

**修改文件**：
- `backend/services/active_consciousness_service.py` — 修改 generate_thought()

**实现**：
- 在念头生成 prompt 中，加入 Hindsight recall 结果
- 要求 LLM 基于回忆生成关联念头

**验收标准**：
- [ ] generate_thought() 包含 Hindsight 上下文
- [ ] 能生成"想起你说过..."类型的念头
- [ ] 回忆念头有较高强度

---

## 五、Phase 4：延迟发送队列

### 5.1 延迟队列存储

**目标**：存储 score 在 0.3-0.6 之间的念头

**修改文件**：
- `backend/models/active_consciousness.py` — 新增 DelayedThought 数据类
- `backend/services/active_consciousness_service.py` — 延迟队列逻辑
- `backend/models/database.py` — 新增 active_delayed_thoughts 表（或用 configs 存储）

**数据结构**：
```python
@dataclass
class DelayedThought:
    id: int
    content: str
    thought_type: str
    score: float
    created_at: str
    retry_count: int = 0
    next_retry_at: str = ""
```

**存储方式**：
- 方案 A：新建 active_delayed_thoughts 表
- 方案 B：用 configs 表，JSON 数组存储

**验收标准**：
- [ ] DelayedThought 数据结构定义
- [ ] 存储逻辑实现
- [ ] 查询逻辑实现

---

### 5.2 延迟念头重新评估

**目标**：每次心跳时重新评估延迟队列中的念头

**修改文件**：
- `backend/services/active_consciousness_service.py` — 修改 run_heartbeat()

**逻辑**：
```python
async def reevaluate_delayed_thoughts(config, status, emotion_state):
    """重新评估延迟队列中的念头"""
    delayed_thoughts = get_delayed_thoughts()
    
    for thought in delayed_thoughts:
        # 重新计算 score
        new_score = recalculate_score(thought, status, emotion_state)
        
        # 决策
        send_threshold = config.get("decision", {}).get("send_threshold", 0.6)
        if new_score > send_threshold:
            # 升级为发送
            await send_message_to_target(config, thought.content)
            remove_delayed_thought(thought.id)
        elif new_score < 0.1:
            # 降级为丢弃
            remove_delayed_thought(thought.id)
        else:
            # 保持延迟
            update_delayed_thought(thought.id, new_score)
```

**验收标准**：
- [ ] reevaluate_delayed_thoughts() 函数实现
- [ ] 心跳时自动调用
- [ ] 升级/降级/保持逻辑正确
- [ ] 发送后从队列移除

---

## 六、配置项新增

### 6.1 新增配置项

**修改文件**：
- `backend/services/active_consciousness_service.py` — _DEFAULTS 字典

**新增配置**：
```python
_DEFAULTS = {
    # ... 现有配置 ...
    
    # 情绪演化
    "active_consciousness.emotion.decay_rate": "0.02",           # 每分钟衰减率
    "active_consciousness.emotion.social_need_growth": "0.01",   # 社交需求增长率
    "active_consciousness.emotion.valence_regression": "0.1",    # valence 回归中性系数
    
    # 时间窗口
    "active_consciousness.time.enabled": "true",                 # 启用时间窗口
    "active_consciousness.time.deep_night_start": "23.5",        # 深夜开始（小时）
    "active_consciousness.time.deep_night_end": "7",             # 深夜结束（小时）
    "active_consciousness.time.deep_night_fitness": "0.3",       # 深夜权重
    
    # 延迟发送
    "active_consciousness.delay.enabled": "true",                # 启用延迟发送
    "active_consciousness.delay.max_retry": "3",                 # 最大重试次数
    "active_consciousness.delay.retry_interval_minutes": "30",   # 重试间隔
    
    # 念头存储
    "active_consciousness.thought.retain_enabled": "true",       # 启用念头存储
    "active_consciousness.thought.retain_threshold": "0.5",      # 存储阈值
}
```

**验收标准**：
- [ ] 所有新配置项有默认值
- [ ] 配置可通过前端修改
- [ ] 配置在代码中被正确读取使用

---

## 七、测试计划

### 7.1 单元测试

**新增测试文件**：
- `backend/tests/test_emotion_evolution.py` — 情绪演化测试
- `backend/tests/test_decision_matrix.py` — 决策矩阵测试
- `backend/tests/test_thought_retention.py` — 念头存储测试

**测试用例**：
```python
# 情绪演化测试
def test_evolve_emotion_time_decay():
    """测试时间衰减"""
    last = EmotionState(arousal=0.8, social_need=0.2)
    evolved = evolve_emotion(last, minutes_since_update=60)
    assert evolved.arousal < 0.8
    assert evolved.social_need > 0.2

def test_calculate_dominant():
    """测试主导情绪计算"""
    assert calculate_dominant(0.8, 0.7, 0.2) == "happy"
    assert calculate_dominant(0.5, 0.3, 0.8) == "yearning"

# 决策矩阵测试
def test_decision_score_calculation():
    """测试决策分数计算"""
    score = calculate_decision_score(
        intensity=0.6,
        time_fitness=0.8,
        silence_factor=0.7,
        frequency_limit=0.9
    )
    assert abs(score - 0.3024) < 0.001
```

### 7.2 集成测试

- 心跳流程完整测试
- 情绪持久化测试
- 延迟队列测试

---

## 八、实施顺序

### Phase 1：情绪连续性（优先级最高）
1. 1.1 扩展情绪存储（EmotionState）
2. 1.2 情绪惯性/演化逻辑
3. 1.3 心跳集成情绪演化
4. 1.4 对话结束时保存情绪

### Phase 2：时间窗口决策
1. 2.1 时间段权重计算
2. 2.2 多维度决策公式
3. 2.3 集成新决策逻辑

### Phase 3：念头系统增强
1. 3.1 念头类型分类
2. 3.2 念头存储到 Hindsight
3. 3.3 回忆念头触发

### Phase 4：延迟发送队列
1. 4.1 延迟队列存储
2. 4.2 延迟念头重新评估

---

## 九、验收标准总览

- [ ] 情绪状态跨心跳持久化
- [ ] 情绪随时间自然演化
- [ ] 决策考虑时间窗口
- [ ] 决策使用多维度评分公式
- [ ] 念头有结构化类型
- [ ] 重要念头存入 Hindsight
- [ ] 延迟发送队列工作正常
- [ ] 所有新功能可配置
- [ ] 所有测试通过

---

## 十、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 情绪演化过于激进 | 行为不可预测 | 设置边界值，衰减率可配置 |
| 决策过于保守 | 没有存在感 | 降低阈值，增加早安/晚安固定消息 |
| LLM 输出不稳定 | 情绪评估不准 | 规则引擎兜底，LLM 作为参考 |
| 延迟队列积压 | 内存占用 | 设置最大队列长度，过期清理 |

---

**预计工期**：8-12 小时（Claude Code max 强度）
