# 被动意识系统重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构被动意识系统，实现平台过滤配置化、天气服务统一、上下文模板自定义、注入效果分析

**Architecture:** 插件层通过 HTTP 调用 Backend API 获取所有数据，Backend 统一处理业务逻辑，前端提供配置和分析界面

**Tech Stack:** Python 3, FastAPI, Vue 3, Naive UI, Jinja2, ECharts

---

## 文件结构

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

plugins/passive-consciousness/
├── __init__.py                    # 修改：重构注入逻辑
├── plugin.yaml                    # 保留
├── config_reader.py               # 保留
├── hindsight_client.py            # 保留
├── consciousness_engine.py        # 删除
├── context_builder.py             # 删除
└── weather_service.py             # 删除

frontend/src/
├── views/
│   ├── PassiveConsciousness.vue   # 修改
│   └── Analysis.vue               # 新增
├── api/
│   └── passive_consciousness.js   # 修改
└── components/
    └── charts/                    # 新增
        ├── TrendChart.vue
        ├── SentimentChart.vue
        ├── PlatformChart.vue
        └── ComparisonChart.vue
```

---

## Phase 1: 平台过滤配置化

### Task 1: 添加平台配置到 Backend

**Files:**
- Modify: `backend/services/passive_consciousness_service.py`
- Modify: `backend/routers/passive_consciousness.py`

- [ ] **Step 1: 添加平台配置到 _DEFAULTS**

在 `backend/services/passive_consciousness_service.py` 的 `_DEFAULTS` 字典中添加：

```python
_DEFAULTS = {
    # ... 现有配置 ...
    "passive_consciousness.platforms.enabled": "true",
    "passive_consciousness.platforms.whitelist": '["weixin"]',
}
```

- [ ] **Step 2: 添加平台配置 API**

在 `backend/routers/passive_consciousness.py` 中添加：

```python
@router.get("/platforms")
async def get_platforms():
    """获取平台配置"""
    try:
        config = PassiveConsciousnessService.get_config()
        platforms = config.get("platforms", {})
        return {
            "success": True,
            "data": {
                "enabled": platforms.get("enabled", True),
                "whitelist": platforms.get("whitelist", ["weixin"]),
            }
        }
    except Exception as e:
        logger.error("获取平台配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/platforms")
async def update_platforms(platforms: dict):
    """更新平台配置"""
    try:
        config = PassiveConsciousnessService.get_config()
        config["platforms"] = platforms
        PassiveConsciousnessService.update_config(config)
        return {"success": True, "message": "平台配置已保存"}
    except Exception as e:
        logger.error("保存平台配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms/available")
async def get_available_platforms():
    """获取可用平台列表"""
    return {
        "success": True,
        "data": [
            {"id": "weixin", "name": "微信", "description": "微信公众号/小程序"},
            {"id": "feishu", "name": "飞书", "description": "飞书机器人"},
            {"id": "telegram", "name": "Telegram", "description": "Telegram Bot"},
            {"id": "discord", "name": "Discord", "description": "Discord Bot"},
            {"id": "slack", "name": "Slack", "description": "Slack Bot"},
            {"id": "custom", "name": "自定义", "description": "自定义平台"},
        ]
    }
```

- [ ] **Step 3: 验证 API**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from routers.passive_consciousness import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/passive_consciousness_service.py backend/routers/passive_consciousness.py
git commit -m "feat: 添加平台过滤配置 API"
```

---

### Task 2: 更新前端平台配置 UI

**Files:**
- Modify: `frontend/src/views/PassiveConsciousness.vue`
- Modify: `frontend/src/api/passive_consciousness.js`

- [ ] **Step 1: 添加平台配置到 config ref**

在 `frontend/src/views/PassiveConsciousness.vue` 的 `config` ref 中添加：

```javascript
const config = ref({
  // ... 现有配置 ...
  platforms: {
    enabled: true,
    whitelist: ['weixin']
  }
})
```

- [ ] **Step 2: 添加平台配置 UI**

在配置 Tab 的注入配置区块后添加：

```vue
<!-- 平台过滤 -->
<n-divider>平台过滤</n-divider>
<n-form-item label="启用平台过滤">
  <n-switch v-model:value="config.platforms.enabled" />
</n-form-item>

<n-form-item label="启用的平台" v-if="config.platforms.enabled">
  <n-select
    v-model:value="config.platforms.whitelist"
    multiple
    :options="platformOptions"
    placeholder="选择启用被动意识的平台"
  />
</n-form-item>
```

- [ ] **Step 3: 更新 platformOptions**

```javascript
const platformOptions = [
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' },
  { label: 'Telegram', value: 'telegram' },
  { label: 'Discord', value: 'discord' },
  { label: 'Slack', value: 'slack' },
  { label: '自定义', value: 'custom' }
]
```

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/views/PassiveConsciousness.vue
git commit -m "feat: 添加平台过滤配置 UI"
```

---

### Task 3: 重构插件平台过滤逻辑

**Files:**
- Modify: `plugins/passive-consciousness/__init__.py`

- [ ] **Step 1: 添加 HTTP 工具函数**

在 `plugins/passive-consciousness/__init__.py` 顶部添加：

```python
import urllib.request
import json

def _http_get(url: str, timeout: int = 5) -> dict:
    """发送 HTTP GET 请求"""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "hermes-passive-consciousness/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

- [ ] **Step 2: 修改平台检查逻辑**

替换 `inject_consciousness_context` 函数中的平台检查部分：

