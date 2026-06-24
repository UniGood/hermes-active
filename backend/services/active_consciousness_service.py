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


async def call_llm_with_fallback(
    llm_func,
    prompt: str,
    fallback_value: Any,
    timeout: float = 30.0
) -> tuple[Any, bool]:
    """
    调用 LLM 并在失败时返回 fallback 值

    Args:
        llm_func: LLM 调用函数（接收 prompt 参数）
        prompt: 提示词
        fallback_value: 失败时的默认值
        timeout: 超时时间（秒）

    Returns:
        (result, success): 结果和是否成功
    """
    try:
        result = await asyncio.wait_for(llm_func(prompt), timeout=timeout)
        if result is None:
            logger.warning("LLM 返回 None，使用 fallback")
            return fallback_value, False
        return result, True
    except TimeoutError:
        logger.error("LLM 调用超时 (%.1f 秒)", timeout)
        return fallback_value, False
    except Exception as e:
        logger.error("LLM 调用异常: %s", e)
        return fallback_value, False

# 全局心跳调度器实例
heartbeat_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 全局 Hindsight 客户端实例
_hindsight_client: Optional[Hindsight] = None


def get_effective_llm_config(config: Dict[str, Any], llm_type: str = "thought") -> Dict[str, Any]:
    """获取有效的 LLM 配置（专用配置为空时回退到通用 llm）"""
    fallback = config.get("llm", {})
    specific = config.get(f"{llm_type}_llm", {})
    # 如果专用配置的 mode 为空，说明未配置，回退到通用
    if not specific.get("mode"):
        return fallback
    return specific


def get_hindsight_client(base_url: str = "http://localhost:8888", timeout: float = 30.0) -> Hindsight:
    """获取 Hindsight 客户端实例（懒加载，base_url 或 timeout 变化时重建）"""
    global _hindsight_client
    if _hindsight_client is not None:
        # 检查参数是否变化，变化则重建
        if getattr(_hindsight_client, '_custom_base_url', None) != base_url or \
           getattr(_hindsight_client, '_custom_timeout', None) != timeout:
            _hindsight_client = None
    if _hindsight_client is None:
        _hindsight_client = Hindsight(base_url=base_url, timeout=timeout)
        _hindsight_client._custom_base_url = base_url
        _hindsight_client._custom_timeout = timeout
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


async def reset_hindsight_client():
    """重置 Hindsight 客户端（用于重连）"""
    global _hindsight_client
    if _hindsight_client is not None:
        try:
            await _hindsight_client.aclose()
        except Exception:
            pass
        _hindsight_client = None
    logger.info("Hindsight 客户端已重置")

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
    # 情绪评估专用 LLM（为空时回退到 llm）
    "active_consciousness.emotion_llm.mode": "",
    "active_consciousness.emotion_llm.provider": "",
    "active_consciousness.emotion_llm.model": "",
    "active_consciousness.emotion_llm.api_key": "",
    "active_consciousness.emotion_llm.base_url": "",
    # 念头生成专用 LLM（为空时回退到 llm）
    "active_consciousness.thought_llm.mode": "",
    "active_consciousness.thought_llm.provider": "",
    "active_consciousness.thought_llm.model": "",
    "active_consciousness.thought_llm.api_key": "",
    "active_consciousness.thought_llm.base_url": "",
    "active_consciousness.active.enabled": "true",
    "active_consciousness.active.heartbeat_interval": "600",
    "active_consciousness.active.send_tag": "[凯莉主动发送]",
    "active_consciousness.active.time_format": "%H:%M",
    "active_consciousness.active.no_send_after_user_msg_minutes": "5",
    "active_consciousness.active.no_send_while_heat_above": "1.0",
    "active_consciousness.active.no_send_while_vibe_below": "0.15",
    "active_consciousness.active.cooldown_minutes": "30",
    "active_consciousness.session.sources": '["weixin"]',
    "active_consciousness.session.max_messages_per_session": "15",
    "active_consciousness.session.filter_tool_messages": "true",
    "active_consciousness.decision.send_threshold": "0.35",
    "active_consciousness.decision.memory_threshold": "0.05",
    "active_consciousness.decision.max_per_hour": "2",
    "active_consciousness.decision.max_per_day": "5",
    "active_consciousness.decision.longing_gap_threshold": "3",
    "active_consciousness.hindsight.enabled": "true",
    "active_consciousness.hindsight.base_url": "http://localhost:8888",
    "active_consciousness.hindsight.bank_id": "hermes",
    "active_consciousness.hindsight.store.bank_id": "hermes-active",
    "active_consciousness.hindsight.recall_limit": "5",
    "active_consciousness.hindsight.reflect_enabled": "true",
    "active_consciousness.hindsight.timeout": "30",
    "active_consciousness.notify.platform": "weixin",
    "active_consciousness.notify.chat_id": "",

    # 天气配置（共享）
    "active_consciousness.weather.enabled": "false",
    "active_consciousness.weather.amap_key": "",
    "active_consciousness.weather.adcode": "370100",
    "active_consciousness.weather.cache_ttl": "3600",
    "active_consciousness.weather.temp_change_threshold": "5.0",

    # 情绪演化
    "active_consciousness.emotion.decay_rate": "0.02",
    "active_consciousness.emotion.social_need_growth": "0.01",
    "active_consciousness.emotion.valence_regression": "0.1",
    "active_consciousness.emotion.weight_evolved": "0.4",
    "active_consciousness.emotion.weight_llm": "0.6",

    # 时间窗口
    "active_consciousness.time.enabled": "true",

    # 延迟发送
    "active_consciousness.delay.enabled": "true",
    "active_consciousness.delay.max_retry": "3",
    "active_consciousness.delay.retry_interval_minutes": "30",
    "active_consciousness.delay.max_queue_size": "10",
    "active_consciousness.delay.max_age_hours": "4",

    # 念头存储
    "active_consciousness.thought.retain_enabled": "false",
    "active_consciousness.thought.retain_threshold": "0.5",

    # ThoughtEngine 配置
    "active_consciousness.thought_engine.enabled": "true",
    "active_consciousness.thought_engine.max_tokens": "300",
    "active_consciousness.thought_engine.temperature": "0.9",
    "active_consciousness.thought_engine.prompt_conversation_limit": "30",
    "active_consciousness.thought_engine.prompt_max_chars": "300",

    # 上下文收集配置
    "active_consciousness.context.conversation_limit": "100",
    "active_consciousness.context.conversation_max_chars": "2000",
    "active_consciousness.context.time_range_days": "7",
    "active_consciousness.context.memory_limit": "5",
    "active_consciousness.context.memory_enabled": "true",
    "active_consciousness.context.weather_enabled": "false",

    # 念头生成提示词模板
    "active_consciousness.prompts.thought_generation": """你是凯莉，曹凡的 AI 朋友。你们认识很久了，你了解他的生活习惯、工作状态、兴趣爱好。

{persona}

【最近对话】
{session_context}

【你记得的事情】
{hindsight_context}

【现在】
{time}
{emotion_display}

想到曹凡了吗？如果你想联系他，说你想说什么。
如果没想到，回复 'SKIP'。
直接说，不要解释。""",

    "active_consciousness.prompts.emotion_evaluation": """你是凯莉，请评估当前的情绪状态。

当前状态：
- 时间：{time}
- 想念分数：{longing_score}（等级：{longing_label}）
- 聊天热度：{chat_heat}（标签：{chat_label}）
- 沉默时长：{silence_minutes} 分钟

最近的对话：
{context}

请评估你当前的情绪状态，返回 JSON 格式：
{{
  "valence": 0.0-1.0（情感效价，0=消极，1=积极），
  "arousal": 0.0-1.0（唤醒度，0=平静，1=激动），
  "social_need": 0.0-1.0（社交需求，0=不需要，1=非常想），
  "dominant": "calm/content/happy/longing/missing/yearning/anxious/bored/concerned"
}}

只返回 JSON，不要解释。""",

    # 想念等级阈值配置（JSON 数组：[阈值, 等级, 标签]）
    "active_consciousness.levels.longing": '[0.0, 0, "calm"], [0.1, 1, "longing"], [0.3, 2, "missing"], [0.5, 3, "yearning"], [0.7, 4, "anxious"]',

    # 聊天热度等级阈值配置（JSON 数组：[阈值, 标签]）
    "active_consciousness.levels.heat": '[0.0, "cold"], [0.5, "warm"], [1.0, "hot"], [3.0, "fire"]',

    # 想念分数计算：沉默分钟数 / 此值 = 分数（最大1.0）
    "active_consciousness.longing.gap_minutes": "300",
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

