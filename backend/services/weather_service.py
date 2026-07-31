"""
天气服务 - 高德地图 API + 和风天气 API
"""
import json
import time
import logging
import urllib.request
import urllib.parse
from typing import Dict, Optional, List

logger = logging.getLogger("hermes.weather")

# 和风天气常用城市 ID 映射
QWEATHER_CITY_IDS = {
    "beijing": "101010100", "北京": "101010100",
    "shanghai": "101020100", "上海": "101020100",
    "guangzhou": "101280101", "广州": "101280101",
    "shenzhen": "101280601", "深圳": "101280601",
    "chengdu": "101270101", "成都": "101270101",
    "hangzhou": "101210101", "杭州": "101210101",
    "wuhan": "101200101", "武汉": "101200101",
    "nanjing": "101190101", "南京": "101190101",
    "xian": "101110101", "西安": "101110101",
    "chongqing": "101040100", "重庆": "101040100",
    "tianjin": "101030100", "天津": "101030100",
    "jinan": "101120101", "济南": "101120101",
    "qingdao": "101120201", "青岛": "101120201",
    "dalian": "101070201", "大连": "101070201",
    "xiamen": "101230201", "厦门": "101230201",
    "kunming": "101290101", "昆明": "101290101",
    "hefei": "101220101", "合肥": "101220101",
    "fuzhou": "101230101", "福州": "101230101",
    "harbin": "101050101", "哈尔滨": "101050101",
    "nanning": "101300101", "南宁": "101300101",
    "nanchang": "101240101", "南昌": "101240101",
    "guiyang": "101260101", "贵阳": "101260101",
}