```python
def inject_consciousness_context(
    session_id: str = "",
    platform: str = "",
    sender_id: str = "",
    user_message: str = "",
    conversation_history: list = None,
    **kwargs,
) -> Optional[dict]:
    try:
        # 1. 从 Backend 获取平台配置
        try:
            platforms_resp = _http_get("http://localhost:18720/api/passive-consciousness/platforms")
            platforms_data = platforms_resp.get("data", {})
            platforms_enabled = platforms_data.get("enabled", True)
            whitelist = platforms_data.get("whitelist", ["weixin"])
        except Exception as e:
            logger.warning("获取平台配置失败: %s，使用默认配置", e)
            platforms_enabled = True
            whitelist = ["weixin"]
        
        # 2. 检查平台是否在白名单中
        if platforms_enabled and platform not in whitelist:
            logger.debug("平台 %s 不在白名单中，跳过注入", platform)
            _write_log(
                session_id=session_id, platform=platform, sender_id=sender_id,
                user_message=user_message, status="skipped",
                error_message=f"平台 {platform} 不在白名单中",
            )
            return None
        
        # ... 继续原有逻辑 ...
```

- [ ] **Step 3: 验证插件**

```bash
cd /home/ubuntu/.hermes/plugins/passive-consciousness
python -c "from __init__ import inject_consciousness_context; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes
git add plugins/passive-consciousness/__init__.py
git commit -m "refactor: 插件平台过滤改为从 Backend 获取配置"
```

---

## Phase 2: 天气服务统一

### Task 4: 新增天气 API 端点

**Files:**
- Modify: `backend/routers/passive_consciousness.py`

- [ ] **Step 1: 添加天气 API 端点**

在 `backend/routers/passive_consciousness.py` 中添加：

```python
@router.get("/weather")
async def get_weather():
    """获取当前天气（带缓存）"""
    try:
        from services.weather_service import WeatherService
        
        config = PassiveConsciousnessService.get_config()
        weather_config = config.get("weather", {})
        
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
                    "weather_code": current.get("weathercode", ""),
                    "temperature": current.get("temp", ""),
                    "humidity": current.get("humidity", ""),
                    "feels_like": current.get("feelsLike", current.get("temp", "")),
                    "pressure": current.get("pressure", ""),
                    "visibility": current.get("visibility", ""),
                    "wind_dir": current.get("winddirection", ""),
                    "wind_scale": current.get("windpower", ""),
                    "wind_speed": current.get("windSpeed", ""),
                    "uv_index": current.get("uv_index", ""),
                    "uv_desc": current.get("uv_desc", ""),
                    "dressing": current.get("dressing", ""),
                    "comfort": current.get("comfort", ""),
                    "cold_risk": current.get("cold_risk", ""),
                    "forecast": result.get("forecast", []),
                    "updated_at": result.get("updated_at", ""),
                    "provider": result.get("provider", ""),
                    "cache_status": result.get("cache_status", {}),
                }
            }
        else:
            return {"success": False, "error": result.get("error", "未知错误")}
    except Exception as e:
        logger.error("获取天气失败: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/weather/refresh")
async def refresh_weather():
    """强制刷新天气"""
    try:
        from services.weather_service import WeatherService
        
        config = PassiveConsciousnessService.get_config()
        weather_config = config.get("weather", {})
        
        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}
        
        service = WeatherService()
        service.clear_cache()
        
        result = await service.get_weather(
            amap_key=weather_config.get("amap_key", ""),
            adcode=weather_config.get("adcode", "370100"),
            cache_ttl=0,
            provider=weather_config.get("provider", "qweather"),
            city=weather_config.get("city", ""),
            qweather_key=weather_config.get("qweather_key", ""),
            qweather_geo_url=weather_config.get("qweather_geo_url", "https://geoapi.qweather.com/v2/city/lookup"),
            qweather_weather_url=weather_config.get("qweather_weather_url", "https://devapi.qweather.com/v7/weather/now"),
        )
        
        if result.get("success"):
            return {"success": True, "message": "天气数据已刷新"}
        else:
            return {"success": False, "error": result.get("error", "未知错误")}
    except Exception as e:
        logger.error("刷新天气失败: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/weather/status")
async def get_weather_status():
    """获取天气服务状态"""
    try:
        from services.weather_service import WeatherService
        
        config = PassiveConsciousnessService.get_config()
        weather_config = config.get("weather", {})
        
        service = WeatherService()
        cache_status = service.get_cache_status()
        
        return {
            "success": True,
            "data": {
                "enabled": weather_config.get("enabled", False),
                "provider": weather_config.get("provider", "qweather"),
                "city": weather_config.get("city", ""),
                "cache": cache_status,
            }
        }
    except Exception as e:
        logger.error("获取天气状态失败: %s", e)
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
git commit -m "feat: 新增天气 API 端点供插件调用"
```

---

### Task 5: 重构插件天气逻辑

**Files:**
- Modify: `plugins/passive-consciousness/__init__.py`
- Delete: `plugins/passive-consciousness/weather_service.py`

- [ ] **Step 1: 修改插件天气获取逻辑**

在 `plugins/passive-consciousness/__init__.py` 中修改天气获取部分：

```python
# 5. 可选：调天气 API
weather_data = None
weather_config = config.get("weather", {})
if weather_config.get("enabled", False):
    try:
        weather_resp = _http_get("http://localhost:18720/api/passive-consciousness/weather")
        if weather_resp.get("success"):
            weather_data = weather_resp.get("data")
    except Exception as e:
        logger.warning("获取天气失败: %s", e)
```

- [ ] **Step 2: 删除插件层天气服务**

```bash
rm plugins/passive-consciousness/weather_service.py
```

- [ ] **Step 3: 验证插件**

```bash
cd /home/ubuntu/.hermes/plugins/passive-consciousness
python -c "from __init__ import inject_consciousness_context; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes
git add plugins/passive-consciousness/__init__.py
git rm plugins/passive-consciousness/weather_service.py
git commit -m "refactor: 插件天气改为从 Backend API 获取"
```

---

## Phase 3: 上下文模板自定义

### Task 6: 添加 Jinja2 依赖和模板服务

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/services/template_service.py`

- [ ] **Step 1: 添加 Jinja2 依赖**

在 `backend/requirements.txt` 中添加：

```
jinja2>=3.1.0
```

- [ ] **Step 2: 安装依赖**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
pip install jinja2
```

