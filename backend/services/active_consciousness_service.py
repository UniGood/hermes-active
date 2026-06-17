"""
主动意识服务 — 配置读写 + 状态查询 + 日志查询 + 心跳调度器
"""
import json
import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from hindsight_client import Hindsight

from models.database import ActiveSession, state_engine, active_engine
from models.active_consciousness import (
    ActiveConsciousnessConfig, ActiveConsciousnessStatus,
    LongingState, ChatHeat, EmotionalIntensity,
    ThoughtLog, HeartbeatLog,
    EmotionState, ThoughtType, DelayedThought
)

logger = logging.getLogger("hermes.active_consciousness")

# 全局心跳调度器实例
heartbeat_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 全局 Hindsight 客户端实例
_hindsight_client: Optional[Hindsight] = None


def get_hindsight_client(base_url: str = "http://localhost:8888", timeout: float = 30.0) -> Hindsight:
    """获取 Hindsight 客户端实例（懒加载，base_url 或 timeout 变化时重建）"""
    global _hindsight_client
    if _hindsight_client is None:
        _hindsight_client = Hindsight(base_url=base_url, timeout=timeout)
    return _hindsight_client


async def close_hindsight_client() -> None:
    """关闭全局 Hindsight 客户端，释放底层 aiohttp 连接"""
    global _hindsight_client
    if _hindsight_client is not None:
        try:
            await _hindsight_client.aclose()
        except Exception:
            pass
        _hindsight_client = None

# 配置 key 前缀
PREFIX = "active_consciousness."

# 默认配置（扁平 key → 默认值）
_DEFAULTS = {
    "active_consciousness.enabled": "false",
    "active_consciousness.llm.mode": "hermes",
    "active_consciousness.llm.provider": "openai",
    "active_consciousness.llm.model": "deepseek-chat",
    "active_consciousness.llm.api_key": "",
    "active_consciousness.llm.base_url": "",
    "active_consciousness.active.enabled": "true",
    "active_consciousness.active.heartbeat_interval": "600",
    "active_consciousness.active.send_tag": "[凯莉主动发送]",
    "active_consciousness.active.time_format": "%H:%M",
    "active_consciousness.active.no_send_after_user_msg_minutes": "10",
    "active_consciousness.active.no_send_while_heat_above": "0.5",
    "active_consciousness.active.no_send_while_vibe_below": "0.3",
    "active_consciousness.active.cooldown_minutes": "30",
    "active_consciousness.session.sources": '["weixin"]',
    "active_consciousness.session.time_range_hours": "24",
    "active_consciousness.session.max_messages_per_session": "15",
    "active_consciousness.session.filter_tool_messages": "true",
    "active_consciousness.decision.send_threshold": "0.6",
    "active_consciousness.decision.delay_threshold": "0.3",
    "active_consciousness.decision.memory_threshold": "0.1",
    "active_consciousness.decision.max_per_hour": "2",
    "active_consciousness.decision.max_per_day": "5",
    "active_consciousness.decision.longing_gap_threshold": "3",
    "active_consciousness.hindsight.enabled": "true",
    "active_consciousness.hindsight.base_url": "http://localhost:8888",
    "active_consciousness.hindsight.bank_id": "hermes",
    "active_consciousness.hindsight.recall_limit": "5",
    "active_consciousness.hindsight.reflect_enabled": "true",
    "active_consciousness.hindsight.timeout": "30",
    "active_consciousness.notify.platform": "weixin",
    "active_consciousness.notify.chat_id": "",

    # 情绪演化
    "active_consciousness.emotion.decay_rate": "0.02",
    "active_consciousness.emotion.social_need_growth": "0.01",
    "active_consciousness.emotion.valence_regression": "0.1",
    "active_consciousness.emotion.weight_evolved": "0.4",
    "active_consciousness.emotion.weight_llm": "0.6",

    # 时间窗口
    "active_consciousness.time.enabled": "true",
    "active_consciousness.time.deep_night_start": "23.5",
    "active_consciousness.time.deep_night_end": "7",
    "active_consciousness.time.deep_night_fitness": "0.3",

    # 延迟发送
    "active_consciousness.delay.enabled": "true",
    "active_consciousness.delay.max_retry": "3",
    "active_consciousness.delay.retry_interval_minutes": "30",
    "active_consciousness.delay.max_queue_size": "10",

    # 念头存储
    "active_consciousness.thought.retain_enabled": "false",
    "active_consciousness.thought.retain_threshold": "0.5",
}

# 想念等级
LONGING_LEVELS = [
    (0.0, 0, "calm"),
    (0.1, 1, "longing"),
    (0.3, 2, "missing"),
    (0.5, 3, "yearning"),
    (0.7, 4, "anxious"),
]

# 聊天热度等级
HEAT_LEVELS = [
    (0.0, "cold"),
    (0.5, "warm"),
    (1.0, "hot"),
    (3.0, "fire"),
]

def _parse_timestamp(ts_str):
    """解析时间戳：支持 Unix 时间戳（float）和 ISO 格式"""
    if not ts_str:
        return None
    try:
        s = str(ts_str)
        if s.replace('.', '').replace('-', '').isdigit() or (s.count('.') == 1 and s.split('.')[0].isdigit()):
            return datetime.fromtimestamp(float(s))
        return datetime.fromisoformat(s)
    except Exception:
        return None


# 英文标签 → 中文
LABEL_CN = {
    # 想念等级
    "calm": "平静",
    "longing": "想念",
    "missing": "思念",
    "yearning": "渴望",
    "anxious": "焦虑",
    # 聊天热度
    "cold": "冷清",
    "warm": "温暖",
    "hot": "火热",
    "fire": "沸腾",
    # 情绪 dominant
    "happy": "开心",
    "content": "满足",
    "bored": "无聊",
    "concerned": "担忧",
}