# 英文标签 → "中文（英文）" 格式（用于前端展示）
LABEL_DISPLAY = {
    # 想念等级
    "calm": "平静（calm）",
    "longing": "想念（longing）",
    "missing": "思念（missing）",
    "yearning": "渴望（yearning）",
    "anxious": "焦虑（anxious）",
    # 聊天热度
    "cold": "冷清（cold）",
    "warm": "温暖（warm）",
    "hot": "火热（hot）",
    "fire": "沸腾（fire）",
    # 情绪 dominant
    "calm": "平静（calm）",
    "content": "满足（content）",
    "happy": "开心（happy）",
    "longing": "想念（longing）",
    "missing": "思念（missing）",
    "yearning": "渴望（yearning）",
    "anxious": "焦虑（anxious）",
    "bored": "无聊（bored）",
    "concerned": "担忧（concerned）",
}

# 念头类型 → "中文（英文）" 格式
THOUGHT_TYPE_DISPLAY = {
    "time": "时间（time）",
    "silence": "沉默（silence）",
    "assoc": "关联（assoc）",
    "memory": "回忆（memory）",
    "emotion": "情绪（emotion）",
    "env": "环境（env）",
}

# 决策类型 → "中文（英文）" 格式
DECISION_TYPE_DISPLAY = {
    "auto_send": "立即发送（auto_send）",
    "delay_send": "延迟发送（delay_send）",
    "memory": "存为记忆（memory）",
    "skip": "跳过（skip）",
    "pending": "待定（pending）",
}


def get_label_display(label: str) -> str:
    """获取标签的"中文（英文）"展示格式"""
    return LABEL_DISPLAY.get(label, label)


def get_thought_type_display(thought_type: str) -> str:
    """获取念头类型的"中文（英文）"展示格式"""
    return THOUGHT_TYPE_DISPLAY.get(thought_type, thought_type)


def get_decision_display(decision: str) -> str:
    """获取决策类型的"中文（英文）"展示格式"""
    return DECISION_TYPE_DISPLAY.get(decision, decision)


def validate_active_consciousness_config(config: Dict[str, Any]) -> List[str]:
    """
    验证主动意识配置

    Args:
        config: 配置字典

    Returns:
        错误消息列表，空列表表示验证通过
    """
    errors = []
    active = config.get("active", {})
    decision = config.get("decision", {})
    emotion = config.get("emotion", {})
    delay = config.get("delay", {})

    # 验证心跳间隔
    try:
        heartbeat_interval = int(active.get("heartbeat_interval", 600))
    except (ValueError, TypeError):
        errors.append("心跳间隔必须是数字")
        heartbeat_interval = 600
    if heartbeat_interval < 60:
        errors.append("心跳间隔不能小于 60 秒")

    # 验证 no_send_after_user_msg_minutes
    try:
        no_send_minutes = int(active.get("no_send_after_user_msg_minutes", 10))
        if no_send_minutes < 0:
            errors.append("用户消息后不发送时间不能为负数")
    except (ValueError, TypeError):
        errors.append("用户消息后不发送时间必须是数字")

    # 验证阈值关系
    try:
        send_threshold = float(decision.get("send_threshold", 0.6))
    except (ValueError, TypeError):
        errors.append("发送阈值必须是数字")
        send_threshold = 0.6

    try:
        memory_threshold = float(decision.get("memory_threshold", 0.1))
    except (ValueError, TypeError):
        errors.append("记忆阈值必须是数字")
        memory_threshold = 0.1

    # 验证阈值范围 0-1
    if not (0 <= send_threshold <= 1):
        errors.append("发送阈值必须在 0-1 之间")
    if not (0 <= memory_threshold <= 1):
        errors.append("记忆阈值必须在 0-1 之间")

    # 验证阈值大小关系
    if send_threshold <= memory_threshold:
        errors.append("发送阈值必须大于记忆阈值")

    # 验证 max_per_hour
    try:
        max_per_hour = int(decision.get("max_per_hour", 2))
        if max_per_hour < 1 or max_per_hour > 1000:
            errors.append("每小时最大消息数必须在 1-1000 之间")
    except (ValueError, TypeError):
        errors.append("每小时最大消息数必须是正整数")

    # 验证 max_per_day
    try:
        max_per_day = int(decision.get("max_per_day", 5))
        if max_per_day < 1 or max_per_day > 1000:
            errors.append("每日最大消息数必须在 1-1000 之间")
    except (ValueError, TypeError):
        errors.append("每日最大消息数必须是正整数")

    # 验证情绪衰减率
    try:
        decay_rate = float(emotion.get("decay_rate", 0.02))
        if decay_rate < 0 or decay_rate > 0.1:
            errors.append("情绪衰减率必须在 0-0.1 之间")
    except (ValueError, TypeError):
        errors.append("情绪衰减率必须是数字")

    # 验证延迟队列参数
    try:
        max_age_hours = float(delay.get("max_age_hours", 4))
        if max_age_hours < 1 or max_age_hours > 24:
            errors.append("延迟队列最大存活时间必须在 1-24 小时之间")
    except (ValueError, TypeError):
        errors.append("延迟队列最大存活时间必须是数字")

    return errors


