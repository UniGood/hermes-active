"""
自由意识服务 — 配置读写 + 调度 + 沉思逻辑 + 日志 + 积淀
"""
import json
import re
import time
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models.database import ActiveSession, active_engine
from services.config_service import ConfigService

logger = logging.getLogger("hermes.free_consciousness")

PREFIX = "free_consciousness."

_DEFAULTS = {
    "free_consciousness.enabled": "false",
    "free_consciousness.llm.mode": "",
    "free_consciousness.llm.provider": "",
    "free_consciousness.llm.api_key": "",
    "free_consciousness.llm.base_url": "",
    "free_consciousness.llm.model": "",
    "free_consciousness.llm.max_tokens": "2000",
    "free_consciousness.llm.temperature": "0.8",
    "free_consciousness.interval_minutes": "30",
    "free_consciousness.recent_rounds": "3",
    "free_consciousness.mid_rounds": "17",
    "free_consciousness.sediment_compress_interval": "10",
    "free_consciousness.include_context": "false",
    "free_consciousness.persona": "",
    "free_consciousness.store_to_hindsight": "false",
}


class FreeConsciousnessService:
    """自由意识服务"""

    _config_cache = None
    _config_cache_ts = 0
    _CONFIG_CACHE_TTL = 60  # 缓存 60 秒

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取自由意识配置（嵌套 dict）"""
        now = time.time()
        if (FreeConsciousnessService._config_cache is not None
                and now - FreeConsciousnessService._config_cache_ts < FreeConsciousnessService._CONFIG_CACHE_TTL):
            return FreeConsciousnessService._config_cache

        db = ActiveSession()
        try:
            result = {}
            for key, default in _DEFAULTS.items():
                value = ConfigService.get_config(db, key)
                result[key] = value if value is not None else default
            nested = FreeConsciousnessService._flat_to_nested(result)
            FreeConsciousnessService._config_cache = nested
            FreeConsciousnessService._config_cache_ts = now
            return nested
        finally:
            db.close()

    @staticmethod
    def update_config(config: Dict[str, Any]):
        """更新自由意识配置"""
        db = ActiveSession()
        try:
            flat = FreeConsciousnessService._nested_to_flat(config)
            for key, value in flat.items():
                if key.startswith(PREFIX):
                    ConfigService.set_config(db, key, str(value) if value is not None else "")
        finally:
            FreeConsciousnessService._config_cache = None
            FreeConsciousnessService._config_cache_ts = 0
            db.close()

    @staticmethod
    def _flat_to_nested(flat: Dict[str, str]) -> Dict[str, Any]:
        """扁平 key → 嵌套 dict"""
        result = {}
        for key, value in flat.items():
            if not key.startswith(PREFIX):
                continue
            parts = key[len(PREFIX):].split(".")
            d = result
            for part in parts[:-1]:
                if part not in d:
                    d[part] = {}
                d = d[part]
            # 类型转换
            final_key = parts[-1]
            if value.lower() in ("true", "false"):
                d[final_key] = value.lower() == "true"
            else:
                try:
                    d[final_key] = int(value)
                except (ValueError, TypeError):
                    try:
                        d[final_key] = float(value)
                    except (ValueError, TypeError):
                        d[final_key] = value
        return result

    @staticmethod
    def _nested_to_flat(config: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """嵌套 dict → 扁平 key"""
        result = {}
        for key, value in config.items():
            full_key = f"{prefix}{key}" if prefix else f"{PREFIX}{key}"
            if isinstance(value, dict):
                result.update(FreeConsciousnessService._nested_to_flat(value, full_key + "."))
            elif value is not None:
                if isinstance(value, bool):
                    result[full_key] = str(value).lower()
                else:
                    result[full_key] = str(value)
        return result

    # ── 日志读写 ──

    @staticmethod
    def get_latest_round_number() -> int:
        """获取最新轮次号"""
        with active_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COALESCE(MAX(round_number), 0) FROM free_consciousness_logs"
            ))
            return result.scalar()

    @staticmethod
    def write_log(round_number, thinking, summary=None, discovery=None,
                  thinking_tokens=None, chain_tokens=None, context_type="chain",
                  llm_details=None, parse_failed=False, error=None) -> int:
        """写入沉思日志"""
        with active_engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO free_consciousness_logs
                (round_number, thinking, summary, discovery, thinking_tokens,
                 chain_tokens, context_type, llm_details, parse_failed, error, created_at)
                VALUES (:round_number, :thinking, :summary, :discovery, :thinking_tokens,
                        :chain_tokens, :context_type, :llm_details, :parse_failed, :error, :created_at)
            """), {
                "round_number": round_number,
                "thinking": thinking,
                "summary": summary,
                "discovery": discovery,
                "thinking_tokens": thinking_tokens,
                "chain_tokens": chain_tokens,
                "context_type": context_type,
                "llm_details": llm_details,
                "parse_failed": parse_failed,
                "error": error,
                "created_at": datetime.now().isoformat()
            })
            conn.commit()
            return result.lastrowid

    @staticmethod
    def get_logs(page=1, page_size=20, round_number=None):
        """分页查询日志"""
        db = ActiveSession()
        try:
            offset = (page - 1) * page_size
            where = "WHERE 1=1"
            params = {"limit": page_size, "offset": offset}
            if round_number is not None:
                where += " AND round_number = :round_number"
                params["round_number"] = round_number

            with active_engine.connect() as conn:
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM free_consciousness_logs {where}"),
                    {k: v for k, v in params.items() if k not in ("limit", "offset")}
                )
                total = count_result.scalar()

                result = conn.execute(text(f"""
                    SELECT id, round_number, thinking, summary, discovery,
                           thinking_tokens, chain_tokens, context_type,
                           llm_details, parse_failed, error, created_at
                    FROM free_consciousness_logs {where}
                    ORDER BY round_number DESC
                    LIMIT :limit OFFSET :offset
                """), params)
                rows = result.fetchall()

            items = []
            for row in rows:
                items.append({
                    "id": row.id,
                    "round_number": row.round_number,
                    "thinking": row.thinking,
                    "summary": row.summary,
                    "discovery": row.discovery,
                    "thinking_tokens": row.thinking_tokens,
                    "chain_tokens": row.chain_tokens,
                    "context_type": row.context_type,
                    "parse_failed": row.parse_failed,
                    "error": row.error,
                    "created_at": row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}
        finally:
            db.close()

    @staticmethod
    def get_log_detail(log_id: int) -> Optional[Dict]:
        """获取单条日志详情"""
        with active_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM free_consciousness_logs WHERE id = :id
            """), {"id": log_id})
            row = result.fetchone()
        if not row:
            return None
        details = row.llm_details
        if details:
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": row.id,
            "round_number": row.round_number,
            "thinking": row.thinking,
            "summary": row.summary,
            "discovery": row.discovery,
            "thinking_tokens": row.thinking_tokens,
            "chain_tokens": row.chain_tokens,
            "context_type": row.context_type,
            "llm_details": details,
            "parse_failed": row.parse_failed,
            "error": row.error,
            "created_at": row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
        }

    @staticmethod
    def delete_log(log_id: int) -> bool:
        """删除单条日志"""
        with active_engine.connect() as conn:
            result = conn.execute(text(
                "DELETE FROM free_consciousness_logs WHERE id = :id"
            ), {"id": log_id})
            conn.commit()
            return result.rowcount > 0

    @staticmethod
    def get_status() -> Dict:
        """获取自由意识状态"""
        config = FreeConsciousnessService.get_config()
        with active_engine.connect() as conn:
            total = conn.execute(text(
                "SELECT COUNT(*) FROM free_consciousness_logs"
            )).scalar()

            latest = conn.execute(text("""
                SELECT round_number, summary, discovery, created_at
                FROM free_consciousness_logs ORDER BY round_number DESC LIMIT 1
            """)).fetchone()

            # 积淀信息
            sediment = conn.execute(text(
                "SELECT source_rounds, source_count, compressed_at FROM free_consciousness_sediment WHERE id=1"
            )).fetchone()

        # 计算思考链 token
        chain_records = load_thinking_chain(config)
        chain_text = build_thinking_chain(chain_records, config)
        chain_tokens = len(chain_text) // 2

        return {
            "enabled": config.get("enabled", False),
            "running": fc_scheduler.running if fc_scheduler else False,
            "total_rounds": total,
            "latest_round": {
                "round_number": latest.round_number,
                "summary": latest.summary,
                "discovery": latest.discovery,
                "created_at": latest.created_at if isinstance(latest.created_at, str) else (latest.created_at.isoformat() if latest.created_at else None)
            } if latest else None,
            "chain_tokens": chain_tokens,
            "interval_minutes": config.get("interval_minutes", 30),
            "sediment": {
                "source_rounds": sediment.source_rounds,
                "source_count": sediment.source_count,
                "compressed_at": sediment.compressed_at.isoformat() if sediment.compressed_at else None
            } if sediment else None,
        }


# ── 调度器 ──

fc_scheduler: Optional[AsyncIOScheduler] = None


def start_fc_scheduler():
    """启动自由意识调度器"""
    global fc_scheduler
    config = FreeConsciousnessService.get_config()
    if not config.get("enabled"):
        logger.info("自由意识未启用，跳过启动")
        return

    interval = config.get("interval_minutes", 30)
    fc_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    fc_scheduler.add_job(
        run_contemplation,
        IntervalTrigger(minutes=interval),
        id="free_consciousness",
        name="自由意识沉思",
        replace_existing=True
    )
    fc_scheduler.start()
    logger.info("自由意识调度器已启动，间隔 %d 分钟", interval)


def stop_fc_scheduler():
    """停止自由意识调度器"""
    global fc_scheduler
    if fc_scheduler and fc_scheduler.running:
        fc_scheduler.shutdown(wait=False)
        logger.info("自由意识调度器已停止")


def restart_fc_scheduler(new_interval: int = None):
    """重启调度器"""
    global fc_scheduler
    stop_fc_scheduler()
    fc_scheduler = None
    if new_interval is None:
        config = FreeConsciousnessService.get_config()
        new_interval = config.get("interval_minutes", 30)
    fc_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    fc_scheduler.add_job(
        run_contemplation,
        IntervalTrigger(minutes=new_interval),
        id="free_consciousness",
        name="自由意识沉思",
        replace_existing=True
    )
    fc_scheduler.start()
    logger.info("自由意识调度器已重启，间隔 %d 分钟", new_interval)


# ── 意识积淀 ──

def load_sediment() -> Optional[Dict]:
    """读取意识积淀"""
    with active_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT content, source_rounds, source_count, compressed_at "
            "FROM free_consciousness_sediment WHERE id=1"
        ))
        row = result.fetchone()
    if row:
        return {
            "content": row.content,
            "source_rounds": row.source_rounds,
            "source_count": row.source_count,
            "compressed_at": row.compressed_at.isoformat() if row.compressed_at else None
        }
    return None


async def compress_sediment(records_to_compress: list, config: dict):
    """把远期记录压缩成意识积淀"""
    parts = []
    for r in records_to_compress:
        if r.summary:
            parts.append(f"第{r.round_number}轮摘要：{r.summary}")
        if r.discovery:
            parts.append(f"第{r.round_number}轮发现：{r.discovery}")

    source_text = "\n".join(parts)
    first_round = records_to_compress[0].round_number
    last_round = records_to_compress[-1].round_number

    prompt = f"""以下是凯莉过去 {len(records_to_compress)} 轮自由沉思的摘要和发现。
请将它们提炼为一段连贯的"意识积淀"文本（不超过 300 字），保留最重要的主题、
洞察和思维脉络。这不是摘要列表，而是一段可读的、连贯的叙述。

{source_text}

请直接输出提炼后的意识积淀文本（不要加标题或前缀）："""

    try:
        llm_config = get_effective_llm_config(config)
        response = await call_llm([{"role": "user", "content": prompt}], llm_config)
        content = response.get("content", "").strip()
        if not content:
            logger.warning("意识积淀压缩返回空，跳过更新")
            return

        with active_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO free_consciousness_sediment (id, content, source_rounds, source_count, compressed_at)
                VALUES (1, :content, :source_rounds, :source_count, :compressed_at)
                ON CONFLICT(id) DO UPDATE SET
                    content=excluded.content,
                    source_rounds=excluded.source_rounds,
                    source_count=excluded.source_count,
                    compressed_at=excluded.compressed_at
            """), {
                "content": content,
                "source_rounds": f"{first_round}-{last_round}",
                "source_count": len(records_to_compress),
                "compressed_at": datetime.now().isoformat()
            })
            conn.commit()

        logger.info("意识积淀已压缩：第 %d-%d 轮 → %d 字",
                     first_round, last_round, len(content))
    except Exception as e:
        logger.error("意识积淀压缩失败: %s", e)


