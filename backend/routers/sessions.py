"""
Session 路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models.database import get_active_db
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 session 列表"""
    result = SessionService.get_sessions(db, page, page_size, platform, search)
    return SessionListResponse(**result)


@router.get("/latest/{platform}", response_model=Optional[SessionInfo])
async def get_latest_session(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """获取最新 session"""
    session = SessionService.get_latest_session(platform)
    if not session:
        raise HTTPException(status_code=404, detail="未找到 session")
    return SessionInfo(**session)


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


@router.get("/{session_id}/context", response_model=List[MessageInfo])
async def get_session_context(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 session 上下文"""
    messages = SessionService.get_session_context(db, session_id, limit)
    return [MessageInfo(**msg) for msg in messages]
