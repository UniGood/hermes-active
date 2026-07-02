"""
自由意识 API 路由
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/free-consciousness", tags=["free-consciousness"])


@router.get("/status")
async def get_status():
    """获取状态"""
    from services.free_consciousness_service import FreeConsciousnessService
    return FreeConsciousnessService.get_status()


@router.post("/toggle")
async def toggle(enabled: bool = Body(..., embed=True)):
    """开关"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, start_fc_scheduler, stop_fc_scheduler
    )
    config = FreeConsciousnessService.get_config()
    config["enabled"] = enabled
    FreeConsciousnessService.update_config(config)

    if enabled:
        start_fc_scheduler()
    else:
        stop_fc_scheduler()

    return {"success": True, "enabled": enabled}


@router.post("/restart")
async def restart():
    """重启调度器"""
    from services.free_consciousness_service import restart_fc_scheduler
    restart_fc_scheduler()
    return {"success": True}


@router.get("/config")
async def get_config():
    """获取配置"""
    from services.free_consciousness_service import FreeConsciousnessService
    return FreeConsciousnessService.get_config()


@router.post("/config")
async def save_config(config: dict = Body(...)):
    """保存配置"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, restart_fc_scheduler
    )
    FreeConsciousnessService.update_config(config)
    # 如果启用了，重启调度器以应用新配置
    full_config = FreeConsciousnessService.get_config()
    if full_config.get("enabled"):
        restart_fc_scheduler()
    return {"success": True}


@router.post("/test-llm")
async def test_llm():
    """测试 LLM 连通性"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, test_llm_connection
    )
    config = FreeConsciousnessService.get_config()
    return await test_llm_connection(config)


@router.get("/logs")
async def get_logs(page: int = 1, page_size: int = 20, round_number: Optional[int] = None):
    """分页查询日志"""
    from services.free_consciousness_service import FreeConsciousnessService
    return FreeConsciousnessService.get_logs(page, page_size, round_number)


@router.get("/logs/{log_id}")
async def get_log_detail(log_id: int):
    """日志详情"""
    from services.free_consciousness_service import FreeConsciousnessService
    detail = FreeConsciousnessService.get_log_detail(log_id)
    if not detail:
        raise HTTPException(status_code=404, detail="日志不存在")
    return detail


@router.delete("/logs/{log_id}")
async def delete_log(log_id: int):
    """删除日志"""
    from services.free_consciousness_service import FreeConsciousnessService
    if not FreeConsciousnessService.delete_log(log_id):
        raise HTTPException(status_code=404, detail="日志不存在")
    return {"success": True}


@router.get("/chain")
async def get_chain():
    """获取当前完整思考链"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, load_thinking_chain, build_thinking_chain
    )
    config = FreeConsciousnessService.get_config()
    records = load_thinking_chain(config)
    chain = build_thinking_chain(records, config)
    return {"chain": chain, "records_count": len(records)}


@router.post("/run")
async def manual_run():
    """手动触发一次沉思"""
    from services.free_consciousness_service import run_contemplation
    try:
        await run_contemplation()
        return {"success": True, "message": "沉思已执行"}
    except Exception as e:
        return {"success": False, "message": str(e)}
