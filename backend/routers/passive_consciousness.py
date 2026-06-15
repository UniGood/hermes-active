"""
被动意识 API 路由 - 用户消息时注入上下文
"""
import logging
from fastapi import APIRouter, HTTPException

from models.passive_consciousness import (
    PassiveConsciousnessConfig, PassiveConsciousnessStatus,
    SuccessResponse, ChatRecord, TestResult
)
from services.passive_consciousness_service import PassiveConsciousnessService

logger = logging.getLogger("hermes.passive_consciousness.router")

router = APIRouter(prefix="/api/passive-consciousness", tags=["passive-consciousness"])


# ============ 配置 ============

@router.get("/config")
async def get_config():
    """获取被动意识配置"""
    try:
        return PassiveConsciousnessService.get_config()
    except Exception as e:
        logger.error("获取配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=SuccessResponse)
async def update_config(config: dict):
    """更新被动意识配置"""
    try:
        PassiveConsciousnessService.update_config(config)
        return SuccessResponse(message="配置已保存")
    except Exception as e:
        logger.error("保存配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 状态 ============

@router.get("/status")
async def get_status():
    """获取被动意识状态"""
    try:
        return PassiveConsciousnessService.get_status()
    except Exception as e:
        logger.error("获取状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 日志 ============

@router.get("/chats")
async def get_chats(limit: int = 50):
    """获取最近聊天记录"""
    return PassiveConsciousnessService.get_chats(limit)


# ============ 测试 ============

@router.post("/test/hindsight-recall")
async def test_hindsight_recall():
    """测试 Hindsight Recall"""
    try:
        config = PassiveConsciousnessService.get_config()
        hindsight_config = config.get("hindsight", {})
        if not hindsight_config.get("enabled"):
            return {"success": False, "error": "Hindsight 未启用"}

        from hindsight_client import Hindsight
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        limit = hindsight_config.get("recall_limit", 5)
        timeout = hindsight_config.get("timeout", 120)

        client = Hindsight(base_url=base_url, timeout=timeout)
        response = await client.arecall(bank_id=bank_id, query="最近的对话和情绪", max_tokens=4096)
        results = [{"text": r.text, "type": r.type, "id": r.id} for r in response.results]
        return {
            "success": True,
            "data": {
                "count": len(results),
                "results": results
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/hindsight-reflect")
async def test_hindsight_reflect():
    """测试 Hindsight Reflect"""
    try:
        config = PassiveConsciousnessService.get_config()
        hindsight_config = config.get("hindsight", {})
        if not hindsight_config.get("reflect_enabled"):
            return {"success": False, "error": "Reflect 未启用"}

        from hindsight_client import Hindsight
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        timeout = hindsight_config.get("timeout", 120)

        client = Hindsight(base_url=base_url, timeout=timeout)
        answer = await client.areflect(bank_id=bank_id, query="总结最近的对话和情绪变化", budget="low")
        return {
            "success": True,
            "data": {
                "reflection": answer.text
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
