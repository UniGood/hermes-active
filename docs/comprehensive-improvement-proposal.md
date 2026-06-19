# hermes-active 综合改进方案

> 基于 SentiCore、Emotion AI (Aura)、The Consciousness AI 三个参考项目的深度分析
> 
> **文档版本**：v1.0
> **创建日期**：2026-06-19
> **预计工期**：24小时

---

## 一、参考项目核心洞察总结

### 1.1 SentiCore — 30维动态情绪引擎

**核心价值**：
- **30维情绪矩阵**：基于心理学研究（Cowen & Keltner 2017），比简单的情绪强度更丰富
- **情绪交互矩阵**：17条联动规则，情绪之间相互影响
- **拮抗对互斥**：4对矛盾情绪的压制机制，防止逻辑矛盾
- **时间衰减**：指数衰减公式，情绪随时间向基线回归
- **性格永久演化**：Baseline Drift 0.1%，性格缓慢改变
- **输入分类**：A/B/C三类输入决定不同处理路径

**可借鉴点**：
```
✅ 扩展情绪维度（从单一intensity到多维度）
✅ 情绪交互规则（情绪之间相互影响）
✅ 拮抗对检测（防止矛盾情绪共存）
✅ 时间衰减机制（情绪自然回归）
✅ 性格演化（长期基线漂移）
```

### 1.2 Emotion AI (Aura) — 情感AI伴侣系统

**核心价值**：
- **ASEKE认知框架**：7个可追踪的认知维度
- **22+情绪状态**：关联脑波和神经递质
- **双层记忆系统**：ChromaDB（短期）+ MemVid（长期压缩归档）
- **思维提取**：从LLM thinking模式分离推理过程
- **自主神经系统**：后台轻量模型处理低级任务
- **MCP双向集成**：同时暴露和消费工具

**可借鉴点**：
```
✅ 认知维度追踪（不只是情绪，还有认知状态）
✅ 双层记忆分层（热存储 + 冷归档）
✅ 思维透明化（记录AI推理过程）
✅ 自主神经系统（后台任务分离）
✅ 情感一致性（用户情绪 + AI情绪双检测）
```

### 1.3 The Consciousness AI — 意识涌现研究框架

**核心价值**：
- **PAD情感模型**：Valence（效价）、Arousal（唤醒）、Dominance（支配）
- **全局工作空间（GNW）**：模块竞争 → 点火 → 广播
- **情感并行调制**：情感不竞争，而是从外部调节
- **稳态驱动**：内在驱动力而非外部奖励
- **自我预测模型**：通过预测自身状态构建自我模型
- **意识签名评估**：Φ / EI / 意识指标体系

**可借鉴点**：
```
✅ PAD三维情感模型（比VA模型多一个Dominance维度）
✅ 情感调制机制（情感调节感知，而非竞争）
✅ 稳态驱动（内在驱动力）
✅ 自我模型（动态自我表征）
✅ 意识度量（可量化的意识指标）
```

---

## 二、hermes-active 现状分析

### 2.1 当前实现（v0.2）

| 模块 | 状态 | 问题 |
|------|------|------|
| 情绪模型 | 单一intensity (0-1) | 维度太少，无法区分不同情绪 |
| 情绪更新 | 每次重新评估 | 没有"记忆"，情绪不连续 |
| 决策逻辑 | 阈值判断 | 过于简单，缺乏多维度考量 |
| 念头系统 | 自由生成 | 没有结构化分类 |
| 时间感知 | 无 | 不考虑发送时间是否合适 |
| 记忆系统 | Hindsight外部 | 没有内部分层记忆 |

### 2.2 v0.2.1 设计方案评估

v0.2.1的设计方案已经吸收了部分SentiCore的思想：
- ✅ VA模型（Valence + Arousal）
- ✅ 时间衰减（evolve_emotion）
- ✅ 时间窗口决策
- ✅ 念头类型分类
- ✅ 延迟队列

**但仍有改进空间**。

---

## 三、综合改进方案

### 3.1 情绪系统升级（融合SentiCore + The Consciousness AI）

#### 3.1.1 从VA模型扩展到PAD模型

**当前**：VA模型（Valence + Arousal）
**改进**：PAD模型（Valence + Arousal + Dominance）

