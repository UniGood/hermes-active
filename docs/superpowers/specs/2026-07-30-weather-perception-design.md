# 天气感知功能设计文档

**日期**: 2026-07-30  
**状态**: 设计完成  
**优先级**: 低  

---

## 1. 概述

为被动意识系统添加天气感知能力，支持从高德地图或和风天气 API 获取实时天气数据，并在内存中缓存以减少 API 调用。

### 1.1 目标

- 支持两个天气 Provider：高德地图、和风天气
- 获取完整天气数据：基础天气、风力、生活指数、天气预报
- 内存缓存机制，可配置过期时间
- 用户可在配置页面选择 Provider 和设置缓存时间

### 1.2 不在范围内

- 天气数据持久化到数据库
- 天气预警推送
- 多城市支持（单城市配置）

---

## 2. 配置参数

存储在 `configs` 表，key 前缀：`passive_consciousness.weather.`

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `passive_consciousness.weather.enabled` | bool | false | 天气感知总开关 |
| `passive_consciousness.weather.provider` | string | qweather | Provider 选择（amap/qweather） |
| `passive_consciousness.weather.city` | string | 北京 | 查询城市名称 |
| `passive_consciousness.weather.cache_hours` | int | 4 | 缓存时长（小时，1-24） |
| `passive_consciousness.weather.amap_key` | string | "" | 高德地图 API Key |
| `passive_consciousness.weather.qweather_key` | string | "" | 和风天气 API Key |
| `passive_consciousness.weather.qweather_geo_url` | string | https://geoapi.qweather.com/v2/city/lookup | 和风 GeoAPI URL |
| `passive_consciousness.weather.qweather_weather_url` | string | https://devapi.qweather.com/v7/weather/now | 和风天气 API URL |

**移除配置**：`weather.adcode`（改用城市名自动查询 ID）

---

## 3. 数据模型

### 3.1 WeatherData

```python
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
    forecast: List[ForecastDay]
    
    # 元数据
    updated_at: datetime    # 数据更新时间
    provider: str           # 数据来源（amap/qweather）
    raw_data: dict          # 原始 API 响应（调试用）
```

### 3.2 ForecastDay

```python
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
```

---

## 4. 架构设计

### 4.1 文件结构

```
backend/
├── services/
│   ├── weather_service.py          # 新增：天气服务核心
│   └── passive_consciousness_service.py  # 修改：集成天气数据
├── routers/
│   └── passive_consciousness.py    # 修改：天气测试端点
└── models/
    └── passive_consciousness.py    # 修改：添加天气数据模型

frontend/src/
├── views/
│   └── PassiveConsciousness.vue    # 修改：天气配置 UI
└── api/
    └── passive_consciousness.js    # 修改：天气 API 调用
```

### 4.2 WeatherService 类

```python
class WeatherService:
    """天气服务 - 内存缓存 + 多 Provider"""
    
    # 类变量：内存缓存
    _cache: Optional[WeatherData] = None
    _cache_time: Optional[datetime] = None
    _cache_lock = threading.Lock()  # 线程安全
    
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
        return {
            "has_cache": cls._cache is not None,
            "cache_time": cls._cache_time.isoformat() if cls._cache_time else None,
            "is_valid": cls._is_cache_valid(PassiveConsciousnessService.get_config().get("weather", {})),
        }
```

---

## 5. API 实现

### 5.1 高德地图 API

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
    live = now_data.get("lives", [{}])[0]
    forecasts = forecast_data.get("forecasts", [{}])[0].get("casts", [])
    
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

### 5.2 和风天气 API

```python
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
    # 常用城市 ID 映射（避免每次都调用 GeoAPI）
    CITY_IDS = {
        "beijing": "101010100", "北京": "101010100",
        "shanghai": "101020100", "上海": "101020100",
        "guangzhou": "101280101", "广州": "101280101",
        "shenzhen": "101280601", "深圳": "101280601",
        # ... 更多城市
    }
    
    city_key = city.lower().strip()
    city_id = CITY_IDS.get(city_key)
    
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

### 5.3 HTTP 工具方法

```python
@classmethod
def _http_get(cls, url: str, timeout: int = 10) -> dict:
    """发送 HTTP GET 请求"""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "hermes-passive-consciousness/1.0")
    
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

---

## 6. API 端点

### 6.1 获取天气数据

```
GET /api/passive-consciousness/weather
```

