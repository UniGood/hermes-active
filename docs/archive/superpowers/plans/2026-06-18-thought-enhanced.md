# 念头增强机制实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现循环增强的念头生成系统，支持多时间范围、天气集成、旧念头去重

**Architecture:** 新增 weather_service.py 和 thought_generator.py，修改 active_consciousness_service.py 集成新逻辑

**Tech Stack:** Python, FastAPI, SQLAlchemy, httpx (高德地图 API)

---

## 文件结构

### 新增文件
- `backend/services/weather_service.py` - 天气服务
- `backend/services/thought_generator.py` - 念头生成器

### 修改文件
- `backend/services/active_consciousness_service.py` - 主服务集成
- `backend/models/active_consciousness.py` - 配置模型
- `frontend/src/views/ActiveConsciousness.vue` - 配置页面

---

## Task 1: 天气服务实现

**Files:**
- Create: `backend/services/weather_service.py`
- Test: `backend/tests/test_weather_service.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_weather_service.py
import pytest
from services.weather_service import WeatherService

def test_weather_service_get_weather():
    """测试获取天气信息"""
    service = WeatherService()
    assert callable(service.get_weather)

def test_weather_service_detect_change():
    """测试天气变化检测"""
    service = WeatherService()
    
    # 天气类型变化
    old = {"current": {"weather": "晴", "temp": 25}}
    new = {"current": {"weather": "阴", "temp": 25}}
    assert service._detect_weather_change(old, new) == "type"
    
    # 温度变化
    old = {"current": {"weather": "晴", "temp": 20}}
    new = {"current": {"weather": "晴", "temp": 26}}
    assert service._detect_weather_change(old, new) == "temp"
    
    # 两者都变化
    old = {"current": {"weather": "晴", "temp": 20}}
    new = {"current": {"weather": "阴", "temp": 26}}
    assert service._detect_weather_change(old, new) == "both"
    
    # 无变化
    old = {"current": {"weather": "晴", "temp": 25}}
    new = {"current": {"weather": "晴", "temp": 25}}
    assert service._detect_weather_change(old, new) is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_weather_service.py -v`
Expected: FAIL with "cannot import name 'WeatherService'"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/weather_service.py

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger("hermes.weather")


