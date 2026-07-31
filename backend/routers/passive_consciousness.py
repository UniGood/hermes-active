"""
被动意识 API 路由 - 用户消息时注入上下文
"""
import json
import logging
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from models.passive_consciousness import (
    PassiveConsciousnessConfig, PassiveConsciousnessPlatformConfig,
    PassiveConsciousnessStatus,
    SuccessResponse, ChatRecord, TestResult
)
from models.database import ActiveSession, state_engine
from services.config_service import ConfigService
from services.passive_consciousness_service import PassiveConsciousnessService

logger = logging.getLogger("hermes.passive_consciousness.router")

router = APIRouter(prefix="/api/passive-consciousness", tags=["passive-consciousness"])

# 插件目录路径
PLUGIN_DIR = Path.home() / ".hermes" / "plugins" / "passive-consciousness"


# ============ 配置 ============

@router.get("/config")
async def get_config():
    """获取被动意识配置"""
    try:
        return PassiveConsciousnessService.get_config()
    except Exception as e:
        logger.error("获取配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=SuccessResponse)
async def update_config(config: dict):
    """更新被动意识配置"""
    try:
        PassiveConsciousnessService.update_config(config)
        return SuccessResponse(message="配置已保存")
    except Exception as e:
        logger.error("保存配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 平台配置 ============

@router.get("/platforms", response_model=PassiveConsciousnessPlatformConfig)
async def get_platforms():
    """获取平台配置"""
    try:
        config = PassiveConsciousnessService.get_config()
        return config.get("platforms", {})
    except Exception as e:
        logger.error("获取平台配置失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/platforms", response_model=SuccessResponse)
async def update_platforms(platforms: PassiveConsciousnessPlatformConfig):
    """更新平台配置"""
    try:
        config = PassiveConsciousnessService.get_config()
        config["platforms"] = platforms.model_dump()
        PassiveConsciousnessService.update_config(config)
        return SuccessResponse(message="平台配置已保存")
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


# ============ 状态 ============

@router.get("/status")
async def get_status():
    """获取被动意识状态"""
    try:
        return PassiveConsciousnessService.get_status()
    except Exception as e:
        logger.error("获取状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 日志 ============

@router.get("/chats")
async def get_chats(limit: int = 50):
    """获取最近聊天记录"""
    return PassiveConsciousnessService.get_chats(limit)


# ============ 测试 ============

@router.post("/test/hindsight-recall")
async def test_hindsight_recall():
    """测试 Hindsight Recall"""
    try:
        config = PassiveConsciousnessService.get_config()
        hindsight_config = config.get("hindsight", {})
        if not hindsight_config.get("enabled"):
            return {"success": False, "error": "Hindsight 未启用"}

        from hindsight_client import Hindsight
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        limit = hindsight_config.get("recall_limit", 5)
        timeout = hindsight_config.get("timeout", 120)

        client = Hindsight(base_url=base_url, timeout=timeout)
        response = await client.arecall(bank_id=bank_id, query="最近的对话和情绪", max_tokens=4096)
        results = [{"text": r.text, "type": r.type, "id": r.id} for r in response.results]
        return {
            "success": True,
            "data": {
                "count": len(results),
                "results": results
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/hindsight-reflect")
async def test_hindsight_reflect():
    """测试 Hindsight Reflect"""
    try:
        config = PassiveConsciousnessService.get_config()
        hindsight_config = config.get("hindsight", {})
        if not hindsight_config.get("reflect_enabled"):
            return {"success": False, "error": "Reflect 未启用"}

        from hindsight_client import Hindsight
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        timeout = hindsight_config.get("timeout", 120)

        client = Hindsight(base_url=base_url, timeout=timeout)
        answer = await client.areflect(bank_id=bank_id, query="总结最近的对话和情绪变化", budget="low")
        return {
            "success": True,
            "data": {
                "reflection": answer.text
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ 天气 API ============


def _get_weather_config() -> dict:
    """从 weather.* 命名空间读取天气配置"""
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


def _build_weather_kwargs(weather_config: dict, cache_ttl: int = None) -> dict:
    """将天气配置 dict 转换为 WeatherService.get_weather 所需的关键字参数"""
    kwargs = {
        "amap_key": weather_config.get("amap_key", ""),
        "adcode": weather_config.get("adcode", "370100"),
        "provider": weather_config.get("provider", "qweather"),
        "city": weather_config.get("city", ""),
        "qweather_key": weather_config.get("qweather_key", ""),
        "qweather_geo_url": weather_config.get("qweather_geo_url", "https://geoapi.qweather.com/v2/city/lookup"),
        "qweather_weather_url": weather_config.get("qweather_weather_url", "https://devapi.qweather.com/v7/weather/now"),
    }
    if cache_ttl is not None:
        kwargs["cache_ttl"] = cache_ttl
    else:
        kwargs["cache_ttl"] = int(weather_config.get("cache_hours", 4)) * 3600
    return kwargs


@router.get("/weather")
async def get_weather():
    """获取当前天气（带缓存）"""
    try:
        from services.weather_service import WeatherService

        weather_config = _get_weather_config()

        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}

        service = WeatherService()
        result = await service.get_weather(**_build_weather_kwargs(weather_config))

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


@router.post("/weather/refresh")
async def refresh_weather():
    """强制刷新天气"""
    try:
        from services.weather_service import WeatherService

        weather_config = _get_weather_config()

        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}

        service = WeatherService()

        result = await service.get_weather(**_build_weather_kwargs(weather_config, cache_ttl=0))

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

        weather_config = _get_weather_config()

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


# ============ 被动意识插件测试 ============


# ============ 模板 API ============


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
async def preview_template_endpoint(template_id: str, data: dict = None):
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

# ============ 分析 API ============


@router.get("/analysis/stats")
async def get_analysis_stats(
    hours: int = 24,
    platform: str = None
):
    """获取注入统计"""
    try:
        from services.analysis_service import AnalysisService
        stats = AnalysisService.get_injection_stats(hours, platform)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error("获取注入统计失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/trends")
async def get_analysis_trends(
    hours: int = 24,
    interval: str = "hour"
):
    """获取趋势数据"""
    try:
        from services.analysis_service import AnalysisService
        trends = AnalysisService.get_trend_data(hours, interval)
        return {"success": True, "data": trends}
    except Exception as e:
        logger.error("获取趋势数据失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/sentiment")
async def get_analysis_sentiment(
    hours: int = 24
):
    """获取情感分析"""
    try:
        from services.analysis_service import AnalysisService
        sentiment = AnalysisService.get_sentiment_analysis(hours)
        return {"success": True, "data": sentiment}
    except Exception as e:
        logger.error("获取情感分析失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/weather")
async def test_weather():
    """测试天气 API（支持高德和和风天气）"""
    try:
        from services.weather_service import WeatherService

        weather_config = _get_weather_config()

        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}

        # 使用 WeatherService 获取天气（强制刷新缓存）
        service = WeatherService()
        result = await service.get_weather(**_build_weather_kwargs(weather_config, cache_ttl=0))

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
                }
            }
        else:
            return {"success": False, "error": result.get("error", "未知错误")}
    except Exception as e:
        logger.error("测试天气失败: %s", e)
        return {"success": False, "error": str(e)}


async def _get_qweather_city_id(geo_url: str, api_key: str, city: str) -> str:
    """查询和风天气城市 ID"""
    # 常用城市 ID 映射
    CITY_IDS = {
        "beijing": "101010100", "北京": "101010100",
        "shanghai": "101020100", "上海": "101020100",
        "guangzhou": "101280101", "广州": "101280101",
        "shenzhen": "101280601", "深圳": "101280601",
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

    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "hermes-passive-consciousness/1.0")

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("code") == "200" and data.get("location"):
        return data["location"][0]["id"]

    raise ValueError(f"未找到城市: {city}")


@router.post("/test/longing")
async def test_longing():
    """测试想念分数计算"""
    try:
        now = datetime.now()
        last_user_msg_at = None
        gap_minutes = 0.0
        score = 0.0

        with state_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT MAX(m.timestamp) FROM messages m "
                "JOIN sessions s ON m.session_id = s.id "
                "WHERE m.role = 'user' AND s.source = 'weixin' AND s.ended_at IS NULL"
            )).fetchone()

            if row and row[0]:
                last_user_msg_at = str(row[0])
                try:
                    last_dt = datetime.fromisoformat(str(row[0]))
                except Exception:
                    last_dt = now
                gap_minutes = round((now - last_dt).total_seconds() / 60.0, 2)
                score = round(min(gap_minutes / 300.0, 1.0), 3)

        # 计算等级
        LONGING_LEVELS = [
            (0.0, 0, "calm", "平静"),
            (0.1, 1, "longing", "想念"),
            (0.3, 2, "missing", "思念"),
            (0.5, 3, "yearning", "渴望"),
            (0.7, 4, "anxious", "焦虑"),
        ]
        level = 0
        label = "calm"
        for threshold, lvl, lbl, _ in reversed(LONGING_LEVELS):
            if score >= threshold:
                level = lvl
                label = lbl
                break

        return {
            "success": True,
            "data": {
                "score": score,
                "level": level,
                "label": label,
                "last_user_msg_at": last_user_msg_at,
                "gap_minutes": gap_minutes,
            }
        }
    except Exception as e:
        logger.error("测试想念分数失败: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/test/chat-heat")
