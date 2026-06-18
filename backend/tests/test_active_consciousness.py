"""延迟队列过期机制测试 + LLM 降级调用测试 + 配置验证测试 + 动态权重合并测试 + 念头类型判断测试 + 延迟队列硬限制测试 + 日志清理测试"""
import pytest
import asyncio
import unittest.mock
from datetime import datetime, timedelta

from services.active_consciousness_service import is_thought_expired, call_llm_with_fallback, validate_active_consciousness_config
from services.active_consciousness_service import merge_emotion_dynamic, calculate_llm_confidence
from services.active_consciousness_service import determine_thought_type_v2
from services.active_consciousness_service import add_to_delay_queue_v2
from services.active_consciousness_service import cleanup_old_logs
from models.active_consciousness import EmotionState, ThoughtType


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


# ============ LLM 降级调用测试 ============

@pytest.mark.asyncio
async def test_call_llm_with_fallback_on_timeout():
    """测试 LLM 超时时的降级处理"""
    async def mock_llm_call(prompt):
        raise TimeoutError("LLM call timeout")

    fallback_value = {"valence": 0.5, "arousal": 0.3, "social_need": 0.2}
    result, success = await call_llm_with_fallback(mock_llm_call, "test prompt", fallback_value)

    assert success == False
    assert result == fallback_value


@pytest.mark.asyncio
async def test_call_llm_with_fallback_on_invalid_response():
    """测试 LLM 返回无效结果时的降级处理"""
    async def mock_llm_call(prompt):
        return None

    fallback_value = {"valence": 0.5, "arousal": 0.3, "social_need": 0.2}
    result, success = await call_llm_with_fallback(mock_llm_call, "test prompt", fallback_value)

    assert success == False
    assert result == fallback_value


@pytest.mark.asyncio
async def test_call_llm_with_fallback_on_success():
    """测试 LLM 正常返回"""
    expected_result = {"valence": 0.8, "arousal": 0.6, "social_need": 0.4}

    async def mock_llm_call(prompt):
        return expected_result

    fallback_value = {"valence": 0.5, "arousal": 0.3, "social_need": 0.2}
    result, success = await call_llm_with_fallback(mock_llm_call, "test prompt", fallback_value)

    assert success == True
    assert result == expected_result


# ============ 配置验证测试 ============

