"""
数据库连接管理
"""
from sqlalchemy import create_engine, MetaData, text
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

    # 自动迁移：给 users 表增加 avatar 列（如果不存在）
    try:
        with active_engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar TEXT"))
            conn.commit()
    except Exception:
        pass  # 列已存在则忽略

    # 自动迁移：给 active_thought_logs 表增加 details 列（如果不存在）
    migrate_thought_logs_table()


def migrate_thought_logs_table():
    """给 active_thought_logs 表添加缺失列（如果不存在）"""
    import logging
    logger = logging.getLogger("hermes.database")

    try:
        with active_engine.connect() as conn:
            # 检查所有列是否存在
            result = conn.execute(text("PRAGMA table_info(active_thought_logs)"))
            columns = [row[1] for row in result.fetchall()]

            # 迁移 1：details 列
            if "details" not in columns:
                conn.execute(text("ALTER TABLE active_thought_logs ADD COLUMN details TEXT"))
                conn.commit()
                logger.info("已添加 details 列到 active_thought_logs 表")

            # 迁移 2：hindsight_stored 列（是否真的存进了 Hindsight）
            if "hindsight_stored" not in columns:
                conn.execute(text("ALTER TABLE active_thought_logs ADD COLUMN hindsight_stored BOOLEAN DEFAULT 0"))
                conn.commit()
                logger.info("已添加 hindsight_stored 列到 active_thought_logs 表")
    except Exception as e:
        logger.warning("迁移 active_thought_logs 表失败: %s", e)


def get_state_metadata():
    """获取 state.db 元数据（只读映射）"""
    metadata = MetaData()
    metadata.reflect(bind=state_engine)
    return metadata
