"""
Hindsight 路由 - 集成 Hindsight 记忆系统（使用 Python SDK）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from models.active import User
from middleware.auth import get_current_user
from hindsight_client import Hindsight

router = APIRouter(prefix="/api/hindsight", tags=["hindsight"])

# 默认配置
DEFAULT_BASE_URL = "http://localhost:8888"
DEFAULT_BANK_ID = "hermes"
DEFAULT_TIMEOUT = 30.0


def _get_hindsight_config():
    """从配置获取 Hindsight 参数"""
    try:
        from services.config_service import ConfigService
        from models.database import ActiveSession
        db = ActiveSession()
        try:
            config = ConfigService.get_config(db, "active_consciousness.hindsight")
            if config:
                import json
                return json.loads(config) if isinstance(config, str) else config
        finally:
            db.close()
    except Exception:
        pass
    return {}


def _create_client():
    """创建 Hindsight 客户端"""
    config = _get_hindsight_config()
    base_url = config.get("base_url", DEFAULT_BASE_URL)
    timeout = config.get("timeout", DEFAULT_TIMEOUT)
    return Hindsight(base_url=base_url, timeout=timeout)


@router.post("/recall")
async def hindsight_recall(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, description="返回数量"),
    current_user: User = Depends(get_current_user)
):
    """从 Hindsight recall 记忆"""
    try:
        client = _create_client()
        response = await client.arecall(bank_id=DEFAULT_BANK_ID, query=query, max_tokens=4096)
        return {
            "success": True,
            "results": [{"text": r.text, "type": r.type, "id": r.id} for r in response.results],
            "total": len(response.results)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Recall 失败: {str(e)}",
            "results": []
        }


@router.post("/reflect")
async def hindsight_reflect(
    query: str = Query(..., description="问题/查询"),
    limit: int = Query(10, description="考虑的记忆数量"),
    current_user: User = Depends(get_current_user)
):
    """从 Hindsight reflect 综合分析"""
    try:
        client = _create_client()
        answer = await client.areflect(bank_id=DEFAULT_BANK_ID, query=query)
        return {
            "success": True,
            "reflection": answer.text
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Reflect 失败: {str(e)}",
            "reflection": ""
        }
