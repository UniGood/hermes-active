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
    PassiveConsciousnessConfig, PassiveConsciousnessStatus,
    SuccessResponse, ChatRecord, TestResult
)
from models.database import ActiveSession, state_engine
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


# ============ 被动意识插件测试 ============

@router.post("/test/weather")
async def test_weather():
    """测试高德天气 API（直接调用，不依赖插件）"""
    try:
        config = PassiveConsciousnessService.get_config()
        weather_config = config.get("weather", {})

        if not weather_config.get("enabled"):
            return {"success": False, "error": "天气感知未启用"}

        api_key = weather_config.get("amap_key", "")
        if not api_key:
            return {"success": False, "error": "高德 API Key 未配置"}

        adcode = weather_config.get("adcode", "370100")

        # 直接调用高德 API，绕过缓存
        params = urllib.parse.urlencode({
            "city": adcode,
            "key": api_key,
            "extensions": "base",
        })
        url = f"https://restapi.amap.com/v3/weather/weatherInfo?{params}"

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "hermes-passive-consciousness/1.0")

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") != "1":
            return {"success": False, "error": f"高德 API 返回错误: {data.get('info', '未知')}"}

        lives = data.get("lives", [])
        if not lives:
            return {"success": False, "error": "高德 API 返回空数据"}

        live = lives[0]
        return {
            "success": True,
            "data": {
                "city": live.get("city", ""),
                "weather": live.get("weather", ""),
                "temperature": live.get("temperature", ""),
                "humidity": live.get("humidity", ""),
                "winddirection": live.get("winddirection", ""),
                "reporttime": live.get("reporttime", ""),
            }
        }
    except Exception as e:
        logger.error("测试天气失败: %s", e)
        return {"success": False, "error": str(e)}


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

        # 步骤 7: 拼装上下文
        try:
            # 动态导入插件的 context_builder
            if str(PLUGIN_DIR) not in sys.path:
                sys.path.insert(0, str(PLUGIN_DIR.parent))

            from passive_consciousness.context_builder import build_context

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

            context = build_context(
                consciousness_data=consciousness_data,
                weather_data=weather_data,
                memories=memories,
                reflection=reflection,
            )

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
