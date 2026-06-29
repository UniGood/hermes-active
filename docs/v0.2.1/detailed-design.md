# hermes-active v0.2.1 详细设计方案

> 从"闹钟式存在"进化到"持续式存在" — 完整可执行的技术方案

---

## 一、方案总览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              hermes-active v0.2.1                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Phase 1   │    │   Phase 2   │    │   Phase 3   │    │   Phase 4   │  │
│  │  情绪连续性  │───▶│  时间窗口   │───▶│  念头系统   │───▶│  延迟队列   │  │
│  │  (核心)     │    │   决策      │    │   增强      │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  │          │
│         ▼                  ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      EmotionState (VA 模型)                         │   │
│  │  valence: 0-1    arousal: 0-1    dominant: str    social_need: 0-1 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         心跳调度器 (APScheduler)                     │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐            │   │
│  │  │ 读取    │──▶│ 演化    │──▶│ LLM     │──▶│ 合并    │            │   │
│  │  │ 情绪    │   │ 情绪    │   │ 评估    │   │ 情绪    │            │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘            │   │
│  │       │                                              │              │   │
│  │       ▼                                              ▼              │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐            │   │
│  │  │ 时间    │──▶│ 决策    │──▶│ 处理    │──▶│ 重评估  │            │   │
│  │  │ 窗口    │   │ 计算    │   │ 结果    │   │ 延迟队列│            │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         存储层                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │ active.db   │  │ state.db    │  │ Hindsight   │                 │   │
│  │  │ (读写)      │  │ (只读)      │  │ (外部)      │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心改进点总结

| 维度 | v0.2 现状 | v0.2.1 目标 | 改进说明 |
|------|-----------|-------------|----------|
| 情绪模型 | 单一 intensity (0-1) | VA 三维度 (valence/arousal/dominant) | 更细腻的情绪表达 |
| 情绪连续 | 每次重新评估 | 跨心跳持久化 + 时间自然演化 | 情绪有"记忆" |
| 决策逻辑 | 阈值判断 (>0.6发) | 多维度评分 (时间×强度×空白×频率) | 更智能的决策 |
| 念头系统 | 自由生成 | 6种类型 + 存储闭环 | 结构化的念头管理 |
| 时间感知 | 无 | 时间窗口权重 (深夜/工作/休息) | 符合人类作息 |

### 1.3 与 v0.2 的差异点

1. **数据结构差异**：
   - v0.2: `emotional_intensity` (单一浮点数)
   - v0.2.1: `EmotionState` (valence, arousal, dominant, social_need)

2. **决策逻辑差异**：
   - v0.2: `if emotional_intensity > 0.5 and longing_level > 0`
   - v0.2.1: `score = intensity × time_fitness × silence_factor × frequency_limit`

3. **心跳流程差异**：
   - v0.2: 读取状态 → LLM评估 → 决策 → 发送
   - v0.2.1: 读取情绪 → 演化 → LLM评估 → 合并 → 时间窗口 → 决策 → 发送 → 重评估延迟队列

---

## 二、Phase 1：情绪连续性（核心）

### 2.1 目标和背景

**目标**：用 VA 模型替代单一 intensity，实现情绪的跨心跳持久化和自然演化。

**背景**：
- v0.2 的情绪值每次心跳都重新计算，没有"记忆"
- 单一 intensity 无法区分开心、平静、想念等不同情绪
- 情绪应该随时间自然变化（如：激动→平静，孤单→想念）

### 2.2 数据结构定义

#### 2.2.1 EmotionState 数据类

```python
# backend/models/active_consciousness.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class DominantEmotion(str, Enum):
    """主导情绪枚举"""
    CALM = "calm"           # 平静
    CONTENT = "content"     # 满足
    HAPPY = "happy"         # 开心
    LONGING = "longing"     # 想念
    MISSING = "missing"     # 思念
    YEARNING = "yearning"   # 渴望
    ANXIOUS = "anxious"     # 焦虑
    BORED = "bored"         # 无聊
    CONCERNED = "concerned" # 担心


@dataclass
class EmotionState:
    """
    情绪状态 - VA 模型
    
    VA 模型说明：
    - Valence (效价): 情感的正负性，0=消极，1=积极
    - Arousal (唤醒度): 情感的激活程度，0=平静，1=激动
    - Dominant (主导情绪): 当前最显著的情绪标签
    - Social Need (社交需求): 想要社交/聊天的程度，0=不需要，1=非常想
    
    设计原则：
    1. 所有值都在 [0, 1] 范围内
    2. 默认值为中性状态（平静、满足）
    3. updated_at 用于计算时间演化
    """
    valence: float = 0.5        # 情感效价 0-1（0=消极, 1=积极）
    arousal: float = 0.3        # 唤醒度 0-1（0=平静, 1=激动）
    dominant: str = "calm"      # 主导情绪标签
    social_need: float = 0.3    # 社交需求 0-1
    updated_at: str = ""        # 上次更新时间 (ISO format)
    
    def __post_init__(self):
        """初始化后验证"""
        self.valence = max(0.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.social_need = max(0.0, min(1.0, self.social_need))
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominant": self.dominant,
            "social_need": round(self.social_need, 3),
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EmotionState':
        """从字典创建"""
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

#### 2.2.2 ThoughtType 枚举

```python
class ThoughtType(str, Enum):
    """
    念头类型枚举
    
    设计原则：
    1. 每种类型对应不同的生成逻辑
    2. 类型影响念头的权重和处理方式
    3. 类型用于日志分析和统计
    """
    TIME = "time"           # 时间念头："23:30了，该睡了"
    SILENCE = "silence"     # 空白念头："好久没说话了"
    ASSOCIATION = "assoc"   # 关联念头："今天周五，一般加班"
    MEMORY = "memory"       # 回忆念头："想起你说过..."
    EMOTION = "emotion"     # 情绪念头："现在有点兴奋"
    ENVIRONMENT = "env"     # 环境念头："外面下雨了"
```

#### 2.2.3 DelayedThought 数据类

```python
@dataclass
class DelayedThought:
    """
    延迟发送的念头
    
    设计原则：
    1. 用于存储 score 在 delay_threshold 和 send_threshold 之间的念头
    2. 每次心跳时重新评估
    3. 支持升级（发送）、降级（丢弃）、保持（继续延迟）
    """
    id: int                         # 唯一标识
    content: str                    # 念头内容
    thought_type: str               # 念头类型 (ThoughtType)
    score: float                    # 当前分数
    created_at: str                 # 创建时间
    retry_count: int = 0            # 重试次数
    next_retry_at: str = ""         # 下次重试时间
    emotion_snapshot: dict = field(default_factory=dict)  # 创建时的情绪快照
    
    def to_dict(self) -> dict:
        """转换为字典"""
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
        """从字典创建"""
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

### 2.3 算法逻辑

#### 2.3.1 情绪演化算法

