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
        search: Optional[str] = None,
        active_only: bool = False,
        filter_zombie: bool = False
    ) -> Dict[str, Any]:
        """获取 session 列表"""
        metadata = get_state_metadata()

        if 'sessions' not in metadata.tables:
            return {"total": 0, "items": []}

        sessions_table = metadata.tables['sessions']

        # 僵尸 session 过滤：只返回每个平台最新的一条活跃 session
        if filter_zombie:
            with state_engine.connect() as conn:
                # 获取每个平台最新的一条活跃 session
                sql = """
                    SELECT s.id, s.source, COALESCE(MAX(m.timestamp), s.started_at) as last_active
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.ended_at IS NULL
                    GROUP BY s.source
                    ORDER BY last_active DESC
                """
                result = conn.execute(text(sql))
                latest_per_platform = {row[1]: row[0] for row in result}

            if not latest_per_platform:
                return {"total": 0, "items": []}

            # 如果指定了平台，只返回该平台的最新 session
            if platform and platform in latest_per_platform:
                session_ids = [latest_per_platform[platform]]
            elif platform:
                return {"total": 0, "items": []}
            else:
                session_ids = list(latest_per_platform.values())

            query = sessions_table.select().where(sessions_table.c.id.in_(session_ids))
            query = query.order_by(sessions_table.c.started_at.desc())

            with state_engine.connect() as conn:
                result = conn.execute(query)
                items = [dict(row._mapping) for row in result]

            return {"total": len(items), "items": items}

        if active_only:
            # 用纯 SQL 获取活跃 session（按最后消息时间排序）
            with state_engine.connect() as conn:
                # 先获取总数
                count_sql = """
                    SELECT COUNT(DISTINCT s.id)
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.ended_at IS NULL
                """
                count_params = {}
                if platform:
                    count_sql += " AND s.source = :platform"
                    count_params["platform"] = platform
                if search:
                    count_sql += " AND (s.title LIKE :search OR s.user_id LIKE :search)"
                    count_params["search"] = f"%{search}%"
                total = conn.execute(text(count_sql), count_params).scalar()

                # 再获取分页数据
                sql = """
                    SELECT s.id, COALESCE(MAX(m.timestamp), s.started_at) as last_active
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.ended_at IS NULL
                """
                params = {}
                if platform:
                    sql += " AND s.source = :platform"
                    params["platform"] = platform
                if search:
                    sql += " AND (s.title LIKE :search OR s.user_id LIKE :search)"
                    params["search"] = f"%{search}%"
                sql += """
                    GROUP BY s.id
                    ORDER BY last_active DESC
                    LIMIT :limit OFFSET :offset
                """
                params["limit"] = page_size
                params["offset"] = (page - 1) * page_size
                active_ids_result = conn.execute(text(sql), params)
                active_ids = [row[0] for row in active_ids_result]

            if active_ids:
                query = sessions_table.select().where(sessions_table.c.id.in_(active_ids))
                query = query.order_by(sessions_table.c.started_at.desc())
                with state_engine.connect() as conn:
                    result = conn.execute(query)
                    items = [dict(row._mapping) for row in result]
            else:
                items = []

            return {"total": total, "items": items}
        else:
            # 非 active_only 模式
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
            count_query = sessions_table.select()
            if platform:
                count_query = count_query.where(sessions_table.c.source == platform)
            if search:
                count_query = count_query.where(
                    sessions_table.c.title.like(f"%{search}%") |
                    sessions_table.c.user_id.like(f"%{search}%")
                )

            from sqlalchemy import func
            total_sql = sessions_table.select().with_only_columns(func.count())
            if platform:
                total_sql = total_sql.where(sessions_table.c.source == platform)
            if search:
                total_sql = total_sql.where(
                    sessions_table.c.title.like(f"%{search}%") |
                    sessions_table.c.user_id.like(f"%{search}%")
                )

            with state_engine.connect() as conn:
                total = conn.execute(total_sql).scalar()

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
