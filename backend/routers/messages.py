"""
消息路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from middleware.auth import get_current_user
from models.database import get_active_db
from models.active import User
from services.message_service import MessageService

router = APIRouter(prefix="/api/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    write_to_db: bool = True
    with_mark: bool = False


class SendProactiveRequest(BaseModel):
    session_id: str
    message: str = ""
    use_llm: bool = False
    write_to_db: bool = True
    with_mark: bool = True


@router.get("/{session_id}")
async def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取消息列表"""
    result = MessageService.get_messages(db, session_id, page, page_size)
    return result


@router.get("/search")
async def search_messages(
    keyword: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """搜索消息"""
    result = MessageService.search_messages(db, keyword, page, page_size)
    return result


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """发送消息到微信（真正发送 + 写入 state.db）"""
    result = await MessageService.send_message(
        session_id=request.session_id,
        message=request.message,
        platform="weixin",
        write_to_db=request.write_to_db,
        with_mark=request.with_mark
    )
    if result.get("success"):
        return {"success": True, "message": result.get("message", "发送成功"), "detail": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "发送失败"))


@router.post("/send-proactive")
async def send_proactive_message(
    request: SendProactiveRequest,
    current_user: User = Depends(get_current_user)
):
    """发送主动消息（支持 LLM 生成）"""
    result = await MessageService.send_proactive_message(
        session_id=request.session_id,
        message=request.message,
        use_llm=request.use_llm,
        write_to_db=request.write_to_db,
        with_mark=request.with_mark
    )
    if result.get("success"):
        return {"success": True, "message": result.get("message", "发送成功"), "detail": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "发送失败"))
