# hermes-active v0.2.1 Phase 1 开发任务

## ⚠️ 严格约束

### 绝对不能动的文件（被动意识模块）
- `backend/models/passive_consciousness.py`
- `backend/models/passive_consciousness_log.py`
- `backend/services/passive_consciousness_service.py`
- `backend/routers/passive_consciousness.py`
- `frontend/src/views/PassiveConsciousness.vue`
- `frontend/src/api/passive_consciousness.js`

以上文件**一个字都不能改**，包括 import 语句。

### 可以修改的文件（主动意识模块）
- `backend/models/active_consciousness.py` — 新增数据类
- `backend/services/active_consciousness_service.py` — 核心逻辑
- `backend/services/config_service.py` — 如果需要新增配置读写方法

---

## 任务目标

基于 `docs/v0.2.1/detailed-design.md` 详细设计方案，实现 Phase 1（情绪连续性）的核心功能。

---

## Phase 1 详细任务

### Task 1.1: EmotionState 数据类

**文件**: `backend/models/active_consciousness.py`

**新增内容**:
```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class DominantEmotion(str, Enum):
    """主导情绪枚举"""
    CALM = "calm"
    CONTENT = "content"
    HAPPY = "happy"
    LONGING = "longing"
    MISSING = "missing"
    YEARNING = "yearning"
    ANXIOUS = "anxious"
    BORED = "bored"
    CONCERNED = "concerned"

@dataclass
class EmotionState:
    """
    情绪状态 - VA 模型
    
    Valence (效价): 情感的正负性，0=消极，1=积极
    Arousal (唤醒度): 情感的激活程度，0=平静，1=激动
    Dominant (主导情绪): 当前最显著的情绪标签
    Social Need (社交需求): 想要社交/聊天的程度，0=不需要，1=非常想
    """
    valence: float = 0.5
    arousal: float = 0.3
    dominant: str = "calm"
    social_need: float = 0.3
    updated_at: str = ""
    
    def __post_init__(self):
        self.valence = max(0.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.social_need = max(0.0, min(1.0, self.social_need))
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominant": self.dominant,
            "social_need": round(self.social_need, 3),
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EmotionState':
        return cls(
            valence=float(data.get("valence", 0.5)),
            arousal=float(data.get("arousal", 0.3)),
            dominant=data.get("dominant", "calm"),
            social_need=float(data.get("social_need", 0.3)),
            updated_at=data.get("updated_at", "")
        )
    
    def intensity(self) -> float:
        """计算综合情绪强度"""
        return (self.valence + self.arousal + self.social_need) / 3
    
    def is_stale(self, minutes: float = 60) -> bool:
        """检查情绪状态是否过期"""
        if not self.updated_at:
            return True
        try:
            updated = datetime.fromisoformat(self.updated_at)
            return (datetime.now() - updated).total_seconds() / 60 > minutes
        except Exception:
            return True
```

### Task 1.2: ThoughtType 枚举

**文件**: `backend/models/active_consciousness.py`

**新增内容**:
```python
class ThoughtType(str, Enum):
    """念头类型枚举"""
    TIME = "time"           # 时间念头：\"23:30了，该睡了\"
    SILENCE = "silence"     # 空白念头：\"好久没说话了\"
    ASSOCIATION = "assoc"   # 关联念头：\"今天周五，一般加班\"
    MEMORY = "memory"       # 回忆念头：\"想起你说过...\"
    EMOTION = "emotion"     # 情绪念头：\"现在有点兴奋\"
    ENVIRONMENT = "env"     # 环境念头：\"外面下雨了\"
```

### Task 1.3: DelayedThought 数据类

**文件**: `backend/models/active_consciousness.py`

**新增内容**:
```python
@dataclass
class DelayedThought:
    """延迟发送的念头"""
    id: int
    content: str
    thought_type: str
    score: float
    created_at: str
    retry_count: int = 0
    next_retry_at: str = ""
    emotion_snapshot: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "thought_type": self.thought_type,
            "score": round(self.score, 3),
            "created_at": self.created_at,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at,
            "emotion_snapshot": self.emotion_snapshot
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DelayedThought':
        return cls(
            id=data.get("id", 0),
            content=data.get("content", ""),
            thought_type=data.get("thought_type", "unknown"),
            score=float(data.get("score", 0.5)),
            created_at=data.get("created_at", ""),
            retry_count=int(data.get("retry_count", 0)),
            next_retry_at=data.get("next_retry_at", ""),
            emotion_snapshot=data.get("emotion_snapshot", {})
        )
```

