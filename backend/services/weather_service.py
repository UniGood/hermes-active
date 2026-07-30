"""
天气服务 - 内存缓存 + 多 Provider（高德/和风）
"""
import json
import logging
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

from models.passive_consciousness import WeatherData, ForecastDay

logger = logging.getLogger("hermes.weather")


class WeatherService:
    """天气服务 - 内存缓存 + 多 Provider"""

    # 类变量：内存缓存
    _cache: Optional[WeatherData] = None
    _cache_time: Optional[datetime] = None
    _cache_lock = threading.Lock()

    @classmethod
    def get_weather(cls, force_refresh: bool = False) -> Optional[WeatherData]:
        """
        获取天气数据

        优先从内存缓存读取，缓存过期或不存在时从 API 获取。

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            WeatherData 或 None（天气未启用时）
        """
        from services.passive_consciousness_service import PassiveConsciousnessService

        config = PassiveConsciousnessService.get_config()
        weather_config = config.get("weather", {})

        if not weather_config.get("enabled"):
            return None

        # 检查缓存（在锁内）
        with cls._cache_lock:
            if not force_refresh and cls._is_cache_valid(weather_config):
                return cls._cache

        # 缓存过期，从 API 获取（在锁外执行 I/O）
        provider = weather_config.get("provider", "qweather")
        city = weather_config.get("city", "北京")

        try:
            if provider == "amap":
                data = cls._fetch_amap(weather_config, city)
            else:
                data = cls._fetch_qweather(weather_config, city)

            # 更新缓存（在锁内）
            with cls._cache_lock:
                cls._cache = data
                cls._cache_time = datetime.now()
            return data

        except Exception as e:
            logger.error("获取天气失败: %s", e)
            # 失败时返回旧缓存（如果有）
            with cls._cache_lock:
                return cls._cache

    @classmethod
    def _is_cache_valid(cls, weather_config: dict) -> bool:
        """检查缓存是否有效"""
        if cls._cache is None or cls._cache_time is None:
            return False

        cache_hours = weather_config.get("cache_hours", 4)
        elapsed = datetime.now() - cls._cache_time
        return elapsed < timedelta(hours=cache_hours)

    @classmethod
    def clear_cache(cls):
        """清除缓存"""
        with cls._cache_lock:
            cls._cache = None
            cls._cache_time = None

    @classmethod
    def get_cache_status(cls) -> dict:
        """获取缓存状态（调试用）"""
        from services.passive_consciousness_service import PassiveConsciousnessService

        config = PassiveConsciousnessService.get_config()
        weather_config = config.get("weather", {})

        with cls._cache_lock:
            return {
                "has_cache": cls._cache is not None,
                "cache_time": cls._cache_time.isoformat() if cls._cache_time else None,
                "is_valid": cls._is_cache_valid(weather_config),
            }

    @classmethod
    def _http_get(cls, url: str, timeout: int = 10) -> dict:
        """发送 HTTP GET 请求"""
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "hermes-passive-consciousness/1.0")

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @classmethod
    def _fetch_amap(cls, config: dict, city: str) -> WeatherData:
        """从高德地图获取天气数据"""
        api_key = config.get("amap_key", "")
        if not api_key:
            raise ValueError("高德 API Key 未配置")

        # 1. 获取实时天气
        now_params = urllib.parse.urlencode({
            "city": city,
            "key": api_key,
            "extensions": "base",
            "output": "JSON",
        })
        now_url = f"https://restapi.amap.com/v3/weather/weatherInfo?{now_params}"
        now_data = cls._http_get(now_url)

        # 2. 获取天气预报（extensions=all）
        forecast_params = urllib.parse.urlencode({
            "city": city,
            "key": api_key,
            "extensions": "all",
            "output": "JSON",
        })
        forecast_url = f"https://restapi.amap.com/v3/weather/weatherInfo?{forecast_params}"
        forecast_data = cls._http_get(forecast_url)

        # 3. 组装数据
        lives = now_data.get("lives", [])
        if not lives:
            raise ValueError(f"高德 API 返回空数据: {now_data}")

        live = lives[0]
        forecasts_list = forecast_data.get("forecasts", [])
        forecasts = forecasts_list[0].get("casts", []) if forecasts_list else []

        return WeatherData(
            city=live.get("city", city),
            weather=live.get("weather", ""),
            weather_code=live.get("weathercode", ""),
            temperature=int(live.get("temperature", 0)),
            humidity=int(live.get("humidity", 0)),
            feels_like=int(live.get("temperature", 0)),  # 高德无体感温度
            pressure=0,  # 高德无气压
            visibility=0,  # 高德无能见度
            wind_dir=live.get("winddirection", ""),
            wind_scale=live.get("windpower", ""),
            wind_speed=0,  # 高德无风速
            uv_index=0,  # 高德无紫外线
            uv_desc="",
            dressing="",
            comfort="",
            cold_risk="",
            forecast=[
                ForecastDay(
                    date=f.get("date", ""),
                    weather=f.get("dayweather", ""),
                    weather_code="",
                    temp_min=int(f.get("nighttemp", 0)),
                    temp_max=int(f.get("daytemp", 0)),
                    wind_dir=f.get("daywind", ""),
                    wind_scale=f.get("daypower", ""),
                )
                for f in forecasts
            ],
            updated_at=datetime.now(),
            provider="amap",
            raw_data={"now": now_data, "forecast": forecast_data},
        )

    @classmethod
    def _fetch_qweather(cls, config: dict, city: str) -> WeatherData:
        """从和风天气获取天气数据"""
        raise NotImplementedError("和风天气 API 将在下一步实现")