class WeatherService:
    """天气服务 - 高德地图 API"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_weather: Optional[Dict] = None
    
    async def get_weather(
        self,
        city: str = "北京",
        cache_ttl: int = 3600,
        temp_threshold: float = 5.0
    ) -> Dict:
        """
        获取天气信息（带缓存）
        
        Returns:
            {
                "current": {"weather": "晴", "temp": 25},
                "future": {"weather": "阴", "temp": 20},
                "city": "北京",
                "weather_changed": bool,
                "change_type": "type" | "temp" | "both" | None
            }
        """
        cache_key = f"weather_{city}"
        
        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < cache_ttl:
                return cached["data"]
        
        # 调用高德地图 API
        weather = await self._fetch_weather_from_amap(city)
        
        # 检查天气变化
        weather["weather_changed"] = False
        weather["change_type"] = None
        
        if self._last_weather:
            change = self._detect_weather_change(
                self._last_weather, weather, temp_threshold
            )
            if change:
                weather["weather_changed"] = True
                weather["change_type"] = change
        
        # 更新缓存和上次天气
        self._cache[cache_key] = {
            "data": weather,
            "timestamp": time.time()
        }
        self._last_weather = weather
        
        return weather
    
    def _detect_weather_change(
        self,
        old_weather: Dict,
        new_weather: Dict,
        temp_threshold: float = 5.0
    ) -> Optional[str]:
        """
        检测天气变化
        
        Returns:
            "type" - 天气类型变化
            "temp" - 温度显著变化
            "both" - 两者都变化
            None - 无显著变化
        """
        type_changed = (
            old_weather.get("current", {}).get("weather") !=
            new_weather.get("current", {}).get("weather")
        )
        
        temp_diff = abs(
            old_weather.get("current", {}).get("temp", 0) -
            new_weather.get("current", {}).get("temp", 0)
        )
        temp_changed = temp_diff >= temp_threshold
        
        if type_changed and temp_changed:
            return "both"
        elif type_changed:
            return "type"
        elif temp_changed:
            return "temp"
        return None
    
    async def _fetch_weather_from_amap(self, city: str) -> Dict:
        """从高德地图 API 获取天气"""
        # TODO: 实现高德地图 API 调用
        # 临时返回模拟数据
        return {
            "current": {"weather": "晴", "temp": 25},
            "future": {"weather": "阴", "temp": 20},
            "city": city
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_weather_service.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/services/weather_service.py backend/tests/test_weather_service.py
git commit -m "feat: add weather service with cache and change detection"
```

---

## Task 2: 念头生成器实现

**Files:**
- Create: `backend/services/thought_generator.py`
- Test: `backend/tests/test_thought_generator.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_thought_generator.py
import pytest
from services.thought_generator import ThoughtGenerator
from models.active_consciousness import EmotionState

def test_thought_generator_select_time_range():
    """测试根据 arousal 选择时间范围"""
    generator = ThoughtGenerator()
    config = {
        "arousal_low_threshold": 0.3,
        "arousal_high_threshold": 0.7
    }
    
    # 低 arousal -> 15 天
    assert generator._select_time_range(0.2, config) == 15
    
    # 中 arousal -> 7 天
    assert generator._select_time_range(0.5, config) == 7
    
    # 高 arousal -> 1 天
    assert generator._select_time_range(0.8, config) == 1

def test_thought_generator_get_count():
    """测试获取念头数量"""
    generator = ThoughtGenerator()
    config = {
        "count_15d": 3,
        "count_7d": 2,
        "count_3d": 2,
        "count_1d": 1
    }
    
    assert generator._get_thought_count(15, config) == 3
    assert generator._get_thought_count(7, config) == 2
    assert generator._get_thought_count(1, config) == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_thought_generator.py -v`
Expected: FAIL with "cannot import name 'ThoughtGenerator'"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/thought_generator.py

import re
import logging
from typing import Dict, List

logger = logging.getLogger("hermes.thought_generator")


class ThoughtGenerator:
    """念头生成器 - 增强版"""
    
    def _select_time_range(self, arousal: float, config: Dict) -> int:
        """根据 arousal 选择时间范围"""
        low_threshold = config.get("arousal_low_threshold", 0.3)
        high_threshold = config.get("arousal_high_threshold", 0.7)
        
        if arousal < low_threshold:
            return 15  # 15 天
        elif arousal < high_threshold:
            return 7   # 7 天
        else:
            return 1   # 1 天
    
    def _get_thought_count(self, time_range: int, config: Dict) -> int:
        """根据时间范围确定生成数量"""
        count_map = {
            15: config.get("count_15d", 3),
            7: config.get("count_7d", 2),
            3: config.get("count_3d", 2),
            1: config.get("count_1d", 1)
        }
        return count_map.get(time_range, 1)
    
    def _build_prompt(
        self,
        time_range: int,
        count: int,
        emotion_state: Dict,
        weather_info: Dict,
        chat_history: List[Dict],
        old_thoughts: List[Dict],
        config: Dict
    ) -> str:
        """构建 prompt"""
        
        # 聊天记录格式化
        chat_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in chat_history[:50]
        ])
        
        # 旧念头格式化
        old_thoughts_text = "\n".join([
            f"{i+1}. {t.get('content', '')}"
            for i, t in enumerate(old_thoughts)
        ])
        
        # 天气信息
        weather_text = ""
        if config.get("weather_enabled") and weather_info.get("weather_changed"):
            change_type = weather_info.get("change_type", "")
            current = weather_info.get("current", {})
            future = weather_info.get("future", {})
            
            weather_text = f"""
【天气变化提醒】
天气刚刚发生了变化（{change_type}）：
- 当前：{current.get('weather', '未知')}，{current.get('temp', '?')}°C
- 未来：{future.get('weather', '未知')}，{future.get('temp', '?')}°C
可以考虑生成天气相关的念头。
"""
        
        prompt = f"""你是凯莉，基于以下信息，生成 {count} 个念头：

【最近 {time_range} 天的聊天记录】
{chat_text}

【你之前的念头（请避免重复）】
{old_thoughts_text}