### Task 1.4: 情绪演化算法

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:
```python
def calculate_dominant(valence: float, arousal: float, social_need: float) -> str:
    """根据 VA 值计算主导情绪标签"""
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

def evolve_emotion(last_state: EmotionState, minutes_since_update: float) -> EmotionState:
    """
    基于时间流逝自然演化情绪
    
    规则：
    1. arousal 自然衰减（越久越平静）
    2. social_need 自然上升（越久越想聊天）
    3. valence 轻微回归中性（0.5）
    """
    # 边界处理
    minutes_since_update = max(0, min(minutes_since_update, 1440))
    hours = minutes_since_update / 60
    
    # 读取配置
    config = ActiveConsciousnessService.get_config()
    emotion_config = config.get("emotion", {})
    decay_rate = float(emotion_config.get("decay_rate", "0.02"))
    growth_rate = float(emotion_config.get("social_need_growth", "0.01"))
    regression_rate = float(emotion_config.get("valence_regression", "0.1"))
    
    # 1. arousal 自然衰减
    new_arousal = max(0.1, last_state.arousal - (decay_rate * hours))
    
    # 2. social_need 自然上升
    new_social_need = min(1.0, last_state.social_need + (growth_rate * hours))
    
    # 3. valence 轻微回归中性
    valence_diff = 0.5 - last_state.valence
    new_valence = last_state.valence + (valence_diff * regression_rate * hours)
    new_valence = max(0.0, min(1.0, new_valence))
    
    # 4. 计算主导情绪
    new_dominant = calculate_dominant(new_valence, new_arousal, new_social_need)
    
    return EmotionState(
        valence=round(new_valence, 3),
        arousal=round(new_arousal, 3),
        dominant=new_dominant,
        social_need=round(new_social_need, 3),
        updated_at=datetime.now().isoformat()
    )

def merge_emotion(evolved: EmotionState, llm_assessed: EmotionState) -> EmotionState:
    """合并演化值和 LLM 评估值"""
    config = ActiveConsciousnessService.get_config()
    emotion_config = config.get("emotion", {})
    weight_evolved = float(emotion_config.get("weight_evolved", "0.4"))
    weight_llm = float(emotion_config.get("weight_llm", "0.6"))
    
    # 如果演化值过期，增加 LLM 权重
    if evolved.is_stale(minutes=60):
        weight_evolved = 0.2
        weight_llm = 0.8
    
    merged_valence = evolved.valence * weight_evolved + llm_assessed.valence * weight_llm
    merged_arousal = evolved.arousal * weight_evolved + llm_assessed.arousal * weight_llm
    merged_social_need = evolved.social_need * weight_evolved + llm_assessed.social_need * weight_llm
    
    # 主导情绪选择
    if llm_assessed.arousal > 0.6:
        merged_dominant = llm_assessed.dominant
    else:
        merged_dominant = evolved.dominant
    
    return EmotionState(
        valence=round(merged_valence, 3),
        arousal=round(merged_arousal, 3),
        dominant=merged_dominant,
        social_need=round(merged_social_need, 3),
        updated_at=datetime.now().isoformat()
    )
```

### Task 1.5: 情绪存储接口

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:
```python
def get_emotion_state() -> EmotionState:
    """获取当前情绪状态"""
    db = ActiveSession()
    try:
        value = ConfigService.get_config(db, "active_consciousness.emotion_state")
        if value:
            try:
                data = json.loads(value)
                return EmotionState.from_dict(data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("解析情绪状态失败: %s", e)
        return EmotionState()
    finally:
        db.close()

def update_emotion_state(state: EmotionState) -> bool:
    """更新情绪状态到数据库"""
    db = ActiveSession()
    try:
        json_str = json.dumps(state.to_dict(), ensure_ascii=False)
        ConfigService.set_config(db, "active_consciousness.emotion_state", json_str)
        logger.info("情绪状态已更新: valence=%.3f, arousal=%.3f, dominant=%s", 
                    state.valence, state.arousal, state.dominant)
        return True
    except Exception as e:
        logger.error("更新情绪状态失败: %s", e)
        return False
    finally:
        db.close()

def get_emotional_intensity_compat() -> float:
    """向后兼容：获取旧格式的情绪强度"""
    emotion_state = get_emotion_state()
    if emotion_state:
        return emotion_state.intensity()
    db = ActiveSession()
    try:
        val = ConfigService.get_config(db, "active_consciousness.current.emotional_intensity")
        return float(val) if val else 0.0
    except Exception:
        return 0.0
    finally:
        db.close()
```

