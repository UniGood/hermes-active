"""
主动意识数据模型 - 心跳触发，主动发送消息
"""
from datetime import datetime
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
