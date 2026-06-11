"""
任务日志路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

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
