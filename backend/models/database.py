"""
数据库连接管理
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from contextlib import contextmanager

from config import STATE_DB_PATH, ACTIVE_DB_PATH, DATA_DIR

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# active.db 引擎（读写）
active_engine = create_engine(
    f"sqlite:///{ACTIVE_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False
)

# state.db 引擎（只读）
state_engine = create_engine(
    f"sqlite:///{STATE_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False
)

# Session 工厂
ActiveSession = sessionmaker(bind=active_engine, autocommit=False, autoflush=False)
StateSession = sessionmaker(bind=state_engine, autocommit=False, autoflush=False)


# 基类
class DeclarativeBase(DeclarativeBase):
    pass


def get_active_db():
    """获取 active.db 会话"""
    db = ActiveSession()
    try:
        yield db
    finally:
        db.close()


def get_state_db():
    """获取 state.db 会话（只读）"""
    db = StateSession()
    try:
        yield db
    finally:
        db.close()


def init_active_db():
    """初始化 active.db 表结构"""
    from .active import Base
    Base.metadata.create_all(bind=active_engine)


def get_state_metadata():
    """获取 state.db 元数据（只读映射）"""
    metadata = MetaData()
    metadata.reflect(bind=state_engine)
    return metadata