async def test_chat_heat():
    """测试聊天热度计算"""
    try:
        recent_count = 0
        recent_msg_at = None

        with state_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT COUNT(*), MAX(m.timestamp) FROM messages m "
                "JOIN sessions s ON m.session_id = s.id "
                "WHERE m.role = 'user' AND s.source = 'weixin' AND s.ended_at IS NULL "
                "AND m.timestamp > datetime('now', '-1 hour')"
            )).fetchone()

            if row:
                recent_count = row[0] or 0
                if row[1]:
                    recent_msg_at = str(row[1])

        heat = round(recent_count / 1.0, 2)

        # 计算等级
        HEAT_LEVELS = [
            (0.0, "cold", "冷清"),
            (0.5, "warm", "温暖"),
            (1.0, "hot", "火热"),
            (3.0, "fire", "沸腾"),
        ]
        label = "cold"
        for threshold, lbl, _ in reversed(HEAT_LEVELS):
            if heat >= threshold:
                label = lbl
                break

        return {
            "success": True,
            "data": {
                "heat": heat,
                "label": label,
                "recent_count": recent_count,
                "recent_msg_at": recent_msg_at,
            }
        }
    except Exception as e:
        logger.error("测试聊天热度失败: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/test/emotional-intensity")
async def test_emotional_intensity():
    """测试情绪值读取"""
    try:
        from services.config_service import ConfigService
        db = ActiveSession()
        try:
            raw_value = ConfigService.get_config(db, "passive_consciousness.current.emotional_intensity")
        finally:
            db.close()

        intensity = 0.0
        label = "工作"
        if raw_value:
            try:
                intensity = round(float(raw_value), 3)
            except ValueError:
                pass

        # 标签
        if intensity < 0.3:
            label = "工作"
        elif intensity < 0.5:
            label = "日常"
        elif intensity < 0.7:
            label = "八卦"
        elif intensity < 0.9:
            label = "情感"
        else:
            label = "深度情感"

        return {
            "success": True,
            "data": {
                "intensity": intensity,
                "label": label,
                "raw_value": raw_value,
            }
        }
    except Exception as e:
        logger.error("测试情绪值失败: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/test/context")
