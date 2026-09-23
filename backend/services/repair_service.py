"""冲突修复服务：状态机 + 诚意评分 + 旧账管理（纯函数优先，便于测试）

模式集合：normal / upset / cold / softening / reconciled / self_at_fault / grudge
状态单例存 configs 键 "active_consciousness.repair_state"（JSON）
"""
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
