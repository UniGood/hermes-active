# 被动意识插件 — 完整实施方案

## 目标

新建一个 Hermes 插件 `passive-consciousness`，通过 `pre_llm_call` 钩子，在每次用户消息到达时自动注入情绪、热度、记忆、天气等上下文信息，让被动意识真正"活"起来。

同时在 hermes-active 前端为所有可配置功能添加测试按钮，实现完整的可观测闭环。

---

## 一、架构总览

```
用户消息到达
    ↓
hermes gateway → conversation_loop
    ↓
pre_llm_call hook 触发
    ↓
passive-consciousness 插件：
  1. 读 active.db configs 表获取配置
  2. 查 state.db 算想念分数、聊天热度
  3. 读 active.db 获取情绪值（由主动意识心跳写入）
  4. [可选] 调高德 API 获取天气
  5. [可选] 调 Hindsight recall 获取记忆
  6. 拼装上下文字符串
    ↓
返回 {"context": "..."} → 注入到用户消息中
    ↓
LLM 生成回复（带被动意识上下文）
```

---

## 二、文件结构

### 新建文件（Hermes 插件）

```
~/.hermes/plugins/passive-consciousness/
├── plugin.yaml                      # 插件清单
├── __init__.py                      # register(ctx) + pre_llm_call 钩子
├── consciousness_engine.py          # 核心引擎：计算想念/热度/情绪
├── context_builder.py               # 上下文拼装器
├── weather_service.py               # 高德天气 API
├── hindsight_client.py              # Hindsight recall/reflect 客户端
├── config_reader.py                 # 读 active.db configs 表
└── tests/
    └── test_consciousness.py        # 单元测试
```

### 修改文件（hermes-active 后端）

```
backend/
├── routers/passive_consciousness.py         # 新增测试 API 端点
├── services/passive_consciousness_service.py # 新增测试逻辑
```

### 修改文件（hermes-active 前端）

```
frontend/src/
├── views/PassiveConsciousness.vue           # 新增测试按钮 UI
├── api/passive_consciousness.js             # 新增测试 API 调用
```

---

## 三、插件详细设计

### 3.1 plugin.yaml

```yaml
name: passive-consciousness
version: "1.0"
description: "被动意识：用户消息到达时注入情绪/热度/记忆/天气上下文"
provides_hooks:
  - pre_llm_call
```

### 3.2 __init__.py — 插件入口

```python
def register(ctx):
    ctx.register_hook("pre_llm_call", inject_consciousness_context)
```

`inject_consciousness_context` 是核心钩子函数，签名：

```python
def inject_consciousness_context(
    session_id: str,
    platform: str,
    sender_id: str,
    user_message: str,
    conversation_history: list,
    **kwargs
) -> dict | None:
```

返回 `{"context": "拼装好的上下文字符串"}` 或 `None`（跳过注入）。

### 3.3 consciousness_engine.py — 核心引擎

从 `passive_consciousness_service.py` 提取核心计算逻辑，但**不依赖 FastAPI/SQLAlchemy**，用原生 sqlite3 读取。

#### 函数清单

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `compute_longing(db_path)` | state.db 路径 | `{score, level, label, last_user_msg_at}` | 算想念分数 |
| `compute_chat_heat(db_path)` | state.db 路径 | `{heat, label, recent_count}` | 算聊天热度 |
| `get_emotional_intensity(db_path)` | active.db 路径 | `{intensity, label}` | 读情绪值（从 configs 表） |
| `compute_all(db_path_state, db_path_active)` | 两个 db 路径 | 合并上述三项 | 一次性计算所有状态 |

#### 想念分数算法（复用现有逻辑）

```python
def compute_longing(state_db_path: str) -> dict:
    conn = sqlite3.connect(state_db_path)
    # 查最近用户消息时间
    row = conn.execute(
        "SELECT MAX(timestamp) FROM messages WHERE role='user' "
        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
    ).fetchone()
    
    if row and row[0]:
        last_user_dt = datetime.fromisoformat(str(row[0]))
        gap_minutes = (now - last_user_dt).total_seconds() / 60
        score = min(gap_minutes / 300, 1.0)  # 5小时=1.0
    else:
        score = 0.0
    
    # 等级映射
    levels = [(0.0, 0, "calm"), (0.1, 1, "longing"), (0.3, 2, "missing"),
              (0.5, 3, "yearning"), (0.7, 4, "anxious")]
    level, label = 0, "calm"
    for threshold, lv, lb in reversed(levels):
        if score >= threshold:
            level, label = lv, lb
            break
    
    return {"score": round(score, 3), "level": level, "label": label, "last_user_msg_at": str(row[0]) if row and row[0] else None}
```

