# 被动意识系统重构设计文档

**日期**: 2026-07-31  
**状态**: 设计完成  
**版本**: v1.0  

---

## 1. 概述

### 1.1 背景

被动意识系统已有基础实现，但存在以下问题：
- 平台过滤硬编码为 `weixin`，无法支持其他平台
- 插件层和 Backend 层各自实现天气服务，代码重复
- 上下文注入格式固定，无法自定义
- 缺少注入效果分析功能

### 1.2 目标

1. **平台过滤配置化**：支持白名单模式，可配置启用的平台
2. **天气服务统一**：插件通过 HTTP 调用 Backend 的天气 API
3. **上下文模板自定义**：支持格式自定义、变量占位符、条件渲染、多套模板
4. **注入效果分析**：注入统计、情感分析、趋势图表、效果对比

### 1.3 不在范围内

- 重写 hermes 插件系统
- 修改 hermes 核心代码
- 添加新的 LLM Provider

---

## 2. 整体架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      Hermes 主进程                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  被动意识插件（轻量）                                │    │
│  │  - hook 注册                                        │    │
│  │  - 上下文注入                                       │    │
│  │  - 所有数据通过 HTTP 从 Backend 获取                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP 调用
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend 服务（FastAPI）                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 天气服务     │  │ 状态服务     │  │ 模板服务     │      │
│  │ - 双 Provider│  │ - 想念分数   │  │ - 模板渲染   │      │
│  │ - 缓存       │  │ - 聊天热度   │  │ - 变量替换   │      │
│  │ - 预报       │  │ - 情绪强度   │  │ - 条件渲染   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ 分析服务     │  │ 配置服务     │                        │
│  │ - 注入统计   │  │ - 平台白名单 │                        │
│  │ - 情感分析   │  │ - 模板配置   │                        │
│  │ - 趋势图表   │  │ - 分析配置   │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      前端（Vue 3）                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 配置管理     │  │ 状态监控     │  │ 效果分析     │      │
│  │ - 平台配置   │  │ - 实时状态   │  │ - 注入统计   │      │
│  │ - 模板配置   │  │ - 天气卡片   │  │ - 趋势图表   │      │
│  │ - 分析配置   │  │ - 历史记录   │  │ - 效果对比   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户消息到达
    │
    ▼
插件 pre_llm_call hook 触发
    │
    ├─ 1. 检查平台白名单（从 Backend 获取配置）
    │
    ├─ 2. 获取状态数据（HTTP → Backend）
    │     - 想念分数
    │     - 聊天热度
    │     - 情绪强度
    │
    ├─ 3. 获取天气数据（HTTP → Backend）
    │
    ├─ 4. 获取 Hindsight 记忆（HTTP → Backend）
    │
    ├─ 5. 渲染模板（HTTP → Backend）
    │     - 加载模板
    │     - 变量替换
    │     - 条件渲染
    │
    ├─ 6. 记录注入日志（HTTP → Backend）
    │
    └─ 7. 返回上下文给 hermes
```

---

## 3. 平台过滤配置化

### 3.1 配置结构

存储在 `active.db` 的 `configs` 表中：

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `passive_consciousness.platforms.enabled` | bool | true | 启用平台过滤 |
| `passive_consciousness.platforms.whitelist` | json | ["weixin"] | 启用的平台列表 |

### 3.2 API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/passive-consciousness/platforms` | 获取平台配置 |
| PUT | `/api/passive-consciousness/platforms` | 更新平台配置 |
| GET | `/api/passive-consciousness/platforms/available` | 获取可用平台列表 |

### 3.3 可用平台列表

| 平台 | 标识 | 说明 |
|------|------|------|
| 微信 | weixin | 微信公众号/小程序 |
| 飞书 | feishu | 飞书机器人 |
| Telegram | telegram | Telegram Bot |
| Discord | discord | Discord Bot |
| Slack | slack | Slack Bot |
| 自定义 | custom | 自定义平台 |

### 3.4 插件调用流程

```python
def inject_consciousness_context(...):
    # 1. 从 Backend 获取平台配置
    config = http_get("http://localhost:18720/api/passive-consciousness/platforms")
    
    # 2. 检查平台是否在白名单中
    if platform not in config["whitelist"]:
        return None  # 跳过注入
    
    # 3. 继续注入流程...
```

---

## 4. 天气服务统一

### 4.1 架构变更

**移除**：插件层的 `weather_service.py`

**新增**：Backend 天气 API 端点供插件调用

