"""
被动意识服务 — 配置读写 + 状态查询 + 聊天记录查询
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import text

from models.database import ActiveSession, state_engine
from models.passive_consciousness import (
    PassiveConsciousnessConfig, PassiveConsciousnessStatus,
    LongingState, ChatHeat, EmotionalIntensity, ChatRecord
)

logger = logging.getLogger("hermes.passive_consciousness")

# 配置 key 前缀
PREFIX = "passive_consciousness."

# 延迟导入 DEFAULT_TEMPLATES（避免循环导入）
def _get_default_templates_json():
    from services.template_service import DEFAULT_TEMPLATES
    return json.dumps(DEFAULT_TEMPLATES, ensure_ascii=False)

# 默认配置（扁平 key → 默认值）
_DEFAULTS = {
    "passive_consciousness.enabled": "false",
    "passive_consciousness.llm.mode": "hermes",
    "passive_consciousness.llm.provider": "openai",
    "passive_consciousness.llm.model": "deepseek-chat",
    "passive_consciousness.llm.api_key": "",
    "passive_consciousness.llm.base_url": "",
    "passive_consciousness.passive.enabled": "true",
    "passive_consciousness.passive.inject_emotion": "true",
    "passive_consciousness.passive.inject_heat": "true",
    "passive_consciousness.passive.inject_memory": "true",
    "passive_consciousness.passive.inject_thought": "true",
    "passive_consciousness.passive.thought_max_chars": "200",
    "passive_consciousness.passive.vibe_max_chars": "50",
    "passive_consciousness.passive.inject_tag": "[CONSCIOUSNESS_CONTEXT]",
    "passive_consciousness.passive.time_format": "%H:%M",
    "passive_consciousness.session.sources": '["weixin"]',
    "passive_consciousness.session.time_range_hours": "24",
    "passive_consciousness.session.max_messages_per_session": "15",
    "passive_consciousness.session.filter_tool_messages": "true",
    "passive_consciousness.hindsight.enabled": "true",
    "passive_consciousness.hindsight.recall_limit": "5",
    "passive_consciousness.hindsight.reflect_enabled": "true",
    "passive_consciousness.weather.enabled": "false",
    "passive_consciousness.weather.provider": "qweather",
    "passive_consciousness.weather.city": "北京",
    "passive_consciousness.weather.cache_hours": "4",
    "passive_consciousness.weather.amap_key": "",
    "passive_consciousness.weather.qweather_key": "",
    "passive_consciousness.weather.qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
    "passive_consciousness.weather.qweather_weather_url": "https://devapi.qweather.com/v7/weather/now",
    "passive_consciousness.platforms.enabled": "false",
    "passive_consciousness.platforms.whitelist": '["weixin"]',
    "passive_consciousness.templates.list": _get_default_templates_json(),
    "passive_consciousness.templates.active_id": "default",
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


class PassiveConsciousnessService:
    """被动意识服务"""

    # ============ 配置 ============

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取被动意识配置"""
        db = ActiveSession()
        try:
            result = {}
            for key, default in _DEFAULTS.items():
                value = ConfigService.get_config(db, key)
                result[key] = value if value is not None else default
            return PassiveConsciousnessService._flat_to_nested(result)
        finally:
            db.close()

    @staticmethod
    def update_config(config: Dict[str, Any]):
        """更新被动意识配置"""
        db = ActiveSession()
        try:
            flat = PassiveConsciousnessService._nested_to_flat(config)
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
                result.update(PassiveConsciousnessService._nested_to_flat(value, full_key + "."))
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
        """获取被动意识状态"""
        db = ActiveSession()
        try:
            config = PassiveConsciousnessService.get_config()
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
                val = ConfigService.get_config(db, "passive_consciousness.current.emotional_intensity")
                if val:
                    emotional_intensity = float(val)
            except Exception:
                pass

            # 获取天气数据
            weather_data = None
            try:
                weather_config = config.get("weather", {})
                if weather_config.get("enabled"):
                    from services.weather_service import WeatherService

                    weather_service = WeatherService()

                    # 使用同步方法调用
                    weather_result = weather_service.get_weather_sync(
                        amap_key=weather_config.get("amap_key", ""),
                        adcode=weather_config.get("adcode", "370100"),
                        cache_ttl=int(weather_config.get("cache_hours", 4)) * 3600,
                        provider=weather_config.get("provider", "qweather"),
                        city=weather_config.get("city", ""),
                        qweather_key=weather_config.get("qweather_key", ""),
                        qweather_geo_url=weather_config.get("qweather_geo_url", "https://geoapi.qweather.com/v2/city/lookup"),
                        qweather_weather_url=weather_config.get("qweather_weather_url", "https://devapi.qweather.com/v7/weather/now"),
                    )

                    if weather_result and weather_result.get("success"):
                        current = weather_result.get("current", {})
                        weather_data = {
                            "city": weather_result.get("city", ""),
                            "weather": current.get("weather", ""),
                            "temperature": current.get("temp", ""),
                            "humidity": current.get("humidity", ""),
                            "wind_dir": current.get("winddirection", ""),
                        }
            except Exception as e:
                logger.warning("获取天气数据失败: %s", e)

            return {
                "enabled": config.get("enabled", False),
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
                    "label": PassiveConsciousnessService._intensity_label(emotional_intensity),
                },
                "weather": weather_data,
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


# 导入 ConfigService（避免循环导入）
from services.config_service import ConfigService
