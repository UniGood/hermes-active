"""
自主意识数据模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ============ 配置相关 ============

class ConsciousnessLLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = ""


class ConsciousnessPassiveConfig(BaseModel):
    enabled: bool = True
    inject_emotion: bool = True
    inject_heat: bool = True
    inject_memory: bool = True
    inject_thought: bool = True
    thought_max_chars: int = 200
    vibe_max_chars: int = 50
    inject_tag: str = "[CONSCIOUSNESS_CONTEXT]"
    time_format: str = "%H:%M"


class ConsciousnessActiveConfig(BaseModel):
    enabled: bool = True
    heartbeat_interval: int = 600
    send_tag: str = "[凯莉主动发送]"
    time_format: str = "%H:%M"
    no_send_after_user_msg_minutes: int = 10
    no_send_while_heat_above: float = 0.5
    no_send_while_vibe_below: float = 0.3


class ConsciousnessSessionConfig(BaseModel):
    sources: List[str] = ["weixin"]
    time_range_hours: int = 24
    max_messages_per_session: int = 15
    filter_tool_messages: bool = True


class ConsciousnessDecisionConfig(BaseModel):
    send_threshold: float = 0.6
    delay_threshold: float = 0.3
    memory_threshold: float = 0.1
    max_per_hour: int = 2
    max_per_day: int = 5


class ConsciousnessHindsightConfig(BaseModel):
    enabled: bool = True
    recall_limit: int = 5
    reflect_enabled: bool = True


class ConsciousnessWeatherConfig(BaseModel):
    enabled: bool = False
    adcode: str = "370100"
    amap_key: str = ""
    cache_ttl: int = 600


class ConsciousnessNotifyConfig(BaseModel):
    platform: str = "weixin"
    chat_id: str = ""


class ConsciousnessConfig(BaseModel):
    enabled: bool = False
    llm: ConsciousnessLLMConfig = ConsciousnessLLMConfig()
    passive: ConsciousnessPassiveConfig = ConsciousnessPassiveConfig()
    active: ConsciousnessActiveConfig = ConsciousnessActiveConfig()
    session: ConsciousnessSessionConfig = ConsciousnessSessionConfig()
    decision: ConsciousnessDecisionConfig = ConsciousnessDecisionConfig()
    hindsight: ConsciousnessHindsightConfig = ConsciousnessHindsightConfig()
    weather: ConsciousnessWeatherConfig = ConsciousnessWeatherConfig()
    notify: ConsciousnessNotifyConfig = ConsciousnessNotifyConfig()


# ============ 状态相关 ============

class LongingState(BaseModel):
    score: float = 0.0
    level: int = 0
    label: str = "calm"
    last_user_msg_at: Optional[str] = None
    last_self_msg_at: Optional[str] = None


class ChatHeat(BaseModel):
    heat: float = 0.0
    label: str = "cold"
    recent_count: int = 0
    recent_hours: float = 0.0
    recent_user_msg_at: Optional[str] = None


class EmotionalIntensity(BaseModel):
    intensity: float = 0.0
    label: str = "工作"


class ConsciousnessStatus(BaseModel):
    enabled: bool = False
    heartbeat_count: int = 0
    last_heartbeat_at: Optional[str] = None
    longing: LongingState = LongingState()
    chat_heat: ChatHeat = ChatHeat()
    emotional_intensity: EmotionalIntensity = EmotionalIntensity()
    active_sessions: int = 0
    today_sent_count: int = 0
    hour_sent_count: int = 0
    last_sent_at: Optional[str] = None


# ============ 日志相关 ============

class ThoughtLog(BaseModel):
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
    id: int
    started_at: Optional[str] = None
    duration_ms: Optional[int] = None
    longing_before: Optional[float] = None
    longing_after: Optional[float] = None
    chat_heat: Optional[float] = None
    emotional_intensity: Optional[float] = None
    recall_count: Optional[int] = None
    reflect_count: Optional[int] = None
    thoughts_generated: Optional[int] = None
    message_sent: bool = False
    error: Optional[str] = None
    created_at: Optional[str] = None


class ChatRecord(BaseModel):
    id: int
    session_id: str
    source: str
    role: str
    content: str
    send_mark: Optional[str] = None
    timestamp: Optional[str] = None


# ============ 测试相关 ============

class TestResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


# ============ API 响应 ============

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
