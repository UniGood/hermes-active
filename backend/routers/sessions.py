"""
Session 路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_active_db, state_engine, get_state_metadata
from models.active import User
from models.schemas import SessionInfo, SessionListResponse, MessageInfo
from services.session_service import SessionService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["Session管理"])


@router.get("", response_model=SessionListResponse)
async def get_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = Query(False, description="只返回活跃 session"),
    filter_zombie: bool = Query(False, description="过滤僵尸 session，只返回每个平台最新的一条"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 session 列表"""
    result = SessionService.get_sessions(db, page, page_size, platform, search, active_only, filter_zombie)
    return SessionListResponse(**result)


@router.get("/platforms")
async def get_platforms(
    current_user: User = Depends(get_current_user)
):
    """获取所有平台列表"""
    metadata = get_state_metadata()
    platforms = []

    if 'sessions' in metadata.tables:
        with state_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT DISTINCT source FROM sessions WHERE source IS NOT NULL"
            ))
            platforms = [row[0] for row in result]

    return platforms


@router.get("/latest/{platform}", response_model=Optional[SessionInfo])
async def get_latest_session(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """获取最新活跃 session（自动处理过期）"""
    if platform == "weixin":
        user_id = SessionService.get_weixin_user_id()
        if not user_id:
            raise HTTPException(status_code=404, detail="未找到微信用户 ID")
        session = SessionService.get_or_create_active_session(platform, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="未找到 session")
        # 转换为 SessionInfo 格式
        from datetime import datetime
        created_at = session.get('created_at')
        started_at = datetime.fromisoformat(created_at).timestamp() if created_at else None
        return SessionInfo(
            id=session['id'],
            source=session.get('source'),
            user_id=session.get('user_id'),
            started_at=started_at,
            was_auto_reset=session.get('was_auto_reset'),
            auto_reset_reason=session.get('auto_reset_reason'),
        )
    else:
        user_id = SessionService.get_user_id_for_platform(platform)
        if not user_id:
            raise HTTPException(status_code=404, detail=f"未找到 {platform} 用户 ID")
        session = SessionService.get_or_create_active_session(platform, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="未找到 session")
        from datetime import datetime
        created_at = session.get('created_at')
        started_at = datetime.fromisoformat(created_at).timestamp() if created_at else None
        return SessionInfo(
            id=session['id'],
            source=session.get('source'),
            user_id=session.get('user_id'),
            started_at=started_at,
            was_auto_reset=session.get('was_auto_reset'),
            auto_reset_reason=session.get('auto_reset_reason'),
        )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 session 详情"""
    session = SessionService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")
    return SessionInfo(**session)


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """获取 session 消息列表"""
    metadata = get_state_metadata()

    if 'messages' not in metadata.tables:
        return {"total": 0, "items": []}

    messages_table = metadata.tables['messages']

    # 获取总数
    with state_engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE session_id = :sid"),
            {"sid": session_id}
        ).scalar() or 0

    # 分页查询
    query = (
        messages_table.select()
        .where(messages_table.c.session_id == session_id)
        .order_by(messages_table.c.timestamp.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    with state_engine.connect() as conn:
        result = conn.execute(query)
        items = [dict(row._mapping) for row in result]

    return {"total": total, "items": items}


@router.get("/{session_id}/context", response_model=List[MessageInfo])
async def get_session_context(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    include_tool: bool = Query(False, description="是否包含 tool 消息"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 session 上下文"""
    messages = SessionService.get_session_context(db, session_id, limit, include_tool)
    return [MessageInfo(**msg) for msg in messages]