def test_validate_config_with_invalid_heartbeat_interval():
    """测试无效心跳间隔验证"""
    config = {
        "active": {
            "heartbeat_interval": 30  # 小于 60
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) > 0
    assert "心跳间隔不能小于 60 秒" in errors[0]


def test_validate_config_with_invalid_thresholds():
    """测试无效阈值验证 - send_threshold 必须大于 delay_threshold"""
    config = {
        "decision": {
            "send_threshold": 0.3,
            "delay_threshold": 0.6  # 大于 send_threshold
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) > 0
    assert "发送阈值必须大于延迟阈值" in errors[0]


def test_validate_config_with_delay_less_than_memory():
    """测试无效阈值验证 - delay_threshold 必须大于 memory_threshold"""
    config = {
        "decision": {
            "send_threshold": 0.8,
            "delay_threshold": 0.1,
            "memory_threshold": 0.3  # 大于 delay_threshold
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) > 0
    assert "延迟阈值必须大于记忆阈值" in errors[0]


def test_validate_config_with_invalid_decay_rate():
    """测试无效情绪衰减率验证"""
    config = {
        "emotion": {
            "decay_rate": 0.5  # 超出 0-0.1 范围
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) > 0
    assert "情绪衰减率必须在 0-0.1 之间" in errors[0]


def test_validate_config_with_invalid_max_age_hours():
    """测试无效延迟队列最大存活时间验证"""
    config = {
        "delay": {
            "max_age_hours": 48  # 超出 1-24 范围
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) > 0
    assert "延迟队列最大存活时间必须在 1-24 小时之间" in errors[0]


def test_validate_config_with_valid_config():
    """测试有效配置验证 - 应返回空错误列表"""
    config = {
        "active": {
            "heartbeat_interval": 600
        },
        "decision": {
            "send_threshold": 0.6,
            "delay_threshold": 0.3,
            "memory_threshold": 0.1
        },
        "emotion": {
            "decay_rate": 0.02
        },
        "delay": {
            "max_age_hours": 4
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) == 0


def test_validate_config_with_multiple_errors():
    """测试多个错误同时存在的情况"""
    config = {
        "active": {
            "heartbeat_interval": 10  # 太小
        },
        "decision": {
            "send_threshold": 0.2,
            "delay_threshold": 0.5,  # 大于 send_threshold
            "memory_threshold": 0.8  # 大于 delay_threshold
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) >= 3
    assert "心跳间隔不能小于 60 秒" in errors
    assert "发送阈值必须大于延迟阈值" in errors
    assert "延迟阈值必须大于记忆阈值" in errors


def test_validate_config_with_empty_config():
    """测试空配置 - 应使用默认值，全部通过验证"""
    config = {}
    errors = validate_active_consciousness_config(config)
    assert len(errors) == 0


# ============ 心跳调度器重启测试 ============

def test_restart_heartbeat_scheduler_exists():
    """测试 restart_heartbeat_scheduler 函数存在且可调用"""
    from services.active_consciousness_service import restart_heartbeat_scheduler
    assert callable(restart_heartbeat_scheduler)


# ============ 动态权重合并测试 ============

def test_merge_emotion_dynamic_with_low_confidence():
    """测试低置信度时的动态权重"""
    evolved = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)
    llm_assessed = EmotionState(valence=0.8, arousal=0.7, social_need=0.5)

    # 低置信度，更信任演化
    merged = merge_emotion_dynamic(evolved, llm_assessed, llm_confidence=0.2)

    # 权重应该是 0.7 演化 + 0.3 LLM
    expected_valence = 0.5 * 0.7 + 0.8 * 0.3
    assert abs(merged.valence - expected_valence) < 0.01


def test_merge_emotion_dynamic_with_high_confidence():
    """测试高置信度时的动态权重"""
    evolved = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)
    llm_assessed = EmotionState(valence=0.8, arousal=0.7, social_need=0.5)

    # 高置信度，更信任 LLM
    merged = merge_emotion_dynamic(evolved, llm_assessed, llm_confidence=0.9)

    # 权重应该是 0.3 演化 + 0.7 LLM
    expected_valence = 0.5 * 0.3 + 0.8 * 0.7
    assert abs(merged.valence - expected_valence) < 0.01


def test_calculate_llm_confidence():
    """测试 LLM 置信度计算"""
    evolved = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)
    llm_assessed = EmotionState(valence=0.6, arousal=0.4, social_need=0.3)

    confidence = calculate_llm_confidence(llm_assessed, evolved)

    # 值在合理范围内，差异不大，置信度应该较高
    assert 0.5 <= confidence <= 1.0


# ============ 念头类型判断 v2 测试 ============

def test_determine_thought_type_v2_with_special_time():
    """测试特殊时间判断 - 早上7点应返回时间类型"""
    status = {"longing": {"silence_minutes": 0}}
    emotion_state = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)

    # 模拟早上 7 点
    mock_now = datetime(2026, 6, 18, 7, 30)
    with unittest.mock.patch('services.active_consciousness_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        result = determine_thought_type_v2(status, emotion_state, [], None)

    assert result == ThoughtType.TIME.value


def test_determine_thought_type_v2_with_long_silence():
    """测试长时间沉默判断 - 3小时以上应返回沉默类型"""
    status = {"longing": {"silence_minutes": 200}}  # 3小时以上
    emotion_state = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)

    # 模拟非特殊时间（下午2点）
    mock_now = datetime(2026, 6, 18, 14, 0)
    with unittest.mock.patch('services.active_consciousness_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        result = determine_thought_type_v2(status, emotion_state, [], None)

    assert result == ThoughtType.SILENCE.value


def test_determine_thought_type_v2_with_high_emotion():
    """测试高情绪强度判断 - 强度>0.6应返回情绪类型"""
    status = {"longing": {"silence_minutes": 0}}
    emotion_state = EmotionState(valence=0.8, arousal=0.7, social_need=0.6)  # 强度 = 0.7

    # 模拟非特殊时间（下午2点）
    mock_now = datetime(2026, 6, 18, 14, 0)
    with unittest.mock.patch('services.active_consciousness_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        result = determine_thought_type_v2(status, emotion_state, [], None)

    assert result == ThoughtType.EMOTION.value


def test_determine_thought_type_v2_with_memory():
    """测试有回忆时应返回回忆类型"""
    status = {"longing": {"silence_minutes": 0}}
    emotion_state = EmotionState(valence=0.3, arousal=0.2, social_need=0.2)  # 低强度

    hindsight_results = [{"id": 1, "content": "一段回忆"}]

    # 模拟非特殊时间（下午2点）
    mock_now = datetime(2026, 6, 18, 14, 0)
    with unittest.mock.patch('services.active_consciousness_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        result = determine_thought_type_v2(status, emotion_state, hindsight_results, None)

    assert result == ThoughtType.MEMORY.value


def test_determine_thought_type_v2_default_association():
    """测试默认情况应返回关联类型"""
    status = {"longing": {"silence_minutes": 0}}
    emotion_state = EmotionState(valence=0.3, arousal=0.2, social_need=0.2)  # 低强度

    # 模拟非特殊时间（下午2点）
    mock_now = datetime(2026, 6, 18, 14, 0)
    with unittest.mock.patch('services.active_consciousness_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now
        result = determine_thought_type_v2(status, emotion_state, [], None)

    assert result == ThoughtType.ASSOCIATION.value


# ============ 延迟队列硬限制测试 ============

def test_add_to_delay_queue_v2_when_full():
    """测试队列满时拒绝新念头"""
    with unittest.mock.patch('services.active_consciousness_service.get_delayed_thoughts') as mock_get:
        mock_get.return_value = [unittest.mock.MagicMock(id=i) for i in range(10)]  # 10 个念头

        with unittest.mock.patch('services.active_consciousness_service.ActiveConsciousnessService.get_config') as mock_config:
            mock_config.return_value = {"delay": {"max_queue_size": 10}}

            result = add_to_delay_queue_v2("测试念头", "time", 0.5, None)
            assert result == False


def test_add_to_delay_queue_v2_when_not_full():
    """测试队列未满时添加新念头"""
    with unittest.mock.patch('services.active_consciousness_service.get_delayed_thoughts') as mock_get:
        mock_get.return_value = [unittest.mock.MagicMock(id=i) for i in range(5)]  # 5 个念头

        with unittest.mock.patch('services.active_consciousness_service.ActiveConsciousnessService.get_config') as mock_config:
            mock_config.return_value = {"delay": {"max_queue_size": 10}}

            with unittest.mock.patch('services.active_consciousness_service.save_delayed_thoughts') as mock_save:
                result = add_to_delay_queue_v2("测试念头", "time", 0.5, None)
                assert result == True
                assert mock_save.called


# ============ 日志清理测试 ============

def test_cleanup_old_logs_exists():
    """测试 cleanup_old_logs 函数存在且可调用"""
    assert callable(cleanup_old_logs)


def test_cleanup_old_logs_with_mock():
    """测试 cleanup_old_logs 使用 mock 数据库验证删除逻辑"""
    mock_conn = unittest.mock.MagicMock()
    mock_result = unittest.mock.MagicMock()
    mock_result.rowcount = 5
    mock_conn.execute.return_value = mock_result

    with unittest.mock.patch('services.active_consciousness_service.active_engine') as mock_engine:
        mock_engine.connect.return_value.__enter__ = unittest.mock.MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = unittest.mock.MagicMock(return_value=False)

        # 不应抛异常
        cleanup_old_logs(days_to_keep=30)

        # 验证执行了 DELETE 语句
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        sql = str(call_args[0][0])
        assert "DELETE FROM active_heartbeat_logs" in sql
        assert "created_at" in sql
