import pytest
from services.weather_service import WeatherService


def test_weather_service_get_weather():
    """测试获取天气信息"""
    service = WeatherService()
    assert callable(service.get_weather)


def test_weather_service_detect_change():
    """测试天气变化检测"""
    service = WeatherService()

    # 天气类型变化
    old = {"current": {"weather": "晴", "temp": 25}}
    new = {"current": {"weather": "阴", "temp": 25}}
    assert service._detect_weather_change(old, new) == "type"

    # 温度变化
    old = {"current": {"weather": "晴", "temp": 20}}
    new = {"current": {"weather": "晴", "temp": 26}}
    assert service._detect_weather_change(old, new) == "temp"

    # 两者都变化
    old = {"current": {"weather": "晴", "temp": 20}}
    new = {"current": {"weather": "阴", "temp": 26}}
    assert service._detect_weather_change(old, new) == "both"

    # 无变化
    old = {"current": {"weather": "晴", "temp": 25}}
    new = {"current": {"weather": "晴", "temp": 25}}
    assert service._detect_weather_change(old, new) is None
