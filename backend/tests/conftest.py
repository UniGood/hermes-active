"""
测试配置和共享 fixtures
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    return session


@pytest.fixture
def mock_config():
    """模拟配置数据"""
    return {
        "enabled": True,
        "platforms": {
            "enabled": True,
            "whitelist": ["weixin", "feishu"]
        },
        "passive": {
            "enabled": True,
            "inject_emotion": True,
            "inject_heat": True,
            "inject_memory": True,
            "inject_thought": True,
            "thought_max_chars": 200,
            "vibe_max_chars": 50,
            "inject_tag": "[CONSCIOUSNESS_CONTEXT]",
            "time_format": "%H:%M"
        },
        "session": {
            "sources": ["weixin"],
            "time_range_hours": 24,
            "max_messages_per_session": 15,
            "filter_tool_messages": True
        },
        "hindsight": {
            "enabled": True,
            "recall_limit": 5,
            "reflect_enabled": True
        },
        "weather": {
            "enabled": False,
            "provider": "qweather",
            "city": "北京",
            "cache_hours": 4,
            "amap_key": "",
            "qweather_key": "",
            "qweather_geo_url": "https://geoapi.qweather.com/v2/city/lookup",
            "qweather_weather_url": "https://devapi.qweather.com/v7/weather/now"
        },
        "templates": {
            "list": [
                {
                    "id": "default",
                    "name": "日常模板",
                    "description": "默认的上下文注入模板",
                    "content": "--- [CONSCIOUSNESS_CONTEXT] ---\n{% if inject_emotion %}🎭 情绪状态：{{ emotional_label }}{% endif %}\n--- /[CONSCIOUSNESS_CONTEXT] ---",
                    "is_default": True
                }
            ],
            "active_id": "default"
        }
    }


@pytest.fixture
def mock_weather_data():
    """模拟天气数据"""
    return {
        "success": True,
        "data": {
            "city": "北京",
            "weather": "晴",
            "temperature": 28,
            "humidity": 45,
            "winddirection": "东南风",
            "forecast": [
                {
                    "date": "2026-07-31",
                    "weather": "多云",
                    "temp_min": 22,
                    "temp_max": 32
                }
            ]
        }
    }


@pytest.fixture
def mock_consciousness_data():
    """模拟意识状态数据"""
    return {
        "longing": {
            "score": 0.35,
            "level": 2,
            "label": "missing",
            "last_user_msg_at": "2026-07-31T10:00:00",
            "last_self_msg_at": "2026-07-31T09:30:00"
        },
        "chat_heat": {
            "heat": 2.5,
            "label": "hot",
            "recent_count": 5,
            "recent_hours": 1.0,
            "recent_user_msg_at": "2026-07-31T10:30:00"
        },
        "emotional_intensity": {
            "intensity": 0.65,
            "label": "八卦"
        }
    }


@pytest.fixture
def mock_template_data():
    """模拟模板渲染数据"""
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
            "wind_dir": "东南风",
            "wind_scale": "3-4级"
        },
        "memories": [
            {"text": "上次聊到了天气和心情"},
            {"text": "讨论了周末计划"}
        ],
        "reflection": "用户最近情绪稳定，聊天频率适中",
        "inject_emotion": True,
        "inject_heat": True,
        "inject_longing": True,
        "inject_memory": True,
        "platform": "weixin",
        "sender_id": "user_001"
    }