def maybe_compress_sediment(config: dict):
    """检查是否需要触发积淀压缩"""
    compress_interval = config.get("sediment_compress_interval", 10)
    recent = config.get("recent_rounds", 3)
    total = FreeConsciousnessService.get_latest_round_number()
    distant_count = total - recent

    if distant_count > 0 and distant_count % compress_interval == 0:
        with active_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT round_number, summary, discovery
                FROM free_consciousness_logs
                WHERE error IS NULL AND round_number <= :max_round
                ORDER BY round_number ASC
            """), {"max_round": total - recent})
            records = result.fetchall()

        if records:
            asyncio.create_task(compress_sediment(records, config))


# ── LLM 调用 ──

def get_effective_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取有效的 LLM 配置（专用配置为空时回退到通用 llm）"""
    fallback = config.get("llm", {})
    return fallback  # 自由意识只有一套 LLM


async def call_llm(messages: list, llm_config: dict) -> dict:
    """调用 LLM，返回 {content, reasoning_content, details}"""
    from services.llm_service import LLMService
    result = await LLMService.generate_message(
        messages=messages,
        llm_config=llm_config,
        max_tokens=llm_config.get("max_tokens"),
        temperature=llm_config.get("temperature", 0.8)
    )
    return result


# ── 思考链 ──

