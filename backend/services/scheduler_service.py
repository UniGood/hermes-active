"""
调度器服务 - 使用 APScheduler 管理定时任务
"""
import logging
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


def _log_run(
    job_id: str,
    job_name: str,
    status: str,
    message: str,
    duration: float = None,
    error: str = None,
    session_id: str = None,
    platform: str = None,
    extra: dict = None
) -> None:
    """统一写入 cron_run 任务日志（保证 details 完整）

    Args:
        job_id, job_name: 任务标识
        status: success / failed / skipped
        message: 简要说明
        duration: 耗时秒
        error: 错误信息
        session_id, platform: 上下文
        extra: 额外 details（如 llm_request/llm_response/context/send_result/skip_reason）
    """
    details = {
        "job_id": job_id,
        "job_name": job_name,
        "session_id": session_id,
        "platform": platform,
    }
    if duration is not None:
        details["duration"] = duration
    if error:
        details["error"] = error
    if extra:
        details.update(extra)
    MessageService.create_task_log(
        task_type="cron_run",
        status=status,
        message=message,
        error=error,
        duration=duration,
        details=details,
    )

# Hindsight 配置已移至 configs 表


def _get_weather_config() -> dict:
    """从数据库读取高德天气配置（与配置管理共享）"""
    db = ActiveSession()
    try:
        amap_key = ConfigService.get_config(db, "active_consciousness.weather.amap_key") or ""
        adcode = ConfigService.get_config(db, "active_consciousness.weather.adcode") or "370100"
        enabled = ConfigService.get_config(db, "active_consciousness.weather.enabled") == "true"
        cache_ttl = int(ConfigService.get_config(db, "active_consciousness.weather.cache_ttl") or "3600")
        temp_threshold = float(ConfigService.get_config(db, "active_consciousness.weather.temp_change_threshold") or "5.0")
        return {
            "enabled": enabled,
            "amap_key": amap_key,
            "adcode": adcode,
            "cache_ttl": cache_ttl,
            "temp_threshold": temp_threshold,
        }
    finally:
        db.close()


async def fetch_weather_for_context(forecast_days: int = 0) -> str:
    """调用 WeatherService 获取天气，返回格式化文本（用于上下文拼接）

    Args:
        forecast_days: 0=仅今天实况；1-3=今天+未来 N 天预报

    返回空字符串表示不启用、配置缺失或调用失败。
    """
    cfg = _get_weather_config()
    if not cfg["enabled"] or not cfg["amap_key"]:
        return ""
    try:
        from services.weather_service import WeatherService
        service = WeatherService()
        result = await service.get_weather(
            amap_key=cfg["amap_key"],
            adcode=cfg["adcode"],
            cache_ttl=cfg["cache_ttl"],
            temp_threshold=cfg["temp_threshold"],
            forecast_days=forecast_days,
        )
        if not result.get("success"):
            return ""

        city = result.get("city") or ""
        current = result.get("current") or {}
        forecast = result.get("forecast") or []

        lines: list[str] = []
        # 今天实况（仅当 forecast_days==0 时单独打印；>=1 时由 forecast 列表中的第一项承载）
        if forecast_days == 0 and current:
            weather = current.get("weather") or "未知"
            temp = current.get("temp") or "?"
            humidity = current.get("humidity") or ""
            winddirection = current.get("winddirection") or ""
            head = f"{city}今日天气：{weather}，白天温度{temp}℃" if city else f"今日天气：{weather}，白天温度{temp}℃"
            extras = []
            if humidity:
                extras.append(f"湿度{humidity}%")
            if winddirection:
                extras.append(f"{winddirection}风")
            if extras:
                head += "，" + "，".join(extras)
            lines.append(head)

        # 预报（仅当 forecast_days>=1 且有数据）
        if forecast_days >= 1 and forecast:
            week_map = {"1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六", "7": "周日"}
            # 头部加上城市
            header = f"{city}预报：" if city else "预报："
            lines.append(header)
            for idx, day in enumerate(forecast):
                date = day.get("date") or ""
                week = week_map.get(str(day.get("week", "")), "")
                dw = day.get("dayweather") or "?"
                nw = day.get("nightweather") or "?"
                dt = day.get("daytemp") or "?"
                nt = day.get("nighttemp") or "?"
                prefix = "今天" if idx == 0 else f"{date}" + (f" {week}" if week else "")
                lines.append(f"  {prefix}：白天{dw} {dt}℃ / 夜间{nw} {nt}℃")

        return "\n".join(lines)
    except Exception as e:
        logger.warning("定时任务获取天气失败: %s", e)
        return ""


def _get_hindsight_base_url() -> str:
    """从数据库读取 Hindsight base_url"""
    db = ActiveSession()
    try:
        url = ConfigService.get_config(db, "active_consciousness.hindsight.base_url")
        return url or "http://localhost:8888"
    finally:
        db.close()