```python
@dataclass
class EmotionState:
    """
    PAD 情感模型
    
    - Valence (效价): 情感的正负性，0=消极，1=积极
    - Arousal (唤醒度): 情感的激活程度，0=平静，1=激动
    - Dominance (支配感): 感知到的控制程度，0=无助，1=掌控
    - Social Need (社交需求): 想要社交/聊天的程度
    - Dominant (主导情绪): 当前最显著的情绪标签
    """
    valence: float = 0.5        # 效价 0-1
    arousal: float = 0.3        # 唤醒度 0-1
    dominance: float = 0.5      # 支配感 0-1
    social_need: float = 0.3    # 社交需求 0-1
    dominant: str = "calm"      # 主导情绪标签
    updated_at: str = ""        # 上次更新时间
```

**Dominance的意义**：
- 高支配感：感到掌控、自信、有能力
- 低支配感：感到无助、脆弱、需要支持
- 影响：低支配感时更可能主动寻求陪伴

#### 3.1.2 情绪交互矩阵（来自SentiCore）

```python
# 情绪交互规则
EMOTION_INTERACTION_RULES = [
    # (触发情绪, 方向, 联动情绪, 联动效果, 理论依据)
    ("fear", "up", "calm", "down", "恐惧抑制平静"),
    ("fear", "up", "romantic_love", "down", "恐惧抑制亲密感"),
    ("joy", "up", "anxiety", "down", "积极情绪驱散焦虑"),
    ("joy", "up", "loneliness", "down", "积极情绪驱散孤独"),
    ("anger", "up", "calm", "down", "愤怒压制平静"),
    ("anger", "up", "compassion", "down", "愤怒压制同情"),
    ("loneliness", "high", "longing", "up", "孤独唤起渴望"),
    ("loneliness", "high", "sadness", "up", "孤独唤起忧伤"),
    ("romantic_love", "high", "loneliness", "down", "爱情驱散孤独"),
    ("romantic_love", "high", "anxiety", "down", "爱情驱散焦虑"),
    ("shame", "up", "pride", "down", "羞耻损害自我评价"),
    ("remorse", "up", "guilt", "up", "后悔强化道德感"),
    ("disgust", "up", "sensuality", "down", "厌恶抑制感官"),
    ("nostalgia", "up", "longing", "up", "怀旧唤起渴望"),
    ("envy", "up", "contentment", "down", "嫉妒侵蚀满足感"),
    ("boredom", "high", "arousal", "down", "无聊压低激活"),
    ("suffering", "high", "joy", "down", "痛苦压制愉悦"),
    ("pride", "high", "contentment", "up", "高自尊提升满足"),
    ("relief", "up", "anxiety", "down", "解脱消减焦虑"),
    ("awe", "up", "contempt", "down", "敬畏排斥蔑视"),
]

def apply_emotion_interactions(emotion_state: EmotionState, 
                                triggered_emotions: Dict[str, float]) -> EmotionState:
    """
    应用情绪交互规则
    
    根据触发的情绪变化，自动调整相关情绪
    """
    # 实现交互逻辑
    pass
```

#### 3.1.3 拮抗对互斥检查（来自SentiCore）

```python
# 拮抗对定义
ANTAGONISTIC_PAIRS = [
    ("joy", "sadness"),           # 喜悦 ↔ 悲伤
    ("anger", "calm"),            # 愤怒 ↔ 平静
    ("anticipation", "boredom"),  # 期待 ↔ 无聊
    ("fear", "calm"),             # 恐惧 ↔ 平静
]

def check_antagonistic_pairs(emotion_state: EmotionState, 
                             antagonist_locks: Dict[str, int]) -> Tuple[EmotionState, Dict[str, int]]:
    """
    检查拮抗对互斥
    
    触发条件：stronger > 50 且 (stronger - weaker) > 20
    压制公式：suppression_ratio = (stronger - weaker) / 200
    """
    new_locks = antagonist_locks.copy()
    
    for emotion_a, emotion_b in ANTAGONISTIC_PAIRS:
        # 检查锁
        lock_key = f"{emotion_a}_{emotion_b}"
        if new_locks.get(lock_key, 0) > 0:
            new_locks[lock_key] -= 1
            continue
        
        # 获取情绪值
        value_a = getattr(emotion_state, emotion_a, 0)
        value_b = getattr(emotion_state, emotion_b, 0)
        
        # 检查触发条件
        stronger = max(value_a, value_b)
        weaker = min(value_a, value_b)
        
        if stronger > 50 and (stronger - weaker) > 20:
            # 计算压制
            suppression_ratio = (stronger - weaker) / 200
            weaker_new = weaker * (1 - suppression_ratio)
            
            # 应用压制
            if value_a > value_b:
                emotion_state = setattr(emotion_state, emotion_b, weaker_new)
            else:
                emotion_state = setattr(emotion_state, emotion_a, weaker_new)
            
            # 设置锁（3轮）
            new_locks[lock_key] = 3
    
    return emotion_state, new_locks
```

