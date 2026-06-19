"""
被动意识日志模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime

from .database import DeclarativeBase


class PassiveConsciousnessLog(DeclarativeBase):
    """被动意识注入日志"""
    __tablename__ = "passive_consciousness_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    session_id = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    sender_id = Column(String, nullable=True)

    # 状态数据
    longing_score = Column(Float, default=0.0)
    longing_label = Column(String, default="calm")
    chat_heat = Column(Float, default=0.0)
    chat_heat_label = Column(String, default="cold")
    emotional_intensity = Column(Float, default=0.0)
    emotional_label = Column(String, default="工作")

    # 天气
    weather_city = Column(String, nullable=True)
    weather_info = Column(String, nullable=True)  # "晴 28°C"

    # 记忆
    memories_count = Column(Integer, default=0)
    has_reflection = Column(Boolean, default=False)

    # 注入结果
    status = Column(String, default="success")  # success / skipped / error
    context_length = Column(Integer, default=0)
    error_message = Column(String, nullable=True)

    # 用户消息摘要
    user_message_preview = Column(String, nullable=True)  # 前100字

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id,
            "platform": self.platform,
            "sender_id": self.sender_id,
            "longing_score": self.longing_score,
            "longing_label": self.longing_label,
            "chat_heat": self.chat_heat,
            "chat_heat_label": self.chat_heat_label,
            "emotional_intensity": self.emotional_intensity,
            "emotional_label": self.emotional_label,
            "weather_city": self.weather_city,
            "weather_info": self.weather_info,
            "memories_count": self.memories_count,
            "has_reflection": self.has_reflection,
            "status": self.status,
            "context_length": self.context_length,
            "error_message": self.error_message,
            "user_message_preview": self.user_message_preview,
        }
