"""
任务日志路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import get_active_db
from models.active import User, TaskLog
from models.schemas import TaskLogInfo, TaskLogListResponse, SuccessResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/task-logs", tags=["任务日志"])


@router.get("", response_model=TaskLogListResponse)
async def get_task_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
    job_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取任务日志列表"""
    query = db.query(TaskLog)

    # 筛选
    if task_type:
        query = query.filter(TaskLog.task_type == task_type)
    if status:
        query = query.filter(TaskLog.status == status)
    if message:
        query = query.filter(TaskLog.message.like(f"%{message}%"))
    if job_name:
        query = query.filter(TaskLog.message.like(f"%{job_name}%"))

    # 获取总数
    total = query.count()

    # 分页
    logs = query.order_by(TaskLog.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return TaskLogListResponse(
        total=total,
        items=[TaskLogInfo(**log.to_dict()) for log in logs]
    )


@router.get("/stats")
async def get_task_log_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取任务日志统计"""
    total = db.query(TaskLog).count()
    success = db.query(TaskLog).filter(TaskLog.status == "success").count()
    failed = db.query(TaskLog).filter(TaskLog.status == "failed").count()

    # 按任务类型统计
    type_stats = db.query(
        TaskLog.task_type,
        func.count(TaskLog.id).label("count")
    ).group_by(TaskLog.task_type).all()

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "by_type": [{"type": t[0], "count": t[1]} for t in type_stats]
    }


@router.get("/{log_id}", response_model=TaskLogInfo)
async def get_task_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取任务日志详情"""
    log = db.query(TaskLog).filter(TaskLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return TaskLogInfo(**log.to_dict())


@router.post("", response_model=SuccessResponse)
async def create_task_log(
    task_type: str = Query(...),
    status: str = Query(...),
    message: Optional[str] = None,
    error: Optional[str] = None,
    duration: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """创建任务日志"""
    log = TaskLog(
        task_type=task_type,
        status=status,
        message=message,
        error=error,
        duration=duration
    )
    db.add(log)
    db.commit()
    return SuccessResponse(message="日志创建成功")


@router.delete("/{log_id}", response_model=SuccessResponse)
async def delete_task_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """删除任务日志"""
    log = db.query(TaskLog).filter(TaskLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    db.delete(log)
    db.commit()

    return SuccessResponse(message="日志删除成功")


@router.delete("", response_model=SuccessResponse)
async def clear_task_logs(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """批量清除任务日志"""
    query = db.query(TaskLog)

    if task_type:
        query = query.filter(TaskLog.task_type == task_type)
    if status:
        query = query.filter(TaskLog.status == status)

    count = query.count()
    query.delete()
    db.commit()

    return SuccessResponse(message=f"已清除 {count} 条日志")
