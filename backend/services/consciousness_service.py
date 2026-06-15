"""
自主意识服务 — 配置读写 + 状态查询 + 日志查询
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import text

from models.database import ActiveSession, state_engine, get_state_metadata
from models.consciousness import (
    ConsciousnessConfig, ConsciousnessStatus, LongingState, ChatHeat,
    EmotionalIntensity, ThoughtLog, HeartbeatLog, ChatRecord
)

logger = logging.getLogger("hermes.consciousness")

# 配置 key 前缀
PREFIX = "consciousness."

# 默认配置（扁平 key → 默认值）
_DEFAULTS = {
    "consciousness.enabled": "false",
    "consciousness.llm.mode": "hermes",
    "consciousness.llm.provider": "openai",
    "consciousness.llm.model": "deepseek-chat",
    "consciousness.llm.api_key": "",
    "consciousness.llm.base_url": "",
    "consciousness.passive.enabled": "true",
    "consciousness.passive.inject_emotion": "true",
    "consciousness.passive.inject_heat": "true",
    "consciousness.passive.inject_memory": "true",
    "consciousness.passive.inject_thought": "true",
    "consciousness.passive.thought_max_chars": "200",
    "consciousness.passive.vibe_max_chars": "50",
    "consciousness.passive.inject_tag": "[CONSCIOUSNESS_CONTEXT]",
    "consciousness.passive.time_format": "%H:%M",
    "consciousness.active.enabled": "true",
    "consciousness.active.heartbeat_interval": "600",
    "consciousness.active.send_tag": "[凯莉主动发送]",
    "consciousness.active.time_format": "%H:%M",
    "consciousness.active.no_send_after_user_msg_minutes": "10",
    "consciousness.active.no_send_while_heat_above": "0.5",
    "consciousness.active.no_send_while_vibe_below": "0.3",
    "consciousness.session.sources": '["weixin"]',
    "consciousness.session.time_range_hours": "24",
    "consciousness.session.max_messages_per_session": "15",
    "consciousness.session.filter_tool_messages": "true",
    "consciousness.decision.send_threshold": "0.6",
    "consciousness.decision.delay_threshold": "0.3",
    "consciousness.decision.memory_threshold": "0.1",
    "consciousness.decision.max_per_hour": "2",
    "consciousness.decision.max_per_day": "5",
    "consciousness.hindsight.enabled": "true",
    "consciousness.hindsight.recall_limit": "5",
    "consciousness.hindsight.reflect_enabled": "true",
    "consciousness.weather.enabled": "false",
    "consciousness.weather.adcode": "370100",
    "consciousness.weather.amap_key": "",
    "consciousness.weather.cache_ttl": "600",
    "consciousness.notify.platform": "weixin",
    "consciousness.notify.chat_id": "",
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


class ConsciousnessService:
    """自主意识服务"""

    # ============ 配置 ============

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取自主意识配置"""
        db = ActiveSession()
        try:
            result = {}
            for key, default in _DEFAULTS.items():
                value = ConfigService.get_config(db, key)
                result[key] = value if value is not None else default
            return ConsciousnessService._flat_to_nested(result)
        finally:
            db.close()

    @staticmethod
    def update_config(config: Dict[str, Any]):
        """更新自主意识配置"""
        db = ActiveSession()
        try:
            flat = ConsciousnessService._nested_to_flat(config)
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
                result.update(ConsciousnessService._nested_to_flat(value, full_key + "."))
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
        """获取自主意识状态"""
        db = ActiveSession()
        try:
            config = ConsciousnessService.get_config()
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
                val = ConfigService.get_config(db, "consciousness.current.emotional_intensity")
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

            # 活跃 session 数
            active_sessions = 0
            try:
                with state_engine.connect() as conn:
                    row = conn.execute(text(
                        "SELECT COUNT(*) FROM sessions WHERE ended_at IS NULL"
                    )).fetchone()
                    if row:
                        active_sessions = row[0] or 0
            except Exception:
                pass

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
                    "label": ConsciousnessService._intensity_label(emotional_intensity),
                },
                "active_sessions": active_sessions,
                "today_sent_count": today_sent_count,
                "hour_sent_count": hour_sent_count,
                "last_sent_at": last_self_msg_at,
            }
        finally:
            db.close()

    @staticmethod
    def _intensity_label(value: float) -> str:
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
            with state_engine.connect() as conn:
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='thought_logs'"
                )).fetchall()
                if not tables:
                    return {"total": 0, "items": []}

                total = conn.execute(text("SELECT COUNT(*) FROM thought_logs")).scalar() or 0
                offset = (page - 1) * page_size
                rows = conn.execute(text(
                    "SELECT * FROM thought_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
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
            with state_engine.connect() as conn:
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='heartbeat_logs'"
                )).fetchall()
                if not tables:
                    return {"total": 0, "items": []}

                total = conn.execute(text("SELECT COUNT(*) FROM heartbeat_logs")).scalar() or 0
                offset = (page - 1) * page_size
                rows = conn.execute(text(
                    "SELECT * FROM heartbeat_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
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
    def get_chats(limit: int = 50) -> Dict[str, Any]:
        """获取最近聊天记录"""
        db = ActiveSession()
        try:
            with state_engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT m.id, m.session_id, s.source, m.role, m.content, m.timestamp "
                    "FROM messages m "
                    "JOIN sessions s ON m.session_id = s.id "
                    "WHERE s.source = 'weixin' AND s.ended_at IS NULL "
                    "AND m.role IN ('user', 'assistant') "
                    "ORDER BY m.timestamp DESC LIMIT :limit"
                ), {"limit": limit}).fetchall()

                items = []
                for row in rows:
                    d = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                    items.append(d)

                return {"total": len(items), "items": items}
        except Exception as e:
            logger.error("查询聊天记录失败: %s", e)
            return {"total": 0, "items": [], "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def delete_thought(thought_id: int) -> bool:
        """删除念头"""
        db = ActiveSession()
        try:
            with state_engine.connect() as conn:
                conn.execute(text("DELETE FROM thought_logs WHERE id = :id"), {"id": thought_id})
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
            with state_engine.connect() as conn:
                conn.execute(text("DELETE FROM heartbeat_logs WHERE id = :id"), {"id": heartbeat_id})
                conn.commit()
            return True
        except Exception as e:
            logger.error("删除心跳日志失败: %s", e)
            return False
        finally:
            db.close()


# 导入 ConfigService（避免循环导入）
from services.config_service import ConfigService