### Task 1.6: 时间窗口权重

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:
```python
TIME_FITNESS_TABLE = [
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
    
    config = ActiveConsciousnessService.get_config()
    time_config = config.get("time", {})
    
    if not time_config.get("enabled", True):
        return 1.0, "未启用"
    
    for start, end, fitness, label in TIME_FITNESS_TABLE:
        if start > end:  # 跨午夜
            if hour >= start or hour < end:
                return fitness, label
        else:
            if start <= hour < end:
                return fitness, label
    
    return 0.3, "深夜"
```

### Task 1.7: 多维度决策公式

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:
```python
def make_decision_v2(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> tuple[str, str, float]:
    """
    多维度决策
    
    公式：score = intensity × time_fitness × silence_factor × frequency_limit
    """
    decision_config = config.get("decision", {})
    
    # 1. 情绪强度
    intensity = emotion_state.intensity()
    
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
    max_per_hour = decision_config.get("max_per_hour", 2)
    frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))
    
    # 计算总分
    score = intensity * time_fitness * silence_factor * frequency_limit
    
    # 决策阈值
    send_threshold = decision_config.get("send_threshold", 0.6)
    delay_threshold = decision_config.get("delay_threshold", 0.3)
    memory_threshold = decision_config.get("memory_threshold", 0.1)
    
    # 构建决策原因
    reason_parts = [
        f"intensity={intensity:.3f}",
        f"time_fitness={time_fitness:.3f}({time_label})",
        f"silence_factor={silence_factor:.3f}",
        f"frequency_limit={frequency_limit:.3f}",
    ]
    reason = ", ".join(reason_parts)
    
    if score > send_threshold:
        return "auto_send", f"score={score:.3f} > {send_threshold} ({reason})", score
    elif score > delay_threshold:
        return "delay_send", f"score={score:.3f} > {delay_threshold} ({reason})", score
    elif score > memory_threshold:
        return "memory", f"score={score:.3f} > {memory_threshold} ({reason})", score
    else:
        return "skip", f"score={score:.3f} <= {memory_threshold} ({reason})", score
```

