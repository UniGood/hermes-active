# 天气感知功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为被动意识系统添加天气感知能力，支持高德地图和和风天气 API，内存缓存可配置过期时间

**Architecture:** 独立 WeatherService 类，使用类变量实现内存缓存，支持两个天气 Provider（高德/和风），通过配置切换

**Tech Stack:** Python 3, FastAPI, Vue 3, Naive UI, urllib (HTTP 请求)

---

## 文件结构

```
backend/
├── models/
│   └── passive_consciousness.py    # 修改：添加 WeatherData、ForecastDay 数据类
├── services/
│   ├── weather_service.py          # 新增：天气服务核心（缓存 + API 调用）
│   └── passive_consciousness_service.py  # 修改：集成天气到状态查询
└── routers/
    └── passive_consciousness.py    # 修改：天气 API 端点

frontend/src/
├── api/
│   └── passive_consciousness.js    # 修改：添加天气 API 调用
└── views/
    └── PassiveConsciousness.vue    # 修改：天气配置和状态 UI
```

---

## Task 1: 添加天气数据模型

**Files:**
- Modify: `backend/models/passive_consciousness.py`

- [ ] **Step 1: 添加 WeatherData 和 ForecastDay 数据类**

在 `backend/models/passive_consciousness.py` 文件末尾添加：

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ForecastDay:
    """天气预报（单日）"""
    date: str               # 日期 (YYYY-MM-DD)
    weather: str            # 天气状况
    weather_code: str       # 天气代码
    temp_min: int           # 最低温度 (°C)
    temp_max: int           # 最高温度 (°C)
    wind_dir: str           # 风向
    wind_scale: str         # 风力等级


@dataclass
class WeatherData:
    """天气数据"""
    # 基础天气
    city: str               # 城市名
    weather: str            # 天气状况（晴/多云/雨）
    weather_code: str       # 天气代码
    temperature: int        # 当前温度 (°C)
    humidity: int           # 湿度 (%)
    feels_like: int         # 体感温度 (°C)
    pressure: int           # 气压 (hPa)
    visibility: int         # 能见度 (km)

    # 风力信息
    wind_dir: str           # 风向（北风/南风/...）
    wind_scale: str         # 风力等级（3-4级）
    wind_speed: float       # 风速 (km/h)

    # 生活指数
    uv_index: int           # 紫外线指数 (0-11+)
    uv_desc: str            # 紫外线描述（最弱/弱/中等/强/很强）
    dressing: str           # 穿衣建议
    comfort: str            # 舒适度指数
    cold_risk: str          # 感冒风险

    # 天气预报（未来3天）
    forecast: List[ForecastDay] = field(default_factory=list)

    # 元数据
    updated_at: Optional[datetime] = None  # 数据更新时间
    provider: str = ""           # 数据来源（amap/qweather）
    raw_data: dict = field(default_factory=dict)  # 原始 API 响应（调试用）
```

- [ ] **Step 2: 验证模型导入**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from models.passive_consciousness import WeatherData, ForecastDay; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/models/passive_consciousness.py
git commit -m "feat: 添加天气数据模型 WeatherData 和 ForecastDay"
```

---

## Task 2: 创建 WeatherService 核心

**Files:**
- Create: `backend/services/weather_service.py`

- [ ] **Step 1: 创建 WeatherService 基础框架**

创建 `backend/services/weather_service.py`：

```python
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
```

- [ ] **Step 2: 验证导入**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from services.weather_service import WeatherService; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/weather_service.py
git commit -m "feat: 创建 WeatherService 基础框架（缓存 + HTTP 工具）"
```

---

## Task 3: 实现高德地图 API

**Files:**
- Modify: `backend/services/weather_service.py`

- [ ] **Step 1: 实现 _fetch_amap 方法**

在 `backend/services/weather_service.py` 中替换 `_fetch_amap` 方法：

```python
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
```

- [ ] **Step 2: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/weather_service.py
git commit -m "feat: 实现高德地图天气 API 调用"
```