### 4.2 API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/passive-consciousness/weather` | 获取当前天气（带缓存） |
| POST | `/api/passive-consciousness/weather/refresh` | 强制刷新天气 |
| GET | `/api/passive-consciousness/weather/status` | 获取天气服务状态 |

### 4.3 天气数据结构

```json
{
  "success": true,
  "data": {
    "city": "北京",
    "weather": "晴",
    "weather_code": "100",
    "temperature": 28,
    "humidity": 45,
    "feels_like": 30,
    "pressure": 1013,
    "visibility": 10,
    "wind_dir": "东南风",
    "wind_scale": "3-4级",
    "wind_speed": 15,
    "uv_index": 6,
    "uv_desc": "较强",
    "dressing": "短袖",
    "comfort": "舒适",
    "cold_risk": "低",
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

### 4.4 实现要点

1. **复用现有 WeatherService**：不重复实现
2. **新增 `/weather` 端点**：供插件调用
3. **保持缓存机制**：避免频繁调用天气 API
4. **错误处理**：返回友好的错误信息

---

## 5. 上下文模板自定义

### 5.1 模板系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  模板系统                                                    │
├─────────────────────────────────────────────────────────────┤
│  1. 模板存储：active.db configs 表                          │
│  2. 模板引擎：Jinja2（轻量、功能强大）                      │
│  3. 变量注入：自动从状态数据中提取                          │
│  4. 条件渲染：支持 if/else 逻辑                            │
│  5. 多套模板：支持按场景切换                                │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 模板配置结构

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `passive_consciousness.templates.list` | json | [...] | 模板列表 |
| `passive_consciousness.templates.active_id` | string | "default" | 当前使用的模板 ID |

### 5.3 模板内容示例

```jinja2
--- [CONSCIOUSNESS_CONTEXT] ---
以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：

{% if inject_emotion %}
🎭 情绪状态：{{ emotional_label }}（强度 {{ "%.1f"|format(emotional_intensity) }}）
{% endif %}

{% if inject_heat %}
🔥 聊天热度：{{ chat_heat_label }}（近1小时 {{ chat_heat_count }} 条消息）
{% endif %}

{% if inject_longing %}
💕 想念程度：{{ longing_label }}（分数 {{ "%.2f"|format(longing_score) }}）
{% endif %}

{% if weather %}
🌤 天气：{{ weather.city }} {{ weather.weather }} {{ weather.temperature }}°C
  💨 {{ weather.wind_dir }} {{ weather.wind_scale }}
  💧 湿度 {{ weather.humidity }}%
  🌡 体感 {{ weather.feels_like }}°C
{% if weather.uv_desc %}
  ☀️ 紫外线 {{ weather.uv_desc }}
{% endif %}
{% if weather.temperature > 30 %}
  ⚠️ 高温提醒：注意防暑降温
{% elif weather.temperature < 5 %}
  ⚠️ 低温提醒：注意保暖
{% endif %}
{% endif %}

{% if memories %}
📖 相关记忆：
{% for memory in memories %}
  {{ loop.index }}. {{ memory.text }}
{% endfor %}
{% endif %}

{% if reflection %}
💭 综合反思：{{ reflection }}
{% endif %}

--- /[CONSCIOUSNESS_CONTEXT] ---
```

### 5.4 可用变量列表

| 变量 | 类型 | 说明 |
|------|------|------|
| `emotional_intensity` | float | 情绪强度 (0.0-1.0) |
| `emotional_label` | string | 情绪标签（工作/日常/八卦/情感/深度情感） |
| `chat_heat` | float | 聊天热度 |
| `chat_heat_label` | string | 热度标签（cold/warm/hot/fire） |
| `chat_heat_count` | int | 近1小时消息数 |
| `longing_score` | float | 想念分数 (0.0-1.0) |
| `longing_label` | string | 想念标签（calm/longing/missing/yearning/anxious） |
| `weather` | object | 天气数据（包含 city、weather、temperature 等） |
| `memories` | list | Hindsight 记忆列表 |
| `reflection` | string | Hindsight 反思文本 |
| `inject_emotion` | bool | 是否注入情绪（配置项） |
| `inject_heat` | bool | 是否注入热度（配置项） |
| `inject_longing` | bool | 是否注入想念（配置项） |
| `inject_memory` | bool | 是否注入记忆（配置项） |
| `now` | datetime | 当前时间 |
| `platform` | string | 当前平台 |
| `sender_id` | string | 发送者 ID |

### 5.5 API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/passive-consciousness/templates` | 获取模板列表 |
| GET | `/api/passive-consciousness/templates/{id}` | 获取单个模板 |
| PUT | `/api/passive-consciousness/templates/{id}` | 更新模板 |
| POST | `/api/passive-consciousness/templates` | 创建模板 |
| DELETE | `/api/passive-consciousness/templates/{id}` | 删除模板 |
| POST | `/api/passive-consciousness/templates/{id}/preview` | 预览模板渲染结果 |
| GET | `/api/passive-consciousness/templates/variables` | 获取可用变量列表 |