class ActiveConsciousnessService:
    """主动意识服务"""

    # ============ 配置 ============

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取主动意识配置"""
        db = ActiveSession()
        try:
            result = {}
            for key, default in _DEFAULTS.items():
                value = ConfigService.get_config(db, key)
                result[key] = value if value is not None else default
            return ActiveConsciousnessService._flat_to_nested(result)
        finally:
            db.close()

    @staticmethod
    def update_config(config: Dict[str, Any]):
        """更新主动意识配置"""
        db = ActiveSession()
        try:
            flat = ActiveConsciousnessService._nested_to_flat(config)
            for key, value in flat.items():
                if key.startswith(PREFIX):
                    ConfigService.set_config(db, key, str(value))
        finally:
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
            if value in ("true", "false"):
                d[final_key] = value == "true"
            elif value.startswith("[") or value.startswith("{"):
                try:
                    d[final_key] = json.loads(value)
                except json.JSONDecodeError:
                    d[final_key] = value
            else:
                try:
                    d[final_key] = int(value)
                except ValueError:
                    try:
                        d[final_key] = float(value)
                    except ValueError:
                        d[final_key] = value
        return result

    @staticmethod
    def _nested_to_flat(nested: Dict[str, Any], prefix: str = PREFIX) -> Dict[str, str]:
        """嵌套 dict → 扁平 key"""
        result = {}
        for key, value in nested.items():
            full_key = f"{prefix}{key}"
            if isinstance(value, dict):
                result.update(ActiveConsciousnessService._nested_to_flat(value, full_key + "."))
            elif isinstance(value, list):
                result[full_key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                result[full_key] = str(value).lower()
            else:
                result[full_key] = str(value)
        return result

    # ============ 状态 ============

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """获取主动意识状态"""
        db = ActiveSession()
        try:
            config = ActiveConsciousnessService.get_config()
            now = datetime.now()

            # 查询想念分数
            longing_score = 0.0
            longing_level = 0
            longing_label = "calm"
            last_user_msg_at = None
            last_self_msg_at = None
            silence_minutes = 0.0

            try:
                with state_engine.connect() as conn:
                    # 最近用户消息
                    row = conn.execute(text(
                        "SELECT MAX(timestamp) FROM messages WHERE role='user' AND session_id IN "
                        "(SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row and row[0]:
                        last_user_msg_at = str(row[0])
                        last_user_dt = _parse_timestamp(row[0]) or now
                        gap_minutes = (now - last_user_dt).total_seconds() / 60
                        longing_score = min(gap_minutes / 300, 1.0)  # 5小时=1.0
                        silence_minutes = gap_minutes

                    # 最近主动消息
                    row = conn.execute(text(
                        "SELECT MAX(timestamp) FROM messages WHERE role='assistant' "
                        "AND content LIKE '凯莉%' AND session_id IN "
                        "(SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row and row[0]:
                        last_self_msg_at = str(row[0])
            except Exception as e:
                logger.warning("查询想念分数失败: %s", e)

            # 计算想念等级
            for threshold, level, label in reversed(LONGING_LEVELS):
                if longing_score >= threshold:
                    longing_level = level
                    longing_label = label
                    break

            # 查询聊天热度
            chat_heat = 0.0
            chat_label = "cold"
            recent_count = 0
            recent_hours = 0.0
            recent_user_msg_at = None

            try:
                with state_engine.connect() as conn:
                    row = conn.execute(text(
                        "SELECT COUNT(*), MAX(timestamp) FROM messages "
                        "WHERE role='user' AND CAST(timestamp AS REAL) > CAST(strftime('%s', 'now', '-1 hour') AS REAL) "
                        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row:
                        recent_count = row[0] or 0
                        if row[1]:
                            recent_user_msg_at = str(row[1])
                        recent_hours = 1.0
                        chat_heat = recent_count / max(recent_hours, 0.1)
            except Exception as e:
                logger.warning("查询聊天热度失败: %s", e)

            # 计算热度等级
            for threshold, label in reversed(HEAT_LEVELS):
                if chat_heat >= threshold:
                    chat_label = label
                    break

            # 情绪值（从 configs 读取，由 LLM 更新）
            emotional_intensity = 0.0
            try:
                val = ConfigService.get_config(db, "active_consciousness.current.emotional_intensity")
                if val:
                    emotional_intensity = float(val)
            except Exception:
                pass

            # 今日发送数
            today_sent_count = 0
            hour_sent_count = 0
            try:
                with state_engine.connect() as conn:
                    row = conn.execute(text(
                        "SELECT COUNT(*) FROM messages "
                        "WHERE role='assistant' AND content LIKE '凯莉%' "
                        "AND CAST(timestamp AS REAL) > CAST(strftime('%s', 'now', 'start of day') AS REAL) "
                        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row:
                        today_sent_count = row[0] or 0

                    row = conn.execute(text(
                        "SELECT COUNT(*) FROM messages "
                        "WHERE role='assistant' AND content LIKE '凯莉%' "
                        "AND CAST(timestamp AS REAL) > CAST(strftime('%s', 'now', '-1 hour') AS REAL) "
                        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row:
                        hour_sent_count = row[0] or 0
            except Exception as e:
                logger.warning("查询发送数失败: %s", e)

            # 查询今日心跳统计
            heartbeat_count = 0
            last_heartbeat_at = None
            try:
                with active_engine.connect() as conn:
                    row = conn.execute(text(
                        "SELECT COUNT(*), MAX(created_at) FROM active_heartbeat_logs "
                        "WHERE created_at > datetime('now', 'start of day')"
                    )).fetchone()
                    if row:
                        heartbeat_count = row[0] or 0
                        if row[1]:
                            last_heartbeat_at = str(row[1])
            except Exception as e:
                logger.warning("查询心跳统计失败: %s", e)

            return {
                "enabled": config.get("enabled", False),
                "heartbeat_count": heartbeat_count,
                "last_heartbeat_at": last_heartbeat_at,
                "longing": {
                    "score": round(longing_score, 3),
                    "level": longing_level,
                    "label": LABEL_CN.get(longing_label, longing_label),
                    "last_user_msg_at": last_user_msg_at,
                    "last_self_msg_at": last_self_msg_at,
                    "silence_minutes": round(silence_minutes, 1),
                },
                "chat_heat": {
                    "heat": round(chat_heat, 2),
                    "label": LABEL_CN.get(chat_label, chat_label),
                    "recent_count": recent_count,
                    "recent_hours": recent_hours,
                    "recent_user_msg_at": recent_user_msg_at,
                },
                "emotional_intensity": {
                    "intensity": round(emotional_intensity, 3),
                    "label": ActiveConsciousnessService._intensity_label(emotional_intensity),
                },
                "today_sent_count": today_sent_count,
                "hour_sent_count": hour_sent_count,
                "last_sent_at": last_self_msg_at,
            }
        finally:
            db.close()

    @staticmethod
    def _intensity_label(value: float) -> str:
        """情绪强度标签"""
        if value < 0.3:
            return "工作"
        elif value < 0.5:
            return "日常"
        elif value < 0.7:
            return "八卦"
        elif value < 0.9:
            return "情感"
        else:
            return "深度情感"

    # ============ 日志 ============

    @staticmethod
    def get_thoughts(page: int = 1, page_size: int = 20, date: Optional[str] = None) -> Dict[str, Any]:
        """获取念头日志，支持日期过滤（格式 YYYY-MM-DD）"""
        db = ActiveSession()
        try:
            # 检查表是否存在
            with active_engine.connect() as conn:
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='active_thought_logs'"
                )).fetchall()
                if not tables:
                    return {"total": 0, "items": []}

                where_clause = ""
                params = {"limit": page_size, "offset": (page - 1) * page_size}
                if date:
                    where_clause = "WHERE date(created_at) = :date"
                    params["date"] = date

                total = conn.execute(text(f"SELECT COUNT(*) FROM active_thought_logs {where_clause}"), params).scalar() or 0
                rows = conn.execute(text(
                    f"SELECT * FROM active_thought_logs {where_clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ), params).fetchall()

                items = []
                for row in rows:
                    d = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                    items.append(d)

                return {"total": total, "items": items}
        except Exception as e:
            logger.error("查询念头日志失败: %s", e)
            return {"total": 0, "items": [], "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def get_heartbeats(page: int = 1, page_size: int = 20, date: Optional[str] = None) -> Dict[str, Any]:
        """获取心跳日志，支持日期过滤（格式 YYYY-MM-DD）"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='active_heartbeat_logs'"
                )).fetchall()
                if not tables:
                    return {"total": 0, "items": []}

                where_clause = ""
                params = {"limit": page_size, "offset": (page - 1) * page_size}
                if date:
                    where_clause = "WHERE date(created_at) = :date"
                    params["date"] = date

                total = conn.execute(text(f"SELECT COUNT(*) FROM active_heartbeat_logs {where_clause}"), params).scalar() or 0
                rows = conn.execute(text(
                    f"SELECT * FROM active_heartbeat_logs {where_clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ), params).fetchall()

                items = []
                for row in rows:
                    d = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                    items.append(d)

                return {"total": total, "items": items}
        except Exception as e:
            logger.error("查询心跳日志失败: %s", e)
            return {"total": 0, "items": [], "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def delete_thought(thought_id: int) -> bool:
        """删除念头"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                conn.execute(text("DELETE FROM active_thought_logs WHERE id = :id"), {"id": thought_id})
                conn.commit()
            return True
        except Exception as e:
            logger.error("删除念头失败: %s", e)
            return False
        finally:
            db.close()

    @staticmethod
    def retry_thought(thought_id: int) -> Dict[str, Any]:
        """重试发送念头"""
        # TODO: 实现重试逻辑
        return {"success": False, "error": "重试功能待实现"}

    @staticmethod
    def delete_heartbeat(heartbeat_id: int) -> bool:
        """删除心跳日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                conn.execute(text("DELETE FROM active_heartbeat_logs WHERE id = :id"), {"id": heartbeat_id})
                conn.commit()
            return True
        except Exception as e:
            logger.error("删除心跳日志失败: %s", e)
            return False
        finally:
            db.close()

    # ============ 心跳调度器 ============

    @staticmethod
    def write_thought_log(
        heartbeat_id: Optional[int],
        thought_type: str,
        content: str,
        intensity: float = 0.5,
        decision: str = "pending",
        reason: Optional[str] = None,
        score: Optional[float] = None,
        recall_count: Optional[int] = None,
        recall_source: Optional[str] = None,
        chat_heat: Optional[float] = None,
        emotional_intensity: Optional[float] = None,
        details: Optional[str] = None
    ) -> int:
        """记录念头日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO active_thought_logs
                    (heartbeat_id, type, content, intensity, decision, reason, score,
                     recall_count, recall_source, chat_heat, emotional_intensity, details, created_at)
                    VALUES (:heartbeat_id, :type, :content, :intensity, :decision, :reason, :score,
                            :recall_count, :recall_source, :chat_heat, :emotional_intensity, :details, :created_at)
                """), {
                    "heartbeat_id": heartbeat_id,
                    "type": thought_type,
                    "content": content,
                    "intensity": intensity,
                    "decision": decision,
                    "reason": reason,
                    "score": score,
                    "recall_count": recall_count,
                    "recall_source": recall_source,
                    "chat_heat": chat_heat,
                    "emotional_intensity": emotional_intensity,
                    "details": details,
                    "created_at": datetime.now().isoformat()
                })
                conn.commit()
                return result.lastrowid
        except Exception as e:
            logger.error("记录念头日志失败: %s", e)
            return 0
        finally:
            db.close()

    @staticmethod
    def write_heartbeat_log(
        started_at: str,
        duration_ms: int,
        longing_before: Optional[float] = None,
        longing_after: Optional[float] = None,
        chat_heat: Optional[float] = None,
        emotional_intensity: Optional[float] = None,
        recall_count: Optional[int] = None,
        reflect_count: Optional[int] = None,
        thoughts_generated: Optional[int] = None,
        message_sent: bool = False,
        error: Optional[str] = None,
        details: Optional[str] = None
    ) -> int:
        """记录心跳日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO active_heartbeat_logs
                    (started_at, duration_ms, longing_before, longing_after, chat_heat,
                     emotional_intensity, recall_count, reflect_count, thoughts_generated,
                     message_sent, error, details, created_at)
                    VALUES (:started_at, :duration_ms, :longing_before, :longing_after, :chat_heat,
                            :emotional_intensity, :recall_count, :reflect_count, :thoughts_generated,
                            :message_sent, :error, :details, :created_at)
                """), {
                    "started_at": started_at,
                    "duration_ms": duration_ms,
                    "longing_before": longing_before,
                    "longing_after": longing_after,
                    "chat_heat": chat_heat,
                    "emotional_intensity": emotional_intensity,
                    "recall_count": recall_count,
                    "reflect_count": reflect_count,
                    "thoughts_generated": thoughts_generated,
                    "message_sent": message_sent,
                    "error": error,
                    "details": details,
                    "created_at": datetime.now().isoformat()
                })
                conn.commit()
                return result.lastrowid
        except Exception as e:
            logger.error("记录心跳日志失败: %s", e)
            return 0
        finally:
            db.close()


