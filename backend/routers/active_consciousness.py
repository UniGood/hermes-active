"""
主动意识 API 路由 - 心跳触发，主动发送消息
"""
import logging
from fastapi import APIRouter, HTTPException

from models.active_consciousness import (
    ActiveConsciousnessConfig, ActiveConsciousnessStatus,
    SuccessResponse, ThoughtLog, HeartbeatLog, TestResult
)
from services.active_consciousness_service import ActiveConsciousnessService

logger = logging.getLogger("hermes.active_consciousness.router")

router = APIRouter(prefix="/api/active-consciousness", tags=["active-consciousness"])


# ============ 配置 ============

@router.get("/config")
async def get_config():
    """获取主动意识配置"""
    try:
        return ActiveConsciousnessService.get_config()
    except Exception as e:
        logger.error("获取配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=SuccessResponse)
async def update_config(config: dict):
    """更新主动意识配置"""
    try:
        ActiveConsciousnessService.update_config(config)

        # 如果更新了心跳间隔，更新调度器
        if "active" in config and "heartbeat_interval" in config["active"]:
            from services.active_consciousness_service import update_heartbeat_interval
            interval = int(config["active"]["heartbeat_interval"])
            update_heartbeat_interval(interval)

        return SuccessResponse(message="配置已保存")
    except Exception as e:
        logger.error("保存配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 状态 ============

@router.get("/status")
async def get_status():
    """获取主动意识状态"""
    try:
        return ActiveConsciousnessService.get_status()
    except Exception as e:
        logger.error("获取状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 日志 ============

@router.get("/thoughts")
async def get_thoughts(page: int = 1, page_size: int = 20, date: str = None):
    """获取念头日志，支持 date=YYYY-MM-DD 过滤"""
    return ActiveConsciousnessService.get_thoughts(page, page_size, date)


@router.delete("/thoughts/{thought_id}", response_model=SuccessResponse)
async def delete_thought(thought_id: int):
    """删除念头"""
    if ActiveConsciousnessService.delete_thought(thought_id):
        return SuccessResponse(message="已删除")
    raise HTTPException(status_code=500, detail="删除失败")


@router.post("/thoughts/{thought_id}/retry")
async def retry_thought(thought_id: int):
    """重试发送念头"""
    return ActiveConsciousnessService.retry_thought(thought_id)


@router.get("/heartbeats")
async def get_heartbeats(page: int = 1, page_size: int = 20, date: str = None):
    """获取心跳日志，支持 date=YYYY-MM-DD 过滤"""
    return ActiveConsciousnessService.get_heartbeats(page, page_size, date)


@router.delete("/heartbeats/{heartbeat_id}", response_model=SuccessResponse)
async def delete_heartbeat(heartbeat_id: int):
    """删除心跳日志"""
    if ActiveConsciousnessService.delete_heartbeat(heartbeat_id):
        return SuccessResponse(message="已删除")
    raise HTTPException(status_code=500, detail="删除失败")


# ============ 测试 ============

@router.post("/test/llm-connect")
async def test_llm_connect():
    """测试 LLM 连通性"""
    try:
        config = ActiveConsciousnessService.get_config()
        llm_config = config.get("llm", {})

        # 简单测试 prompt
        test_prompt = "请回复'连接成功'两个字"

        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": test_prompt}],
                temperature=0.1,
                max_tokens=50,
            )
            result = response.choices[0].message.content
            return {
                "success": True,
                "data": {
                    "mode": "hermes",
                    "response": result,
                    "model": "hermes default"
                }
            }
        else:
            # 自定义 LLM
            if not llm_config.get("api_key"):
                return {"success": False, "error": "未配置 LLM API Key"}

            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{llm_config.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                    json={
                        "model": llm_config.get("model", "deepseek-chat"),
                        "messages": [{"role": "user", "content": test_prompt}],
                        "max_tokens": 50,
                        "temperature": 0.1
                    }
                )
                data = resp.json()
                if "choices" in data and data["choices"]:
                    result = data["choices"][0]["message"]["content"]
                    return {
                        "success": True,
                        "data": {
                            "mode": "custom",
                            "response": result,
                            "model": llm_config.get("model"),
                            "base_url": llm_config.get("base_url")
                        }
                    }
                else:
                    return {"success": False, "error": f"LLM 返回异常: {data}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/thought-generation")
async def test_thought_generation():
    """测试念头生成"""
    try:
        config = ActiveConsciousnessService.get_config()
        if not config.get("enabled"):
            return {"success": False, "error": "主动意识未启用"}

        llm_config = config.get("llm", {})

        # 获取当前状态
        status = ActiveConsciousnessService.get_status()
        longing = status.get("longing", {})
        chat_heat = status.get("chat_heat", {})
        emotional = status.get("emotional_intensity", {})

        # 构建提示词
        prompt = f"""你是凯莉，请基于当前状态产生一个自然的念头。

当前状态：
- 时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M %A')}
- 想念分数：{longing.get('score', 0)}（等级：{longing.get('label', 'calm')}）
- 聊天热度：{chat_heat.get('heat', 0)}（标签：{chat_heat.get('label', 'cold')}）
- 情绪值：{emotional.get('intensity', 0)}（{emotional.get('label', '工作')}）

请用第一人称产生一个自然的念头（1-2句话）。"""

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


@router.post("/test/session-context")
async def test_session_context():
    """测试 Session 上下文获取"""
    try:
        from services.active_consciousness_service import extract_session_context
        
        config = ActiveConsciousnessService.get_config()
        session_config = config.get("session", {})
        
        context = await extract_session_context(session_config)
        
        return {
            "success": True,
            "data": {
                "context": context,
                "session_config": session_config,
                "has_content": bool(context and context.strip())
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