### 5.6 实现要点

1. **模板引擎**：使用 Jinja2（Python 标准模板引擎）
2. **模板存储**：存储在 `configs` 表中，JSON 格式
3. **变量注入**：自动从状态数据中提取变量
4. **安全沙箱**：限制模板中的危险操作
5. **预览功能**：使用模拟数据渲染模板

---

## 6. 注入效果分析

### 6.1 数据模型

扩展 `passive_consciousness_logs` 表：

```sql
ALTER TABLE passive_consciousness_logs ADD COLUMN template_id TEXT;
ALTER TABLE passive_consciousness_logs ADD COLUMN context_preview TEXT;
ALTER TABLE passive_consciousness_logs ADD COLUMN llm_response_sentiment TEXT;
ALTER TABLE passive_consciousness_logs ADD COLUMN llm_response_length INTEGER;
ALTER TABLE passive_consciousness_logs ADD COLUMN response_time_ms INTEGER;
```

### 6.2 分析服务

```python
class AnalysisService:
    """注入效果分析服务"""
    
    @staticmethod
    def get_injection_stats(
        start_date: str = None,
        end_date: str = None,
        platform: str = None,
        group_by: str = "day"  # day/week/month
    ) -> dict:
        """获取注入统计"""
        # 返回：总注入次数、成功率、各平台分布、各状态分布
        pass
    
    @staticmethod
    def get_sentiment_analysis(
        start_date: str = None,
        end_date: str = None,
        platform: str = None
    ) -> dict:
        """获取情感分析"""
        # 返回：注入前后情感变化、情感分布、情感趋势
        pass
    
    @staticmethod
    def get_trend_data(
        metric: str,  # longing/heat/emotion
        start_date: str = None,
        end_date: str = None,
        platform: str = None
    ) -> dict:
        """获取趋势数据"""
        # 返回：时间序列数据、平均值、最大值、最小值
        pass
    
    @staticmethod
    def get_effect_comparison(
        start_date: str = None,
        end_date: str = None,
        platform: str = None
    ) -> dict:
        """获取效果对比"""
        # 返回：注入 vs 未注入的回复质量对比
        pass
```

### 6.3 API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/passive-consciousness/analysis/stats` | 注入统计 |
| GET | `/api/passive-consciousness/analysis/sentiment` | 情感分析 |
| GET | `/api/passive-consciousness/analysis/trends` | 趋势数据 |
| GET | `/api/passive-consciousness/analysis/comparison` | 效果对比 |
| GET | `/api/passive-consciousness/analysis/export` | 导出数据 |

### 6.4 响应格式

#### 注入统计

```json
{
  "success": true,
  "data": {
    "summary": {
      "total_injections": 1250,
      "success_count": 1200,
      "error_count": 50,
      "success_rate": 0.96,
      "avg_context_length": 450
    },
    "by_platform": {
      "weixin": {"count": 1000, "success_rate": 0.97},
      "feishu": {"count": 250, "success_rate": 0.93}
    },
    "by_status": {
      "success": 1200,
      "skipped": 30,
      "error": 20
    },
    "by_hour": {
      "00": 10, "01": 5
    },
    "by_template": {
      "default": 800,
      "festival": 400
    }
  }
}
```

#### 情感分析

```json
{
  "success": true,
  "data": {
    "distribution": {
      "positive": 450,
      "neutral": 600,
      "negative": 150
    },
    "trend": [
      {"date": "2026-07-01", "positive": 45, "neutral": 60, "negative": 15}
    ],
    "avg_sentiment_score": 0.65,
    "sentiment_change_after_injection": 0.12
  }
}
```

#### 趋势数据

```json
{
  "success": true,
  "data": {
    "metric": "longing",
    "period": "2026-07-01 ~ 2026-07-30",
    "data_points": [
      {"timestamp": "2026-07-01T00:00:00", "value": 0.35}
    ],
    "statistics": {
      "avg": 0.42,
      "max": 0.85,
      "min": 0.12,
      "std_dev": 0.15
    }
  }
}
```

#### 效果对比