#### 聊天热度算法

```python
def compute_chat_heat(state_db_path: str) -> dict:
    conn = sqlite3.connect(state_db_path)
    row = conn.execute(
        "SELECT COUNT(*), MAX(timestamp) FROM messages "
        "WHERE role='user' AND timestamp > datetime('now', '-1 hour') "
        "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
    ).fetchone()
    
    recent_count = row[0] or 0
    heat = recent_count / 1.0  # 每小时消息数
    
    levels = [(0.0, "cold"), (0.5, "warm"), (1.0, "hot"), (3.0, "fire")]
    label = "cold"
    for threshold, lb in reversed(levels):
        if heat >= threshold:
            label = lb
            break
    
    return {"heat": round(heat, 2), "label": label, "recent_count": recent_count}
```

#### 情绪值读取

```python
def get_emotional_intensity(active_db_path: str) -> dict:
    conn = sqlite3.connect(active_db_path)
    row = conn.execute(
        "SELECT value FROM configs WHERE key='passive_consciousness.current.emotional_intensity'"
    ).fetchone()
    
    intensity = float(row[0]) if row and row[0] else 0.0
    
    labels = [(0.3, "工作"), (0.5, "日常"), (0.7, "八卦"), (0.9, "情感"), (1.0, "深度情感")]
    label = "工作"
    for threshold, lb in labels:
        if intensity < threshold:
            label = lb
            break
    
    return {"intensity": round(intensity, 3), "label": label}
```

### 3.4 weather_service.py — 高德天气

```python
import json
import time
import urllib.request

# 缓存
_weather_cache = {"data": None, "timestamp": 0}

def get_weather(adcode: str, api_key: str, cache_ttl: int = 600) -> dict | None:
    """调用高德天气 API，带缓存"""
    now = time.time()
    if _weather_cache["data"] and (now - _weather_cache["timestamp"]) < cache_ttl:
        return _weather_cache["data"]
    
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={api_key}&extensions=base"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-passive-consciousness/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        if data.get("status") == "1" and data.get("lives"):
            weather = data["lives"][0]
            result = {
                "city": weather.get("city", ""),
                "weather": weather.get("weather", ""),
                "temperature": weather.get("temperature", ""),
                "winddirection": weather.get("winddirection", ""),
                "windpower": weather.get("windpower", ""),
                "humidity": weather.get("humidity", ""),
                "reporttime": weather.get("reporttime", ""),
            }
            _weather_cache["data"] = result
            _weather_cache["timestamp"] = now
            return result
    except Exception as e:
        logger.warning("高德天气 API 调用失败: %s", e)
    
    return None
```

### 3.5 hindsight_client.py — Hindsight 客户端

```python
import json
import urllib.request

def hindsight_recall(query: str, bank_id: str = "hermes", limit: int = 5, 
                     base_url: str = "http://localhost:8888", timeout: int = 10) -> list[dict]:
    """调用 Hindsight Recall API"""
    url = f"{base_url}/api/v1/recall"
    payload = json.dumps({
        "bank_id": bank_id,
        "query": query,
        "max_results": limit,
        "include_types": ["episodic", "semantic"]
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=payload, 
                                      headers={"Content-Type": "application/json"},
                                      method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        results = []
        for item in data.get("results", []):
            results.append({
                "text": item.get("text", ""),
                "type": item.get("type", ""),
                "score": item.get("score", 0),
            })
        return results
    except Exception as e:
        logger.warning("Hindsight recall 失败: %s", e)
        return []


def hindsight_reflect(query: str, bank_id: str = "hermes",
                      base_url: str = "http://localhost:8888", timeout: int = 30) -> str | None:
    """调用 Hindsight Reflect API"""
    url = f"{base_url}/api/v1/reflect"
    payload = json.dumps({
        "bank_id": bank_id,
        "query": query,
        "budget": "low"
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=payload,
                                      headers={"Content-Type": "application/json"},
                                      method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("text", "")
    except Exception as e:
        logger.warning("Hindsight reflect 失败: %s", e)
        return None
```

### 3.6 config_reader.py — 配置读取