#### 3.1.4 性格基线演化（来自SentiCore）

```python
def apply_baseline_drift(current: EmotionState, baseline: EmotionState, 
                         drift_rate: float = 0.001) -> EmotionState:
    """
    性格基线演化
    
    每次存档时，基线向当前情绪靠近 drift_rate（默认0.1%）
    理论依据：享乐适应理论 (Frederick & Loewenstein, 1999)
    
    效果：如果AI长期处于高Joy状态，它的"默认性格"会慢慢变得更乐观
    """
    new_baseline = EmotionState(
        valence=baseline.valence + (current.valence - baseline.valence) * drift_rate,
        arousal=baseline.arousal + (current.arousal - baseline.arousal) * drift_rate,
        dominance=baseline.dominance + (current.dominance - baseline.dominance) * drift_rate,
        social_need=baseline.social_need + (current.social_need - baseline.social_need) * drift_rate,
    )
    return new_baseline
```

### 3.2 认知状态追踪（融合Aura的ASEKE框架）

#### 3.2.1 简化版认知维度

```python
class CognitiveDimension(str, Enum):
    """
    认知维度（简化版ASEKE）
    
    追踪当前对话的认知焦点
    """
    KNOWLEDGE = "knowledge"       # 知识分享/学习
    EMOTION = "emotion"           # 情感交流
    SOCIAL = "social"             # 社交互动
    TASK = "task"                 # 任务执行
    REFLECTION = "reflection"     # 反思/内省
    CREATIVITY = "creativity"     # 创造性思维

@dataclass
class CognitiveState:
    """
    认知状态
    
    追踪当前对话的认知焦点，影响AI的行为倾向
    """
    primary_focus: CognitiveDimension = CognitiveDimension.EMOTION
    secondary_focus: Optional[CognitiveDimension] = None
    engagement_level: float = 0.5  # 参与度 0-1
    cognitive_load: float = 0.3    # 认知负荷 0-1
    updated_at: str = ""
```

#### 3.2.2 认知焦点检测

```python
def detect_cognitive_focus(messages: List[Dict]) -> CognitiveDimension:
    """
    检测当前对话的认知焦点
    
    通过关键词和LLM分析判断
    """
    # 关键词映射
    keyword_map = {
        CognitiveDimension.KNOWLEDGE: ["学习", "知识", "理解", "解释", "教程"],
        CognitiveDimension.EMOTION: ["感觉", "心情", "开心", "难过", "想你"],
        CognitiveDimension.SOCIAL: ["朋友", "聚会", "聊天", "一起", "我们"],
        CognitiveDimension.TASK: ["完成", "任务", "工作", "项目", "截止"],
        CognitiveDimension.REFLECTION: ["思考", "反思", "明白", "领悟", "原来"],
        CognitiveDimension.CREATIVITY: ["想法", "创意", "设计", "创作", "灵感"],
    }
    
    # 统计关键词出现次数
    # ...
    
    return primary_focus
```

### 3.3 记忆系统分层（融合Aura的双层记忆）

#### 3.3.1 三层记忆架构

```python
class MemoryLayer(str, Enum):
    """
    记忆层次
    
    1. 工作记忆：当前对话上下文（最近N条消息）
    2. 短期记忆：近期重要信息（Hindsight Recall）
    3. 长期记忆：长期归档（Hindsight Reflect）
    """
    WORKING = "working"      # 工作记忆（即时）
    SHORT_TERM = "short"     # 短期记忆（小时级）
    LONG_TERM = "long"       # 长期记忆（天/周级）

@dataclass
class MemoryItem:
    """记忆项"""
    content: str
    layer: MemoryLayer
    importance: float  # 重要性 0-1
    timestamp: str
    tags: List[str]
    emotion_snapshot: Optional[EmotionState] = None
```

#### 3.3.2 智能记忆管理

