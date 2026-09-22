"""深夜适配因子测试"""
from services.active_consciousness_service import _deep_night_factor


class TestDeepNightFactor:
    def test_daytime_full_factor(self):
        assert _deep_night_factor(12.0, 23.5, 7.0, 0.3) == 1.0

    def test_midnight_reduced_factor(self):
        assert _deep_night_factor(2.0, 23.5, 7.0, 0.3) == 0.3

    def test_late_evening_reduced(self):
        assert _deep_night_factor(23.75, 23.5, 7.0, 0.3) == 0.3

    def test_early_morning_reduced(self):
        assert _deep_night_factor(6.5, 23.5, 7.0, 0.3) == 0.3

    def test_boundary_start_exclusive(self):
        assert _deep_night_factor(23.5, 23.5, 7.0, 0.3) == 1.0

    def test_no_midnight_cross(self):
        assert _deep_night_factor(23.0, 22.0, 23.5, 0.5) == 0.5
        assert _deep_night_factor(10.0, 22.0, 23.5, 0.5) == 1.0
