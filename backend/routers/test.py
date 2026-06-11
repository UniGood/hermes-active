"""
测试路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import TestFullRequest, SuccessResponse
from services.session_service import SessionService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/test", tags=["测试工具"])


@router.post("/full", response_model=SuccessResponse)
async def test_full_flow(
    request: TestFullRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """测试完整流程"""
    # 1. 获取最新 session
    session = SessionService.get_latest_session(request.platform)
    if not session:
        return SuccessResponse(message="未找到 session，测试失败")

    # 2. 获取上下文
    context = SessionService.get_session_context(db, session["id"], limit=10)

    # 3. 生成消息（可选）
    message = "测试消息"
    if request.use_llm:
        # TODO: 调用 LLM 生成消息
        message = "LLM 生成的消息（待实现）"

    # 4. 发送消息
    # TODO: 实际发送消息

    # 5. 记录日志
    # TODO: 写入 task_logs

    return SuccessResponse(
        message=f"完整流程测试成功，session: {session['id']}，消息数: {len(context)}"
    )
