"""
天气服务 - 高德地图 API
"""
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger("hermes.weather")


class WeatherService:
    """天气服务 - 高德地图 API"""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_weather: Optional[Dict] = None

    async def get_weather(
        self,
        city: str = "北京",
        cache_ttl: int = 3600,
        temp_threshold: float = 5.0
    ) -> Dict:
        """
        获取天气信息（带缓存）

        Returns:
            {
                "current": {"weather": "晴", "temp": 25},
                "future": {"weather": "阴", "temp": 20},
                "city": "北京",
                "weather_changed": bool,
                "change_type": "type" | "temp" | "both" | None
            }
        """
        cache_key = f"weather_{city}"

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < cache_ttl:
                return cached["data"]

        # 调用高德地图 API
        weather = await self._fetch_weather_from_amap(city)

        # 检查天气变化
        weather["weather_changed"] = False
        weather["change_type"] = None

        if self._last_weather:
            change = self._detect_weather_change(
                self._last_weather, weather, temp_threshold
            )
            if change:
                weather["weather_changed"] = True
                weather["change_type"] = change

        # 更新缓存和上次天气
        self._cache[cache_key] = {
            "data": weather,
            "timestamp": time.time()
        }
        self._last_weather = weather

        return weather

    def _detect_weather_change(
        self,
        old_weather: Dict,
        new_weather: Dict,
        temp_threshold: float = 5.0
    ) -> Optional[str]:
        """
        检测天气变化

        Returns:
            "type" - 天气类型变化
            "temp" - 温度显著变化
            "both" - 两者都变化
            None - 无显著变化
        """
        type_changed = (
            old_weather.get("current", {}).get("weather") !=
            new_weather.get("current", {}).get("weather")
        )

        temp_diff = abs(
            old_weather.get("current", {}).get("temp", 0) -
            new_weather.get("current", {}).get("temp", 0)
        )
        temp_changed = temp_diff >= temp_threshold

        if type_changed and temp_changed:
            return "both"
        elif type_changed:
            return "type"
        elif temp_changed:
            return "temp"
        return None

    async def _fetch_weather_from_amap(self, city: str) -> Dict:
        """从高德地图 API 获取天气"""
        # TODO: 实现高德地图 API 调用
        # 临时返回模拟数据
        return {
            "current": {"weather": "晴", "temp": 25},
            "future": {"weather": "阴", "temp": 20},
            "city": city
        }
