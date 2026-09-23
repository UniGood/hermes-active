# Task: 冲突修复·数据层 + 状态机

## STRICT RULES
- ONLY modify: 新建 `backend/services/repair_service.py`、新建 `backend/tests/test_repair_state.py`、`backend/models/active.py`（只加新类，不动既有 7 表）、`backend/models/database.py`（只加新迁移函数）、`backend/routers/active_consciousness.py`（只加一个 GET 端点）。
- Do NOT touch 其他文件。Do NOT modify `backend/config.py`、`main.py`、既有测试。Do NOT run git。Do NOT 复杂化：状态机必须是纯函数，不做 LLM 调用（下个任务做）。
- 注释用中文。Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。cwd = 项目根。

## Context
hermes-active 冲突修复机制（设计规格 A2）：生气→冷淡→哄→和好的状态机 + 旧账（翻旧账）机制。本任务只做数据层+纯函数状态机，不做 LLM。RepairState 单例存 configs 键 `active_consciousness.repair_state`（JSON），旧账存新表 `repair_grievances`。

## Files
### File 1: `backend/tests/test_repair_state.py`（先写，确认失败）
```python
"""冲突修复状态机测试"""
from services.repair_service import (
    transition, score_goodwill, add_grievance, should_cite_grievance)


class TestTransition:
    def test_upset_by_severe_event(self):
        assert transition("normal", {"type": "trigger", "severity": 4, "valence_drop": 0.5}) == "upset"

    def test_no_transition_on_noise(self):
        assert transition("normal", {"type": "trigger", "severity": 1, "valence_drop": 0.1}) == "normal"

    def test_upset_to_cold_after_hours(self):
        assert transition("upset", {"type": "tick", "hours_since": 5}) == "cold"

    def test_goodwill_accumulates_to_softening(self):
        st = {"mode": "cold", "points": 0.0}
        mode = transition("cold", {"type": "goodwill", "points": 2.0}, state=st)
        assert mode == "softening"

    def test_softening_to_reconciled(self):
        st = {"mode": "softening", "points": 5.0}
        assert transition("softening", {"type": "goodwill", "points": 1.5}, state=st) == "reconciled"

    def test_decay_to_grudge(self):
        assert transition("cold", {"type": "tick", "hours_since": 80}) == "grudge"

    def test_self_at_fault_branch(self):
        assert transition("normal", {"type": "self_fault"}) == "self_at_fault"

    def test_reconciled_resets(self):
        assert transition("reconciled", {"type": "tick", "hours_since": 1}) == "normal"


class TestGoodwill:
    def test_sincere_scores_high(self):
        r = score_goodwill(4, is_repeat=False, hours_since_upset=2)
        assert r > 0.5

    def test_repeat_counts_zero(self):
        assert score_goodwill(5, is_repeat=True, hours_since_upset=1) == 0.0

    def test_time_decay(self):
        fast = score_goodwill(4, is_repeat=False, hours_since_upset=1)
        slow = score_goodwill(4, is_repeat=False, hours_since_upset=60)
        assert slow < fast


class TestGrievances:
    def test_add_and_cap(self):
        mem = []
        for i in range(7):
            mem = add_grievance(mem, f"事{i}", severity=2)
        assert len(mem) <= 5

    def test_cooldown(self):
        mem = [{"event": "旧事", "severity": 3, "settled_at": "2026-09-01", "last_cited_at": "2026-09-20"}]
        assert should_cite_grievance(mem, "2026-09-22") is False
        assert should_cite_grievance([{"event": "x", "severity": 3, "last_cited_at": None}], "2026-09-22") is True
```

### File 2: `backend/services/repair_service.py`（新建）
```python
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
        if mode in ("cold", "upset") and total >= RECONCILE_POINTS * 0.4:
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
```

### File 3: `backend/models/active.py`
末尾新增（仿现有类风格，`Column`/`Base` 等已 import）：
```python
class RepairGrievance(Base):
    """冲突旧账（翻旧账机制）"""
    __tablename__ = "repair_grievances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(Text, nullable=False)          # 事件描述
    severity = Column(Integer, default=1)          # 1-5
    settled_at = Column(String, nullable=True)     # 翻篇时间
    last_cited_at = Column(String, nullable=True)  # 上次被翻的时间
    created_at = Column(String, nullable=False)
```

### File 4: `backend/models/database.py`
仿 `migrate_thought_logs_table` 新增 `migrate_repair_grievances_table()`（CREATE TABLE IF NOT EXISTS repair_grievances），并在 init/migrate 调用链处注册（与现有迁移函数同处调用）。

### File 5: `backend/routers/active_consciousness.py`
只加一个 `GET /repair/state`：读 configs 键 `active_consciousness.repair_state`（JSON，缺省 `{"mode":"normal","points":0}`），返回 `{"mode": ..., "level": 模糊档位}`——档位映射：points <2→"冰"、<4.8→"化冰"、否则"回暖"。**不返回 points 数字**（防游戏化）。mode 中文映射：normal 温柔/upset 有点赌气/cold 冷淡/softening 嘴硬心软/reconciled 回暖/grudge 淡淡的/self_at_fault 心虚讨好。

## Verification
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_repair_state.py -x -q  # 13 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -q --tb=no                 # 基线 23 failed 不新增
```

## After making changes
输出改动摘要。不跑 git。
