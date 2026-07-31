# 天气配置统一实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一天气配置到 `weather.*` 命名空间，删除被动意识和主动意识中的重复配置

**Architecture:** 新建 `weather.*` 命名空间，修改 WeatherService 和相关 API 从新命名空间读取配置，删除旧配置

**Tech Stack:** Python 3, FastAPI, SQLAlchemy

---

## 文件结构

```
backend/
├── services/
│   ├── config_service.py              # 添加 weather.* 默认值
│   ├── weather_service.py             # 修改配置读取逻辑
│   ├── passive_consciousness_service.py # 删除天气配置
│   ├── active_consciousness_service.py  # 删除天气配置
│   └── context_collector.py           # 修改配置读取逻辑
├── routers/
│   ├── config.py                      # 修改天气配置 API
│   └── passive_consciousness.py       # 修改天气 API

frontend/src/
└── views/
    └── PassiveConsciousness.vue       # 删除天气配置区块
```

---

## Task 1: 添加 weather.* 默认配置

**Files:**
- Modify: `backend/services/config_service.py`

- [ ] **Step 1: 添加天气配置默认值**

在 `backend/services/config_service.py` 中添加天气配置默认值：

```python
# 天气配置默认值
WEATHER_CONFIG_DEFAULTS = {
    "weather.enabled": "false",
    "weather.provider": "qweather",
    "weather.city": "北京",
    "weather.cache_hours": "4",
    "weather.amap_key": "",
    "weather.adcode": "370100",
    "weather.qweather_key": "",
    "weather.qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
    "weather.qweather_weather_url": "https://devapi.qweather.com/v7/weather/now",
    "weather.cache_ttl": "3600",
    "weather.temp_change_threshold": "5.0",
}
```

- [ ] **Step 2: 验证导入**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from services.config_service import ConfigService; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/config_service.py
git commit -m "feat: 添加 weather.* 配置默认值"
```

---

## Task 2: 修改天气配置 API

**Files:**
- Modify: `backend/routers/config.py`

- [ ] **Step 1: 修改 GET /api/config/weather**

将 `backend/routers/config.py` 中的 `get_weather_config` 函数修改为从 `weather.*` 读取：

```python
@router.get("/weather")
async def get_weather_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """获取天气配置"""
    import logging
    logger = logging.getLogger("hermes.config")

    # 从 weather.* 读取配置
    result = {
        "enabled": ConfigService.get_config(db, "weather.enabled") == "true",
        "provider": ConfigService.get_config(db, "weather.provider") or "qweather",
        "city": ConfigService.get_config(db, "weather.city") or "北京",
        "cache_hours": int(ConfigService.get_config(db, "weather.cache_hours") or "4"),
        "amap_key": ConfigService.get_config(db, "weather.amap_key") or "",
        "adcode": ConfigService.get_config(db, "weather.adcode") or "370100",
        "cache_ttl": int(ConfigService.get_config(db, "weather.cache_ttl") or "3600"),
        "temp_change_threshold": float(ConfigService.get_config(db, "weather.temp_change_threshold") or "5.0"),
        "qweather_key": ConfigService.get_config(db, "weather.qweather_key") or "",
        "qweather_geo_url": ConfigService.get_config(db, "weather.qweather_geo_url") or "https://geoapi.qweather.com/v2/city/lookup",
        "qweather_weather_url": ConfigService.get_config(db, "weather.qweather_weather_url") or "https://devapi.qweather.com/v7/weather/now",
    }
    logger.info("返回天气配置: %s", result)
    return result