---

## Task 4: 实现和风天气 API

**Files:**
- Modify: `backend/services/weather_service.py`

- [ ] **Step 1: 实现 _fetch_qweather 和 _get_qweather_city_id 方法**

在 `backend/services/weather_service.py` 中替换 `_fetch_qweather` 方法，并添加 `_get_qweather_city_id`：

```python
# 常用城市 ID 映射（避免每次都调用 GeoAPI）
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
    "suzhou": "101190401", "苏州": "101190401",
    "zhengzhou": "101180101", "郑州": "101180101",
    "changsha": "101250101", "长沙": "101250101",
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


@classmethod
def _fetch_qweather(cls, config: dict, city: str) -> WeatherData:
    """从和风天气获取天气数据"""
    api_key = config.get("qweather_key", "")
    geo_url = config.get("qweather_geo_url", "https://geoapi.qweather.com/v2/city/lookup")
    weather_url = config.get("qweather_weather_url", "https://devapi.qweather.com/v7/weather/now")

    if not api_key:
        raise ValueError("和风天气 API Key 未配置")

    # 1. 查询城市 ID
    city_id = cls._get_qweather_city_id(geo_url, api_key, city)

    # 2. 获取实时天气
    now_params = urllib.parse.urlencode({
        "location": city_id,
        "key": api_key,
    })
    now_url = f"{weather_url}?{now_params}"
    now_data = cls._http_get(now_url)

    # 3. 获取天气预报
    forecast_url = f"https://devapi.qweather.com/v7/weather/3d?{now_params}"
    forecast_data = cls._http_get(forecast_url)

    # 4. 获取生活指数
    indices_url = f"https://devapi.qweather.com/v7/indices/1d?type=1,3,5&{now_params}"
    indices_data = cls._http_get(indices_url)

    # 5. 组装数据
    now = now_data.get("now", {})
    forecasts = forecast_data.get("daily", [])
    indices = indices_data.get("daily", [])

    # 解析生活指数
    uv_index = next((i for i in indices if i.get("type") == "5"), {})
    dressing = next((i for i in indices if i.get("type") == "3"), {})
    comfort = next((i for i in indices if i.get("type") == "1"), {})

    return WeatherData(
        city=city,
        weather=now.get("text", ""),
        weather_code=now.get("code", ""),
        temperature=int(now.get("temp", 0)),
        humidity=int(now.get("humidity", 0)),
        feels_like=int(now.get("feelsLike", 0)),
        pressure=int(now.get("pressure", 0)),
        visibility=int(now.get("vis", 0)),
        wind_dir=now.get("windDir", ""),
        wind_scale=now.get("windScale", ""),
        wind_speed=float(now.get("windSpeed", 0)),
        uv_index=int(uv_index.get("level", 0)) if uv_index else 0,
        uv_desc=uv_index.get("text", "") if uv_index else "",
        dressing=dressing.get("text", "") if dressing else "",
        comfort=comfort.get("text", "") if comfort else "",
        cold_risk="",
        forecast=[
            ForecastDay(
                date=f.get("fxDate", ""),
                weather=f.get("textDay", ""),
                weather_code=f.get("codeDay", ""),
                temp_min=int(f.get("tempMin", 0)),
                temp_max=int(f.get("tempMax", 0)),
                wind_dir=f.get("windDirDay", ""),
                wind_scale=f.get("windScaleDay", ""),
            )
            for f in forecasts
        ],
        updated_at=datetime.now(),
        provider="qweather",
        raw_data={"now": now_data, "forecast": forecast_data, "indices": indices_data},
    )


@classmethod
def _get_qweather_city_id(cls, geo_url: str, api_key: str, city: str) -> str:
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
    data = cls._http_get(url)

    if data.get("code") == "200" and data.get("location"):
        return data["location"][0]["id"]

    raise ValueError(f"未找到城市: {city}")
```