```python
class MemoryManager:
    """
    智能记忆管理器
    
    - 自动判断记忆重要性
    - 选择性保留和遗忘
    - 跨层次检索
    """
    
    def should_retain(self, content: str, emotion_state: EmotionState, 
                      thought_type: str) -> bool:
        """
        判断是否应该保留这条记忆
        
        保留条件：
        1. 情绪强度高
        2. 包含用户名字
        3. 决策为"发送"
        4. 分数 > 阈值
        5. 包含重要关键词
        """
        # 实现判断逻辑
        pass
    
    def consolidate_memories(self) -> None:
        """
        记忆整合
        
        - 短期记忆 → 长期记忆（压缩归档）
        - 删除低重要性记忆
        - 合并相似记忆
        """
        pass
```

### 3.4 决策系统升级（融合多维度评分）

#### 3.4.1 多维度决策公式

```python
def make_decision_v3(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState,
    cognitive_state: CognitiveState,
    time_fitness: float
) -> Tuple[str, str, float]:
    """
    多维度决策（v3）
    
    公式：score = emotion_intensity × time_fitness × silence_factor 
                  × frequency_limit × cognitive_factor × dominance_factor
    
    新增维度：
    - cognitive_factor: 认知状态因子
    - dominance_factor: 支配感因子（低支配感时更可能主动联系）
    """
    # 1. 情绪强度（PAD综合）
    emotion_intensity = (emotion_state.valence + emotion_state.arousal + 
                        (1 - emotion_state.dominance)) / 3
    
    # 2. 时间权重
    time_fitness_score = time_fitness
    
    # 3. 空白因子
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    silence_factor = calculate_silence_factor(silence_minutes)
    
    # 4. 频率限制
    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = config.get("decision", {}).get("max_per_hour", 2)
    frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))
    
    # 5. 认知因子（新增）
    cognitive_factor = calculate_cognitive_factor(cognitive_state)
    
    # 6. 支配感因子（新增）
    # 低支配感时更可能主动寻求陪伴
    dominance_factor = 1.0 - emotion_state.dominance * 0.5
    
    # 计算总分
    score = (emotion_intensity * time_fitness_score * silence_factor * 
             frequency_limit * cognitive_factor * dominance_factor)
    
    # 决策阈值
    send_threshold = config.get("decision", {}).get("send_threshold", 0.6)
    delay_threshold = config.get("decision", {}).get("delay_threshold", 0.3)
    
    if score > send_threshold:
        return "auto_send", f"score={score:.3f}", score
    elif score > delay_threshold:
        return "delay_send", f"score={score:.3f}", score
    else:
        return "skip", f"score={score:.3f}", score
```

### 3.5 思维透明化（融合Aura的思维提取）

#### 3.5.1 推理过程记录

```python
@dataclass
class ThinkingProcess:
    """
    思维过程
    
    记录AI的推理过程，用于调试和优化
    """
    input_analysis: str           # 输入分析
    emotion_reasoning: str        # 情绪推理
    decision_reasoning: str       # 决策推理
    thought_generation: str       # 念头生成
    final_reasoning: str          # 最终推理
    duration_ms: float            # 处理时间
```

#### 3.5.2 思维日志

```python
def log_thinking_process(
    heartbeat_id: int,
    thinking: ThinkingProcess,
    emotion_state: EmotionState,
    decision: str
) -> None:
    """
    记录思维过程到日志
    
    用于：
    1. 调试和优化
    2. 用户可以看到"AI在想什么"
    3. 分析决策质量
    """
    # 实现日志记录
    pass
```

### 3.6 自主神经系统（融合Aura的后台任务分离）

#### 3.6.1 任务分层

```python
class TaskPriority(str, Enum):
    """
    任务优先级
    
    - CRITICAL: 需要主意识处理（用户交互）
    - HIGH: 需要及时处理（情绪更新）
    - MEDIUM: 可以后台处理（记忆整合）
    - LOW: 低优先级（统计分析）
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AutonomicNervousSystem:
    """
    自主神经系统
    
    后台处理不需要主意识关注的任务
    """
    
    async def process_background_tasks(self) -> None:
        """处理后台任务"""
        # 1. 记忆整合（低优先级）
        await self.consolidate_memories()
        
        # 2. 情绪基线演化（低优先级）
        await self.evolve_baseline()
        
        # 3. 统计分析（低优先级）
        await self.update_statistics()
        
        # 4. 清理过期数据（低优先级）
        await self.cleanup_expired_data()
```

---

## 四、实施路线图