```python
import sqlite3
import json

def read_config(db_path: str, prefix: str = "passive_consciousness.") -> dict:
    """从 active.db configs 表读取被动意识配置，返回嵌套 dict"""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT key, value FROM configs WHERE key LIKE ?", (prefix + "%",)
    ).fetchall()
    conn.close()
    
    flat = {row[0]: row[1] for row in rows}
    return _flat_to_nested(flat, prefix)


def _flat_to_nested(flat: dict, prefix: str) -> dict:
    """扁平 key → 嵌套 dict"""
    result = {}
    for key, value in flat.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix):].split(".")
        d = result
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        # 类型转换
        final_key = parts[-1]
        if value in ("true", "false"):
            d[final_key] = value == "true"
        elif value.startswith("[") or value.startswith("{"):
            try:
                d[final_key] = json.loads(value)
            except json.JSONDecodeError:
                d[final_key] = value
        else:
            try:
                d[final_key] = int(value)
            except ValueError:
                try:
                    d[final_key] = float(value)
                except ValueError:
                    d[final_key] = value
    return result
```

### 3.7 context_builder.py — 上下文拼装

```python
def build_consciousness_context(
    config: dict,
    longing: dict,
    heat: dict,
    emotion: dict,
    weather: dict | None,
    memories: list[dict],
    reflect: str | None,
) -> str:
    """将所有感知数据拼装成注入上下文"""
    parts = []
    
    passive = config.get("passive", {})
    inject_tag = passive.get("inject_tag", "[CONSCIOUSNESS_CONTEXT]")
    
    parts.append(f"--- {inject_tag} ---")
    parts.append("以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：")
    parts.append("")
    
    # 情绪值
    if passive.get("inject_emotion", True):
        parts.append(f"🎭 情绪状态：{emotion['label']}（强度 {emotion['intensity']}）")
    
    # 聊天热度
    if passive.get("inject_heat", True):
        parts.append(f"🔥 聊天热度：{heat['label']}（近1小时 {heat['recent_count']} 条消息）")
    
    # 想念分数
    parts.append(f"💕 想念程度：{longing['label']}（分数 {longing['score']}）")
    
    # 天气
    if weather and config.get("weather", {}).get("enabled", False):
        parts.append(f"🌤 天气：{weather['city']} {weather['weather']} {weather['temperature']}°C 湿度{weather['humidity']}%")
    
    # 记忆
    if passive.get("inject_memory", True) and memories:
        parts.append("")
        parts.append("📖 相关记忆：")
        for i, mem in enumerate(memories[:5], 1):
            parts.append(f"  {i}. {mem['text'][:200]}")
    
    # 反思
    if passive.get("inject_memory", True) and reflect:
        parts.append("")
        parts.append(f"💭 综合反思：{reflect[:300]}")
    
    parts.append(f"--- /{inject_tag} ---")
    
    return "\n".join(parts)
```

### 3.8 __init__.py — 完整钩子逻辑