**响应**：
```json
{
  "success": true,
  "data": {
    "city": "北京",
    "weather": "晴",
    "temperature": 28,
    "humidity": 45,
    "feels_like": 30,
    "wind_dir": "东南风",
    "wind_scale": "3-4级",
    "wind_speed": 15,
    "uv_index": 6,
    "uv_desc": "较强",
    "dressing": "短袖",
    "forecast": [
      {
        "date": "2026-07-31",
        "weather": "多云",
        "temp_min": 22,
        "temp_max": 32
      }
    ],
    "updated_at": "2026-07-30T14:30:00",
    "provider": "qweather",
    "cache_status": {
      "has_cache": true,
      "is_valid": true,
      "cache_time": "2026-07-30T14:30:00"
    }
  }
}
```

### 6.2 测试天气（强制刷新）

```
POST /api/passive-consciousness/test/weather
```

**响应**：同上，但强制刷新缓存

### 6.3 清除天气缓存

```
POST /api/passive-consciousness/weather/clear-cache
```

**响应**：
```json
{
  "success": true,
  "message": "缓存已清除"
}
```

---

## 7. 前端改动

### 7.1 配置页面

在 PassiveConsciousness.vue 的配置 Tab 中添加天气配置区块：

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
    <n-input v-model:value="config.weather.amap_key" placeholder="输入高德 API Key" />
  </n-form-item>
  
  <n-form-item label="和风 API Key" v-if="config.weather.provider === 'qweather'">
    <n-input v-model:value="config.weather.qweather_key" placeholder="输入和风天气 API Key" />
  </n-form-item>
  
  <n-form-item label="和风 GeoAPI URL" v-if="config.weather.provider === 'qweather'">
    <n-input v-model:value="config.weather.qweather_geo_url" placeholder="https://geoapi.qweather.com/v2/city/lookup" />
  </n-form-item>
  
  <n-form-item label="和风天气 URL" v-if="config.weather.provider === 'qweather'">
    <n-input v-model:value="config.weather.qweather_weather_url" placeholder="https://devapi.qweather.com/v7/weather/now" />
  </n-form-item>
</template>
```

### 7.2 状态页面

在状态 Tab 中添加天气卡片：

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
      </n-space>
    </template>
    <n-text v-else type="secondary">天气感知未启用</n-text>
  </n-card>
</n-grid-item>
```

---

## 8. 集成到被动意识

### 8.1 状态查询集成

在 `PassiveConsciousnessService.get_status()` 中添加天气数据：

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
            "uv_desc": weather.uv_desc,
            "dressing": weather.dressing,
        }
except Exception as e:
    logger.warning("获取天气数据失败: %s", e)

return {
    # ... 原有字段
    "weather": weather_data,
}
```

### 8.2 上下文注入集成

在被动意识上下文注入时，天气数据可作为环境信息注入：

```python
# 天气感知
if weather_data:
    context_parts.append(
        f"【天气】{weather_data['city']} {weather_data['weather']} "
        f"{weather_data['temperature']}°C，体感{weather_data['feels_like']}°C，"
        f"{weather_data['wind_dir']}{weather_data['wind_scale']}"
    )
```

---

## 9. 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置 | 返回 None，日志警告 |
| API 调用失败 | 返回旧缓存（如有），日志记录错误 |
| 城市未找到 | 抛出 ValueError，上层捕获 |
| 网络超时 | 重试 1 次，失败返回旧缓存 |
| 响应格式异常 | 记录原始数据，返回部分数据 |

---

## 10. 测试策略

### 10.1 单元测试

- `test_weather_service.py`
  - 测试缓存过期逻辑
  - 测试高德 API 解析
  - 测试和风 API 解析
  - 测试城市 ID 查询

### 10.2 集成测试

- 测试端点 `/test/weather`
- 测试配置保存/读取
- 测试状态查询集成

---

## 11. 实现步骤

1. **添加数据模型**：在 `models/passive_consciousness.py` 中添加 WeatherData、ForecastDay
2. **创建 WeatherService**：在 `backend/services/weather_service.py` 中实现
3. **更新配置默认值**：在 `_DEFAULTS` 中添加新的天气配置项
4. **修改状态查询**：在 `get_status()` 中集成天气数据
5. **更新 API 端点**：修改 `test_weather()` 端点，添加新端点
6. **更新前端配置 UI**：添加天气配置区块
7. **更新前端状态 UI**：添加天气状态卡片
8. **测试验证**：运行全量测试

---

## 12. 待确认项

- [ ] 和风天气 API 的具体 URL 是否需要用户配置？还是使用默认值即可？
- [ ] 是否需要支持天气预警功能？
- [ ] 天气数据是否需要记录到日志表？
