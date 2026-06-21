"""
定时任务路由
"""
import time
import logging
from datetime import datetime

logger = logging.getLogger("hermes.cron")
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import CronJobCreate, CronJobUpdate, CronJobInfo, CronJobListResponse, PreviewPromptRequest, SuccessResponse
from services.config_service import ConfigService
from services.llm_service import LLMService
from services.message_service import MessageService
from services.session_service import SessionService
from services.scheduler_service import sync_jobs_from_db
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/cron", tags=["定时任务"])


@router.get("", response_model=CronJobListResponse)
async def get_cron_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取任务列表"""
    jobs = ConfigService.get_cron_jobs(db)
    return CronJobListResponse(items=[CronJobInfo(**job) for job in jobs])


@router.post("", response_model=SuccessResponse)
async def create_cron_job(
    request: CronJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """创建任务"""
    import uuid

    jobs = ConfigService.get_cron_jobs(db)

    new_job = {
        "id": str(uuid.uuid4())[:8],
        "name": request.name,
        "schedule": request.schedule,
        "enabled": request.enabled,
        "prompt": request.prompt,
        "system_prompt": request.system_prompt,
        "user_prompt": request.user_prompt,
        "append_soul_md": request.append_soul_md,
        "session_id": request.session_id,
        "platform": request.platform,
        "use_llm": request.use_llm,
        "write_to_db": request.write_to_db,
        "with_mark": request.with_mark,
        "mark_format": request.mark_format,
        "send_mark": request.send_mark,
        "time_format": request.time_format,
        "cooldown_enabled": request.cooldown_enabled,
        "cooldown_minutes": request.cooldown_minutes,
        "last_run_at": None,
        "next_run_at": None
    }

    jobs.append(new_job)
    ConfigService.save_cron_jobs(db, jobs)

    # 同步到调度器
    sync_jobs_from_db()

    return SuccessResponse(message="任务创建成功")


@router.put("/{job_id}", response_model=SuccessResponse)
async def update_cron_job(
    job_id: str,
    request: CronJobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新任务"""
    jobs = ConfigService.get_cron_jobs(db)

    for job in jobs:
        if job["id"] == job_id:
            if request.name is not None:
                job["name"] = request.name
            if request.schedule is not None:
                job["schedule"] = request.schedule
            if request.enabled is not None:
                job["enabled"] = request.enabled
            if request.prompt is not None:
                job["prompt"] = request.prompt
            if request.system_prompt is not None:
                job["system_prompt"] = request.system_prompt
            if request.user_prompt is not None:
                job["user_prompt"] = request.user_prompt
            if request.append_soul_md is not None:
                job["append_soul_md"] = request.append_soul_md
            if request.session_id is not None:
                job["session_id"] = request.session_id
            if request.platform is not None:
                job["platform"] = request.platform
            if request.use_llm is not None:
                job["use_llm"] = request.use_llm
            if request.write_to_db is not None:
                job["write_to_db"] = request.write_to_db
            if request.with_mark is not None:
                job["with_mark"] = request.with_mark
            if request.mark_format is not None:
                job["mark_format"] = request.mark_format
            if request.send_mark is not None:
                job["send_mark"] = request.send_mark
            if request.time_format is not None:
                job["time_format"] = request.time_format
            if request.cooldown_enabled is not None:
                job["cooldown_enabled"] = request.cooldown_enabled
            if request.cooldown_minutes is not None:
                job["cooldown_minutes"] = request.cooldown_minutes

            ConfigService.save_cron_jobs(db, jobs)
            # 同步到调度器
            sync_jobs_from_db()
            return SuccessResponse(message="任务更新成功")

    raise HTTPException(status_code=404, detail="任务不存在")


@router.delete("/{job_id}", response_model=SuccessResponse)
async def delete_cron_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """删除任务"""
    jobs = ConfigService.get_cron_jobs(db)
    jobs = [job for job in jobs if job["id"] != job_id]
    ConfigService.save_cron_jobs(db, jobs)

    # 同步到调度器
    sync_jobs_from_db()

    return SuccessResponse(message="任务删除成功")