```python
"""
被动意识 Hermes 插件
在 pre_llm_call 时注入情绪/热度/记忆/天气上下文
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger("hermes.plugins.passive-consciousness")

# 数据库路径
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
STATE_DB = HERMES_HOME / "state.db"
ACTIVE_DB = HERMES_HOME / "hermes-active" / "data" / "active.db"


def inject_consciousness_context(
    session_id: str = "",
    platform: str = "",
    sender_id: str = "",
    user_message: str = "",
    conversation_history: list = None,
    **kwargs
) -> dict | None:
    """pre_llm_call 钩子：注入被动意识上下文"""
    
    # 只处理微信平台
    if platform != "weixin":
        return None
    
    # 检查数据库是否存在
    if not STATE_DB.exists() or not ACTIVE_DB.exists():
        return None
    
    try:
        from config_reader import read_config
        from consciousness_engine import compute_all
        from weather_service import get_weather
        from hindsight_client import hindsight_recall, hindsight_reflect
        from context_builder import build_consciousness_context
    except ImportError as e:
        logger.warning("被动意识插件模块导入失败: %s", e)
        return None
    
    try:
        # 1. 读配置
        config = read_config(str(ACTIVE_DB))
        
        if not config.get("enabled", False):
            return None
        
        # 2. 计算状态
        state = compute_all(str(STATE_DB), str(ACTIVE_DB))
        
        # 3. 天气（可选）
        weather = None
        weather_config = config.get("weather", {})
        if weather_config.get("enabled", False) and weather_config.get("amap_key"):
            weather = get_weather(
                adcode=weather_config.get("adcode", "370100"),
                api_key=weather_config["amap_key"],
                cache_ttl=weather_config.get("cache_ttl", 600)
            )
        
        # 4. Hindsight 记忆（可选）
        memories = []
        reflect_text = None
        hindsight_config = config.get("hindsight", {})
        if hindsight_config.get("enabled", False):
            # 用最近的用户消息作为查询
            query = user_message[:100] if user_message else "最近的对话和情绪"
            memories = hindsight_recall(
                query=query,
                bank_id="hermes",
                limit=hindsight_config.get("recall_limit", 5),
            )
            if hindsight_config.get("reflect_enabled", False):
                reflect_text = hindsight_reflect(
                    query=f"总结最近的对话和情绪变化，用户刚说：{user_message[:50]}",
                    bank_id="hermes",
                )
        
        # 5. 拼装上下文
        context = build_consciousness_context(
            config=config,
            longing=state["longing"],
            heat=state["chat_heat"],
            emotion=state["emotional_intensity"],
            weather=weather,
            memories=memories,
            reflect=reflect_text,
        )
        
        if context:
            logger.info("被动意识注入: longing=%s heat=%s emotion=%s weather=%s memories=%d",
                       state["longing"]["label"], state["chat_heat"]["label"],
                       state["emotional_intensity"]["label"],
                       "yes" if weather else "no", len(memories))
            return {"context": context}
        
    except Exception as e:
        logger.warning("被动意识注入失败: %s", e)
    
    return None


def register(ctx):
    ctx.register_hook("pre_llm_call", inject_consciousness_context)
```

---

## 四、hermes-active 前端测试按钮设计

### 4.1 新增 API 端点

在 `routers/passive_consciousness.py` 新增以下测试端点：

| 方法 | 路径 | 说明 | 对应配置 |
|------|------|------|----------|
| POST | `/api/passive-consciousness/test/weather` | 测试高德天气 API | weather.* |
| POST | `/api/passive-consciousness/test/hindsight-recall` | 测试 Hindsight Recall | hindsight.* |
| POST | `/api/passive-consciousness/test/hindsight-reflect` | 测试 Hindsight Reflect | hindsight.* |
| POST | `/api/passive-consciousness/test/longing` | 测试想念分数计算 | — |
| POST | `/api/passive-consciousness/test/chat-heat` | 测试聊天热度计算 | — |
| POST | `/api/passive-consciousness/test/emotional-intensity` | 测试情绪值读取 | — |
| POST | `/api/passive-consciousness/test/context` | 测试完整上下文拼装 | 所有配置 |
| GET  | `/api/passive-consciousness/test/full` | 一键全量测试 | 所有配置 |

### 4.2 后端实现

#### 测试天气

```python
@router.post("/test/weather")
async def test_weather():
    """测试高德天气 API"""
    config = PassiveConsciousnessService.get_config()
    weather_config = config.get("weather", {})
    
    if not weather_config.get("enabled"):
        return {"success": False, "error": "天气感知未启用"}
    
    api_key = weather_config.get("amap_key", "")
    if not api_key:
        return {"success": False, "error": "未配置高德 API Key"}
    
    adcode = weather_config.get("adcode", "370100")
    cache_ttl = weather_config.get("cache_ttl", 600)
    
    # 直接调用，绕过缓存
    import urllib.request
    import json
    
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={api_key}&extensions=base"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-test/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        if data.get("status") == "1" and data.get("lives"):
            weather = data["lives"][0]
            return {
                "success": True,
                "data": {
                    "city": weather.get("city", ""),
                    "weather": weather.get("weather", ""),
                    "temperature": weather.get("temperature", ""),
                    "humidity": weather.get("humidity", ""),
                    "winddirection": weather.get("winddirection", ""),
                    "reporttime": weather.get("reporttime", ""),
                }
            }
        else:
            return {"success": False, "error": f"API 返回异常: {data.get('info', 'unknown')}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 测试想念分数

```python
@router.post("/test/longing")
async def test_longing():
    """测试想念分数计算"""
    from sqlalchemy import text
    from models.database import state_engine
    
    try:
        with state_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT MAX(timestamp) FROM messages WHERE role='user' AND session_id IN "
                "(SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
            )).fetchone()
            
            if row and row[0]:
                from datetime import datetime
                last_user_dt = datetime.fromisoformat(str(row[0]))
                gap_minutes = (datetime.now() - last_user_dt).total_seconds() / 60
                score = min(gap_minutes / 300, 1.0)
                
                levels = [(0.0, 0, "calm"), (0.1, 1, "longing"), (0.3, 2, "missing"),
                          (0.5, 3, "yearning"), (0.7, 4, "anxious")]
                level, label = 0, "calm"
                for threshold, lv, lb in reversed(levels):
                    if score >= threshold:
                        level, label = lv, lb
                        break
                
                return {
                    "success": True,
                    "data": {
                        "score": round(score, 3),
                        "level": level,
                        "label": label,
                        "last_user_msg_at": str(row[0]),
                        "gap_minutes": round(gap_minutes, 1),
                    }
                }
            else:
                return {"success": True, "data": {"score": 0, "level": 0, "label": "calm", "last_user_msg_at": None}}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 测试聊天热度