- [ ] **Step 2: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/weather_service.py
git commit -m "feat: 实现和风天气 API 调用（含生活指数和城市 ID 查询）"
```

---

## Task 5: 更新配置默认值

**Files:**
- Modify: `backend/services/passive_consciousness_service.py`

- [ ] **Step 1: 添加新的天气配置项**

在 `backend/services/passive_consciousness_service.py` 中找到 `_DEFAULTS` 字典，修改天气相关配置：

```python
_DEFAULTS = {
    # ... 其他配置保持不变 ...
    "passive_consciousness.weather.enabled": "false",
    "passive_consciousness.weather.provider": "qweather",
    "passive_consciousness.weather.city": "北京",
    "passive_consciousness.weather.cache_hours": "4",
    "passive_consciousness.weather.amap_key": "",
    "passive_consciousness.weather.qweather_key": "",
    "passive_consciousness.weather.qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
    "passive_consciousness.weather.qweather_weather_url": "https://devapi.qweather.com/v7/weather/now",
}
```

注意：移除旧的 `weather.adcode` 配置项。

- [ ] **Step 2: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/passive_consciousness_service.py
git commit -m "feat: 更新天气配置项（支持 Provider 选择和缓存时间）"
```

---

## Task 6: 集成天气到状态查询

**Files:**
- Modify: `backend/services/passive_consciousness_service.py`

- [ ] **Step 1: 在 get_status() 中添加天气数据**

在 `backend/services/passive_consciousness_service.py` 的 `get_status()` 方法中，在返回 `return` 语句之前添加：

```python
# 获取天气数据
weather_data = None
try:
    from services.weather_service import WeatherService
    weather = WeatherService.get_weather()
    if weather:
        weather_data = {
            "city": weather.city,
            "weather": weather.weather,
            "temperature": weather.temperature,
            "humidity": weather.humidity,
            "feels_like": weather.feels_like,
            "wind_dir": weather.wind_dir,
            "wind_scale": weather.wind_scale,
            "wind_speed": weather.wind_speed,
            "uv_index": weather.uv_index,
            "uv_desc": weather.uv_desc,
            "dressing": weather.dressing,
            "comfort": weather.comfort,
            "forecast": [
                {
                    "date": f.date,
                    "weather": f.weather,
                    "temp_min": f.temp_min,
                    "temp_max": f.temp_max,
                }
                for f in weather.forecast
            ],
            "updated_at": weather.updated_at.isoformat() if weather.updated_at else None,
            "provider": weather.provider,
        }
except Exception as e:
    logger.warning("获取天气数据失败: %s", e)
```

然后修改返回值，添加 `weather` 字段：

```python
return {
    "enabled": config.get("enabled", False),
    "longing": { ... },
    "chat_heat": { ... },
    "emotional_intensity": { ... },
    "weather": weather_data,  # 新增
}
```

- [ ] **Step 2: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/passive_consciousness_service.py
git commit -m "feat: 集成天气数据到被动意识状态查询"
```

---

## Task 7: 更新天气 API 端点

**Files:**
- Modify: `backend/routers/passive_consciousness.py`

- [ ] **Step 1: 替换 test_weather 端点**

在 `backend/routers/passive_consciousness.py` 中找到 `test_weather` 函数，替换为：

```python
@router.post("/test/weather")
async def test_weather():
    """测试天气感知（强制刷新缓存）"""
    try:
        from services.weather_service import WeatherService

        weather = WeatherService.get_weather(force_refresh=True)
        if not weather:
            return {"success": False, "error": "天气感知未启用或获取失败"}

        return {
            "success": True,
            "data": {
                "city": weather.city,
                "weather": weather.weather,
                "temperature": weather.temperature,
                "humidity": weather.humidity,
                "feels_like": weather.feels_like,
                "pressure": weather.pressure,
                "visibility": weather.visibility,
                "wind_dir": weather.wind_dir,
                "wind_scale": weather.wind_scale,
                "wind_speed": weather.wind_speed,
                "uv_index": weather.uv_index,
                "uv_desc": weather.uv_desc,
                "dressing": weather.dressing,
                "comfort": weather.comfort,
                "cold_risk": weather.cold_risk,
                "forecast": [
                    {
                        "date": f.date,
                        "weather": f.weather,
                        "temp_min": f.temp_min,
                        "temp_max": f.temp_max,
                        "wind_dir": f.wind_dir,
                        "wind_scale": f.wind_scale,
                    }
                    for f in weather.forecast
                ],
                "updated_at": weather.updated_at.isoformat() if weather.updated_at else None,
                "provider": weather.provider,
                "cache_status": WeatherService.get_cache_status(),
            }
        }
    except Exception as e:
        logger.error("测试天气失败: %s", e)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: 添加获取天气端点**