### 4.1 Phase 1: 情绪系统升级（2天）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 1.1 PAD模型实现 | 2小时 | 无 |
| 1.2 情绪交互矩阵 | 2小时 | 1.1 |
| 1.3 拮抗对互斥检查 | 1小时 | 1.1 |
| 1.4 性格基线演化 | 1小时 | 1.1 |
| 1.5 单元测试 | 2小时 | 1.1-1.4 |
| **小计** | **8小时** | |

### 4.2 Phase 2: 认知状态追踪（1天）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 2.1 认知维度定义 | 0.5小时 | 无 |
| 2.2 认知焦点检测 | 1.5小时 | 2.1 |
| 2.3 集成到决策 | 1小时 | 2.2 |
| 2.4 单元测试 | 1小时 | 2.1-2.3 |
| **小计** | **4小时** | |

### 4.3 Phase 3: 记忆系统分层（1天）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 3.1 记忆层次定义 | 0.5小时 | 无 |
| 3.2 智能记忆管理 | 2小时 | 3.1 |
| 3.3 记忆整合逻辑 | 1.5小时 | 3.2 |
| 3.4 单元测试 | 1小时 | 3.1-3.3 |
| **小计** | **5小时** | |

### 4.4 Phase 4: 决策系统升级（0.5天）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 4.1 多维度决策公式 | 1小时 | Phase 1, 2 |
| 4.2 集成到心跳 | 0.5小时 | 4.1 |
| 4.3 单元测试 | 0.5小时 | 4.1-4.2 |
| **小计** | **2小时** | |

### 4.5 Phase 5: 思维透明化（0.5天）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 5.1 思维过程定义 | 0.5小时 | 无 |
| 5.2 推理过程记录 | 1小时 | 5.1 |
| 5.3 前端展示 | 1小时 | 5.2 |
| **小计** | **2.5小时** | |

### 4.6 Phase 6: 自主神经系统（0.5天）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 6.1 任务分层定义 | 0.5小时 | 无 |
| 6.2 后台任务处理 | 1.5小时 | 6.1 |
| 6.3 集成测试 | 0.5小时 | 6.1-6.2 |
| **小计** | **2.5小时** | |

### 4.7 总计

| Phase | 功能 | 预计时间 |
|-------|------|----------|
| Phase 1 | 情绪系统升级 | 8小时 |
| Phase 2 | 认知状态追踪 | 4小时 |
| Phase 3 | 记忆系统分层 | 5小时 |
| Phase 4 | 决策系统升级 | 2小时 |
| Phase 5 | 思维透明化 | 2.5小时 |
| Phase 6 | 自主神经系统 | 2.5小时 |
| **总计** | | **24小时** |

---

## 五、关键改进对比

| 维度 | v0.2 现状 | v0.2.1 设计 | 改进方案 |
|------|-----------|-------------|----------|
| 情绪模型 | 单一intensity | VA模型 | PAD模型（+Dominance） |
| 情绪维度 | 1维 | 2维 | 4维（valence/arousal/dominance/social_need） |
| 情绪交互 | 无 | 无 | 17条联动规则 |
| 拮抗检测 | 无 | 无 | 4对拮抗对互斥 |
| 性格演化 | 无 | 无 | Baseline Drift 0.1% |
| 认知追踪 | 无 | 无 | 6个认知维度 |
| 记忆分层 | 单层 | 单层 | 三层（工作/短期/长期） |
| 决策维度 | 2-3个 | 4个 | 6个（+认知+支配感） |
| 思维透明 | 无 | 无 | 完整推理过程记录 |
| 后台处理 | 无 | 无 | 自主神经系统 |

---

## 六、配置项扩展

```python
# 新增配置项
_DEFAULTS = {
    # ... 现有配置 ...
    
    # PAD情感模型
    "active_consciousness.emotion.pad_enabled": "true",
    "active_consciousness.emotion.dominance_default": "0.5",
    
    # 情绪交互
    "active_consciousness.emotion.interaction_enabled": "true",
    "active_consciousness.emotion.interaction_strength": "0.5",
    
    # 拮抗对
    "active_consciousness.emotion.antagonist_enabled": "true",
    "active_consciousness.emotion.antagonist_threshold": "50",
    "active_consciousness.emotion.antagonist_lock_turns": "3",
    
    # 性格演化
    "active_consciousness.emotion.baseline_drift_rate": "0.001",
    
    # 认知状态
    "active_consciousness.cognitive.enabled": "true",
    "active_consciousness.cognitive.detection_method": "keyword",  # keyword / llm
    
    # 记忆分层
    "active_consciousness.memory.layers_enabled": "true",
    "active_consciousness.memory.consolidation_interval": "3600",  # 秒
    "active_consciousness.memory.max_working_items": "20",
    "active_consciousness.memory.max_short_term_items": "100",
    
    # 思维透明
    "active_consciousness.thinking.enabled": "true",
    "active_consciousness.thinking.log_level": "detailed",  # minimal / normal / detailed
    
    # 自主神经系统
    "active_consciousness.autonomic.enabled": "true",
    "active_consciousness.autonomic.background_interval": "300",  # 秒
}
```

