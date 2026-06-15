"""
active.db 数据模型
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    avatar = Column(Text, nullable=True)  # base64 编码的头像图片
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))
    updated_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), onupdate=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "avatar": self.avatar,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TaskLog(Base):
    """任务执行记录表"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    message = Column(Text)
    error = Column(Text)
    duration = Column(Float)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), index=True)

    def to_dict(self):
        details = self.details
        if details:
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "duration": self.duration,
            "details": details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Config(Base):
    """配置表"""
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))
    updated_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), onupdate=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ThoughtLog(Base):
    """想法日志表"""
    __tablename__ = "active_thought_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    heartbeat_id = Column(Integer, nullable=True)
    type = Column(String(50), nullable=False, default="thought")
    content = Column(Text, nullable=False)
    intensity = Column(Float, default=0.5)
    decision = Column(String(50), default="pending")
    reason = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    recall_count = Column(Integer, nullable=True)
    recall_source = Column(String(100), nullable=True)
    chat_heat = Column(Float, nullable=True)
    emotional_intensity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "heartbeat_id": self.heartbeat_id,
            "type": self.type,
            "content": self.content,
            "intensity": self.intensity,
            "decision": self.decision,
            "reason": self.reason,
            "score": self.score,
            "recall_count": self.recall_count,
            "recall_source": self.recall_source,
            "chat_heat": self.chat_heat,
            "emotional_intensity": self.emotional_intensity,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class HeartbeatLog(Base):
    """心跳日志表"""
    __tablename__ = "active_heartbeat_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    longing_before = Column(Float, nullable=True)
    longing_after = Column(Float, nullable=True)
    chat_heat = Column(Float, nullable=True)
    emotional_intensity = Column(Float, nullable=True)
    recall_count = Column(Integer, nullable=True)
    reflect_count = Column(Integer, nullable=True)
    thoughts_generated = Column(Integer, nullable=True)
    message_sent = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON格式的详细日志（LLM请求/响应等）
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), index=True)

    def to_dict(self):
        details = self.details
        if details:
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_ms": self.duration_ms,
            "longing_before": self.longing_before,
            "longing_after": self.longing_after,
            "chat_heat": self.chat_heat,
            "emotional_intensity": self.emotional_intensity,
            "recall_count": self.recall_count,
            "reflect_count": self.reflect_count,
            "thoughts_generated": self.thoughts_generated,
            "message_sent": self.message_sent,
            "error": self.error,
            "details": details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
