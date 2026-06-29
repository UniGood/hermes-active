# 主动意识念头增强机制设计

> v0.2.1 版本 - 循环增强的念头生成系统

---

## 一、核心概念

### 1.1 循环增强逻辑

```
旧念头 + 聊天记录 + 天气信息 → 新念头 → 存入 Hindsight → 下次心跳召回 → 循环
```

### 1.2 设计目标

1. **多维度思考**：不同时间范围产生不同视角的念头
2. **循环增强**：新旧念头混合思考，产生更深入的理解
3. **避免重复**：召回旧念头，prompt 指令避免重复
4. **环境感知**：天气变化触发相关念头
5. **参数可调**：所有参数可配置，方便调整

---

## 二、架构设计

### 2.1 整体流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        心跳触发                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. 读取当前情绪状态                                               │
│    - arousal: 0.4                                                │
│    - valence: 0.6                                                │
│    - social_need: 0.5                                            │
│    - dominant: "longing"                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 根据 arousal 选择时间范围                                      │
│    arousal=0.4 → 7 天                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 获取天气信息（内存缓存）                                        │
│    - 当前：晴，25°C，北京                                         │
│    - 未来：明天阴，20°C                                           │
│    - 检查天气是否变化：                                           │
│      · 上次缓存：阴，22°C                                        │
│      · 变化检测：类型变化（阴→晴）✓                               │
│      · 温度变化：3°C（未达到 5°C 阈值）                           │
│      · 结论：天气变化，需要在 prompt 中强调                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 读取聊天记录（最近 7 天）                                       │
│    - 从 message 表查询                                           │
│    - 过滤 tool 消息                                              │
│    - 按时间排序                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. 从 Hindsight 召回旧念头（最近 10 条）                           │
│    - 从 hermes-active Bank 召回                                 │
│    - 用于 prompt 去重指令                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. LLM 深度思考                                                  │
│                                                                 │
│    Prompt:                                                      │
│    "你是凯莉，基于以下信息，生成 2 个念头：                        │
│                                                                 │
│     【最近 7 天的聊天记录】                                       │
│     {chat_history}                                              │
│                                                                 │
│     【你之前的念头（请避免重复）】                                 │
│     1. 最近有点想聊天                                            │
│     2. 用户上周提到喜欢咖啡                                      │
│     3. 今天天气不错                                              │
│     ...（共 10 条）                                              │
│                                                                 │
│     【当前情绪状态】                                              │
│     valence=0.6, arousal=0.4, dominant=longing                  │
│                                                                 │
│     【天气变化提醒】                                              │
│     天气刚刚从阴天转晴，温度从 22°C 升到 25°C                      │
│     可以考虑生成天气相关的念头                                    │
│                                                                 │
│     【未来天气】                                                  │
│     明天阴天，20°C                                                │
│                                                                 │
│     请生成 2 个念头，每个念头用 <thought> 标签包裹。              │
│     注意：请避免与之前的念头重复。"                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 解析
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        生成的念头                                 │
│                                                                 │
│  1. "天气转晴了，心情也变好了" (emotion)                          │
│  2. "明天阴天，提醒他带伞" (environment)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 分层存储
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  active.db                    │    Hindsight                    │
│  (所有念头)                   │    (重要念头)                    │
│                               │                                 │
│  - 念头日志                   │    - hermes-active Bank         │
│  - 情绪快照                   │    - 可被召回                    │
│  - 决策结果                   │    - 用于下次思考                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、配置参数

### 3.1 配置结构

```python
class ActiveConsciousnessThoughtEnhancedConfig(BaseModel):
    """增强念头生成配置"""
    
    # ============ 时间范围配置 ============
    
    # arousal 阈值
    arousal_low_threshold: float = 0.3      # 低于此值使用 15 天
    arousal_high_threshold: float = 0.7     # 高于此值使用 1 天
    
    # 时间范围对应的念头数量
    count_15d: int = 3                      # 15 天生成 3 个念头
    count_7d: int = 2                       # 7 天生成 2 个念头
    count_3d: int = 2                       # 3 天生成 2 个念头
    count_1d: int = 1                       # 1 天生成 1 个念头
    
    # ============ LLM 配置 ============
    
    temperature: float = 0.9                # 温度（越高越随机）
    max_tokens: int = 500                   # 最大 token 数
    
    # ============ 天气配置 ============
    
    weather_enabled: bool = True            # 是否启用天气
    weather_cache_ttl: int = 3600           # 天气缓存时间（秒）
    weather_trigger_enabled: bool = True    # 是否启用天气触发念头
    weather_type_change_trigger: bool = True  # 天气类型变化触发
    weather_temp_change_threshold: float = 5.0  # 温度变化阈值（°C）
    
    # ============ 旧念头召回配置 ============
    
    recall_old_thoughts_limit: int = 10     # 召回旧念头数量
    
    # ============ 存储配置 ============
    
    retain_threshold: float = 0.5           # 存入 Hindsight 的阈值
    retain_on_weather: bool = True          # 天气相关念头是否存入 Hindsight
```