class ActiveConsciousnessService:
    """主动意识服务"""

    # 配置缓存（TTL 60秒）
    _config_cache = None
    _config_cache_ts: float = 0
    _CONFIG_CACHE_TTL: float = 60

    # ============ 配置 ============

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取主动意识配置"""
        now = time.time()
        if (ActiveConsciousnessService._config_cache is not None
                and now - ActiveConsciousnessService._config_cache_ts < ActiveConsciousnessService._CONFIG_CACHE_TTL):
            return ActiveConsciousnessService._config_cache

        db = ActiveSession()
        try:
            result = {}
            for key, default in _DEFAULTS.items():
                value = ConfigService.get_config(db, key)
                result[key] = value if value is not None else default
            nested = ActiveConsciousnessService._flat_to_nested(result)
            ActiveConsciousnessService._config_cache = nested
            ActiveConsciousnessService._config_cache_ts = now
            return nested
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
            # 清除配置缓存
            ActiveConsciousnessService._config_cache = None
            ActiveConsciousnessService._config_cache_ts = 0
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

            # 从配置获取想念分数计算参数
            longing_gap_minutes = int(ConfigService.get_config(db, "active_consciousness.longing.gap_minutes") or "300")

            # 查询想念分数
            longing_score = 0.0
            longing_level = 0
            longing_label = "calm"
            last_user_msg_at = None
            last_self_msg_at = None
            silence_minutes = 0.0

            try:
                # 从配置获取 session 来源
                session_sources = config.get("session", {}).get("sources", ["weixin"])
                sources_placeholders = ", ".join(f"'{s}'" for s in session_sources)

                with state_engine.connect() as conn:
                    # 最近用户消息（查询所有配置的 session 来源，不限制 session 状态）
                    row = conn.execute(text(
                        f"SELECT MAX(timestamp) FROM messages WHERE role='user' AND session_id IN "
                        f"(SELECT id FROM sessions WHERE source IN ({sources_placeholders}))"
                    )).fetchone()
                    if row and row[0]:
                        last_user_msg_at = str(row[0])
                        last_user_dt = _parse_timestamp(row[0]) or now
                        gap_minutes = (now - last_user_dt).total_seconds() / 60
                        silence_minutes = gap_minutes

                    # 查询最近1小时用户消息数（用于衰减计算）
                    reply_count_row = conn.execute(text(
                        f"SELECT COUNT(*) FROM messages WHERE role='user' "
                        f"AND CAST(timestamp AS REAL) > CAST(strftime('%s', 'now', '-1 hour') AS REAL) "
                        f"AND session_id IN (SELECT id FROM sessions WHERE source IN ({sources_placeholders}))"
                    )).fetchone()
                    recent_reply_count = reply_count_row[0] if reply_count_row else 0

                    # 想念分数计算：基础分 × 衰减因子
                    # 基础分：基于累积沉默时间（上限1.0）
                    base_score = min(silence_minutes / longing_gap_minutes, 1.0)
                    # 衰减因子：用户每回复一条消息，衰减10%（最少保留10%）
                    decay_factor = max(0.1, 1.0 - recent_reply_count * 0.1)
                    # 最终分数
                    longing_score = base_score * decay_factor

                    # 最近主动消息
                    row = conn.execute(text(
                        f"SELECT MAX(timestamp) FROM messages WHERE role='assistant' "
                        f"AND session_id IN "
                        f"(SELECT id FROM sessions WHERE source IN ({sources_placeholders}))"
                    )).fetchone()
                    if row and row[0]:
                        last_self_msg_at = str(row[0])
            except Exception as e:
                logger.warning("查询想念分数失败: %s", e)

            # 从配置获取想念等级
            longing_levels_str = ConfigService.get_config(db, "active_consciousness.levels.longing") or ""
            longing_levels = LONGING_LEVELS  # 默认值
            if longing_levels_str:
                try:
                    longing_levels = json.loads(f"[{longing_levels_str}]")
                except json.JSONDecodeError:
                    pass

            # 计算想念等级
            for item in reversed(longing_levels):
                threshold, level, label = item[0], item[1], item[2]
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
                session_sources = config.get("session", {}).get("sources", ["weixin"])
                sources_placeholders = ", ".join(f"'{s}'" for s in session_sources)

                with state_engine.connect() as conn:
                    row = conn.execute(text(
                        f"SELECT COUNT(*), MAX(timestamp) FROM messages "
                        f"WHERE role='user' AND CAST(timestamp AS REAL) > CAST(strftime('%s', 'now', '-1 hour') AS REAL) "
                        f"AND session_id IN (SELECT id FROM sessions WHERE source IN ({sources_placeholders}) AND ended_at IS NULL)"
                    )).fetchone()
                    if row:
                        recent_count = row[0] or 0
                        if row[1]:
                            recent_user_msg_at = str(row[1])
                        recent_hours = 1.0
                        chat_heat = recent_count / max(recent_hours, 0.1)
            except Exception as e:
                logger.warning("查询聊天热度失败: %s", e)

            # 从配置获取热度等级
            heat_levels_str = ConfigService.get_config(db, "active_consciousness.levels.heat") or ""
            heat_levels = HEAT_LEVELS  # 默认值
            if heat_levels_str:
                try:
                    heat_levels = json.loads(f"[{heat_levels_str}]")
                except json.JSONDecodeError:
                    pass

            # 计算热度等级
            chat_level_index = 0
            for idx, item in enumerate(reversed(heat_levels)):
                threshold, label = item[0], item[1]
                if chat_heat >= threshold:
                    chat_label = label
                    chat_level_index = len(heat_levels) - 1 - idx
                    break

            # 情绪值（从 configs 读取，由 LLM 更新）
            emotional_intensity = 0.0
            try:
                val = ConfigService.get_config(db, "active_consciousness.current.emotional_intensity")
                if val:
                    emotional_intensity = float(val)
            except Exception:
                pass

            # 今日发送数（查心跳日志中的 message_sent=1）
            # 数据库 created_at/started_at 存的是北京时间（+8 时区字符串）
            # SQLite 的 datetime('now') 返回 UTC，必须用 'localtime' 修饰才能对齐
            # 同时 created_at 是 'YYYY-MM-DDTHH:MM:SS.fff' 格式，需要用 datetime() 转换才能比较
            today_sent_count = 0
            hour_sent_count = 0
            try:
                with active_engine.connect() as conn:
                    # 今日 = 北京时间今天 00:00
                    row = conn.execute(text(
                        "SELECT COUNT(*) FROM active_heartbeat_logs "
                        "WHERE message_sent = 1 "
                        "AND datetime(created_at) > datetime('now', 'localtime', 'start of day')"
                    )).fetchone()
                    if row:
                        today_sent_count = row[0] or 0

                    # 本小时 = 北京时间过去 1 小时
                    row = conn.execute(text(
                        "SELECT COUNT(*) FROM active_heartbeat_logs "
                        "WHERE message_sent = 1 "
                        "AND datetime(created_at) > datetime('now', 'localtime', '-1 hour')"
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
                        "WHERE created_at > datetime('now', '+8 hours', 'start of day')"
                    )).fetchone()
                    if row:
                        heartbeat_count = row[0] or 0
                        if row[1]:
                            last_heartbeat_at = str(row[1])
            except Exception as e:
                logger.warning("查询心跳统计失败: %s", e)

            # 获取延迟队列数量
            delayed_thoughts = get_delayed_thoughts()
            delayed_count = len(delayed_thoughts)

            # 获取情绪状态
            emotion_state = get_emotion_state()

            # 获取配置信息（用于前端动态计算）
            decision_config = config.get("decision", {})
            active_config = config.get("active", {})
            levels_config = config.get("levels", {})
            
            return {
                "enabled": config.get("enabled", False),
                "heartbeat_count": heartbeat_count,
                "last_heartbeat_at": last_heartbeat_at,
                "longing": {
                    "score": round(longing_score, 3),
                    "level": longing_level,
                    "label": LABEL_CN.get(longing_label, longing_label),
                    "label_display": get_label_display(longing_label),
                    "last_user_msg_at": last_user_msg_at,
                    "last_self_msg_at": last_self_msg_at,
                    "silence_minutes": round(silence_minutes, 1),
                },
                "chat_heat": {
                    "heat": round(chat_heat, 2),
                    "label": LABEL_CN.get(chat_label, chat_label),
                    "label_display": get_label_display(chat_label),
                    "level_index": chat_level_index,
                    "total_levels": len(heat_levels),
                    "recent_count": recent_count,
                    "recent_hours": recent_hours,
                    "recent_user_msg_at": recent_user_msg_at,
                },
                "emotional_intensity": {
                    "intensity": round(emotional_intensity, 3),
                    "label": ActiveConsciousnessService._intensity_label(emotional_intensity),
                },
                "emotion_state": {
                    "valence": round(emotion_state.valence, 3),
                    "arousal": round(emotion_state.arousal, 3),
                    "social_need": round(emotion_state.social_need, 3),
                    "dominant": emotion_state.dominant,
                    "dominant_display": get_label_display(emotion_state.dominant),
                    "intensity": round(emotion_state.intensity(), 3),
                    "updated_at": emotion_state.updated_at,
                },
                "today_sent_count": today_sent_count,
                "hour_sent_count": hour_sent_count,
                "last_sent_at": last_self_msg_at,
                "delayed_count": delayed_count,
                # 配置信息（前端动态计算用）
                "config": {
                    "decision": {
                        "send_threshold": float(decision_config.get("send_threshold", 0.35)),
                        "memory_threshold": float(decision_config.get("memory_threshold", 0.05)),
                        "max_per_hour": int(decision_config.get("max_per_hour", 2)),
                        "max_per_day": int(decision_config.get("max_per_day", 5)),
                    },
                    "active": {
                        "heartbeat_interval": int(active_config.get("heartbeat_interval", 600)),
                        "cooldown_minutes": int(active_config.get("cooldown_minutes", 30)),
                        "no_send_after_user_msg_minutes": int(active_config.get("no_send_after_user_msg_minutes", 5)),
                        "no_send_while_heat_above": float(active_config.get("no_send_while_heat_above", 3.0)),
                    },
                    "longing": {
                        "gap_minutes": int(config.get("longing", {}).get("gap_minutes", 300)),
                    },
                    "levels": {
                        "heat": levels_config.get("heat", ""),
                    },
                },
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
                # 不返回 details 字段以提高性能
                rows = conn.execute(text(
                    f"SELECT id, heartbeat_id, type, content, intensity, decision, reason, score, recall_count, recall_source, chat_heat, emotional_intensity, hindsight_stored, created_at FROM active_thought_logs {where_clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
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
                    f"SELECT id, started_at, duration_ms, longing_before, longing_after, "
                    f"chat_heat, emotional_intensity, recall_count, reflect_count, "
                    f"thoughts_generated, message_sent, error, created_at "
                    f"FROM active_heartbeat_logs {where_clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
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
    def get_heartbeat_detail(heartbeat_id: int) -> Optional[Dict[str, Any]]:
        """获取单条心跳日志详情（含完整 details JSON）"""
        try:
            with active_engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT * FROM active_heartbeat_logs WHERE id = :id"
                ), {"id": heartbeat_id}).fetchone()
                if not row:
                    return None
                d = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                return d
        except Exception as e:
            logger.error("查询心跳详情失败: %s", e)
            return None

    @staticmethod
    def get_thought_detail(thought_id: int) -> Optional[Dict[str, Any]]:
        """获取单条念头日志详情（含完整 details JSON）"""
        try:
            with active_engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT * FROM active_thought_logs WHERE id = :id"
                ), {"id": thought_id}).fetchone()
                if not row:
                    return None
                d = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                return d
        except Exception as e:
            logger.error("查询念头详情失败: %s", e)
            return None

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
        hindsight_stored: bool = False,
        details: Optional[str] = None
    ) -> int:
        """记录念头日志"""
        db = ActiveSession()
        try:
            with active_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO active_thought_logs
                    (heartbeat_id, type, content, intensity, decision, reason, score,
                     recall_count, recall_source, chat_heat, emotional_intensity, hindsight_stored, details, created_at)
                    VALUES (:heartbeat_id, :type, :content, :intensity, :decision, :reason, :score,
                            :recall_count, :recall_source, :chat_heat, :emotional_intensity, :hindsight_stored, :details, :created_at)
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
                    "hindsight_stored": hindsight_stored,
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


def load_hermes_persona() -> str:
    """
    加载 Hermes 人设文件（SOUL.md / MEMORY.md / USER.md）

    优先调用 hermes 公共函数，失败时降级为直接读文件。

    Returns:
        人设文本，用于增强念头生成的个性化
    """
    from pathlib import Path

    hermes_dir = Path.home() / ".hermes"
    persona_parts = []

    # 1. SOUL.md — 优先调用 hermes 公共函数
    soul_content = None
    try:
        import sys
        sys.path.insert(0, str(hermes_dir / 'hermes-agent'))
        from agent.prompt_builder import load_soul_md
        soul_content = load_soul_md()
    except ImportError:
        logger.debug("无法导入 hermes load_soul_md，降级为直接读文件")
    except Exception as e:
        logger.warning("调用 hermes load_soul_md 失败: %s，降级为直接读文件", e)

    # 降级：直接读文件
    if not soul_content:
        soul_path = hermes_dir / "SOUL.md"
        if soul_path.exists():
            try:
                soul_content = soul_path.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.warning("读取 SOUL.md 失败: %s", e)

    if soul_content:
        # 截取关键部分，避免太长
        if len(soul_content) > 2000:
            soul_content = soul_content[:2000] + "\n...(已截断)"
        persona_parts.append(f"## SOUL.md\n{soul_content}")

    # 2. MEMORY.md / USER.md — 优先调用 hermes 公共函数
    memory_content = None
    user_content = None
    try:
        from tools.memory_tool import MemoryStore
        store = MemoryStore()
        store.load_from_disk()
        # 拼接条目
        if store.memory_entries:
            memory_content = "\n".join(store.memory_entries)
        if store.user_entries:
            user_content = "\n".join(store.user_entries)
    except ImportError:
        logger.debug("无法导入 hermes MemoryStore，降级为直接读文件")
    except Exception as e:
        logger.warning("调用 hermes MemoryStore 失败: %s，降级为直接读文件", e)

    # 降级：直接读文件
    memories_dir = hermes_dir / "memories"
    if not memory_content:
        memory_path = memories_dir / "MEMORY.md"
        if memory_path.exists():
            try:
                memory_content = memory_path.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.warning("读取 MEMORY.md 失败: %s", e)

    if not user_content:
        user_path = memories_dir / "USER.md"
        if user_path.exists():
            try:
                user_content = user_path.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.warning("读取 USER.md 失败: %s", e)

    if memory_content:
        if len(memory_content) > 2000:
            memory_content = memory_content[:2000] + "\n...(已截断)"
        persona_parts.append(f"## MEMORY.md\n{memory_content}")

    if user_content:
        if len(user_content) > 2000:
            user_content = user_content[:2000] + "\n...(已截断)"
        persona_parts.append(f"## USER.md\n{user_content}")

    return "\n\n".join(persona_parts) if persona_parts else ""


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
    send_mark = config.get("active", {}).get("send_tag", "凯莉")
    time_format = config.get("active", {}).get("time_format", "%H:%M")

    result = await MessageService.send_message(
        session_id=chat_id,
        message=thought,
        platform=platform,
        write_to_db=True,
        with_mark=True,
        send_mark=send_mark,
        time_format=time_format
    )

    return result.get("success", False)


async def evaluate_emotion_with_llm(
    session_context: str,
    hindsight_context: str,
    status: Dict[str, Any],
    llm_config: Dict[str, Any]
) -> tuple:
    """
    使用 LLM 评估当前情绪状态，输出 VA 值

    返回：(EmotionState, dict) — 情绪状态 + LLM调用详情(prompt_sent, response_received, duration_ms)
    """
    now = datetime.now()
    longing = status.get("longing", {})
    chat_heat = status.get("chat_heat", {})

    # 从配置获取提示词模板
    prompt_template = ConfigService.get_config(
        ActiveSession(), "active_consciousness.prompts.emotion_evaluation"
    ) or _DEFAULTS["active_consciousness.prompts.emotion_evaluation"]

    # 计算沉默时长
    silence_minutes = longing.get('silence_minutes', 0)

    prompt = prompt_template.format(
        time=now.strftime('%Y-%m-%d %H:%M %A'),
        longing_score=longing.get('score', 0),
        longing_label=longing.get('label', '平静'),
        chat_heat=chat_heat.get('heat', 0),
        chat_label=chat_heat.get('label', '冷清'),
        silence_minutes=round(silence_minutes, 1) if silence_minutes else 0,
        context=session_context or "无",
    )

    prompt = f"{prompt}\n\n{hindsight_context}"

    fallback_state = EmotionState()
    llm_details = {"prompt_sent": prompt, "response_received": None, "duration_ms": None}
    logger.info("LLM 情绪评估开始")

    # 构建 LLM 调用函数
    async def _call_llm(p: str) -> str:
        nonlocal llm_details
        start_time = time.time()
        if llm_config.get("mode") == "hermes":
            import asyncio
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = await asyncio.to_thread(
                call_llm,
                task='title_generation',
                messages=[{"role": "user", "content": p}],
                temperature=0.7,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=p,
                temperature=0.7,
                max_tokens=200
            )
            raw = result.get("content", "").strip() if result.get("success") else ""

        duration_ms = round((time.time() - start_time) * 1000)
        llm_details["duration_ms"] = duration_ms
        llm_details["response_received"] = raw
        logger.info("LLM 情绪评估完成: %dms, response=%s", duration_ms, raw[:200])
        return raw if raw else None

    # 使用 fallback 机制调用 LLM
    raw, success = await call_llm_with_fallback(_call_llm, prompt, None)

    if not success or not raw:
        logger.warning("LLM 情绪评估失败，使用默认值")
        return fallback_state, llm_details

    # 解析 JSON
    try:
        import re
        json_match = re.search(r'\{[^}]+\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            return EmotionState(
                valence=float(data.get("valence", 0.5)),
                arousal=float(data.get("arousal", 0.3)),
                social_need=float(data.get("social_need", 0.3)),
                dominant=data.get("dominant", "calm")
            ), llm_details
        else:
            logger.warning("LLM 情绪评估返回格式无效: %s", raw[:200])
            return fallback_state, llm_details
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error("解析 LLM 情绪返回失败: %s", e)
        return fallback_state, llm_details



async def generate_memory_thought(
    config: Dict[str, Any],
    status: Dict[str, Any],
    hindsight_results: List[Dict],
    emotion_state: EmotionState,
    context_bundle=None
) -> Optional[Dict]:
    """基于 Hindsight 记忆生成念头（使用 ThoughtEngine 统一入口）"""
    if not hindsight_results:
        return None
    try:
        from services.thought_engine import ThoughtEngine
        engine = ThoughtEngine(config)
        result = await engine.generate(status)
        return result  # 返回完整结果（含 thought + llm_details + context_bundle）
    except Exception as e:
        logger.warning("记忆念头生成失败: %s", e)
        return None


async def generate_and_send_thought_with_emotion(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState,
    decision_type: str,
    heartbeat_id: Optional[int] = None,
    decision_score: float = 0.0
) -> tuple[bool, Dict[str, Any]]:
    """生成念头并发送消息（使用 ThoughtEngine）"""
    details = {
        "thought_generation": None,
        "message_sending": None,
    }

    # 使用 ThoughtEngine 生成念头
    from services.thought_engine import ThoughtEngine
    engine = ThoughtEngine(config)
    result = await engine.generate(status)
    
    thought = result.get("thought")
    want_to_contact = result.get("want_to_contact", False)
    details["thought_generation"] = result.get("llm_details")
    details["context_bundle"] = result.get("context_bundle")
    
    # 如果 LLM 不想联系用户，返回 False
    if not want_to_contact or not thought:
        logger.info("LLM 不想联系用户，跳过发送")
        return False, details

    # 确定念头类型
    hindsight_results = result.get("context_bundle", {}).get("memories", [])
    weather_info = result.get("context_bundle", {}).get("weather")
    thought_type = determine_thought_type(status, emotion_state, hindsight_results, weather_info)
    
    # 构建念头日志详情
    hindsight_tags = ["active_consciousness", "thought", thought_type, emotion_state.dominant]
    if "曹凡" in thought:
        hindsight_tags.append("user_related")
    if emotion_state.intensity() > 0.7:
        hindsight_tags.append("high_emotion")
    
    thought_details = {
        "thought_type": thought_type,
        "emotion_state": emotion_state.to_dict(),
        "decision": decision_type,
        "score": round(decision_score, 3),
        "hindsight_tags": hindsight_tags,
        "hindsight_stored": False,
        "llm_call": result.get("llm_details", {}),
        "context_bundle": result.get("context_bundle", {}),
    }
    
    # 记录念头日志
    ActiveConsciousnessService.write_thought_log(
        heartbeat_id=heartbeat_id,
        thought_type=thought_type,
        content=thought,
        intensity=emotion_state.intensity(),
        decision=decision_type,
        reason=f"情绪: {emotion_state.dominant}, 决策: {decision_type}",
        score=decision_score,
        recall_count=len(hindsight_results),
        recall_source="hindsight",
        chat_heat=status.get("chat_heat", {}).get("heat", 0),
        emotional_intensity=emotion_state.intensity(),
        hindsight_stored=bool(details.get("hindsight_stored", False)),
        details=json.dumps(thought_details, ensure_ascii=False)
    )
    
    # 发送消息
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

        # 6. 使用 ContextCollector 收集结构化上下文
        from services.context_collector import ContextCollector
        context_collector = ContextCollector(config)
        context_bundle = await context_collector.collect(status)
        all_details["context_bundle"] = context_bundle.to_dict()

        # 构建情绪评估用的 session_context（完整内容，不截断）
        context_config = config.get("context", {})
        conversation_limit = context_config.get("conversation_limit", 50)
        session_context = "\n".join(
            f"{m.get('role', '?')}: {m.get('content', '')}"
            for m in context_bundle.conversations[-conversation_limit:]
        ) if context_bundle.conversations else ""
        hindsight_context = "相关记忆:\n" + "\n".join(
            f"- {m}" for m in context_bundle.memories
        ) if context_bundle.memories else ""
        recall_count = len(context_bundle.memories)
        hindsight_results = [{"text": m, "type": "memory"} for m in context_bundle.memories]

        # 存储召回数据到 details（供前端展示）- 存完整数据，不截断
        all_details["session_context"] = session_context if session_context else ""
        all_details["hindsight_context"] = hindsight_context if hindsight_context else ""
        all_details["recall_results"] = [
            {"text": r.get("text", ""), "type": r.get("type", "memory")}
            for r in hindsight_results
        ]
        # 存储 session 对话（供前端展示完整上下文，不截断内容）
        all_details["session_messages"] = [
            {"role": m.get("role", "?"), "content": m.get("content", ""), "time": m.get("time", "")}
            for m in (context_bundle.conversations[-conversation_limit:] if context_bundle.conversations else [])
        ]

        # 7. LLM 评估当前情绪（输出 VA 值）—— 使用情绪评估专用 LLM
        llm_config = get_effective_llm_config(config, "emotion")
        llm_assessed, emotion_llm_details = await evaluate_emotion_with_llm(
            session_context, hindsight_context, status, llm_config
        )
        all_details["emotion_llm_details"] = emotion_llm_details
        # 如果 LLM 返回全0（模型未正常响应），使用演化值作为 fallback
        if abs(llm_assessed.valence) < 0.01 and abs(llm_assessed.arousal) < 0.01 and abs(llm_assessed.social_need) < 0.01:
            logger.warning("LLM 情绪评估返回全0，使用演化值作为 fallback")
            llm_assessed = evolved_state
        all_details["emotion_llm"] = llm_assessed.to_dict()

        # 8. 合并情绪（演化值 + LLM 评估值）- 使用动态权重
        llm_confidence = calculate_llm_confidence(llm_assessed, evolved_state)
        merged_state = merge_emotion_dynamic(evolved_state, llm_assessed, llm_confidence)
        all_details["emotion_merged"] = merged_state.to_dict()
        all_details["llm_confidence"] = llm_confidence
        logger.info("情绪合并: valence=%.3f, arousal=%.3f, dominant=%s, confidence=%.2f",
                    merged_state.valence, merged_state.arousal, merged_state.dominant, llm_confidence)

        # 9. 保存情绪状态
        update_emotion_state(merged_state)

        # 10. 使用新决策公式（先计算决策分数）
        decision_type, reason, score = make_decision_v2(config, status, merged_state)
        all_details["decision"] = {
            "type": decision_type,
            "reason": reason,
            "score": round(score, 3)
        }
        logger.info("决策结果: type=%s, score=%.3f, reason=%s", decision_type, score, reason)

        # 11. 发送保护检查（在决策计算之后，只拦截实际发送）
        protection_result, protection_reason = check_send_protection(config, status, merged_state)
        if protection_result == "skip":
            # 保护机制拦截，但保留决策分数
            all_details["decision"]["blocked_by_protection"] = True
            all_details["decision"]["protection_reason"] = protection_reason
            logger.info("发送保护拦截（保留决策分数 %.3f）: %s", score, protection_reason)
            # 不改变 decision_type，让后续逻辑根据原始决策处理

        # 13. 记录心跳日志（初始）
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

        # 14. 处理决策结果
        blocked_by_protection = all_details.get("decision", {}).get("blocked_by_protection", False)
        
        if decision_type == "skip":
            logger.info("心跳跳过: %s", reason)

        elif decision_type == "memory":
            # 存为记忆（不发送）
            gen_result = await generate_memory_thought(config, status, hindsight_results, merged_state, context_bundle)
            thought = gen_result.get("thought") if gen_result else None
            if thought:
                # 合并 llm_details + thought 字段
                llm_details = gen_result.get("llm_details", {})
                all_details["thought_generation"] = {**llm_details, "thought": thought, "success": True}
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
                    hindsight_stored=bool(stored),
                    details=json.dumps({"emotion_state": merged_state.to_dict(), "hindsight_tags": hindsight_tags}, ensure_ascii=False)
                )
                logger.info("念头存为记忆: %s", thought[:50])
            else:
                all_details["thought_generation"] = {"success": False, "error": "念头生成返回空"}

        elif decision_type == "auto_send":
            # 自动发送（检查保护机制）
            if blocked_by_protection:
                # 保护机制拦截，跳过实际发送，但记录念头
                logger.info("保护机制拦截，跳过实际发送")
                all_details["thought_generation"] = {"success": False, "error": "保护机制拦截"}
            else:
                # 正常发送
                sent, gen_details = await generate_and_send_thought_with_emotion(
                    config, status, merged_state, decision_type, heartbeat_id, score
                )
                all_details.update(gen_details)
                all_details["actual_sent"] = sent

                if sent:
                    # 发送成功后存入 Hindsight
                    thought = gen_details.get("message_sending", {}).get("thought", "")
                    if thought:
                        weather_info = all_details.get("context_bundle", {}).get("weather")
                        thought_type = determine_thought_type_v2(status, merged_state, hindsight_results, weather_info)
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

        # 15. 重评估延迟队列
        delay_stats = await reevaluate_delayed_thoughts(config, status, merged_state)
        all_details["delay_reeval"] = delay_stats
        if any(v > 0 for v in delay_stats.values()):
            logger.info("延迟队列重评估: %s", delay_stats)

        # 16. 读取更新后的情绪值
        all_details["emotion_after"] = get_emotion_state().to_dict()

        # 17. 更新心跳日志（含 details）
        duration_ms = round((time.time() - start_time) * 1000)
        logger.info("=== 心跳完成 === duration=%dms, decision=%s", duration_ms, decision_type)
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
                        "message_sent": all_details.get("actual_sent", False),
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


# ============ 日志清理 ============

def cleanup_old_logs(days_to_keep: int = 30):
    """
    清理旧的心跳日志

    Args:
        days_to_keep: 保留天数
    """
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

    try:
        with active_engine.connect() as conn:
            # 删除旧的心跳日志
            result = conn.execute(text("""
                DELETE FROM active_heartbeat_logs
                WHERE created_at < :cutoff
            """), {"cutoff": cutoff_date})
            deleted_count = result.rowcount
            conn.commit()

            logger.info("已清理 %d 条旧心跳日志 (保留 %d 天)", deleted_count, days_to_keep)
    except Exception as e:
        logger.error("清理旧日志失败: %s", e)


# 全局日志清理调度器实例
log_cleanup_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def schedule_log_cleanup():
    """调度日志清理任务"""
    global log_cleanup_scheduler

    if log_cleanup_scheduler.running:
        logger.info("日志清理调度器已在运行")
        return

    # 每天凌晨 3 点执行清理
    from apscheduler.triggers.cron import CronTrigger
    log_cleanup_scheduler.add_job(
        cleanup_old_logs,
        CronTrigger(hour=3, minute=0),
        id="log_cleanup_job",
        name="日志清理",
        replace_existing=True
    )

    log_cleanup_scheduler.start()
    logger.info("日志清理调度器已启动")


def stop_log_cleanup_scheduler():
    """停止日志清理调度器"""
    global log_cleanup_scheduler
    if log_cleanup_scheduler and log_cleanup_scheduler.running:
        log_cleanup_scheduler.shutdown(wait=False)
        logger.info("日志清理调度器已停止")


def restart_heartbeat_scheduler(new_interval: int = None):
    """
    重启心跳调度器

    Args:
        new_interval: 新的心跳间隔（秒），如果为 None 则使用配置中的值
    """
    global heartbeat_scheduler

    # 停止现有调度器
    if heartbeat_scheduler.running:
        heartbeat_scheduler.shutdown(wait=False)
        logger.info("心跳调度器已停止")

    # 获取新的间隔
    if new_interval is None:
        config = ActiveConsciousnessService.get_config()
        new_interval = int(config.get("active", {}).get("heartbeat_interval", 600))

    # 创建新的调度器
    heartbeat_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    heartbeat_scheduler.add_job(
        run_heartbeat,
        IntervalTrigger(seconds=new_interval),
        id="active_consciousness_heartbeat",
        name="主动意识心跳",
        replace_existing=True
    )

    # 启动调度器
    heartbeat_scheduler.start()
    logger.info("心跳调度器已重启，间隔: %d 秒", new_interval)


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


def merge_emotion_dynamic(
    evolved: EmotionState,
    llm_assessed: EmotionState,
    llm_confidence: float
) -> EmotionState:
    """
    动态权重合并情绪

    Args:
        evolved: 演化后的情绪
        llm_assessed: LLM 评估的情绪
        llm_confidence: LLM 评估的置信度 (0-1)

    Returns:
        合并后的情绪
    """
    # 根据置信度调整权重
    if llm_confidence < 0.3:
        # LLM 不可信，更信任演化
        weight_evolved, weight_llm = 0.7, 0.3
    elif llm_confidence > 0.8:
        # LLM 很可信，更信任 LLM
        weight_evolved, weight_llm = 0.3, 0.7
    else:
        # 默认权重
        weight_evolved, weight_llm = 0.4, 0.6

    logger.info("动态权重合并: confidence=%.2f, evolved_weight=%.2f, llm_weight=%.2f",
                llm_confidence, weight_evolved, weight_llm)

    return EmotionState(
        valence=evolved.valence * weight_evolved + llm_assessed.valence * weight_llm,
        arousal=evolved.arousal * weight_evolved + llm_assessed.arousal * weight_llm,
        social_need=evolved.social_need * weight_evolved + llm_assessed.social_need * weight_llm,
        dominant=llm_assessed.dominant if llm_confidence > 0.5 else evolved.dominant,
        updated_at=datetime.now().isoformat()
    )


def calculate_llm_confidence(llm_assessed: EmotionState, evolved: EmotionState) -> float:
    """
    计算 LLM 评估的置信度

    置信度基于：
    1. LLM 返回值是否在合理范围内
    2. LLM 返回值与演化值的差异
    """
    confidence = 0.5  # 基础置信度

    # 检查值是否在合理范围内
    if 0 <= llm_assessed.valence <= 1 and 0 <= llm_assessed.arousal <= 1:
        confidence += 0.2

    # 检查与演化值的差异（差异太大可能表示 LLM 不准确）
    valence_diff = abs(llm_assessed.valence - evolved.valence)
    arousal_diff = abs(llm_assessed.arousal - evolved.arousal)

    if valence_diff < 0.3 and arousal_diff < 0.3:
        confidence += 0.3
    elif valence_diff > 0.5 or arousal_diff > 0.5:
        confidence -= 0.2

    return max(0.0, min(1.0, confidence))


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


def check_send_protection(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> tuple[Optional[str], Optional[str]]:
    """
    发送保护检查

    在决策之前检查是否应该跳过发送。

    Returns:
        (decision, reason): 如果应该跳过，返回 ("skip", reason)；否则返回 (None, None)
    """
    active_config = config.get("active", {})

    # 1. 用户消息后不发送
    no_send_minutes = int(active_config.get("no_send_after_user_msg_minutes", 10))
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < no_send_minutes:
        logger.info("发送保护: 用户最近 %.0f 分钟内有消息（阈值 %d 分钟）", silence_minutes, no_send_minutes)
        return "skip", f"用户最近 {no_send_minutes} 分钟内有消息（沉默 {silence_minutes:.0f} 分钟）"

    # 2. 热度过高不发送
    heat_threshold = float(active_config.get("no_send_while_heat_above", 1.0))
    current_heat = status.get("chat_heat", {}).get("heat", 0)
    if current_heat > heat_threshold:
        logger.info("发送保护: 聊天热度 %.2f 超过阈值 %.2f", current_heat, heat_threshold)
        return "skip", f"聊天热度 {current_heat:.2f} 超过阈值 {heat_threshold}"

    # 3. 情绪过低不发送
    vibe_threshold = float(active_config.get("no_send_while_vibe_below", 0.15))
    current_intensity = emotion_state.intensity()
    if current_intensity < vibe_threshold:
        logger.info("发送保护: 情绪强度 %.3f 低于阈值 %.2f", current_intensity, vibe_threshold)
        return "skip", f"情绪强度 {current_intensity:.3f} 低于阈值 {vibe_threshold}"

    return None, None  # 通过所有检查


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
    if silence_minutes < 30:
        silence_factor = 0.6    # 30 分钟内
    elif silence_minutes < 60:
        silence_factor = 0.75   # 30-60 分钟
    elif silence_minutes < 180:
        silence_factor = 0.85   # 1-3 小时
    elif silence_minutes < 360:
        silence_factor = 0.95   # 3-6 小时
    else:
        silence_factor = 1.0    # 6 小时以上

    # 4. 频率限制（二元判断：未超频=1.0，已超频=0.0）
    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = decision_config.get("max_per_hour", 2)
    frequency_limit = 1.0 if hour_sent < max_per_hour else 0.0

    # 计算总分
    score = intensity * time_fitness * silence_factor * frequency_limit

    logger.info("决策计算: intensity=%.3f, time_fitness=%.3f(%s), silence_factor=%.3f, frequency_limit=%.3f",
                intensity, time_fitness, time_label, silence_factor, frequency_limit)

    # 决策阈值
    send_threshold = decision_config.get("send_threshold", 0.6)
    memory_threshold = decision_config.get("memory_threshold", 0.1)

    # 构建决策原因
    reason_parts = [
        f"intensity={intensity:.3f}",
        f"time_fitness={time_fitness:.3f}({time_label})",
        f"silence_factor={silence_factor:.3f}",
        f"frequency_limit={frequency_limit:.3f}",
    ]
    reason = ", ".join(reason_parts)

    logger.info("决策结果: score=%.3f, decision=%s, threshold(send=%.3f, memory=%.3f)",
                score, "auto_send" if score > send_threshold else "memory" if score > memory_threshold else "skip",
                send_threshold, memory_threshold)

    if score > send_threshold:
        return "auto_send", f"score={score:.3f} > {send_threshold} ({reason})", score
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


def determine_thought_type_v2(
    status: Dict[str, Any],
    emotion_state: EmotionState,
    hindsight_results: List[Dict],
    context: Optional[Dict]
) -> str:
    """
    更智能的念头类型判断

    优先级：
    1. 特殊时间（早安 7-8, 晚安 22-23）
    2. 长时间沉默（>180分钟）
    3. 高情绪强度（>0.6）
    4. 相关回忆
    5. 默认关联
    """
    now = datetime.now()

    # 1. 检查特殊时间（早安 7-8, 晚安 22-23）
    if now.hour in [7, 8, 22, 23]:
        return ThoughtType.TIME.value

    # 2. 检查沉默时长
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes > 180:  # 3小时没聊天
        return ThoughtType.SILENCE.value

    # 3. 检查天气变化（雨、雪、大风等特殊天气）
    if context and context.get("weather") in ["雨", "雪", "大风", "雷阵雨"]:
        return ThoughtType.ENVIRONMENT.value

    # 4. 检查情绪强度
    if emotion_state.intensity() > 0.6:
        return ThoughtType.EMOTION.value

    # 5. 检查是否有相关回忆
    if hindsight_results and len(hindsight_results) > 0:
        return ThoughtType.MEMORY.value

    # 6. 默认关联念头
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

    logger.info("retain_thought_to_hindsight 调用: thought=%s, thought_type=%s, score=%.3f", thought[:50], thought_type, score)
    logger.info("retain_thought_to_hindsight 配置: thought_config=%s", json.dumps(thought_config, ensure_ascii=False))

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
        # 使用 store.bank_id 用于存储，而不是 recall 的 bank_id
        store_config = hindsight_config.get("store", {})
        bank_id = store_config.get("bank_id", "hermes-active")
        timeout = float(hindsight_config.get("timeout", 30))

        # 强制确保使用正确的 bank_id 用于存储
        if not bank_id or bank_id == "hermes":
            logger.warning("Hindsight 存储 bank_id 不正确: '%s'，强制使用 'hermes-active'", bank_id)
            bank_id = "hermes-active"

        logger.info("Hindsight 存储配置: base_url=%s, store.bank_id=%s, timeout=%s", base_url, bank_id, timeout)

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

        logger.info("Hindsight 存储调用: bank_id=%s, content=%s, tags=%s", bank_id, content[:50], tags)
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







def get_recent_thoughts_from_db(limit: int = 5) -> List[Dict]:
    """从本地 active_thought_logs 表获取最近的念头"""
    try:
        with active_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT type, content, intensity, decision, created_at "
                "FROM active_thought_logs "
                "WHERE decision IN ('send', 'memory') "
                "ORDER BY created_at DESC LIMIT :limit"
            ), {"limit": limit}).fetchall()
            return [{"text": f"[{r[0]}] {r[1]}", "type": "thought", "intensity": r[2]} for r in rows]
    except Exception as e:
        logger.warning("查询本地念头失败: %s", e)
        return []

def pre_calculate_score(
    emotion_state: EmotionState,
    status: Dict[str, Any],
    decision_config: Dict[str, Any]
) -> float:
    """在不调 LLM 的情况下估算 score（用于过滤低分心跳，节省 token）

    算法复用 make_decision 的核心公式：
        score = intensity × time_fitness × silence_factor × frequency_limit

    Args:
        emotion_state: 当前情绪状态
        status: 状态 dict（包含 longing、chat_heat 等）
        decision_config: 决策配置

    Returns:
        预估 score（0.0~1.0）
    """
    intensity = emotion_state.intensity()

    time_fitness, _ = get_time_fitness()

    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < 30:
        silence_factor = 0.6
    elif silence_minutes < 60:
        silence_factor = 0.75
    elif silence_minutes < 180:
        silence_factor = 0.85
    elif silence_minutes < 360:
        silence_factor = 0.95
    else:
        silence_factor = 1.0

    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = decision_config.get("max_per_hour", 100)
    frequency_limit = 1.0 if hour_sent < max_per_hour else 0.0

    return intensity * time_fitness * silence_factor * frequency_limit
