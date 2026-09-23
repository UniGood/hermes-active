"""学习回路测试：采集、对账、质性总结、注入"""
from unittest.mock import patch, MagicMock
import asyncio


def _run(r):
    return asyncio.get_event_loop().run_until_complete(r) if asyncio.iscoroutine(r) else r


class TestCollection:
    def test_record_effect_on_send(self):
        from services.learning_service import record_sent
        with patch("services.learning_service.active_engine") as me:
            record_sent(thought_id=9, topic="趣事", tone="chill", sent_at="2026-09-22T21:00:00")
            me.connect.return_value.__enter__.return_value.execute.assert_called()

    @patch("services.learning_service.state_engine")
    def test_reconcile_detects_reply(self, mock_state):
        from services.learning_service import reconcile_effects
        row = MagicMock(); row.created_at = "2026-09-22T21:30:00"; row.role = "user"
        mock_state.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [row]
        labels = reconcile_effects([{"thought_id": 9, "sent_at": "2026-09-22T21:00:00", "topic": "趣事"}])
        assert labels[0]["effect"] == "engaged"


class TestLessons:
    @patch("services.learning_service.call_llm_json")
    def test_weekly_lessons_summary(self, mock_llm):
        from services.learning_service import summarize_lessons
        mock_llm.return_value = {"lessons": ["趣事类回应好于嘘寒问暖"]}
        with patch("services.learning_service.active_engine"), \
             patch("services.learning_service._load_effects") as me:
            me.return_value = [{"topic": "趣事", "effect": "engaged"}] * 5
            new = summarize_lessons(min_samples=3)
            assert any("趣事" in l for l in new)

    def test_small_sample_skips(self):
        from services.learning_service import summarize_lessons
        with patch("services.learning_service._load_effects", return_value=[{"topic": "x", "effect": "ignored"}] * 3):
            assert summarize_lessons(min_samples=10) == []

    def test_lessons_rolling_cap(self):
        from services.learning_service import trim_lessons
        mem = [{"summary": f"教训{i}", "evidence_count": 1} for i in range(30)]
        assert len(trim_lessons(mem)) <= 20

    def test_injection_includes_lessons(self):
        from services.thought_engine import _build_lessons_block
        assert "趣事" in _build_lessons_block([{"summary": "趣事回应好", "retired": False}])
        assert _build_lessons_block([]) == ""