```python
@router.post("/test/chat-heat")
async def test_chat_heat():
    """测试聊天热度计算"""
    from sqlalchemy import text
    from models.database import state_engine
    
    try:
        with state_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT COUNT(*), MAX(timestamp) FROM messages "
                "WHERE role='user' AND timestamp > datetime('now', '-1 hour') "
                "AND session_id IN (SELECT id FROM sessions WHERE source='weixin' AND ended_at IS NULL)"
            )).fetchone()
            
            recent_count = row[0] or 0
            heat = recent_count / 1.0
            
            levels = [(0.0, "cold"), (0.5, "warm"), (1.0, "hot"), (3.0, "fire")]
            label = "cold"
            for threshold, lb in reversed(levels):
                if heat >= threshold:
                    label = lb
                    break
            
            return {
                "success": True,
                "data": {
                    "heat": round(heat, 2),
                    "label": label,
                    "recent_count": recent_count,
                    "recent_msg_at": str(row[1]) if row[1] else None,
                }
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 测试情绪值

```python
@router.post("/test/emotional-intensity")
async def test_emotional_intensity():
    """测试情绪值读取"""
    try:
        from services.config_service import ConfigService
        from models.database import ActiveSession
        
        db = ActiveSession()
        try:
            val = ConfigService.get_config(db, "passive_consciousness.current.emotional_intensity")
            intensity = float(val) if val else 0.0
            
            labels = [(0.3, "工作"), (0.5, "日常"), (0.7, "八卦"), (0.9, "情感"), (1.0, "深度情感")]
            label = "工作"
            for threshold, lb in labels:
                if intensity < threshold:
                    label = lb
                    break
            
            return {
                "success": True,
                "data": {
                    "intensity": round(intensity, 3),
                    "label": label,
                    "raw_value": val,
                }
            }
        finally:
            db.close()
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 测试完整上下文拼装