### 3.2 配置默认值

```python
_DEFAULTS = {
    # 增强念头生成配置
    "active_consciousness.thought_enhanced.enabled": "true",
    
    # 时间范围配置
    "active_consciousness.thought_enhanced.arousal_low_threshold": "0.3",
    "active_consciousness.thought_enhanced.arousal_high_threshold": "0.7",
    "active_consciousness.thought_enhanced.count_15d": "3",
    "active_consciousness.thought_enhanced.count_7d": "2",
    "active_consciousness.thought_enhanced.count_3d": "2",
    "active_consciousness.thought_enhanced.count_1d": "1",
    
    # LLM 配置
    "active_consciousness.thought_enhanced.temperature": "0.9",
    "active_consciousness.thought_enhanced.max_tokens": "500",
    
    # 天气配置
    "active_consciousness.thought_enhanced.weather_enabled": "true",
    "active_consciousness.thought_enhanced.weather_cache_ttl": "3600",
    "active_consciousness.thought_enhanced.weather_trigger_enabled": "true",
    "active_consciousness.thought_enhanced.weather_type_change_trigger": "true",
    "active_consciousness.thought_enhanced.weather_temp_change_threshold": "5.0",
    
    # 旧念头召回配置
    "active_consciousness.thought_enhanced.recall_old_thoughts_limit": "10",
    
    # 存储配置
    "active_consciousness.thought_enhanced.retain_threshold": "0.5",
    "active_consciousness.thought_enhanced.retain_on_weather": "true",
}
```

---

## 四、代码结构

### 4.1 新增文件

```
backend/services/
├── active_consciousness_service.py     # 主服务（修改）
├── weather_service.py                  # 天气服务（新增）
└── thought_generator.py                # 念头生成器（新增）
```

### 4.2 天气服务

```python
# backend/services/weather_service.py

import time
import logging
from typing import Dict, Optional
import httpx

logger = logging.getLogger("hermes.weather")


class WeatherService:
    """天气服务 - 高德地图 API"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_weather: Optional[Dict] = None
    
    async def get_weather(
        self,
        city: str = "北京",
        cache_ttl: int = 3600
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
            change = self._detect_weather_change(self._last_weather, weather)
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

### 4.3 念头生成器

```python
# backend/services/thought_generator.py

import logging
from typing import Dict, List, Optional
from models.active_consciousness import EmotionState

logger = logging.getLogger("hermes.thought_generator")


