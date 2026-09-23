"""冲突修复服务：状态机 + 诚意评分 + 旧账管理（纯函数优先，便于测试）

模式集合：normal / upset / cold / softening / reconciled / self_at_fault / grudge
状态单例存 configs 键 "active_consciousness.repair_state"（JSON）
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

RECONCILE_POINTS = 6.0   # 和好所需积分
GRIEVANCE_CAP = 5
GRIEVANCE_COOLDOWN_DAYS = 30


def transition(mode: str, event: Dict[str, Any], state: Optional[Dict] = None) -> str:
    """纯函数状态机。event: {type: trigger|tick|goodwill|self_fault, ...}"""
    st = state or {}
    t = event.get("type")
    if t == "self_fault":
        return "self_at_fault"
    if t == "trigger":
        sev = event.get("severity", 0)
        drop = event.get("valence_drop", 0.0)
        if mode == "normal" and sev >= 3 and drop >= 0.3:
            return "upset"
        return mode
    if t == "tick":
        h = event.get("hours_since", 0)
        if mode == "reconciled":
            return "normal"
        if mode == "upset" and h >= 4:
            return "cold"
        if mode == "cold" and h >= 72:
            return "grudge"
        if mode == "self_at_fault" and h >= 24:
            return "normal"
        return mode
    if t == "goodwill":
        pts = event.get("points", 0.0)
        total = st.get("points", 0.0) + pts
        # softening 门槛：约 1/3 和好积分（2.0 分）开始嘴硬心软
        if mode in ("cold", "upset") and total >= RECONCILE_POINTS / 3:
            return "softening"
        if mode == "softening" and total >= RECONCILE_POINTS:
            return "reconciled"
        return mode
    return mode


def score_goodwill(sincerity: int, is_repeat: bool, hours_since_upset: float) -> float:
    """诚意积分：LLM 评 1-5 分 → 积分；重复套话 0 分；时间衰减。"""
    if is_repeat or not (1 <= sincerity <= 5):
        return 0.0
    base = (sincerity - 1) / 4.0
    decay = max(0.3, 1.0 - hours_since_upset / 72.0)
    return base * decay * 2.0


def add_grievance(mem: List[Dict], event: str, severity: int) -> List[Dict]:
    """记旧账（上限 GRIEVANCE_CAP，新的挤掉最旧的）"""
    mem = list(mem) + [{
        "event": event, "severity": severity,
        "settled_at": None, "last_cited_at": None,
        "created_at": datetime.now().isoformat()}]
    return sorted(mem, key=lambda g: g.get("created_at") or "")[-GRIEVANCE_CAP:]


def should_cite_grievance(mem: List[Dict], today: Optional[str] = None) -> bool:
    """翻旧账冷却：任一旧账距上次引用超 30 天才可翻（防祥林嫂）"""
    today = today or datetime.now().strftime("%Y-%m-%d")
    for g in mem:
        last = g.get("last_cited_at")
        if last is None:
            return True
        d = (datetime.fromisoformat(today) - datetime.fromisoformat(last)).days
        if d >= GRIEVANCE_COOLDOWN_DAYS:
            return True
    return False


def call_llm_json(prompt: str, llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """极简 JSON LLM 调用（本服务内部工具）。

    复用 active_consciousness_service 的现有 LLM 调用方式（hermes → auxiliary_client，
    其他 → LLMService）。prompt 自带"只输出 JSON"约束；解析失败抛异常，由调用方兜底。
    """
    cfg = llm_config or {}
    mode = cfg.get("mode") or "hermes"
    raw = ""
    if mode == "hermes":
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
        from agent.auxiliary_client import call_llm, extract_content_or_reasoning

        response = call_llm(
            messages=[{"role": "user", "content": f"{prompt}\n只输出 JSON，不要解释。"}],
            temperature=0.3,
            max_tokens=200,
        )
        raw = extract_content_or_reasoning(response) or ""
    else:
        import asyncio
        from services.llm_service import LLMService

        result = asyncio.get_event_loop().run_until_complete(
            LLMService.generate_message(
                llm_config=cfg,
                prompt=f"{prompt}\n只输出 JSON，不要解释。",
                temperature=0.3,
                max_tokens=200,
            )
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error") or "LLM 调用失败")
        raw = (result.get("content") or "").strip()

    raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            raise ValueError(f"无法解析 JSON: {raw[:200]}")
        data = json.loads(m.group())
    if not isinstance(data, dict):
        raise ValueError(f"LLM 返回非对象: {raw[:200]}")
    return data


def evaluate_trigger(session_context: str, emotion: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 归因：刚才是否因用户言行受伤 + 严重度 1-5。失败兜底 severity=0（无归因，不误伤）。"""
    try:
        prompt = (f"你是凯莉。刚才的对话如下：\n{(session_context or '')[-800:]}\n"
                  f"当前情绪 valence={emotion.get('valence', 0) if emotion else 0}。\n"
                  '判断用户是否说了让你受伤/生气的话。只输出 JSON：'
                  '{"trigger": "一句话描述原因，没有则空串", "severity": 1到5的整数，5最严重，没有则0}')
        r = call_llm_json(prompt, {})
        return {"trigger": str(r.get("trigger", "")), "severity": int(r.get("severity", 0) or 0)}
    except Exception:
        return {"trigger": "", "severity": 0}


def evaluate_goodwill(user_msg: str, recent_goodwills: list, hours_since_upset: float = 0.0) -> Dict[str, Any]:
    """诚意评分：一次 LLM 调用输出 sincerity 1-5 + is_repeat，转积分。失败 0 分。

    hours_since_upset 由调用方从 RepairState.started_at 算出后传入（默认 0.0）。
    """
    try:
        recent = "；".join(str(x) for x in (recent_goodwills or [])[-5:]) or "（无）"
        prompt = (f"你（凯莉）和用户冷战/生气中。用户刚发来示好消息：\n{user_msg}\n"
                  f"他之前的示好：{recent}\n"
                  '评估这次哄人的诚意，只输出 JSON：'
                  '{"sincerity": 1到5（5=真走心，1=敷衍）， "is_repeat": true/false（与之前的话是否同一套话术）}')
        r = call_llm_json(prompt, {})
        s = int(r.get("sincerity", 0) or 0)
        rep = bool(r.get("is_repeat", False))
        points = score_goodwill(s, is_repeat=rep, hours_since_upset=hours_since_upset)
        return {"sincerity": s, "is_repeat": rep, "points": points}
    except Exception:
        return {"sincerity": 0, "is_repeat": False, "points": 0.0}