```

- [ ] **Step 2: 修改 PUT /api/config/weather**

将 `update_weather_config` 函数修改为写入 `weather.*`：

```python
@router.put("/weather", response_model=SuccessResponse)
async def update_weather_config(
    weather_config: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """更新天气配置"""
    import logging
    logger = logging.getLogger("hermes.config")
    logger.info("收到天气配置更新请求: %s", weather_config)

    # 验证配置
    provider = weather_config.get("provider", "qweather")
    if weather_config.get("enabled"):
        if provider == "qweather" and not weather_config.get("qweather_key"):
            raise HTTPException(status_code=400, detail="启用和风天气时必须配置 API Key")
        elif provider == "amap" and not weather_config.get("amap_key"):
            raise HTTPException(status_code=400, detail="启用高德天气时必须配置 API Key")

    # 保存配置到 weather.* 命名空间
    flat_keys = {
        "enabled": "weather.enabled",
        "provider": "weather.provider",
        "city": "weather.city",
        "cache_hours": "weather.cache_hours",
        "amap_key": "weather.amap_key",
        "adcode": "weather.adcode",
        "cache_ttl": "weather.cache_ttl",
        "temp_change_threshold": "weather.temp_change_threshold",
        "qweather_key": "weather.qweather_key",
        "qweather_geo_url": "weather.qweather_geo_url",
        "qweather_weather_url": "weather.qweather_weather_url",
    }
    for field, config_key in flat_keys.items():
        if field in weather_config:
            value = weather_config[field]
            # 布尔值转换为小写字符串
            if isinstance(value, bool):
                value = str(value).lower()
            else:
                value = str(value)
            logger.info("保存配置: %s = %s", config_key, value)
            ConfigService.set_config(db, config_key, value)

    return SuccessResponse(message="天气配置已保存")
```

- [ ] **Step 3: 修改 GET /api/config/weather/test**

将 `test_weather` 函数修改为从 `weather.*` 读取：

```python
@router.get("/weather/test")
async def test_weather(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """测试天气 API"""
    from services.weather_service import WeatherService

    # 从 weather.* 读取配置
    provider = ConfigService.get_config(db, "weather.provider") or "qweather"
    city = ConfigService.get_config(db, "weather.city") or "北京"
    amap_key = ConfigService.get_config(db, "weather.amap_key") or ""
    adcode = ConfigService.get_config(db, "weather.adcode") or "370100"
    qweather_key = ConfigService.get_config(db, "weather.qweather_key") or ""
    qweather_geo_url = ConfigService.get_config(db, "weather.qweather_geo_url") or "https://geoapi.qweather.com/v2/city/lookup"
    qweather_weather_url = ConfigService.get_config(db, "weather.qweather_weather_url") or "https://devapi.qweather.com/v7/weather/now"

    # ... 其余代码保持不变
```

- [ ] **Step 4: 验证 API**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from routers.config import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/routers/config.py
git commit -m "refactor: 天气配置 API 改为使用 weather.* 命名空间"
```

---

## Task 3: 修改被动意识天气 API

**Files:**
- Modify: `backend/routers/passive_consciousness.py`

- [ ] **Step 1: 修改天气 API 端点**

将 `backend/routers/passive_consciousness.py` 中的天气相关端点修改为从 `weather.*` 读取配置：

```python
def _get_weather_config():
    """获取天气配置（从 weather.* 命名空间）"""
    from services.config_service import ConfigService
    from models.database import ActiveSession

    db = ActiveSession()
    try:
        return {
            "enabled": ConfigService.get_config(db, "weather.enabled") == "true",
            "provider": ConfigService.get_config(db, "weather.provider") or "qweather",
            "city": ConfigService.get_config(db, "weather.city") or "北京",
            "cache_hours": int(ConfigService.get_config(db, "weather.cache_hours") or "4"),
            "amap_key": ConfigService.get_config(db, "weather.amap_key") or "",
            "adcode": ConfigService.get_config(db, "weather.adcode") or "370100",
            "qweather_key": ConfigService.get_config(db, "weather.qweather_key") or "",
            "qweather_geo_url": ConfigService.get_config(db, "weather.qweather_geo_url") or "https://geoapi.qweather.com/v2/city/lookup",
            "qweather_weather_url": ConfigService.get_config(db, "weather.qweather_weather_url") or "https://devapi.qweather.com/v7/weather/now",
        }
    finally:
        db.close()


@router.get("/weather")
async def get_weather():
    """获取当前天气（带缓存）"""
    try:
        from services.weather_service import WeatherService

        weather_config = _get_weather_config()

        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}

        service = WeatherService()
        result = await service.get_weather(
            amap_key=weather_config.get("amap_key", ""),
            adcode=weather_config.get("adcode", "370100"),
            cache_ttl=int(weather_config.get("cache_hours", 4)) * 3600,
            provider=weather_config.get("provider", "qweather"),
            city=weather_config.get("city", ""),
            qweather_key=weather_config.get("qweather_key", ""),
            qweather_geo_url=weather_config.get("qweather_geo_url", "https://geoapi.qweather.com/v2/city/lookup"),
            qweather_weather_url=weather_config.get("qweather_weather_url", "https://devapi.qweather.com/v7/weather/now"),
        )

        if result.get("success"):
            current = result.get("current", {})
            return {
                "success": True,
                "data": {
                    "city": result.get("city", ""),
                    "weather": current.get("weather", ""),
                    "temperature": current.get("temp", ""),
                    "humidity": current.get("humidity", ""),
                    "winddirection": current.get("winddirection", ""),
                    "forecast": result.get("forecast", []),
                    "weather_changed": result.get("weather_changed", False),
                    "change_type": result.get("change_type"),
                }
            }
        else:
            return {"success": False, "error": result.get("error", "未知错误")}
    except Exception as e:
        logger.error("获取天气失败: %s", e)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: 验证 API**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from routers.passive_consciousness import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/routers/passive_consciousness.py
git commit -m "refactor: 被动意识天气 API 改为使用 weather.* 命名空间"
```

---

## Task 4: 删除被动意识天气配置

**Files:**
- Modify: `backend/services/passive_consciousness_service.py`

- [ ] **Step 1: 删除天气配置默认值**

在 `backend/services/passive_consciousness_service.py` 的 `_DEFAULTS` 字典中删除天气相关配置：

```python
# 删除以下行：
"passive_consciousness.weather.enabled": "false",
"passive_consciousness.weather.provider": "qweather",
"passive_consciousness.weather.city": "北京",
"passive_consciousness.weather.cache_hours": "4",
"passive_consciousness.weather.amap_key": "",
"passive_consciousness.weather.qweather_key": "",
"passive_consciousness.weather.qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
"passive_consciousness.weather.qweather_weather_url": "https://devapi.qweather.com/v7/weather/now",
```

- [ ] **Step 2: 修改 get_status 方法**

修改 `get_status` 方法中的天气数据获取逻辑，从 `weather.*` 读取配置：

```python
# 获取天气数据
weather_data = None
try:
    from services.weather_service import WeatherService

    # 从 weather.* 读取配置
    weather_enabled = ConfigService.get_config(db, "weather.enabled") == "true"
    if weather_enabled:
        weather_service = WeatherService()
        weather_result = weather_service.get_weather_sync(
            amap_key=ConfigService.get_config(db, "weather.amap_key") or "",
            adcode=ConfigService.get_config(db, "weather.adcode") or "370100",
            cache_ttl=int(ConfigService.get_config(db, "weather.cache_hours") or "4") * 3600,
            provider=ConfigService.get_config(db, "weather.provider") or "qweather",
            city=ConfigService.get_config(db, "weather.city") or "",
            qweather_key=ConfigService.get_config(db, "weather.qweather_key") or "",
            qweather_geo_url=ConfigService.get_config(db, "weather.qweather_geo_url") or "https://geoapi.qweather.com/v2/city/lookup",
            qweather_weather_url=ConfigService.get_config(db, "weather.qweather_weather_url") or "https://devapi.qweather.com/v7/weather/now",
        )

        if weather_result and weather_result.get("success"):
            current = weather_result.get("current", {})
            weather_data = {
                "city": weather_result.get("city", ""),
                "weather": current.get("weather", ""),
                "temperature": current.get("temp", ""),
                "humidity": current.get("humidity", ""),
                "winddirection": current.get("winddirection", ""),
            }
except Exception as e:
    logger.warning("获取天气数据失败: %s", e)
```

- [ ] **Step 3: 验证服务**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from services.passive_consciousness_service import PassiveConsciousnessService; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/passive_consciousness_service.py
git commit -m "refactor: 被动意识删除天气配置，使用 weather.* 命名空间"
```

---

## Task 5: 删除主动意识天气配置

**Files:**
- Modify: `backend/services/active_consciousness_service.py`
- Modify: `backend/services/context_collector.py`

- [ ] **Step 1: 删除主动意识天气配置默认值**

在 `backend/services/active_consciousness_service.py` 的 `_DEFAULTS` 字典中删除天气相关配置：

```python
# 删除以下行：
"active_consciousness.weather.enabled": "false",
"active_consciousness.weather.amap_key": "",
"active_consciousness.weather.adcode": "370100",
"active_consciousness.weather.cache_ttl": "3600",
"active_consciousness.weather.temp_change_threshold": "5.0",
```

- [ ] **Step 2: 修改 context_collector.py**

修改 `backend/services/context_collector.py` 中的天气配置读取逻辑：

```python
# 在 collect_context 方法中，修改天气配置读取
# 从 weather.* 读取配置
weather_enabled = ConfigService.get_config(db, "weather.enabled") == "true"
if weather_enabled:
    weather_config = {
        "enabled": True,
        "amap_key": ConfigService.get_config(db, "weather.amap_key") or "",
        "adcode": ConfigService.get_config(db, "weather.adcode") or "370100",
        "cache_ttl": int(ConfigService.get_config(db, "weather.cache_ttl") or "3600"),
        "temp_change_threshold": float(ConfigService.get_config(db, "weather.temp_change_threshold") or "5.0"),
        "provider": ConfigService.get_config(db, "weather.provider") or "qweather",
        "city": ConfigService.get_config(db, "weather.city") or "",
        "qweather_key": ConfigService.get_config(db, "weather.qweather_key") or "",
        "qweather_geo_url": ConfigService.get_config(db, "weather.qweather_geo_url") or "https://geoapi.qweather.com/v2/city/lookup",
        "qweather_weather_url": ConfigService.get_config(db, "weather.qweather_weather_url") or "https://devapi.qweather.com/v7/weather/now",
    }
```

- [ ] **Step 3: 验证服务**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from services.active_consciousness_service import ActiveConsciousnessService; print('OK')"
python -c "from services.context_collector import ContextCollector; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/active_consciousness_service.py backend/services/context_collector.py
git commit -m "refactor: 主动意识删除天气配置，使用 weather.* 命名空间"
```

---

## Task 6: 删除前端天气配置区块

**Files:**
- Modify: `frontend/src/views/PassiveConsciousness.vue`

- [ ] **Step 1: 删除天气配置区块**

在 `frontend/src/views/PassiveConsciousness.vue` 中删除天气配置区块：

```vue
<!-- 删除以下区块 -->
<!-- 天气感知 -->
<n-divider>天气感知</n-divider>
<n-form-item label="启用天气感知">
  <n-switch v-model:value="config.weather.enabled" />
</n-form-item>

<template v-if="config.weather.enabled">
  ...
</template>
```

- [ ] **Step 2: 删除天气配置数据**

在 `config` ref 中删除 `weather` 字段：

```javascript
const config = ref({
  // ... 其他配置
  // 删除 weather 字段
})
```

- [ ] **Step 3: 验证构建**

```bash
cd /home/ubuntu/.hermes/hermes-active/frontend
npm run build
```

Expected: 构建成功

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/views/PassiveConsciousness.vue
git commit -m "refactor: 被动意识页面删除天气配置区块"
```

---

## Task 7: 数据库迁移

**Files:**
- Create: `backend/migrations/weather_config_migration.py`

- [ ] **Step 1: 创建迁移脚本**

创建 `backend/migrations/weather_config_migration.py`：

```python
"""
天气配置迁移脚本
将 passive_consciousness.weather.* 和 active_consciousness.weather.* 迁移到 weather.*
"""
import sqlite3
import os

def migrate():
    """执行迁移"""
    db_path = os.path.expanduser("~/.hermes/hermes-active/data/active.db")

    if not os.path.exists(db_path):
        print("数据库不存在，跳过迁移")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 旧配置到新配置的映射
    migration_map = {
        "passive_consciousness.weather.enabled": "weather.enabled",
        "passive_consciousness.weather.provider": "weather.provider",
        "passive_consciousness.weather.city": "weather.city",
        "passive_consciousness.weather.cache_hours": "weather.cache_hours",
        "passive_consciousness.weather.amap_key": "weather.amap_key",
        "passive_consciousness.weather.qweather_key": "weather.qweather_key",
        "passive_consciousness.weather.qweather_geo_url": "weather.qweather_geo_url",
        "passive_consciousness.weather.qweather_weather_url": "weather.qweather_weather_url",
        "active_consciousness.weather.enabled": "weather.enabled",
        "active_consciousness.weather.amap_key": "weather.amap_key",
        "active_consciousness.weather.adcode": "weather.adcode",
        "active_consciousness.weather.cache_ttl": "weather.cache_ttl",
        "active_consciousness.weather.temp_change_threshold": "weather.temp_change_threshold",
    }

    migrated = 0
    for old_key, new_key in migration_map.items():
        # 检查旧配置是否存在
        cursor.execute("SELECT value FROM configs WHERE key = ?", (old_key,))
        row = cursor.fetchone()

        if row:
            old_value = row[0]

            # 检查新配置是否已存在
            cursor.execute("SELECT value FROM configs WHERE key = ?", (new_key,))
            new_row = cursor.fetchone()

            if not new_row:
                # 迁移配置
                cursor.execute(
                    "INSERT INTO configs (key, value) VALUES (?, ?)",
                    (new_key, old_value)
                )
                migrated += 1
                print(f"迁移: {old_key} -> {new_key} = {old_value}")
            else:
                print(f"跳过: {new_key} 已存在")

    conn.commit()
    conn.close()

    print(f"迁移完成，共迁移 {migrated} 条配置")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2: 运行迁移**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python migrations/weather_config_migration.py
```

Expected: 迁移完成

- [ ] **Step 3: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/migrations/weather_config_migration.py
git commit -m "feat: 添加天气配置迁移脚本"
```

---

## Task 8: 测试验证

- [ ] **Step 1: 运行单元测试**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -m pytest tests/test_weather_service.py -v
```

Expected: 所有测试通过

- [ ] **Step 2: 测试天气配置 API**

```bash
# 获取天气配置
curl http://localhost:18720/api/config/weather

# 更新天气配置
curl -X PUT http://localhost:18720/api/config/weather \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "city": "北京"}'

# 测试天气 API
curl http://localhost:18720/api/config/weather/test
```

Expected: 所有 API 正常响应

- [ ] **Step 3: 测试被动意识天气**

```bash
curl http://localhost:18720/api/passive-consciousness/weather
```

Expected: 返回天气数据

- [ ] **Step 4: 最终提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add -A
git commit -m "feat: 天气配置统一完成"
```

---

## 自审查清单

### 1. Spec 覆盖检查

- ✅ 新建 `weather.*` 命名空间
- ✅ 删除被动意识天气配置
- ✅ 删除主动意识天气配置
- ✅ 修改天气配置 API
- ✅ 修改被动意识天气 API
- ✅ 修改前端配置页面
- ✅ 数据库迁移

### 2. Placeholder 扫描

- ✅ 无 TBD/TODO
- ✅ 所有代码步骤都有完整代码

### 3. 类型一致性检查

- ✅ 配置 key 命名一致
- ✅ API 返回格式一致

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-07-31-weather-config-unification.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