# 导入 ConfigService（避免循环导入）
from services.config_service import ConfigService


# ============ 心跳调度器核心函数 ============

async def extract_session_context(session_config: Dict[str, Any]) -> str:
    """Step 1: 提取近期 session 上下文"""
    try:
        from services.message_service import MessageService
        from services.session_service import SessionService
        from services.fallback_session_service import FallbackSessionService

        sources = session_config.get("sources", ["weixin"])
        time_range_hours = session_config.get("time_range_hours", 24)
        max_messages = session_config.get("max_messages_per_session", 15)
        filter_tool = session_config.get("filter_tool_messages", True)

        context_parts = []

        for platform in sources:
            user_id = SessionService.get_weixin_user_id() if platform == "weixin" else None
            if not user_id:
                continue

            session = FallbackSessionService.get_or_create_active_session(platform, user_id)
            if not session:
                continue

            session_id = session["id"] if isinstance(session, dict) else session.id
            messages = MessageService.get_session_context_raw(
                session_id, limit=max_messages, include_tool=not filter_tool
            )

            if messages:
                msg_text = "\n".join(
                    f"{m.get('role', 'unknown')}: {(m.get('content') or '')[:200]}"
                    for m in messages[-10:]  # 最近10条
                )
                context_parts.append(f"[{platform}] 最近对话:\n{msg_text}")

        return "\n\n".join(context_parts) if context_parts else ""
    except Exception as e:
        logger.warning("提取 session 上下文失败: %s", e)
        return ""


async def call_hindsight_recall(
    query: str,
    limit: int = 5,
    bank_id: str = "hermes",
    base_url: str = "http://localhost:8888",
    timeout: float = 30.0,
) -> List[Dict]:
    """调用 Hindsight Recall API（使用 Python SDK）"""
    try:
        client = get_hindsight_client(base_url=base_url, timeout=timeout)
        response = await client.arecall(bank_id=bank_id, query=query, max_tokens=4096)
        return [{"text": r.text, "type": r.type, "id": r.id} for r in response.results[:limit]]
    except Exception as e:
        logger.warning("Hindsight Recall 失败: %s", e)
        return []


async def call_hindsight_reflect(
    query: str,
    bank_id: str = "hermes",
    base_url: str = "http://localhost:8888",
    timeout: float = 30.0,
) -> str:
    """调用 Hindsight Reflect API（使用 Python SDK）"""
    try:
        client = get_hindsight_client(base_url=base_url, timeout=timeout)
        response = await client.areflect(bank_id=bank_id, query=query, budget="low")
        return response.text
    except Exception as e:
        logger.warning("Hindsight Reflect 失败: %s", e)
        return ""


async def generate_thought(config: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
    """生成念头（三步流程）"""
    llm_config = config.get("llm", {})
    session_config = config.get("session", {})
    hindsight_config = config.get("hindsight", {})
    recall_count = 0
    reflect_count = 0

    # Step 1: 近期 session 提取
    session_context = await extract_session_context(session_config)

    # Step 2: Hindsight Recall/Reflect
    hindsight_context = ""
    if hindsight_config.get("enabled", True):
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        hs_timeout = float(hindsight_config.get("timeout", 30))

        recall_results = await call_hindsight_recall(
            "最近的对话和情绪",
            limit=hindsight_config.get("recall_limit", 5),
            bank_id=bank_id,
            base_url=base_url,
            timeout=hs_timeout,
        )
        if recall_results:
            recall_count = len(recall_results)
            hindsight_context += "相关记忆:\n" + "\n".join(
                f"- {r.get('text', '')}" for r in recall_results
            )

        if hindsight_config.get("reflect_enabled", True):
            reflect_result = await call_hindsight_reflect(
                "总结最近的对话和情绪变化",
                bank_id=bank_id,
                base_url=base_url,
                timeout=hs_timeout,
            )
            if reflect_result:
                reflect_count = 1
                hindsight_context += "\n\n综合分析:\n" + reflect_result

    # Step 3: 念头生成（LLM）
    now = datetime.now()
    prompt = f"""你是凯莉，请基于当前状态产生一个自然的念头。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 想念分数：{status['longing'].get('score', 0)}（等级：{status['longing'].get('label', 'calm')}）
- 聊天热度：{status['chat_heat'].get('heat', 0)}（标签：{status['chat_heat'].get('label', 'cold')}）
- 情绪值：{status['emotional_intensity'].get('intensity', 0)}（{status['emotional_intensity'].get('label', '工作')}）

{session_context}

{hindsight_context}

请用第一人称产生一个自然的念头（1-2句话）。"""

    thought = None
    llm_duration = 0
    error_msg = None
    llm_model = llm_config.get("model", "unknown")

    # LLM 调用详情
    llm_details = {
        "model": llm_model,
        "mode": llm_config.get("mode", "hermes"),
        "temperature": 0.9,
        "max_tokens": 200,
        "prompt_preview": prompt[:500],
        "response": None,
        "error": None,
    }

    try:
        start_time = time.time()

        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            thought = response.choices[0].message.content
            llm_details["response"] = thought
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )
            if result.get("success"):
                thought = result["content"]
                llm_details["response"] = thought
                llm_details["model"] = result.get("model", llm_model)
            else:
                error_msg = result.get("message", "LLM 调用失败")
                llm_details["error"] = error_msg

        llm_duration = round((time.time() - start_time) * 1000)
        llm_details["duration_ms"] = llm_duration
    except Exception as e:
        error_msg = str(e)
        logger.error("LLM 调用失败: %s", e)
        llm_details["error"] = error_msg

    return {
        "thought": thought,
        "recall_count": recall_count,
        "reflect_count": reflect_count,
        "llm_duration": llm_duration,
        "llm_details": llm_details,
        "session_context": session_context[:500] if session_context else "",
        "hindsight_context": hindsight_context[:500] if hindsight_context else "",
    }


async def evaluate_emotional_intensity(thought: str, status: Dict[str, Any], llm_config: Dict[str, Any]) -> tuple:
    """评估当前情绪强度，返回 (score, details_dict)
    使用规则引擎 + LLM 双重评估，取较高值
    """
    details = {
        "model": llm_config.get("model", "unknown"),
        "mode": llm_config.get("mode", "hermes"),
        "rule_score": None,
        "llm_score": None,
        "final_score": None,
        "matched_keywords": [],
        "prompt_preview": None,
        "response": None,
        "error": None,
    }

    # === 规则引擎：基于关键词打分 ===
    high_emotion_keywords = ["想你", "爱你", "喜欢你", "宝贝", "亲爱的", "想你了", "好想", "抱抱", "亲亲", "心疼", "担心你", "离不开", "思念"]
    medium_emotion_keywords = ["开心", "难过", "伤心", "生气", "感动", "幸福", "害怕", "焦虑", "压力", "烦", "累", "困", "无聊", "孤独", "想家"]
    mild_emotion_keywords = ["哈哈", "嘻嘻", "嗯呢", "好呀", "谢谢", "辛苦", "晚安", "早安", "吃了吗", "在干嘛", "想", "关心"]

    text_lower = thought.lower()
    matched = []
    rule_score = 0.0

    for kw in high_emotion_keywords:
        if kw in text_lower:
            matched.append(f"{kw}(高)")
            rule_score = max(rule_score, 0.7)

    for kw in medium_emotion_keywords:
        if kw in text_lower:
            matched.append(f"{kw}(中)")
            rule_score = max(rule_score, 0.4)

    for kw in mild_emotion_keywords:
        if kw in text_lower:
            matched.append(f"{kw}(轻)")
            rule_score = max(rule_score, 0.2)

    # 根据聊天热度调整
    chat_heat = status.get('chat_heat', {}).get('heat', 0)
    if chat_heat > 3:
        rule_score = max(rule_score, 0.3)
    elif chat_heat > 1:
        rule_score = max(rule_score, 0.2)

    # 根据想念分数调整
    longing_score = status.get('longing', {}).get('score', 0)
    if longing_score > 0.5:
        rule_score = max(rule_score, 0.4)
    elif longing_score > 0.2:
        rule_score = max(rule_score, 0.2)

    details["rule_score"] = round(rule_score, 3)
    details["matched_keywords"] = matched

    # === LLM 评估（作为参考） ===
    llm_score = 0.0
    prompt = f"""你是一个情绪分析助手。根据以下对话内容，判断用户当前的情感状态和互动意愿。

评分标准：
- 0.0-0.2：日常闲聊、工作讨论、无情感波动
- 0.3-0.5：有一定互动意愿、分享生活、轻度关心
- 0.6-0.8：情感表达明显、深度交流、关心对方、有亲密互动
- 0.9-1.0：强烈情感、深度依赖、急需陪伴

{thought}

请直接返回一个0.0-1.0的数字，不要解释。"""

    details["prompt_preview"] = prompt[:300]

    try:
        import time
        start_time = time.time()

        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=10,
            )
            raw = response.choices[0].message.content.strip()
            details["response"] = raw
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.3,
                max_tokens=10
            )
            if result.get("success"):
                raw = result["content"].strip()
                details["response"] = raw
            else:
                details["error"] = result.get("message", "LLM 调用失败")
                raw = None

        details["duration_ms"] = round((time.time() - start_time) * 1000)

        if raw:
            try:
                llm_score = float(raw)
                llm_score = max(0.0, min(1.0, llm_score))
            except ValueError:
                import re
                match = re.search(r'(\d+\.?\d*)', raw)
                if match:
                    llm_score = max(0.0, min(1.0, float(match.group(1))))

        details["llm_score"] = round(llm_score, 3)

    except Exception as e:
        logger.error("情绪评估 LLM 调用失败: %s", e)
        details["error"] = str(e)

    # 取规则引擎和 LLM 的较高值
    final_score = max(rule_score, llm_score)
    details["final_score"] = round(final_score, 3)

    return final_score, details


