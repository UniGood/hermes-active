"""
定时任务路由
"""
import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import CronJobCreate, CronJobUpdate, CronJobInfo, CronJobListResponse, SuccessResponse
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
        "session_id": request.session_id,
        "platform": request.platform,
        "use_llm": request.use_llm,
        "write_to_db": request.write_to_db,
        "with_mark": request.with_mark,
        "mark_format": request.mark_format,
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
    """手动运行任务"""
    start_time = time.time()
    jobs = ConfigService.get_cron_jobs(db)

    # 查找任务
    target_job = None
    for job in jobs:
        if job["id"] == job_id:
            target_job = job
            break

    if not target_job:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        # 获取 session - 优先使用任务配置的 session_id
        session_id = target_job.get("session_id")
        platform = target_job.get("platform", "weixin")

        if session_id:
            # 指定了 session_id，直接使用
            session = SessionService.get_session_by_id(db, session_id)
        else:
            # 未指定 session_id，获取该平台最新活跃 session
            session = SessionService.get_latest_session(platform)

        if not session:
            MessageService.create_task_log(
                task_type="cron_run",
                status="failed",
                message=f"任务 {target_job['name']} 运行失败",
                error=f"未找到可用 session (平台: {platform})",
                duration=round(time.time() - start_time, 2)
            )
            raise HTTPException(status_code=400, detail=f"未找到可用 session (平台: {platform})")

        session_id = session["id"] if isinstance(session, dict) else session.id

        # 获取 LLM 配置和提示词配置
        llm_config = ConfigService.get_llm_config(db)
        prompts_config = ConfigService.get_prompts_config(db)

        raw_prompt = target_job.get("prompt") or ""
        # 从 prompt 中解析上下文配置
        from services.scheduler_service import _parse_context_config
        ctx_config, user_prompt_text = _parse_context_config(raw_prompt)
        prompt_text = user_prompt_text or prompts_config.get("system", "")

        # 获取上下文
        context_limit = ctx_config.get("session_limit", 20)
        context_msgs = MessageService.get_session_context_raw(session_id, limit=context_limit)
        context_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in context_msgs
        )

        generation_template = prompts_config.get("generation", "{context}")
        user_prompt = generation_template.replace("{context}", context_text)

        # 获取任务参数
        use_llm = target_job.get("use_llm", True)
        write_to_db = target_job.get("write_to_db", True)
        with_mark = target_job.get("with_mark", True)
        mark_format = target_job.get("mark_format", "[凯莉主动发送] {timestamp}: {content}")

        generated_message = ""

        # 调用 LLM 生成消息
        if use_llm:
            llm_result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=user_prompt,
                system_prompt=prompt_text,
                temperature=0.7,
                max_tokens=200
            )

            if not llm_result.get("success"):
                MessageService.create_task_log(
                    task_type="cron_run",
                    status="failed",
                    message=f"任务 {target_job['name']} LLM 生成失败",
                    error=llm_result.get("message", "未知错误"),
                    duration=round(time.time() - start_time, 2)
                )
                raise HTTPException(status_code=500, detail=f"LLM 生成失败: {llm_result.get('message')}")

            generated_message = llm_result["content"]
        else:
            # 不使用 LLM，使用提示词作为消息
            generated_message = prompt_text

        # 发送消息
        send_result = await MessageService.send_message(
            session_id=session_id,
            message=generated_message,
            platform=platform,
            write_to_db=write_to_db,
            with_mark=with_mark,
            mark_format=mark_format
        )

        duration = round(time.time() - start_time, 2)

        # 更新 last_run_at
        target_job["last_run_at"] = datetime.utcnow().isoformat()
        ConfigService.save_cron_jobs(db, jobs)

        # 记录日志
        if send_result.get("success"):
            MessageService.create_task_log(
                task_type="cron_run",
                status="success",
                message=f"任务 {target_job['name']} 运行成功，session: {session_id}",
                duration=duration
            )
            return SuccessResponse(message=f"任务运行成功，消息已发送到 session {session_id}")
        else:
            MessageService.create_task_log(
                task_type="cron_run",
                status="failed",
                message=f"任务 {target_job['name']} 发送失败",
                error=send_result.get("message", "未知错误"),
                duration=duration
            )
            raise HTTPException(status_code=500, detail=send_result.get("message", "发送失败"))

    except HTTPException:
        raise
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        MessageService.create_task_log(
            task_type="cron_run",
            status="failed",
            message=f"任务 {target_job['name']} 运行异常",
            error=str(e),
            duration=duration
        )
        raise HTTPException(status_code=500, detail=f"任务运行失败: {str(e)}")


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

        # 获取接下来 5 次运行时间
        next_runs = []
        for _ in range(5):
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