def load_thinking_chain(config: dict) -> list:
    """读取最近的沉思记录，按时间正序返回"""
    recent = config.get("recent_rounds", 3)
    mid = config.get("mid_rounds", 17)
    limit = recent + mid
    with active_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, round_number, thinking, summary, discovery, created_at
            FROM free_consciousness_logs
            WHERE error IS NULL
            ORDER BY round_number DESC
            LIMIT :limit
        """), {"limit": limit})
        rows = result.fetchall()
    return list(reversed(rows))


def build_thinking_chain(records: list, config: dict) -> str:
    """按四层记忆模型拼接思考链"""
    recent = config.get("recent_rounds", 3)
    mid = config.get("mid_rounds", 17)

    if not records:
        sediment = load_sediment()
        if sediment:
            return f"【意识积淀】\n{sediment['content']}\n\n（以上是你过去的思考积淀。请在此基础上继续。）"
        return "（这是你的第一次沉思，没有任何历史。请自由地开始你的思考。）"

    sections = []
    total = len(records)

    # 1. 意识积淀
    sediment = load_sediment()
    if sediment:
        sections.append(f"【意识积淀·覆盖第 {sediment['source_rounds']} 轮】\n{sediment['content']}")

    # 2. 近期 + 中期
    for i, record in enumerate(records):
        distance = total - 1 - i
        round_num = record.round_number

        if distance < recent:
            sections.append(f"【第 {round_num} 轮】\n{record.thinking}")
        elif distance < mid:
            summary = record.summary or record.thinking[:100] + "..."
            sections.append(f"【第 {round_num} 轮·摘要】{summary}")
        else:
            if record.discovery:
                sections.append(f"【第 {round_num} 轮·发现】{record.discovery}")

    return "\n\n".join(sections)


# ── Prompt 构建 ──

def build_contemplation_prompt(chain_text: str, config: dict) -> list:
    """构建沉思的 messages 列表"""
    persona = config.get("persona", "")
    persona_section = f"\n你的思考风格：{persona}" if persona else ""

    system_content = f"""你正在进行自由沉思。这是你的内在思考空间，你可以在这里探索任何想法、