async def test_context():
    """测试完整上下文拼装"""
    steps = []
    errors = []
    context = ""

    try:
        # 步骤 1: 计算想念分数
        try:
            longing_resp = await test_longing()
            longing_ok = longing_resp.get("success", False)
            steps.append({"name": "想念分数", "ok": longing_ok, "data": longing_resp.get("data")})
            if not longing_ok:
                errors.append(f"想念分数: {longing_resp.get('error', '未知错误')}")
        except Exception as e:
            steps.append({"name": "想念分数", "ok": False, "error": str(e)})
            errors.append(f"想念分数: {e}")

        # 步骤 2: 计算聊天热度
        try:
            heat_resp = await test_chat_heat()
            heat_ok = heat_resp.get("success", False)
            steps.append({"name": "聊天热度", "ok": heat_ok, "data": heat_resp.get("data")})
            if not heat_ok:
                errors.append(f"聊天热度: {heat_resp.get('error', '未知错误')}")
        except Exception as e:
            steps.append({"name": "聊天热度", "ok": False, "error": str(e)})
            errors.append(f"聊天热度: {e}")

        # 步骤 3: 读取情绪值
        try:
            emotion_resp = await test_emotional_intensity()
            emotion_ok = emotion_resp.get("success", False)
            steps.append({"name": "情绪值", "ok": emotion_ok, "data": emotion_resp.get("data")})
            if not emotion_ok:
                errors.append(f"情绪值: {emotion_resp.get('error', '未知错误')}")
        except Exception as e:
            steps.append({"name": "情绪值", "ok": False, "error": str(e)})
            errors.append(f"情绪值: {e}")

        # 步骤 4: 获取天气
        try:
            weather_resp = await test_weather()
            weather_ok = weather_resp.get("success", False)
            steps.append({"name": "天气感知", "ok": weather_ok, "data": weather_resp.get("data")})
            if not weather_ok:
                errors.append(f"天气感知: {weather_resp.get('error', '未知错误')}")
        except Exception as e:
            steps.append({"name": "天气感知", "ok": False, "error": str(e)})
            errors.append(f"天气感知: {e}")

        # 步骤 5: Hindsight Recall
        try:
            recall_resp = await test_hindsight_recall()
            recall_ok = recall_resp.get("success", False)
            steps.append({"name": "Hindsight Recall", "ok": recall_ok, "data": recall_resp.get("data")})
            if not recall_ok:
                errors.append(f"Hindsight Recall: {recall_resp.get('error', '未知错误')}")
        except Exception as e:
            steps.append({"name": "Hindsight Recall", "ok": False, "error": str(e)})
            errors.append(f"Hindsight Recall: {e}")

        # 步骤 6: Hindsight Reflect
        try:
            reflect_resp = await test_hindsight_reflect()
            reflect_ok = reflect_resp.get("success", False)
            steps.append({"name": "Hindsight Reflect", "ok": reflect_ok, "data": reflect_resp.get("data")})
            if not reflect_ok:
                errors.append(f"Hindsight Reflect: {reflect_resp.get('error', '未知错误')}")
        except Exception as e:
            steps.append({"name": "Hindsight Reflect", "ok": False, "error": str(e)})
            errors.append(f"Hindsight Reflect: {e}")

        # 步骤 7: 拼装上下文（使用模板渲染 API）
        try:
            from services.template_service import TemplateService

            # 收集数据
            consciousness_data = {
                "longing": steps[0].get("data", {}) if steps[0].get("ok") else {},
                "chat_heat": steps[1].get("data", {}) if steps[1].get("ok") else {},
                "emotional_intensity": steps[2].get("data", {}) if steps[2].get("ok") else {},
            }

            weather_data = steps[3].get("data") if steps[3].get("ok") else None

            recall_data = steps[4].get("data") if steps[4].get("ok") else None
            memories = recall_data.get("results", []) if recall_data else None

            reflection = None
            if steps[5].get("ok"):
                reflection = steps[5].get("data", {}).get("reflection")

            # 构建模板数据
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
                "inject_emotion": True,
                "inject_heat": True,
                "inject_longing": True,
                "inject_memory": True,
            }

            # 使用模板渲染服务
            context = TemplateService.render_active_template(template_data)

            steps.append({"name": "上下文拼装", "ok": True, "data": {"length": len(context)}})
        except Exception as e:
            steps.append({"name": "上下文拼装", "ok": False, "error": str(e)})
            errors.append(f"上下文拼装: {e}")

        return {
            "steps": steps,
            "context": context,
            "errors": errors,
        }

    except Exception as e:
        logger.error("测试上下文拼装失败: %s", e)
        return {
            "steps": steps,
            "context": "",
            "errors": errors + [str(e)],
        }


