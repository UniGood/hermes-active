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
            # 未指定 session_id，使用 get_or_create 自动处理过期
            user_id = SessionService.get_weixin_user_id()
            if not user_id:
                MessageService.create_task_log(
                    task_type="cron_run",
                    status="failed",
                    message=f"任务 {target_job['name']} 运行失败",
                    error="未找到微信用户 ID（sessions.json 中无 weixin dm session）",
                    duration=round(time.time() - start_time, 2)
                )
                raise HTTPException(status_code=400, detail="未找到微信用户 ID")

            from services.fallback_session_service import FallbackSessionService
            session = FallbackSessionService.get_or_create_active_session(platform, user_id)
            if session and session.get("was_auto_reset"):
                logger.info(f"Session 已自动重置（原因: {session.get('auto_reset_reason')}），新 session: {session['id']}")
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
            from services.scheduler_service import _parse_context_config
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

            from services.scheduler_service import _parse_context_config
            ctx_config, user_prompt_clean = _parse_context_config(user_prompt_raw)
            user_prompt_final = user_prompt_clean or prompts_config.get("generation", "{context}")
        else:
            # 兼容旧的单一 prompt 字段
            from services.scheduler_service import _parse_context_config
            ctx_config, user_prompt_text = _parse_context_config(raw_prompt)
            prompt_text = user_prompt_text or prompts_config.get("system", "")
            user_prompt_final = prompts_config.get("generation", "{context}")

        # 获取上下文
        context_msgs = []
        session_enabled = ctx_config.get("session_enabled", True)
        if session_enabled:
            context_limit = ctx_config.get("session_limit", 20)
            include_tool = ctx_config.get("include_tool", False)
            context_msgs = MessageService.get_session_context_raw(session_id, limit=context_limit, include_tool=include_tool)
            context_text = "\n".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in context_msgs
            )
        else:
            context_text = ""

        user_prompt = user_prompt_final.replace("{context}", context_text)

        # 冷却时间检查
        cooldown_enabled = target_job.get("cooldown_enabled", False)
        cooldown_minutes = target_job.get("cooldown_minutes", 10)
        if cooldown_enabled and context_msgs:
            from datetime import timezone, timedelta
            now = datetime.now(timezone(timedelta(hours=8)))
            last_user_time = None
            for msg in reversed(context_msgs):
                if msg.get("role") == "user" and msg.get("timestamp"):
                    ts = msg["timestamp"]
                    if isinstance(ts, (int, float)):
                        last_user_time = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
                    break
            if last_user_time:
                elapsed = (now - last_user_time).total_seconds() / 60
                if elapsed < cooldown_minutes:
                    reason = f"用户最后发言距今 {elapsed:.1f} 分钟，不足冷却时间 {cooldown_minutes} 分钟"
                    MessageService.create_task_log(
                        task_type="cron_run",
                        status="skipped",
                        message=f"任务 {target_job['name']} 跳过执行",
                        error=reason,
                        duration=round(time.time() - start_time, 2),
                        details={"skip_reason": reason, "cooldown_minutes": cooldown_minutes, "elapsed_minutes": round(elapsed, 1)}
                    )
                    return {"success": True, "message": f"跳过执行: {reason}"}

        # 获取任务参数
        use_llm = target_job.get("use_llm", True)
        write_to_db = target_job.get("write_to_db", True)
        with_mark = target_job.get("with_mark", True)
        mark_format = target_job.get("mark_format", "[凯莉主动发送] {timestamp}: {content}")
        send_mark = target_job.get("send_mark", "[凯莉主动发送]")
        time_format = target_job.get("time_format", "%H:%M 星期{weekday}")

        generated_message = ""

        # 调用 LLM 生成消息
        if use_llm:
            if llm_config.get("mode") == "hermes":
                # 使用 hermes 的 call_llm
                import sys as _sys
                from pathlib import Path as _Path
                _sys.path.insert(0, str(_Path.home() / '.hermes' / 'hermes-agent'))
                from agent.auxiliary_client import call_llm

                response = call_llm(
                    task="title_generation",
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200,
                )
                generated_message = response.choices[0].message.content.strip()
            else:
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
            mark_format=mark_format,
            send_mark=send_mark,
            time_format=time_format
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

    # 上下文数据
    context_data = {
        "session_messages": [],
        "recall_results": [],
        "reflect_result": ""
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
    if not context_summary_parts:
        context_summary_parts.append("无上下文数据")

    return {
        "system_prompt": final_system_prompt,
        "user_prompt": final_user_prompt,
        "soul_md": soul_md_content,
        "context_summary": " | ".join(context_summary_parts),
        "context_data": context_data
    }
