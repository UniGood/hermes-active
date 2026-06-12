"""
调度器服务 - 使用 APScheduler 管理定时任务
"""
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from models.database import ActiveSession
from services.config_service import ConfigService
from services.message_service import MessageService
from services.session_service import SessionService
from services.llm_service import LLMService

logger = logging.getLogger("hermes.scheduler")

# 全局调度器实例
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def run_cron_job(job_id: str):
    """执行定时任务"""
    db = ActiveSession()
    try:
        jobs = ConfigService.get_cron_jobs(db)
        target_job = None
        for job in jobs:
            if job["id"] == job_id:
                target_job = job
                break

        if not target_job:
            logger.warning(f"任务 {job_id} 不存在")
            return

        if not target_job.get("enabled", False):
            logger.info(f"任务 {target_job['name']} 已禁用，跳过")
            return

        logger.info(f"开始执行任务: {target_job['name']} ({job_id})")
        start_time = datetime.now().timestamp()

        # 获取 session
        session_id = target_job.get("session_id")
        platform = target_job.get("platform", "weixin")

        if session_id:
            session = SessionService.get_session_by_id(db, session_id)
        else:
            session = SessionService.get_latest_session(platform)

        if not session:
            logger.error(f"任务 {target_job['name']} 未找到可用 session (平台: {platform})")
            MessageService.create_task_log(
                task_type="cron_run",
                status="failed",
                message=f"任务 {target_job['name']} 运行失败",
                error=f"未找到可用 session (平台: {platform})",
                duration=round(datetime.now().timestamp() - start_time, 2)
            )
            return

        sid = session["id"] if isinstance(session, dict) else session.id

        # 获取 LLM 配置和提示词配置
        llm_config = ConfigService.get_llm_config(db)
        prompts_config = ConfigService.get_prompts_config(db)

        prompt_text = target_job.get("prompt") or prompts_config.get("system", "")

        # 获取上下文
        context_limit = target_job.get("context_limit", 20)
        context_msgs = MessageService.get_session_context_raw(sid, limit=context_limit)
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
                logger.error(f"任务 {target_job['name']} LLM 生成失败: {llm_result.get('message')}")
                MessageService.create_task_log(
                    task_type="cron_run",
                    status="failed",
                    message=f"任务 {target_job['name']} LLM 生成失败",
                    error=llm_result.get("message", "未知错误"),
                    duration=round(datetime.now().timestamp() - start_time, 2)
                )
                return

            generated_message = llm_result["content"]
        else:
            generated_message = prompt_text

        # 发送消息
        send_result = await MessageService.send_message(
            session_id=sid,
            message=generated_message,
            platform=platform,
            write_to_db=write_to_db,
            with_mark=with_mark,
            mark_format=mark_format
        )

        duration = round(datetime.now().timestamp() - start_time, 2)

        # 更新 last_run_at
        target_job["last_run_at"] = datetime.utcnow().isoformat()
        ConfigService.save_cron_jobs(db, jobs)

        if send_result.get("success"):
            logger.info(f"任务 {target_job['name']} 运行成功，耗时 {duration}s")
            MessageService.create_task_log(
                task_type="cron_run",
                status="success",
                message=f"任务 {target_job['name']} 运行成功，session: {sid}",
                duration=duration
            )
        else:
            logger.error(f"任务 {target_job['name']} 发送失败: {send_result.get('message')}")
            MessageService.create_task_log(
                task_type="cron_run",
                status="failed",
                message=f"任务 {target_job['name']} 发送失败",
                error=send_result.get("message", "未知错误"),
                duration=duration
            )

    except Exception as e:
        logger.exception(f"任务 {job_id} 运行异常: {e}")
        MessageService.create_task_log(
            task_type="cron_run",
            status="failed",
            message=f"任务运行异常",
            error=str(e),
            duration=0
        )
    finally:
        db.close()


def _parse_cron_schedule(schedule: str) -> dict:
    """解析 cron 表达式为 CronTrigger 参数"""
    parts = schedule.strip().split()
    if len(parts) != 5:
        raise ValueError(f"无效的 cron 表达式: {schedule}")

    minute, hour, day, month, dow = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": dow,
    }


def sync_jobs_from_db():
    """从数据库同步任务到调度器"""
    db = ActiveSession()
    try:
        jobs = ConfigService.get_cron_jobs(db)
    finally:
        db.close()

    # 获取当前调度器中的任务 ID
    existing_job_ids = {job.id for job in scheduler.get_jobs()}
    db_job_ids = set()

    for job_config in jobs:
        job_id = job_config["id"]
        db_job_ids.add(job_id)

        if not job_config.get("enabled", False):
            # 如果任务被禁用，移除调度器中的任务
            if job_id in existing_job_ids:
                scheduler.remove_job(job_id)
                logger.info(f"移除禁用任务: {job_config['name']} ({job_id})")
            continue

        schedule = job_config.get("schedule", "")
        if not schedule:
            continue

        try:
            trigger_params = _parse_cron_schedule(schedule)
            trigger = CronTrigger(**trigger_params, timezone="Asia/Shanghai")

            # 如果任务已存在，更新它；否则添加新任务
            if job_id in existing_job_ids:
                scheduler.reschedule_job(job_id, trigger=trigger)
                logger.info(f"更新任务调度: {job_config['name']} ({job_id}) -> {schedule}")
            else:
                scheduler.add_job(
                    run_cron_job,
                    trigger=trigger,
                    id=job_id,
                    args=[job_id],
                    name=job_config.get("name", job_id),
                    replace_existing=True
                )
                logger.info(f"添加任务: {job_config['name']} ({job_id}) -> {schedule}")
        except Exception as e:
            logger.error(f"解析任务 {job_config['name']} 的 cron 表达式失败: {e}")

    # 移除数据库中已删除的任务
    for job_id in existing_job_ids - db_job_ids:
        scheduler.remove_job(job_id)
        logger.info(f"移除已删除任务: {job_id}")


def start_scheduler():
    """启动调度器"""
    if scheduler.running:
        logger.info("调度器已在运行")
        return

    scheduler.start()
    logger.info("调度器已启动")

    # 从数据库加载任务
    sync_jobs_from_db()

    # 添加定时同步任务（每分钟检查一次数据库中的任务变更）
    scheduler.add_job(
        sync_jobs_from_db,
        trigger="interval",
        minutes=1,
        id="_sync_jobs",
        name="同步任务配置",
        replace_existing=True
    )


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")