在 `test_weather` 函数之后添加：

```python
@router.get("/weather")
async def get_weather():
    """获取天气数据（优先从缓存读取）"""
    try:
        from services.weather_service import WeatherService

        weather = WeatherService.get_weather()
        if not weather:
            return {"success": False, "error": "天气感知未启用"}

        return {
            "success": True,
            "data": {
                "city": weather.city,
                "weather": weather.weather,
                "temperature": weather.temperature,
                "humidity": weather.humidity,
                "feels_like": weather.feels_like,
                "wind_dir": weather.wind_dir,
                "wind_scale": weather.wind_scale,
                "wind_speed": weather.wind_speed,
                "uv_index": weather.uv_index,
                "uv_desc": weather.uv_desc,
                "dressing": weather.dressing,
                "comfort": weather.comfort,
                "forecast": [
                    {
                        "date": f.date,
                        "weather": f.weather,
                        "temp_min": f.temp_min,
                        "temp_max": f.temp_max,
                    }
                    for f in weather.forecast
                ],
                "updated_at": weather.updated_at.isoformat() if weather.updated_at else None,
                "provider": weather.provider,
                "cache_status": WeatherService.get_cache_status(),
            }
        }
    except Exception as e:
        logger.error("获取天气失败: %s", e)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 3: 添加清除缓存端点**

在 `get_weather` 函数之后添加：

```python
@router.post("/weather/clear-cache")
async def clear_weather_cache():
    """清除天气缓存"""
    try:
        from services.weather_service import WeatherService
        WeatherService.clear_cache()
        return {"success": True, "message": "缓存已清除"}
    except Exception as e:
        logger.error("清除缓存失败: %s", e)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/routers/passive_consciousness.py
git commit -m "feat: 更新天气 API 端点（获取/测试/清除缓存）"
```

---

## Task 8: 更新前端 API 封装

**Files:**
- Modify: `frontend/src/api/passive_consciousness.js`

- [ ] **Step 1: 添加天气 API 方法**

在 `frontend/src/api/passive_consciousness.js` 中添加：

```javascript
/**
 * 获取天气数据（优先从缓存读取）
 */
export function getWeather() {
  return http.get('/passive-consciousness/weather')
}

/**
 * 测试天气感知（强制刷新缓存）
 */
export function testWeather() {
  return http.post('/passive-consciousness/test/weather')
}

/**
 * 清除天气缓存
 */
export function clearWeatherCache() {
  return http.post('/passive-consciousness/weather/clear-cache')
}
```

同时确保在文件末尾的默认导出中包含这些方法：

```javascript
export default {
  // ... 其他方法
  getWeather,
  testWeather,
  clearWeatherCache,
}
```

- [ ] **Step 2: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/api/passive_consciousness.js
git commit -m "feat: 添加天气 API 封装"
```

---

## Task 9: 更新前端配置 UI

**Files:**
- Modify: `frontend/src/views/PassiveConsciousness.vue`

- [ ] **Step 1: 添加天气配置到 config ref**

