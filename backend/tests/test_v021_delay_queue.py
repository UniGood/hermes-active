"""v0.2.1 延迟队列单元测试"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.active_consciousness import EmotionState, DelayedThought


class TestDelayedThought:
    """DelayedThought 数据类测试"""

    def test_to_dict(self):
        thought = DelayedThought(
            id=1,
            content="测试",
            thought_type="emotion",
            score=0.45,
            created_at="2026-06-16T10:30:00"
        )
        d = thought.to_dict()
        assert d["id"] == 1
        assert d["content"] == "测试"
        assert d["score"] == 0.45

    def test_from_dict(self):
        d = {
            "id": 1,
            "content": "测试",
            "thought_type": "emotion",
            "score": 0.45,
            "created_at": "2026-06-16T10:30:00"
        }
        thought = DelayedThought.from_dict(d)
        assert thought.id == 1
        assert thought.score == 0.45

    def test_default_values(self):
        thought = DelayedThought(
            id=1,
            content="测试",
            thought_type="emotion",
            score=0.45,
            created_at="2026-06-16T10:30:00"
        )
        assert thought.retry_count == 0
        assert thought.next_retry_at == ""
        assert thought.emotion_snapshot == {}


class TestGetDelayedThoughts:
    """获取延迟队列测试"""

    @patch('services.active_consciousness_service.ActiveSession')
    @patch('services.active_consciousness_service.ConfigService')
    def test_empty_queue(self, mock_config_service, mock_session):
        """空队列返回空列表"""
        mock_config_service.get_config.return_value = None
        from services.active_consciousness_service import get_delayed_thoughts
        result = get_delayed_thoughts()
        assert result == []

    @patch('services.active_consciousness_service.ActiveSession')
    @patch('services.active_consciousness_service.ConfigService')
    def test_parse_queue(self, mock_config_service, mock_session):
        """正确解析队列"""
        import json
        queue_data = [
            {
                "id": 1,
                "content": "测试念头",
                "thought_type": "emotion",
                "score": 0.45,
                "created_at": "2026-06-16T10:30:00"
            }
        ]
        mock_config_service.get_config.return_value = json.dumps(queue_data)
        from services.active_consciousness_service import get_delayed_thoughts
        result = get_delayed_thoughts()
        assert len(result) == 1
        assert result[0].content == "测试念头"


class TestSaveDelayedThoughts:
    """保存延迟队列测试"""

    @patch('services.active_consciousness_service.ActiveSession')
    @patch('services.active_consciousness_service.ConfigService')
    def test_save_thoughts(self, mock_config_service, mock_session):
        """正确保存队列"""
        from services.active_consciousness_service import save_delayed_thoughts
        thoughts = [
            DelayedThought(
                id=1,
                content="测试",
                thought_type="emotion",
                score=0.45,
                created_at="2026-06-16T10:30:00"
            )
        ]
        result = save_delayed_thoughts(thoughts)
        assert result == True
        mock_config_service.set_config.assert_called_once()


class TestAddToDelayQueue:
    """添加到延迟队列测试"""

    @patch('services.active_consciousness_service.save_delayed_thoughts')
    @patch('services.active_consciousness_service.get_delayed_thoughts')
    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_add_thought(self, mock_get_config, mock_get_thoughts, mock_save):
        """添加念头到队列"""
        mock_get_config.return_value = {"delay": {"max_queue_size": 10}}
        mock_get_thoughts.return_value = []
        mock_save.return_value = True

        from services.active_consciousness_service import add_to_delay_queue
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        result = add_to_delay_queue("测试内容", "emotion", 0.45, emotion)
        assert result == True
        assert mock_save.call_count == 1

    @patch('services.active_consciousness_service.save_delayed_thoughts')
    @patch('services.active_consciousness_service.get_delayed_thoughts')
    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_queue_size_limit(self, mock_get_config, mock_get_thoughts, mock_save):
        """队列大小限制生效"""
        mock_get_config.return_value = {"delay": {"max_queue_size": 2}}
        # 现有 2 个念头
        mock_get_thoughts.return_value = [
            DelayedThought(id=1, content="旧念头1", thought_type="emotion", score=0.3, created_at="2026-06-16T10:00:00"),
            DelayedThought(id=2, content="旧念头2", thought_type="emotion", score=0.4, created_at="2026-06-16T10:01:00"),
        ]
        mock_save.return_value = True

        from services.active_consciousness_service import add_to_delay_queue
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        result = add_to_delay_queue("新念头", "emotion", 0.5, emotion)
        assert result == True
        # 验证保存时队列长度为 2（移除了最旧的）
        saved_thoughts = mock_save.call_args[0][0]
        assert len(saved_thoughts) == 2


class TestReevaluateDelayedThoughts:
    """重评估延迟队列测试"""

    @patch('services.active_consciousness_service.save_delayed_thoughts')
    @patch('services.active_consciousness_service.get_delayed_thoughts')
    @patch('services.active_consciousness_service.get_time_fitness')
    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_empty_queue(self, mock_get_config, mock_time_fitness, mock_get_thoughts, mock_save):
        """空队列返回零统计"""
        mock_get_config.return_value = {}
        mock_time_fitness.return_value = (0.8, "工作时间")
        mock_get_thoughts.return_value = []

        from services.active_consciousness_service import reevaluate_delayed_thoughts
        import asyncio
        config = {"delay": {"max_retry": 3}, "decision": {"send_threshold": 0.6}}
        status = {"longing": {"silence_minutes": 120}, "hour_sent_count": 0}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)

        stats = asyncio.run(reevaluate_delayed_thoughts(config, status, emotion))
        assert stats == {"sent": 0, "discarded": 0, "kept": 0}

    @patch('services.active_consciousness_service.save_delayed_thoughts')
    @patch('services.active_consciousness_service.get_delayed_thoughts')
    @patch('services.active_consciousness_service.get_time_fitness')
    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_discard_max_retry(self, mock_get_config, mock_time_fitness, mock_get_thoughts, mock_save):
        """超过最大重试次数自动丢弃"""
        mock_get_config.return_value = {}
        mock_time_fitness.return_value = (0.8, "工作时间")
        mock_get_thoughts.return_value = [
            DelayedThought(id=1, content="旧念头", thought_type="emotion", score=0.3, created_at="2026-06-16T10:00:00", retry_count=3)
        ]
        mock_save.return_value = True

        from services.active_consciousness_service import reevaluate_delayed_thoughts
        import asyncio
        config = {"delay": {"max_retry": 3}, "decision": {"send_threshold": 0.6}}
        status = {"longing": {"silence_minutes": 120}, "hour_sent_count": 0}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)

        stats = asyncio.run(reevaluate_delayed_thoughts(config, status, emotion))
        assert stats["discarded"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