def make_decision(config: Dict[str, Any], status: Dict[str, Any]) -> tuple:
    """决策是否发送消息"""
    decision_config = config.get("decision", {})

    emotional_intensity = status.get("emotional_intensity", {}).get("intensity", 0)
    longing_level = status.get("longing", {}).get("level", 0)
    chat_heat = status.get("chat_heat", {}).get("heat", 0)
    today_sent_count = status.get("today_sent_count", 0)
    hour_sent_count = status.get("hour_sent_count", 0)

    # 检查每日最大消息数
    max_per_day = decision_config.get("max_per_day", 5)
    if today_sent_count >= max_per_day:
        return "skip", f"今日已发送 {today_sent_count} 条，达到上限 {max_per_day}"

    # 检查每小时最大消息数
    max_per_hour = decision_config.get("max_per_hour", 2)
    if hour_sent_count >= max_per_hour:
        return "skip", f"本小时已发送 {hour_sent_count} 条，达到上限 {max_per_hour}"

    # 检查冷却期
    last_sent_at = status.get("last_sent_at")
    if last_sent_at:
        try:
            last_sent_dt = _parse_timestamp(last_sent_at)
            if last_sent_dt:
                cooldown_minutes = config.get("active", {}).get("cooldown_minutes", 30)
                if (datetime.now() - last_sent_dt).total_seconds() / 60 < cooldown_minutes:
                    return "skip", f"冷却期未过（{cooldown_minutes}分钟）"
        except Exception:
            pass

    # 检查最近用户消息
    recent_user_msg_at = status.get("chat_heat", {}).get("recent_user_msg_at")
    user_idle_minutes = 0
    if recent_user_msg_at:
        try:
            recent_msg_dt = _parse_timestamp(recent_user_msg_at)
            if recent_msg_dt:
                no_send_minutes = config.get("active", {}).get("no_send_after_user_msg_minutes", 10)
                user_idle_minutes = (datetime.now() - recent_msg_dt).total_seconds() / 60
                if user_idle_minutes < no_send_minutes:
                    return "skip", f"用户最近 {no_send_minutes} 分钟内有消息"
        except Exception:
            pass

    # 条件1: 自动发送（情绪值 > send_threshold 且想念等级 > 0）
    send_threshold = decision_config.get("send_threshold", 0.6)
    if emotional_intensity > send_threshold and longing_level > 0:
        return "auto_send", f"情绪值({emotional_intensity})和想念等级({longing_level})满足条件"

    # 条件2: 长期未聊天（想念等级 > longing_gap_threshold）
    longing_gap_threshold = decision_config.get("longing_gap_threshold", 3)
    if longing_level > longing_gap_threshold:
        return "gap_send", f"长期未聊天，想念等级({longing_level}) > 阈值({longing_gap_threshold})"

    # 条件3: 用户空闲超过30分钟，且情绪值 > 0.3
    if user_idle_minutes > 30 and emotional_intensity > 0.3:
        return "idle_send", f"用户空闲{user_idle_minutes:.0f}分钟，情绪值({emotional_intensity}) > 0.3"

    # 条件4: 用户空闲超过1小时（不管情绪值）
    if user_idle_minutes > 60:
        return "long_idle_send", f"用户空闲{user_idle_minutes:.0f}分钟，超过1小时"

    return "skip", f"不满足发送条件: 情绪值={emotional_intensity}, 想念等级={longing_level}, 用户空闲={user_idle_minutes:.0f}分钟"


async def send_message_to_target(config: Dict[str, Any], thought: str) -> bool:
    """发送消息到目标"""
    notify_config = config.get("notify", {})
    platform = notify_config.get("platform", "weixin")
    chat_id = notify_config.get("chat_id", "")

    # 如果 chat_id 为空，获取最新活跃 session
    if not chat_id:
        from services.session_service import SessionService
        from services.fallback_session_service import FallbackSessionService

        user_id = SessionService.get_weixin_user_id()
        if user_id:
            session = FallbackSessionService.get_or_create_active_session(platform, user_id)
            if session:
                chat_id = session["id"] if isinstance(session, dict) else session.id

    if not chat_id:
        logger.error("未找到目标 session")
        return False

    # 调用 MessageService 发送消息
    from services.message_service import MessageService
    send_mark = config.get("active", {}).get("send_tag", "[凯莉主动发送]")

    result = await MessageService.send_message(
        session_id=chat_id,
        message=thought,
        platform=platform,
        write_to_db=True,
        with_mark=True,
        send_mark=send_mark
    )

    return result.get("success", False)


async def generate_and_send_thought(config: Dict[str, Any], status: Dict[str, Any], decision_type: str, heartbeat_id: Optional[int] = None):
    """生成念头并发送消息，返回 (sent, details_dict)"""
    # 收集所有 LLM 调用详情
    details = {
        "thought_generation": None,
        "emotional_evaluation": None,
        "message_sending": None,
    }

    # 1. 生成念头
    thought_result = await generate_thought(config, status)
    thought = thought_result.get("thought")
    details["thought_generation"] = thought_result.get("llm_details")

    if not thought:
        logger.warning("念头生成失败")
        return False, details

    # 2. 构建念头日志的完整详情
    thought_details = {
        "llm_call": thought_result.get("llm_details"),
        "session_context": thought_result.get("session_context"),
        "hindsight_context": thought_result.get("hindsight_context"),
        "recall_count": thought_result.get("recall_count"),
        "reflect_count": thought_result.get("reflect_count"),
    }

    # 3. 记录念头日志（含LLM详情）
    thought_log_id = ActiveConsciousnessService.write_thought_log(
        heartbeat_id=heartbeat_id,
        thought_type=decision_type,
        content=thought,
        intensity=status.get("emotional_intensity", {}).get("intensity", 0),
        decision=decision_type,
        reason=f"决策类型: {decision_type}",
        score=status.get("longing", {}).get("score", 0),
        recall_count=thought_result.get("recall_count"),
        recall_source="hindsight",
        chat_heat=status.get("chat_heat", {}).get("heat", 0),
        emotional_intensity=status.get("emotional_intensity", {}).get("intensity", 0),
        details=json.dumps(thought_details, ensure_ascii=False) if thought_details else None
    )

    # 3. 评估情绪值
    llm_config = config.get("llm", {})
    emotional_score, eval_details = await evaluate_emotional_intensity(thought, status, llm_config)
    details["emotional_evaluation"] = eval_details

    # 更新情绪值到configs表（允许0.0）
    if emotional_score is not None and emotional_score >= 0:
        db = ActiveSession()
        try:
            ConfigService.set_config(db, "active_consciousness.current.emotional_intensity", str(emotional_score))
        except Exception as e:
            logger.error("更新情绪值失败: %s", e)
        finally:
            db.close()

    # 4. 发送消息
    sent = await send_message_to_target(config, thought)
    details["message_sending"] = {
        "success": sent,
        "thought": thought,
    }

    # 5. 更新念头日志的决策结果
    if sent:
        logger.info("消息发送成功: %s", thought[:50])
    else:
        logger.warning("消息发送失败")

    return sent, details