在 `frontend/src/views/PassiveConsciousness.vue` 中找到 `config` ref，添加 `weather` 字段：

```javascript
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  passive: { enabled: true, inject_emotion: true, inject_heat: true, inject_memory: true, inject_thought: true, thought_max_chars: 200, vibe_max_chars: 50, inject_tag: '[CONSCIOUSNESS_CONTEXT]', time_format: '%H:%M' },
  session: { sources: ['weixin'], time_range_hours: 24, max_messages_per_session: 15, filter_tool_messages: true },
  hindsight: { enabled: true, recall_limit: 5, reflect_enabled: true },
  weather: { enabled: false, provider: 'qweather', city: '北京', cache_hours: 4, amap_key: '', qweather_key: '', qweather_geo_url: 'https://geoapi.qweather.com/v2/city/lookup', qweather_weather_url: 'https://devapi.qweather.com/v7/weather/now' }
})
```

- [ ] **Step 2: 添加天气配置 UI**

在 `frontend/src/views/PassiveConsciousness.vue` 中找到 `<!-- 天气感知（配置已移至「配置管理」页面） -->` 注释，替换为：

```vue
<!-- 天气感知 -->
<n-divider>天气感知</n-divider>
<n-form-item label="启用天气感知">
  <n-switch v-model:value="config.weather.enabled" />
</n-form-item>

<template v-if="config.weather.enabled">
  <n-form-item label="天气服务">
    <n-radio-group v-model:value="config.weather.provider">
      <n-radio value="qweather">和风天气</n-radio>
      <n-radio value="amap">高德地图</n-radio>
    </n-radio-group>
  </n-form-item>

  <n-form-item label="城市">
    <n-input v-model:value="config.weather.city" placeholder="北京" />
  </n-form-item>

  <n-form-item label="缓存时间（小时）">
    <n-input-number
      v-model:value="config.weather.cache_hours"
      :min="1"
      :max="24"
    />
  </n-form-item>

  <n-form-item label="高德 API Key" v-if="config.weather.provider === 'amap'">
    <n-input v-model:value="config.weather.amap_key" placeholder="输入高德 API Key" show-password-on="click" type="password" />
  </n-form-item>

  <n-form-item label="和风 API Key" v-if="config.weather.provider === 'qweather'">
    <n-input v-model:value="config.weather.qweather_key" placeholder="输入和风天气 API Key" show-password-on="click" type="password" />
  </n-form-item>

  <n-form-item label="和风 GeoAPI URL" v-if="config.weather.provider === 'qweather'">
    <n-input v-model:value="config.weather.qweather_geo_url" placeholder="https://geoapi.qweather.com/v2/city/lookup" />
  </n-form-item>

  <n-form-item label="和风天气 URL" v-if="config.weather.provider === 'qweather'">
    <n-input v-model:value="config.weather.qweather_weather_url" placeholder="https://devapi.qweather.com/v7/weather/now" />
  </n-form-item>
</template>
```

