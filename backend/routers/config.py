"""
配置路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import LLMConfig, PromptsConfig, SuccessResponse
from services.config_service import ConfigService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/config", tags=["配置管理"])


@router.get("/llm", response_model=LLMConfig)
async def get_llm_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取 LLM 配置"""
    config = ConfigService.get_llm_config(db)
    return LLMConfig(**config)


@router.put("/llm", response_model=SuccessResponse)
async def update_llm_config(
    config: LLMConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新 LLM 配置"""
    ConfigService.update_llm_config(db, config.model_dump())
    return SuccessResponse(message="LLM 配置更新成功")


@router.get("/prompts", response_model=PromptsConfig)
async def get_prompts_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取提示词配置"""
    config = ConfigService.get_prompts_config(db)
    return PromptsConfig(**config)


@router.put("/prompts", response_model=SuccessResponse)
async def update_prompts_config(
    prompts: PromptsConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新提示词配置"""
    ConfigService.update_prompts_config(db, prompts.model_dump())
    return SuccessResponse(message="提示词配置更新成功")
