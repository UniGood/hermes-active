"""
LLM 路由
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import LLMTestRequest, LLMGenerateRequest, SuccessResponse
from services.config_service import ConfigService
from services.llm_service import LLMService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/llm", tags=["LLM管理"])


@router.post("/test")
async def test_llm_connection(
    request: LLMTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """测试 LLM 连通性"""
    # 获取配置，请求参数优先
    llm_config = ConfigService.get_llm_config(db)
    if request.provider:
        llm_config["provider"] = request.provider
    if request.model:
        llm_config["model"] = request.model
    if request.api_key:
        llm_config["api_key"] = request.api_key
    if request.base_url:
        llm_config["base_url"] = request.base_url

    result = await LLMService.test_connection(llm_config)
    return result


@router.post("/generate")
async def generate_message(
    request: LLMGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """生成消息"""
    llm_config = ConfigService.get_llm_config(db)

    result = await LLMService.generate_message(
        llm_config=llm_config,
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )

    if result.get("success"):
        return {
            "success": True,
            "message": "生成成功",
            "content": result["content"],
            "model": result.get("model"),
            "duration": result.get("duration")
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "生成失败"),
            "content": ""
        }


@router.get("/providers", response_model=List[str])
async def get_providers(
    current_user: User = Depends(get_current_user)
):
    """获取可用 provider 列表"""
    return LLMService.get_providers()
