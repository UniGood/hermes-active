"""
主动意识 API 路由 - 心跳触发，主动发送消息
"""
import json
import logging
from fastapi import Body, Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from models.active_consciousness import (
    ActiveConsciousnessConfig, ActiveConsciousnessStatus,
    SuccessResponse, ThoughtLog, HeartbeatLog, TestResult
)
from services.active_consciousness_service import (
    ActiveConsciousnessService,
    validate_active_consciousness_config
)
from services.config_service import ConfigService
from middleware.auth import get_current_user
from models.active import User
from models.database import get_active_db

logger = logging.getLogger("hermes.active_consciousness.router")

router = APIRouter(prefix="/api/active-consciousness", tags=["active-consciousness"])


# ============ 配置 ============

@router.get("/config")
async def get_config(
    current_user: User = Depends(get_current_user),
):
    """获取主动意识配置"""
    try:
        return ActiveConsciousnessService.get_config()
    except Exception as e:
        logger.error("获取配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=SuccessResponse)
async def update_config(config: dict,
    current_user: User = Depends(get_current_user),
):
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
async def get_status(
    current_user: User = Depends(get_current_user),
):
    """获取主动意识状态"""
    try:
        return ActiveConsciousnessService.get_status()
    except Exception as e:
        logger.error("获取状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repair/state")
async def get_repair_state(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db),
):
    """获取冲突修复状态（模糊档位，不暴露积分数值，防游戏化）"""
    # mode 中文映射
    mode_labels = {
        "normal": "温柔",
        "upset": "有点赌气",
        "cold": "冷淡",
        "softening": "嘴硬心软",
        "reconciled": "回暖",
        "grudge": "淡淡的",
        "self_at_fault": "心虚讨好",
    }
    try:
        raw = ConfigService.get_config(db, "active_consciousness.repair_state")
        state = {"mode": "normal", "points": 0}
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    state.update(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        mode = state.get("mode", "normal")
        points = float(state.get("points", 0) or 0)
        # 好感积分模糊档位：冰 / 化冰 / 回暖
        if points < 2:
            level = "冰"
        elif points < 4.8:
            level = "化冰"
        else:
            level = "回暖"
        return {"mode": mode_labels.get(mode, mode), "level": level}
    except Exception as e:
        logger.error("获取修复状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 日志 ============

@router.get("/thoughts")
async def get_thoughts(page: int = 1, page_size: int = 20, date: str = None,
                       heartbeat_id: int = None, thought_id: int = None,
    current_user: User = Depends(get_current_user),
):
    """获取念头日志，支持 date=YYYY-MM-DD / heartbeat_id / thought_id 过滤"""
    result = ActiveConsciousnessService.get_thoughts(page, page_size, date, heartbeat_id, thought_id)
    # 添加展示用的中文标签
    from services.active_consciousness_service import get_thought_type_display, get_decision_display
    for item in result.get("items", []):
        item["type_display"] = get_thought_type_display(item.get("type", ""))
        item["decision_display"] = get_decision_display(item.get("decision", ""))
    return result


@router.delete("/thoughts/{thought_id}", response_model=SuccessResponse)
async def delete_thought(thought_id: int,
    current_user: User = Depends(get_current_user),
):
    """删除念头"""
    if ActiveConsciousnessService.delete_thought(thought_id):
        return SuccessResponse(message="已删除")
    raise HTTPException(status_code=500, detail="删除失败")


@router.get("/thoughts/{thought_id}")
async def get_thought_detail(thought_id: int,
    current_user: User = Depends(get_current_user),
):
    """获取单条念头详情（含完整 details JSON）"""
    return ActiveConsciousnessService.get_thought_detail(thought_id)


@router.post("/thoughts/{thought_id}/retry")
async def retry_thought(thought_id: int,
    current_user: User = Depends(get_current_user),
):
    """重试发送念头"""
    return await ActiveConsciousnessService.retry_thought(thought_id)


@router.get("/heartbeats")
async def get_heartbeats(page: int = 1, page_size: int = 20, date: str = None,
                         heartbeat_id: int = None,
    current_user: User = Depends(get_current_user),
):
    """获取心跳日志，支持 date=YYYY-MM-DD / heartbeat_id 过滤"""
    return ActiveConsciousnessService.get_heartbeats(page, page_size, date, heartbeat_id)


@router.get("/heartbeats/{heartbeat_id}")
async def get_heartbeat_detail(heartbeat_id: int,
    current_user: User = Depends(get_current_user),
):
    """获取单条心跳日志详情（含完整 details JSON）"""
    return ActiveConsciousnessService.get_heartbeat_detail(heartbeat_id)


@router.delete("/heartbeats/{heartbeat_id}", response_model=SuccessResponse)
async def delete_heartbeat(heartbeat_id: int,
    current_user: User = Depends(get_current_user),
):
    """删除心跳日志"""
    if ActiveConsciousnessService.delete_heartbeat(heartbeat_id):
        return SuccessResponse(message="已删除")
    raise HTTPException(status_code=500, detail="删除失败")


# ============ 测试 ============

def _apply_form_overrides(config: dict, form: dict | None) -> dict:
    """把前端表单当前值（未保存）覆盖到配置上——测试用，不落库。

    form 期望形如 {llm: {...}, emotion_llm/thought_llm: {...}}，
    缺失的键保持 DB 配置，保证向后兼容（不传 body = 原行为）。
    """
    if not form:
        return config
    for key in ("llm", "emotion_llm", "thought_llm"):
        if isinstance(form.get(key), dict):
            config[key] = form[key]
    return config


@router.post("/test/llm-connect")
async def test_llm_connect(
    form: dict | None = Body(default=None),
    current_user: User = Depends(get_current_user),
):
    """测试 LLM 连通性（支持传入未保存的表单配置）"""
    config = _apply_form_overrides(ActiveConsciousnessService.get_config(), form)
    llm_config = config.get("llm", {})
    return await _test_llm_connection(llm_config, "通用 LLM")


async def _test_llm_connection(llm_config: dict, label: str) -> dict:
    """通用 LLM 连通测试（不限制 max_tokens）"""
    import time
    try:
        test_prompt = "请回复'连接成功'两个字"
        start_ms = time.time()
        if llm_config.get("mode") == "hermes":
            import asyncio, sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm
            response = await asyncio.to_thread(
                call_llm,
                messages=[{"role": "user", "content": test_prompt}],
                temperature=0.1,
            )
            raw = response.choices[0].message.content or ""
            duration_ms = int((time.time() - start_ms) * 1000)
            return {"success": True, "data": {"mode": "hermes", "response": raw, "model": "hermes default", "label": label, "duration_ms": duration_ms}}
        else:
            if not llm_config.get("api_key"):
                return {"success": False, "error": f"{label}未配置 API Key"}
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{llm_config.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                    json={"model": llm_config.get("model", "deepseek-chat"), "messages": [{"role": "user", "content": test_prompt}], "temperature": 0.1}
                )
                duration_ms = int((time.time() - start_ms) * 1000)
                data = resp.json()
                if "choices" in data and data["choices"]:
                    msg = data["choices"][0].get("message", {})
                    # 兼容不同模型：content 可能在 content 或 reasoning 字段
                    raw = msg.get("content") or msg.get("reasoning") or ""
                    return {"success": True, "data": {"mode": "custom", "response": raw, "model": llm_config.get("model"), "base_url": llm_config.get("base_url"), "label": label, "duration_ms": duration_ms}}
                else:
                    return {"success": False, "error": f"{label} LLM 返回异常: {data}"}
    except Exception as e:
        return {"success": False, "error": f"{label}: {str(e)}"}


@router.post("/test/emotion-llm-connect")
async def test_emotion_llm_connect(
    form: dict | None = Body(default=None),
    current_user: User = Depends(get_current_user),
):
    """测试情绪评估 LLM 连通性（支持传入未保存的表单配置）"""
    config = _apply_form_overrides(ActiveConsciousnessService.get_config(), form)
    from services.active_consciousness_service import get_effective_llm_config
    llm_config = get_effective_llm_config(config, "emotion")
    return await _test_llm_connection(llm_config, "情绪评估")


@router.post("/test/thought-llm-connect")
async def test_thought_llm_connect(
    form: dict | None = Body(default=None),
    current_user: User = Depends(get_current_user),
):
    """测试念头生成 LLM 连通性（支持传入未保存的表单配置）"""
    config = _apply_form_overrides(ActiveConsciousnessService.get_config(), form)
    from services.active_consciousness_service import get_effective_llm_config
    llm_config = get_effective_llm_config(config, "thought")
    return await _test_llm_connection(llm_config, "念头生成")


@router.post("/test/thought-generation")
async def test_thought_generation(
    current_user: User = Depends(get_current_user),
):
    """测试念头生成（使用 ThoughtEngine 统一入口）"""
    try:
        config = ActiveConsciousnessService.get_config()
        if not config.get("enabled"):
            return {"success": False, "error": "主动意识未启用"}

        status = ActiveConsciousnessService.get_status()
        from services.thought_engine import ThoughtEngine
        engine = ThoughtEngine(config)
        result = await engine.generate(status)

        return {
            "success": True,
            "data": {
                "thought": result.get("thought"),
                "want_to_contact": result.get("want_to_contact"),
                "llm_details": result.get("llm_details"),
                "context_bundle": {
                    "conversations_count": len(result.get("context_bundle", {}).get("conversations", [])),
                    "memories_count": len(result.get("context_bundle", {}).get("memories", [])),
                }
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/session-context")
async def test_session_context(
    current_user: User = Depends(get_current_user),
):
    """测试 Session 上下文获取"""
    try:
        from services.context_collector import ContextCollector

        config = ActiveConsciousnessService.get_config()
        status = ActiveConsciousnessService.get_status()
        collector = ContextCollector(config)
        context = await collector.collect(status)

        return {
            "success": True,
            "data": {
                "context": "\n".join(
                    f"{m.get('role','?')}: {m.get('content','')[:200]}"
                    for m in context.conversations[-20:]
                ),
                "conversations_count": len(context.conversations),
                "memories_count": len(context.memories),
                "has_content": bool(context.conversations)
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/context-collector")
async def test_context_collector(
    current_user: User = Depends(get_current_user),
):
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
async def test_thought_engine(
    current_user: User = Depends(get_current_user),
):
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