```python
def evolve_emotion(last_state: EmotionState, minutes_since_update: float) -> EmotionState:
    """
    基于时间流逝自然演化情绪
    
    物理意义：
    1. arousal 自然衰减：激动的状态会自然平静下来
    2. social_need 自然上升：长时间不聊天会更想聊天
    3. valence 轻微回归中性：极端情绪会逐渐平复
    
    参数说明：
    - decay_rate: 每小时衰减率，0.02 表示每小时 arousal 下降 0.02
    - growth_rate: 每小时增长率，0.01 表示每小时 social_need 上升 0.01
    - regression_rate: valence 回归中性系数，0.1 表示每小时向 0.5 靠近 10%
    
    边界条件：
    - minutes_since_update < 0: 视为 0
    - minutes_since_update > 1440 (24小时): 视为 1440，防止过度演化
    - 所有值保持在 [0, 1] 范围内
    """
    # 边界处理
    minutes_since_update = max(0, min(minutes_since_update, 1440))
    hours = minutes_since_update / 60
    
    # 读取配置的衰减率
    config = ActiveConsciousnessService.get_config()
    emotion_config = config.get("emotion", {})
    decay_rate = float(emotion_config.get("decay_rate", "0.02"))
    growth_rate = float(emotion_config.get("social_need_growth", "0.01"))
    regression_rate = float(emotion_config.get("valence_regression", "0.1"))
    
    # 1. arousal 自然衰减（越久越平静）
    # 公式：new_arousal = max(0.1, last_arousal - decay_rate * hours)
    # 最低保持 0.1，防止完全无感
    new_arousal = max(0.1, last_state.arousal - (decay_rate * hours))
    
    # 2. social_need 自然上升（越久越想聊天）
    # 公式：new_social_need = min(1.0, last_social_need + growth_rate * hours)
    # 最高 1.0，表示非常想聊天
    new_social_need = min(1.0, last_state.social_need + (growth_rate * hours))
    
    # 3. valence 轻微回归中性（0.5）
    # 公式：new_valence = last_valence + (0.5 - last_valence) * regression_rate * hours
    # 如果 valence > 0.5，会下降；如果 < 0.5，会上升
    valence_diff = 0.5 - last_state.valence
    new_valence = last_state.valence + (valence_diff * regression_rate * hours)
    new_valence = max(0.0, min(1.0, new_valence))
    
    # 4. 根据新值计算主导情绪
    new_dominant = calculate_dominant(new_valence, new_arousal, new_social_need)
    
    return EmotionState(
        valence=round(new_valence, 3),
        arousal=round(new_arousal, 3),
        dominant=new_dominant,
        social_need=round(new_social_need, 3),
        updated_at=datetime.now().isoformat()
    )
```

#### 2.3.2 主导情绪计算

```python
def calculate_dominant(valence: float, arousal: float, social_need: float) -> str:
    """
    根据 VA 值计算主导情绪标签
    
    决策树逻辑：
    1. 首先检查社交需求（高社交需求优先）
    2. 然后检查唤醒度（低唤醒度 = 平静）
    3. 最后检查效价（正/负效价）
    
    返回值：DominantEmotion 枚举值
    
    边界条件：
    - 所有输入值都在 [0, 1] 范围内
    - 默认返回 "calm"
    """
    # 高社交需求：渴望/焦虑
    if social_need > 0.7:
        return "yearning" if valence > 0.5 else "anxious"
    
    # 中等社交需求：想念/思念
    if social_need > 0.5:
        return "longing" if valence > 0.5 else "missing"
    
    # 低唤醒度：平静
    if arousal < 0.3:
        return "calm"
    
    # 高效价：开心/满足
    if valence > 0.7:
        return "happy" if arousal > 0.6 else "content"
    
    # 低效价：无聊/担心
    if valence < 0.3:
        return "bored" if arousal < 0.4 else "concerned"
    
    # 默认：平静
    return "calm"
```

#### 2.3.3 情绪合并策略