### Task 1.8: Hindsight 念头存储（带标签）

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:
```python
def determine_thought_type(
    status: Dict[str, Any],
    emotion_state: EmotionState,
    hindsight_results: List[Dict],
    weather_info: Optional[Dict]
) -> str:
    """根据上下文判断念头类型"""
    # 优先级：回忆 > 天气 > 情绪 > 沉默 > 时间 > 默认
    if hindsight_results and len(hindsight_results) > 0:
        return ThoughtType.MEMORY.value
    if weather_info and weather_info.get("weather") in ["雨", "雪", "大风", "雷阵雨"]:
        return ThoughtType.ENVIRONMENT.value
    if emotion_state.intensity() > 0.5:
        return ThoughtType.EMOTION.value
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes > 120:
        return ThoughtType.SILENCE.value
    now = datetime.now()
    if now.hour in [7, 8, 12, 13, 22, 23]:
        return ThoughtType.TIME.value
    return ThoughtType.ASSOCIATION.value

async def retain_thought_to_hindsight(
    thought: str,
    emotion_state: EmotionState,
    thought_type: str,
    score: float
) -> bool:
    """
    将重要念头存入 Hindsight（带标签标识）
    
    存储条件（满足任一即可）：
    1. 情绪强度 > retain_threshold
    2. 包含用户名字（如\"曹凡\"）
    3. 分数 > retain_threshold
    
    标签设计：
    - \"thought\": 固定标签，标识这是主动意识的念头
    - thought_type: 念头类型（time/silence/assoc/memory/emotion/env）
    - emotion_state.dominant: 当前主导情绪（calm/happy/longing 等）
    - \"active_consciousness\": 来源标识
    """
    config = ActiveConsciousnessService.get_config()
    thought_config = config.get("thought", {})
    
    if not thought_config.get("retain_enabled", True):
        return False
    
    retain_threshold = float(thought_config.get("retain_threshold", "0.5"))
    intensity = emotion_state.intensity()
    
    should_retain = (
        intensity > retain_threshold or
        "曹凡" in thought or
        score > retain_threshold
    )
    
    if not should_retain:
        return False
    
    try:
        hindsight_config = config.get("hindsight", {})
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        timeout = float(hindsight_config.get("timeout", 30))
        
        client = get_hindsight_client(base_url=base_url, timeout=timeout)
        
        # 构建内容（带类型前缀）
        content = f"[{thought_type}] {thought}"
        
        # 构建标签（重要！用于后续检索和分类）
        tags = [
            "active_consciousness",  # 来源：主动意识模块
            "thought",               # 类型：念头
            thought_type,            # 念头类型：time/silence/assoc/memory/emotion/env
            emotion_state.dominant,  # 主导情绪：calm/happy/longing 等
        ]
        
        # 如果包含用户名字，加特殊标签
        if "曹凡" in thought:
            tags.append("user_related")
        
        # 如果情绪强度高，加标签
        if intensity > 0.7:
            tags.append("high_emotion")
        
        await client.aretain(
            bank_id=bank_id,
            content=content,
            tags=tags
        )
        
        logger.info("念头已存入 Hindsight: type=%s, tags=%s, content=%s", 
                    thought_type, tags, thought[:50])
        return True
        
    except Exception as e:
        logger.warning("存入 Hindsight 失败: %s", e)
        return False
```

### Task 1.9: 延迟队列管理

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:
```python
def get_delayed_thoughts() -> List[DelayedThought]:
    """获取延迟队列中的念头"""
    db = ActiveSession()
    try:
        value = ConfigService.get_config(db, "active_consciousness.delayed_thoughts")
        if not value:
            return []
        try:
            data = json.loads(value)
            return [DelayedThought.from_dict(item) for item in data]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("解析延迟队列失败: %s", e)
            return []
    finally:
        db.close()

def save_delayed_thoughts(thoughts: List[DelayedThought]) -> bool:
    """保存延迟队列"""
    db = ActiveSession()
    try:
        data = [t.to_dict() for t in thoughts]
        json_str = json.dumps(data, ensure_ascii=False)
        ConfigService.set_config(db, "active_consciousness.delayed_thoughts", json_str)
        return True
    except Exception as e:
        logger.error("保存延迟队列失败: %s", e)
        return False
    finally:
        db.close()

def add_to_delay_queue(
    content: str,
    thought_type: str,
    score: float,
    emotion_state: EmotionState
) -> bool:
    """添加念头到延迟队列"""
    thoughts = get_delayed_thoughts()
    
    # 检查队列大小限制
    config = ActiveConsciousnessService.get_config()
    max_queue_size = int(config.get("delay", {}).get("max_queue_size", 10))
    if len(thoughts) >= max_queue_size:
        # 移除最旧的
        thoughts = thoughts[-(max_queue_size-1):]
    
    new_thought = DelayedThought(
        id=int(datetime.now().timestamp()),
        content=content,
        thought_type=thought_type,
        score=score,
        created_at=datetime.now().isoformat(),
        emotion_snapshot=emotion_state.to_dict()
    )
    thoughts.append(new_thought)
    return save_delayed_thoughts(thoughts)

async def reevaluate_delayed_thoughts(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Dict[str, int]:
    """重新评估延迟队列中的念头"""
    delay_config = config.get("delay", {})
    max_retry = int(delay_config.get("max_retry", 3))
    retry_interval = int(delay_config.get("retry_interval_minutes", 30))
    
    decision_config = config.get("decision", {})
    send_threshold = decision_config.get("send_threshold", 0.6)
    
    delayed_thoughts = get_delayed_thoughts()
    if not delayed_thoughts:
        return {"sent": 0, "discarded": 0, "kept": 0}
    
    stats = {"sent": 0, "discarded": 0, "kept": 0}
    remaining_thoughts = []
    
    for thought in delayed_thoughts:
        # 超过最大重试次数
        if thought.retry_count >= max_retry:
            stats["discarded"] += 1
            continue
        
        # 检查是否到了重试时间
        if thought.next_retry_at:
            try:
                next_retry = datetime.fromisoformat(thought.next_retry_at)
                if datetime.now() < next_retry:
                    remaining_thoughts.append(thought)
                    stats["kept"] += 1
                    continue
            except Exception:
                pass
        
        # 重新计算 score
        time_fitness, _ = get_time_fitness()
        silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
        if silence_minutes < 60:
            silence_factor = 0.3
        elif silence_minutes < 180:
            silence_factor = 0.5
        elif silence_minutes < 360:
            silence_factor = 0.7
        else:
            silence_factor = 0.9
        
        hour_sent = status.get("hour_sent_count", 0)
        max_per_hour = decision_config.get("max_per_hour", 2)
        frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))
        
        intensity = emotion_state.intensity()
        new_score = intensity * time_fitness * silence_factor * frequency_limit
        
        if new_score > send_threshold:
            # 升级为发送
            success = await send_message_to_target(config, thought.content)
            if success:
                stats["sent"] += 1
                # 存入 Hindsight
                await retain_thought_to_hindsight(
                    thought.content, emotion_state, thought.thought_type, new_score
                )
            else:
                thought.retry_count += 1
                thought.next_retry_at = (
                    datetime.now() + timedelta(minutes=retry_interval)
                ).isoformat()
                remaining_thoughts.append(thought)
                stats["kept"] += 1
        elif new_score < 0.1:
            stats["discarded"] += 1
        else:
            thought.score = new_score
            thought.retry_count += 1
            thought.next_retry_at = (
                datetime.now() + timedelta(minutes=retry_interval)
            ).isoformat()
            remaining_thoughts.append(thought)
            stats["kept"] += 1
    
    save_delayed_thoughts(remaining_thoughts)
    return stats
```