```json
{
  "success": true,
  "data": {
    "with_injection": {
      "count": 1200,
      "avg_response_length": 280,
      "avg_response_time_ms": 1500,
      "sentiment_distribution": {
        "positive": 0.45,
        "neutral": 0.45,
        "negative": 0.10
      }
    },
    "without_injection": {
      "count": 500,
      "avg_response_length": 220,
      "avg_response_time_ms": 1200,
      "sentiment_distribution": {
        "positive": 0.35,
        "neutral": 0.50,
        "negative": 0.15
      }
    },
    "improvement": {
      "response_length": "+27%",
      "positive_sentiment": "+10%",
      "negative_sentiment": "-5%"
    }
  }
}
```

### 6.5 前端实现

使用 **ECharts** 图表库：

```bash
npm install echarts vue-echarts
```

图表类型：
- 注入趋势：折线图
- 情感分布：饼图
- 平台分布：柱状图
- 效果对比：对比柱状图

---

## 7. 文件结构

### 7.1 Backend 文件

```
backend/
├── models/
│   └── passive_consciousness.py    # 修改：添加新数据模型
├── services/
│   ├── passive_consciousness_service.py  # 修改：集成新功能
│   ├── weather_service.py               # 保留：天气服务
│   ├── template_service.py              # 新增：模板服务
│   └── analysis_service.py              # 新增：分析服务
├── routers/
│   └── passive_consciousness.py    # 修改：添加新 API 端点
└── requirements.txt               # 修改：添加 jinja2 依赖
```

### 7.2 Plugin 文件

```
plugins/passive-consciousness/
├── __init__.py                    # 修改：重构注入逻辑
├── plugin.yaml                    # 保留
├── config_reader.py               # 保留
├── hindsight_client.py            # 保留
├── consciousness_engine.py        # 删除：功能移至 Backend
├── context_builder.py             # 删除：功能移至 Backend
└── weather_service.py             # 删除：功能移至 Backend
```

### 7.3 Frontend 文件

```
frontend/src/
├── views/
│   ├── PassiveConsciousness.vue   # 修改：添加新配置和分析页面
│   └── Analysis.vue               # 新增：分析页面
├── api/
│   └── passive_consciousness.js   # 修改：添加新 API 调用
└── components/
    └── charts/                    # 新增：图表组件
        ├── TrendChart.vue
        ├── SentimentChart.vue
        ├── PlatformChart.vue
        └── ComparisonChart.vue
```

---

## 8. 实现步骤

### Phase 1: 平台过滤配置化

1. 添加平台配置到 `_DEFAULTS`
2. 实现平台配置 API
3. 修改插件逻辑，使用 HTTP 获取配置
4. 更新前端配置 UI

### Phase 2: 天气服务统一

1. 新增天气 API 端点（复用现有 WeatherService）
2. 删除插件层的 `weather_service.py`
3. 修改插件逻辑，使用 HTTP 获取天气
4. 更新前端天气配置 UI

### Phase 3: 上下文模板自定义

1. 添加 Jinja2 依赖
2. 实现模板服务（TemplateService）
3. 实现模板 API
4. 修改插件逻辑，使用 HTTP 获取渲染后的上下文
5. 更新前端模板配置 UI

### Phase 4: 注入效果分析

1. 扩展日志表结构
2. 实现分析服务（AnalysisService）
3. 实现分析 API
4. 添加 ECharts 依赖
5. 实现分析前端页面

---

## 9. 错误处理

| 场景 | 处理方式 |
|------|----------|
| Backend 服务不可用 | 插件跳过注入，记录错误日志 |
| 平台不在白名单 | 跳过注入，记录日志 |
| 天气 API 调用失败 | 返回 None，继续注入其他内容 |
| 模板渲染失败 | 使用默认模板，记录错误 |
| 数据库连接失败 | 跳过注入，记录错误 |

---

## 10. 测试策略

### 10.1 单元测试

- 测试平台白名单过滤逻辑
- 测试模板渲染引擎
- 测试分析服务数据聚合

### 10.2 集成测试

- 测试插件与 Backend 的 HTTP 调用
- 测试前端与 Backend 的 API 交互
- 测试完整的注入流程

### 10.3 端到端测试

- 测试用户配置平台白名单后注入行为
- 测试模板自定义后注入内容
- 测试分析页面数据展示

---

## 11. 待确认项

- [ ] 情感分析使用简单关键词匹配还是调用外部 API？
- [ ] 是否需要支持模板导入/导出功能？
- [ ] 分析数据是否需要定期清理？