@router.post("/{job_id}/run", response_model=SuccessResponse)
async def run_cron_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """手动运行任务（复用 scheduler_service.run_cron_job，保证 details 完整）"""
    # 先校验任务存在
    jobs = ConfigService.get_cron_jobs(db)
    target_job = next((j for j in jobs if j["id"] == job_id), None)
    if not target_job:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 记录开始前的最新 task_log id，用来识别本次新写入的日志
    from models.active import TaskLog as _TaskLog
    last_log_id = db.query(_TaskLog).order_by(_TaskLog.id.desc()).first()
    last_log_id = last_log_id.id if last_log_id else 0

    # 复用 scheduler_service 的实现（带 details）
    from services.scheduler_service import run_cron_job as _scheduler_run
    await _scheduler_run(job_id)

    # 查本次产生的最新日志，给前端响应
    new_log = db.query(_TaskLog).filter(_TaskLog.id > last_log_id)\
        .order_by(_TaskLog.id.desc()).first()

    if not new_log:
        return SuccessResponse(message=f"任务 {target_job['name']} 已执行，但未产生日志")

    if new_log.status == "success":
        return SuccessResponse(message=f"任务 {target_job['name']} 运行成功，消息已发送到 session")
    if new_log.status == "skipped":
        reason = (new_log.error or "").strip() or "跳过原因未记录"
        return SuccessResponse(message=f"任务 {target_job['name']} 跳过执行：{reason}")

    # failed
    raise HTTPException(
        status_code=500,
        detail=f"任务 {target_job['name']} 失败：{new_log.error or '未知错误'}"
    )


@router.post("/{job_id}/toggle", response_model=SuccessResponse)
async def toggle_cron_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """切换任务状态"""
    jobs = ConfigService.get_cron_jobs(db)

    for job in jobs:
        if job["id"] == job_id:
            job["enabled"] = not job["enabled"]
            ConfigService.save_cron_jobs(db, jobs)

            # 同步到调度器
            sync_jobs_from_db()

            status = "启用" if job["enabled"] else "暂停"
            return SuccessResponse(message=f"任务已{status}")

    raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/parse-cron")
async def parse_cron_expression(
    expression: str = Query(..., description="Cron 表达式"),
    current_user: User = Depends(get_current_user)
):
    """解析 cron 表达式，返回下次运行时间和频率描述"""
    try:
        from croniter import croniter
        from datetime import datetime

        now = datetime.now()
        cron = croniter(expression, now)

        # 获取接下来 10 次运行时间
        next_runs = []
        for _ in range(10):
            next_time = cron.get_next(datetime)
            next_runs.append(next_time.strftime("%Y-%m-%d %H:%M:%S"))

        # 生成频率描述
        parts = expression.split()
        if len(parts) == 5:
            minute, hour, day, month, dow = parts

            # 简单的频率描述生成
            if minute.startswith("*/"):
                freq = f"每 {minute[2:]} 分钟"
            elif hour.startswith("*/"):
                freq = f"每 {hour[2:]} 小时"
            elif minute == "0" and hour == "0":
                freq = "每天午夜"
            elif minute == "0" and hour.isdigit():
                freq = f"每天 {hour}:00"
            elif hour and "-" in hour and minute.isdigit():
                freq = f"每天 {hour}:{minute.zfill(2)}"
            else:
                freq = f"{expression}"
        else:
            freq = expression

        return {
            "success": True,
            "expression": expression,
            "next_runs": next_runs,
            "frequency": freq
        }
    except ImportError:
        return {
            "success": False,
            "message": "croniter 库未安装，请运行: pip install croniter"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Cron 表达式解析失败: {str(e)}"
        }