async def call_hindsight_recall(query: str, limit: int = 10) -> list:
    """调用 Hindsight Recall API 获取相关记忆"""
    base_url = _get_hindsight_base_url()
    url = f"{base_url}/v1/default/banks/hermes/memories/recall"
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
    base_url = _get_hindsight_base_url()
    url = f"{base_url}/v1/default/banks/hermes/reflect"
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
    target_job = None  # 提前初始化，让 except 块能安全访问
    try:
        jobs = ConfigService.get_cron_jobs(db)
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
            # 指定 session_id 的情况，直接使用
            session = SessionService.get_session_by_id(db, session_id)
        else:
            # 使用 get_or_create 自动处理过期
            user_id = SessionService.get_weixin_user_id()
            if not user_id:
                logger.error(f"任务 {target_job['name']} 未找到微信用户 ID (sessions.json 中无 weixin dm session)")
                _log_run(
                    job_id=job_id,
                    job_name=target_job["name"],
                    status="failed",
                    message=f"任务 {target_job['name']} 运行失败",
                    duration=round(datetime.now().timestamp() - start_time, 2),
                    error="未找到微信用户 ID（sessions.json 中无 weixin dm session）",
                )
                return

            from services.fallback_session_service import FallbackSessionService
            session = FallbackSessionService.get_or_create_active_session(
                platform=platform,
                user_id=user_id
            )

            if session and session.get("was_auto_reset"):
                logger.info(f"Session 已自动重置（原因: {session.get('auto_reset_reason')}），新 session: {session['id']}")

        if not session:
            logger.error(f"任务 {target_job['name']} 未找到可用 session (平台: {platform})")
            _log_run(
                job_id=job_id,
                job_name=target_job["name"],
                status="failed",
                message=f"任务 {target_job['name']} 运行失败",
                duration=round(datetime.now().timestamp() - start_time, 2),
                error=f"未找到可用 session (平台: {platform})",
                platform=platform,
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
            user_prompt_final = user_prompt_clean or prompts_config.get("generation", "{session}\n{memory}\n{weather}\n当前时间：{time}")
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
            user_prompt_final = user_prompt_clean or prompts_config.get("generation", "{session}\n{memory}\n{weather}\n当前时间：{time}")
        else:
            # 兼容旧的单一 prompt 字段
            ctx_config, user_prompt_text = _parse_context_config(raw_prompt)
            prompt_text = user_prompt_text or prompts_config.get("system", "")
            user_prompt_final = prompts_config.get("generation", "{session}\n{memory}\n{weather}\n当前时间：{time}")

        # 获取上下文 - 支持独立占位符：{session} {memory} {weather} {time}
        # 获取上下文数据

        # 0. 当前时间占位符
        from datetime import timezone, timedelta
        tz_bj = timezone(timedelta(hours=8))
        now_bj = datetime.now(tz_bj)
        time_format = ctx_config.get("time_format", "%Y-%m-%d %H:%M:%S")
        if time_format:
            WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']
            weekday = WEEKDAY_NAMES[now_bj.weekday()]
            time_str = time_format.replace('{weekday}', weekday)
            for fmt, val in [('%Y', now_bj.year), ('%m', f'{now_bj.month:02d}'), ('%d', f'{now_bj.day:02d}'),
                             ('%H', f'{now_bj.hour:02d}'), ('%M', f'{now_bj.minute:02d}'), ('%S', f'{now_bj.second:02d}')]:
                time_str = time_str.replace(str(fmt), str(val))
        else:
            time_str = now_bj.strftime('%Y-%m-%d %H:%M:%S')

        # 1. Session 上下文（按平台跨 session 获取，不限制单个 session）
        context_msgs = []
        session_text = ""
        session_enabled = ctx_config.get("session_enabled", True)
        if session_enabled:
            context_limit = ctx_config.get("session_limit", 20)
            include_tool = ctx_config.get("include_tool", False)
            context_msgs = MessageService.get_recent_messages_by_platform(
                platform=platform, limit=context_limit, include_tool=include_tool
            )
            if context_msgs:
                session_text = "\n".join(
                    f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                    for m in context_msgs
                )

        # 2. Hindsight 记忆（Recall + Reflect 合并）
        memory_parts = []
        recall_enabled = ctx_config.get("hindsight_recall_enabled", False)
        recall_query = ctx_config.get("hindsight_recall_query", "")
        if recall_enabled and recall_query:
            recall_limit = ctx_config.get("hindsight_recall_limit", 10)
            recall_results = await call_hindsight_recall(recall_query, recall_limit)
            if recall_results:
                recall_text = "\n".join(f"- {r.get('text', '')}" for r in recall_results)
                memory_parts.append(f"=== 相关记忆 ===\n{recall_text}")

        reflect_enabled = ctx_config.get("hindsight_reflect_enabled", False)
        reflect_query = ctx_config.get("hindsight_reflect_query", "")
        if reflect_enabled and reflect_query:
            reflect_result = await call_hindsight_reflect(reflect_query)
            if reflect_result:
                memory_parts.append(f"=== 综合分析 ===\n{reflect_result}")

        memory_text = "\n\n".join(memory_parts)

        # 3. 天气感知
        weather_text = ""
        if ctx_config.get("weather_enabled", False):
            raw_days = ctx_config.get("weather_days", 0)
            try:
                wd = int(raw_days)
            except (ValueError, TypeError):
                wd = 0
            if wd not in (0, 2, 3, 4):
                wd = 0
            weather_text = await fetch_weather_for_context(forecast_days=wd) or ""

        # 替换所有占位符
        user_prompt = user_prompt_final
        user_prompt = user_prompt.replace("{session}", session_text or "（无对话记录）")
        user_prompt = user_prompt.replace("{memory}", memory_text or "（无相关记忆）")
        user_prompt = user_prompt.replace("{weather}", weather_text or "（无天气信息）")
        user_prompt = user_prompt.replace("{time}", time_str)

        # 冷却时间检查
        cooldown_enabled = target_job.get("cooldown_enabled", False)
        cooldown_minutes = target_job.get("cooldown_minutes", 10)
        if cooldown_enabled and context_msgs:
            from datetime import timezone, timedelta
            now = datetime.now(timezone(timedelta(hours=8)))
            # 找最后一条 user 消息的时间
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
                    logger.info(f"任务 {target_job['name']} 跳过执行: {reason}")
                    _log_run(
                        job_id=job_id,
                        job_name=target_job["name"],
                        status="skipped",
                        message=f"任务 {target_job['name']} 跳过执行",
                        duration=round(datetime.now().timestamp() - start_time, 2),
                        error=reason,
                        platform=platform,
                        session_id=sid,
                        extra={"skip_reason": reason, "cooldown_minutes": cooldown_minutes, "elapsed_minutes": round(elapsed, 1)}
                    )
                    return

        # 获取任务参数
        use_llm = target_job.get("use_llm", True)
        write_to_db = target_job.get("write_to_db", True)
        with_mark = target_job.get("with_mark", True)
        mark_format = target_job.get("mark_format", "[凯莉主动发送] {timestamp}: {content}")
        send_mark = target_job.get("send_mark", "凯莉")
        time_format = target_job.get("time_format", "%H:%M 星期{weekday}")

        generated_message = ""
        reasoning_content = None  # 推理内容（LLM 返回后提取）

        # 收集执行详情
        details = {
            "job_id": job_id,
            "job_name": target_job.get("name", ""),
            "session_id": sid,
            "platform": platform,
            "context": {
                "session_count": len(context_msgs) if session_enabled and context_msgs else 0,
                "session_messages": [{"role": m.get("role", ""), "content": m.get("content", "")[:200]} for m in (context_msgs or [])[-10:]],
                "session_text": (session_text or "")[:2000],
                "memory_text": (memory_text or "")[:2000],
                "weather_text": (weather_text or "")[:500],
                "time_str": time_str,
                "weather_enabled": ctx_config.get("weather_enabled", False),
                "weather_days": ctx_config.get("weather_days", 0),
            }
        }

        # 调用 LLM 生成消息
        if use_llm:
            import time as _time
            llm_start = _time.time()

            # 读取 max_tokens 配置（0=不限制）
            max_tokens = int(target_job.get("max_tokens", 0) or 0)

            # 判断 LLM 模式：hermes 用 call_llm，自定义用 LLMService
            if llm_config.get("mode") == "hermes":
                try:
                    import sys as _sys
                    from pathlib import Path as _Path
                    _sys.path.insert(0, str(_Path.home() / '.hermes' / 'hermes-agent'))
                    from agent.auxiliary_client import call_llm

                    llm_kwargs = dict(
                        task="title_generation",
                        messages=[
                            {"role": "system", "content": prompt_text},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                    )
                    if max_tokens > 0:
                        llm_kwargs["max_tokens"] = max_tokens
                    response = call_llm(**llm_kwargs,
                    )
                    msg = response.choices[0].message
                    generated_message = msg.content.strip()
                    reasoning_content = getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)
                    llm_duration = round(_time.time() - llm_start, 2)

                    details["llm_request"] = {
                        "mode": "hermes",
                        "model": getattr(response, 'model', 'default'),
                        "temperature": 0.7,
                        "max_tokens": max_tokens,
                        "system_prompt": prompt_text,
                        "user_prompt": user_prompt,
                    }
                    details["llm_response"] = {
                        "content": generated_message,
                        "duration": llm_duration,
                    }
                except Exception as e:
                    llm_duration = round(_time.time() - llm_start, 2)
                    details["llm_request"] = {"mode": "hermes", "system_prompt": prompt_text, "user_prompt": user_prompt}
                    details["llm_response"] = {"error": str(e), "duration": llm_duration}
                    logger.error(f"任务 {target_job['name']} LLM 调用失败: {e}")
                    _log_run(
                        job_id=job_id,
                        job_name=target_job["name"],
                        status="failed",
                        message=f"任务 {target_job['name']} LLM 调用失败",
                        duration=round(datetime.now().timestamp() - start_time, 2),
                        error=str(e),
                        platform=platform,
                        session_id=sid,
                        extra={"llm_request": details.get("llm_request"), "llm_response": details.get("llm_response"), "failure_stage": "llm_call"}
                    )
                    return
            else:
                llm_kwargs_custom = dict(
                    llm_config=llm_config,
                    prompt=user_prompt,
                    system_prompt=prompt_text,
                    temperature=0.7,
                )
                if max_tokens > 0:
                    llm_kwargs_custom["max_tokens"] = max_tokens
                llm_result = await LLMService.generate_message(**llm_kwargs_custom)
                llm_duration = round(_time.time() - llm_start, 2)

                details["llm_request"] = {
                    "mode": "custom",
                    "model": llm_config.get("model", ""),
                    "temperature": 0.7,
                    "max_tokens": max_tokens,
                    "system_prompt": prompt_text,
                    "user_prompt": user_prompt,
                }

                if not llm_result.get("success"):
                    details["llm_response"] = {"error": llm_result.get("message", ""), "duration": llm_duration}
                    logger.error(f"任务 {target_job['name']} LLM 生成失败: {llm_result.get('message')}")
                    _log_run(
                        job_id=job_id,
                        job_name=target_job["name"],
                        status="failed",
                        message=f"任务 {target_job['name']} LLM 生成失败",
                        duration=round(datetime.now().timestamp() - start_time, 2),
                        error=llm_result.get("message", "未知错误"),
                        platform=platform,
                        session_id=sid,
                        extra={"llm_request": details.get("llm_request"), "llm_response": details.get("llm_response"), "failure_stage": "llm_generate"}
                    )
                    return

                generated_message = llm_result["content"]
                reasoning_content = llm_result.get("reasoning_content")
                details["llm_response"] = {"content": generated_message, "duration": llm_duration}
        else:
            generated_message = prompt_text

        # 发送消息
        send_result = await MessageService.send_message(
            session_id=sid,
            message=generated_message,
            platform=platform,
            write_to_db=write_to_db,
            with_mark=with_mark,
            mark_format=mark_format,
            send_mark=send_mark,
            time_format=time_format,
            reasoning_content=reasoning_content,
        )

        details["send_result"] = {
            "success": send_result.get("success", False),
            "message": send_result.get("message", ""),
            "final_message": send_result.get("db_content", generated_message),
        }

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
            _log_run(
                job_id=job_id,
                job_name=target_job["name"],
                status="success",
                message=f"任务 {target_job['name']} 运行成功，session: {sid}",
                duration=duration,
                platform=platform,
                session_id=sid,
                extra=details,  # 完整 details（context/llm_request/llm_response/send_result）
            )
        else:
            logger.error(f"任务 {target_job['name']} 发送失败: {send_result.get('message')}")
            _log_run(
                job_id=job_id,
                job_name=target_job["name"],
                status="failed",
                message=f"任务 {target_job['name']} 发送失败",
                duration=duration,
                error=send_result.get("message", "未知错误"),
                platform=platform,
                session_id=sid,
                # 把完整 details（含 context/llm_request/llm_response）都塞进去
                extra={**details, "failure_stage": "send"},
            )

    except Exception as e:
        logger.exception(f"任务 {job_id} 运行异常: {e}")
        job_name = target_job.get("name", job_id) if target_job else job_id
        _log_run(
            job_id=job_id,
            job_name=job_name,
            status="failed",
            message=f"任务 {job_name} 运行异常",
            duration=0,
            error=str(e),
            extra={"failure_stage": "exception", "exception_type": type(e).__name__}
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
        "weather_enabled": False,
        "weather_days": 0,
        "time_format": "%Y-%m-%d %H:%M:%S",
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
        elif key == "weather":
            config["weather_enabled"] = value == "true"
        elif key == "weather_days":
            try:
                v = int(value)
                # 合法值: 0=今天实况，2=今+明，3=今+明+后，4=今+明+后+大后（API 实测最多返回 4 天）
                if v in (0, 2, 3, 4):
                    config["weather_days"] = v
                else:
                    config["weather_days"] = 0
            except (ValueError, TypeError):
                config["weather_days"] = 0
        elif key == "time_format":
            config["time_format"] = urllib.parse.unquote(value)

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
