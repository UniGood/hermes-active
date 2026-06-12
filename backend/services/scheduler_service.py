"""
调度器服务 - 使用 APScheduler 管理定时任务
"""
import logging
import asyncio
import aiohttp
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from models.database import ActiveSession
from services.config_service import ConfigService
from services.message_service import MessageService
from services.session_service import SessionService
from services.llm_service import LLMService

logger = logging.getLogger("hermes.scheduler")

HINDSIGHT_BASE_URL = "http://localhost:8888/v1/default/banks/hermes"


async def call_hindsight_recall(query: str, limit: int = 10) -> list:
    """调用 Hindsight Recall API 获取相关记忆"""
    url = f"{HINDSIGHT_BASE_URL}/memories/recall"
    payload = {"query": query, "limit": limit}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", data.get("memories", []))
                    logger.info(f"Hindsight Recall 成功: {len(results)} 条结果")
                    return results
                else:
                    text = await resp.text()
                    logger.warning(f"Hindsight Recall 失败 ({resp.status}): {text}")
                    return []
    except Exception as e:
        logger.warning(f"Hindsight Recall 请求异常: {e}")
        return []


async def call_hindsight_reflect(query: str) -> str:
    """调用 Hindsight Reflect API 获取综合分析"""
    url = f"{HINDSIGHT_BASE_URL}/reflect"
    payload = {"query": query}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    reflection = data.get("reflection", data.get("result", ""))
                    logger.info("Hindsight Reflect 成功")
                    return reflection
                else:
                    text = await resp.text()
                    logger.warning(f"Hindsight Reflect 失败 ({resp.status}): {text}")
                    return ""
    except Exception as e:
        logger.warning(f"Hindsight Reflect 请求异常: {e}")
        return ""


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

        # 解析提示词 - 支持新的 system_prompt/user_prompt 字段和旧的 prompt 字段
        system_prompt_text = target_job.get("system_prompt")
        user_prompt_text = target_job.get("user_prompt")
        append_soul_md = target_job.get("append_soul_md", True)
        raw_prompt = target_job.get("prompt") or ""

        # 如果有新的 system_prompt/user_prompt 字段，优先使用
        if system_prompt_text is not None or user_prompt_text is not None:
            # 使用新字段
            prompt_text = system_prompt_text or prompts_config.get("system", "")

            # 如果需要拼接 soul.md
            if append_soul_md:
                soul_content = ConfigService.read_hermes_soul()
                if soul_content:
                    prompt_text = prompt_text + "\n\n" + soul_content if prompt_text else soul_content

            # 解析用户提示词中的上下文配置
            ctx_config, user_prompt_clean = _parse_context_config(user_prompt_text or "")
            user_prompt_final = user_prompt_clean or prompts_config.get("generation", "{context}")
        elif raw_prompt and "|||" in raw_prompt:
            # 兼容旧的 ||| 分隔格式
            parts = raw_prompt.split("|||", 1)
            prompt_text = parts[0].strip()
            user_prompt_raw = parts[1].strip()

            # 检查是否需要拼接 soul.md
            if prompt_text.endswith("[SOUL_MD]"):
                prompt_text = prompt_text[:-9].strip()
                soul_content = ConfigService.read_hermes_soul()
                if soul_content:
                    prompt_text = prompt_text + "\n\n" + soul_content if prompt_text else soul_content

            ctx_config, user_prompt_clean = _parse_context_config(user_prompt_raw)
            user_prompt_final = user_prompt_clean or prompts_config.get("generation", "{context}")
        else:
            # 兼容旧的单一 prompt 字段
            ctx_config, user_prompt_text = _parse_context_config(raw_prompt)
            prompt_text = user_prompt_text or prompts_config.get("system", "")
            user_prompt_final = prompts_config.get("generation", "{context}")

        # 获取上下文 - 拼接 Session、Hindsight Recall、Hindsight Reflect
        context_parts = []

        # 1. Session 上下文
        session_enabled = ctx_config.get("session_enabled", True)
        if session_enabled:
            context_limit = ctx_config.get("session_limit", 20)
            include_tool = ctx_config.get("include_tool", False)
            context_msgs = MessageService.get_session_context_raw(sid, limit=context_limit, include_tool=include_tool)
            if context_msgs:
                session_text = "\n".join(
                    f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                    for m in context_msgs
                )
                context_parts.append(f"=== 最近对话 ===\n{session_text}")

        # 2. Hindsight Recall
        recall_enabled = ctx_config.get("hindsight_recall_enabled", False)
        recall_query = ctx_config.get("hindsight_recall_query", "")
        if recall_enabled and recall_query:
            recall_limit = ctx_config.get("hindsight_recall_limit", 10)
            recall_results = await call_hindsight_recall(recall_query, recall_limit)
            if recall_results:
                recall_text = "\n".join(f"- {r.get('text', '')}" for r in recall_results)
                context_parts.append(f"=== 相关记忆 ===\n{recall_text}")

        # 3. Hindsight Reflect
        reflect_enabled = ctx_config.get("hindsight_reflect_enabled", False)
        reflect_query = ctx_config.get("hindsight_reflect_query", "")
        if reflect_enabled and reflect_query:
            reflect_result = await call_hindsight_reflect(reflect_query)
            if reflect_result:
                context_parts.append(f"=== 综合分析 ===\n{reflect_result}")

        context_text = "\n\n".join(context_parts)
        user_prompt = user_prompt_final.replace("{context}", context_text)

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

        # 更新 last_run_at 和 next_run_at
        target_job["last_run_at"] = datetime.utcnow().isoformat()
        # 计算 next_run_at
        try:
            from croniter import croniter
            schedule = target_job.get("schedule", "")
            if schedule:
                now = datetime.now()
                cron = croniter(schedule, now)
                target_job["next_run_at"] = cron.get_next(datetime).isoformat()
        except Exception as e:
            logger.warning(f"计算 next_run_at 失败: {e}")
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