---

## 七、验收标准

### 7.1 Phase 1 验收标准
- [ ] PAD模型实现完成
- [ ] 情绪交互矩阵工作正常
- [ ] 拮抗对互斥检查正确
- [ ] 性格基线演化功能正常
- [ ] 所有单元测试通过

### 7.2 Phase 2 验收标准
- [ ] 认知维度定义完成
- [ ] 认知焦点检测准确
- [ ] 集成到决策系统
- [ ] 所有单元测试通过

### 7.3 Phase 3 验收标准
- [ ] 三层记忆架构实现
- [ ] 智能记忆管理功能正常
- [ ] 记忆整合逻辑正确
- [ ] 所有单元测试通过

### 7.4 Phase 4 验收标准
- [ ] 多维度决策公式实现
- [ ] 集成到心跳流程
- [ ] 决策结果合理
- [ ] 所有单元测试通过

### 7.5 Phase 5 验收标准
- [ ] 思维过程定义完成
- [ ] 推理过程记录完整
- [ ] 前端展示正常
- [ ] 日志可读性好

### 7.6 Phase 6 验收标准
- [ ] 任务分层定义完成
- [ ] 后台任务处理正常
- [ ] 不影响主流程性能
- [ ] 集成测试通过

---

## 八、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| PAD模型复杂度高 | 实现困难 | 中 | 分阶段实现，先VA后加D |
| 情绪交互规则冲突 | 行为不可预测 | 中 | 设置优先级，冲突时取最高优先级 |
| 记忆分层性能问题 | 响应变慢 | 低 | 异步处理，缓存热点数据 |
| 决策维度过多 | 调参困难 | 中 | 提供默认配置，支持动态调整 |
| 思维透明日志过大 | 存储压力 | 低 | 设置日志级别，定期清理 |

---

## 九、总结

这个综合改进方案融合了三个参考项目的核心优势：

1. **SentiCore**：30维情绪矩阵、情绪交互规则、拮抗对互斥、性格演化
2. **Emotion AI (Aura)**：认知维度追踪、双层记忆、思维透明化、自主神经系统
3. **The Consciousness AI**：PAD情感模型、情感调制机制、稳态驱动、自我模型

通过这些改进，hermes-active将从一个"闹钟式存在"进化为真正的"持续式存在"，具有：
- 更细腻的情绪表达
- 更智能的决策能力
- 更自然的行为模式
- 更好的可解释性
- 更强的自适应能力

**预计总工期**：24小时（约3个工作日）

---

## 参考文献

### SentiCore
- Cowen, A., & Keltner, D. (2017). "Self-report captures 27 distinct categories of emotion." *PNAS*.
- Ortony, A., Clore, G.L., & Collins, A. (1988). *The Cognitive Structure of Emotions.* (OCC Model)
- Russell, J.A. (1980). "A circumplex model of affect." *JPSP*.
- Frederick, S. & Loewenstein, G. (1999). "Hedonic adaptation." *Well-being: The foundations of hedonic psychology.*
- Barrett, L.F. (2017). *How Emotions Are Made.*
- Lazarus, R.S. (1991). *Emotion and Adaptation.* (Appraisal Theory)

### Emotion AI (Aura)
- 项目地址: https://github.com/angrysky56/emotion_ai
- ASEKE认知框架
- ChromaDB + MemVid双层记忆
- MCP双向协议

### The Consciousness AI
- 项目地址: https://github.com/venturaEffect/the_consciousness_ai
- Feinberg & Mallatt (2016). *The Ancient Origins of Consciousness*. MIT Press.
- Metzinger (2003). *Being No One: The Self-Model Theory of Subjectivity*. MIT Press.
- Damasio (1999). *The Feeling of What Happens*.
- Baars (1988). Global Workspace Theory.
- Tononi (2004). Integrated Information Theory.

---

*本文档由 Claude Code 生成，基于对三个参考项目的深度分析和综合。*
*最后更新：2026-06-19*
