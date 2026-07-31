# 天气配置统一设计文档

**日期**: 2026-07-31
**状态**: 设计完成
**版本**: v1.0

---

## 1. 概述

### 1.1 背景

当前天气配置分散在两个命名空间：
- `passive_consciousness.weather.*`（被动意识）
- `active_consciousness.weather.*`（主动意识）

配置管理模块（`Config.vue`）已有统一的天气配置页面，但需要合并两个命名空间的数据。

### 1.2 目标

- 新建 `weather.*` 命名空间统一存储天气配置
- 删除 `passive_consciousness.weather.*` 和 `active_consciousness.weather.*`
- 被动意识和主动意识都从 `weather.*` 读取配置
- 使用 WeatherService 现有的类级别缓存

### 1.3 不在范围内

- 修改天气服务的核心逻辑
- 添加新的天气 Provider
- 修改天气数据结构

---

## 2. 配置迁移

### 2.1 旧配置（删除）

```
passive_consciousness.weather.enabled
passive_consciousness.weather.provider
passive_consciousness.weather.city
passive_consciousness.weather.cache_hours
passive_consciousness.weather.amap_key
passive_consciousness.weather.qweather_key
passive_consciousness.weather.qweather_geo_url
passive_consciousness.weather.qweather_weather_url

active_consciousness.weather.enabled
active_consciousness.weather.amap_key
active_consciousness.weather.adcode
active_consciousness.weather.cache_ttl
active_consciousness.weather.temp_change_threshold
```

### 2.2 新配置（统一）

```
weather.enabled              # bool, 默认 false
weather.provider             # string, 默认 "qweather"
weather.city                 # string, 默认 "北京"
weather.cache_hours          # int, 默认 4
weather.amap_key             # string, 默认 ""
weather.adcode               # string, 默认 "370100"
weather.qweather_key         # string, 默认 ""
weather.qweather_geo_url     # string, 默认 "https://geoapi.qweather.com/v2/city/lookup"
weather.qweather_weather_url # string, 默认 "https://devapi.qweather.com/v7/weather/now"
weather.cache_ttl            # int, 默认 3600
weather.temp_change_threshold # float, 默认 5.0
```

---

## 3. 架构设计

### 3.1 数据流

```
┌─────────────────────────────────────────────────────────────┐
│  配置管理模块 (Config.vue)                                  │
│  └─ 天气配置 Tab                                            │
│     └─ 读写 weather.* 配置                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ConfigService                                              │
│  └─ get_config("weather.*")                                 │
│  └─ set_config("weather.*", value)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  WeatherService                                             │
│  └─ get_weather()                                           │
│     └─ 从 weather.* 读取配置                                │
│     └─ 使用类级别缓存                                       │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│  被动意识插件              │     │  主动意识服务              │
│  └─ 调用 Backend API      │     │  └─ 调用 Backend API      │
│     └─ GET /weather       │     │     └─ GET /weather       │
└───────────────────────────┘     └───────────────────────────┘
```

### 3.2 API 端点

现有端点（修改）：
- `GET /api/config/weather` - 获取天气配置（从 `weather.*` 读取）
- `PUT /api/config/weather` - 更新天气配置（写入 `weather.*`）
- `GET /api/config/weather/test` - 测试天气 API
- `GET /api/passive-consciousness/weather` - 获取天气数据
- `POST /api/passive-consciousness/weather/refresh` - 刷新天气缓存

---

## 4. 实现步骤

### 4.1 添加新配置默认值

在 `config_service.py` 或相关文件中添加 `weather.*` 默认值。

### 4.2 修改天气配置 API

修改 `routers/config.py` 中的 `/api/config/weather` 端点，使用 `weather.*` 命名空间。

### 4.3 修改 WeatherService

修改 `weather_service.py` 中的配置读取逻辑，从 `weather.*` 读取。

### 4.4 修改被动意识服务

删除 `passive_consciousness_service.py` 中的天气配置默认值。

### 4.5 修改主动意识服务

删除 `active_consciousness_service.py` 中的天气配置默认值。

### 4.6 修改前端

删除 `PassiveConsciousness.vue` 中的天气配置区块。

### 4.7 数据库迁移

将旧配置迁移到新命名空间。

---

## 5. 文件结构

```
backend/
├── services/
│   ├── config_service.py              # 添加 weather.* 默认值
│   ├── weather_service.py             # 修改配置读取逻辑
│   ├── passive_consciousness_service.py # 删除天气配置
│   ├── active_consciousness_service.py  # 删除天气配置
│   └── context_collector.py           # 修改配置读取逻辑
├── routers/
│   └── config.py                      # 修改天气配置 API

frontend/src/
└── views/
    ├── PassiveConsciousness.vue       # 删除天气配置区块
    └── Config.vue                     # 天气配置页面（保留）
```

---

## 6. 测试策略

### 6.1 单元测试

- 测试天气配置读取
- 测试天气配置更新
- 测试配置迁移

### 6.2 集成测试

- 测试被动意识获取天气
- 测试主动意识获取天气
- 测试配置管理页面

---

## 7. 风险和注意事项

### 7.1 数据迁移

- 需要将旧配置迁移到新命名空间
- 迁移后删除旧配置

### 7.2 向后兼容

- 插件需要重新部署
- 后端服务需要重启

---

## 8. 待确认项

- [ ] 是否需要保留旧配置作为备份？
- [ ] 迁移脚本是否需要手动运行？
