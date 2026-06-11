"""
Session 服务
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_state_metadata, state_engine


class SessionService:
    """Session 服务类"""

    @staticmethod
    def get_sessions(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        platform: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取 session 列表"""
        metadata = get_state_metadata()

        if 'sessions' not in metadata.tables:
            return {"total": 0, "items": []}

        sessions_table = metadata.tables['sessions']

        # 构建查询
        query = sessions_table.select()

        # 平台筛选
        if platform:
            query = query.where(sessions_table.c.source == platform)

        # 搜索
        if search:
            query = query.where(
                sessions_table.c.title.like(f"%{search}%") |
                sessions_table.c.user_id.like(f"%{search}%")
            )

        # 获取总数
        count_query = text("SELECT COUNT(*) FROM sessions")
        with state_engine.connect() as conn:
            total = conn.execute(count_query).scalar()

        # 分页查询
        query = query.order_by(sessions_table.c.started_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return {"total": total, "items": items}

    @staticmethod
    def get_session_by_id(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
        """获取 session 详情"""
        metadata = get_state_metadata()

        if 'sessions' not in metadata.tables:
            return None

        sessions_table = metadata.tables['sessions']
        query = sessions_table.select().where(sessions_table.c.id == session_id)

        with state_engine.connect() as conn:
            result = conn.execute(query)
            row = result.first()
            if row:
                return dict(row._mapping)
        return None

    @staticmethod
    def get_latest_session(platform: str = "weixin") -> Optional[Dict[str, Any]]:
        """获取最新 session"""
        metadata = get_state_metadata()

        if 'sessions' not in metadata.tables:
            return None

        sessions_table = metadata.tables['sessions']
        query = (
            sessions_table.select()
            .where(sessions_table.c.source == platform)
            .order_by(sessions_table.c.started_at.desc())
            .limit(1)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            row = result.first()
            if row:
                return dict(row._mapping)
        return None

    @staticmethod
    def get_session_context(db: Session, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取 session 上下文（消息历史）"""
        metadata = get_state_metadata()

        if 'messages' not in metadata.tables:
            return []

        messages_table = metadata.tables['messages']
        query = (
            messages_table.select()
            .where(messages_table.c.session_id == session_id)
            .order_by(messages_table.c.timestamp.desc())
            .limit(limit)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return list(reversed(items))