CTX_MARKER_START = "<!--CTX:"
CTX_MARKER_END = "-->"


def _parse_context_config(raw_prompt: str) -> tuple:
    """从 prompt 中解析上下文配置，返回 (config_dict, user_prompt)"""
    import urllib.parse

    default_config = {
        "session_enabled": True,
        "session_limit": 20,
        "include_tool": False,
        "hindsight_recall_enabled": False,
        "hindsight_recall_query": "",
        "hindsight_recall_limit": 10,
        "hindsight_reflect_enabled": False,
        "hindsight_reflect_query": "",
    }

    if not raw_prompt or not raw_prompt.startswith(CTX_MARKER_START):
        return default_config, raw_prompt or ""

    end_idx = raw_prompt.find(CTX_MARKER_END)
    if end_idx == -1:
        return default_config, raw_prompt

    ctx_str = raw_prompt[len(CTX_MARKER_START):end_idx]
    user_prompt = raw_prompt[end_idx + len(CTX_MARKER_END):].strip()

    config = dict(default_config)
    for pair in ctx_str.split(";"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        if key == "session_enabled":
            config["session_enabled"] = value == "true"
        elif key == "session_limit":
            config["session_limit"] = int(value) if value.isdigit() else 20
        elif key == "include_tool":
            config["include_tool"] = value == "true"
        elif key == "recall":
            config["hindsight_recall_enabled"] = value == "true"
        elif key == "recall_query":
            config["hindsight_recall_query"] = urllib.parse.unquote(value)
        elif key == "recall_limit":
            config["hindsight_recall_limit"] = int(value) if value.isdigit() else 10
        elif key == "reflect":
            config["hindsight_reflect_enabled"] = value == "true"
        elif key == "reflect_query":
            config["hindsight_reflect_query"] = urllib.parse.unquote(value)

    return config, user_prompt


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
    jobs_updated = False

    for job_config in jobs:
        job_id = job_config["id"]
        db_job_ids.add(job_id)

        if not job_config.get("enabled", False):
            # 如果任务被禁用，移除调度器中的任务
            if job_id in existing_job_ids:
                scheduler.remove_job(job_id)
                logger.info(f"移除禁用任务: {job_config['name']} ({job_id})")
            # 禁用任务也要计算 next_run_at（但标记为 null）
            if job_config.get("next_run_at") is not None:
                job_config["next_run_at"] = None
                jobs_updated = True
            continue

        schedule = job_config.get("schedule", "")
        if not schedule:
            continue

        try:
            trigger_params = _parse_cron_schedule(schedule)
            trigger = CronTrigger(**trigger_params, timezone="Asia/Shanghai")

            # 使用 croniter 计算 next_run_at
            try:
                from croniter import croniter
                now = datetime.now()
                cron = croniter(schedule, now)
                next_run = cron.get_next(datetime)
                next_run_iso = next_run.isoformat()

                if job_config.get("next_run_at") != next_run_iso:
                    job_config["next_run_at"] = next_run_iso
                    jobs_updated = True
            except Exception as e:
                logger.warning(f"计算任务 {job_config['name']} 的 next_run_at 失败: {e}")

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

    # 如果有更新，回写数据库
    if jobs_updated:
        db = ActiveSession()
        try:
            ConfigService.save_cron_jobs(db, jobs)
            logger.info("已更新任务的 next_run_at")
        finally:
            db.close()


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
