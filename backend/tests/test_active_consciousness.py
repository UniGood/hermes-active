"""延迟队列过期机制测试"""
import pytest
from datetime import datetime, timedelta

from services.active_consciousness_service import is_thought_expired


def test_is_thought_expired_with_old_thought():
    """测试过期念头检测 - 5小时前的念头应过期"""
    old_thought = {
        "id": 1,
        "content": "测试念头",
        "created_at": (datetime.now() - timedelta(hours=5)).isoformat()
    }
    assert is_thought_expired(old_thought, max_age_hours=4) == True


def test_is_thought_expired_with_recent_thought():
    """测试未过期念头检测 - 1小时前的念头不应过期"""
    recent_thought = {
        "id": 2,
        "content": "测试念头",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat()
    }
    assert is_thought_expired(recent_thought, max_age_hours=4) == False


def test_is_thought_expired_with_no_created_at():
    """测试缺少 created_at 字段时应返回过期"""
    thought_no_time = {
        "id": 3,
        "content": "测试念头"
    }
    assert is_thought_expired(thought_no_time, max_age_hours=4) == True


def test_is_thought_expired_with_exact_boundary():
    """测试边界情况 - 刚好4小时前的念头应过期"""
    thought = {
        "id": 4,
        "content": "测试念头",
        "created_at": (datetime.now() - timedelta(hours=4, seconds=1)).isoformat()
    }
    assert is_thought_expired(thought, max_age_hours=4) == True
