"""
被动意识数据模型 - 用户消息时注入上下文
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ============ 配置相关 ============

class PassiveConsciousnessLLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "openai"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = ""


class PassiveConsciousnessPassiveConfig(BaseModel):
    """被动意识注入配置"""
    enabled: bool = True
    inject_emotion: bool = True
    inject_heat: bool = True
    inject_memory: bool = True
    inject_thought: bool = True
    thought_max_chars: int = 200
    vibe_max_chars: int = 50
    inject_tag: str = "[CONSCIOUSNESS_CONTEXT]"
    time_format: str = "%H:%M"


class PassiveConsciousnessSessionConfig(BaseModel):
    """Session 来源配置"""
    sources: List[str] = ["weixin"]
    time_range_hours: int = 24
    max_messages_per_session: int = 15
    filter_tool_messages: bool = True


class PassiveConsciousnessHindsightConfig(BaseModel):
    """Hindsight 记忆配置"""
    enabled: bool = True
    recall_limit: int = 5
    reflect_enabled: bool = True


class PassiveConsciousnessWeatherConfig(BaseModel):
    """天气感知配置"""
    enabled: bool = False
    adcode: str = "370100"
    amap_key: str = ""
    cache_ttl: int = 600


class PassiveConsciousnessConfig(BaseModel):
    """被动意识完整配置"""
    enabled: bool = False
    llm: PassiveConsciousnessLLMConfig = PassiveConsciousnessLLMConfig()
    passive: PassiveConsciousnessPassiveConfig = PassiveConsciousnessPassiveConfig()
    session: PassiveConsciousnessSessionConfig = PassiveConsciousnessSessionConfig()
    hindsight: PassiveConsciousnessHindsightConfig = PassiveConsciousnessHindsightConfig()
    weather: PassiveConsciousnessWeatherConfig = PassiveConsciousnessWeatherConfig()


# ============ 状态相关 ============

class LongingState(BaseModel):
    """想念状态"""
    score: float = 0.0
    level: int = 0
    label: str = "calm"
    last_user_msg_at: Optional[str] = None
    last_self_msg_at: Optional[str] = None


class ChatHeat(BaseModel):
    """聊天热度"""
    heat: float = 0.0
    label: str = "cold"
    recent_count: int = 0
    recent_hours: float = 0.0
    recent_user_msg_at: Optional[str] = None


class EmotionalIntensity(BaseModel):
    """情绪强度"""
    intensity: float = 0.0
    label: str = "工作"


class PassiveConsciousnessStatus(BaseModel):
    """被动意识状态"""
    enabled: bool = False
    longing: LongingState = LongingState()
    chat_heat: ChatHeat = ChatHeat()
    emotional_intensity: EmotionalIntensity = EmotionalIntensity()


# ============ 日志相关 ============

class ChatRecord(BaseModel):
    """聊天记录"""
    id: int
    session_id: str
    source: str
    role: str
    content: str
    send_mark: Optional[str] = None
    timestamp: Optional[str] = None


# ============ 测试相关 ============

class TestResult(BaseModel):
    """测试结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


# ============ API 响应 ============

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str = "操作成功"


# ============ 天气数据 ============

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
    forecast: List[ForecastDay] = field(default_factory=list)

    # 元数据
    updated_at: Optional[datetime] = None  # 数据更新时间
    provider: str = ""           # 数据来源（amap/qweather）
    raw_data: dict = field(default_factory=dict)  # 原始 API 响应（调试用）
