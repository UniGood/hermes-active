# backend/tests/test_thought_generator.py
import pytest
from services.thought_generator import ThoughtGenerator


def test_thought_generator_select_time_range():
    """测试根据 arousal 选择时间范围"""
    generator = ThoughtGenerator()
    config = {
        "arousal_low_threshold": 0.3,
        "arousal_high_threshold": 0.7
    }

    # 低 arousal -> 15 天
    assert generator._select_time_range(0.2, config) == 15

    # 中 arousal -> 7 天
    assert generator._select_time_range(0.5, config) == 7

    # 高 arousal -> 1 天
    assert generator._select_time_range(0.8, config) == 1


def test_thought_generator_get_count():
    """测试获取念头数量"""
    generator = ThoughtGenerator()
    config = {
        "count_15d": 3,
        "count_7d": 2,
        "count_3d": 2,
        "count_1d": 1
    }

    assert generator._get_thought_count(15, config) == 3
    assert generator._get_thought_count(7, config) == 2
    assert generator._get_thought_count(1, config) == 1


def test_thought_generator_parse_thoughts():
    """测试解析念头"""
    generator = ThoughtGenerator()

    response = """
    <thought>今天天气真好，心情也变好了</thought>
    <thought>明天要下雨，提醒他带伞</thought>
    """

    thoughts = generator._parse_thoughts(response)
    assert len(thoughts) == 2
    assert thoughts[0]["content"] == "今天天气真好，心情也变好了"
    assert thoughts[1]["content"] == "明天要下雨，提醒他带伞"
