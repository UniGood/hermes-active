"""自由意识对外出口测试：Hindsight 沉淀 + 灵感源采集"""
from unittest.mock import patch, MagicMock
import asyncio


def _run(result):
    if not asyncio.iscoroutine(result):
        return result
    # 每次用全新事件 loop，避免与其他测试共享/复用已关闭的 loop
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(result)
    finally:
        loop.close()


class TestHindsightExport:
    @patch("services.free_consciousness_service.get_hindsight_client")
    def test_retain_to_hindsight_writes_memory(self, mock_get_client):
        from services.free_consciousness_service import FreeConsciousnessService
        client = MagicMock()
        mock_get_client.return_value = client
        ok = FreeConsciousnessService.retain_to_hindsight(
            round_number=3, thinking="今天的思考",
            summary="一句话总结", discovery="一个发现")
        assert ok is True
        client.retain.assert_called_once()
        args = client.retain.call_args
        content = args.kwargs.get("content") or args.args[1]
        assert "第3轮" in content
        assert (args.kwargs.get("metadata") or {}).get("source") == "free-consciousness"

    @patch("services.free_consciousness_service.get_hindsight_client", side_effect=RuntimeError("down"))
    def test_retain_failure_does_not_break(self, mock_g):
        from services.free_consciousness_service import FreeConsciousnessService
        ok = FreeConsciousnessService.retain_to_hindsight(1, "t", None, None)
        assert ok is False


class TestInspirationSource:
    def test_context_bundle_carries_free_thoughts(self):
        from services.context_collector import ContextBundle
        # ContextBundle 必填字段以 dataclass 定义为准：time_context / user_habits 等需补齐
        b = ContextBundle(
            conversations=[], memories=[],
            emotion={"valence": 0.0, "arousal": 0.0, "social": 0.0, "dominant": "calm"},
            time_context={"hour": 12, "is_workday": True, "is_meal_time": False,
                          "is_sleep_time": False, "time_display": "2026-09-22 12:00"},
            weather=None,
            user_habits="",
            free_thoughts=["昨夜想着搬家的事"])
        assert b.free_thoughts == ["昨夜想着搬家的事"]
        assert "free_thoughts" in b.to_dict()

    @patch("services.context_collector.active_engine")
    def test_collect_pulls_recent_free_thoughts(self, mock_engine):
        from services.context_collector import ContextCollector
        r1 = MagicMock(); r1.summary = "想着旅行"; r1.discovery = None; r1.thinking = "长文本"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [r1]
        c = ContextCollector({"hindsight": {"enabled": False}})
        bundle = _run(c.collect({"longing": 0.1}))
        assert any("旅行" in x for x in bundle.free_thoughts)