async def evaluate_emotion_with_llm(
    session_context: str,
    hindsight_context: str,
    status: Dict[str, Any],
    llm_config: Dict[str, Any]
) -> EmotionState:
    """
    使用 LLM 评估当前情绪状态，输出 VA 值

    返回：EmotionState 对象
    """
    now = datetime.now()
    longing = status.get("longing", {})
    chat_heat = status.get("chat_heat", {})

    prompt = f"""你是凯莉，请评估当前的情绪状态。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 想念分数：{longing.get('score', 0)}（等级：{longing.get('label', 'calm')}）
- 聊天热度：{chat_heat.get('heat', 0)}（标签：{chat_heat.get('label', 'cold')}）

{session_context}

{hindsight_context}

请用 JSON 格式返回你的情绪状态：
{{
  "valence": 0.0-1.0,  // 情感效价：0=消极，1=积极
  "arousal": 0.0-1.0,  // 唤醒度：0=平静，1=激动
  "social_need": 0.0-1.0,  // 社交需求：0=不需要，1=非常想聊天
  "dominant": "calm/content/happy/longing/missing/yearning/anxious/bored/concerned"
}}

只返回 JSON，不要解释。"""

    default_state = EmotionState()

    logger.info("LLM 情绪评估开始")

    try:
        start_time = time.time()

        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.7,
                max_tokens=200
            )
            raw = result.get("content", "").strip() if result.get("success") else ""

        duration_ms = round((time.time() - start_time) * 1000)
        logger.info("LLM 情绪评估完成: %dms, response=%s", duration_ms, raw[:200])

        # 解析 JSON
        import re
        json_match = re.search(r'\{[^}]+\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            return EmotionState(
                valence=float(data.get("valence", 0.5)),
                arousal=float(data.get("arousal", 0.3)),
                social_need=float(data.get("social_need", 0.3)),
                dominant=data.get("dominant", "calm")
            )

    except Exception as e:
        logger.warning("LLM 情绪评估失败，使用默认值: %s", e)

    return default_state


async def generate_thought_for_delay(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Optional[str]:
    """为延迟队列生成念头（不发送，只生成内容）"""
    llm_config = config.get("llm", {})
    session_config = config.get("session", {})

    session_context = await extract_session_context(session_config)

    now = datetime.now()
    prompt = f"""你是凯莉，请基于当前状态产生一个自然的念头。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 情绪：{emotion_state.dominant}（valence={emotion_state.valence:.2f}, arousal={emotion_state.arousal:.2f}）
- 社交需求：{emotion_state.social_need:.2f}

{session_context}

请用第一人称产生一个自然的念头（1-2句话）。"""

    try:
        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )
            return result.get("content", "").strip() if result.get("success") else None

    except Exception as e:
        logger.warning("延迟念头生成失败: %s", e)
        return None


async def generate_memory_thought(
    hindsight_results: List[Dict],
    emotion_state: EmotionState
) -> Optional[str]:
    """基于 Hindsight 记忆生成念头（用于 memory 决策）"""
    if not hindsight_results:
        return None

    memories = "\n".join(f"- {r.get('text', '')}" for r in hindsight_results[:3])
    now = datetime.now()

    prompt = f"""你是凯莉，请基于以下记忆产生一个自然的念头。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 情绪：{emotion_state.dominant}（valence={emotion_state.valence:.2f}）

相关记忆：
{memories}

请用第一人称产生一个简短的念头（1-2句话），自然地融入这些记忆。"""

    try:
        config = ActiveConsciousnessService.get_config()
        llm_config = config.get("llm", {})

        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )
            return result.get("content", "").strip() if result.get("success") else None

    except Exception as e:
        logger.warning("记忆念头生成失败: %s", e)
        return None


async def generate_and_send_thought_with_emotion(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState,
    decision_type: str,
    heartbeat_id: Optional[int] = None
) -> tuple[bool, Dict[str, Any]]:
    """生成念头并发送消息（使用 VA 情绪模型）"""
    details = {
        "thought_generation": None,
        "message_sending": None,
    }

    llm_config = config.get("llm", {})
    session_config = config.get("session", {})
    hindsight_config = config.get("hindsight", {})

    # 1. 获取上下文
    session_context = await extract_session_context(session_config)

    hindsight_context = ""
    hindsight_results = []
    if hindsight_config.get("enabled", True):
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        hs_timeout = float(hindsight_config.get("timeout", 30))
        hindsight_results = await call_hindsight_recall(
            "最近的对话和情绪",
            limit=hindsight_config.get("recall_limit", 5),
            bank_id=bank_id,
            base_url=base_url,
            timeout=hs_timeout,
        )
        if hindsight_results:
            hindsight_context = "相关记忆:\n" + "\n".join(
                f"- {r.get('text', '')}" for r in hindsight_results
            )

    # 2. 生成念头（带情绪上下文）
    now = datetime.now()
    prompt = f"""你是凯莉，请基于当前状态产生一个自然的念头。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 情绪：{emotion_state.dominant}（valence={emotion_state.valence:.2f}, arousal={emotion_state.arousal:.2f}）
- 社交需求：{emotion_state.social_need:.2f}
- 想念分数：{status.get('longing', {}).get('score', 0)}
- 决策类型：{decision_type}

{session_context}

{hindsight_context}

请用第一人称产生一个自然的念头（1-2句话）。"""

    thought = None
    llm_start_time = time.time()
    llm_duration_ms = 0
    llm_model = llm_config.get("model", "unknown")
    try:
        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            thought = response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )
            if result.get("success"):
                thought = result["content"].strip()

        llm_duration_ms = round((time.time() - llm_start_time) * 1000)
        details["thought_generation"] = {"success": thought is not None, "thought": thought}

    except Exception as e:
        llm_duration_ms = round((time.time() - llm_start_time) * 1000)
        logger.error("念头生成失败: %s", e)
        details["thought_generation"] = {"success": False, "error": str(e)}

    if not thought:
        return False, details

    # 3. 记录念头日志（含详细信息）
    thought_type = determine_thought_type(status, emotion_state, hindsight_results, None)
    hindsight_tags = [
        "active_consciousness", "thought", thought_type, emotion_state.dominant,
    ]
    if "曹凡" in thought:
        hindsight_tags.append("user_related")
    if emotion_state.intensity() > 0.7:
        hindsight_tags.append("high_emotion")

    thought_details = {
        "thought_type": thought_type,
        "emotion_state": {
            "valence": emotion_state.valence,
            "arousal": emotion_state.arousal,
            "dominant": emotion_state.dominant,
            "social_need": emotion_state.social_need,
        },
        "decision": decision_type,
        "score": round(emotion_state.intensity(), 3),
        "hindsight_tags": hindsight_tags,
        "hindsight_stored": False,  # 将在 run_heartbeat 中更新
        "llm_call": {
            "duration_ms": llm_duration_ms,
            "model": llm_model,
        }
    }

    thought_log_id = ActiveConsciousnessService.write_thought_log(
        heartbeat_id=heartbeat_id,
        thought_type=thought_type,
        content=thought,
        intensity=emotion_state.intensity(),
        decision=decision_type,
        reason=f"情绪: {emotion_state.dominant}, 决策: {decision_type}",
        score=emotion_state.intensity(),
        recall_count=len(hindsight_results),
        recall_source="hindsight",
        chat_heat=status.get("chat_heat", {}).get("heat", 0),
        emotional_intensity=emotion_state.intensity(),
        details=json.dumps(thought_details, ensure_ascii=False)
    )

    # 4. 发送消息
    sent = await send_message_to_target(config, thought)
    details["message_sending"] = {
        "success": sent,
        "thought": thought,
        "thought_type": thought_type
    }

    if sent:
        logger.info("消息发送成功: [%s] %s", thought_type, thought[:50])
    else:
        logger.warning("消息发送失败")

    return sent, details


