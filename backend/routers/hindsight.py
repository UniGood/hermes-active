"""
Hindsight 路由 - 集成 Hindsight 记忆系统
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from models.active import User
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/hindsight", tags=["hindsight"])

HINDSIGHT_BASE_URL = "http://localhost:8888"
HINDSIGHT_BANK_ID = "hermes"


@router.post("/recall")
async def hindsight_recall(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, description="返回数量"),
    current_user: User = Depends(get_current_user)
):
    """从 Hindsight recall 记忆"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{HINDSIGHT_BASE_URL}/v1/default/banks/{HINDSIGHT_BANK_ID}/memories/recall",
                json={"query": query, "limit": limit}
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "results": data.get("results", []),
                    "total": len(data.get("results", []))
                }
            else:
                return {
                    "success": False,
                    "message": f"Hindsight API 返回错误: {response.status_code}",
                    "results": []
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "无法连接到 Hindsight 服务 (localhost:8888)",
            "results": []
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{HINDSIGHT_BASE_URL}/v1/default/banks/{HINDSIGHT_BANK_ID}/reflect",
                json={"query": query, "limit": limit}
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "reflection": data.get("reflection", "")
                }
            else:
                return {
                    "success": False,
                    "message": f"Hindsight API 返回错误: {response.status_code}",
                    "reflection": ""
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "无法连接到 Hindsight 服务 (localhost:8888)",
            "reflection": ""
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Reflect 失败: {str(e)}",
            "reflection": ""
        }
