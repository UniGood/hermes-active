"""
主动意识 API 路由 - 心跳触发，主动发送消息
"""
import logging
from fastapi import APIRouter, HTTPException

from models.active_consciousness import (
    ActiveConsciousnessConfig, ActiveConsciousnessStatus,
    SuccessResponse, ThoughtLog, HeartbeatLog, TestResult
)
from services.active_consciousness_service import (
    ActiveConsciousnessService,
    validate_active_consciousness_config
)

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
    # 验证配置
    errors = validate_active_consciousness_config(config)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "配置验证失败", "errors": errors}
        )

    try:
        # 获取旧配置（用于比较心跳间隔）
        old_config = ActiveConsciousnessService.get_config()
        old_interval = int(old_config.get("active", {}).get("heartbeat_interval", 600))

        # 更新配置
        ActiveConsciousnessService.update_config(config)

        # 如果心跳间隔变化，重启调度器以确保新配置立即生效
        new_interval = int(config.get("active", {}).get("heartbeat_interval", old_interval))
        if new_interval != old_interval:
            from services.active_consciousness_service import restart_heartbeat_scheduler
            restart_heartbeat_scheduler(new_interval)

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
    result = ActiveConsciousnessService.get_thoughts(page, page_size, date)
    # 添加展示用的中文标签
    from services.active_consciousness_service import get_thought_type_display, get_decision_display
    for item in result.get("items", []):
        item["type_display"] = get_thought_type_display(item.get("type", ""))
        item["decision_display"] = get_decision_display(item.get("decision", ""))
    return result


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
        emotion_state = status.get("emotion_state", {})

        # 从配置获取提示词模板
        from services.active_consciousness_service import _DEFAULTS, get_label_display
        from services.config_service import ConfigService
        from models.database import ActiveSession

        prompt_template = ConfigService.get_config(
            ActiveSession(), "active_consciousness.prompts.thought_generation"
        ) or _DEFAULTS["active_consciousness.prompts.thought_generation"]

        now = __import__('datetime').datetime.now()
        prompt = prompt_template.format(
            time=now.strftime('%Y-%m-%d %H:%M %A'),
            longing_score=longing.get('score', 0),
            longing_label=longing.get('label', '平静'),
            chat_heat=chat_heat.get('heat', 0),
            chat_label=chat_heat.get('label', '冷清'),
            emotional_intensity=emotional.get('intensity', 0),
            emotional_label=emotional.get('label', '工作'),
            dominant=emotion_state.get('dominant', 'calm'),
            valence=emotion_state.get('valence', 0.5),
            arousal=emotion_state.get('arousal', 0.3),
            social_need=emotion_state.get('social_need', 0.3),
        )

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


@router.post("/test/context-collector")
async def test_context_collector():
    """测试 ContextCollector 上下文收集"""
    try:
        from services.context_collector import ContextCollector

        config = ActiveConsciousnessService.get_config()
        status = ActiveConsciousnessService.get_status()

        collector = ContextCollector(config)
        bundle = await collector.collect(status)

        return {
            "success": True,
            "data": {
                "conversations_count": len(bundle.conversations),
                "conversations": bundle.conversations[:5],  # 只返回前5条
                "memories_count": len(bundle.memories),
                "memories": bundle.memories,
                "emotion": bundle.emotion,
                "time_context": bundle.time_context,
                "weather": bundle.weather,
                "user_habits_preview": bundle.user_habits[:200] if bundle.user_habits else "",
                "bundle_json": bundle.to_json()
            }
        }
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@router.post("/test/thought-engine")
async def test_thought_engine():
    """测试 ThoughtEngine 完整流程"""
    try:
        from services.thought_engine import ThoughtEngine

        config = ActiveConsciousnessService.get_config()
        status = ActiveConsciousnessService.get_status()

        engine = ThoughtEngine(config)
        result = await engine.generate(status)

        return {
            "success": True,
            "data": {
                "thought": result.get("thought"),
                "want_to_contact": result.get("want_to_contact"),
                "is_skip": not result.get("want_to_contact"),
                "context_bundle": {
                    "conversations_count": len(result.get("context_bundle", {}).get("conversations", [])),
                    "memories_count": len(result.get("context_bundle", {}).get("memories", [])),
                    "emotion": result.get("context_bundle", {}).get("emotion"),
                    "time_context": result.get("context_bundle", {}).get("time_context"),
                    "weather": result.get("context_bundle", {}).get("weather"),
                },
                "llm_details": {
                    "model": result.get("llm_details", {}).get("model"),
                    "duration_ms": result.get("llm_details", {}).get("duration_ms"),
                    "prompt_tokens": result.get("llm_details", {}).get("prompt_tokens"),
                    "completion_tokens": result.get("llm_details", {}).get("completion_tokens"),
                    "error": result.get("llm_details", {}).get("error"),
                }
            }
        }
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