@router.get("/sessions")
async def get_available_sessions(
    platform: str = Query("weixin", description="平台类型"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取可用的 session 列表（用于任务配置）"""
    sessions = SessionService.get_sessions(db, page=1, page_size=20, platform=platform)
    return sessions


@router.post("/preview-prompt")
async def preview_prompt(
    request: PreviewPromptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """预览最终提示词（拼接 soul.md 和上下文配置后）"""
    import httpx

    # 获取默认提示词配置（如果传入的为空）
    system_prompt = request.system_prompt
    if not system_prompt:
        system_prompt = ConfigService.get_config(db, "default_system_prompt") or ""

    user_prompt = request.user_prompt
    if not user_prompt:
        user_prompt = ConfigService.get_config(db, "default_user_prompt") or ""

    # 拼接 soul.md
    soul_md_content = ""
    final_system_prompt = system_prompt
    if request.append_soul_md:
        soul_md_content = ConfigService.read_hermes_soul() or ""
        if soul_md_content:
            final_system_prompt = system_prompt + "\n\n" + soul_md_content if system_prompt else soul_md_content

    # 解析上下文配置
    ctx_config = request.context_config or {}
    session_enabled = ctx_config.get("session_enabled", True)
    session_limit = ctx_config.get("session_limit", 20)
    include_tool = ctx_config.get("include_tool", False)
    recall_enabled = ctx_config.get("hindsight_recall_enabled", False)
    recall_query = ctx_config.get("hindsight_recall_query", "")
    recall_limit = ctx_config.get("hindsight_recall_limit", 10)
    reflect_enabled = ctx_config.get("hindsight_reflect_enabled", False)
    reflect_query = ctx_config.get("hindsight_reflect_query", "")
    weather_enabled = ctx_config.get("weather_enabled", False)
    weather_days = max(0, min(3, int(ctx_config.get("weather_days", 0) or 0)))

    # 上下文数据
    context_data = {
        "session_messages": [],
        "recall_results": [],
        "reflect_result": "",
        "weather_text": ""
    }

    # 确定 session_id：优先使用传入的，否则获取最新活跃 session
    effective_session_id = request.session_id
    if not effective_session_id:
        # 尝试获取最新活跃 session（自动处理过期）
        user_id = SessionService.get_user_id_for_platform("weixin")
        if user_id:
            from services.fallback_session_service import FallbackSessionService
            latest_session = FallbackSessionService.get_or_create_active_session("weixin", user_id)
            if latest_session:
                effective_session_id = latest_session.get("id")

    # 获取 Session 上下文
    if session_enabled and effective_session_id:
        context_msgs = MessageService.get_session_context_raw(effective_session_id, limit=session_limit, include_tool=include_tool)
        context_data["session_messages"] = [
            {"role": m.get("role", "unknown"), "content": m.get("content", "")}
            for m in context_msgs
        ]

    # 获取 Hindsight Recall
    if recall_enabled and recall_query:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8888/v1/default/banks/hermes/memories/recall",
                    json={"query": recall_query, "limit": recall_limit}
                )
                if response.status_code == 200:
                    data = response.json()
                    context_data["recall_results"] = data.get("results", [])
        except Exception:
            pass  # 静默失败，不影响预览

    # 获取 Hindsight Reflect
    if reflect_enabled and reflect_query:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8888/v1/default/banks/hermes/reflect",
                    json={"query": reflect_query, "limit": 10}
                )
                if response.status_code == 200:
                    data = response.json()
                    context_data["reflect_result"] = data.get("reflection", "")
        except Exception:
            pass  # 静默失败，不影响预览

    # 获取天气（复用配置管理中的 amap 配置；extensions=all 最多预报 3 天）
    if weather_enabled:
        try:
            from services.scheduler_service import fetch_weather_for_context
            raw_days = ctx_config.get("weather_days", 0)
            try:
                wd = int(raw_days)
            except (ValueError, TypeError):
                wd = 0
            if wd not in (0, 2, 3, 4):
                wd = 0
            context_data["weather_text"] = await fetch_weather_for_context(forecast_days=wd)
        except Exception:
            pass  # 静默失败，不影响预览

    # 构建上下文文本并替换 {context}
    context_parts = []
    if context_data["session_messages"]:
        context_parts.append(
            "\n".join(f"{m['role']}: {m['content']}" for m in context_data["session_messages"])
        )
    if context_data["recall_results"]:
        recall_texts = [r.get("text", "") for r in context_data["recall_results"] if r.get("text")]
        if recall_texts:
            context_parts.append("[Recall 记忆]\n" + "\n".join(recall_texts))
    if context_data["reflect_result"]:
        context_parts.append("[Reflect 分析]\n" + context_data["reflect_result"])
    if context_data["weather_text"]:
        context_parts.append("[当前天气]\n" + context_data["weather_text"])

    context_text = "\n\n".join(context_parts) if context_parts else ""
    final_user_prompt = user_prompt.replace("{context}", context_text)

    # 构建上下文配置摘要
    context_summary_parts = []
    if context_data["session_messages"]:
        context_summary_parts.append(f"Session: {len(context_data['session_messages'])} 条")
    if context_data["recall_results"]:
        context_summary_parts.append(f"Recall: {len(context_data['recall_results'])} 条")
    if context_data["reflect_result"]:
        context_summary_parts.append("Reflect: 1 条")
    if context_data["weather_text"]:
        context_summary_parts.append("Weather: 已启用")
    if not context_summary_parts:
        context_summary_parts.append("无上下文数据")

    return {
        "system_prompt": final_system_prompt,
        "user_prompt": final_user_prompt,
        "soul_md": soul_md_content,
        "context_summary": " | ".join(context_summary_parts),
        "context_data": context_data
    }
