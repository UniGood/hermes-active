"""
消息路由
"""
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from middleware.auth import get_current_user
from models.database import get_active_db
from models.active import User
from services.message_service import MessageService, DEFAULT_MARK_FORMAT
from services.config_service import ConfigService

router = APIRouter(prefix="/api/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    platform: str = "weixin"
    write_to_db: bool = True
    with_mark: bool = False
    mark_format: str = DEFAULT_MARK_FORMAT


class SendProactiveRequest(BaseModel):
    session_id: str
    message: str = ""
    platform: str = "weixin"
    use_llm: bool = False
    write_to_db: bool = True
    with_mark: bool = True
    mark_format: str = DEFAULT_MARK_FORMAT


class GenerateRequest(BaseModel):
    session_id: str
    context_source: str = "session"  # session / recall / reflect
    context_data: Optional[str] = None  # recall/reflect 的结果文本
    system_prompt: Optional[str] = None  # 自定义系统提示词
    user_prompt: Optional[str] = None  # 自定义用户提示词模板
    append_soul_md: bool = True  # 是否拼接 soul.md


class PreviewRequest(BaseModel):
    session_id: str
    context_source: str = "session"
    context_data: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    append_soul_md: bool = True


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


@router.post("/generate")
async def generate_message(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """仅生成主动消息（不发送、不写入DB）"""
    import time as _time
    start_time = _time.time()
    llm_config = ConfigService.get_llm_config(db)
    prompts_config = ConfigService.get_prompts_config(db)

    try:
        # 根据 context_source 获取上下文
        context_source = request.context_source
        context_data = request.context_data

        if context_source == "session":
            # 从 session 获取上下文
            context_msgs = MessageService.get_session_context_raw(request.session_id, limit=20)
            context_text = "\n".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
                for m in context_msgs[-10:]
            )
        elif context_source in ("recall", "reflect") and context_data:
            # 使用传入的 context_data（Hindsight recall/reflect 结果）
            context_text = context_data
        else:
            context_text = ""

        # 使用自定义提示词或默认提示词
        system_prompt = request.system_prompt if request.system_prompt is not None else prompts_config.get("system", "")

        # 拼接 soul.md
        if request.append_soul_md:
            soul_content = ConfigService.read_hermes_soul()
            if soul_content:
                system_prompt = system_prompt + "\n\n" + soul_content if system_prompt else soul_content

        generation_template = request.user_prompt if request.user_prompt is not None else prompts_config.get("generation", "{context}")
        user_prompt = generation_template.replace("{context}", context_text)

        if llm_config.get("mode") == "hermes":
            # 使用 hermes 的 LLM
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task="title_generation",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200,
            )
            content = response.choices[0].message.content.strip()
            duration = round(_time.time() - start_time, 2)
            MessageService.create_task_log(
                task_type="generate",
                status="success",
                message=f"生成消息成功（hermes），session: {request.session_id}，来源: {context_source}",
                duration=duration
            )
            return {"success": True, "message": content, "source": "hermes", "context_source": context_source}
        else:
            # 使用自定义 LLM
            from services.llm_service import LLMService

            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=200
            )

            if result.get("success"):
                duration = round(_time.time() - start_time, 2)
                MessageService.create_task_log(
                    task_type="generate",
                    status="success",
                    message=f"生成消息成功（custom），session: {request.session_id}，来源: {context_source}",
                    duration=duration
                )
                return {"success": True, "message": result["content"], "source": "custom", "context_source": context_source}
            else:
                duration = round(_time.time() - start_time, 2)
                MessageService.create_task_log(
                    task_type="generate",
                    status="failed",
                    message=f"生成消息失败，session: {request.session_id}",
                    error=result.get("message", "生成失败"),
                    duration=duration
                )
                raise HTTPException(status_code=500, detail=result.get("message", "生成失败"))
    except HTTPException:
        raise
    except Exception as e:
        duration = round(_time.time() - start_time, 2)
        MessageService.create_task_log(
            task_type="generate",
            status="failed",
            message=f"生成消息异常，session: {request.session_id}",
            error=str(e),
            duration=duration
        )
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """发送消息到指定平台（真正发送 + 写入 state.db）"""
    result = await MessageService.send_message(
        session_id=request.session_id,
        message=request.message,
        platform=request.platform,
        write_to_db=request.write_to_db,
        with_mark=request.with_mark,
        mark_format=request.mark_format
    )
    if result.get("success"):
        return {"success": True, "message": result.get("message", "发送成功"), "detail": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "发送失败"))


@router.post("/send-proactive")
async def send_proactive_message(
    request: SendProactiveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """发送主动消息（支持 LLM 生成）"""
    llm_config = ConfigService.get_llm_config(db)
    prompts_config = ConfigService.get_prompts_config(db)

    result = await MessageService.send_proactive_message(
        session_id=request.session_id,
        message=request.message,
        platform=request.platform,
        use_llm=request.use_llm,
        llm_config=llm_config,
        prompts_config=prompts_config,
        write_to_db=request.write_to_db,
        with_mark=request.with_mark,
        mark_format=request.mark_format
    )
    if result.get("success"):
        return {"success": True, "message": result.get("message", "发送成功"), "detail": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "发送失败"))


@router.post("/preview")
async def preview_prompt(
    request: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """预览完整提示词（不调用 LLM）"""
    prompts_config = ConfigService.get_prompts_config(db)

    # 获取上下文
    context_source = request.context_source
    context_data = request.context_data
    context_content = ""

    if context_source == "session":
        context_msgs = MessageService.get_session_context_raw(request.session_id, limit=20)
        if context_msgs:
            context_content = "\n".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
                for m in context_msgs[-10:]
            )
    elif context_data:
        context_content = context_data

    # 构建提示词
    system_prompt = request.system_prompt if request.system_prompt is not None else prompts_config.get("system", "")
    soul_md = ""

    # 拼接 soul.md
    if request.append_soul_md:
        soul_md = ConfigService.read_hermes_soul() or ""
        if soul_md:
            system_prompt = system_prompt + "\n\n" + soul_md if system_prompt else soul_md

    user_prompt_template = request.user_prompt if request.user_prompt is not None else prompts_config.get("generation", "{context}")
    user_prompt_final = user_prompt_template.replace("{context}", context_content)

    return {
        "system_prompt": system_prompt,
        "user_prompt_template": user_prompt_template,
        "user_prompt_final": user_prompt_final,
        "context_content": context_content,
        "soul_md": soul_md
    }
