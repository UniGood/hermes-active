"""retry_thought 重试发送念头测试"""
from unittest.mock import patch, MagicMock
import asyncio

from services.active_consciousness_service import ActiveConsciousnessService


def _run(result):
    return asyncio.get_event_loop().run_until_complete(result) if asyncio.iscoroutine(result) else result


class TestRetryThought:
    @patch("services.active_consciousness_service.send_message_to_target")
    @patch("services.active_consciousness_service.check_send_protection")
    @patch("services.active_consciousness_service.active_engine")
    def test_retry_sends_existing_thought(self, mock_engine, mock_protect, mock_send):
        mock_protect.return_value = (True, "ok")
        mock_send.return_value = (True, {"platform": "weixin"})
        row = MagicMock()
        row.id, row.content = 7, "测试念头内容"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row
        result = _run(ActiveConsciousnessService.retry_thought(7))
        assert result["success"] is True
        mock_send.assert_called_once()
        assert "测试念头内容" in str(mock_send.call_args)

    @patch("services.active_consciousness_service.active_engine")
    def test_retry_missing_thought(self, mock_engine):
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
        result = _run(ActiveConsciousnessService.retry_thought(999))
        assert result["success"] is False
        assert "不存在" in result["error"]

    @patch("services.active_consciousness_service.check_send_protection")
    @patch("services.active_consciousness_service.active_engine")
    def test_retry_blocked_by_protection(self, mock_engine, mock_protect):
        mock_protect.return_value = (False, "夜间免打扰")
        row = MagicMock()
        row.id, row.content = 3, "x"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row
        result = _run(ActiveConsciousnessService.retry_thought(3))
        assert result["success"] is False
        assert "免打扰" in result["error"] or "保护" in result["error"]
