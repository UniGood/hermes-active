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