```python
@router.post("/test/context")
async def test_context():
    """测试完整上下文拼装（模拟一次完整的被动意识流程）"""
    result = {"steps": [], "context": None, "errors": []}
    
    # Step 1: 读配置
    try:
        config = PassiveConsciousnessService.get_config()
        result["steps"].append({"name": "读取配置", "status": "ok", "enabled": config.get("enabled", False)})
    except Exception as e:
        result["errors"].append(f"读取配置失败: {e}")
        return result
    
    if not config.get("enabled", False):
        result["errors"].append("被动意识未启用")
        return result
    
    # Step 2: 计算想念
    longing_resp = await test_longing()
    longing = longing_resp.get("data", {"score": 0, "level": 0, "label": "calm"})
    result["steps"].append({"name": "想念分数", "status": "ok" if longing_resp.get("success") else "error", "data": longing})
    
    # Step 3: 计算热度
    heat_resp = await test_chat_heat()
    heat = heat_resp.get("data", {"heat": 0, "label": "cold", "recent_count": 0})
    result["steps"].append({"name": "聊天热度", "status": "ok" if heat_resp.get("success") else "error", "data": heat})
    
    # Step 4: 读情绪
    emotion_resp = await test_emotional_intensity()
    emotion = emotion_resp.get("data", {"intensity": 0, "label": "工作"})
    result["steps"].append({"name": "情绪值", "status": "ok" if emotion_resp.get("success") else "error", "data": emotion})
    
    # Step 5: 天气
    weather = None
    if config.get("weather", {}).get("enabled"):
        weather_resp = await test_weather()
        if weather_resp.get("success"):
            weather = weather_resp["data"]
        result["steps"].append({"name": "天气", "status": "ok" if weather_resp.get("success") else "error", "data": weather or weather_resp.get("error")})
    
    # Step 6: Hindsight
    memories = []
    reflect_text = None
    if config.get("hindsight", {}).get("enabled"):
        recall_resp = await test_hindsight_recall()
        if recall_resp.get("success"):
            memories = recall_resp["data"]["results"]
        result["steps"].append({"name": "Hindsight Recall", "status": "ok" if recall_resp.get("success") else "error", "count": len(memories)})
        
        if config.get("hindsight", {}).get("reflect_enabled"):
            reflect_resp = await test_hindsight_reflect()
            if reflect_resp.get("success"):
                reflect_text = reflect_resp["data"]["reflection"]
            result["steps"].append({"name": "Hindsight Reflect", "status": "ok" if reflect_resp.get("success") else "error"})
    
    # Step 7: 拼装
    try:
        # 动态导入插件的 context_builder
        import sys
        plugin_dir = Path.home() / ".hermes" / "plugins" / "passive-consciousness"
        if str(plugin_dir) not in sys.path:
            sys.path.insert(0, str(plugin_dir))
        from context_builder import build_consciousness_context
        
        context = build_consciousness_context(
            config=config,
            longing=longing,
            heat=heat,
            emotion=emotion,
            weather=weather,
            memories=memories,
            reflect=reflect_text,
        )
        result["context"] = context
        result["steps"].append({"name": "上下文拼装", "status": "ok", "length": len(context)})
    except Exception as e:
        result["errors"].append(f"上下文拼装失败: {e}")
    
    return result
```

#### 一键全量测试

```python
@router.get("/test/full")
async def test_full():
    """一键全量测试，返回所有测试结果"""
    results = {}
    
    results["config"] = await get_config()
    results["longing"] = await test_longing()
    results["chat_heat"] = await test_chat_heat()
    results["emotional_intensity"] = await test_emotional_intensity()
    results["weather"] = await test_weather()
    results["hindsight_recall"] = await test_hindsight_recall()
    results["hindsight_reflect"] = await test_hindsight_reflect()
    results["context"] = await test_context()
    
    return results
```

### 4.3 前端 UI 设计

在 `PassiveConsciousness.vue` 中新增 **测试** Tab：

