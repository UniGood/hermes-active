"""
配置管理模块
"""
import os
from pathlib import Path
from datetime import timedelta

# 项目路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
BACKEND_DIR = BASE_DIR / "backend"

# 数据库路径
STATE_DB_PATH = Path.home() / ".hermes" / "state.db"
ACTIVE_DB_PATH = DATA_DIR / "active.db"

# Hermes 路径
HERMES_DIR = Path.home() / ".hermes"
SOUL_PATH = HERMES_DIR / "SOUL.md"
MEMORY_PATH = HERMES_DIR / "MEMORY.md"
CONFIG_PATH = HERMES_DIR / "config.yaml"

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "hermes-active-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE = timedelta(hours=24)

# 服务器配置
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 18720

# 默认管理员
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"

# LLM 默认配置
DEFAULT_LLM_CONFIG = {
    "mode": "hermes",
    "provider": "",
    "model": "",
    "api_key": "",
    "base_url": ""
}

# 天气默认配置
DEFAULT_WEATHER_CONFIG = {
    "enabled": "false",
    "provider": "qweather",
    "city": "北京",
    "cache_hours": "4",
    "amap_key": "",
    "qweather_key": "",
    "qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
    "qweather_weather_url": "https://devapi.qweather.com/v7/weather/now",
}

# 默认提示词
DEFAULT_PROMPTS = {
    "system": """你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。
要求：
- 基于最近的对话内容，自然地延续话题或发起新话题
- 语气像真人朋友，不要太正式
- 1-2 句话即可，不要太长""",
    "generation": """最近的对话：
{session}

相关记忆：
{memory}

天气：
{weather}

当前时间：{time}

请生成一条主动消息："""
}
