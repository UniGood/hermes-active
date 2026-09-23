"""学习回路：效果采集 + state.db 对账 + LLM 质性总结（单用户样本稀薄，不做统计调参）"""
from datetime import datetime
from typing import Any, Dict, List
import logging

from sqlalchemy import text

from models.database import active_engine, state_engine
from services.repair_service import call_llm_json

logger = logging.getLogger("hermes.learning")

EFFECT_CAP = 200        # 效果样本上限
LESSON_CAP = 20         # 教训滚动上限
MIN_SAMPLES = 10        # 周总结最小样本
BUSY_HOURS = (9, 18)    # 工作时段（忙时 ignored 降权，spec B4-4）

# 短冷回复：内容长度不超过此值视为敷衍
_SHORT_COLD_CHARS = 6


def record_sent(thought_id: int, topic: str, tone: str, sent_at: str) -> None:
    """发送成功钩子：记效果样本（effect 留空，等对账补标签）"""
    try:
        with active_engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO message_effects (thought_id, topic, tone, sent_at, effect, reply_latency) "
                "VALUES (:thought_id, :topic, :tone, :sent_at, NULL, NULL)"
            ), {
                "thought_id": thought_id,
                "topic": topic or "general",
                "tone": tone or "normal",
                "sent_at": sent_at,
            })
            conn.commit()
            # 样本滚动上限：超出时删最旧
            conn.execute(text(
                "DELETE FROM message_effects WHERE id NOT IN ("
                "  SELECT id FROM message_effects ORDER BY sent_at DESC LIMIT :cap"
                ")"
            ), {"cap": EFFECT_CAP})
            conn.commit()
    except Exception as e:
        logger.warning("记录效果样本失败: %s", e)


def _load_effects() -> List[Dict]:
    """读效果样本（对账/总结共用）"""
    try:
        with active_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, thought_id, topic, tone, sent_at, effect, reply_latency "
                "FROM message_effects ORDER BY sent_at DESC LIMIT :cap"
            ), {"cap": EFFECT_CAP}).fetchall()
            items = []
            for row in rows:
                if hasattr(row, "_mapping"):
                    items.append(dict(row._mapping))
                else:
                    items.append({
                        "id": row[0], "thought_id": row[1], "topic": row[2],
                        "tone": row[3], "sent_at": row[4], "effect": row[5],
                        "reply_latency": row[6],
                    })
            return items
    except Exception as e:
        logger.warning("读取效果样本失败: %s", e)
        return []


def _row_field(row, name, default=None):
    """从结果行取字段（兼容 SQLAlchemy Row 与 mock 对象）"""
    val = getattr(row, name, None)
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val if val is not None else default
    return default


def _parse_ts(value) -> datetime | None:
    """解析时间戳（ISO 或 unix）"""
    if value is None:
        return None
    try:
        s = str(value)
        if s.replace('.', '', 1).isdigit():
            return datetime.fromtimestamp(float(s))
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _is_busy_hour(sent_at: str) -> bool:
    """发送时刻是否落在工作时段（busy 豁免）"""
    dt = _parse_ts(sent_at)
    if not dt:
        return False
    return BUSY_HOURS[0] <= dt.hour < BUSY_HOURS[1]


def _label_effect(reply_latency_min: float | None, user_rounds: int, texts: List[str], busy: bool) -> str:
    """效果标签
    - ignored：2h 无回复（busy 时段降级 acknowledged，不重罚）
    - engaged：回复 <10min 或 >=3 轮；其余有实质回复也算搭理
    - acknowledged：<3 轮短冷（内容敷衍）
    """
    if reply_latency_min is None or reply_latency_min >= 120:
        return "acknowledged" if busy else "ignored"
    # 有回复：快回或多轮 → engaged
    if reply_latency_min < 10 or user_rounds >= 3:
        return "engaged"
    # <3 轮：看是否短冷（有文本且都很短）；无文本/非短冷 → engaged
    if user_rounds < 3 and texts:
        if all(len(t.strip()) <= _SHORT_COLD_CHARS for t in texts if t):
            return "acknowledged"
    return "engaged"