class ThoughtGenerator:
    """念头生成器 - 增强版"""
    
    async def generate_thoughts(
        self,
        config: Dict,
        emotion_state: EmotionState,
        weather_info: Dict,
        chat_history: List[Dict],
        old_thoughts: List[Dict]
    ) -> List[Dict]:
        """
        生成念头
        
        Args:
            config: 增强念头生成配置
            emotion_state: 当前情绪状态
            weather_info: 天气信息
            chat_history: 聊天记录
            old_thoughts: 旧念头（用于去重）
        
        Returns:
            [{"content": "...", "type": "...", "score": 0.7}, ...]
        """
        # 1. 根据 arousal 选择时间范围
        time_range = self._select_time_range(
            emotion_state.arousal,
            config
        )
        
        # 2. 确定生成数量
        count = self._get_thought_count(time_range, config)
        
        # 3. 构建 prompt
        prompt = self._build_prompt(
            time_range=time_range,
            count=count,
            emotion_state=emotion_state,
            weather_info=weather_info,
            chat_history=chat_history,
            old_thoughts=old_thoughts,
            config=config
        )
        
        # 4. 调用 LLM
        response = await self._call_llm(prompt, config)
        
        # 5. 解析念头
        thoughts = self._parse_thoughts(response)
        
        return thoughts
    
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
        emotion_state: EmotionState,
        weather_info: Dict,
        chat_history: List[Dict],
        old_thoughts: List[Dict],
        config: Dict
    ) -> str:
        """构建 prompt"""
        
        # 聊天记录格式化
        chat_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in chat_history[:50]  # 限制长度
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
valence={emotion_state.valence:.2f}, arousal={emotion_state.arousal:.2f}, dominant={emotion_state.dominant}
{weather_text}
请生成 {count} 个念头，每个念头用 <thought> 标签包裹。
注意：请避免与之前的念头重复。"""

        return prompt
    
    def _parse_thoughts(self, response: str) -> List[Dict]:
        """解析 LLM 返回的念头"""
        import re
        
        thoughts = []
        pattern = r'<thought>(.*?)</thought>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            thoughts.append({
                "content": match.strip(),
                "type": "association",  # 默认类型
                "score": 0.5
            })
        
        return thoughts
```

---

## 五、前端配置页面

### 5.1 配置面板新增区域

```vue
<!-- ActiveConsciousness.vue 配置面板新增 -->

<n-divider>🧠 增强念头生成</n-divider>

<!-- 总开关 -->
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
  
  <n-form-item label="15 天生成念头数">
    <n-input-number 
      v-model:value="config.thought_enhanced.count_15d" 
      :min="1" :max="5" 
    />
  </n-form-item>
  
  <n-form-item label="7 天生成念头数">
    <n-input-number 
      v-model:value="config.thought_enhanced.count_7d" 
      :min="1" :max="5" 
    />
  </n-form-item>
  
  <n-form-item label="3 天生成念头数">
    <n-input-number 
      v-model:value="config.thought_enhanced.count_3d" 
      :min="1" :max="5" 
    />
  </n-form-item>
  
  <n-form-item label="1 天生成念头数">
    <n-input-number 
      v-model:value="config.thought_enhanced.count_1d" 
      :min="1" :max="5" 
    />
  </n-form-item>
  
  <!-- LLM 配置 -->
  <n-divider>LLM 思考配置</n-divider>
  
  <n-form-item label="Temperature（随机性）">
    <n-input-number 
      v-model:value="config.thought_enhanced.temperature" 
      :min="0" :max="2" :step="0.1" 
    />
  </n-form-item>
  
  <n-form-item label="最大 Token 数">
    <n-input-number 
      v-model:value="config.thought_enhanced.max_tokens" 
      :min="100" :max="2000" :step="100" 
    />
  </n-form-item>
  
  <!-- 天气配置 -->
  <n-divider>天气配置</n-divider>
  
  <n-form-item label="启用天气">
    <n-switch v-model:value="config.thought_enhanced.weather_enabled" />
  </n-form-item>
  
  <template v-if="config.thought_enhanced.weather_enabled">
    <n-form-item label="天气缓存时间（秒）">
      <n-input-number 
        v-model:value="config.thought_enhanced.weather_cache_ttl" 
        :min="60" :max="86400" :step="60" 
      />
    </n-form-item>
    
    <n-form-item label="启用天气触发念头">
      <n-switch v-model:value="config.thought_enhanced.weather_trigger_enabled" />
    </n-form-item>
    
    <template v-if="config.thought_enhanced.weather_trigger_enabled">
      <n-form-item label="天气类型变化触发">
        <n-switch v-model:value="config.thought_enhanced.weather_type_change_trigger" />
      </n-form-item>
      
      <n-form-item label="温度变化阈值（°C）">
        <n-input-number 
          v-model:value="config.thought_enhanced.weather_temp_change_threshold" 
          :min="1" :max="20" :step="1" 
        />
      </n-form-item>
    </template>
  </template>
  
  <!-- 旧念头召回配置 -->
  <n-divider>旧念头召回配置</n-divider>
  
  <n-form-item label="召回旧念头数量">
    <n-input-number 
      v-model:value="config.thought_enhanced.recall_old_thoughts_limit" 
      :min="1" :max="50" :step="1" 
    />
  </n-form-item>
  
  <!-- 存储配置 -->
  <n-divider>存储配置</n-divider>
  
  <n-form-item label="存入 Hindsight 阈值">
    <n-input-number 
      v-model:value="config.thought_enhanced.retain_threshold" 
      :min="0" :max="1" :step="0.1" 
    />
  </n-form-item>
  
  <n-form-item label="天气念头存入 Hindsight">
    <n-switch v-model:value="config.thought_enhanced.retain_on_weather" />
  </n-form-item>
</template>
```

---

## 六、验收标准

1. **时间范围选择**：根据 arousal 正确选择 15天/7天/3天/1天
2. **聊天记录读取**：从 message 表正确读取指定时间范围的记录
3. **天气集成**：高德地图 API 正确返回天气信息，缓存生效
4. **天气变化检测**：正确检测天气类型变化和温度变化
5. **念头生成**：LLM 正确生成指定数量的念头
6. **去重机制**：召回旧念头，prompt 指令避免重复
7. **分层存储**：所有念头存 active.db，重要念头存 Hindsight
8. **循环增强**：下次心跳能召回之前的念头，与新记录混合思考
9. **配置化**：所有参数可配置，前端页面可调整

---

**最后更新**：2026-06-18
**版本**：v1.0
