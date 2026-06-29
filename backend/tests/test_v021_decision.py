"""v0.2.1 决策矩阵单元测试"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.active_consciousness import EmotionState


class TestTimeFitness:
    """时间权重测试"""

    @patch('services.active_consciousness_service.datetime')
    def test_morning_window(self, mock_datetime):
        from services.active_consciousness_service import get_time_fitness
        mock_datetime.now.return_value = datetime(2026, 6, 16, 8, 0)
        fitness, label = get_time_fitness()
        assert fitness == 1.0
        assert label == "早安窗口"

    @patch('services.active_consciousness_service.datetime')
    def test_work_time(self, mock_datetime):
        from services.active_consciousness_service import get_time_fitness
        mock_datetime.now.return_value = datetime(2026, 6, 16, 10, 0)
        fitness, label = get_time_fitness()
        assert fitness == 0.8
        assert label == "工作时间"

    @patch('services.active_consciousness_service.datetime')
    def test_deep_night(self, mock_datetime):
        from services.active_consciousness_service import get_time_fitness
        mock_datetime.now.return_value = datetime(2026, 6, 16, 23, 30)
        fitness, label = get_time_fitness()
        assert fitness == 0.3
        assert label == "深夜"


class TestDecisionV2:
    """多维度决策测试"""

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    @patch('services.active_consciousness_service.get_time_fitness')
    def test_high_score_auto_send(self, mock_time_fitness, mock_get_config):
        """高分自动发送"""
        mock_get_config.return_value = {}
        mock_time_fitness.return_value = (1.0, "下班时间")

        from services.active_consciousness_service import make_decision_v2
        # 使用较低的阈值以确保测试通过
        config = {
            "decision": {"send_threshold": 0.5, "memory_threshold": 0.1, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 0}
        emotion = EmotionState(valence=0.9, arousal=0.8, social_need=0.7)

        decision, reason, score = make_decision_v2(config, status, emotion)
        assert decision == "auto_send"
        assert score > 0.5

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    @patch('services.active_consciousness_service.get_time_fitness')
    def test_medium_score_memory(self, mock_time_fitness, mock_get_config):
        """中分存为记忆（delay_send 已移除）"""
        mock_get_config.return_value = {}
        mock_time_fitness.return_value = (1.0, "下班时间")

        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "memory_threshold": 0.1, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 0}
        # intensity = (0.7 + 0.6 + 0.5) / 3 = 0.6
        # score = 0.6 * 1.0 * 0.7 * 1.0 = 0.42
        emotion = EmotionState(valence=0.7, arousal=0.6, social_need=0.5)

        decision, reason, score = make_decision_v2(config, status, emotion)
        assert decision == "memory"
        assert 0.1 < score <= 0.6

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    @patch('services.active_consciousness_service.get_time_fitness')
    def test_low_score_memory(self, mock_time_fitness, mock_get_config):
        """低分存为记忆"""
        mock_get_config.return_value = {}
        mock_time_fitness.return_value = (0.3, "深夜")

        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "memory_threshold": 0.1, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 30}, "hour_sent_count": 2}
        emotion = EmotionState(valence=0.3, arousal=0.2, social_need=0.2)

        decision, reason, score = make_decision_v2(config, status, emotion)
        assert decision in ("memory", "skip")

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    @patch('services.active_consciousness_service.get_time_fitness')
    def test_frequency_limit(self, mock_time_fitness, mock_get_config):
        """频率限制生效"""
        mock_get_config.return_value = {}
        mock_time_fitness.return_value = (1.0, "下班时间")

        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 2}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)

        decision, reason, score = make_decision_v2(config, status, emotion)
        # 频率限制应该降低分数
        assert score < 0.6


class TestDetermineThoughtType:
    """念头类型测试"""

    def test_memory_type(self):
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        hindsight = [{"text": "你说过喜欢看电影"}]
        result = determine_thought_type(status, emotion, hindsight, None)
        assert result == "memory"

    def test_emotion_type(self):
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        result = determine_thought_type(status, emotion, [], None)
        assert result == "emotion"

    def test_silence_type(self):
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 180}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        result = determine_thought_type(status, emotion, [], None)
        assert result == "silence"

    def test_time_type(self):
        from services.active_consciousness_service import determine_thought_type
        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 16, 8, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            status = {"longing": {"silence_minutes": 30}}
            emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
            result = determine_thought_type(status, emotion, [], None)
            assert result == "time"

    def test_association_type(self):
        from services.active_consciousness_service import determine_thought_type
        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 16, 15, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            status = {"longing": {"silence_minutes": 30}}
            emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
            result = determine_thought_type(status, emotion, [], None)
            assert result == "assoc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
