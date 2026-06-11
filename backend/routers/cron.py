"""
定时任务路由
"""
import time
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import CronJobCreate, CronJobUpdate, CronJobInfo, CronJobListResponse, SuccessResponse
from services.config_service import ConfigService
from services.llm_service import LLMService
from services.message_service import MessageService
from services.session_service import SessionService
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
        "last_run_at": None,
        "next_run_at": None
    }

    jobs.append(new_job)
    ConfigService.save_cron_jobs(db, jobs)

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

            ConfigService.save_cron_jobs(db, jobs)
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
        # 获取最新 session
        session = SessionService.get_latest_session("weixin")
        if not session:
            MessageService.create_task_log(
                task_type="cron_run",
                status="failed",
                message=f"任务 {target_job['name']} 运行失败",
                error="未找到可用 session",
                duration=round(time.time() - start_time, 2)
            )
            raise HTTPException(status_code=400, detail="未找到可用 session")

        # 获取 LLM 配置和提示词配置
        llm_config = ConfigService.get_llm_config(db)
        prompts_config = ConfigService.get_prompts_config(db)

        prompt_text = target_job.get("prompt") or prompts_config.get("system", "")

        # 获取上下文
        context_msgs = MessageService.get_session_context_raw(session["id"], limit=20)
        context_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in context_msgs
        )

        generation_template = prompts_config.get("generation", "{context}")
        user_prompt = generation_template.replace("{context}", context_text)

        # 调用 LLM 生成消息
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

        # 发送消息（上下文注入）
        send_result = await MessageService.send_message(
            session_id=session["id"],
            message=generated_message,
            platform="weixin"
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
                message=f"任务 {target_job['name']} 运行成功，session: {session['id']}",
                duration=duration
            )
            return SuccessResponse(message=f"任务运行成功，消息已发送到 session {session['id']}")
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

            status = "启用" if job["enabled"] else "暂停"
            return SuccessResponse(message=f"任务已{status}")

    raise HTTPException(status_code=404, detail="任务不存在")
