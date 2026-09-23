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
                            # 支持 Unix 时间戳（float）和 ISO 格式
                            ts = row[0]
                            if isinstance(ts, (int, float)):
                                last_user_dt = datetime.fromtimestamp(float(ts))
                            else:
                                last_user_dt = datetime.fromisoformat(str(ts))
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

            # 计算 1 小时前的 Unix 时间戳
            one_hour_ago = (now.timestamp() - 3600)

            try:
                with state_engine.connect() as conn:
                    row = conn.execute(text(
                        "SELECT COUNT(*), MAX(timestamp) FROM messages "
                        "WHERE role='user' AND timestamp > :one_hour_ago "
                        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
                    ), {"one_hour_ago": one_hour_ago}).fetchone()
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

            # 模板情绪变量：情绪三轴来自 EmotionState（单一真相源）
            emotion_ctx = PassiveConsciousnessService._build_emotion_context()
            # 注入时机顺带：用户回复她的主动消息且冷战中 → 诚意评分（失败不影响主流程）
            try:
                PassiveConsciousnessService.maybe_evaluate_goodwill()
            except Exception as _gw_err:
                logger.debug("诚意评分跳过: %s", _gw_err)

            # 获取天气数据（从 weather.* 命名空间读取配置）
            weather_data = None
            try:
                weather_enabled = ConfigService.get_config(db, "weather.enabled") == "true"
                if weather_enabled:
                    from services.weather_service import WeatherService

                    weather_service = WeatherService()

                    # 使用同步方法调用
                    weather_result = weather_service.get_weather_sync(
                        amap_key=ConfigService.get_config(db, "weather.amap_key") or "",
                        adcode=ConfigService.get_config(db, "weather.adcode") or "370100",
                        cache_ttl=int(ConfigService.get_config(db, "weather.cache_hours") or "4") * 3600,
                        provider=ConfigService.get_config(db, "weather.provider") or "qweather",
                        city=ConfigService.get_config(db, "weather.city") or "",
                        qweather_key=ConfigService.get_config(db, "weather.qweather_key") or "",
                        qweather_geo_url=ConfigService.get_config(db, "weather.qweather_geo_url") or "https://geoapi.qweather.com/v2/city/lookup",
                        qweather_weather_url=ConfigService.get_config(db, "weather.qweather_weather_url") or "https://devapi.qweather.com/v7/weather/now",
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
                # 情绪三轴（模板占位符 {valence}/{arousal}/{social}）：只读，来自 EmotionState
                "valence": emotion_ctx["valence"],
                "arousal": emotion_ctx["arousal"],
                "social": emotion_ctx["social"],
                "label": emotion_ctx["label"],
                # 冲突修复语气词（模板占位符 {mood_mode}）
                "mood_mode": emotion_ctx.get("mood_mode", "温柔"),
                "weather": weather_data,
            }
        finally:
            db.close()

    @staticmethod
    def _build_emotion_context() -> Dict[str, Any]:
        """
        构建模板情绪变量（单一真相源）。

        情绪三轴 valence/arousal/social 与情绪 label 只从 EmotionState 读取，
        不再从关系维度/内心六维取值。模板占位符名字保持不变。
        另附 {mood_mode} 语气词（冲突修复状态 → 中文语气），供模板选用。
        """
        st = get_emotion_state().to_dict()
        return {
            "valence": st.get("valence", 0.5),
            "arousal": st.get("arousal", 0.3),
            # EmotionState 内部字段为 social_need，模板占位符仍为 {social}
            "social": st.get("social", st.get("social_need", 0.3)),
            "label": st.get("label", st.get("dominant", "calm")),
            "mood_mode": PassiveConsciousnessService._get_mood_mode_label(),
        }

    # 冲突修复 mode → 中文语气词（模板 {mood_mode} 占位符）
    MOOD_MODE_LABELS = {
        "normal": "温柔",
        "upset": "有点赌气",
        "cold": "冷淡硬句",
        "softening": "嘴硬心软",
        "reconciled": "回暖撒娇",
        "grudge": "淡淡的",
        "self_at_fault": "心虚讨好",
    }

    @staticmethod
    def _load_repair_state() -> Dict[str, Any]:
        """读取冲突修复状态单例（configs 键 active_consciousness.repair_state）"""
        state = {"mode": "normal", "points": 0.0, "started_at": None,
                 "trigger_event": None, "goodwill_history": []}
        try:
            db = ActiveSession()
            try:
                raw = ConfigService.get_config(db, "active_consciousness.repair_state")
            finally:
                db.close()
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    state.update(parsed)
        except Exception as e:
            logger.debug("读取 repair_state 失败，使用默认: %s", e)
        return state

    @staticmethod
    def _save_repair_state(state: Dict[str, Any]) -> None:
        """写回冲突修复状态单例"""
        db = ActiveSession()
        try:
            ConfigService.set_config(
                db, "active_consciousness.repair_state",
                json.dumps(state, ensure_ascii=False)
            )
        finally:
            db.close()

    @staticmethod
    def _get_mood_mode_label() -> str:
        """当前 repair mode → 中文语气词（模板 {mood_mode}）"""
        try:
            mode = PassiveConsciousnessService._load_repair_state().get("mode", "normal")
            return PassiveConsciousnessService.MOOD_MODE_LABELS.get(mode, "温柔")
        except Exception:
            return "温柔"

    @staticmethod
    def maybe_evaluate_goodwill(user_msg: str = "") -> Optional[Dict[str, Any]]:
        """注入时机顺带：用户回复她的主动消息且冷战中 → 诚意评分 → transition → 更新 repair_state。

        触发条件：mode 不是 normal，且（state.db 里）上一条是她的主动消息且距今 <2h。
        失败不影响注入主流程（内部 try/except 全包）。
        """
        try:
            from services.repair_service import evaluate_goodwill, transition

            state = PassiveConsciousnessService._load_repair_state()
            mode = state.get("mode", "normal")
            if mode == "normal":
                return None

            # 查最近消息：确认上一条是她的主动消息且距今 <2h
            now = datetime.now()
            rows = []
            try:
                with state_engine.connect() as conn:
                    rows = conn.execute(text(
                        "SELECT role, content, timestamp FROM messages WHERE session_id IN "
                        "(SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL) "
                        "ORDER BY timestamp DESC LIMIT 5"
                    )).fetchall()
            except Exception as e:
                logger.debug("查询消息失败，跳过诚意评分: %s", e)
                return None

            def _ts(v):
                try:
                    if isinstance(v, (int, float)):
                        return datetime.fromtimestamp(float(v))
                    s = str(v)
                    if s.replace('.', '').isdigit():
                        return datetime.fromtimestamp(float(s))
                    return datetime.fromisoformat(s)
                except Exception:
                    return None

            msgs = [{"role": r[0], "content": (r[1] or ""), "ts": _ts(r[2])} for r in (rows or [])]
            # 最新一条应是用户消息（注入时机 = 用户消息到达）
            if not msgs or msgs[0].get("role") != "user":
                return None
            current_user_msg = user_msg or msgs[0].get("content") or ""
            if not current_user_msg.strip():
                return None
            # 上一条须是她的主动消息（[凯莉% 前缀）且距今 <2h
            if len(msgs) < 2:
                return None
            prev = msgs[1]
            prev_content = prev.get("content") or ""
            if prev.get("role") != "assistant" or not prev_content.startswith("[凯莉"):
                return None
            if not prev.get("ts") or (now - prev["ts"]).total_seconds() >= 2 * 3600:
                return None

            # hours_since_upset 从 started_at 算
            hours_since_upset = 0.0
            started_at = state.get("started_at")
            if started_at:
                try:
                    hours_since_upset = max(
                        0.0, (now - datetime.fromisoformat(started_at)).total_seconds() / 3600
                    )
                except Exception:
                    hours_since_upset = 0.0

            recent_goodwills = state.get("goodwill_history") or []
            # 只存用户示好文本，便于 evaluate_goodwill 做重复话术比对
            recent_texts = [
                (g.get("text") if isinstance(g, dict) else str(g))
                for g in recent_goodwills[-5:]
            ]
            result = evaluate_goodwill(current_user_msg, recent_texts, hours_since_upset=hours_since_upset)

            # 更新 state：points 累计、mode 变化、goodwills 追加
            state["points"] = float(state.get("points", 0.0) or 0.0) + float(result.get("points", 0.0) or 0.0)
            new_mode = transition(mode, {"type": "goodwill", "points": result.get("points", 0.0)}, state=state)
            state["mode"] = new_mode
            history = list(state.get("goodwill_history") or [])
            history.append({
                "text": current_user_msg[:100],
                "sincerity": result.get("sincerity", 0),
                "points": result.get("points", 0.0),
                "at": now.isoformat(),
            })
            state["goodwill_history"] = history[-20:]
            PassiveConsciousnessService._save_repair_state(state)
            logger.info("诚意评分: sincerity=%s repeat=%s points=%.2f → mode=%s",
                        result.get("sincerity"), result.get("is_repeat"),
                        result.get("points", 0.0), new_mode)
            return result
        except Exception as e:
            logger.warning("诚意评分失败（不影响注入主流程）: %s", e)
            return None

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
# 情绪单一真相源：模板情绪变量只从 EmotionState 读取
from services.active_consciousness_service import get_emotion_state
