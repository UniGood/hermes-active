"""
天气服务 - 内存缓存 + 多 Provider（高德/和风）
"""
import json
import logging
import threading
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

        with cls._cache_lock:
            # 检查缓存是否有效
            if not force_refresh and cls._is_cache_valid(weather_config):
                return cls._cache

            # 缓存过期，从 API 获取
            provider = weather_config.get("provider", "qweather")
            city = weather_config.get("city", "北京")

            try:
                if provider == "amap":
                    data = cls._fetch_amap(weather_config, city)
                else:
                    data = cls._fetch_qweather(weather_config, city)

                # 更新缓存
                cls._cache = data
                cls._cache_time = datetime.now()
                return data

            except Exception as e:
                logger.error("获取天气失败: %s", e)
                # 失败时返回旧缓存（如果有）
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
        raise NotImplementedError("高德地图 API 将在下一步实现")

    @classmethod
    def _fetch_qweather(cls, config: dict, city: str) -> WeatherData:
        """从和风天气获取天气数据"""
        raise NotImplementedError("和风天气 API 将在下一步实现")
