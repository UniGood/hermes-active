"""A2 LLM 集成测试：trigger 归因 + 诚意评分"""
from unittest.mock import patch, MagicMock
import asyncio


def _run(r):
    return asyncio.get_event_loop().run_until_complete(r) if asyncio.iscoroutine(r) else r


class TestTriggerAttribution:
    @patch("services.repair_service.call_llm_json")
    def test_trigger_extracted(self, mock_llm):
        from services.repair_service import evaluate_trigger
        mock_llm.return_value = {"trigger": "他说了重话：你做的都是没用的", "severity": 4}
        r = evaluate_trigger("刚才的对话……", {"valence": -0.5})
        assert r["severity"] == 4
        assert "重话" in r["trigger"]

    @patch("services.repair_service.call_llm_json", side_effect=RuntimeError("down"))
    def test_trigger_failure_safe(self, mock_llm):
        from services.repair_service import evaluate_trigger
        r = evaluate_trigger("x", {})
        assert r["severity"] == 0


class TestGoodwillScoring:
    @patch("services.repair_service.call_llm_json")
    def test_sincerity_parsing(self, mock_llm):
        from services.repair_service import evaluate_goodwill
        mock_llm.return_value = {"sincerity": 5, "is_repeat": False}
        r = evaluate_goodwill("我真的知道错了，不该说那句话", [])
        assert r["sincerity"] == 5 and r["points"] > 0

    @patch("services.repair_service.call_llm_json")
    def test_repeat_gets_zero(self, mock_llm):
        from services.repair_service import evaluate_goodwill
        mock_llm.return_value = {"sincerity": 5, "is_repeat": True}
        r = evaluate_goodwill("我错了", ["我错了"])
        assert r["points"] == 0.0
