"""
天气服务 - 高德地图 API
"""
import json
import time
import logging
import urllib.request
import urllib.parse
from typing import Dict, Optional

logger = logging.getLogger("hermes.weather")


class WeatherService:
    """天气服务 - 高德地图 API"""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_weather: Dict[str, Dict] = {}  # 按城市存储

    async def get_weather(
        self,
        amap_key: str = "",
        adcode: str = "370100",
        cache_ttl: int = 3600,
        temp_threshold: float = 5.0
    ) -> Dict:
        """
        获取天气信息（带缓存）

        Args:
            amap_key: 高德开放平台 Key
            adcode: 城市编码
            cache_ttl: 缓存时长（秒）
            temp_threshold: 温度变化阈值

        Returns:
            {
                "current": {"weather": "晴", "temp": 25, "city": "济南"},
                "future": None,  # base 模式不返回预报
                "city": "济南",
                "weather_changed": bool,
                "change_type": "type" | "temp" | "both" | None,
                "success": bool,
                "error": str | None
            }
        """
        cache_key = f"weather_{adcode}"

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < cache_ttl:
                return cached["data"]

        # 调用高德地图 API
        weather = await self._fetch_weather_from_amap(amap_key, adcode)

        # 检查天气变化
        weather["weather_changed"] = False
        weather["change_type"] = None

        if weather.get("success") and adcode in self._last_weather:
            change = self._detect_weather_change(
                self._last_weather[adcode], weather, temp_threshold
            )
            if change:
                weather["weather_changed"] = True
                weather["change_type"] = change

        # 更新缓存和上次天气
        if weather.get("success"):
            self._cache[cache_key] = {
                "data": weather,
                "timestamp": time.time()
            }
            self._last_weather[adcode] = weather

        return weather

    def _detect_weather_change(
        self,
        old_weather: Dict,
        new_weather: Dict,
        temp_threshold: float = 5.0
    ) -> Optional[str]:
        """检测天气变化

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

        old_temp = old_weather.get("current", {}).get("temp")
        new_temp = new_weather.get("current", {}).get("temp")

        # 如果任一温度缺失，跳过温度比较
        if old_temp is None or new_temp is None:
            temp_changed = False
        else:
            try:
                temp_diff = abs(float(old_temp) - float(new_temp))
                temp_changed = temp_diff >= temp_threshold
            except (ValueError, TypeError):
                temp_changed = False

        if type_changed and temp_changed:
            return "both"
        elif type_changed:
            return "type"
        elif temp_changed:
            return "temp"
        return None

    async def _fetch_weather_from_amap(self, amap_key: str, adcode: str) -> Dict:
        """
        从高德地图 API 获取天气

        Args:
            amap_key: 高德开放平台 Key
            adcode: 城市编码

        Returns:
            {
                "current": {"weather": "晴", "temp": 25, "city": "济南"},
                "city": "济南",
                "success": bool,
                "error": str | None
            }
        """
        if not amap_key:
            logger.warning("高德 API Key 未配置")
            return {
                "current": None,
                "city": "",
                "success": False,
                "error": "高德 API Key 未配置"
            }

        try:
            params = urllib.parse.urlencode({
                "city": adcode,
                "key": amap_key,
                "extensions": "base",
            })
            url = f"https://restapi.amap.com/v3/weather/weatherInfo?{params}"

            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "hermes-active/1.0")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("status") == "1" and data.get("lives"):
                live = data["lives"][0]
                return {
                    "current": {
                        "weather": live.get("weather", ""),
                        "temp": live.get("temperature", ""),
                        "humidity": live.get("humidity", ""),
                        "winddirection": live.get("winddirection", ""),
                    },
                    "city": live.get("city", ""),
                    "success": True,
                    "error": None
                }
            else:
                error_msg = data.get("info", "未知错误")
                logger.error("高德 API 返回错误: %s", error_msg)
                return {
                    "current": None,
                    "city": "",
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error("高德 API 调用失败: %s", e)
            return {
                "current": None,
                "city": "",
                "success": False,
                "error": str(e)
            }
