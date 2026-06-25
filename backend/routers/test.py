"""
测试路由
"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import TestFullRequest, SuccessResponse
from services.session_service import SessionService
from services.message_service import MessageService
from services.config_service import ConfigService
from services.llm_service import LLMService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/test", tags=["测试工具"])


@router.post("/full", response_model=SuccessResponse)
async def test_full_flow(
    request: TestFullRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """测试完整流程"""
    start_time = time.time()

    # 1. 获取最新活跃 session（自动处理过期）
    user_id = SessionService.get_user_id_for_platform(request.platform)
    if not user_id:
        MessageService.create_task_log(
            task_type="test_flow",
            status="failed",
            message="完整流程测试失败",
            error=f"未找到 {request.platform} 平台的用户 ID",
            duration=round(time.time() - start_time, 2),
            details={"platform": request.platform, "failure_stage": "no_user_id"}
        )
        return SuccessResponse(message=f"未找到 {request.platform} 用户 ID，测试失败")
    from services.fallback_session_service import FallbackSessionService
    session = FallbackSessionService.get_or_create_active_session(request.platform, user_id)
    if not session:
        MessageService.create_task_log(
            task_type="test_flow",
            status="failed",
            message="完整流程测试失败",
            error=f"未找到 {request.platform} 平台的 session",
            duration=round(time.time() - start_time, 2),
            details={"platform": request.platform, "failure_stage": "no_session"}
        )
        return SuccessResponse(message="未找到 session，测试失败")

    # 2. 获取上下文
    context = SessionService.get_session_context(db, session["id"], limit=10)

    # 3. 生成消息
    message = "测试消息"
    reasoning_content = None
    if request.use_llm:
        llm_config = ConfigService.get_llm_config(db)
        prompts_config = ConfigService.get_prompts_config(db)

        context_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in context
        )

        system_prompt = prompts_config.get("system", "")
        generation_template = prompts_config.get("generation", "{context}")
        user_prompt = generation_template.replace("{context}", context_text)

        llm_result = await LLMService.generate_message(
            llm_config=llm_config,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200
        )

        if llm_result.get("success"):
            message = llm_result["content"]
            reasoning_content = llm_result.get("reasoning_content")
        else:
            MessageService.create_task_log(
                task_type="test_flow",
                status="failed",
                message="完整流程测试失败（LLM 生成）",
                error=llm_result.get("message", "LLM 生成失败"),
                duration=round(time.time() - start_time, 2),
                details={"platform": request.platform, "use_llm": True, "failure_stage": "llm_generate"}
            )
            return SuccessResponse(message=f"LLM 生成消息失败: {llm_result.get('message')}")

    # 4. 发送消息（上下文注入）
    send_result = await MessageService.send_message(
        session_id=session["id"],
        message=message,
        platform=request.platform,
        reasoning_content=reasoning_content
    )

    duration = round(time.time() - start_time, 2)

    # 5. 记录日志
    if send_result.get("success"):
        MessageService.create_task_log(
            task_type="test_flow",
            status="success",
            message=f"完整流程测试成功，session: {session['id']}，消息数: {len(context)}",
            duration=duration,
            details={
                "session_id": session["id"],
                "platform": request.platform,
                "context_count": len(context),
                "generated_message": message[:500],
                "send_result": send_result
            }
        )
        return SuccessResponse(
            message=f"完整流程测试成功，session: {session['id']}，消息数: {len(context)}"
        )
    else:
        MessageService.create_task_log(
            task_type="test_flow",
            status="failed",
            message="完整流程测试失败（发送消息）",
            error=send_result.get("message", "发送失败"),
            duration=duration,
            details={
                "session_id": session["id"],
                "platform": request.platform,
                "send_result": send_result,
                "failure_stage": "send"
            }
        )
        return SuccessResponse(message=f"消息发送失败: {send_result.get('message')}")
