"""
定时任务路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import CronJobCreate, CronJobUpdate, CronJobInfo, CronJobListResponse, SuccessResponse
from services.config_service import ConfigService
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
    # TODO: 实现手动运行任务逻辑
    # 1. 查找任务
    # 2. 执行任务
    # 3. 更新 last_run_at

    return SuccessResponse(message="任务运行成功")


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