- [ ] **Step 3: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/views/PassiveConsciousness.vue
git commit -m "feat: 添加天气配置 UI（Provider 选择、城市、缓存时间）"
```

---

## Task 10: 更新前端状态 UI

**Files:**
- Modify: `frontend/src/views/PassiveConsciousness.vue`

- [ ] **Step 1: 添加天气到 status ref**

在 `frontend/src/views/PassiveConsciousness.vue` 中找到 `status` ref，添加 `weather` 字段：

```javascript
const status = ref({
  enabled: false,
  longing: { score: 0, level: 0, label: 'calm', last_user_msg_at: null, last_self_msg_at: null },
  chat_heat: { heat: 0, label: 'cold', recent_count: 0, recent_hours: 0, recent_user_msg_at: null },
  emotional_intensity: { intensity: 0, label: '工作' },
  weather: null
})
```

- [ ] **Step 2: 添加天气状态卡片**

在 `frontend/src/views/PassiveConsciousness.vue` 中找到情绪值卡片 `</n-grid-item>` 之后，添加天气卡片：

```vue
<n-grid-item>
  <n-card title="🌤 天气">
    <template v-if="status.weather">
      <n-statistic :value="status.weather.temperature" :suffix="'°C'">
        <template #prefix>
          <n-tag size="small">{{ status.weather.weather }}</n-tag>
        </template>
      </n-statistic>
      <n-space vertical size="small" style="margin-top: 8px">
        <n-text>💨 {{ status.weather.wind_dir }} {{ status.weather.wind_scale }}</n-text>
        <n-text>💧 湿度 {{ status.weather.humidity }}%</n-text>
        <n-text>🌡 体感 {{ status.weather.feels_like }}°C</n-text>
        <n-text v-if="status.weather.uv_desc">☀️ 紫外线 {{ status.weather.uv_desc }}</n-text>
        <n-text v-if="status.weather.dressing">👔 {{ status.weather.dressing }}</n-text>
      </n-space>
      <n-divider v-if="status.weather.forecast?.length" style="margin: 12px 0 8px">未来天气</n-divider>
      <n-space v-if="status.weather.forecast?.length" size="small">
        <n-tag v-for="f in status.weather.forecast" :key="f.date" size="small">
          {{ f.date }} {{ f.weather }} {{ f.temp_min }}-{{ f.temp_max }}°C
        </n-tag>
      </n-space>
    </template>
    <n-text v-else type="secondary">天气感知未启用</n-text>
  </n-card>
</n-grid-item>
```

- [ ] **Step 3: 更新天气测试卡片**

在 `frontend/src/views/PassiveConsciousness.vue` 中找到天气测试卡片 `🌤 天气感知（高德 API）`，更新为：

```vue
<n-grid-item>
  <n-card title="🌤 天气感知" size="small">
    <n-space style="margin-bottom: 12px">
      <n-button @click="runTest('weather')" :loading="testing.weather" size="small">
        测试（强制刷新）
      </n-button>
      <n-button @click="clearWeatherCache" size="small" secondary>
        清除缓存
      </n-button>
    </n-space>
    <n-alert v-if="testResults.weather?.error" type="error" style="margin-bottom: 8px">
      {{ testResults.weather.error }}
    </n-alert>
    <n-descriptions v-if="testResults.weather?.data" :column="1" label-placement="left" bordered size="small">
      <n-descriptions-item label="城市">{{ testResults.weather.data.city }}</n-descriptions-item>
      <n-descriptions-item label="天气">{{ testResults.weather.data.weather }}</n-descriptions-item>
      <n-descriptions-item label="温度">{{ testResults.weather.data.temperature }}°C</n-descriptions-item>
      <n-descriptions-item label="体感">{{ testResults.weather.data.feels_like }}°C</n-descriptions-item>
      <n-descriptions-item label="湿度">{{ testResults.weather.data.humidity }}%</n-descriptions-item>
      <n-descriptions-item label="风向">{{ testResults.weather.data.wind_dir }} {{ testResults.weather.data.wind_scale }}</n-descriptions-item>
      <n-descriptions-item label="风速">{{ testResults.weather.data.wind_speed }} km/h</n-descriptions-item>
      <n-descriptions-item label="紫外线" v-if="testResults.weather.data.uv_desc">{{ testResults.weather.data.uv_desc }}</n-descriptions-item>
      <n-descriptions-item label="穿衣" v-if="testResults.weather.data.dressing">{{ testResults.weather.data.dressing }}</n-descriptions-item>
      <n-descriptions-item label="Provider">{{ testResults.weather.data.provider }}</n-descriptions-item>
      <n-descriptions-item label="缓存状态">{{ testResults.weather.data.cache_status?.is_valid ? '有效' : '过期/无' }}</n-descriptions-item>
    </n-descriptions>
    <template v-if="testResults.weather?.data?.forecast?.length">
      <n-divider style="margin: 12px 0 8px">未来天气</n-divider>
      <n-list bordered size="small">
        <n-list-item v-for="f in testResults.weather.data.forecast" :key="f.date">
          <n-space>
            <n-text>{{ f.date }}</n-text>
            <n-tag size="small">{{ f.weather }}</n-tag>
            <n-text>{{ f.temp_min }}-{{ f.temp_max }}°C</n-text>
            <n-text>{{ f.wind_dir }} {{ f.wind_scale }}</n-text>
          </n-space>
        </n-list-item>
      </n-list>
    </template>
  </n-card>
