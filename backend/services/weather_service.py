"""
天气服务 - 高德地图 API
"""
import json
import time
import logging
import urllib.request
import urllib.parse
from typing import Dict, Optional, List

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
        temp_threshold: float = 5.0,
        forecast_days: int = 0
    ) -> Dict:
        """
        获取天气信息（带缓存）

        Args:
            amap_key: 高德开放平台 Key
            adcode: 城市编码
            cache_ttl: 缓存时长（秒）
            temp_threshold: 温度变化阈值
            forecast_days: 预报天数（0=仅今天实况；1-3=今天+未来 N 天预报）

        Returns:
            {
                "current": {"weather": "晴", "temp": 25, "city": "济南"},  # 仅 forecast_days>=1 时存在
                "forecast": [{"date": "2026-06-22", "dayweather": "晴", "daytemp": 32, ...}],  # forecast_days>=1 时存在
                "city": "济南",
                "weather_changed": bool,
                "change_type": "type" | "temp" | "both" | None,
                "success": bool,
                "error": str | None
            }
        """
        cache_key = f"weather_{adcode}_{forecast_days}"

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < cache_ttl:
                return cached["data"]

        # 调用高德地图 API
        if forecast_days >= 1:
            weather = await self._fetch_forecast_from_amap(amap_key, adcode, forecast_days)
        else:
            weather = await self._fetch_weather_from_amap(amap_key, adcode)

        # 检查天气变化（仅实况场景）
        weather["weather_changed"] = False
        weather["change_type"] = None

        if weather.get("success") and forecast_days == 0 and adcode in self._last_weather:
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
            if forecast_days == 0:
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

    async def _fetch_forecast_from_amap(
        self,
        amap_key: str,
        adcode: str,
        forecast_days: int = 1
    ) -> Dict:
        """
        从高德地图 API 获取预报天气（extensions=all）

        Args:
            amap_key: 高德开放平台 Key
            adcode: 城市编码
            forecast_days: 预报天数（1-3；返回包含今天在内的 N 天数据）

        Returns:
            {
                "current": {"weather": "晴", "temp": 25, "city": "济南"},  # 今天的实况（base）
                "forecast": [{"date": "2026-06-22", "dayweather": "晴", "daytemp": 32, ...}, ...],
                "city": "济南",
                "success": bool,
                "error": str | None
            }
        """
        if not amap_key:
            logger.warning("高德 API Key 未配置")
            return {
                "current": None,
                "forecast": [],
                "city": "",
                "success": False,
                "error": "高德 API Key 未配置"
            }

        try:
            params = urllib.parse.urlencode({
                "city": adcode,
                "key": amap_key,
                "extensions": "all",
            })
            url = f"https://restapi.amap.com/v3/weather/weatherInfo?{params}"

            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "hermes-active/1.0")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("status") == "1":
                city = ""
                current = None
                forecast: List[Dict] = []

                # 注意：extensions=all 时 casts 嵌套在 forecasts[0].casts
                # 文档说预报3天，实际返回包含今天共4天 cast
                forecasts = data.get("forecasts") or []
                if forecasts:
                    first_block = forecasts[0]
                    city = first_block.get("city", "")
                    casts = first_block.get("casts") or []
                    # 当天实况（取第一天的白天天气和温度）
                    if casts:
                        first = casts[0]
                        current = {
                            "weather": first.get("dayweather", ""),
                            "temp": first.get("daytemp", ""),
                            "humidity": "",  # 预报接口不返回湿度
                            "winddirection": first.get("daywind", ""),
                        }
                    # 预报切片
                    for cast in casts[: max(1, forecast_days)]:
                        forecast.append({
                            "date": cast.get("date", ""),
                            "week": cast.get("week", ""),
                            "dayweather": cast.get("dayweather", ""),
                            "nightweather": cast.get("nightweather", ""),
                            "daytemp": cast.get("daytemp", ""),
                            "nighttemp": cast.get("nighttemp", ""),
                            "daywind": cast.get("daywind", ""),
                            "daypower": cast.get("daypower", ""),
                        })

                return {
                    "current": current,
                    "forecast": forecast,
                    "city": city,
                    "success": True,
                    "error": None
                }
            else:
                error_msg = data.get("info", "未知错误")
                logger.error("高德 API 返回错误: %s", error_msg)
                return {
                    "current": None,
                    "forecast": [],
                    "city": "",
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error("高德 API 调用失败: %s", e)
            return {
                "current": None,
                "forecast": [],
                "city": "",
                "success": False,
                "error": str(e)
            }
