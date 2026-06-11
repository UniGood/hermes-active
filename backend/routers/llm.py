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
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/llm", tags=["LLM管理"])


@router.post("/test", response_model=SuccessResponse)
async def test_llm_connection(
    request: LLMTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """测试 LLM 连通性"""
    # TODO: 实现 LLM 连通性测试
    # 1. 获取配置
    # 2. 尝试调用 LLM
    # 3. 返回测试结果

    return SuccessResponse(message="LLM 连通性测试成功")


@router.post("/generate")
async def generate_message(
    request: LLMGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """生成消息"""
    # TODO: 实现 LLM 消息生成
    # 1. 获取 LLM 配置
    # 2. 调用 LLM 生成消息
    # 3. 返回生成的消息

    return {
        "success": True,
        "message": "生成成功",
        "content": "这是一条生成的消息（待实现）"
    }


@router.get("/providers", response_model=List[str])
async def get_providers(
    current_user: User = Depends(get_current_user)
):
    """获取可用 provider 列表"""
    # TODO: 从配置或硬编码获取可用的 provider 列表
    return ["openai", "anthropic", "xiaomi", "custom"]