def reconcile_effects(sent_rows: List[Dict]) -> List[Dict]:
    """读 state.db（只读！）用户消息对账 reply_latency → effect 标签。

    标签：ignored=2h 无回复；acknowledged=<3 轮短冷；engaged=回复 <10min 或 >=3 轮。
    busy 豁免：发送时刻在 BUSY_HOURS 内的 ignored 降级为 acknowledged（不重罚）。
    """
    labels: List[Dict] = []
    for item in sent_rows or []:
        sent_at = item.get("sent_at")
        topic = item.get("topic")
        thought_id = item.get("thought_id")
        busy = _is_busy_hour(sent_at)

        user_times: List[datetime] = []
        texts: List[str] = []
        try:
            with state_engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT timestamp AS created_at, role, content FROM messages "
                    "WHERE timestamp > :sent_at ORDER BY timestamp ASC LIMIT 50"
                ), {"sent_at": sent_at}).fetchall()
            for row in rows:
                role = _row_field(row, "role")
                created = _row_field(row, "created_at")
                content = _row_field(row, "content", "")
                if role != "user":
                    continue
                ts = _parse_ts(created)
                if ts:
                    user_times.append(ts)
                if isinstance(content, str) and content:
                    texts.append(content)
        except Exception as e:
            logger.warning("对账查询 state.db 失败: %s", e)

        sent_dt = _parse_ts(sent_at)
        reply_latency_min = None
        if user_times and sent_dt:
            reply_latency_min = (user_times[0] - sent_dt).total_seconds() / 60

        effect = _label_effect(reply_latency_min, len(user_times), texts, busy)
        labels.append({
            "thought_id": thought_id,
            "topic": topic,
            "sent_at": sent_at,
            "effect": effect,
            "reply_latency": int(reply_latency_min) if reply_latency_min is not None else None,
        })

    # 回写 effect 标签（失败不影响返回值）
    try:
        with active_engine.connect() as conn:
            for lab in labels:
                conn.execute(text(
                    "UPDATE message_effects SET effect = :effect, reply_latency = :latency "
                    "WHERE thought_id = :thought_id AND sent_at = :sent_at"
                ), {
                    "effect": lab["effect"],
                    "latency": lab["reply_latency"],
                    "thought_id": lab["thought_id"],
                    "sent_at": lab["sent_at"],
                })
            conn.commit()
    except Exception as e:
        logger.warning("回写 effect 标签失败: %s", e)

    return labels


def _build_lessons_prompt(effects: List[Dict]) -> str:
    """把效果明细（话题×效果）拼成质性总结 prompt"""
    lines = []
    for e in effects:
        lines.append(f"- 话题={e.get('topic') or 'general'} 效果={e.get('effect') or 'pending'} 语气={e.get('tone') or 'normal'}")
    detail = "\n".join(lines)
    return (
        "下面是最近主动消息的发送效果样本（话题×效果）：\n"
        f"{detail}\n\n"
        "请从这些零散样本里做质性总结（不要统计调参），产出 1-5 条一句话经验教训，"
        "例如「嘘寒问暖类回应差，趣事类回应好」「晚上 10 点后聊得开」。"
        '只输出 JSON：{"lessons": ["一句话教训"]}'
    )


def summarize_lessons(min_samples: int = MIN_SAMPLES) -> List[str]:
    """质性总结：≥min_samples 条效果样本才跑 LLM，产出一句话教训列表，写 lessons 表 + trim_lessons。
    LLM 调用复用 repair_service.call_llm_json。失败返回 [] 不抛。
    """
    try:
        effects = _load_effects()
        if len(effects) < min_samples:
            return []

        prompt = _build_lessons_prompt(effects)
        try:
            data = call_llm_json(prompt, {"mode": "hermes"})
        except Exception as e:
            logger.warning("教训 LLM 总结失败: %s", e)
            return []
        if not isinstance(data, dict):
            return []
        lessons = data.get("lessons") or []
        if not isinstance(lessons, list):
            return []
        lessons = [str(x).strip() for x in lessons if str(x).strip()]
        if not lessons:
            return []

        now = datetime.now().isoformat()
        try:
            with active_engine.connect() as conn:
                for summary in lessons:
                    conn.execute(text(
                        "INSERT INTO lessons (summary, evidence_count, retired, created_at) "
                        "VALUES (:summary, :evidence_count, 0, :created_at)"
                    ), {
                        "summary": summary,
                        "evidence_count": max(1, len(effects) // max(len(lessons), 1)),
                        "created_at": now,
                    })
                conn.commit()
            # 滚动淘汰
            mem = _load_lessons_raw()
            keep = trim_lessons(mem)
            keep_ids = {m.get("id") for m in keep if m.get("id") is not None}
            with active_engine.connect() as conn:
                for m in mem:
                    lid = m.get("id")
                    if lid is not None and lid not in keep_ids:
                        conn.execute(text("DELETE FROM lessons WHERE id = :id"), {"id": lid})
                conn.commit()
        except Exception as e:
            logger.warning("写入 lessons 失败: %s", e)

        return lessons
    except Exception as e:
        logger.warning("summarize_lessons 异常: %s", e)
        return []


def _load_lessons_raw() -> List[Dict]:
    """读全部教训（含 retired）"""
    try:
        with active_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, summary, evidence_count, retired, created_at FROM lessons ORDER BY created_at ASC"
            )).fetchall()
            items = []
            for row in rows:
                if hasattr(row, "_mapping"):
                    items.append(dict(row._mapping))
                else:
                    items.append({
                        "id": row[0], "summary": row[1], "evidence_count": row[2],
                        "retired": row[3], "created_at": row[4],
                    })
            return items
    except Exception as e:
        logger.warning("读取 lessons 失败: %s", e)
        return []


def trim_lessons(mem: List[Dict]) -> List[Dict]:
    """滚动保留最近 LESSON_CAP 条（按 created_at）"""
    if not mem:
        return []
    ordered = sorted(mem, key=lambda x: str(x.get("created_at") or ""))
    return ordered[-LESSON_CAP:]


def weekly_job() -> None:
    """周总结任务（scheduler 每周一 09:00 调）：先 reconcile 再 summarize"""
    try:
        pending = [e for e in _load_effects() if not e.get("effect")]
        if pending:
            reconcile_effects(pending)
        summarize_lessons()
        logger.info("学习回路周总结完成")
    except Exception as e:
        logger.warning("学习回路周总结失败: %s", e)
