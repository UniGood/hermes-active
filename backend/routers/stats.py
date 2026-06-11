"""
统计路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_active_db, state_engine
from models.active import User
from models.schemas import StatsOverview, TrendResponse, TrendPoint, PlatformStats, ProactiveStats
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(
    current_user: User = Depends(get_current_user)
):
    """获取总览统计"""
    # TODO: 实现实际的统计查询
    # 这里返回示例数据

    return StatsOverview(
        total_sessions=100,
        total_messages=5000,
        today_messages=50,
        week_messages=300,
        month_messages=1200,
        user_messages=2500,
        assistant_messages=2500
    )


@router.get("/trend", response_model=TrendResponse)
async def get_stats_trend(
    current_user: User = Depends(get_current_user)
):
    """获取趋势统计"""
    # TODO: 实现实际的趋势查询
    # 这里返回示例数据

    points = [
        TrendPoint(time=f"2024-01-{i:02d}", count=10 + i * 5)
        for i in range(1, 31)
    ]

    return TrendResponse(points=points)


@router.get("/proactive", response_model=ProactiveStats)
async def get_proactive_stats(
    current_user: User = Depends(get_current_user)
):
    """获取主动消息统计"""
    # TODO: 实现实际的主动消息统计

    return ProactiveStats(
        total=100,
        today=5,
        success_rate=0.95
    )


@router.get("/platforms")
async def get_platform_stats(
    current_user: User = Depends(get_current_user)
):
    """获取平台统计"""
    # TODO: 实现实际的平台统计查询

    return [
        PlatformStats(platform="weixin", count=80),
        PlatformStats(platform="feishu", count=20)
    ]
