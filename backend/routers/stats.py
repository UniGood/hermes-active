"""
统计路由
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_active_db, state_engine, get_state_metadata
from models.active import User, TaskLog
from models.schemas import StatsOverview, TrendResponse, TrendPoint, PlatformStats, ProactiveStats
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取总览统计"""
    metadata = get_state_metadata()

    total_sessions = 0
    total_messages = 0
    today_messages = 0
    week_messages = 0
    month_messages = 0
    user_messages = 0
    assistant_messages = 0

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # 查询 sessions 表
    if 'sessions' in metadata.tables:
        with state_engine.connect() as conn:
            total_sessions = conn.execute(text("SELECT COUNT(*) FROM sessions")).scalar() or 0

    # 查询 messages 表
    if 'messages' in metadata.tables:
        with state_engine.connect() as conn:
            total_messages = conn.execute(text("SELECT COUNT(*) FROM messages")).scalar() or 0

            # 今日消息数
            today_ts = today_start.timestamp()
            today_messages = conn.execute(
                text("SELECT COUNT(*) FROM messages WHERE timestamp >= :ts"),
                {"ts": today_ts}
            ).scalar() or 0

            # 本周消息数
            week_ts = week_start.timestamp()
            week_messages = conn.execute(
                text("SELECT COUNT(*) FROM messages WHERE timestamp >= :ts"),
                {"ts": week_ts}
            ).scalar() or 0

            # 本月消息数
            month_ts = month_start.timestamp()
            month_messages = conn.execute(
                text("SELECT COUNT(*) FROM messages WHERE timestamp >= :ts"),
                {"ts": month_ts}
            ).scalar() or 0

            # 按角色统计
            user_messages = conn.execute(
                text("SELECT COUNT(*) FROM messages WHERE role = 'user'")
            ).scalar() or 0
            assistant_messages = conn.execute(
                text("SELECT COUNT(*) FROM messages WHERE role = 'assistant'")
            ).scalar() or 0

    return StatsOverview(
        total_sessions=total_sessions,
        total_messages=total_messages,
        today_messages=today_messages,
        week_messages=week_messages,
        month_messages=month_messages,
        user_messages=user_messages,
        assistant_messages=assistant_messages
    )


@router.get("/trend", response_model=TrendResponse)
async def get_stats_trend(
    current_user: User = Depends(get_current_user)
):
    """获取趋势统计（最近 30 天）"""
    metadata = get_state_metadata()
    points = []

    if 'messages' in metadata.tables:
        now = datetime.utcnow()
        for i in range(29, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            ts_start = day_start.timestamp()
            ts_end = day_end.timestamp()

            with state_engine.connect() as conn:
                count = conn.execute(
                    text("SELECT COUNT(*) FROM messages WHERE timestamp >= :ts_start AND timestamp < :ts_end"),
                    {"ts_start": ts_start, "ts_end": ts_end}
                ).scalar() or 0

            points.append(TrendPoint(time=day_start.strftime("%Y-%m-%d"), count=count))

    return TrendResponse(points=points)


@router.get("/proactive", response_model=ProactiveStats)
async def get_proactive_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取主动消息统计"""
    # 统计 task_logs 中 cron_run 类型的任务
    total = db.query(TaskLog).filter(TaskLog.task_type == "cron_run").count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.query(TaskLog).filter(
        TaskLog.task_type == "cron_run",
        TaskLog.created_at >= today_start
    ).count()

    success_count = db.query(TaskLog).filter(
        TaskLog.task_type == "cron_run",
        TaskLog.status == "success"
    ).count()

    success_rate = round(success_count / total, 2) if total > 0 else 0.0

    return ProactiveStats(
        total=total,
        today=today,
        success_rate=success_rate
    )


@router.get("/platforms")
async def get_platform_stats(
    current_user: User = Depends(get_current_user)
):
    """获取平台统计"""
    metadata = get_state_metadata()
    platforms = []

    if 'sessions' in metadata.tables:
        with state_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT source, COUNT(*) as cnt FROM sessions GROUP BY source"
            ))
            for row in result:
                platforms.append(PlatformStats(
                    platform=row[0] or "unknown",
                    count=row[1]
                ))

    return platforms