```vue
<!-- Tab 4: 测试 -->
<n-tab-pane name="test" tab="测试">
  <n-space vertical>
    <!-- 一键全量测试 -->
    <n-button type="primary" @click="runFullTest" :loading="testing.full" block>
      🚀 一键全量测试
    </n-button>
    
    <n-divider>单项测试</n-divider>
    
    <!-- 想念分数 -->
    <n-card title="💕 想念分数" size="small">
      <n-button @click="runTest('longing')" :loading="testing.longing" size="small">
        测试计算
      </n-button>
      <n-descriptions v-if="results.longing" :column="2" size="small" style="margin-top: 8px">
        <n-descriptions-item label="分数">{{ results.longing.data?.score }}</n-descriptions-item>
        <n-descriptions-item label="等级">{{ results.longing.data?.label }}</n-descriptions-item>
        <n-descriptions-item label="差距">{{ results.longing.data?.gap_minutes }} 分钟</n-descriptions-item>
        <n-descriptions-item label="最后消息">{{ results.longing.data?.last_user_msg_at }}</n-descriptions-item>
      </n-descriptions>
    </n-card>
    
    <!-- 聊天热度 -->
    <n-card title="🔥 聊天热度" size="small">
      <n-button @click="runTest('chat-heat')" :loading="testing.chatHeat" size="small">
        测试计算
      </n-button>
      <n-descriptions v-if="results.chatHeat" :column="2" size="small" style="margin-top: 8px">
        <n-descriptions-item label="热度">{{ results.chatHeat.data?.heat }}</n-descriptions-item>
        <n-descriptions-item label="等级">{{ results.chatHeat.data?.label }}</n-descriptions-item>
        <n-descriptions-item label="近1小时">{{ results.chatHeat.data?.recent_count }} 条</n-descriptions-item>
      </n-descriptions>
    </n-card>
    
    <!-- 情绪值 -->
    <n-card title="🎭 情绪值" size="small">
      <n-button @click="runTest('emotional-intensity')" :loading="testing.emotion" size="small">
        测试读取
      </n-button>
      <n-descriptions v-if="results.emotion" :column="2" size="small" style="margin-top: 8px">
        <n-descriptions-item label="强度">{{ results.emotion.data?.intensity }}</n-descriptions-item>
        <n-descriptions-item label="标签">{{ results.emotion.data?.label }}</n-descriptions-item>
        <n-descriptions-item label="原始值">{{ results.emotion.data?.raw_value }}</n-descriptions-item>
      </n-descriptions>
    </n-card>
    
    <!-- 天气 -->
    <n-card title="🌤 天气感知" size="small">
      <n-button @click="runTest('weather')" :loading="testing.weather" size="small">
        测试高德 API
      </n-button>
      <n-descriptions v-if="results.weather" :column="2" size="small" style="margin-top: 8px">
        <n-descriptions-item label="城市">{{ results.weather.data?.city }}</n-descriptions-item>
        <n-descriptions-item label="天气">{{ results.weather.data?.weather }}</n-descriptions-item>
        <n-descriptions-item label="温度">{{ results.weather.data?.temperature }}°C</n-descriptions-item>
        <n-descriptions-item label="湿度">{{ results.weather.data?.humidity }}%</n-descriptions-item>
      </n-descriptions>
      <n-alert v-if="results.weather && !results.weather.success" type="error" style="margin-top: 8px">
        {{ results.weather.error }}
      </n-alert>
    </n-card>
    
    <!-- Hindsight -->
    <n-card title="📖 Hindsight 记忆" size="small">
      <n-space>
        <n-button @click="runTest('hindsight-recall')" :loading="testing.recall" size="small">
          测试 Recall
        </n-button>
        <n-button @click="runTest('hindsight-reflect')" :loading="testing.reflect" size="small">
          测试 Reflect
        </n-button>
      </n-space>
      <div v-if="results.recall" style="margin-top: 8px">
        <n-tag type="info" size="small">Recall 结果: {{ results.recall.data?.count || 0 }} 条</n-tag>
        <n-list v-if="results.recall.data?.results?.length" size="small" style="margin-top: 4px">
          <n-list-item v-for="(r, i) in results.recall.data.results" :key="i">
            <n-text depth="3" style="font-size: 12px">{{ r.text?.substring(0, 100) }}...</n-text>
          </n-list-item>
        </n-list>
      </div>
      <div v-if="results.reflect" style="margin-top: 8px">
        <n-tag type="warning" size="small">Reflect 结果</n-tag>
        <n-text depth="3" style="font-size: 12px; display: block; margin-top: 4px">
          {{ results.reflect.data?.reflection?.substring(0, 300) }}
        </n-text>
      </div>
    </n-card>
    
    <!-- 上下文预览 -->
    <n-card title="📋 完整上下文预览" size="small">
      <n-button type="success" @click="runTest('context')" :loading="testing.context" size="small">
        模拟完整流程
      </n-button>
      <div v-if="results.context" style="margin-top: 8px">
        <n-space v-for="step in results.context.steps" :key="step.name" size="small">
          <n-tag :type="step.status === 'ok' ? 'success' : 'error'" size="small">{{ step.name }}</n-tag>
        </n-space>
        <n-code v-if="results.context.context" :code="results.context.context" language="text" 
                style="margin-top: 8px; max-height: 400px; overflow-y: auto" />
      </div>
    </n-card>
  </n-space>
</n-tab-pane>
```

### 4.4 前端 JS API

在 `api/passive_consciousness.js` 新增：

```javascript
// 测试 API
const testLonging = () => request.post('/api/passive-consciousness/test/longing')
const testChatHeat = () => request.post('/api/passive-consciousness/test/chat-heat')
const testEmotionalIntensity = () => request.post('/api/passive-consciousness/test/emotional-intensity')
const testWeather = () => request.post('/api/passive-consciousness/test/weather')
const testHindsightRecall = () => request.post('/api/passive-consciousness/test/hindsight-recall')
const testHindsightReflect = () => request.post('/api/passive-consciousness/test/hindsight-reflect')
const testContext = () => request.post('/api/passive-consciousness/test/context')
const testFull = () => request.get('/api/passive-consciousness/test/full')
```

---

## 五、开发步骤

### Phase 1：插件骨架（30 分钟）
1. 创建 `~/.hermes/plugins/passive-consciousness/` 目录
2. 编写 `plugin.yaml`
3. 编写 `__init__.py`（register + 空钩子）
4. 重启 hermes gateway 验证插件加载