</n-grid-item>
```

- [ ] **Step 4: 添加清除缓存方法**

在 `frontend/src/views/PassiveConsciousness.vue` 的 `<script setup>` 中添加：

```javascript
// 清除天气缓存
const clearWeatherCache = async () => {
  try {
    await api.clearWeatherCache()
    message.success('天气缓存已清除')
  } catch (e) {
    message.error('清除缓存失败: ' + e.message)
  }
}
```

- [ ] **Step 5: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/views/PassiveConsciousness.vue
git commit -m "feat: 添加天气状态卡片和测试 UI"
```

---

## Task 11: 验证和测试

- [ ] **Step 1: 启动后端服务**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python main.py
```

Expected: 服务启动成功，无报错

- [ ] **Step 2: 测试配置保存**

```bash
curl -X PUT http://localhost:18720/api/passive-consciousness/config \
  -H "Content-Type: application/json" \
  -d '{"weather": {"enabled": true, "provider": "qweather", "city": "北京", "cache_hours": 4}}'
```

Expected: `{"message": "配置已保存"}`

- [ ] **Step 3: 测试天气获取**

```bash
curl http://localhost:18720/api/passive-consciousness/weather
```

Expected: 返回天气数据或"天气感知未启用"错误

- [ ] **Step 4: 测试天气强制刷新**

```bash
curl -X POST http://localhost:18720/api/passive-consciousness/test/weather
```

Expected: 返回天气数据（强制从 API 获取）

- [ ] **Step 5: 测试清除缓存**

```bash
curl -X POST http://localhost:18720/api/passive-consciousness/weather/clear-cache
```

Expected: `{"success": true, "message": "缓存已清除"}`

- [ ] **Step 6: 启动前端服务**

```bash
cd /home/ubuntu/.hermes/hermes-active/frontend
npm run dev
```

Expected: 前端启动成功，访问 http://localhost:5173

- [ ] **Step 7: 在 UI 中测试**

1. 打开被动意识配置页面
2. 启用天气感知
3. 选择 Provider（和风天气或高德地图）
4. 输入城市和 API Key
5. 保存配置
6. 切换到状态 Tab，查看天气卡片
7. 切换到测试 Tab，点击"测试（强制刷新）"

- [ ] **Step 8: 最终提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add -A
git commit -m "feat: 天气感知功能完成（高德/和风双 Provider + 内存缓存）"
```

---

## 自审查清单

### 1. Spec 覆盖检查

- ✅ 支持两个天气 Provider（高德/和风）
- ✅ 获取完整天气数据（基础天气、风力、生活指数、天气预报）
- ✅ 内存缓存机制，可配置过期时间
- ✅ 用户可在配置页面选择 Provider 和设置缓存时间
- ✅ 天气数据集成到状态查询
- ✅ 前端配置 UI
- ✅ 前端状态 UI

### 2. Placeholder 扫描

- ✅ 无 TBD/TODO
- ✅ 所有代码步骤都有完整代码
- ✅ 所有命令都有精确路径和预期输出

### 3. 类型一致性检查

- ✅ WeatherData 字段名称一致
- ✅ ForecastDay 字段名称一致
- ✅ API 端点返回格式一致
- ✅ 前端字段名称与后端一致

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-07-30-weather-perception.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