### Task 1.10: 新增配置项

**文件**: `backend/services/active_consciousness_service.py`

**在 `_DEFAULTS` 字典中新增**:
```python
# 情绪演化
"active_consciousness.emotion.decay_rate": "0.02",
"active_consciousness.emotion.social_need_growth": "0.01",
"active_consciousness.emotion.valence_regression": "0.1",
"active_consciousness.emotion.weight_evolved": "0.4",
"active_consciousness.emotion.weight_llm": "0.6",

# 时间窗口
"active_consciousness.time.enabled": "true",
"active_consciousness.time.deep_night_start": "23.5",
"active_consciousness.time.deep_night_end": "7",
"active_consciousness.time.deep_night_fitness": "0.3",

# 延迟发送
"active_consciousness.delay.enabled": "true",
"active_consciousness.delay.max_retry": "3",
"active_consciousness.delay.retry_interval_minutes": "30",
"active_consciousness.delay.max_queue_size": "10",

# 念头存储
"active_consciousness.thought.retain_enabled": "true",
"active_consciousness.thought.retain_threshold": "0.5",
```

---

## 验收标准

1. [ ] EmotionState 数据类定义完成
2. [ ] ThoughtType 枚举定义完成
3. [ ] DelayedThought 数据类定义完成
4. [ ] evolve_emotion() 函数实现
5. [ ] calculate_dominant() 函数实现
6. [ ] merge_emotion() 函数实现
7. [ ] get_emotion_state() / update_emotion_state() 函数实现
8. [ ] get_time_fitness() 函数实现
9. [ ] make_decision_v2() 函数实现
10. [ ] retain_thought_to_hindsight() 函数实现（带标签）
11. [ ] determine_thought_type() 函数实现
12. [ ] 延迟队列相关函数实现
13. [ ] 所有新增配置项已添加
14. [ ] **被动意识文件未被修改**
15. [ ] Python 语法检查通过

---

## 注意事项

1. **不要破坏现有功能**：旧的 emotional_intensity 逻辑保留
2. **配置优先**：所有阈值从 configs 表读取
3. **state.db 只读**：只往 active.db 写数据
4. **向后兼容**：旧 API 保持可用
5. **Hindsight 标签**：入库时必须使用标签标识来源、类型、情绪状态
6. **被动意识不碰**：绝对不能修改 passive_consciousness 相关文件