【当前情绪状态】
valence={emotion_state.get('valence', 0.5):.2f}, arousal={emotion_state.get('arousal', 0.5):.2f}, dominant={emotion_state.get('dominant', 'calm')}
{weather_text}
请生成 {count} 个念头，每个念头用 <thought> 标签包裹。
注意：请避免与之前的念头重复。"""

        return prompt
    
    def _parse_thoughts(self, response: str) -> List[Dict]:
        """解析 LLM 返回的念头"""
        thoughts = []
        pattern = r'<thought>(.*?)</thought>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            thoughts.append({
                "content": match.strip(),
                "type": "association",
                "score": 0.5
            })
        
        return thoughts
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_thought_generator.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/services/thought_generator.py backend/tests/test_thought_generator.py
git commit -m "feat: add thought generator with time range selection"
```

---

## Task 3: 配置模型扩展

**Files:**
- Modify: `backend/models/active_consciousness.py`
- Modify: `backend/services/active_consciousness_service.py`

- [ ] **Step 1: 添加配置模型**

```python
# backend/models/active_consciousness.py

class ActiveConsciousnessThoughtEnhancedConfig(BaseModel):
    """增强念头生成配置"""
    enabled: bool = True
    
    # 时间范围配置
    arousal_low_threshold: float = 0.3
    arousal_high_threshold: float = 0.7
    count_15d: int = 3
    count_7d: int = 2
    count_3d: int = 2
    count_1d: int = 1
    
    # LLM 配置
    temperature: float = 0.9
    max_tokens: int = 500
    
    # 天气配置
    weather_enabled: bool = True
    weather_cache_ttl: int = 3600
    weather_trigger_enabled: bool = True
    weather_type_change_trigger: bool = True
    weather_temp_change_threshold: float = 5.0
    
    # 旧念头召回配置
    recall_old_thoughts_limit: int = 10
    
    # 存储配置
    retain_threshold: float = 0.5
    retain_on_weather: bool = True
```

- [ ] **Step 2: 添加默认配置**

```python
# backend/services/active_consciousness_service.py

_DEFAULTS = {
    # ... 现有配置 ...
    
    # 增强念头生成配置
    "active_consciousness.thought_enhanced.enabled": "true",
    "active_consciousness.thought_enhanced.arousal_low_threshold": "0.3",
    "active_consciousness.thought_enhanced.arousal_high_threshold": "0.7",
    "active_consciousness.thought_enhanced.count_15d": "3",
    "active_consciousness.thought_enhanced.count_7d": "2",
    "active_consciousness.thought_enhanced.count_3d": "2",
    "active_consciousness.thought_enhanced.count_1d": "1",
    "active_consciousness.thought_enhanced.temperature": "0.9",
    "active_consciousness.thought_enhanced.max_tokens": "500",
    "active_consciousness.thought_enhanced.weather_enabled": "true",
    "active_consciousness.thought_enhanced.weather_cache_ttl": "3600",
    "active_consciousness.thought_enhanced.weather_trigger_enabled": "true",
    "active_consciousness.thought_enhanced.weather_type_change_trigger": "true",
    "active_consciousness.thought_enhanced.weather_temp_change_threshold": "5.0",
    "active_consciousness.thought_enhanced.recall_old_thoughts_limit": "10",
    "active_consciousness.thought_enhanced.retain_threshold": "0.5",
    "active_consciousness.thought_enhanced.retain_on_weather": "true",
}
```

- [ ] **Step 3: 添加验证逻辑**

```python
# backend/services/active_consciousness_service.py

def validate_active_consciousness_config(config: Dict[str, Any]) -> List[str]:
    errors = []
    
    # ... 现有验证 ...
    
    # 增强念头生成配置验证
    thought_enhanced = config.get("thought_enhanced", {})
    
    # arousal 阈值
    low_threshold = thought_enhanced.get("arousal_low_threshold", 0.3)
    high_threshold = thought_enhanced.get("arousal_high_threshold", 0.7)
    if low_threshold >= high_threshold:
        errors.append("低唤醒度阈值必须小于高唤醒度阈值")
    
    # 念头数量
    for key in ["count_15d", "count_7d", "count_3d", "count_1d"]:
        count = thought_enhanced.get(key, 1)
        if count < 1 or count > 5:
            errors.append(f"{key} 必须在 1-5 之间")
    
    # temperature
    temp = thought_enhanced.get("temperature", 0.9)
    if temp < 0 or temp > 2:
        errors.append("temperature 必须在 0-2 之间")
    
    return errors
```

- [ ] **Step 4: 提交**

```bash
git add backend/models/active_consciousness.py backend/services/active_consciousness_service.py
git commit -m "feat: add thought enhanced config model and validation"
```

---

## Task 4: 心跳集成

**Files:**
- Modify: `backend/services/active_consciousness_service.py`

- [ ] **Step 1: 修改 run_heartbeat 函数**

```python
# backend/services/active_consciousness_service.py

async def run_heartbeat():
    """执行心跳"""
    # ... 现有代码 ...
    
    # 5. 获取上下文（增强版）
    thought_enhanced_config = config.get("thought_enhanced", {})
    
    if thought_enhanced_config.get("enabled", False):
        # 使用增强念头生成
        from services.weather_service import WeatherService
        from services.thought_generator import ThoughtGenerator
        
        weather_service = WeatherService()
        thought_generator = ThoughtGenerator()
        
        # 获取天气
        weather_info = await weather_service.get_weather(
            cache_ttl=int(thought_enhanced_config.get("weather_cache_ttl", 3600)),
            temp_threshold=float(thought_enhanced_config.get("weather_temp_change_threshold", 5.0))
        )
        
        # 根据 arousal 选择时间范围
        time_range = thought_generator._select_time_range(
            merged_state.arousal,
            thought_enhanced_config
        )
        
        # 读取聊天记录
        chat_history = await get_chat_history_from_messages(
            days=time_range,
            platforms=session_config.get("sources", ["weixin"]),
            limit=int(session_config.get("max_messages_per_session", 15))
        )
        
        # 召回旧念头
        old_thoughts = await recall_from_hindsight(
            query="最近的想法",
            limit=int(thought_enhanced_config.get("recall_old_thoughts_limit", 10)),
            bank_id=store_config.get("bank_id", "hermes-active"),
            base_url=store_config.get("base_url", "http://localhost:8888"),
            timeout=float(store_config.get("timeout", 30))
        )
        
        # 生成念头
        thoughts = await thought_generator.generate_thoughts(
            config=thought_enhanced_config,
            emotion_state=merged_state.to_dict(),
            weather_info=weather_info,
            chat_history=chat_history,
            old_thoughts=old_thoughts
        )
        
        # 存储念头
        for thought in thoughts:
            # 存入 active.db
            write_thought_log(thought)
            
            # 检查是否存入 Hindsight
            if should_retain_to_hindsight(thought, thought_enhanced_config):
                await retain_thought_to_hindsight(thought)
    
    # ... 继续现有代码 ...
```

- [ ] **Step 2: 添加 get_chat_history_from_messages 函数**

```python
# backend/services/active_consciousness_service.py

async def get_chat_history_from_messages(
    days: int,
    platforms: List[str],
    limit: int = 50
) -> List[Dict]:
    """从 message 表读取聊天记录"""
    try:
        with active_engine.connect() as conn:
            # 计算时间范围
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 查询消息
            result = conn.execute(text("""
                SELECT m.role, m.content, m.created_at, s.platform
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.created_at > :cutoff
                AND s.platform IN :platforms
                AND m.role != 'tool'
                ORDER BY m.created_at DESC
                LIMIT :limit
            """), {
                "cutoff": cutoff_date,
                "platforms": tuple(platforms),
                "limit": limit
            })
            
            messages = []
            for row in result:
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "created_at": row[2],
                    "platform": row[3]
                })
            
            return messages
    except Exception as e:
        logger.error("读取聊天记录失败: %s", e)
        return []
```

- [ ] **Step 3: 提交**

```bash
git add backend/services/active_consciousness_service.py
git commit -m "feat: integrate thought enhanced into heartbeat"
```

---

## Task 5: 前端配置页面

**Files:**
- Modify: `frontend/src/views/ActiveConsciousness.vue`

- [ ] **Step 1: 添加配置区域**

在配置面板中添加增强念头生成配置区域：

```vue
<!-- ActiveConsciousness.vue -->

<n-divider>🧠 增强念头生成</n-divider>

<n-form-item label="启用增强念头生成">
  <n-switch v-model:value="config.thought_enhanced.enabled" />
</n-form-item>

<template v-if="config.thought_enhanced.enabled">
  <!-- 时间范围配置 -->
  <n-divider>时间范围配置</n-divider>
  
  <n-form-item label="低唤醒度阈值（使用 15 天）">
    <n-input-number 
      v-model:value="config.thought_enhanced.arousal_low_threshold" 
      :min="0" :max="1" :step="0.1" 
    />
  </n-form-item>
  
  <n-form-item label="高唤醒度阈值（使用 1 天）">
    <n-input-number 
      v-model:value="config.thought_enhanced.arousal_high_threshold" 
      :min="0" :max="1" :step="0.1" 
    />
  </n-form-item>
  
  <!-- ... 其他配置 ... -->
</template>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat: add thought enhanced config UI"
```

---

## 验收标准

- [ ] 天气服务能获取天气信息并检测变化
- [ ] 念头生成器能根据 arousal 选择时间范围
- [ ] 念头生成器能生成指定数量的念头
- [ ] 配置模型包含所有增强念头生成参数
- [ ] 心跳流程集成增强念头生成逻辑
- [ ] 前端配置页面展示所有参数
- [ ] 所有测试通过

---

**最后更新**：2026-06-18
**版本**：v1.0