- [ ] **Step 3: 创建模板服务**

创建 `backend/services/template_service.py`：

```python
"""
模板服务 - Jinja2 模板渲染
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

logger = logging.getLogger("hermes.template_service")

# 默认模板
DEFAULT_TEMPLATE = """--- [CONSCIOUSNESS_CONTEXT] ---
以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：

{% if inject_emotion %}
🎭 情绪状态：{{ emotional_label }}（强度 {{ "%.1f"|format(emotional_intensity) }})
{% endif %}

{% if inject_heat %}
🔥 聊天热度：{{ chat_heat_label }}（近1小时 {{ chat_heat_count }} 条消息）
{% endif %}

{% if inject_longing %}
💕 想念程度：{{ longing_label }}（分数 {{ "%.2f"|format(longing_score) }})
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

--- /[CONSCIOUSNESS_CONTEXT] ---"""

# 默认模板列表
DEFAULT_TEMPLATES = [
    {
        "id": "default",
        "name": "日常模板",
        "description": "默认的上下文注入模板",
        "content": DEFAULT_TEMPLATE,
        "is_default": True,
    }
]


class TemplateService:
    """模板服务"""
    
    _env = Environment(loader=BaseLoader())
    
    @staticmethod
    def get_templates() -> List[Dict[str, Any]]:
        """获取模板列表"""
        from services.passive_consciousness_service import PassiveConsciousnessService
        from services.config_service import ConfigService
        
        db = ActiveSession()
        try:
            config = PassiveConsciousnessService.get_config()
            templates_json = config.get("templates", {}).get("list", None)
            
            if templates_json:
                return json.loads(templates_json) if isinstance(templates_json, str) else templates_json
            else:
                return DEFAULT_TEMPLATES
        finally:
            db.close()
    
    @staticmethod
    def get_template(template_id: str) -> Optional[Dict[str, Any]]:
        """获取单个模板"""
        templates = TemplateService.get_templates()
        for t in templates:
            if t["id"] == template_id:
                return t
        return None
    
    @staticmethod
    def get_active_template() -> Dict[str, Any]:
        """获取当前激活的模板"""
        from services.passive_consciousness_service import PassiveConsciousnessService
        
        config = PassiveConsciousnessService.get_config()
        active_id = config.get("templates", {}).get("active_id", "default")
        
        template = TemplateService.get_template(active_id)
        if template:
            return template
        
        # 回退到默认模板
        return DEFAULT_TEMPLATES[0]
    
    @staticmethod
    def render_template(
        template_content: str,
        data: Dict[str, Any],
    ) -> str:
        """渲染模板"""
        try:
            template = TemplateService._env.from_string(template_content)
            return template.render(**data)
        except TemplateSyntaxError as e:
            logger.error("模板语法错误: %s", e)
            raise ValueError(f"模板语法错误: {e}")
        except Exception as e:
            logger.error("模板渲染失败: %s", e)
            raise
    
    @staticmethod
    def render_active_template(data: Dict[str, Any]) -> str:
        """渲染当前激活的模板"""
        template = TemplateService.get_active_template()
        return TemplateService.render_template(template["content"], data)
    
    @staticmethod
    def preview_template(template_content: str, data: Dict[str, Any] = None) -> str:
        """预览模板渲染结果"""
        if data is None:
            data = TemplateService._get_mock_data()
        return TemplateService.render_template(template_content, data)
    
    @staticmethod
    def _get_mock_data() -> Dict[str, Any]:
        """获取模拟数据用于预览"""
        return {
            "emotional_intensity": 0.65,
            "emotional_label": "八卦",
            "chat_heat": 2.5,
            "chat_heat_label": "hot",
            "chat_heat_count": 5,
            "longing_score": 0.35,
            "longing_label": "missing",
            "weather": {
                "city": "北京",
                "weather": "晴",
                "temperature": 28,
                "humidity": 45,
                "feels_like": 30,
                "wind_dir": "东南风",
                "wind_scale": "3-4级",
                "uv_desc": "较强",
            },
            "memories": [
                {"text": "上次聊到了天气和心情"},
                {"text": "讨论了周末计划"},
            ],
            "reflection": "用户最近情绪稳定，聊天频率适中",
            "inject_emotion": True,
            "inject_heat": True,
            "inject_longing": True,
            "inject_memory": True,
            "now": datetime.now(),
            "platform": "weixin",
            "sender_id": "user_001",
        }
    
    @staticmethod
    def get_variables() -> List[Dict[str, str]]:
        """获取可用变量列表"""
        return [
            {"name": "emotional_intensity", "type": "float", "description": "情绪强度 (0.0-1.0)"},
            {"name": "emotional_label", "type": "string", "description": "情绪标签"},
            {"name": "chat_heat", "type": "float", "description": "聊天热度"},
            {"name": "chat_heat_label", "type": "string", "description": "热度标签"},
            {"name": "chat_heat_count", "type": "int", "description": "近1小时消息数"},
            {"name": "longing_score", "type": "float", "description": "想念分数 (0.0-1.0)"},
            {"name": "longing_label", "type": "string", "description": "想念标签"},
            {"name": "weather", "type": "object", "description": "天气数据"},
            {"name": "memories", "type": "list", "description": "Hindsight 记忆列表"},
            {"name": "reflection", "type": "string", "description": "Hindsight 反思文本"},
            {"name": "inject_emotion", "type": "bool", "description": "是否注入情绪"},
            {"name": "inject_heat", "type": "bool", "description": "是否注入热度"},
            {"name": "inject_longing", "type": "bool", "description": "是否注入想念"},
            {"name": "inject_memory", "type": "bool", "description": "是否注入记忆"},
            {"name": "now", "type": "datetime", "description": "当前时间"},
            {"name": "platform", "type": "string", "description": "当前平台"},
            {"name": "sender_id", "type": "string", "description": "发送者 ID"},
        ]


# 导入 ActiveSession（避免循环导入）
from models.database import ActiveSession
```

