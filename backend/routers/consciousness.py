"""
自主意识 API 路由
"""
import logging
from fastapi import APIRouter, HTTPException

from models.consciousness import (
    ConsciousnessConfig, ConsciousnessStatus, SuccessResponse,
    ThoughtLog, HeartbeatLog, ChatRecord, TestResult
)
from services.consciousness_service import ConsciousnessService

logger = logging.getLogger("hermes.consciousness.router")

router = APIRouter(prefix="/api/consciousness", tags=["consciousness"])


# ============ 配置 ============

@router.get("/config")
async def get_config():
    """获取自主意识配置"""
    try:
        return ConsciousnessService.get_config()
    except Exception as e:
        logger.error("获取配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=SuccessResponse)
async def update_config(config: dict):
    """更新自主意识配置"""
    try:
        ConsciousnessService.update_config(config)
        return SuccessResponse(message="配置已保存")
    except Exception as e:
        logger.error("保存配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 状态 ============

@router.get("/status")
async def get_status():
    """获取自主意识状态"""
    try:
        return ConsciousnessService.get_status()
    except Exception as e:
        logger.error("获取状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 日志 ============

@router.get("/thoughts")
async def get_thoughts(page: int = 1, page_size: int = 20):
    """获取念头日志"""
    return ConsciousnessService.get_thoughts(page, page_size)


@router.delete("/thoughts/{thought_id}", response_model=SuccessResponse)
async def delete_thought(thought_id: int):
    """删除念头"""
    if ConsciousnessService.delete_thought(thought_id):
        return SuccessResponse(message="已删除")
    raise HTTPException(status_code=500, detail="删除失败")


@router.post("/thoughts/{thought_id}/retry")
async def retry_thought(thought_id: int):
    """重试发送念头"""
    return ConsciousnessService.retry_thought(thought_id)


@router.get("/heartbeats")
async def get_heartbeats(page: int = 1, page_size: int = 20):
    """获取心跳日志"""
    return ConsciousnessService.get_heartbeats(page, page_size)


@router.delete("/heartbeats/{heartbeat_id}", response_model=SuccessResponse)
async def delete_heartbeat(heartbeat_id: int):
    """删除心跳日志"""
    if ConsciousnessService.delete_heartbeat(heartbeat_id):
        return SuccessResponse(message="已删除")
    raise HTTPException(status_code=500, detail="删除失败")


@router.get("/chats")
async def get_chats(limit: int = 50):
    """获取最近聊天记录"""
    return ConsciousnessService.get_chats(limit)


# ============ 测试 ============

@router.post("/test/weather")
async def test_weather():
    """测试天气获取"""
    try:
        config = ConsciousnessService.get_config()
        weather_config = config.get("weather", {})
        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}

        adcode = weather_config.get("adcode", "370100")
        amap_key = weather_config.get("amap_key", "")
        if not amap_key:
            return {"success": False, "error": "未配置高德 API Key"}

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://restapi.amap.com/v3/weather/weatherInfo",
                params={"city": adcode, "key": amap_key, "extensions": "base"}
            )
            data = resp.json()
            if data.get("status") == "1" and data.get("lives"):
                weather = data["lives"][0]
                return {
                    "success": True,
                    "data": {
                        "city": weather.get("city"),
                        "weather": weather.get("weather"),
                        "temperature": weather.get("temperature"),
                        "wind_direction": weather.get("winddirection"),
                        "wind_power": weather.get("windpower"),
                        "humidity": weather.get("humidity"),
                        "report_time": weather.get("reporttime"),
                    }
                }
            else:
                return {"success": False, "error": f"API 返回异常: {data}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/hindsight-recall")
async def test_hindsight_recall():
    """测试 Hindsight Recall"""
    try:
        config = ConsciousnessService.get_config()
        hindsight_config = config.get("hindsight", {})
        if not hindsight_config.get("enabled"):
            return {"success": False, "error": "Hindsight 未启用"}

        import httpx
        limit = hindsight_config.get("recall_limit", 5)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "http://localhost:8888/v1/default/banks/hermes/memories/recall",
                json={"query": "最近的对话和情绪", "limit": limit}
            )
            data = resp.json()
            results = data.get("results", data.get("memories", []))
            return {
                "success": True,
                "data": {
                    "count": len(results),
                    "results": results[:limit]
                }
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/hindsight-reflect")
async def test_hindsight_reflect():
    """测试 Hindsight Reflect"""
    try:
        config = ConsciousnessService.get_config()
        hindsight_config = config.get("hindsight", {})
        if not hindsight_config.get("reflect_enabled"):
            return {"success": False, "error": "Reflect 未启用"}

        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "http://localhost:8888/v1/default/banks/hermes/reflect",
                json={"query": "总结最近的对话和情绪变化"}
            )
            data = resp.json()
            return {
                "success": True,
                "data": {
                    "reflection": data.get("reflection", data.get("result", ""))
                }
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/thought-generation")
async def test_thought_generation():
    """测试想法生成"""
    try:
        config = ConsciousnessService.get_config()
        if not config.get("enabled"):
            return {"success": False, "error": "自主意识未启用"}

        llm_config = config.get("llm", {})

        # 获取当前状态
        status = ConsciousnessService.get_status()
        longing = status.get("longing", {})
        chat_heat = status.get("chat_heat", {})
        emotional = status.get("emotional_intensity", {})

        # 构建提示词
        prompt = f"""你是凯莉，请基于当前状态产生一个自然的想法。

当前状态：
- 时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M %A')}
- 想念分数：{longing.get('score', 0)}（等级：{longing.get('label', 'calm')}）
- 聊天热度：{chat_heat.get('heat', 0)}（标签：{chat_heat.get('label', 'cold')}）
- 情绪值：{emotional.get('intensity', 0)}（{emotional.get('label', '工作')}）

请用第一人称产生一个自然的想法（1-2句话）。"""

        thought = None

        # 判断 LLM 模式
        if llm_config.get("mode") == "hermes":
            # 使用 hermes 的 LLM
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            thought = response.choices[0].message.content
        else:
            # 使用自定义 LLM
            if not llm_config.get("api_key"):
                return {"success": False, "error": "未配置 LLM API Key"}

            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{llm_config.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                    json={
                        "model": llm_config.get("model", "deepseek-chat"),
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                        "temperature": 0.9
                    }
                )
                data = resp.json()
                if "choices" in data and data["choices"]:
                    thought = data["choices"][0]["message"]["content"]
                else:
                    return {"success": False, "error": f"LLM 返回异常: {data}"}

        if thought:
            return {
                "success": True,
                    "data": {
                        "thought": thought,
                        "status": status
                    }
                    }
    except Exception as e:
        return {"success": False, "error": str(e)}