回忆、感受、创意、问题。没有任务压力，没有用户等待，只有你自己安静地思考。{persona_section}

以下是你之前的思考记录：
{chain_text}"""

    user_content = """请从上一轮思考的地方继续，自由地想任何你想想的事情。
如果你有新的发现或洞察，请特别标注。

请严格按以下 JSON 格式输出（不要输出其他内容）：
{{
  "thinking": "你的完整思考过程...",
  "summary": "本轮思考的一句话摘要（30字以内）",
  "discovery": "本轮关键发现（如果没有新发现则为 null）"
}}"""

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]


# ── LLM 输出解析 ──

def parse_llm_output(response_text: str) -> dict:
    """解析 LLM 输出的 JSON"""
    text = response_text.strip()

    # 尝试提取 JSON（可能被 ```json ... ``` 包裹）
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    try:
        data = json.loads(text)
        thinking = (data.get("thinking") or "").strip()
        summary = (data.get("summary") or "").strip()
        discovery = data.get("discovery")

        if not thinking:
            thinking = response_text.strip()

        return {
            "thinking": thinking,
            "summary": summary or thinking[:100] + "...",
            "discovery": discovery,
            "parse_failed": False
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "thinking": response_text.strip(),
            "summary": response_text.strip()[:100] + "...",
            "discovery": None,
            "parse_failed": True
        }


# ── 实时上下文 ──

async def collect_realtime_context() -> str:
    """收集实时上下文（时间 + 情绪状态）"""
    parts = []
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    parts.append(f"当前时间：{now}")

    try:
        from services.active_consciousness_service import get_emotion_state
        emotion = get_emotion_state()
        parts.append(f"当前情绪：{emotion.dominant}（效价 {emotion.valence:.2f}，唤醒 {emotion.arousal:.2f}）")
    except Exception:
        pass

    return "\n".join(parts)


# ── 沉思主函数 ──

async def run_contemplation():
    """执行一次沉思"""
    start_time = time.time()
    config = FreeConsciousnessService.get_config()

    if not config.get("enabled"):
        return

    round_number = FreeConsciousnessService.get_latest_round_number() + 1
    all_details = {}

    try:
        logger.info("=== 自由意识沉思第 %d 轮开始 ===", round_number)

        # 1. 读取思考链
        chain_records = load_thinking_chain(config)
        chain_text = build_thinking_chain(chain_records, config)
        all_details["chain_rounds"] = len(chain_records)
        all_details["chain_preview"] = chain_text[:500]

        # 2. 可选：注入实时上下文
        context_type = "chain"
        if config.get("include_context"):
            context_text = await collect_realtime_context()
            chain_text = chain_text + "\n\n---\n当前世界的状态：\n" + context_text
            context_type = "chain+context"

        # 3. 构建 prompt
        messages = build_contemplation_prompt(chain_text, config)
        all_details["prompt_sent"] = messages
        all_details["chain_tokens"] = sum(len(m["content"]) // 2 for m in messages)

        # 4. 请求 LLM
        llm_config = get_effective_llm_config(config)
        response = await call_llm(messages, llm_config)
        all_details["llm_details"] = response.get("details", {})

        response_text = response.get("content", "")
        reasoning_content = response.get("reasoning_content")
        all_details["response_raw"] = response_text
        if reasoning_content:
            all_details["reasoning_content"] = reasoning_content

        # 5. 解析输出
        parsed = parse_llm_output(response_text)
        all_details["parse_failed"] = parsed["parse_failed"]

        # 6. 写入日志
        duration_ms = round((time.time() - start_time) * 1000)
        FreeConsciousnessService.write_log(
            round_number=round_number,
            thinking=parsed["thinking"],
            summary=parsed["summary"],
            discovery=parsed["discovery"],
            thinking_tokens=len(parsed["thinking"]) // 2,
            chain_tokens=all_details["chain_tokens"],
            context_type=context_type,
            llm_details=json.dumps(all_details, ensure_ascii=False),
            parse_failed=parsed["parse_failed"]
        )

        # 7. 可选：发现存入 Hindsight
        if config.get("store_to_hindsight") and parsed["discovery"]:
            try:
                from services.active_consciousness_service import retain_thought_to_hindsight
                await retain_thought_to_hindsight(
                    parsed["discovery"], None, "free_consciousness", 0
                )
            except Exception as e:
                logger.warning("存入 Hindsight 失败: %s", e)

        # 8. 检查积淀压缩
        maybe_compress_sediment(config)

        logger.info("沉思第 %d 轮完成，耗时 %dms", round_number, duration_ms)

    except Exception as e:
        logger.error("沉思第 %d 轮异常: %s", round_number, e)
        duration_ms = round((time.time() - start_time) * 1000)
        FreeConsciousnessService.write_log(
            round_number=round_number,
            thinking=f"[错误] {str(e)}",
            error=str(e),
            llm_details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )


# ── 测试 LLM 连通性 ──

async def test_llm_connection(config: dict) -> dict:
    """测试 LLM 连通性"""
    import time as _time
    start = _time.time()
    try:
        llm_config = get_effective_llm_config(config)
        if not llm_config.get("api_key") and not llm_config.get("mode"):
            return {"success": False, "message": "未配置 LLM API Key"}
        response = await call_llm([{"role": "user", "content": "Hi"}], llm_config)
        duration = round(_time.time() - start, 2)
        content = response.get("content", "")
        if content:
            return {"success": True, "message": f"连通成功 (耗时 {duration}s)", "duration": duration}
        return {"success": False, "message": "LLM 返回空"}
    except Exception as e:
        duration = round(_time.time() - start, 2)
        return {"success": False, "message": f"连通失败: {str(e)}", "duration": duration}
