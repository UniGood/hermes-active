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
from services.config_service import ConfigService

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


class GenerateRequest(BaseModel):
    session_id: str


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
    llm_config = ConfigService.get_llm_config(db)
    prompts_config = ConfigService.get_prompts_config(db)

    if llm_config.get("mode") == "hermes":
        # 使用 hermes 的 LLM
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            context_msgs = MessageService.get_session_context_raw(request.session_id, limit=20)
            context_text = "\n".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
                for m in context_msgs[-10:]
            )

            system_prompt = prompts_config.get("system", "")
            generation_template = prompts_config.get("generation", "{context}")
            user_prompt = generation_template.replace("{context}", context_text)

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
            return {"success": True, "message": content, "source": "hermes"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hermes LLM 调用失败: {str(e)}")
    else:
        # 使用自定义 LLM
        from services.llm_service import LLMService

        context_msgs = MessageService.get_session_context_raw(request.session_id, limit=20)
        context_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
            for m in context_msgs[-10:]
        )

        system_prompt = prompts_config.get("system", "")
        generation_template = prompts_config.get("generation", "{context}")
        user_prompt = generation_template.replace("{context}", context_text)

        result = await LLMService.generate_message(
            llm_config=llm_config,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200
        )

        if result.get("success"):
            return {"success": True, "message": result["content"], "source": "custom"}
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "生成失败"))


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """发送主动消息（支持 LLM 生成）"""
    llm_config = ConfigService.get_llm_config(db)
    prompts_config = ConfigService.get_prompts_config(db)

    result = await MessageService.send_proactive_message(
        session_id=request.session_id,
        message=request.message,
        use_llm=request.use_llm,
        llm_config=llm_config,
        prompts_config=prompts_config,
        write_to_db=request.write_to_db,
        with_mark=request.with_mark
    )
    if result.get("success"):
        return {"success": True, "message": result.get("message", "发送成功"), "detail": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "发送失败"))