### Phase 2：核心引擎（45 分钟）
1. 编写 `config_reader.py`
2. 编写 `consciousness_engine.py`（longing + heat + emotion）
3. 编写单元测试验证计算逻辑
4. 手动测试：读 state.db 验证数据正确

### Phase 3：外部服务（30 分钟）
1. 编写 `weather_service.py`
2. 编写 `hindsight_client.py`
3. 手动测试 API 调用

### Phase 4：上下文拼装（20 分钟）
1. 编写 `context_builder.py`
2. 完善 `__init__.py` 钩子逻辑
3. 发一条微信消息验证注入效果

### Phase 5：后端测试 API（30 分钟）
1. 在 `routers/passive_consciousness.py` 新增 8 个测试端点
2. 重启 hermes-active 后端
3. curl 测试每个端点

### Phase 6：前端测试 UI（30 分钟）
1. 在 `PassiveConsciousness.vue` 新增测试 Tab
2. 在 `api/passive_consciousness.js` 新增 API 调用
3. 构建前端、验证 UI

### Phase 7：集成测试（15 分钟）
1. 启用被动意识配置
2. 前端一键全量测试
3. 发微信消息验证完整闭环

---

## 六、配置参数汇总

### 插件配置（configs 表，前缀 `passive_consciousness.`）

| Key | 类型 | 默认值 | 测试按钮 |
|-----|------|--------|----------|
| `enabled` | bool | false | — |
| `llm.mode` | string | hermes | — |
| `passive.enabled` | bool | true | — |
| `passive.inject_emotion` | bool | true | ✅ 情绪值测试 |
| `passive.inject_heat` | bool | true | ✅ 聊天热度测试 |
| `passive.inject_memory` | bool | true | ✅ Hindsight 测试 |
| `passive.inject_thought` | bool | true | — |
| `passive.inject_tag` | string | [CONSCIOUSNESS_CONTEXT] | — |
| `session.sources` | json | ["weixin"] | — |
| `session.time_range_hours` | int | 24 | — |
| `session.max_messages_per_session` | int | 15 | — |
| `hindsight.enabled` | bool | true | ✅ Recall 测试 |
| `hindsight.recall_limit` | int | 5 | ✅ Recall 测试 |
| `hindsight.reflect_enabled` | bool | true | ✅ Reflect 测试 |
| `weather.enabled` | bool | false | ✅ 天气 API 测试 |
| `weather.adcode` | string | 370100 | ✅ 天气 API 测试 |
| `weather.amap_key` | string | "" | ✅ 天气 API 测试 |
| `weather.cache_ttl` | int | 600 | — |

### 测试按钮清单

| 测试按钮 | 调用端点 | 验证内容 |
|----------|----------|----------|
| 💕 测试想念分数 | POST /test/longing | state.db 查询 + 分数计算 |
| 🔥 测试聊天热度 | POST /test/chat-heat | state.db 查询 + 热度计算 |
| 🎭 测试情绪值 | POST /test/emotional-intensity | active.db configs 读取 |
| 🌤 测试天气 | POST /test/weather | 高德 API 调用 |
| 📖 测试 Recall | POST /test/hindsight-recall | Hindsight API 调用 |
| 💭 测试 Reflect | POST /test/hindsight-reflect | Hindsight API 调用 |
| 📋 模拟完整流程 | POST /test/context | 全链路拼装 |
| 🚀 一键全量测试 | GET /test/full | 所有测试一次跑完 |

---

## 七、注意事项

1. **插件用 sqlite3 不用 SQLAlchemy** — hermes 插件不应依赖 hermes-active 的 ORM，直接用标准库 sqlite3
2. **不修改 hermes-agent 源码** — 纯插件机制，通过 `pre_llm_call` 钩子接入
3. **微信平台过滤** — 钩子内检查 `platform == "weixin"`，不影响其他平台
4. **错误静默** — 插件内部所有异常 catch 后 warning 日志，不阻断主流程
5. **缓存天气** — 天气 API 有调用限制，用内存缓存 + TTL
6. **Hindsight 超时** — recall 10s、reflect 30s，超时返回空不阻塞
7. **上下文大小控制** — 记忆最多 5 条，每条最多 200 字；反思最多 300 字
8. **LLM 配置问题** — 设计文档提到被动意识不需要 LLM 配置，但 `llm.mode` 保留兼容，测试按钮不涉及
