"""
消息路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import MessageListResponse, SendMessageRequest, SendProactiveRequest, SuccessResponse
from services.message_service import MessageService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/messages", tags=["消息管理"])


@router.get("/{session_id}", response_model=MessageListResponse)
async def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取消息列表"""
    result = MessageService.get_messages(db, session_id, page, page_size)
    return MessageListResponse(**result)


@router.post("/send", response_model=SuccessResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """发送消息"""
    result = await MessageService.send_message(
        session_id=request.session_id,
        message=request.message,
        is_test=request.is_test
    )
    return SuccessResponse(message=result["message"])


@router.post("/send-proactive", response_model=SuccessResponse)
async def send_proactive_message(
    request: SendProactiveRequest,
    current_user: User = Depends(get_current_user)
):
    """发送主动消息"""
    result = await MessageService.send_proactive_message(
        session_id=request.session_id,
        message=request.message,
        use_llm=request.use_llm
    )
    return SuccessResponse(message=result["message"])


@router.get("/search")
async def search_messages(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """搜索消息"""
    result = MessageService.search_messages(db, keyword, page, page_size)
    return result