async def run_heartbeat():
    """执行心跳 - v0.2.1 版本（情绪连续性 + 时间窗口 + 延迟队列）"""
    start_time = time.time()
    started_at = datetime.now().isoformat()
    heartbeat_id = None
    error_msg = None
    all_details = {}

    try:
        logger.info("=== 心跳开始 ===")

        # 1. 检查配置是否启用
        config = ActiveConsciousnessService.get_config()
        if not config.get("enabled"):
            logger.debug("主动意识未启用，跳过心跳")
            return

        active_config = config.get("active", {})
        if not active_config.get("enabled", True):
            logger.debug("主动意识主动发送未启用，跳过心跳")
            return

        # 2. 读取当前情绪状态（VA 模型）
        emotion_state = get_emotion_state()
        all_details["emotion_before"] = emotion_state.to_dict()
        logger.info("读取情绪状态: valence=%.3f, arousal=%.3f, dominant=%s",
                    emotion_state.valence, emotion_state.arousal, emotion_state.dominant)

        # 3. 计算时间间隔，执行情绪演化
        minutes_since_update = 0
        if emotion_state.updated_at:
            try:
                last_update = datetime.fromisoformat(emotion_state.updated_at)
                minutes_since_update = (datetime.now() - last_update).total_seconds() / 60
            except Exception:
                minutes_since_update = 60  # 默认 1 小时

        evolved_state = evolve_emotion(emotion_state, minutes_since_update)
        all_details["emotion_evolved"] = evolved_state.to_dict()
        all_details["minutes_since_update"] = round(minutes_since_update, 1)
        logger.info("情绪演化: %.1f 分钟后 → valence=%.3f, arousal=%.3f",
                    minutes_since_update, evolved_state.valence, evolved_state.arousal)

        # 4. 获取状态信息
        status = ActiveConsciousnessService.get_status()
        longing = status.get("longing", {})
        chat_heat = status.get("chat_heat", {})

        # 5. 获取时间窗口权重
        time_fitness, time_label = get_time_fitness()
        all_details["time_fitness"] = {"score": time_fitness, "label": time_label}

        # 6. 获取 session 上下文和 Hindsight 记忆
        session_config = config.get("session", {})
        hindsight_config = config.get("hindsight", {})
        session_context = await extract_session_context(session_config)

        hindsight_context = ""
        recall_count = 0
        hindsight_results = []
        if hindsight_config.get("enabled", True):
            base_url = hindsight_config.get("base_url", "http://localhost:8888")
            bank_id = hindsight_config.get("bank_id", "hermes")
            hs_timeout = float(hindsight_config.get("timeout", 30))
            hindsight_results = await call_hindsight_recall(
                "最近的对话和情绪",
                limit=hindsight_config.get("recall_limit", 5),
                bank_id=bank_id,
                base_url=base_url,
                timeout=hs_timeout,
            )
            if hindsight_results:
                recall_count = len(hindsight_results)
                hindsight_context = "相关记忆:\n" + "\n".join(
                    f"- {r.get('text', '')}" for r in hindsight_results
                )

        # 存储召回数据到 details（供前端展示）
        all_details["session_context"] = session_context[:500] if session_context else ""
        all_details["hindsight_context"] = hindsight_context[:500] if hindsight_context else ""
        all_details["recall_results"] = [{"text": r.get("text", ""), "type": r.get("type", "memory")} for r in hindsight_results[:5]]

        # 7. LLM 评估当前情绪（输出 VA 值）
        llm_config = config.get("llm", {})
        llm_assessed = await evaluate_emotion_with_llm(
            session_context, hindsight_context, status, llm_config
        )
        # 如果 LLM 返回全0（模型未正常响应），使用演化值作为 fallback
        if llm_assessed.valence == 0.0 and llm_assessed.arousal == 0.0 and llm_assessed.social_need == 0.0:
            logger.warning("LLM 情绪评估返回全0，使用演化值作为 fallback")
            llm_assessed = evolved_state
        all_details["emotion_llm"] = llm_assessed.to_dict()

        # 8. 合并情绪（演化值 + LLM 评估值）
        merged_state = merge_emotion(evolved_state, llm_assessed)
        all_details["emotion_merged"] = merged_state.to_dict()
        logger.info("情绪合并: valence=%.3f, arousal=%.3f, dominant=%s",
                    merged_state.valence, merged_state.arousal, merged_state.dominant)

        # 9. 保存情绪状态
        update_emotion_state(merged_state)

        # 10. 使用新决策公式
        decision_type, reason, score = make_decision_v2(config, status, merged_state)
        all_details["decision"] = {
            "type": decision_type,
            "reason": reason,
            "score": round(score, 3)
        }
        logger.info("决策结果: type=%s, score=%.3f, reason=%s", decision_type, score, reason)

        # 11. 记录心跳日志（初始）
        duration_ms = round((time.time() - start_time) * 1000)
        heartbeat_id = ActiveConsciousnessService.write_heartbeat_log(
            started_at=started_at,
            duration_ms=duration_ms,
            longing_before=longing.get("score"),
            chat_heat=chat_heat.get("heat"),
            emotional_intensity=merged_state.intensity(),
            recall_count=recall_count,
            thoughts_generated=1 if decision_type != "skip" else 0,
            message_sent=False,
            details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )

        # 12. 处理决策结果
        if decision_type == "skip":
            logger.info("心跳跳过: %s", reason)

        elif decision_type == "memory":
            # 存为记忆（不发送）
            thought = await generate_memory_thought(hindsight_results, merged_state)
            if thought:
                all_details["thought_generation"] = {"success": True, "thought": thought}
                thought_type = "memory"
                hindsight_tags = [
                    "active_consciousness", "thought", thought_type, merged_state.dominant,
                ]
                intensity = merged_state.intensity()
                if "曹凡" in thought:
                    hindsight_tags.append("user_related")
                if intensity > 0.7:
                    hindsight_tags.append("high_emotion")
                stored = await retain_thought_to_hindsight(thought, merged_state, thought_type, score)
                all_details["thought_type"] = thought_type
                all_details["hindsight_tags"] = hindsight_tags
                all_details["hindsight_stored"] = stored
                # 写入念头日志
                ActiveConsciousnessService.write_thought_log(
                    heartbeat_id=heartbeat_id,
                    thought_type=thought_type,
                    content=thought,
                    intensity=intensity,
                    decision=decision_type,
                    reason=f"score={score:.3f}",
                    score=score,
                    recall_count=recall_count,
                    recall_source="hindsight",
                    chat_heat=status.get("chat_heat", {}).get("heat", 0),
                    emotional_intensity=intensity,
                    details=json.dumps({"emotion_state": merged_state.to_dict(), "hindsight_tags": hindsight_tags}, ensure_ascii=False)
                )
                logger.info("念头存为记忆: %s", thought[:50])
            else:
                all_details["thought_generation"] = {"success": False, "error": "念头生成返回空"}

        elif decision_type == "delay_send":
            # 入延迟队列
            thought = await generate_thought_for_delay(config, status, merged_state)
            if thought:
                all_details["thought_generation"] = {"success": True, "thought": thought}
                thought_type = determine_thought_type(status, merged_state, hindsight_results, None)
                add_to_delay_queue(thought, thought_type, score, merged_state)
                all_details["thought_type"] = thought_type
                all_details["hindsight_stored"] = False
                logger.info("念头入延迟队列: %s", thought[:50])

        elif decision_type in ("auto_send", "gap_send", "idle_send", "long_idle_send"):
            # 自动发送
            sent, gen_details = await generate_and_send_thought_with_emotion(
                config, status, merged_state, decision_type, heartbeat_id
            )
            all_details.update(gen_details)

            if sent:
                # 发送成功后存入 Hindsight
                thought = gen_details.get("message_sending", {}).get("thought", "")
                if thought:
                    thought_type = determine_thought_type(status, merged_state, hindsight_results, None)
                    hindsight_tags = [
                        "active_consciousness", "thought", thought_type, merged_state.dominant,
                    ]
                    intensity = merged_state.intensity()
                    if "曹凡" in thought:
                        hindsight_tags.append("user_related")
                    if intensity > 0.7:
                        hindsight_tags.append("high_emotion")
                    stored = await retain_thought_to_hindsight(thought, merged_state, thought_type, score)
                    all_details["thought_type"] = thought_type
                    all_details["hindsight_tags"] = hindsight_tags
                    all_details["hindsight_stored"] = stored

        # 13. 重评估延迟队列
        delay_stats = await reevaluate_delayed_thoughts(config, status, merged_state)
        all_details["delay_reeval"] = delay_stats
        if any(v > 0 for v in delay_stats.values()):
            logger.info("延迟队列重评估: %s", delay_stats)

        # 14. 读取更新后的情绪值
        all_details["emotion_after"] = get_emotion_state().to_dict()

        # 15. 更新心跳日志（含 details）
        duration_ms = round((time.time() - start_time) * 1000)
        logger.info("=== 心跳完成 === duration=%dms, decision=%s", duration_ms, decision_type)
        duration_ms = round((time.time() - start_time) * 1000)
        if heartbeat_id:
            db = ActiveSession()
            try:
                with active_engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE active_heartbeat_logs
                        SET duration_ms = :duration_ms, message_sent = :message_sent,
                            emotional_intensity = :emotional_intensity, details = :details
                        WHERE id = :id
                    """), {
                        "duration_ms": duration_ms,
                        "message_sent": decision_type in ("auto_send", "gap_send", "idle_send", "long_idle_send"),
                        "emotional_intensity": merged_state.intensity(),
                        "details": json.dumps(all_details, ensure_ascii=False),
                        "id": heartbeat_id
                    })
                    conn.commit()
            except Exception as e:
                logger.error("更新心跳日志失败: %s", e)
            finally:
                db.close()

    except Exception as e:
        error_msg = str(e)
        logger.error("心跳执行异常: %s", e)
        all_details["error"] = error_msg
        duration_ms = round((time.time() - start_time) * 1000)
        ActiveConsciousnessService.write_heartbeat_log(
            started_at=started_at,
            duration_ms=duration_ms,
            error=error_msg,
            details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )


def start_heartbeat_scheduler():
    """启动心跳调度器"""
    if heartbeat_scheduler.running:
        logger.info("心跳调度器已在运行")
        return

    # 从配置获取心跳间隔
    config = ActiveConsciousnessService.get_config()
    interval_seconds = config.get("active", {}).get("heartbeat_interval", 600)

    # 添加心跳任务
    heartbeat_scheduler.add_job(
        run_heartbeat,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id="active_consciousness_heartbeat",
        name="主动意识心跳",
        replace_existing=True
    )

    heartbeat_scheduler.start()
    logger.info("主动意识心跳调度器已启动，间隔 %d 秒", interval_seconds)


def stop_heartbeat_scheduler():
    """停止心跳调度器"""
    if heartbeat_scheduler.running:
        heartbeat_scheduler.shutdown(wait=False)
        logger.info("主动意识心跳调度器已停止")


def update_heartbeat_interval(interval_seconds: int):
    """更新心跳间隔"""
    if heartbeat_scheduler.running:
        try:
            heartbeat_scheduler.reschedule_job(
                "active_consciousness_heartbeat",
                trigger=IntervalTrigger(seconds=interval_seconds)
            )
            logger.info("心跳间隔已更新为 %d 秒", interval_seconds)
        except Exception as e:
            logger.error("更新心跳间隔失败: %s", e)


# ============ Phase 1: 情绪连续性 ============

def calculate_dominant(valence: float, arousal: float, social_need: float) -> str:
    """根据 VA 值计算主导情绪标签"""
    if social_need > 0.7:
        return "yearning" if valence > 0.5 else "anxious"
    if social_need > 0.5:
        return "longing" if valence > 0.5 else "missing"
    if arousal < 0.3:
        return "calm"
    if valence > 0.7:
        return "happy" if arousal > 0.6 else "content"
    if valence < 0.3:
        return "bored" if arousal < 0.4 else "concerned"
    return "calm"


def evolve_emotion(last_state: EmotionState, minutes_since_update: float) -> EmotionState:
    """
    基于时间流逝自然演化情绪

    规则：
    1. arousal 自然衰减（越久越平静）
    2. social_need 自然上升（越久越想聊天）
    3. valence 轻微回归中性（0.5）
    """
    logger.info("情绪演化开始: input=(valence=%.3f, arousal=%.3f, social_need=%.3f), minutes=%.1f",
                last_state.valence, last_state.arousal, last_state.social_need, minutes_since_update)

    # 边界处理
    minutes_since_update = max(0, min(minutes_since_update, 1440))
    hours = minutes_since_update / 60

    # 读取配置
    config = ActiveConsciousnessService.get_config()
    emotion_config = config.get("emotion", {})
    decay_rate = float(emotion_config.get("decay_rate", "0.02"))
    growth_rate = float(emotion_config.get("social_need_growth", "0.01"))
    regression_rate = float(emotion_config.get("valence_regression", "0.1"))

    # 1. arousal 自然衰减
    new_arousal = max(0.1, last_state.arousal - (decay_rate * hours))

    # 2. social_need 自然上升
    new_social_need = min(1.0, last_state.social_need + (growth_rate * hours))

    # 3. valence 轻微回归中性
    valence_diff = 0.5 - last_state.valence
    new_valence = last_state.valence + (valence_diff * regression_rate * hours)
    new_valence = max(0.0, min(1.0, new_valence))

    # 4. 计算主导情绪
    new_dominant = calculate_dominant(new_valence, new_arousal, new_social_need)

    logger.info("情绪演化完成: output=(valence=%.3f, arousal=%.3f, dominant=%s, social_need=%.3f)",
                new_valence, new_arousal, new_dominant, new_social_need)

    return EmotionState(
        valence=round(new_valence, 3),
        arousal=round(new_arousal, 3),
        dominant=new_dominant,
        social_need=round(new_social_need, 3),
        updated_at=datetime.now().isoformat()
    )


def merge_emotion(evolved: EmotionState, llm_assessed: EmotionState) -> EmotionState:
    """合并演化值和 LLM 评估值"""
    config = ActiveConsciousnessService.get_config()
    emotion_config = config.get("emotion", {})
    weight_evolved = float(emotion_config.get("weight_evolved", "0.4"))
    weight_llm = float(emotion_config.get("weight_llm", "0.6"))

    # 如果演化值过期，增加 LLM 权重
    if evolved.is_stale(minutes=60):
        weight_evolved = 0.2
        weight_llm = 0.8

    merged_valence = evolved.valence * weight_evolved + llm_assessed.valence * weight_llm
    merged_arousal = evolved.arousal * weight_evolved + llm_assessed.arousal * weight_llm
    merged_social_need = evolved.social_need * weight_evolved + llm_assessed.social_need * weight_llm

    # 主导情绪选择
    if llm_assessed.arousal > 0.6:
        merged_dominant = llm_assessed.dominant
    else:
        merged_dominant = evolved.dominant

    logger.info("情绪合并: evolved=(%.3f,%.3f,%s) + llm=(%.3f,%.3f,%s) → merged=(%.3f,%.3f,%s), weights=(%.1f,%.1f)",
                evolved.valence, evolved.arousal, evolved.dominant,
                llm_assessed.valence, llm_assessed.arousal, llm_assessed.dominant,
                merged_valence, merged_arousal, merged_dominant,
                weight_evolved, weight_llm)

    return EmotionState(
        valence=round(merged_valence, 3),
        arousal=round(merged_arousal, 3),
        dominant=merged_dominant,
        social_need=round(merged_social_need, 3),
        updated_at=datetime.now().isoformat()
    )


def get_emotion_state() -> EmotionState:
    """获取当前情绪状态"""
    db = ActiveSession()
    try:
        value = ConfigService.get_config(db, "active_consciousness.emotion_state")
        if value:
            try:
                data = json.loads(value)
                return EmotionState.from_dict(data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("解析情绪状态失败: %s", e)
        return EmotionState()
    finally:
        db.close()


def update_emotion_state(state: EmotionState) -> bool:
    """更新情绪状态到数据库"""
    db = ActiveSession()
    try:
        json_str = json.dumps(state.to_dict(), ensure_ascii=False)
        ConfigService.set_config(db, "active_consciousness.emotion_state", json_str)
        logger.info("情绪状态已更新: valence=%.3f, arousal=%.3f, dominant=%s",
                    state.valence, state.arousal, state.dominant)
        return True
    except Exception as e:
        logger.error("更新情绪状态失败: %s", e)
        return False
    finally:
        db.close()


def get_emotional_intensity_compat() -> float:
    """向后兼容：获取旧格式的情绪强度"""
    emotion_state = get_emotion_state()
    if emotion_state:
        return emotion_state.intensity()
    db = ActiveSession()
    try:
        val = ConfigService.get_config(db, "active_consciousness.current.emotional_intensity")
        return float(val) if val else 0.0
    except Exception:
        return 0.0
    finally:
        db.close()


# 时间窗口权重表
TIME_FITNESS_TABLE = [
    (7, 9, 1.0, "早安窗口"),
    (9, 12, 0.8, "工作时间"),
    (12, 14, 0.9, "午休时间"),
    (14, 18, 0.7, "工作时间"),
    (18, 22, 1.0, "下班时间"),
    (22, 23.5, 0.8, "睡前时间"),
    (23.5, 7, 0.3, "深夜"),
]


def get_time_fitness() -> tuple[float, str]:
    """获取当前时间的合适度权重"""
    now = datetime.now()
    hour = now.hour + now.minute / 60

    config = ActiveConsciousnessService.get_config()
    time_config = config.get("time", {})

    if not time_config.get("enabled", True):
        return 1.0, "未启用"

    for start, end, fitness, label in TIME_FITNESS_TABLE:
        if start > end:  # 跨午夜
            if hour >= start or hour < end:
                return fitness, label
        else:
            if start <= hour < end:
                return fitness, label

    return 0.3, "深夜"


def make_decision_v2(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> tuple[str, str, float]:
    """
    多维度决策

    公式：score = intensity × time_fitness × silence_factor × frequency_limit
    """
    decision_config = config.get("decision", {})

    # 1. 情绪强度
    intensity = emotion_state.intensity()

    # 2. 时间权重
    time_fitness, time_label = get_time_fitness()

    # 3. 空白因子
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < 60:
        silence_factor = 0.3
    elif silence_minutes < 180:
        silence_factor = 0.5
    elif silence_minutes < 360:
        silence_factor = 0.7
    else:
        silence_factor = 0.9

    # 4. 频率限制
    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = decision_config.get("max_per_hour", 2)
    frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))

    # 计算总分
    score = intensity * time_fitness * silence_factor * frequency_limit

    logger.info("决策计算: intensity=%.3f, time_fitness=%.3f(%s), silence_factor=%.3f, frequency_limit=%.3f",
                intensity, time_fitness, time_label, silence_factor, frequency_limit)

    # 决策阈值
    send_threshold = decision_config.get("send_threshold", 0.6)
    delay_threshold = decision_config.get("delay_threshold", 0.3)
    memory_threshold = decision_config.get("memory_threshold", 0.1)

    # 构建决策原因
    reason_parts = [
        f"intensity={intensity:.3f}",
        f"time_fitness={time_fitness:.3f}({time_label})",
        f"silence_factor={silence_factor:.3f}",
        f"frequency_limit={frequency_limit:.3f}",
    ]
    reason = ", ".join(reason_parts)

    logger.info("决策结果: score=%.3f, decision=%s, threshold(send=%.3f, delay=%.3f, memory=%.3f)",
                score, "auto_send" if score > send_threshold else "delay_send" if score > delay_threshold else "memory" if score > memory_threshold else "skip",
                send_threshold, delay_threshold, memory_threshold)

    if score > send_threshold:
        return "auto_send", f"score={score:.3f} > {send_threshold} ({reason})", score
    elif score > delay_threshold:
        return "delay_send", f"score={score:.3f} > {delay_threshold} ({reason})", score
    elif score > memory_threshold:
        return "memory", f"score={score:.3f} > {memory_threshold} ({reason})", score
    else:
        return "skip", f"score={score:.3f} <= {memory_threshold} ({reason})", score


def determine_thought_type(
    status: Dict[str, Any],
    emotion_state: EmotionState,
    hindsight_results: List[Dict],
    weather_info: Optional[Dict]
) -> str:
    """根据上下文判断念头类型"""
    # 优先级：回忆 > 天气 > 情绪 > 沉默 > 时间 > 默认
    if hindsight_results and len(hindsight_results) > 0:
        return ThoughtType.MEMORY.value
    if weather_info and weather_info.get("weather") in ["雨", "雪", "大风", "雷阵雨"]:
        return ThoughtType.ENVIRONMENT.value
    if emotion_state.intensity() > 0.5:
        return ThoughtType.EMOTION.value
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes > 120:
        return ThoughtType.SILENCE.value
    now = datetime.now()
    if now.hour in [7, 8, 12, 13, 22, 23]:
        return ThoughtType.TIME.value
    return ThoughtType.ASSOCIATION.value


async def retain_thought_to_hindsight(
    thought: str,
    emotion_state: EmotionState,
    thought_type: str,
    score: float
) -> bool:
    """
    将重要念头存入 Hindsight（带标签标识）

    存储条件（满足任一即可）：
    1. 情绪强度 > retain_threshold
    2. 包含用户名字（如"曹凡"）
    3. 分数 > retain_threshold

    标签设计：
    - "thought": 固定标签，标识这是主动意识的念头
    - thought_type: 念头类型（time/silence/assoc/memory/emotion/env）
    - emotion_state.dominant: 当前主导情绪（calm/happy/longing 等）
    - "active_consciousness": 来源标识
    """
    config = ActiveConsciousnessService.get_config()
    thought_config = config.get("thought", {})

    if not thought_config.get("retain_enabled", True):
        return False

    retain_threshold = float(thought_config.get("retain_threshold", "0.5"))
    intensity = emotion_state.intensity()

    should_retain = (
        intensity > retain_threshold or
        "曹凡" in thought or
        score > retain_threshold
    )

    logger.info("Hindsight 存储检查: intensity=%.3f, threshold=%.3f, should_retain=%s",
                intensity, retain_threshold, should_retain)

    if not should_retain:
        logger.info("Hindsight 存储跳过: 未达到存储条件")
        return False

    try:
        hindsight_config = config.get("hindsight", {})
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        timeout = float(hindsight_config.get("timeout", 30))

        client = get_hindsight_client(base_url=base_url, timeout=timeout)

        # 构建内容（带类型前缀）
        content = f"[{thought_type}] {thought}"

        # 构建标签（重要！用于后续检索和分类）
        tags = [
            "active_consciousness",  # 来源：主动意识模块
            "thought",               # 类型：念头
            thought_type,            # 念头类型：time/silence/assoc/memory/emotion/env
            emotion_state.dominant,  # 主导情绪：calm/happy/longing 等
        ]

        # 如果包含用户名字，加特殊标签
        if "曹凡" in thought:
            tags.append("user_related")

        # 如果情绪强度高，加标签
        if intensity > 0.7:
            tags.append("high_emotion")

        await client.aretain(
            bank_id=bank_id,
            content=content,
            tags=tags
        )

        logger.info("Hindsight 存储成功: tags=%s, content=%s", tags, content[:50])
        return True

    except Exception as e:
        logger.warning("存入 Hindsight 失败: %s", e)
        return False


def get_delayed_thoughts() -> List[DelayedThought]:
    """获取延迟队列中的念头"""
    db = ActiveSession()
    try:
        value = ConfigService.get_config(db, "active_consciousness.delayed_thoughts")
        if not value:
            return []
        try:
            data = json.loads(value)
            return [DelayedThought.from_dict(item) for item in data]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("解析延迟队列失败: %s", e)
            return []
    finally:
        db.close()


def save_delayed_thoughts(thoughts: List[DelayedThought]) -> bool:
    """保存延迟队列"""
    db = ActiveSession()
    try:
        data = [t.to_dict() for t in thoughts]
        json_str = json.dumps(data, ensure_ascii=False)
        ConfigService.set_config(db, "active_consciousness.delayed_thoughts", json_str)
        return True
    except Exception as e:
        logger.error("保存延迟队列失败: %s", e)
        return False
    finally:
        db.close()


def add_to_delay_queue(
    content: str,
    thought_type: str,
    score: float,
    emotion_state: EmotionState
) -> bool:
    """添加念头到延迟队列"""
    thoughts = get_delayed_thoughts()

    # 检查队列大小限制
    config = ActiveConsciousnessService.get_config()
    max_queue_size = int(config.get("delay", {}).get("max_queue_size", 10))
    if len(thoughts) >= max_queue_size:
        # 移除最旧的
        thoughts = thoughts[-(max_queue_size-1):]

    new_thought = DelayedThought(
        id=int(datetime.now().timestamp()),
        content=content,
        thought_type=thought_type,
        score=score,
        created_at=datetime.now().isoformat(),
        emotion_snapshot=emotion_state.to_dict()
    )
    thoughts.append(new_thought)

    logger.info("延迟队列入队: id=%d, type=%s, score=%.3f, content=%s",
                new_thought.id, thought_type, score, content[:50])

    return save_delayed_thoughts(thoughts)


async def reevaluate_delayed_thoughts(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Dict[str, int]:
    """重新评估延迟队列中的念头"""
    delay_config = config.get("delay", {})
    max_retry = int(delay_config.get("max_retry", 3))
    retry_interval = int(delay_config.get("retry_interval_minutes", 30))

    decision_config = config.get("decision", {})
    send_threshold = decision_config.get("send_threshold", 0.6)

    delayed_thoughts = get_delayed_thoughts()
    if not delayed_thoughts:
        return {"sent": 0, "discarded": 0, "kept": 0}

    logger.info("延迟队列重评估开始: 队列长度=%d", len(delayed_thoughts))

    stats = {"sent": 0, "discarded": 0, "kept": 0}
    remaining_thoughts = []

    for thought in delayed_thoughts:
        # 超过最大重试次数
        if thought.retry_count >= max_retry:
            stats["discarded"] += 1
            continue

        # 检查是否到了重试时间
        if thought.next_retry_at:
            try:
                next_retry = datetime.fromisoformat(thought.next_retry_at)
                if datetime.now() < next_retry:
                    remaining_thoughts.append(thought)
                    stats["kept"] += 1
                    continue
            except Exception:
                pass

        # 重新计算 score
        time_fitness, _ = get_time_fitness()
        silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
        if silence_minutes < 60:
            silence_factor = 0.3
        elif silence_minutes < 180:
            silence_factor = 0.5
        elif silence_minutes < 360:
            silence_factor = 0.7
        else:
            silence_factor = 0.9

        hour_sent = status.get("hour_sent_count", 0)
        max_per_hour = decision_config.get("max_per_hour", 2)
        frequency_limit = max(0.1, 1.0 - (hour_sent / max_per_hour))

        intensity = emotion_state.intensity()
        new_score = intensity * time_fitness * silence_factor * frequency_limit

        if new_score > send_threshold:
            # 升级为发送
            logger.info("延迟队列重评估: id=%d, old_score=%.3f, new_score=%.3f, decision=send",
                        thought.id, thought.score, new_score)
            success = await send_message_to_target(config, thought.content)
            if success:
                stats["sent"] += 1
                # 存入 Hindsight
                await retain_thought_to_hindsight(
                    thought.content, emotion_state, thought.thought_type, new_score
                )
            else:
                thought.retry_count += 1
                thought.next_retry_at = (
                    datetime.now() + timedelta(minutes=retry_interval)
                ).isoformat()
                remaining_thoughts.append(thought)
                stats["kept"] += 1
        elif new_score < 0.1:
            logger.info("延迟队列重评估: id=%d, old_score=%.3f, new_score=%.3f, decision=discard",
                        thought.id, thought.score, new_score)
            stats["discarded"] += 1
        else:
            logger.info("延迟队列重评估: id=%d, old_score=%.3f, new_score=%.3f, decision=keep",
                        thought.id, thought.score, new_score)
            thought.score = new_score
            thought.retry_count += 1
            thought.next_retry_at = (
                datetime.now() + timedelta(minutes=retry_interval)
            ).isoformat()
            remaining_thoughts.append(thought)
            stats["kept"] += 1

    logger.info("延迟队列重评估完成: stats=%s", stats)

    save_delayed_thoughts(remaining_thoughts)
    return stats