- [ ] **Step 4: 验证模板服务**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from services.template_service import TemplateService; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/requirements.txt backend/services/template_service.py
git commit -m "feat: 添加 Jinja2 模板服务"
```

---

### Task 7: 添加模板配置和 API

**Files:**
- Modify: `backend/services/passive_consciousness_service.py`
- Modify: `backend/routers/passive_consciousness.py`

- [ ] **Step 1: 添加模板配置到 _DEFAULTS**

在 `backend/services/passive_consciousness_service.py` 的 `_DEFAULTS` 字典中添加：

```python
_DEFAULTS = {
    # ... 现有配置 ...
    "passive_consciousness.templates.list": json.dumps(DEFAULT_TEMPLATES, ensure_ascii=False),
    "passive_consciousness.templates.active_id": "default",
}
```

- [ ] **Step 2: 添加模板 API**

在 `backend/routers/passive_consciousness.py` 中添加：

```python
@router.get("/templates")
async def get_templates():
    """获取模板列表"""
    try:
        from services.template_service import TemplateService
        templates = TemplateService.get_templates()
        return {"success": True, "data": templates}
    except Exception as e:
        logger.error("获取模板列表失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """获取单个模板"""
    try:
        from services.template_service import TemplateService
        template = TemplateService.get_template(template_id)
        if template:
            return {"success": True, "data": template}
        else:
            raise HTTPException(status_code=404, detail="模板不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取模板失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(template: dict):
    """创建模板"""
    try:
        from services.template_service import TemplateService
        
        # 验证必填字段
        if not template.get("id") or not template.get("name") or not template.get("content"):
            raise HTTPException(status_code=400, detail="缺少必填字段")
        
        # 检查 ID 是否已存在
        existing = TemplateService.get_template(template["id"])
        if existing:
            raise HTTPException(status_code=400, detail="模板 ID 已存在")
        
        # 添加到模板列表
        templates = TemplateService.get_templates()
        templates.append(template)
        
        # 保存到配置
        config = PassiveConsciousnessService.get_config()
        if "templates" not in config:
            config["templates"] = {}
        config["templates"]["list"] = templates
        PassiveConsciousnessService.update_config(config)
        
        return {"success": True, "message": "模板已创建"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("创建模板失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/templates/{template_id}")
async def update_template(template_id: str, template: dict):
    """更新模板"""
    try:
        from services.template_service import TemplateService
        
        # 检查模板是否存在
        existing = TemplateService.get_template(template_id)
        if not existing:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 更新模板
        templates = TemplateService.get_templates()
        for i, t in enumerate(templates):
            if t["id"] == template_id:
                templates[i] = {**t, **template, "id": template_id}
                break
        
        # 保存到配置
        config = PassiveConsciousnessService.get_config()
        if "templates" not in config:
            config["templates"] = {}
        config["templates"]["list"] = templates
        PassiveConsciousnessService.update_config(config)
        
        return {"success": True, "message": "模板已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新模板失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """删除模板"""
    try:
        from services.template_service import TemplateService
        
        # 检查是否是默认模板
        if template_id == "default":
            raise HTTPException(status_code=400, detail="不能删除默认模板")
        
        # 检查模板是否存在
        existing = TemplateService.get_template(template_id)
        if not existing:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 删除模板
        templates = TemplateService.get_templates()
        templates = [t for t in templates if t["id"] != template_id]
        
        # 保存到配置
        config = PassiveConsciousnessService.get_config()
        if "templates" not in config:
            config["templates"] = {}
        config["templates"]["list"] = templates
        
        # 如果删除的是当前激活的模板，切换到默认模板
        if config.get("templates", {}).get("active_id") == template_id:
            config["templates"]["active_id"] = "default"
        
        PassiveConsciousnessService.update_config(config)
        
        return {"success": True, "message": "模板已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除模板失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/preview")
async def preview_template(template_id: str, data: dict = None):
    """预览模板渲染结果"""
    try:
        from services.template_service import TemplateService
        
        template = TemplateService.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        preview = TemplateService.preview_template(template["content"], data)
        return {"success": True, "data": {"preview": preview}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("预览模板失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/variables")
async def get_template_variables():
    """获取可用变量列表"""
    try:
        from services.template_service import TemplateService
        variables = TemplateService.get_variables()
        return {"success": True, "data": variables}
    except Exception as e:
        logger.error("获取变量列表失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 验证 API**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from routers.passive_consciousness import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add backend/services/passive_consciousness_service.py backend/routers/passive_consciousness.py
git commit -m "feat: 添加模板配置和 API"
```

---

### Task 8: 重构插件上下文渲染逻辑

**Files:**
- Modify: `plugins/passive-consciousness/__init__.py`
- Delete: `plugins/passive-consciousness/consciousness_engine.py`
- Delete: `plugins/passive-consciousness/context_builder.py`

- [ ] **Step 1: 修改插件上下文渲染逻辑**

在 `plugins/passive-consciousness/__init__.py` 中修改上下文渲染部分：

```python
# 7. 渲染模板
context = None
try:
    # 准备模板数据
    template_data = {
        "emotional_intensity": consciousness_data.get("emotional_intensity", {}).get("intensity", 0.0),
        "emotional_label": consciousness_data.get("emotional_intensity", {}).get("label", "工作"),
        "chat_heat": consciousness_data.get("chat_heat", {}).get("heat", 0.0),
        "chat_heat_label": consciousness_data.get("chat_heat", {}).get("label", "cold"),
        "chat_heat_count": consciousness_data.get("chat_heat", {}).get("recent_count", 0),
        "longing_score": consciousness_data.get("longing", {}).get("score", 0.0),
        "longing_label": consciousness_data.get("longing", {}).get("label", "calm"),
        "weather": weather_data,
        "memories": memories,
        "reflection": reflection,
        "inject_emotion": config.get("passive", {}).get("inject_emotion", True),
        "inject_heat": config.get("passive", {}).get("inject_heat", True),
        "inject_longing": True,
        "inject_memory": config.get("passive", {}).get("inject_memory", True),
        "now": datetime.now(),
        "platform": platform,
        "sender_id": sender_id,
    }
    
    # 调用 Backend 模板渲染 API
    render_resp = _http_post(
        "http://localhost:18720/api/passive-consciousness/templates/render",
        data=template_data
    )
    
    if render_resp.get("success"):
        context = render_resp.get("data", {}).get("context")
    else:
        logger.warning("模板渲染失败: %s", render_resp.get("error"))
except Exception as e:
    logger.warning("上下文渲染失败: %s", e)

if not context:
    return None
```

- [ ] **Step 2: 添加 HTTP POST 工具函数**

在 `plugins/passive-consciousness/__init__.py` 的 `_http_get` 函数后添加：

```python
def _http_post(url: str, data: dict, timeout: int = 10) -> dict:
    """发送 HTTP POST 请求"""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "hermes-passive-consciousness/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

- [ ] **Step 3: 添加模板渲染 API**

在 `backend/routers/passive_consciousness.py` 中添加：

```python
@router.post("/templates/render")
async def render_template(data: dict):
    """渲染模板（供插件调用）"""
    try:
        from services.template_service import TemplateService
        
        context = TemplateService.render_active_template(data)
        return {"success": True, "data": {"context": context}}
    except Exception as e:
        logger.error("渲染模板失败: %s", e)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 4: 删除旧的模块文件**

```bash
rm plugins/passive-consciousness/consciousness_engine.py
rm plugins/passive-consciousness/context_builder.py
```

- [ ] **Step 5: 验证插件**

```bash
cd /home/ubuntu/.hermes/plugins/passive-consciousness
python -c "from __init__ import inject_consciousness_context; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: 提交**

```bash
cd /home/ubuntu/.hermes
git add plugins/passive-consciousness/__init__.py
git rm plugins/passive-consciousness/consciousness_engine.py plugins/passive-consciousness/context_builder.py
git add backend/routers/passive_consciousness.py
git commit -m "refactor: 插件上下文改为从 Backend 模板渲染获取"
```

---

### Task 9: 更新前端模板配置 UI

**Files:**
- Modify: `frontend/src/views/PassiveConsciousness.vue`
- Modify: `frontend/src/api/passive_consciousness.js`

- [ ] **Step 1: 添加模板配置到 config ref**

在 `frontend/src/views/PassiveConsciousness.vue` 的 `config` ref 中添加：

```javascript
const config = ref({
  // ... 现有配置 ...
  templates: {
    list: [],
    active_id: 'default'
  }
})
```

- [ ] **Step 2: 添加模板配置 UI**

在配置 Tab 的天气配置区块后添加：

```vue
<!-- 上下文模板 -->
<n-divider>上下文模板</n-divider>
<n-form-item label="当前模板">
  <n-select
    v-model:value="config.templates.active_id"
    :options="templateOptions"
    placeholder="选择注入模板"
  />
</n-form-item>

<n-button @click="openTemplateEditor" size="small" style="margin-bottom: 12px">
  编辑模板
</n-button>

<!-- 模板编辑器弹窗 -->
<n-modal v-model:show="showTemplateEditor" title="模板编辑器" style="width: 80%">
  <n-grid :cols="2" :x-gap="12">
    <n-grid-item>
      <n-card title="模板内容" size="small">
        <n-input
          v-model:value="editingTemplate.content"
          type="textarea"
          :rows="20"
          placeholder="输入模板内容..."
        />
      </n-card>
    </n-grid-item>
    <n-grid-item>
      <n-card title="预览" size="small">
        <n-code :code="previewResult" language="text" word-wrap />
      </n-card>
    </n-grid-item>
  </n-grid>
  
  <template #footer>
    <n-space>
      <n-button @click="previewTemplate">预览</n-button>
      <n-button type="primary" @click="saveTemplate">保存</n-button>
    </n-space>
  </template>
</n-modal>
```

- [ ] **Step 3: 添加模板相关方法**

```javascript
// 模板相关
const showTemplateEditor = ref(false)
const editingTemplate = ref({ id: '', name: '', content: '' })
const previewResult = ref('')
const templateOptions = computed(() => {
  return config.value.templates.list.map(t => ({
    label: t.name,
    value: t.id
  }))
})

const openTemplateEditor = () => {
  const activeId = config.value.templates.active_id
  const template = config.value.templates.list.find(t => t.id === activeId)
  if (template) {
    editingTemplate.value = { ...template }
  }
  showTemplateEditor.value = true
}

const previewTemplate = async () => {
  try {
    const resp = await api.previewTemplate('default', {})
    previewResult.value = resp.data?.preview || '预览失败'
  } catch (e) {
    message.error('预览失败: ' + e.message)
  }
}

const saveTemplate = async () => {
  try {
    await api.updateTemplate(editingTemplate.value.id, editingTemplate.value)
    message.success('模板已保存')
    showTemplateEditor.value = false
    await loadConfig()
  } catch (e) {
    message.error('保存失败: ' + e.message)
  }
}
```

- [ ] **Step 4: 添加模板 API 调用**

在 `frontend/src/api/passive_consciousness.js` 中添加：

```javascript
/**
 * 获取模板列表
 */
export function getTemplates() {
  return http.get('/passive-consciousness/templates')
}

/**
 * 获取单个模板
 */
export function getTemplate(id) {
  return http.get(`/passive-consciousness/templates/${id}`)
}

/**
 * 创建模板
 */
export function createTemplate(template) {
  return http.post('/passive-consciousness/templates', template)
}

/**
 * 更新模板
 */
export function updateTemplate(id, template) {
  return http.put(`/passive-consciousness/templates/${id}`, template)
}

/**
 * 删除模板
 */
export function deleteTemplate(id) {
  return http.delete(`/passive-consciousness/templates/${id}`)
}

/**
 * 预览模板
 */
export function previewTemplate(id, data) {
  return http.post(`/passive-consciousness/templates/${id}/preview`, data)
}

/**
 * 获取可用变量
 */
export function getTemplateVariables() {
  return http.get('/passive-consciousness/templates/variables')
}
```

- [ ] **Step 5: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/views/PassiveConsciousness.vue frontend/src/api/passive_consciousness.js
git commit -m "feat: 添加模板配置 UI"
```

---

## Phase 4: 注入效果分析

### Task 10: 扩展日志表和分析服务

**Files:**
- Modify: `plugins/passive-consciousness/__init__.py`
- Create: `backend/services/analysis_service.py`

- [ ] **Step 1: 扩展日志表结构**

在 `plugins/passive-consciousness/__init__.py` 的 `_write_log` 函数中修改 CREATE TABLE 语句：

```sql
CREATE TABLE IF NOT EXISTS passive_consciousness_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    platform TEXT,
    sender_id TEXT,
    longing_score REAL DEFAULT 0.0,
    longing_label TEXT DEFAULT 'calm',
    chat_heat REAL DEFAULT 0.0,
    chat_heat_label TEXT DEFAULT 'cold',
    emotional_intensity REAL DEFAULT 0.0,
    emotional_label TEXT DEFAULT '工作',
    weather_city TEXT,
    weather_info TEXT,
    memories_count INTEGER DEFAULT 0,
    has_reflection INTEGER DEFAULT 0,
    template_id TEXT,
    context_length INTEGER DEFAULT 0,
    context_preview TEXT,
    status TEXT DEFAULT 'success',
    error_message TEXT,
    user_message_preview TEXT
)
```

- [ ] **Step 2: 更新日志写入逻辑**

在 `_write_log` 函数中添加新字段：

```python
cursor.execute("""
    INSERT INTO passive_consciousness_logs (
        timestamp, session_id, platform, sender_id,
        longing_score, longing_label, chat_heat, chat_heat_label,
        emotional_intensity, emotional_label,
        weather_city, weather_info,
        memories_count, has_reflection,
        template_id, context_length, context_preview,
        status, error_message, user_message_preview
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    datetime.now().isoformat(),
    session_id, platform, sender_id,
    longing_score, longing_label, chat_heat, chat_heat_label,
    emotional_intensity, emotional_label,
    weather_city, weather_info,
    memories_count, has_reflection,
    template_id, len(context), context[:500] if context else None,
    status, error_message, user_message_preview,
))
```

- [ ] **Step 3: 创建分析服务**

创建 `backend/services/analysis_service.py`：

```python
"""
分析服务 - 注入效果分析
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy import text

from models.database import ActiveSession, state_engine

logger = logging.getLogger("hermes.analysis_service")


class AnalysisService:
    """注入效果分析服务"""
    
    @staticmethod
    def get_injection_stats(
        start_date: str = None,
        end_date: str = None,
        platform: str = None,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """获取注入统计"""
        try:
            with state_engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {}
                
                if start_date:
                    conditions.append("timestamp >= :start_date")
                    params["start_date"] = start_date
                if end_date:
                    conditions.append("timestamp <= :end_date")
                    params["end_date"] = end_date
                if platform:
                    conditions.append("platform = :platform")
                    params["platform"] = platform
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                # 总注入次数
                row = conn.execute(text(
                    f"SELECT COUNT(*) FROM passive_consciousness_logs WHERE {where_clause}"
                ), params).fetchone()
                total_injections = row[0] if row else 0
                
                # 成功次数
                row = conn.execute(text(
                    f"SELECT COUNT(*) FROM passive_consciousness_logs WHERE {where_clause} AND status = 'success'"
                ), params).fetchone()
                success_count = row[0] if row else 0
                
                # 错误次数
                row = conn.execute(text(
                    f"SELECT COUNT(*) FROM passive_consciousness_logs WHERE {where_clause} AND status = 'error'"
                ), params).fetchone()
                error_count = row[0] if row else 0
                
                # 平均上下文长度
                row = conn.execute(text(
                    f"SELECT AVG(context_length) FROM passive_consciousness_logs WHERE {where_clause} AND status = 'success'"
                ), params).fetchone()
                avg_context_length = round(row[0], 2) if row and row[0] else 0
                
                # 各平台分布
                rows = conn.execute(text(
                    f"SELECT platform, COUNT(*) as cnt FROM passive_consciousness_logs WHERE {where_clause} GROUP BY platform"
                ), params).fetchall()
                by_platform = {row[0]: row[1] for row in rows if row[0]}
                
                # 各状态分布
                rows = conn.execute(text(
                    f"SELECT status, COUNT(*) as cnt FROM passive_consciousness_logs WHERE {where_clause} GROUP BY status"
                ), params).fetchall()
                by_status = {row[0]: row[1] for row in rows if row[0]}
                
                # 各小时分布
                rows = conn.execute(text(
                    f"SELECT strftime('%H', timestamp) as hour, COUNT(*) as cnt FROM passive_consciousness_logs WHERE {where_clause} GROUP BY hour"
                ), params).fetchall()
                by_hour = {row[0]: row[1] for row in rows if row[0]}
                
                # 各模板分布
                rows = conn.execute(text(
                    f"SELECT template_id, COUNT(*) as cnt FROM passive_consciousness_logs WHERE {where_clause} GROUP BY template_id"
                ), params).fetchall()
                by_template = {row[0] or "unknown": row[1] for row in rows}
                
                return {
                    "summary": {
                        "total_injections": total_injections,
                        "success_count": success_count,
                        "error_count": error_count,
                        "success_rate": round(success_count / total_injections, 4) if total_injections > 0 else 0,
                        "avg_context_length": avg_context_length,
                    },
                    "by_platform": by_platform,
                    "by_status": by_status,
                    "by_hour": by_hour,
                    "by_template": by_template,
                }
        except Exception as e:
            logger.error("获取注入统计失败: %s", e)
            raise
    
    @staticmethod
    def get_trend_data(
        metric: str,
        start_date: str = None,
        end_date: str = None,
        platform: str = None
    ) -> Dict[str, Any]:
        """获取趋势数据"""
        try:
            # 确定要查询的字段
            field_map = {
                "longing": "longing_score",
                "heat": "chat_heat",
                "emotion": "emotional_intensity",
            }
            field = field_map.get(metric, "longing_score")
            
            with state_engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {}
                
                if start_date:
                    conditions.append("timestamp >= :start_date")
                    params["start_date"] = start_date
                if end_date:
                    conditions.append("timestamp <= :end_date")
                    params["end_date"] = end_date
                if platform:
                    conditions.append("platform = :platform")
                    params["platform"] = platform
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                # 查询数据点
                rows = conn.execute(text(
                    f"SELECT timestamp, {field} FROM passive_consciousness_logs "
                    f"WHERE {where_clause} AND status = 'success' "
                    f"ORDER BY timestamp"
                ), params).fetchall()
                
                data_points = [
                    {"timestamp": row[0], "value": round(row[1], 4)}
                    for row in rows
                ]
                
                # 计算统计信息
                if data_points:
                    values = [dp["value"] for dp in data_points]
                    avg_val = sum(values) / len(values)
                    max_val = max(values)
                    min_val = min(values)
                    std_dev = (sum((v - avg_val) ** 2 for v in values) / len(values)) ** 0.5
                else:
                    avg_val = max_val = min_val = std_dev = 0
                
                return {
                    "metric": metric,
                    "period": f"{start_date or '开始'} ~ {end_date or '现在'}",
                    "data_points": data_points,
                    "statistics": {
                        "avg": round(avg_val, 4),
                        "max": round(max_val, 4),
                        "min": round(min_val, 4),
                        "std_dev": round(std_dev, 4),
                    }
                }
        except Exception as e:
            logger.error("获取趋势数据失败: %s", e)
            raise
    
    @staticmethod
    def get_sentiment_analysis(
        start_date: str = None,
        end_date: str = None,
        platform: str = None
    ) -> Dict[str, Any]:
        """获取情感分析"""
        try:
            with state_engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {}
                
                if start_date:
                    conditions.append("timestamp >= :start_date")
                    params["start_date"] = start_date
                if end_date:
                    conditions.append("timestamp <= :end_date")
                    params["end_date"] = end_date
                if platform:
                    conditions.append("platform = :platform")
                    params["platform"] = platform
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                # 情感分布
                rows = conn.execute(text(
                    f"SELECT emotional_label, COUNT(*) as cnt "
                    f"FROM passive_consciousness_logs "
                    f"WHERE {where_clause} AND status = 'success' "
                    f"GROUP BY emotional_label"
                ), params).fetchall()
                
                distribution = {row[0]: row[1] for row in rows if row[0]}
                
                # 平均情感强度
                row = conn.execute(text(
                    f"SELECT AVG(emotional_intensity) "
                    f"FROM passive_consciousness_logs "
                    f"WHERE {where_clause} AND status = 'success'"
                ), params).fetchone()
                avg_sentiment_score = round(row[0], 4) if row and row[0] else 0
                
                # 按日期统计
                rows = conn.execute(text(
                    f"SELECT DATE(timestamp) as date, AVG(emotional_intensity) as avg_intensity "
                    f"FROM passive_consciousness_logs "
                    f"WHERE {where_clause} AND status = 'success' "
                    f"GROUP BY date ORDER BY date"
                ), params).fetchall()
                
                trend = [
                    {"date": row[0], "avg_intensity": round(row[1], 4)}
                    for row in rows
                ]
                
                return {
                    "distribution": distribution,
                    "trend": trend,
                    "avg_sentiment_score": avg_sentiment_score,
                }
        except Exception as e:
            logger.error("获取情感分析失败: %s", e)
            raise
```

- [ ] **Step 4: 验证分析服务**

```bash
cd /home/ubuntu/.hermes/hermes-active/backend
python -c "from services.analysis_service import AnalysisService; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add plugins/passive-consciousness/__init__.py backend/services/analysis_service.py
git commit -m "feat: 扩展日志表和添加分析服务"
```

---

### Task 11: 添加分析 API

**Files:**
- Modify: `backend/routers/passive_consciousness.py`

- [ ] **Step 1: 添加分析 API**

在 `backend/routers/passive_consciousness.py` 中添加：

```python
@router.get("/analysis/stats")
async def get_analysis_stats(
    start_date: str = None,
    end_date: str = None,
    platform: str = None,
    group_by: str = "day"
):
    """获取注入统计"""
    try:
        from services.analysis_service import AnalysisService
        stats = AnalysisService.get_injection_stats(start_date, end_date, platform, group_by)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error("获取注入统计失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/trends")
async def get_analysis_trends(
    metric: str = "longing",
    start_date: str = None,
    end_date: str = None,
    platform: str = None
):
    """获取趋势数据"""
    try:
        from services.analysis_service import AnalysisService
        trends = AnalysisService.get_trend_data(metric, start_date, end_date, platform)
        return {"success": True, "data": trends}
    except Exception as e:
        logger.error("获取趋势数据失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/sentiment")
async def get_analysis_sentiment(
    start_date: str = None,
    end_date: str = None,
    platform: str = None
):
    """获取情感分析"""
    try:
        from services.analysis_service import AnalysisService
        sentiment = AnalysisService.get_sentiment_analysis(start_date, end_date, platform)
        return {"success": True, "data": sentiment}
    except Exception as e:
        logger.error("获取情感分析失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
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
git commit -m "feat: 添加分析 API 端点"
```

---

### Task 12: 添加前端分析页面

**Files:**
- Create: `frontend/src/views/Analysis.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/api/passive_consciousness.js`

- [ ] **Step 1: 安装 ECharts**

```bash
cd /home/ubuntu/.hermes/hermes-active/frontend
npm install echarts vue-echarts
```

- [ ] **Step 2: 创建分析页面**

创建 `frontend/src/views/Analysis.vue`：

```vue
<template>
  <div class="analysis-page">
    <n-card title="📊 被动意识效果分析" style="margin-bottom: 16px">
      <!-- 筛选条件 -->
      <n-space style="margin-bottom: 16px">
        <n-date-picker v-model:value="dateRange" type="daterange" />
        <n-select
          v-model:value="selectedPlatform"
          :options="platformOptions"
          placeholder="平台"
          clearable
          style="width: 150px"
        />
        <n-button type="primary" @click="loadData">查询</n-button>
      </n-space>

      <!-- 统计概览 -->
      <n-grid :cols="4" :x-gap="12" :y-gap="12">
        <n-grid-item>
          <n-card title="总注入次数" size="small">
            <n-statistic :value="stats.summary?.total_injections || 0" />
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="成功率" size="small">
            <n-statistic
              :value="((stats.summary?.success_rate || 0) * 100)"
              :precision="1"
              suffix="%"
            />
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="平均上下文长度" size="small">
            <n-statistic :value="stats.summary?.avg_context_length || 0" suffix="字符" />
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="情感得分" size="small">
            <n-statistic :value="sentiment.avg_sentiment_score || 0" :precision="3" />
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-card>

    <!-- 图表区域 -->
    <n-grid :cols="2" :x-gap="12" :y-gap="12">
      <n-grid-item>
        <n-card title="注入趋势" size="small">
          <v-chart :option="trendChartOption" style="height: 300px" autoresize />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="情感分布" size="small">
          <v-chart :option="sentimentChartOption" style="height: 300px" autoresize />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="平台分布" size="small">
          <v-chart :option="platformChartOption" style="height: 300px" autoresize />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="状态分布" size="small">
          <v-chart :option="statusChartOption" style="height: 300px" autoresize />
        </n-card>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import api from '../api/passive_consciousness'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

const message = useMessage()

// 筛选条件
const dateRange = ref(null)
const selectedPlatform = ref(null)

const platformOptions = [
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' },
  { label: 'Telegram', value: 'telegram' },
]

// 数据
const stats = ref({
  summary: {},
  by_platform: {},
  by_status: {},
  by_hour: {},
  by_template: {},
})

const trends = ref({
  data_points: [],
  statistics: {},
})

const sentiment = ref({
  distribution: {},
  trend: [],
  avg_sentiment_score: 0,
})

// 图表配置
const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: trends.value.data_points.map(dp => dp.timestamp.split('T')[0]),
  },
  yAxis: { type: 'value' },
  series: [{
    data: trends.value.data_points.map(dp => dp.value),
    type: 'line',
    smooth: true,
  }],
}))

const sentimentChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: '60%',
    data: Object.entries(sentiment.value.distribution).map(([name, value]) => ({
      name,
      value,
    })),
  }],
}))

const platformChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: Object.keys(stats.value.by_platform),
  },
  yAxis: { type: 'value' },
  series: [{
    data: Object.values(stats.value.by_platform),
    type: 'bar',
  }],
}))

const statusChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: '60%',
    data: Object.entries(stats.value.by_status).map(([name, value]) => ({
      name,
      value,
    })),
  }],
}))

// 加载数据
const loadData = async () => {
  try {
    const params = {}
    if (dateRange.value) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    if (selectedPlatform.value) {
      params.platform = selectedPlatform.value
    }

    const [statsResp, trendsResp, sentimentResp] = await Promise.all([
      api.getAnalysisStats(params),
      api.getAnalysisTrends({ ...params, metric: 'emotion' }),
      api.getAnalysisSentiment(params),
    ])

    stats.value = statsResp.data || {}
    trends.value = trendsResp.data || {}
    sentiment.value = sentimentResp.data || {}
  } catch (e) {
    message.error('加载数据失败: ' + e.message)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.analysis-page {
  padding: 0;
}
</style>
```

- [ ] **Step 3: 添加分析 API 调用**

在 `frontend/src/api/passive_consciousness.js` 中添加：

```javascript
/**
 * 获取注入统计
 */
export function getAnalysisStats(params) {
  return http.get('/passive-consciousness/analysis/stats', { params })
}

/**
 * 获取趋势数据
 */
export function getAnalysisTrends(params) {
  return http.get('/passive-consciousness/analysis/trends', { params })
}

/**
 * 获取情感分析
 */
export function getAnalysisSentiment(params) {
  return http.get('/passive-consciousness/analysis/sentiment', { params })
}
```

- [ ] **Step 4: 添加路由**

在 `frontend/src/router/index.js` 中添加：

```javascript
{
  path: '/analysis',
  name: 'Analysis',
  component: () => import('../views/Analysis.vue'),
  meta: { title: '效果分析', icon: 'chart' }
}
```

- [ ] **Step 5: 提交**

```bash
cd /home/ubuntu/.hermes/hermes-active
git add frontend/src/views/Analysis.vue frontend/src/api/passive_consciousness.js frontend/src/router/index.js
git commit -m "feat: 添加前端分析页面"
```

---

## 自审查清单

### 1. Spec 覆盖检查

- ✅ 平台过滤配置化（Task 1-3）
- ✅ 天气服务统一（Task 4-5）
- ✅ 上下文模板自定义（Task 6-9）
- ✅ 注入效果分析（Task 10-12）

### 2. Placeholder 扫描

- ✅ 无 TBD/TODO
- ✅ 所有代码步骤都有完整代码
- ✅ 所有命令都有精确路径和预期输出

### 3. 类型一致性检查

- ✅ API 返回格式一致（success/data/error）
- ✅ 配置 key 命名一致（passive_consciousness.*）
- ✅ 前端字段名称与后端一致

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-07-31-passive-consciousness-refactor.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