```python
def merge_emotion(evolved: EmotionState, llm_assessed: EmotionState) -> EmotionState:
    """
    合并演化值和 LLM 评估值
    
    设计原则：
    1. LLM 评估权重更高（0.6），因为 LLM 能理解上下文
    2. 演化值作为基础（0.4），保持情绪连续性
    3. 主导情绪优先采用 LLM 的判断（如果 LLM 有高唤醒度）
    
    参数说明：
    - weight_evolved: 演化值权重，默认 0.4
    - weight_llm: LLM 评估权重，默认 0.6
    
    边界条件：
    - 如果 LLM 评估失败，返回演化值
    - 如果演化值过期（>1小时），增加 LLM 权重
    """
    # 读取配置的权重
    config = ActiveConsciousnessService.get_config()
    emotion_config = config.get("emotion", {})
    weight_evolved = float(emotion_config.get("weight_evolved", "0.4"))
    weight_llm = float(emotion_config.get("weight_llm", "0.6"))
    
    # 检查演化值是否过期
    if evolved.is_stale(minutes=60):
        weight_evolved = 0.2
        weight_llm = 0.8
    
    # 合并数值
    merged_valence = evolved.valence * weight_evolved + llm_assessed.valence * weight_llm
    merged_arousal = evolved.arousal * weight_evolved + llm_assessed.arousal * weight_llm
    merged_social_need = evolved.social_need * weight_evolved + llm_assessed.social_need * weight_llm
    
    # 主导情绪选择：如果 LLM 唤醒度高，采用 LLM 的判断
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

### 2.4 接口定义

#### 2.4.1 get_emotion_state()

```python
def get_emotion_state() -> EmotionState:
    """
    获取当前情绪状态
    
    返回：EmotionState 对象
    
    异常处理：
    - 如果 configs 表中没有情绪数据，返回默认值
    - 如果 JSON 解析失败，返回默认值
    
    日志记录：
    - 读取成功：debug 级别
    - 读取失败：warning 级别
    """
    db = ActiveSession()
    try:
        # 从 configs 表读取 JSON 格式的情绪状态
        value = ConfigService.get_config(db, "active_consciousness.emotion_state")
        if value:
            try:
                data = json.loads(value)
                return EmotionState.from_dict(data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("解析情绪状态失败: %s", e)
        
        # 返回默认值
        return EmotionState()
    finally:
        db.close()
```

#### 2.4.2 update_emotion_state()

```python
def update_emotion_state(state: EmotionState) -> bool:
    """
    更新情绪状态到数据库
    
    参数：
    - state: EmotionState 对象
    
    返回：是否成功
    
    异常处理：
    - 数据库写入失败：记录错误日志，返回 False
    
    日志记录：
    - 更新成功：info 级别，记录新值
    - 更新失败：error 级别
    """
    db = ActiveSession()
    try:
        # 转换为 JSON 并保存
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
```

### 2.5 存储设计

#### 2.5.1 使用 configs 表存储

```sql
-- 不需要新建表，使用现有的 configs 表
-- key: active_consciousness.emotion_state
-- value: JSON 格式的情绪状态

-- 示例数据：
-- key: "active_consciousness.emotion_state"
-- value: '{"valence": 0.6, "arousal": 0.4, "dominant": "content", "social_need": 0.3, "updated_at": "2026-06-16T10:30:00"}'
```

#### 2.5.2 向后兼容方案

```python
def get_emotional_intensity_compat() -> float:
    """
    向后兼容：获取旧格式的情绪强度
    
    用于：
    1. 旧 API 仍然返回 emotional_intensity
    2. 旧的决策逻辑可能还在使用
    
    实现：
    - 优先从新的 EmotionState 计算
    - 如果没有，从旧的 configs 读取
    """
    # 尝试从新的 EmotionState 计算
    emotion_state = get_emotion_state()
    if emotion_state:
        return emotion_state.intensity()
    
    # 回退到旧的读取方式
    db = ActiveSession()
    try:
        val = ConfigService.get_config(db, "active_consciousness.current.emotional_intensity")
        return float(val) if val else 0.0
    except Exception:
        return 0.0
    finally:
        db.close()
```

### 2.6 配置项列表

```python
# 新增配置项（添加到 _DEFAULTS）

_DEFAULTS = {
    # ... 现有配置 ...
    
    # 情绪演化
    "active_consciousness.emotion.decay_rate": "0.02",           # arousal 每小时衰减率
    "active_consciousness.emotion.social_need_growth": "0.01",   # social_need 每小时增长率
    "active_consciousness.emotion.valence_regression": "0.1",    # valence 回归中性系数
    "active_consciousness.emotion.weight_evolved": "0.4",        # 演化值权重
    "active_consciousness.emotion.weight_llm": "0.6",            # LLM 评估权重
}
```

### 2.7 测试用例

```python
# backend/tests/test_emotion_evolution.py

import pytest
from datetime import datetime, timedelta
from models.active_consciousness import EmotionState, DominantEmotion
from services.active_consciousness_service import (
    evolve_emotion, calculate_dominant, merge_emotion
)


class TestEmotionState:
    """EmotionState 数据类测试"""
    
    def test_default_values(self):
        """测试默认值"""
        state = EmotionState()
        assert state.valence == 0.5
        assert state.arousal == 0.3
        assert state.dominant == "calm"
        assert state.social_need == 0.3
    
    def test_boundary_clamping(self):
        """测试边界值截断"""
        state = EmotionState(valence=1.5, arousal=-0.1)
        assert state.valence == 1.0
        assert state.arousal == 0.0
    
    def test_to_dict(self):
        """测试转换为字典"""
        state = EmotionState(valence=0.6, arousal=0.4)
        d = state.to_dict()
        assert d["valence"] == 0.6
        assert d["arousal"] == 0.4
        assert "updated_at" in d
    
    def test_from_dict(self):
        """测试从字典创建"""
        d = {"valence": 0.7, "arousal": 0.5, "dominant": "happy"}
        state = EmotionState.from_dict(d)
        assert state.valence == 0.7
        assert state.dominant == "happy"
    
    def test_intensity(self):
        """测试综合强度计算"""
        state = EmotionState(valence=0.6, arousal=0.4, social_need=0.3)
        assert abs(state.intensity() - 0.433) < 0.01


class TestEvolveEmotion:
    """情绪演化测试"""
    
    def test_no_evolution(self):
        """测试无时间流逝"""
        last = EmotionState(arousal=0.5, social_need=0.3)
        evolved = evolve_emotion(last, minutes_since_update=0)
        assert evolved.arousal == 0.5
        assert evolved.social_need == 0.3
    
    def test_arousal_decay(self):
        """测试 arousal 衰减"""
        last = EmotionState(arousal=0.8)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.arousal < 0.8
    
    def test_social_need_growth(self):
        """测试 social_need 增长"""
        last = EmotionState(social_need=0.2)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.social_need > 0.2
    
    def test_valence_regression(self):
        """测试 valence 回归中性"""
        # 高效价应该下降
        last_high = EmotionState(valence=0.8)
        evolved_high = evolve_emotion(last_high, minutes_since_update=60)
        assert evolved_high.valence < 0.8
        
        # 低效价应该上升
        last_low = EmotionState(valence=0.2)
        evolved_low = evolve_emotion(last_low, minutes_since_update=60)
        assert evolved_low.valence > 0.2
    
    def test_boundary_minutes(self):
        """测试时间边界"""
        last = EmotionState(arousal=0.5)
        
        # 负数时间视为 0
        evolved_neg = evolve_emotion(last, minutes_since_update=-10)
        assert evolved_neg.arousal == 0.5
        
        # 超过 24 小时截断为 1440 分钟
        evolved_long = evolve_emotion(last, minutes_since_update=2000)
        assert evolved_long.arousal >= 0.1  # 最低值


class TestCalculateDominant:
    """主导情绪计算测试"""
    
    def test_high_social_need(self):
        """测试高社交需求"""
        assert calculate_dominant(0.6, 0.5, 0.8) == "yearning"
        assert calculate_dominant(0.4, 0.5, 0.8) == "anxious"
    
    def test_medium_social_need(self):
        """测试中等社交需求"""
        assert calculate_dominant(0.6, 0.5, 0.6) == "longing"
        assert calculate_dominant(0.4, 0.5, 0.6) == "missing"
    
    def test_low_arousal(self):
        """测试低唤醒度"""
        assert calculate_dominant(0.5, 0.2, 0.3) == "calm"
    
    def test_high_valence(self):
        """测试高效价"""
        assert calculate_dominant(0.8, 0.7, 0.3) == "happy"
        assert calculate_dominant(0.8, 0.5, 0.3) == "content"
    
    def test_low_valence(self):
        """测试低效价"""
        assert calculate_dominant(0.2, 0.3, 0.3) == "bored"
        assert calculate_dominant(0.2, 0.5, 0.3) == "concerned"


class TestMergeEmotion:
    """情绪合并测试"""
    
    def test_normal_merge(self):
        """测试正常合并"""
        evolved = EmotionState(valence=0.4, arousal=0.3, social_need=0.2)
        llm = EmotionState(valence=0.6, arousal=0.5, social_need=0.4)
        
        merged = merge_emotion(evolved, llm)
        
        # 权重 0.4 + 0.6
        expected_valence = 0.4 * 0.4 + 0.6 * 0.6
        assert abs(merged.valence - expected_valence) < 0.01
    
    def test_high_arousal_llm(self):
        """测试 LLM 高唤醒度时采用其主导情绪"""
        evolved = EmotionState(dominant="calm")
        llm = EmotionState(arousal=0.7, dominant="happy")
        
        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "happy"
    
    def test_low_arousal_llm(self):
        """测试 LLM 低唤醒度时保留演化值的主导情绪"""
        evolved = EmotionState(dominant="longing")
        llm = EmotionState(arousal=0.5, dominant="calm")
        
        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "longing"
```

### 2.8 验收标准

- [ ] EmotionState 数据类定义完成，包含所有字段和方法
- [ ] get_emotion_state() 能正确读取当前情绪
- [ ] update_emotion_state() 能正确更新情绪
- [ ] evolve_emotion() 函数实现，情绪随时间正确演化
- [ ] calculate_dominant() 函数实现，主导情绪计算正确
- [ ] merge_emotion() 函数实现，合并逻辑正确
- [ ] 向后兼容：旧的 emotional_intensity 仍可读取
- [ ] 所有单元测试通过

---

## 三、Phase 2：时间窗口决策

### 3.1 目标和背景

**目标**：根据当前时间调整决策权重，让凯莉在合适的时间发送消息。

**背景**：
- 深夜发送消息会打扰用户休息
- 工作时间发送消息可能影响用户工作
- 早安、晚安消息应该在特定时间窗口发送

### 3.2 数据结构定义

#### 3.2.1 时间窗口配置

```python
# 时间窗口权重表
TIME_FITNESS_TABLE = [
    # (start_hour, end_hour, fitness, label)
    # 设计原则：
    # - 早安窗口 (7-9): 权重 1.0，适合发送早安消息
    # - 工作时间 (9-12): 权重 0.8，可以发送但不要太频繁
    # - 午休时间 (12-14): 权重 0.9，适合轻松聊天
    # - 工作时间 (14-18): 权重 0.7，尽量少打扰
    # - 下班时间 (18-22): 权重 1.0，最适合聊天
    # - 睡前时间 (22-23.5): 权重 0.8，适合晚安消息
    # - 深夜 (23.5-7): 权重 0.3，尽量不打扰
    (7, 9, 1.0, "早安窗口"),
    (9, 12, 0.8, "工作时间"),
    (12, 14, 0.9, "午休时间"),
    (14, 18, 0.7, "工作时间"),
    (18, 22, 1.0, "下班时间"),
    (22, 23.5, 0.8, "睡前时间"),
    (23.5, 7, 0.3, "深夜"),
]
```

### 3.3 算法逻辑

#### 3.3.1 时间权重计算

```python
def get_time_fitness() -> tuple[float, str]:
    """
    获取当前时间的合适度权重
    
    返回：(fitness_score, time_label)
    
    物理意义：
    - fitness_score: 0-1 之间的权重，表示当前时间发送消息的合适程度
    - time_label: 时间段标签，用于日志和调试
    
    边界条件：
    - 23:30 应该属于"深夜"（23.5-7）
    - 00:00 应该属于"深夜"
    - 6:59 应该属于"深夜"
    - 7:00 应该属于"早安窗口"
    """
    now = datetime.now()
    hour = now.hour + now.minute / 60  # 转换为小数小时
    
    # 读取配置
    config = ActiveConsciousnessService.get_config()
    time_config = config.get("time", {})
    
    # 如果时间窗口功能未启用，返回默认权重 1.0
    if not time_config.get("enabled", True):
        return 1.0, "未启用"
    
    # 遍历时间窗口表
    for start, end, fitness, label in TIME_FITNESS_TABLE:
        # 处理跨午夜的情况（如 23.5-7）
        if start > end:
            if hour >= start or hour < end:
                return fitness, label
        else:
            if start <= hour < end:
                return fitness, label
    
    # 默认返回深夜权重
    return 0.3, "深夜"
```

#### 3.3.2 多维度决策公式

```python
def make_decision_v2(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> tuple[str, str, float]:
    """
    多维度决策
    
    公式：score = intensity × time_fitness × silence_factor × frequency_limit
    
    参数说明：
    - intensity: 情绪强度（valence + arousal + social_need 的综合）
    - time_fitness: 时间窗口权重（0-1）
    - silence_factor: 空白时长因子（0-1）
    - frequency_limit: 频率限制因子（0-1）
    
    返回：(decision_type, reason, score)
    
    决策逻辑：
    - score > send_threshold → auto_send（自动发送）
    - score > delay_threshold → delay_send（延迟发送）
    - score > memory_threshold → memory（存为记忆）
    - 否则 → skip（跳过）
    
    边界条件：
    - 所有因子都在 [0, 1] 范围内
    - 最终 score 也在 [0, 1] 范围内
    """
    decision_config = config.get("decision", {})
    
    # 1. 情绪强度
    # 公式：(valence + arousal + social_need) / 3
    # 范围：[0, 1]
    intensity = emotion_state.intensity()
    
    # 2. 时间权重
    # 来自 TIME_FITNESS_TABLE
    time_fitness, time_label = get_time_fitness()
    
    # 3. 空白因子
    # 设计原则：
    # - 空白 < 1小时：权重 0.3（刚聊过，不要太频繁）
    # - 空白 1-3小时：权重 0.5（可以聊聊）
    # - 空白 3-6小时：权重 0.7（比较想聊）
    # - 空白 > 6小时：权重 0.9（非常想聊）
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
    # 公式：max(0.1, 1.0 - (hour_sent / max_per_hour))
    # 设计原则：
    # - 如果本小时已发送 max_per_hour 条，权重降到 0.1
    # - 最低保持 0.1，防止完全不发送
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
    
    # 决策
    if score > send_threshold:
        return "auto_send", f"score={score:.3f} > {send_threshold} ({reason})", score
    elif score > delay_threshold:
        return "delay_send", f"score={score:.3f} > {delay_threshold} ({reason})", score
    elif score > memory_threshold:
        return "memory", f"score={score:.3f} > {memory_threshold} ({reason})", score
    else:
        return "skip", f"score={score:.3f} <= {memory_threshold} ({reason})", score
```

### 3.4 接口定义

```python
def get_time_fitness_info() -> Dict[str, Any]:
    """
    获取时间窗口信息（用于前端展示）
    
    返回：
    - current_fitness: 当前权重
    - current_label: 当前时间段标签
    - next_change: 下次切换时间
    - fitness_table: 完整的时间窗口表
    """
    fitness, label = get_time_fitness()
    
    # 计算下次切换时间
    now = datetime.now()
    current_hour = now.hour + now.minute / 60
    
    next_change = None
    for start, end, _, _ in TIME_FITNESS_TABLE:
        if start > current_hour:
            next_change = start
            break
    
    return {
        "current_fitness": fitness,
        "current_label": label,
        "next_change_hour": next_change,
        "fitness_table": TIME_FITNESS_TABLE
    }
```

### 3.5 配置项列表

```python
# 新增配置项

_DEFAULTS = {
    # ... 现有配置 ...
    
    # 时间窗口
    "active_consciousness.time.enabled": "true",                 # 启用时间窗口
    "active_consciousness.time.deep_night_start": "23.5",        # 深夜开始（小时）
    "active_consciousness.time.deep_night_end": "7",             # 深夜结束（小时）
    "active_consciousness.time.deep_night_fitness": "0.3",       # 深夜权重
}
```

### 3.6 测试用例

```python
# backend/tests/test_decision_matrix.py

import pytest
from datetime import datetime
from unittest.mock import patch
from models.active_consciousness import EmotionState
from services.active_consciousness_service import (
    get_time_fitness, make_decision_v2
)


class TestTimeFitness:
    """时间权重测试"""
    
    @patch('services.active_consciousness_service.datetime')
    def test_morning_window(self, mock_datetime):
        """测试早安窗口 (7-9)"""
        mock_datetime.now.return_value = datetime(2026, 6, 16, 8, 0)
        fitness, label = get_time_fitness()
        assert fitness == 1.0
        assert label == "早安窗口"
    
    @patch('services.active_consciousness_service.datetime')
    def test_work_time(self, mock_datetime):
        """测试工作时间 (9-12)"""
        mock_datetime.now.return_value = datetime(2026, 6, 16, 10, 0)
        fitness, label = get_time_fitness()
        assert fitness == 0.8
        assert label == "工作时间"
    
    @patch('services.active_consciousness_service.datetime')
    def test_deep_night(self, mock_datetime):
        """测试深夜 (23:30)"""
        mock_datetime.now.return_value = datetime(2026, 6, 16, 23, 30)
        fitness, label = get_time_fitness()
        assert fitness == 0.3
        assert label == "深夜"
    
    @patch('services.active_consciousness_service.datetime')
    def test_midnight(self, mock_datetime):
        """测试午夜 (00:00)"""
        mock_datetime.now.return_value = datetime(2026, 6, 16, 0, 0)
        fitness, label = get_time_fitness()
        assert fitness == 0.3
        assert label == "深夜"


class TestDecisionV2:
    """多维度决策测试"""
    
    def test_high_score_auto_send(self):
        """测试高分自动发送"""
        config = {
            "decision": {
                "send_threshold": 0.6,
                "delay_threshold": 0.3,
                "memory_threshold": 0.1,
                "max_per_hour": 2
            }
        }
        status = {
            "longing": {"silence_minutes": 300},
            "hour_sent_count": 0
        }
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        with patch('services.active_consciousness_service.get_time_fitness', 
                   return_value=(1.0, "下班时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision == "auto_send"
            assert score > 0.6
    
    def test_medium_score_delay_send(self):
        """测试中分延迟发送"""
        config = {
            "decision": {
                "send_threshold": 0.6,
                "delay_threshold": 0.3,
                "memory_threshold": 0.1,
                "max_per_hour": 2
            }
        }
        status = {
            "longing": {"silence_minutes": 120},
            "hour_sent_count": 1
        }
        emotion = EmotionState(valence=0.5, arousal=0.4, social_need=0.3)
        
        with patch('services.active_consciousness_service.get_time_fitness', 
                   return_value=(0.8, "工作时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision == "delay_send"
            assert 0.3 < score <= 0.6
    
    def test_frequency_limit(self):
        """测试频率限制"""
        config = {
            "decision": {
                "send_threshold": 0.6,
                "max_per_hour": 2
            }
        }
        status = {
            "longing": {"silence_minutes": 300},
            "hour_sent_count": 2  # 已达到上限
        }
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        with patch('services.active_consciousness_service.get_time_fitness', 
                   return_value=(1.0, "下班时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            # 频率限制应该降低分数
            assert score < 0.6
```

### 3.7 验收标准

- [ ] get_time_fitness() 函数实现，返回正确的权重和标签
- [ ] make_decision_v2() 函数实现，使用多维度评分公式
- [ ] 时间边界处理正确（如 23:30、00:00）
- [ ] 频率限制逻辑正确
- [ ] 返回值包含完整的决策原因
- [ ] 所有单元测试通过

---

## 四、Phase 3：念头系统增强

### 4.1 目标和背景

**目标**：为念头添加结构化类型，实现念头存储到 Hindsight 的闭环。

**背景**：
- v0.2 的念头是自由文本，没有分类
- 重要念头应该存入 Hindsight，供后续回忆使用
- 不同类型的念头有不同的处理逻辑

### 4.2 数据结构定义

#### 4.2.1 念头类型说明

```python
class ThoughtType(str, Enum):
    """
    念头类型枚举
    
    类型说明：
    - TIME: 时间念头，基于当前时间生成
      示例："23:30了，该睡了"
      触发条件：特定时间点（如早安、晚安、午休）
    
    - SILENCE: 空白念头，基于沉默时长生成
      示例："好久没说话了"
      触发条件：长时间无消息（>2小时）
    
    - ASSOCIATION: 关联念头，基于上下文关联生成
      示例："今天周五，一般加班"
      触发条件：特定日期、事件关联
    
    - MEMORY: 回忆念头，基于 Hindsight 回忆生成
      示例："想起你说过..."
      触发条件：Hindsight 返回相关记忆
    
    - EMOTION: 情绪念头，基于当前情绪生成
      示例："现在有点兴奋"
      触发条件：情绪强度 > 0.5
    
    - ENVIRONMENT: 环境念头，基于外部环境生成
      示例："外面下雨了"
      触发条件：天气变化、特殊天气
    """
    TIME = "time"
    SILENCE = "silence"
    ASSOCIATION = "assoc"
    MEMORY = "memory"
    EMOTION = "emotion"
    ENVIRONMENT = "env"
```

### 4.3 算法逻辑

#### 4.3.1 念头类型判断

```python
def determine_thought_type(
    status: Dict[str, Any],
    emotion_state: EmotionState,
    hindsight_results: List[Dict],
    weather_info: Optional[Dict]
) -> ThoughtType:
    """
    根据上下文判断念头类型
    
    优先级：
    1. 如果有 Hindsight 回忆 → MEMORY
    2. 如果有特殊天气 → ENVIRONMENT
    3. 如果情绪强度高 → EMOTION
    4. 如果沉默时间长 → SILENCE
    5. 如果是特殊时间点 → TIME
    6. 默认 → ASSOCIATION
    """
    # 1. 有回忆
    if hindsight_results and len(hindsight_results) > 0:
        return ThoughtType.MEMORY
    
    # 2. 特殊天气
    if weather_info and weather_info.get("weather") in ["雨", "雪", "大风", "雷阵雨"]:
        return ThoughtType.ENVIRONMENT
    
    # 3. 情绪强度高
    if emotion_state.intensity() > 0.5:
        return ThoughtType.EMOTION
    
    # 4. 沉默时间长
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes > 120:  # 2小时
        return ThoughtType.SILENCE
    
    # 5. 特殊时间点
    now = datetime.now()
    if now.hour in [7, 8, 12, 13, 22, 23]:
        return ThoughtType.TIME
    
    # 6. 默认
    return ThoughtType.ASSOCIATION
```

#### 4.3.2 念头存储到 Hindsight

```python
async def retain_thought(
    thought: str,
    emotion_state: EmotionState,
    thought_type: ThoughtType,
    score: float
) -> bool:
    """
    将重要念头存入 Hindsight
    
    存储条件（满足任一即可）：
    1. 情绪强度 > 0.5
    2. 包含用户名字（如"曹凡"）
    3. 决策为"发送"
    4. 分数 > 0.5
    
    参数：
    - thought: 念头内容
    - emotion_state: 当前情绪状态
    - thought_type: 念头类型
    - score: 决策分数
    
    返回：是否成功存储
    """
    # 读取配置
    config = ActiveConsciousnessService.get_config()
    thought_config = config.get("thought", {})
    
    # 检查是否启用
    if not thought_config.get("retain_enabled", True):
        return False
    
    # 检查存储条件
    retain_threshold = float(thought_config.get("retain_threshold", "0.5"))
    intensity = emotion_state.intensity()
    
    should_retain = (
        intensity > retain_threshold or
        "曹凡" in thought or
        score > retain_threshold
    )
    
    if not should_retain:
        return False
    
    # 存储到 Hindsight
    try:
        hindsight_config = config.get("hindsight", {})
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        timeout = float(hindsight_config.get("timeout", 30))
        
        client = get_hindsight_client(base_url=base_url, timeout=timeout)
        
        # 构建内容
        content = f"[{thought_type.value}] {thought}"
        
        # 构建标签
        tags = ["thought", thought_type.value, emotion_state.dominant]
        
        # 存储
        await client.aretain(
            bank_id=bank_id,
            content=content,
            tags=tags
        )
        
        logger.info("念头已存入 Hindsight: type=%s, content=%s", 
                    thought_type.value, thought[:50])
        return True
        
    except Exception as e:
        logger.warning("存入 Hindsight 失败: %s", e)
        return False
```

#### 4.3.3 回忆念头生成

```python
async def generate_memory_thought(
    hindsight_results: List[Dict],
    emotion_state: EmotionState
) -> Optional[str]:
    """
    基于 Hindsight 回忆生成念头
    
    逻辑：
    1. 从 Hindsight 结果中提取关键信息
    2. 结合当前情绪状态
    3. 生成"想起你说过..."类型的念头
    
    返回：念头文本，或 None（如果无法生成）
    """
    if not hindsight_results:
        return None
    
    # 选择最相关的一条记忆
    memory = hindsight_results[0]
    memory_text = memory.get("text", "")
    
    if not memory_text:
        return None
    
    # 截取关键部分
    if len(memory_text) > 100:
        memory_text = memory_text[:100] + "..."
    
    # 根据情绪状态生成不同的开头
    if emotion_state.dominant in ["longing", "missing", "yearning"]:
        prefix = "突然想起"
    elif emotion_state.dominant in ["happy", "content"]:
        prefix = "想起"
    else:
        prefix = "记得"
    
    return f"{prefix}你说过：{memory_text}"
```

### 4.4 接口定义

```python
def get_thought_type_stats(days: int = 7) -> Dict[str, int]:
    """
    获取念头类型统计
    
    参数：
    - days: 统计天数
    
    返回：
    - 各类型的数量统计
    """
    db = ActiveSession()
    try:
        with active_engine.connect() as conn:
            # 查询最近 N 天的念头类型统计
            result = conn.execute(text("""
                SELECT type, COUNT(*) as count
                FROM active_thought_logs
                WHERE created_at > datetime('now', :days_param)
                GROUP BY type
            """), {"days_param": f"-{days} days"}).fetchall()
            
            stats = {}
            for row in result:
                stats[row[0]] = row[1]
            
            return stats
    except Exception as e:
        logger.error("查询念头类型统计失败: %s", e)
        return {}
    finally:
        db.close()
```

### 4.5 配置项列表

```python
# 新增配置项

_DEFAULTS = {
    # ... 现有配置 ...
    
    # 念头存储
    "active_consciousness.thought.retain_enabled": "true",       # 启用念头存储
    "active_consciousness.thought.retain_threshold": "0.5",      # 存储阈值
}
```

### 4.6 测试用例

```python
# backend/tests/test_thought_retention.py

import pytest
from models.active_consciousness import EmotionState, ThoughtType
from services.active_consciousness_service import (
    determine_thought_type, retain_thought
)


class TestThoughtType:
    """念头类型测试"""
    
    def test_memory_type(self):
        """测试回忆类型"""
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        hindsight = [{"text": "你说过喜欢看电影"}]
        
        result = determine_thought_type(status, emotion, hindsight, None)
        assert result == ThoughtType.MEMORY
    
    def test_emotion_type(self):
        """测试情绪类型"""
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        result = determine_thought_type(status, emotion, [], None)
        assert result == ThoughtType.EMOTION
    
    def test_silence_type(self):
        """测试空白类型"""
        status = {"longing": {"silence_minutes": 180}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        
        result = determine_thought_type(status, emotion, [], None)
        assert result == ThoughtType.SILENCE


class TestRetainThought:
    """念头存储测试"""
    
    @pytest.mark.asyncio
    async def test_high_intensity_retain(self):
        """测试高强度情绪存储"""
        thought = "今天好开心啊"
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        # Mock Hindsight client
        with patch('services.active_consciousness_service.get_hindsight_client') as mock_client:
            mock_client.return_value.aretain = AsyncMock()
            
            result = await retain_thought(thought, emotion, ThoughtType.EMOTION, 0.7)
            assert result == True
            mock_client.return_value.aretain.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_low_intensity_no_retain(self):
        """测试低强度不存储"""
        thought = "今天天气不错"
        emotion = EmotionState(valence=0.4, arousal=0.3, social_need=0.2)
        
        result = await retain_thought(thought, emotion, ThoughtType.ASSOCIATION, 0.3)
        assert result == False
```

### 4.7 验收标准

- [ ] ThoughtType 枚举定义完成
- [ ] determine_thought_type() 函数实现
- [ ] retain_thought() 函数实现
- [ ] 念头日志记录类型
- [ ] LLM prompt 输出包含类型
- [ ] 重要念头自动存入 Hindsight
- [ ] 所有单元测试通过

---

## 五、Phase 4：延迟发送队列

### 5.1 目标和背景

**目标**：存储 score 在 delay_threshold 和 send_threshold 之间的念头，在合适时机发送。

**背景**：
- 有些念头分数不够高，直接发送可能不合适
- 但这些念头可能在稍后的时间点变得合适
- 需要一个队列来管理这些"待定"的念头

### 5.2 数据结构定义

#### 5.2.1 延迟队列存储

```python
# 使用 configs 表存储延迟队列
# key: active_consciousness.delayed_thoughts
# value: JSON 数组格式

# 示例：
# [
#   {
#     "id": 1,
#     "content": "今天天气不错",
#     "thought_type": "env",
#     "score": 0.45,
#     "created_at": "2026-06-16T10:30:00",
#     "retry_count": 0,
#     "next_retry_at": "",
#     "emotion_snapshot": {"valence": 0.5, "arousal": 0.3}
#   }
# ]
```

### 5.3 算法逻辑

#### 5.3.1 延迟队列读取

```python
def get_delayed_thoughts() -> List[DelayedThought]:
    """
    获取延迟队列中的念头
    
    返回：DelayedThought 列表
    
    异常处理：
    - JSON 解析失败：返回空列表
    - 数据库读取失败：返回空列表
    """
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
    """
    保存延迟队列
    
    参数：
    - thoughts: DelayedThought 列表
    
    返回：是否成功
    """
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
```

#### 5.3.2 延迟念头重新评估

```python
async def reevaluate_delayed_thoughts(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Dict[str, int]:
    """
    重新评估延迟队列中的念头
    
    处理逻辑：
    1. 遍历每个延迟念头
    2. 重新计算 score（基于当前情绪和时间）
    3. 判断处理方式：
       - score > send_threshold → 升级为发送
       - score < 0.1 → 降级为丢弃
       - 否则 → 保持延迟，更新 score
    
    返回：处理统计 {"sent": int, "discarded": int, "kept": int}
    """
    # 读取配置
    delay_config = config.get("delay", {})
    max_retry = int(delay_config.get("max_retry", 3))
    retry_interval = int(delay_config.get("retry_interval_minutes", 30))
    
    decision_config = config.get("decision", {})
    send_threshold = decision_config.get("send_threshold", 0.6)
    
    # 读取延迟队列
    delayed_thoughts = get_delayed_thoughts()
    if not delayed_thoughts:
        return {"sent": 0, "discarded": 0, "kept": 0}
    
    stats = {"sent": 0, "discarded": 0, "kept": 0}
    remaining_thoughts = []
    
    for thought in delayed_thoughts:
        # 检查是否超过最大重试次数
        if thought.retry_count >= max_retry:
            stats["discarded"] += 1
            logger.info("延迟念头超过最大重试次数，丢弃: %s", thought.content[:30])
            continue
        
        # 检查是否到了重试时间
        if thought.next_retry_at:
            try:
                next_retry = datetime.fromisoformat(thought.next_retry_at)
                if datetime.now() < next_retry:
                    # 还没到重试时间，保持延迟
                    remaining_thoughts.append(thought)
                    stats["kept"] += 1
                    continue
            except Exception:
                pass
        
        # 重新计算 score
        new_score = recalculate_thought_score(thought, status, emotion_state, config)
        
        # 判断处理方式
        if new_score > send_threshold:
            # 升级为发送
            success = await send_message_to_target(config, thought.content)
            if success:
                stats["sent"] += 1
                logger.info("延迟念头升级为发送: score=%.3f, content=%s", 
                           new_score, thought.content[:30])
            else:
                # 发送失败，保留在队列中
                thought.retry_count += 1
                thought.next_retry_at = (
                    datetime.now() + timedelta(minutes=retry_interval)
                ).isoformat()
                remaining_thoughts.append(thought)
                stats["kept"] += 1
        elif new_score < 0.1:
            # 降级为丢弃
            stats["discarded"] += 1
            logger.info("延迟念头降级为丢弃: score=%.3f, content=%s", 
                       new_score, thought.content[:30])
        else:
            # 保持延迟，更新 score
            thought.score = new_score
            thought.retry_count += 1
            thought.next_retry_at = (
                datetime.now() + timedelta(minutes=retry_interval)
            ).isoformat()
            remaining_thoughts.append(thought)
            stats["kept"] += 1
    
    # 保存更新后的队列
    save_delayed_thoughts(remaining_thoughts)
    
    return stats
```

#### 5.3.3 延迟念头分数重算

```python
def recalculate_thought_score(
    thought: DelayedThought,
    status: Dict[str, Any],
    emotion_state: EmotionState,
    config: Dict[str, Any]
) -> float:
    """
    重新计算延迟念头的分数
    
    逻辑：
    1. 获取当前情绪状态
    2. 获取当前时间权重
    3. 获取沉默时长
    4. 应用决策公式
    
    返回：新的分数
    """
    # 获取时间权重
    time_fitness, _ = get_time_fitness()
    
    # 获取沉默因子
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < 60:
        silence_factor = 0.3
    elif silence_minutes < 180:
        silence_factor = 0.5
    elif silence_minutes < 360:
        silence_factor = 0.7
    else:
        silence_factor = 0.9
    
    # 获取频率限制
    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = config.get("decision", {}).get("max_per_hour", 2)
    frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))
    
    # 计算新的情绪强度
    intensity = emotion_state.intensity()
    
    # 应用决策公式
    new_score = intensity * time_fitness * silence_factor * frequency_limit
    
    return new_score
```

### 5.4 接口定义

```python
def get_delayed_thoughts_list() -> List[Dict[str, Any]]:
    """
    获取延迟队列列表（用于前端展示）
    
    返回：延迟念头字典列表
    """
    thoughts = get_delayed_thoughts()
    return [t.to_dict() for t in thoughts]


def clear_delayed_thoughts() -> bool:
    """
    清空延迟队列
    
    返回：是否成功
    """
    return save_delayed_thoughts([])


def remove_delayed_thought(thought_id: int) -> bool:
    """
    移除指定的延迟念头
    
    参数：
    - thought_id: 念头 ID
    
    返回：是否成功
    """
    thoughts = get_delayed_thoughts()
    thoughts = [t for t in thoughts if t.id != thought_id]
    return save_delayed_thoughts(thoughts)
```

### 5.5 配置项列表

```python
# 新增配置项

_DEFAULTS = {
    # ... 现有配置 ...
    
    # 延迟发送
    "active_consciousness.delay.enabled": "true",                # 启用延迟发送
    "active_consciousness.delay.max_retry": "3",                 # 最大重试次数
    "active_consciousness.delay.retry_interval_minutes": "30",   # 重试间隔（分钟）
    "active_consciousness.delay.max_queue_size": "10",           # 最大队列长度
}
```

### 5.6 测试用例

```python
# backend/tests/test_delay_queue.py

import pytest
from datetime import datetime, timedelta
from models.active_consciousness import EmotionState, DelayedThought
from services.active_consciousness_service import (
    get_delayed_thoughts, save_delayed_thoughts,
    reevaluate_delayed_thoughts
)


class TestDelayedThought:
    """延迟念头测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        thought = DelayedThought(
            id=1,
            content="测试内容",
            thought_type="emotion",
            score=0.45,
            created_at="2026-06-16T10:30:00"
        )
        d = thought.to_dict()
        assert d["id"] == 1
        assert d["content"] == "测试内容"
        assert d["score"] == 0.45
    
    def test_from_dict(self):
        """测试从字典创建"""
        d = {
            "id": 1,
            "content": "测试内容",
            "thought_type": "emotion",
            "score": 0.45,
            "created_at": "2026-06-16T10:30:00"
        }
        thought = DelayedThought.from_dict(d)
        assert thought.id == 1
        assert thought.score == 0.45


class TestDelayedQueue:
    """延迟队列测试"""
    
    def test_save_and_get(self):
        """测试保存和读取"""
        thoughts = [
            DelayedThought(id=1, content="测试1", thought_type="emotion", 
                          score=0.4, created_at="2026-06-16T10:30:00"),
            DelayedThought(id=2, content="测试2", thought_type="silence", 
                          score=0.35, created_at="2026-06-16T11:30:00"),
        ]
        
        # Mock ConfigService
        with patch('services.active_consciousness_service.ConfigService') as mock_config:
            mock_config.get_config.return_value = json.dumps(
                [t.to_dict() for t in thoughts]
            )
            
            result = get_delayed_thoughts()
            assert len(result) == 2
            assert result[0].content == "测试1"


class TestReevaluate:
    """重新评估测试"""
    
    @pytest.mark.asyncio
    async def test_upgrade_to_send(self):
        """测试升级为发送"""
        config = {
            "decision": {"send_threshold": 0.6, "max_per_hour": 2},
            "delay": {"max_retry": 3, "retry_interval_minutes": 30}
        }
        status = {
            "longing": {"silence_minutes": 300},
            "hour_sent_count": 0
        }
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        # Mock 函数
        with patch('services.active_consciousness_service.get_delayed_thoughts') as mock_get, \
             patch('services.active_consciousness_service.send_message_to_target') as mock_send, \
             patch('services.active_consciousness_service.get_time_fitness', 
                   return_value=(1.0, "下班时间")):
            
            mock_get.return_value = [
                DelayedThought(id=1, content="测试", thought_type="emotion", 
                              score=0.4, created_at="2026-06-16T10:30:00")
            ]
            mock_send.return_value = True
            
            stats = await reevaluate_delayed_thoughts(config, status, emotion)
            assert stats["sent"] == 1
            mock_send.assert_called_once()
```

### 5.7 验收标准

- [ ] DelayedThought 数据结构定义完成
- [ ] get_delayed_thoughts() 函数实现
- [ ] save_delayed_thoughts() 函数实现
- [ ] reevaluate_delayed_thoughts() 函数实现
- [ ] 心跳时自动调用重评估
- [ ] 升级/降级/保持逻辑正确
- [ ] 发送后从队列移除
- [ ] 超过最大重试次数自动丢弃
- [ ] 所有单元测试通过

---

## 六、执行流程图

### 6.1 心跳主流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              心跳主流程                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 1. 心跳触发   │
                            │ (定时器)      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 2. 读取配置   │
                            │ (consciousness.*) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 3. 读取当前   │
                            │ 情绪状态      │
                            │ (EmotionState) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 4. 计算时间   │
                            │ 间隔          │
                            │ (minutes_since) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 5. 调用       │
                            │ evolve_emotion() │
                            │ 演化情绪      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 6. 获取时间   │
                            │ 窗口权重      │
                            │ (get_time_fitness) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 7. 获取沉默   │
                            │ 时长          │
                            │ (silence_minutes) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 8. 读取延迟   │
                            │ 队列          │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 9. LLM 评估   │
                            │ 输入：        │
                            │ - 近期 session │
                            │ - Hindsight   │
                            │ - 天气        │
                            │ - 当前情绪    │
                            │ 输出：        │
                            │ - 新 VA 值    │
                            │ - 念头        │
                            │ - 念头类型    │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 10. 合并情绪  │
                            │ (演化值 + LLM) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 11. 决策计算  │
                            │ (make_decision_v2) │
                            └───────┬───────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ auto_send │   │delay_send │   │  memory   │
            │ 生成消息  │   │ 入延迟队列│   │ 存入      │
            │ 发送      │   │           │   │ Hindsight │
            │ 记录日志  │   │           │   │           │
            └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                  │               │               │
                  └───────────────┼───────────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 12. 重评估    │
                          │ 延迟队列      │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 13. 更新状态  │
                          │ 到数据库      │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 14. 记录      │
                          │ 心跳日志      │
                          └───────────────┘
```

### 6.2 消息发送流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              消息发送流程                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 1. 接收发送   │
                            │ 请求          │
                            │ (content,     │
                            │  emotion,     │
                            │  thought_type) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 2. 生成消息   │
                            │ 内容 (LLM)    │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 3. 调用       │
                            │ send-and-inject │
                            │ API           │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 4. 更新最后   │
                            │ 发送时间      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 5. 触发       │
                            │ 冷却期        │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 6. 更新       │
                            │ 发送计数      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 7. 保存       │
                            │ 情绪状态      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 8. 存入       │
                            │ Hindsight     │
                            │ (如果符合条件) │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 9. 记录       │
                            │ 发送日志      │
                            └───────────────┘
```

### 6.3 延迟队列处理流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            延迟队列处理流程                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 1. 读取       │
                            │ 延迟队列      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 2. 遍历每个   │
                            │ 延迟念头      │
                            └───────┬───────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 3. 计算新     │
                            │ score         │
                            │ - 当前情绪    │
                            │ - 时间权重    │
                            │ - 沉默时长    │
                            │ - 频率限制    │
                            └───────┬───────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │score > 0.6│   │0.1 < score│   │score < 0.1│
            │ 升级      │   │  ≤ 0.6    │   │ 降级      │
            │ 发送      │   │ 保持      │   │ 丢弃      │
            └─────┬─────┘   │ 延迟      │   └─────┬─────┘
                  │         └─────┬─────┘         │
                  │               │               │
                  └───────────────┼───────────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 4. 更新队列   │
                          │ 状态          │
                          └───────────────┘
```

### 6.4 异常处理流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              异常处理流程                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │ 异常发生      │
                            └───────┬───────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ LLM 调用  │   │ 数据库    │   │ 消息发送  │
            │ 失败      │   │ 操作失败  │   │ 失败      │
            └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                  │               │               │
                  ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ 使用规则  │   │ 记录错误  │   │ 加入      │
            │ 引擎兜底  │   │ 日志      │   │ 延迟队列  │
            └─────┬─────┘   └─────┬─────┘   │ 重试      │
                  │               │         └─────┬─────┘
                  │               │               │
                  └───────────────┼───────────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 记录异常日志  │
                          │ (vibe_logs)   │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 继续执行      │
                          │ (不中断心跳)  │
                          └───────────────┘
```

---

## 七、风险评估

### 7.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 情绪演化过于激进 | 行为不可预测 | 中 | 设置边界值，衰减率可配置 |
| LLM 输出不稳定 | 情绪评估不准 | 高 | 规则引擎兜底，LLM 作为参考 |
| 延迟队列积压 | 内存占用 | 低 | 设置最大队列长度，过期清理 |
| 时间窗口边界错误 | 决策异常 | 低 | 完善单元测试，覆盖边界情况 |

### 7.2 性能风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 心跳间隔太短 | 系统负载高 | 中 | 默认 10 分钟，可配置 |
| LLM 调用超时 | 心跳阻塞 | 中 | 设置超时时间，异步调用 |
| 数据库写入频繁 | I/O 压力 | 低 | 批量写入，减少写入次数 |

### 7.3 兼容性风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 旧 API 不兼容 | 前端报错 | 低 | 保留旧 API，添加新 API |
| 配置格式变化 | 配置丢失 | 低 | 向后兼容，自动迁移 |
| 数据库结构变化 | 数据丢失 | 低 | 使用 configs 表，无需迁移 |

### 7.4 缓解措施总结

1. **配置优先**：所有阈值、权重都从 configs 表读取，支持动态调整
2. **规则引擎兜底**：LLM 失败时使用规则引擎，保证基本功能
3. **边界值保护**：所有数值都有 min/max 限制，防止异常值
4. **向后兼容**：旧 API 保留，旧配置可读取
5. **日志完善**：每个步骤都有日志记录，便于排查问题

---

## 八、工作量估算

### 8.1 Phase 1：情绪连续性（核心）

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 1.1 EmotionState 数据类 | 0.5 小时 | 无 |
| 1.2 get/update_emotion_state | 1 小时 | 1.1 |
| 1.3 evolve_emotion | 1 小时 | 1.1 |
| 1.4 calculate_dominant | 0.5 小时 | 1.1 |
| 1.5 merge_emotion | 0.5 小时 | 1.1 |
| 1.6 单元测试 | 1 小时 | 1.2-1.5 |
| **小计** | **4.5 小时** | |

### 8.2 Phase 2：时间窗口决策

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 2.1 get_time_fitness | 0.5 小时 | 无 |
| 2.2 make_decision_v2 | 1 小时 | 2.1 |
| 2.3 集成到心跳 | 0.5 小时 | 2.2 |
| 2.4 单元测试 | 0.5 小时 | 2.1-2.3 |
| **小计** | **2.5 小时** | |

### 8.3 Phase 3：念头系统增强

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 3.1 ThoughtType 枚举 | 0.5 小时 | 无 |
| 3.2 determine_thought_type | 0.5 小时 | 3.1 |
| 3.3 retain_thought | 1 小时 | 3.1 |
| 3.4 集成到心跳 | 0.5 小时 | 3.2-3.3 |
| 3.5 单元测试 | 0.5 小时 | 3.1-3.4 |
| **小计** | **3 小时** | |

### 8.4 Phase 4：延迟发送队列

| 任务 | 预计时间 | 依赖 |
|------|----------|------|
| 4.1 DelayedThought 数据类 | 0.5 小时 | 无 |
| 4.2 get/save_delayed_thoughts | 0.5 小时 | 4.1 |
| 4.3 reevaluate_delayed_thoughts | 1 小时 | 4.2 |
| 4.4 集成到心跳 | 0.5 小时 | 4.3 |
| 4.5 单元测试 | 0.5 小时 | 4.1-4.4 |
| **小计** | **3 小时** | |

### 8.5 总计

| Phase | 预计时间 |
|-------|----------|
| Phase 1：情绪连续性 | 4.5 小时 |
| Phase 2：时间窗口决策 | 2.5 小时 |
| Phase 3：念头系统增强 | 3 小时 |
| Phase 4：延迟发送队列 | 3 小时 |
| **总计** | **13 小时** |

### 8.6 关键路径

```
Phase 1 (EmotionState) → Phase 2 (make_decision_v2) → Phase 4 (reevaluate)
                                    ↓
                            Phase 3 (retain_thought)
```

### 8.7 依赖关系

- Phase 1 是其他 Phase 的基础
- Phase 2 依赖 Phase 1 的 EmotionState
- Phase 3 相对独立，但需要 EmotionState
- Phase 4 依赖 Phase 2 的决策公式

---

## 九、配置项完整列表

```python
# backend/services/active_consciousness_service.py

_DEFAULTS = {
    # ========== 现有配置 ==========
    "active_consciousness.enabled": "false",
    "active_consciousness.llm.mode": "hermes",
    "active_consciousness.llm.provider": "openai",
    "active_consciousness.llm.model": "deepseek-chat",
    "active_consciousness.llm.api_key": "",
    "active_consciousness.llm.base_url": "",
    "active_consciousness.active.enabled": "true",
    "active_consciousness.active.heartbeat_interval": "600",
    "active_consciousness.active.send_tag": "[凯莉主动发送]",
    "active_consciousness.active.time_format": "%H:%M",
    "active_consciousness.active.no_send_after_user_msg_minutes": "10",
    "active_consciousness.active.no_send_while_heat_above": "0.5",
    "active_consciousness.active.no_send_while_vibe_below": "0.3",
    "active_consciousness.active.cooldown_minutes": "30",
    "active_consciousness.session.sources": '["weixin"]',
    "active_consciousness.session.time_range_hours": "24",
    "active_consciousness.session.max_messages_per_session": "15",
    "active_consciousness.session.filter_tool_messages": "true",
    "active_consciousness.decision.send_threshold": "0.6",
    "active_consciousness.decision.delay_threshold": "0.3",
    "active_consciousness.decision.memory_threshold": "0.1",
    "active_consciousness.decision.max_per_hour": "2",
    "active_consciousness.decision.max_per_day": "5",
    "active_consciousness.decision.longing_gap_threshold": "3",
    "active_consciousness.hindsight.enabled": "true",
    "active_consciousness.hindsight.base_url": "http://localhost:8888",
    "active_consciousness.hindsight.bank_id": "hermes",
    "active_consciousness.hindsight.recall_limit": "5",
    "active_consciousness.hindsight.reflect_enabled": "true",
    "active_consciousness.hindsight.timeout": "30",
    "active_consciousness.notify.platform": "weixin",
    "active_consciousness.notify.chat_id": "",
    
    # ========== v0.2.1 新增配置 ==========
    
    # 情绪演化
    "active_consciousness.emotion.decay_rate": "0.02",           # arousal 每小时衰减率
    "active_consciousness.emotion.social_need_growth": "0.01",   # social_need 每小时增长率
    "active_consciousness.emotion.valence_regression": "0.1",    # valence 回归中性系数
    "active_consciousness.emotion.weight_evolved": "0.4",        # 演化值权重
    "active_consciousness.emotion.weight_llm": "0.6",            # LLM 评估权重
    
    # 时间窗口
    "active_consciousness.time.enabled": "true",                 # 启用时间窗口
    "active_consciousness.time.deep_night_start": "23.5",        # 深夜开始（小时）
    "active_consciousness.time.deep_night_end": "7",             # 深夜结束（小时）
    "active_consciousness.time.deep_night_fitness": "0.3",       # 深夜权重
    
    # 延迟发送
    "active_consciousness.delay.enabled": "true",                # 启用延迟发送
    "active_consciousness.delay.max_retry": "3",                 # 最大重试次数
    "active_consciousness.delay.retry_interval_minutes": "30",   # 重试间隔（分钟）
    "active_consciousness.delay.max_queue_size": "10",           # 最大队列长度
    
    # 念头存储
    "active_consciousness.thought.retain_enabled": "true",       # 启用念头存储
    "active_consciousness.thought.retain_threshold": "0.5",      # 存储阈值
}
```

---

## 十、测试计划

### 10.1 单元测试

| 测试文件 | 测试内容 | 测试用例数 |
|----------|----------|------------|
| test_emotion_evolution.py | 情绪演化 | 10+ |
| test_decision_matrix.py | 决策矩阵 | 8+ |
| test_thought_retention.py | 念头存储 | 6+ |
| test_delay_queue.py | 延迟队列 | 8+ |

### 10.2 集成测试

| 测试场景 | 测试内容 |
|----------|----------|
| 心跳完整流程 | 从触发到日志记录 |
| 情绪持久化 | 跨心跳情绪保持 |
| 延迟队列 | 入队、重评估、出队 |
| 时间窗口 | 不同时间段的决策 |

### 10.3 测试覆盖率目标

- 核心函数：100%
- 辅助函数：80%+
- 整体：70%+

---

## 十一、验收标准总览

### 11.1 功能验收

- [ ] 情绪状态跨心跳持久化
- [ ] 情绪随时间自然演化
- [ ] 决策考虑时间窗口
- [ ] 决策使用多维度评分公式
- [ ] 念头有结构化类型
- [ ] 重要念头存入 Hindsight
- [ ] 延迟发送队列工作正常
- [ ] 所有新功能可配置

### 11.2 质量验收

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 测试覆盖率达标
- [ ] 无明显性能问题
- [ ] 日志记录完善

### 11.3 兼容性验收

- [ ] 旧 API 保持可用
- [ ] 旧配置可读取
- [ ] 向后兼容 emotional_intensity
- [ ] 前端无需修改（或修改很小）

---

## 十二、总结

v0.2.1 的核心改进是让凯莉从"闹钟式存在"进化到"持续式存在"。通过：

1. **情绪连续性**：情绪有"记忆"，会随时间自然演化
2. **时间窗口决策**：在合适的时间发送消息
3. **念头系统增强**：结构化的念头管理
4. **延迟发送队列**：智能的时机选择

这些改进让凯莉的行为更加自然、智能，真正实现"一直存在"的感觉。

**预计工期**：13 小时（Claude Code max 强度）

**关键成功因素**：
1. EmotionState 的正确实现
2. 决策公式的合理调参
3. 延迟队列的稳定运行
4. 完善的单元测试

---

**文档版本**：v1.0
**最后更新**：2026-06-16
**作者**：Claude Code (AI Assistant)
