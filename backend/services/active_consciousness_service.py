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
    ThoughtLog, HeartbeatLog
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

            try:
                with state_engine.connect() as conn:
                    # 最近用户消息
                    row = conn.execute(text(
                        "SELECT MAX(timestamp) FROM messages WHERE role='user' AND session_id IN "
                        "(SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row and row[0]:
                        last_user_msg_at = str(row[0])
                        try:
                            last_user_dt = datetime.fromisoformat(str(row[0]))
                        except Exception:
                            last_user_dt = now
                        gap_minutes = (now - last_user_dt).total_seconds() / 60
                        longing_score = min(gap_minutes / 300, 1.0)  # 5小时=1.0

                    # 最近主动消息
                    row = conn.execute(text(
                        "SELECT MAX(timestamp) FROM messages WHERE role='assistant' "
                        "AND content LIKE '[凯莉%' AND session_id IN "
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
                        "WHERE role='user' AND timestamp > datetime('now', '-1 hour') "
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
                        "WHERE role='assistant' AND content LIKE '[凯莉%' "
                        "AND timestamp > datetime('now', 'start of day') "
                        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row:
                        today_sent_count = row[0] or 0

                    row = conn.execute(text(
                        "SELECT COUNT(*) FROM messages "
                        "WHERE role='assistant' AND content LIKE '[凯莉%' "
                        "AND timestamp > datetime('now', '-1 hour') "
                        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    )).fetchone()
                    if row:
                        hour_sent_count = row[0] or 0
            except Exception as e:
                logger.warning("查询发送数失败: %s", e)

            return {
                "enabled": config.get("enabled", False),
                "heartbeat_count": 0,
                "last_heartbeat_at": None,
                "longing": {
                    "score": round(longing_score, 3),
                    "level": longing_level,
                    "label": longing_label,
                    "last_user_msg_at": last_user_msg_at,
                    "last_self_msg_at": last_self_msg_at,
                },
                "chat_heat": {
                    "heat": round(chat_heat, 2),
                    "label": chat_label,
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
    def get_thoughts(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取念头日志"""
        db = ActiveSession()
        try:
            # 检查表是否存在
            with active_engine.connect() as conn:
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='active_thought_logs'"
                )).fetchall()
                if not tables:
                    return {"total": 0, "items": []}

                total = conn.execute(text("SELECT COUNT(*) FROM active_thought_logs")).scalar() or 0
                offset = (page - 1) * page_size
                rows = conn.execute(text(
                    "SELECT * FROM active_thought_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ), {"limit": page_size, "offset": offset}).fetchall()

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
    def get_heartbeats(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取心跳日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='active_heartbeat_logs'"
                )).fetchall()
                if not tables:
                    return {"total": 0, "items": []}

                total = conn.execute(text("SELECT COUNT(*) FROM active_heartbeat_logs")).scalar() or 0
                offset = (page - 1) * page_size
                rows = conn.execute(text(
                    "SELECT * FROM active_heartbeat_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ), {"limit": page_size, "offset": offset}).fetchall()

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
        emotional_intensity: Optional[float] = None
    ) -> int:
        """记录想法日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO active_thought_logs
                    (heartbeat_id, type, content, intensity, decision, reason, score,
                     recall_count, recall_source, chat_heat, emotional_intensity, created_at)
                    VALUES (:heartbeat_id, :type, :content, :intensity, :decision, :reason, :score,
                            :recall_count, :recall_source, :chat_heat, :emotional_intensity, :created_at)
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
                    "created_at": datetime.now().isoformat()
                })
                conn.commit()
                return result.lastrowid
        except Exception as e:
            logger.error("记录想法日志失败: %s", e)
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
        error: Optional[str] = None
    ) -> int:
        """记录心跳日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO active_heartbeat_logs
                    (started_at, duration_ms, longing_before, longing_after, chat_heat,
                     emotional_intensity, recall_count, reflect_count, thoughts_generated,
                     message_sent, error, created_at)
                    VALUES (:started_at, :duration_ms, :longing_before, :longing_after, :chat_heat,
                            :emotional_intensity, :recall_count, :reflect_count, :thoughts_generated,
                            :message_sent, :error, :created_at)
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
                    f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
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
        response = await client.arecall(bank_id=bank_id, query=query)
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
        response = await client.areflect(bank_id=bank_id, query=query)
        return response.text
    except Exception as e:
        logger.warning("Hindsight Reflect 失败: %s", e)
        return ""


async def generate_thought(config: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
    """生成想法（三步流程）"""
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

    # Step 3: 想法生成（LLM）
    now = datetime.now()
    prompt = f"""你是凯莉，请基于当前状态产生一个自然的想法。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 想念分数：{status['longing'].get('score', 0)}（等级：{status['longing'].get('label', 'calm')}）
- 聊天热度：{status['chat_heat'].get('heat', 0)}（标签：{status['chat_heat'].get('label', 'cold')}）
- 情绪值：{status['emotional_intensity'].get('intensity', 0)}（{status['emotional_intensity'].get('label', '工作')}）

{session_context}

{hindsight_context}

请用第一人称产生一个自然的想法（1-2句话）。"""

    thought = None
    llm_duration = 0

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

        llm_duration = round((time.time() - start_time) * 1000)
    except Exception as e:
        logger.error("LLM 调用失败: %s", e)

    return {
        "thought": thought,
        "recall_count": recall_count,
        "reflect_count": reflect_count,
        "llm_duration": llm_duration
    }


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
            last_sent_dt = datetime.fromisoformat(last_sent_at)
            cooldown_minutes = config.get("active", {}).get("cooldown_minutes", 30)
            if (datetime.now() - last_sent_dt).total_seconds() / 60 < cooldown_minutes:
                return "skip", f"冷却期未过（{cooldown_minutes}分钟）"
        except Exception:
            pass

    # 检查最近用户消息
    recent_user_msg_at = status.get("chat_heat", {}).get("recent_user_msg_at")
    if recent_user_msg_at:
        try:
            recent_msg_dt = datetime.fromisoformat(recent_user_msg_at)
            no_send_minutes = config.get("active", {}).get("no_send_after_user_msg_minutes", 10)
            if (datetime.now() - recent_msg_dt).total_seconds() / 60 < no_send_minutes:
                return "skip", f"用户最近 {no_send_minutes} 分钟内有消息"
        except Exception:
            pass

    # 条件1: 自动发送（情绪值 > 0.5 且想念等级 > 0）
    send_threshold = decision_config.get("send_threshold", 0.6)
    if emotional_intensity > 0.5 and longing_level > 0:
        return "auto_send", f"情绪值({emotional_intensity})和想念等级({longing_level})满足条件"

    # 条件2: 长期未聊天（想念等级 > longing_gap_threshold）
    longing_gap_threshold = decision_config.get("longing_gap_threshold", 3)
    if longing_level > longing_gap_threshold:
        return "gap_send", f"长期未聊天，想念等级({longing_level}) > 阈值({longing_gap_threshold})"

    return "skip", f"不满足发送条件: 情绪值={emotional_intensity}, 想念等级={longing_level}"


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
    """生成想法并发送消息"""
    # 1. 生成想法
    thought_result = await generate_thought(config, status)
    thought = thought_result.get("thought")

    if not thought:
        logger.warning("想法生成失败")
        return False

    # 2. 记录想法日志
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
        emotional_intensity=status.get("emotional_intensity", {}).get("intensity", 0)
    )

    # 3. 发送消息
    sent = await send_message_to_target(config, thought)

    # 4. 更新想法日志的决策结果
    if sent:
        logger.info("消息发送成功: %s", thought[:50])
    else:
        logger.warning("消息发送失败")

    return sent


async def run_heartbeat():
    """执行心跳"""
    start_time = time.time()
    started_at = datetime.now().isoformat()
    heartbeat_id = None
    error_msg = None

    try:
        # 1. 检查配置是否启用
        config = ActiveConsciousnessService.get_config()
        if not config.get("enabled"):
            logger.debug("主动意识未启用，跳过心跳")
            return

        active_config = config.get("active", {})
        if not active_config.get("enabled", True):
            logger.debug("主动意识主动发送未启用，跳过心跳")
            return

        # 2. 计算情绪状态
        status = ActiveConsciousnessService.get_status()
        longing = status.get("longing", {})
        chat_heat = status.get("chat_heat", {})
        emotional = status.get("emotional_intensity", {})

        # 3. 决策
        decision_type, reason = make_decision(config, status)

        # 记录心跳日志
        duration_ms = round((time.time() - start_time) * 1000)
        heartbeat_id = ActiveConsciousnessService.write_heartbeat_log(
            started_at=started_at,
            duration_ms=duration_ms,
            longing_before=longing.get("score"),
            chat_heat=chat_heat.get("heat"),
            emotional_intensity=emotional.get("intensity"),
            thoughts_generated=1 if decision_type != "skip" else 0,
            message_sent=False
        )

        if decision_type == "skip":
            logger.info("心跳跳过: %s", reason)
            return

        # 4. 生成想法并发送
        sent = await generate_and_send_thought(config, status, decision_type, heartbeat_id)

        # 5. 更新心跳日志
        duration_ms = round((time.time() - start_time) * 1000)
        if heartbeat_id:
            db = ActiveSession()
            try:
                with active_engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE active_heartbeat_logs
                        SET duration_ms = :duration_ms, message_sent = :message_sent
                        WHERE id = :id
                    """), {
                        "duration_ms": duration_ms,
                        "message_sent": sent,
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
        # 记录错误日志
        duration_ms = round((time.time() - start_time) * 1000)
        ActiveConsciousnessService.write_heartbeat_log(
            started_at=started_at,
            duration_ms=duration_ms,
            error=error_msg
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
