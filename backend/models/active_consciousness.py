"""
主动意识数据模型 - 心跳触发，主动发送消息
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ============ 配置相关 ============

class ActiveConsciousnessLLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "openai"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = ""


class ActiveConsciousnessActiveConfig(BaseModel):
    """主动意识配置"""
    enabled: bool = True
    heartbeat_interval: int = 600
    send_tag: str = "[凯莉主动发送]"
    time_format: str = "%H:%M"
    no_send_after_user_msg_minutes: int = 10
    no_send_while_heat_above: float = 0.5
    no_send_while_vibe_below: float = 0.3


class ActiveConsciousnessSessionConfig(BaseModel):
    """Session 来源配置"""
    sources: List[str] = ["weixin"]
    max_messages_per_session: int = 15
    filter_tool_messages: bool = True


class ActiveConsciousnessDecisionConfig(BaseModel):
    """决策阈值配置"""
    send_threshold: float = 0.6
    delay_threshold: float = 0.3
    memory_threshold: float = 0.1
    max_per_hour: int = 2
    max_per_day: int = 5


class ActiveConsciousnessEmotionConfig(BaseModel):
    """情绪演化配置"""
    decay_rate: float = 0.02            # 每分钟 arousal 衰减率
    social_need_growth: float = 0.01    # 社交需求每分钟增长率
    valence_regression: float = 0.1     # valence 回归中性系数


class ActiveConsciousnessTimeConfig(BaseModel):
    """时间窗口配置"""
    enabled: bool = True
    deep_night_start: float = 23.5      # 深夜开始（小时）
    deep_night_end: float = 7.0         # 深夜结束（小时）
    deep_night_fitness: float = 0.3     # 深夜权重


class ActiveConsciousnessDelayConfig(BaseModel):
    """延迟发送配置"""
    enabled: bool = True
    max_retry: int = 3                  # 最大重试次数
    retry_interval_minutes: int = 30    # 重试间隔（分钟）


class ActiveConsciousnessThoughtConfig(BaseModel):
    """念头存储配置"""
    retain_enabled: bool = True
    retain_threshold: float = 0.5       # 存储阈值


class ActiveConsciousnessWeatherConfig(BaseModel):
    """天气配置（共享）"""
    enabled: bool = False
    amap_key: str = ""              # 高德开放平台 Key
    adcode: str = "370100"          # 城市编码（默认济南）
    cache_ttl: int = 3600           # 缓存时长（秒）
    temp_change_threshold: float = 5.0  # 温度变化阈值


class ActiveConsciousnessNotifyConfig(BaseModel):
    """通知目标配置"""
    platform: str = "weixin"
    chat_id: str = ""


class ActiveConsciousnessConfig(BaseModel):
    """主动意识完整配置"""
    enabled: bool = False
    llm: ActiveConsciousnessLLMConfig = ActiveConsciousnessLLMConfig()
    active: ActiveConsciousnessActiveConfig = ActiveConsciousnessActiveConfig()
    session: ActiveConsciousnessSessionConfig = ActiveConsciousnessSessionConfig()
    decision: ActiveConsciousnessDecisionConfig = ActiveConsciousnessDecisionConfig()
    notify: ActiveConsciousnessNotifyConfig = ActiveConsciousnessNotifyConfig()
    weather: ActiveConsciousnessWeatherConfig = ActiveConsciousnessWeatherConfig()
    # v0.2.1 新增
    emotion: ActiveConsciousnessEmotionConfig = ActiveConsciousnessEmotionConfig()
    time_window: ActiveConsciousnessTimeConfig = ActiveConsciousnessTimeConfig()
    delay: ActiveConsciousnessDelayConfig = ActiveConsciousnessDelayConfig()
    thought: ActiveConsciousnessThoughtConfig = ActiveConsciousnessThoughtConfig()


# ============ 状态相关 ============

class LongingState(BaseModel):
    """想念状态"""
    score: float = 0.0
    level: int = 0
    label: str = "calm"
    last_user_msg_at: Optional[str] = None
    last_self_msg_at: Optional[str] = None


class ChatHeat(BaseModel):
    """聊天热度"""
    heat: float = 0.0
    label: str = "cold"
    recent_count: int = 0
    recent_hours: float = 0.0
    recent_user_msg_at: Optional[str] = None


class ThoughtType(str, Enum):
    """念头类型枚举"""
    TIME = "time"           # 时间念头："23:30了，该睡了"
    SILENCE = "silence"     # 空白念头："好久没说话了"
    ASSOCIATION = "assoc"   # 关联念头："今天周五，一般加班"
    MEMORY = "memory"       # 回忆念头："想起你说过..."
    EMOTION = "emotion"     # 情绪念头："现在有点兴奋"
    ENVIRONMENT = "env"     # 环境念头："外面下雨了"


class EmotionalIntensity(BaseModel):
    """情绪强度"""
    intensity: float = 0.0
    label: str = "工作"


class ActiveConsciousnessStatus(BaseModel):
    """主动意识状态"""
    enabled: bool = False
    heartbeat_count: int = 0
    last_heartbeat_at: Optional[str] = None
    longing: LongingState = LongingState()
    chat_heat: ChatHeat = ChatHeat()
    emotional_intensity: EmotionalIntensity = EmotionalIntensity()
    # v0.2.1 新增
    time_fitness: Optional[Dict[str, Any]] = None
    delayed_count: int = 0
    today_sent_count: int = 0
    hour_sent_count: int = 0
    last_sent_at: Optional[str] = None


# ============ 日志相关 ============

class ThoughtLog(BaseModel):
    """想法日志"""
    id: int
    heartbeat_id: Optional[int] = None
    type: str
    content: str
    intensity: float = 0.5
    decision: str = "pending"
    reason: Optional[str] = None
    score: Optional[float] = None
    recall_count: Optional[int] = None
    recall_source: Optional[str] = None
    chat_heat: Optional[float] = None
    emotional_intensity: Optional[float] = None
    created_at: Optional[str] = None


class HeartbeatLog(BaseModel):
    """心跳日志"""
    id: int
    started_at: Optional[str] = None
    duration_ms: Optional[int] = None
    longing_before: Optional[float] = None
    longing_after: Optional[float] = None
    chat_heat: Optional[float] = None
    emotional_intensity: Optional[float] = None
    # v0.2.1 新增
    emotion_valence: Optional[float] = None
    emotion_arousal: Optional[float] = None
    emotion_dominant: Optional[str] = None
    recall_count: Optional[int] = None
    reflect_count: Optional[int] = None
    thoughts_generated: Optional[int] = None
    message_sent: bool = False
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


# ============ 测试相关 ============

class TestResult(BaseModel):
    """测试结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


# ============ API 响应 ============

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str = "操作成功"


# ============ Phase 1: 情绪连续性 ============

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
        """
        计算综合情绪强度（加权公式）

        权重分配：
        - social_need 占 50%（社交需求是主动发送的核心驱动力）
        - arousal 占 30%（唤醒度反映情绪激活程度）
        - valence 占 20%（效价作为辅助参考）
        """
        return self.social_need * 0.5 + self.arousal * 0.3 + self.valence * 0.2

    def is_stale(self, minutes: float = 60) -> bool:
        """检查情绪状态是否过期"""
        if not self.updated_at:
            return True
        try:
            updated = datetime.fromisoformat(self.updated_at)
            return (datetime.now() - updated).total_seconds() / 60 > minutes
        except Exception:
            return True


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