@router.get("/test/full")
async def test_full():
    """一键全量测试"""
    results = {}

    # 测试想念分数
    try:
        results["longing"] = await test_longing()
    except Exception as e:
        results["longing"] = {"success": False, "error": str(e)}

    # 测试聊天热度
    try:
        results["chat_heat"] = await test_chat_heat()
    except Exception as e:
        results["chat_heat"] = {"success": False, "error": str(e)}

    # 测试情绪值
    try:
        results["emotional_intensity"] = await test_emotional_intensity()
    except Exception as e:
        results["emotional_intensity"] = {"success": False, "error": str(e)}

    # 测试天气
    try:
        results["weather"] = await test_weather()
    except Exception as e:
        results["weather"] = {"success": False, "error": str(e)}

    # 测试 Hindsight Recall
    try:
        results["hindsight_recall"] = await test_hindsight_recall()
    except Exception as e:
        results["hindsight_recall"] = {"success": False, "error": str(e)}

    # 测试 Hindsight Reflect
    try:
        results["hindsight_reflect"] = await test_hindsight_reflect()
    except Exception as e:
        results["hindsight_reflect"] = {"success": False, "error": str(e)}

    # 测试上下文拼装
    try:
        results["context"] = await test_context()
    except Exception as e:
        results["context"] = {"success": False, "error": str(e)}

    # 统计
    total = len(results)
    success_count = sum(
        1 for v in results.values()
        if (isinstance(v, dict) and v.get("success")) or
           (isinstance(v, dict) and "steps" in v)
    )

    return {
        "total": total,
        "success": success_count,
        "failed": total - success_count,
        "results": results,
    }
