"""
active.db 数据模型
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))
    updated_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), onupdate=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
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
