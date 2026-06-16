"""v0.2.1 情绪演化单元测试"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.active_consciousness import EmotionState, DominantEmotion


class TestEmotionState:
    """EmotionState 数据类测试"""

    def test_default_values(self):
        state = EmotionState()
        assert state.valence == 0.5
        assert state.arousal == 0.3
        assert state.dominant == "calm"
        assert state.social_need == 0.3

    def test_boundary_clamping(self):
        state = EmotionState(valence=1.5, arousal=-0.1, social_need=2.0)
        assert state.valence == 1.0
        assert state.arousal == 0.0
        assert state.social_need == 1.0

    def test_to_dict(self):
        state = EmotionState(valence=0.6, arousal=0.4)
        d = state.to_dict()
        assert d["valence"] == 0.6
        assert d["arousal"] == 0.4
        assert "updated_at" in d

    def test_from_dict(self):
        d = {"valence": 0.7, "arousal": 0.5, "dominant": "happy"}
        state = EmotionState.from_dict(d)
        assert state.valence == 0.7
        assert state.dominant == "happy"

    def test_intensity(self):
        state = EmotionState(valence=0.6, arousal=0.4, social_need=0.3)
        expected = (0.6 + 0.4 + 0.3) / 3
        assert abs(state.intensity() - expected) < 0.01

    def test_is_stale_false(self):
        state = EmotionState(updated_at=datetime.now().isoformat())
        assert state.is_stale(minutes=60) == False

    def test_is_stale_true(self):
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        state = EmotionState(updated_at=old_time)
        assert state.is_stale(minutes=60) == True


class TestEvolveEmotion:
    """情绪演化测试"""

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_no_evolution(self, mock_get_config):
        """无时间流逝不演化"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5, social_need=0.3)
        evolved = evolve_emotion(last, minutes_since_update=0)
        assert evolved.arousal == 0.5
        assert evolved.social_need == 0.3

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_arousal_decay(self, mock_get_config):
        """arousal 随时间衰减"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.8)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.arousal < 0.8

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_social_need_growth(self, mock_get_config):
        """social_need 随时间增长"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(social_need=0.2)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.social_need > 0.2

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_valence_regression_high(self, mock_get_config):
        """高效价回归中性"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(valence=0.8)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.valence < 0.8

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_valence_regression_low(self, mock_get_config):
        """低效价回归中性"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(valence=0.2)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.valence > 0.2

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_boundary_minutes_negative(self, mock_get_config):
        """负数时间视为0"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5)
        evolved = evolve_emotion(last, minutes_since_update=-10)
        assert evolved.arousal == 0.5

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_boundary_minutes_max(self, mock_get_config):
        """超过24小时截断"""
        mock_get_config.return_value = {
            "emotion": {
                "decay_rate": "0.02",
                "social_need_growth": "0.01",
                "valence_regression": "0.1"
            }
        }
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5)
        evolved = evolve_emotion(last, minutes_since_update=2000)
        assert evolved.arousal >= 0.1  # 最低值


class TestCalculateDominant:
    """主导情绪计算测试"""

    def test_high_social_need_positive(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.6, 0.5, 0.8) == "yearning"

    def test_high_social_need_negative(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.4, 0.5, 0.8) == "anxious"

    def test_medium_social_need_positive(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.6, 0.5, 0.6) == "longing"

    def test_low_arousal(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.5, 0.2, 0.3) == "calm"

    def test_high_valence_high_arousal(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.8, 0.7, 0.3) == "happy"

    def test_high_valence_low_arousal(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.8, 0.5, 0.3) == "content"


class TestMergeEmotion:
    """情绪合并测试"""

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_normal_merge(self, mock_get_config):
        mock_get_config.return_value = {
            "emotion": {
                "weight_evolved": "0.4",
                "weight_llm": "0.6"
            }
        }
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(valence=0.4, arousal=0.3, social_need=0.2)
        llm = EmotionState(valence=0.6, arousal=0.5, social_need=0.4)
        merged = merge_emotion(evolved, llm)
        # 权重 0.4 + 0.6
        expected_valence = 0.4 * 0.4 + 0.6 * 0.6
        assert abs(merged.valence - expected_valence) < 0.01

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_high_arousal_llm_uses_llm_dominant(self, mock_get_config):
        """LLM 高唤醒度时采用其主导情绪"""
        mock_get_config.return_value = {
            "emotion": {
                "weight_evolved": "0.4",
                "weight_llm": "0.6"
            }
        }
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(dominant="calm")
        llm = EmotionState(arousal=0.7, dominant="happy")
        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "happy"

    @patch('services.active_consciousness_service.ActiveConsciousnessService.get_config')
    def test_low_arousal_llm_keeps_evolved_dominant(self, mock_get_config):
        """LLM 低唤醒度时保留演化值的主导情绪"""
        mock_get_config.return_value = {
            "emotion": {
                "weight_evolved": "0.4",
                "weight_llm": "0.6"
            }
        }
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(dominant="longing")
        llm = EmotionState(arousal=0.5, dominant="calm")
        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "longing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