class WeatherService:
    """天气服务 - 高德地图 API + 和风天气 API"""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_weather: Dict[str, Dict] = {}  # 按城市存储

    async def get_weather(
        self,
        amap_key: str = "",
        adcode: str = "370100",
        cache_ttl: int = 3600,
        temp_threshold: float = 5.0,
        forecast_days: int = 0,
        # 新增参数（可选，向后兼容）
        provider: str = "amap",
        city: str = "",
        qweather_key: str = "",
        qweather_geo_url: str = "https://geoapi.qweather.com/v2/city/lookup",
        qweather_weather_url: str = "https://devapi.qweather.com/v7/weather/now",
    ) -> Dict:
        """
        获取天气信息（带缓存）

        Args:
            amap_key: 高德开放平台 Key
            adcode: 城市编码（高德）
            cache_ttl: 缓存时长（秒）
            temp_threshold: 温度变化阈值
            forecast_days: 预报天数（0=仅今天实况；1-3=今天+未来 N 天预报）
            provider: 天气服务提供商（amap/qweather）
            city: 城市名称（和风天气）
            qweather_key: 和风天气 API Key
            qweather_geo_url: 和风 GeoAPI URL
            qweather_weather_url: 和风天气 API URL

        Returns:
            {
                "current": {"weather": "晴", "temp": 25, "city": "济南"},
                "forecast": [{"date": "2026-06-22", "dayweather": "晴", "daytemp": 32, ...}],
                "city": "济南",
                "weather_changed": bool,
                "change_type": "type" | "temp" | "both" | None,
                "success": bool,
                "error": str | None
            }
        """
        # 确定缓存键
        cache_key = f"weather_{provider}_{adcode}_{city}_{forecast_days}"

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < cache_ttl:
                return cached["data"]

        # 根据 provider 调用不同的 API
        if provider == "qweather":
            weather = await self._fetch_weather_from_qweather(
                qweather_key, city, qweather_geo_url, qweather_weather_url, forecast_days
            )
        else:
            # 默认使用高德
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

    def get_weather_sync(self, **kwargs) -> Dict:
        """同步版本的 get_weather，用于非异步上下文（如 get_status）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已有事件循环在运行，用线程池执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.get_weather(**kwargs))
                return future.result(timeout=30)
        else:
            return asyncio.run(self.get_weather(**kwargs))

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

    async def _fetch_weather_from_qweather(
        self,
        api_key: str,
        city: str,
        geo_url: str,
        weather_url: str,
        forecast_days: int = 0
    ) -> Dict:
        """
        从和风天气 API 获取天气

        Args:
            api_key: 和风天气 API Key
            city: 城市名称
            geo_url: GeoAPI URL
            weather_url: 天气 API URL
            forecast_days: 预报天数

        Returns:
            {
                "current": {"weather": "晴", "temp": 25, "city": "北京"},
                "forecast": [...],
                "city": "北京",
                "success": bool,
                "error": str | None
            }
        """
        if not api_key:
            logger.warning("和风天气 API Key 未配置")
            return {
                "current": None,
                "forecast": [],
                "city": "",
                "success": False,
                "error": "和风天气 API Key 未配置"
            }

        try:
            # 1. 查询城市 ID
            city_id = await self._get_qweather_city_id(geo_url, api_key, city)

            # 2. 获取实时天气
            now_params = urllib.parse.urlencode({
                "location": city_id,
                "key": api_key,
            })
            now_url = f"{weather_url}?{now_params}"
            now_data = await self._http_get(now_url)

            # 3. 获取天气预报（如果需要）
            forecast_data = []
            if forecast_days >= 1:
                forecast_url = f"https://devapi.qweather.com/v7/weather/3d?{now_params}"
                forecast_resp = await self._http_get(forecast_url)
                forecast_data = forecast_resp.get("daily", [])

            # 4. 组装数据
            now = now_data.get("now", {})

            current = {
                "weather": now.get("text", ""),
                "temp": now.get("temp", ""),
                "humidity": now.get("humidity", ""),
                "winddirection": now.get("windDir", ""),
            }

            forecast = []
            for f in forecast_data[:max(1, forecast_days)]:
                forecast.append({
                    "date": f.get("fxDate", ""),
                    "dayweather": f.get("textDay", ""),
                    "nightweather": f.get("textNight", ""),
                    "daytemp": f.get("tempMax", ""),
                    "nighttemp": f.get("tempMin", ""),
                    "daywind": f.get("windDirDay", ""),
                    "daypower": f.get("windScaleDay", ""),
                })

            return {
                "current": current,
                "forecast": forecast,
                "city": city,
                "success": True,
                "error": None
            }

        except Exception as e:
            logger.error("和风天气 API 调用失败: %s", e)
            return {
                "current": None,
                "forecast": [],
                "city": "",
                "success": False,
                "error": str(e)
            }

    async def _get_qweather_city_id(self, geo_url: str, api_key: str, city: str) -> str:
        """查询和风天气城市 ID"""
        city_key = city.lower().strip()
        city_id = QWEATHER_CITY_IDS.get(city_key)

        if city_id:
            return city_id

        # 调用 GeoAPI 查询
        params = urllib.parse.urlencode({
            "location": city,
            "key": api_key,
        })
        url = f"{geo_url}?{params}"
        data = await self._http_get(url)

        if data.get("code") == "200" and data.get("location"):
            return data["location"][0]["id"]

        raise ValueError(f"未找到城市: {city}")

    def clear_cache(self):
        """清除天气缓存"""
        self._cache.clear()
        self._last_weather.clear()

    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        now = time.time()
        entries = {}
        for key, cached in self._cache.items():
            age = now - cached["timestamp"]
            entries[key] = {
                "age_seconds": round(age, 1),
                "has_data": cached["data"].get("success", False),
            }
        return {
            "entries": len(entries),
            "details": entries,
        }

    async def _http_get(self, url: str, timeout: int = 10) -> Dict:
        """发送 HTTP GET 请求"""
        import io
        import gzip

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "hermes-passive-consciousness/1.0")

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 检查 Content-Encoding 头
            encoding = resp.headers.get('Content-Encoding', '')
            data = resp.read()

            if encoding == 'gzip' or data[:2] == b'\x1f\x8b':
                data = gzip.decompress(data)

            return json.loads(data.decode("utf-8"))
