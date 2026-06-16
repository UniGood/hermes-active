"""
主动意识数据模型 - 心跳触发，主动发送消息
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
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
    time_range_hours: int = 24
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


class EmotionState(BaseModel):
    """VA 三维情绪状态"""
    valence: float = 0.5       # 情感效价 0-1（0=消极, 1=积极）
    arousal: float = 0.5       # 唤醒度 0-1（0=平静, 1=激动）
    dominant: str = "calm"     # 主导情绪标签
    social_need: float = 0.3   # 社交需求 0-1
    updated_at: Optional[str] = None  # 上次更新时间 ISO 格式


class DelayedThought(BaseModel):
    """延迟发送念头"""
    id: Optional[int] = None
    content: str = ""
    thought_type: str = "time"
    score: float = 0.0
    created_at: Optional[str] = None
    retry_count: int = 0
    next_retry_at: Optional[str] = None


class ActiveConsciousnessStatus(BaseModel):
    """主动意识状态"""
    enabled: bool = False
    heartbeat_count: int = 0
    last_heartbeat_at: Optional[str] = None
    longing: LongingState = LongingState()
    chat_heat: ChatHeat = ChatHeat()
    emotional_intensity: EmotionalIntensity = EmotionalIntensity()
    # v0.2.1 新增
    emotion_state: Optional[EmotionState] = None
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
