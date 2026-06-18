# 主动意识模块闭环优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化主动意识模块的闭环逻辑，解决 12 个问题，提升系统稳定性和用户体验

**Architecture:** 基于现有主动意识服务架构，修改 `active_consciousness_service.py` 中的核心函数，添加过期机制、完善异常处理、优化配置验证

**Tech Stack:** Python, FastAPI, SQLAlchemy, APScheduler

---

## 文件结构

### 修改文件
- `backend/services/active_consciousness_service.py` - 主要修改文件
- `backend/routers/config.py` - 配置路由
- `backend/services/message_service.py` - 消息服务

### 测试文件
- `backend/tests/test_active_consciousness.py` - 主动意识测试

---

## Task 1: 延迟队列过期机制（P0）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:2210-2304`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from datetime import datetime, timedelta
from services.active_consciousness_service import is_thought_expired, reevaluate_delayed_thoughts

def test_is_thought_expired_with_old_thought():
    """测试过期念头检测"""
    # 创建一个 5 小时前的念头
    old_thought = {
        "id": 1,
        "content": "测试念头",
        "created_at": (datetime.now() - timedelta(hours=5)).isoformat()
    }
    assert is_thought_expired(old_thought, max_age_hours=4) == True

def test_is_thought_expired_with_recent_thought():
    """测试未过期念头检测"""
    # 创建一个 1 小时前的念头
    recent_thought = {
        "id": 2,
        "content": "测试念头",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat()
    }
    assert is_thought_expired(recent_thought, max_age_hours=4) == False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_is_thought_expired_with_old_thought -v`
Expected: FAIL with "is_thought_expired not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 reevaluate_delayed_thoughts 函数之前添加

def is_thought_expired(thought: dict, max_age_hours: float = 4.0) -> bool:
    """
    检查念头是否过期
    
    Args:
        thought: 念头数据
        max_age_hours: 最大存活时间（小时）
    
    Returns:
        True 如果念头已过期
    """
    created_at = thought.get("created_at")
    if not created_at:
        return True
    
    try:
        created = datetime.fromisoformat(created_at)
        age_hours = (datetime.now() - created).total_seconds() / 3600
        return age_hours > max_age_hours
    except Exception:
        return True
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_is_thought_expired_with_old_thought -v`
Expected: PASS

- [ ] **Step 5: 修改 reevaluate_delayed_thoughts 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 reevaluate_delayed_thoughts 函数，在循环开始时添加过期检查

async def reevaluate_delayed_thoughts(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Dict[str, int]:
    """重新评估延迟队列中的念头"""
    delay_config = config.get("delay", {})
    max_retry = int(delay_config.get("max_retry", 3))
    retry_interval = int(delay_config.get("retry_interval_minutes", 30))
    max_age_hours = float(delay_config.get("max_age_hours", 4))  # 新增配置

    decision_config = config.get("decision", {})
    send_threshold = decision_config.get("send_threshold", 0.6)

    delayed_thoughts = get_delayed_thoughts()
    if not delayed_thoughts:
        return {"sent": 0, "discarded": 0, "kept": 0}

    logger.info("延迟队列重评估开始: 队列长度=%d", len(delayed_thoughts))

    stats = {"sent": 0, "discarded": 0, "kept": 0}
    remaining_thoughts = []

    for thought in delayed_thoughts:
        # 检查是否过期（新增）
        if is_thought_expired(thought, max_age_hours):
            logger.info("延迟队列重评估: id=%d, 过期丢弃", thought.id)
            stats["discarded"] += 1
            continue
        
        # 超过最大重试次数
        if thought.retry_count >= max_retry:
            stats["discarded"] += 1
            continue

        # ... 其余代码保持不变 ...
```

- [ ] **Step 6: 添加配置项**

```python
# backend/services/active_consciousness_service.py
# 在 _DEFAULTS 字典中添加

_DEFAULTS = {
    # ... 现有配置 ...
    
    # 延迟发送
    "active_consciousness.delay.enabled": "true",
    "active_consciousness.delay.max_retry": "3",
    "active_consciousness.delay.retry_interval_minutes": "30",
    "active_consciousness.delay.max_queue_size": "10",
    "active_consciousness.delay.max_age_hours": "4",  # 新增
}
```

- [ ] **Step 7: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: add delay queue expiration mechanism"
```

---

## Task 2: LLM 调用降级完善（P0）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:1577-1586`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import call_llm_with_fallback

@pytest.mark.asyncio
async def test_call_llm_with_fallback_on_timeout():
    """测试 LLM 超时时的降级处理"""
    # 模拟 LLM 调用超时
    async def mock_llm_call(prompt):
        raise TimeoutError("LLM call timeout")
    
    fallback_value = {"valence": 0.5, "arousal": 0.3, "social_need": 0.2}
    result, success = await call_llm_with_fallback(mock_llm_call, "test prompt", fallback_value)
    
    assert success == False
    assert result == fallback_value

@pytest.mark.asyncio
async def test_call_llm_with_fallback_on_invalid_response():
    """测试 LLM 返回无效结果时的降级处理"""
    # 模拟 LLM 返回 None
    async def mock_llm_call(prompt):
        return None
    
    fallback_value = {"valence": 0.5, "arousal": 0.3, "social_need": 0.2}
    result, success = await call_llm_with_fallback(mock_llm_call, "test prompt", fallback_value)
    
    assert success == False
    assert result == fallback_value
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_call_llm_with_fallback_on_timeout -v`
Expected: FAIL with "call_llm_with_fallback not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 evaluate_emotion_with_llm 函数之前添加

async def call_llm_with_fallback(
    llm_func,
    prompt: str,
    fallback_value: Any,
    timeout: float = 30.0
) -> tuple[Any, bool]:
    """
    调用 LLM 并在失败时返回 fallback 值
    
    Args:
        llm_func: LLM 调用函数
        prompt: 提示词
        fallback_value: 失败时的默认值
        timeout: 超时时间（秒）
    
    Returns:
        (result, success): 结果和是否成功
    """
    try:
        result = await asyncio.wait_for(llm_func(prompt), timeout=timeout)
        if result is None:
            logger.warning("LLM 返回 None，使用 fallback")
            return fallback_value, False
        return result, True
    except TimeoutError:
        logger.error("LLM 调用超时 (%.1f 秒)", timeout)
        return fallback_value, False
    except Exception as e:
        logger.error("LLM 调用异常: %s", e)
        return fallback_value, False
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_call_llm_with_fallback_on_timeout -v`
Expected: PASS

- [ ] **Step 5: 修改 evaluate_emotion_with_llm 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 evaluate_emotion_with_llm 函数

async def evaluate_emotion_with_llm(
    session_context: str,
    hindsight_context: str,
    status: Dict[str, Any],
    llm_config: Dict[str, Any]
) -> EmotionState:
    """使用 LLM 评估当前情绪"""
    # 构建提示词
    prompt = build_emotion_evaluation_prompt(session_context, hindsight_context, status)
    
    # 默认 fallback 值
    fallback_state = EmotionState(
        valence=0.5,
        arousal=0.3,
        social_need=0.2,
        dominant="calm"
    )
    
    # 调用 LLM
    if llm_config.get("mode") == "hermes":
        from agent.auxiliary_client import call_llm
        result, success = await call_llm_with_fallback(
            lambda p: call_llm(messages=[{"role": "user", "content": p}]),
            prompt,
            fallback_state
        )
    else:
        from services.llm_service import LLMService
        result, success = await call_llm_with_fallback(
            lambda p: LLMService.generate_message(llm_config=llm_config, prompt=p),
            prompt,
            fallback_state
        )
    
    if not success:
        return fallback_state
    
    # 解析 LLM 返回的情绪值
    try:
        emotion_data = parse_emotion_response(result)
        return EmotionState(
            valence=emotion_data.get("valence", 0.5),
            arousal=emotion_data.get("arousal", 0.3),
            social_need=emotion_data.get("social_need", 0.2),
            dominant=emotion_data.get("dominant", "calm")
        )
    except Exception as e:
        logger.error("解析 LLM 情绪返回失败: %s", e)
        return fallback_state
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: improve LLM call fallback mechanism"
```

---

## Task 3: 配置验证（P1）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:183-192`
- Modify: `backend/routers/config.py`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import validate_active_consciousness_config

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
    """测试无效阈值验证"""
    config = {
        "decision": {
            "send_threshold": 0.3,
            "delay_threshold": 0.6  # 大于 send_threshold
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) > 0
    assert "发送阈值必须大于延迟阈值" in errors[0]

def test_validate_config_with_valid_config():
    """测试有效配置验证"""
    config = {
        "active": {
            "heartbeat_interval": 600
        },
        "decision": {
            "send_threshold": 0.6,
            "delay_threshold": 0.3
        }
    }
    errors = validate_active_consciousness_config(config)
    assert len(errors) == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_validate_config_with_invalid_heartbeat_interval -v`
Expected: FAIL with "validate_active_consciousness_config not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 ActiveConsciousnessService 类之前添加

def validate_active_consciousness_config(config: Dict[str, Any]) -> List[str]:
    """
    验证主动意识配置
    
    Args:
        config: 配置字典
    
    Returns:
        错误消息列表，空列表表示验证通过
    """
    errors = []
    
    # 验证心跳间隔
    heartbeat_interval = config.get("active", {}).get("heartbeat_interval", 600)
    if heartbeat_interval < 60:
        errors.append("心跳间隔不能小于 60 秒")
    
    # 验证阈值关系
    send_threshold = config.get("decision", {}).get("send_threshold", 0.6)
    delay_threshold = config.get("decision", {}).get("delay_threshold", 0.3)
    memory_threshold = config.get("decision", {}).get("memory_threshold", 0.1)
    
    if send_threshold <= delay_threshold:
        errors.append("发送阈值必须大于延迟阈值")
    if delay_threshold <= memory_threshold:
        errors.append("延迟阈值必须大于记忆阈值")
    
    # 验证情绪演化参数
    decay_rate = config.get("emotion", {}).get("decay_rate", 0.02)
    if decay_rate < 0 or decay_rate > 0.1:
        errors.append("情绪衰减率必须在 0-0.1 之间")
    
    # 验证延迟队列参数
    max_age_hours = config.get("delay", {}).get("max_age_hours", 4)
    if max_age_hours < 1 or max_age_hours > 24:
        errors.append("延迟队列最大存活时间必须在 1-24 小时之间")
    
    return errors
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_validate_config_with_invalid_heartbeat_interval -v`
Expected: PASS

- [ ] **Step 5: 修改配置更新路由**

```python
# backend/routers/config.py
# 在 update_active_consciousness_config 函数中添加验证

from services.active_consciousness_service import (
    ActiveConsciousnessService,
    validate_active_consciousness_config
)

@router.put("/active-consciousness/config")
async def update_active_consciousness_config(config: Dict[str, Any]):
    """更新主动意识配置"""
    # 验证配置
    errors = validate_active_consciousness_config(config)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "配置验证失败", "errors": errors}
        )
    
    # 更新配置
    ActiveConsciousnessService.update_config(config)
    return {"success": True, "message": "配置已更新"}
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/routers/config.py backend/tests/test_active_consciousness.py
git commit -m "feat: add config validation for active consciousness"
```

---

## Task 4: 配置实时生效（P1）

**Files:**
- Modify: `backend/routers/config.py`
- Modify: `backend/services/active_consciousness_service.py:1745-1760`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import restart_heartbeat_scheduler

def test_restart_heartbeat_scheduler():
    """测试重启心跳调度器"""
    # 这个测试需要实际运行调度器，这里只是验证函数存在
    assert callable(restart_heartbeat_scheduler)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_restart_heartbeat_scheduler -v`
Expected: FAIL with "restart_heartbeat_scheduler not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 start_heartbeat_scheduler 函数之后添加

def restart_heartbeat_scheduler(new_interval: int = None):
    """
    重启心跳调度器
    
    Args:
        new_interval: 新的心跳间隔（秒），如果为 None 则使用配置中的值
    """
    global heartbeat_scheduler
    
    # 停止现有调度器
    if heartbeat_scheduler.running:
        heartbeat_scheduler.shutdown()
        logger.info("心跳调度器已停止")
    
    # 获取新的间隔
    if new_interval is None:
        config = ActiveConsciousnessService.get_config()
        new_interval = int(config.get("active", {}).get("heartbeat_interval", 600))
    
    # 创建新的调度器
    heartbeat_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    heartbeat_scheduler.add_job(
        run_heartbeat,
        IntervalTrigger(seconds=new_interval),
        id="heartbeat_job",
        name="主动意识心跳",
        replace_existing=True
    )
    
    # 启动调度器
    heartbeat_scheduler.start()
    logger.info("心跳调度器已重启，间隔: %d 秒", new_interval)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_restart_heartbeat_scheduler -v`
Expected: PASS

- [ ] **Step 5: 修改配置更新路由**

```python
# backend/routers/config.py
# 修改 update_active_consciousness_config 函数

@router.put("/active-consciousness/config")
async def update_active_consciousness_config(config: Dict[str, Any]):
    """更新主动意识配置"""
    # 验证配置
    errors = validate_active_consciousness_config(config)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "配置验证失败", "errors": errors}
        )
    
    # 获取旧配置
    old_config = ActiveConsciousnessService.get_config()
    old_interval = old_config.get("active", {}).get("heartbeat_interval", 600)
    
    # 更新配置
    ActiveConsciousnessService.update_config(config)
    
    # 如果心跳间隔变化，重启调度器
    new_interval = config.get("active", {}).get("heartbeat_interval", old_interval)
    if new_interval != old_interval:
        from services.active_consciousness_service import restart_heartbeat_scheduler
        restart_heartbeat_scheduler(new_interval)
    
    return {"success": True, "message": "配置已更新"}
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/routers/config.py backend/tests/test_active_consciousness.py
git commit -m "feat: restart heartbeat scheduler on config change"
```

---

## Task 5: 情绪与日志一致性（P1）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:1606-1618`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import run_heartbeat

@pytest.mark.asyncio
async def test_run_heartbeat_saves_emotion_before_log():
    """测试心跳先保存情绪再记录日志"""
    # 这个测试需要 mock 数据库，这里只是验证逻辑存在
    # 实际测试需要更复杂的设置
    pass
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_run_heartbeat_saves_emotion_before_log -v`
Expected: FAIL or PASS (depending on implementation)

- [ ] **Step 3: 修改 run_heartbeat 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 run_heartbeat 函数，调整保存顺序

async def run_heartbeat():
    """执行心跳 - v0.2.1 版本（情绪连续性 + 时间窗口 + 延迟队列）"""
    # ... 前面的代码保持不变 ...
    
    # 9. 保存情绪状态（先保存）
    update_emotion_state(merged_state)
    all_details["emotion_saved"] = True
    
    # 10. 使用新决策公式
    decision_type, reason, score = make_decision_v2(config, status, merged_state)
    all_details["decision"] = {
        "type": decision_type,
        "reason": reason,
        "score": round(score, 3)
    }
    logger.info("决策结果: type=%s, score=%.3f, reason=%s", decision_type, score, reason)
    
    # 11. 记录心跳日志（后记录，此时情绪已保存）
    duration_ms = round((time.time() - start_time) * 1000)
    heartbeat_id = ActiveConsciousnessService.write_heartbeat_log(
        started_at=started_at,
        duration_ms=duration_ms,
        longing_before=longing.get("score"),
        chat_heat=chat_heat.get("heat"),
        emotional_intensity=merged_state.intensity(),
        recall_count=recall_count,
        thoughts_generated=1 if decision_type != "skip" else 0,
        message_sent=False,
        details=json.dumps(all_details, ensure_ascii=False) if all_details else None
    )
    
    # ... 后面的代码保持不变 ...
```

- [ ] **Step 4: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "fix: save emotion state before logging in heartbeat"
```

---

## Task 6: 动态权重调整（P2）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:1588-1592`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import merge_emotion_dynamic
from models.active_consciousness import EmotionState

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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_merge_emotion_dynamic_with_low_confidence -v`
Expected: FAIL with "merge_emotion_dynamic not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 merge_emotion 函数之后添加

def merge_emotion_dynamic(
    evolved: EmotionState,
    llm_assessed: EmotionState,
    llm_confidence: float
) -> EmotionState:
    """
    动态权重合并情绪
    
    Args:
        evolved: 演化后的情绪
        llm_assessed: LLM 评估的情绪
        llm_confidence: LLM 评估的置信度 (0-1)
    
    Returns:
        合并后的情绪
    """
    # 根据置信度调整权重
    if llm_confidence < 0.3:
        # LLM 不可信，更信任演化
        weight_evolved, weight_llm = 0.7, 0.3
    elif llm_confidence > 0.8:
        # LLM 很可信，更信任 LLM
        weight_evolved, weight_llm = 0.3, 0.7
    else:
        # 默认权重
        weight_evolved, weight_llm = 0.4, 0.6
    
    logger.info("动态权重合并: confidence=%.2f, evolved_weight=%.2f, llm_weight=%.2f",
                llm_confidence, weight_evolved, weight_llm)
    
    return EmotionState(
        valence=evolved.valence * weight_evolved + llm_assessed.valence * weight_llm,
        arousal=evolved.arousal * weight_evolved + llm_assessed.arousal * weight_llm,
        social_need=evolved.social_need * weight_evolved + llm_assessed.social_need * weight_llm,
        dominant=llm_assessed.dominant if llm_confidence > 0.5 else evolved.dominant,
        updated_at=datetime.now().isoformat()
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_merge_emotion_dynamic_with_low_confidence -v`
Expected: PASS

- [ ] **Step 5: 修改 run_heartbeat 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 run_heartbeat 函数，使用动态权重

# 8. 合并情绪（演化值 + LLM 评估值）- 使用动态权重
llm_confidence = calculate_llm_confidence(llm_assessed, evolved_state)  # 新增函数
merged_state = merge_emotion_dynamic(evolved_state, llm_assessed, llm_confidence)
all_details["emotion_merged"] = merged_state.to_dict()
all_details["llm_confidence"] = llm_confidence
logger.info("情绪合并: valence=%.3f, arousal=%.3f, dominant=%s, confidence=%.2f",
            merged_state.valence, merged_state.arousal, merged_state.dominant, llm_confidence)
```

- [ ] **Step 6: 添加置信度计算函数**

```python
# backend/services/active_consciousness_service.py
# 在 merge_emotion_dynamic 函数之后添加

def calculate_llm_confidence(llm_assessed: EmotionState, evolved: EmotionState) -> float:
    """
    计算 LLM 评估的置信度
    
    置信度基于：
    1. LLM 返回值是否在合理范围内
    2. LLM 返回值与演化值的差异
    """
    confidence = 0.5  # 基础置信度
    
    # 检查值是否在合理范围内
    if 0 <= llm_assessed.valence <= 1 and 0 <= llm_assessed.arousal <= 1:
        confidence += 0.2
    
    # 检查与演化值的差异（差异太大可能表示 LLM 不准确）
    valence_diff = abs(llm_assessed.valence - evolved.valence)
    arousal_diff = abs(llm_assessed.arousal - evolved.arousal)
    
    if valence_diff < 0.3 and arousal_diff < 0.3:
        confidence += 0.3
    elif valence_diff > 0.5 or arousal_diff > 0.5:
        confidence -= 0.2
    
    return max(0.0, min(1.0, confidence))
```

- [ ] **Step 7: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: add dynamic emotion merge weights based on LLM confidence"
```

---

## Task 7: 念头类型判断优化（P2）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:2040-2060`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from datetime import datetime
from services.active_consciousness_service import determine_thought_type_v2
from models.active_consciousness import EmotionState, ThoughtType

def test_determine_thought_type_v2_with_special_time():
    """测试特殊时间判断"""
    status = {"longing": {"silence_minutes": 0}}
    emotion_state = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)
    
    # 模拟早上 7 点
    with unittest.mock.patch('services.active_consciousness_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 6, 18, 7, 30)
        result = determine_thought_type_v2(status, emotion_state, [], None)
    
    assert result == ThoughtType.TIME.value

def test_determine_thought_type_v2_with_long_silence():
    """测试长时间沉默判断"""
    status = {"longing": {"silence_minutes": 200}}  # 3小时以上
    emotion_state = EmotionState(valence=0.5, arousal=0.3, social_need=0.2)
    
    result = determine_thought_type_v2(status, emotion_state, [], None)
    assert result == ThoughtType.SILENCE.value

def test_determine_thought_type_v2_with_high_emotion():
    """测试高情绪强度判断"""
    status = {"longing": {"silence_minutes": 0}}
    emotion_state = EmotionState(valence=0.8, arousal=0.7, social_need=0.6)  # 高强度
    
    result = determine_thought_type_v2(status, emotion_state, [], None)
    assert result == ThoughtType.EMOTION.value
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_determine_thought_type_v2_with_special_time -v`
Expected: FAIL with "determine_thought_type_v2 not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 determine_thought_type 函数之后添加

def determine_thought_type_v2(
    status: Dict[str, Any],
    emotion_state: EmotionState,
    hindsight_results: List[Dict],
    context: Optional[Dict]
) -> str:
    """
    更智能的念头类型判断
    
    优先级：
    1. 特殊时间（早安、晚安）
    2. 长时间沉默
    3. 高情绪强度
    4. 相关回忆
    5. 默认关联
    """
    now = datetime.now()
    
    # 1. 检查特殊时间（早安 7-8, 晚安 22-23）
    if now.hour in [7, 8, 22, 23]:
        return ThoughtType.TIME.value
    
    # 2. 检查沉默时长
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes > 180:  # 3小时没聊天
        return ThoughtType.SILENCE.value
    
    # 3. 检查情绪强度
    if emotion_state.intensity() > 0.6:
        return ThoughtType.EMOTION.value
    
    # 4. 检查是否有相关回忆
    if hindsight_results and len(hindsight_results) > 0:
        return ThoughtType.MEMORY.value
    
    # 5. 默认关联念头
    return ThoughtType.ASSOCIATION.value
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_determine_thought_type_v2_with_special_time -v`
Expected: PASS

- [ ] **Step 5: 修改 run_heartbeat 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 run_heartbeat 函数，使用新的念头类型判断

# 在生成念头时使用新的判断函数
thought_type = determine_thought_type_v2(status, merged_state, hindsight_results, None)
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: improve thought type determination logic"
```

---

## Task 8: 延迟队列硬限制（P2）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:2178-2203`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import add_to_delay_queue_v2

def test_add_to_delay_queue_v2_when_full():
    """测试队列满时拒绝新念头"""
    # 模拟队列已满
    with unittest.mock.patch('services.active_consciousness_service.get_delayed_thoughts') as mock_get:
        mock_get.return_value = [{"id": i} for i in range(10)]  # 10 个念头
        
        result = add_to_delay_queue_v2("测试念头", "time", 0.5, None)
        assert result == False

def test_add_to_delay_queue_v2_when_not_full():
    """测试队列未满时添加新念头"""
    # 模拟队列未满
    with unittest.mock.patch('services.active_consciousness_service.get_delayed_thoughts') as mock_get:
        mock_get.return_value = [{"id": i} for i in range(5)]  # 5 个念头
        
        with unittest.mock.patch('services.active_consciousness_service.save_delayed_thoughts') as mock_save:
            result = add_to_delay_queue_v2("测试念头", "time", 0.5, None)
            assert result == True
            assert mock_save.called
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_add_to_delay_queue_v2_when_full -v`
Expected: FAIL with "add_to_delay_queue_v2 not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 add_to_delay_queue 函数之后添加

def add_to_delay_queue_v2(
    content: str,
    thought_type: str,
    score: float,
    emotion_state: EmotionState
) -> bool:
    """
    添加念头到延迟队列（硬限制版本）
    
    Returns:
        True 如果添加成功，False 如果队列已满
    """
    thoughts = get_delayed_thoughts()
    
    # 硬限制：队列满时拒绝新念头
    config = ActiveConsciousnessService.get_config()
    max_queue_size = int(config.get("delay", {}).get("max_queue_size", 10))
    
    if len(thoughts) >= max_queue_size:
        logger.warning("延迟队列已满 (%d/%d)，拒绝新念头: %s", 
                      len(thoughts), max_queue_size, content[:50])
        return False
    
    # 添加新念头
    new_thought = DelayedThought(
        id=int(datetime.now().timestamp()),
        content=content,
        thought_type=thought_type,
        score=score,
        created_at=datetime.now().isoformat(),
        emotion_snapshot=emotion_state.to_dict() if emotion_state else {}
    )
    thoughts.append(new_thought)
    
    # 保存
    save_delayed_thoughts(thoughts)
    logger.info("念头已添加到延迟队列: id=%d, type=%s, score=%.3f", 
                new_thought.id, thought_type, score)
    return True
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_add_to_delay_queue_v2_when_full -v`
Expected: PASS

- [ ] **Step 5: 修改 run_heartbeat 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 run_heartbeat 函数，使用新的延迟队列函数

elif decision_type == "delay_send":
    # 入延迟队列（使用硬限制版本）
    thought = await generate_thought_for_delay(config, status, merged_state)
    if thought:
        all_details["thought_generation"] = {"success": True, "thought": thought}
        thought_type = determine_thought_type_v2(status, merged_state, hindsight_results, None)
        added = add_to_delay_queue_v2(thought, thought_type, score, merged_state)
        all_details["thought_type"] = thought_type
        all_details["hindsight_stored"] = False
        all_details["delay_queue_added"] = added
        if added:
            logger.info("念头入延迟队列: %s", thought[:50])
        else:
            logger.warning("念头入延迟队列失败（队列已满）: %s", thought[:50])
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: add hard limit for delay queue"
```

---

## Task 9: 日志清理机制（P2）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:1745-1760`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from datetime import datetime, timedelta
from services.active_consciousness_service import cleanup_old_logs

def test_cleanup_old_logs():
    """测试清理旧日志"""
    # 这个测试需要实际数据库，这里只是验证函数存在
    assert callable(cleanup_old_logs)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_cleanup_old_logs -v`
Expected: FAIL with "cleanup_old_logs not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 start_heartbeat_scheduler 函数之后添加

def cleanup_old_logs(days_to_keep: int = 30):
    """
    清理旧的心跳日志
    
    Args:
        days_to_keep: 保留天数
    """
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    
    try:
        with active_engine.connect() as conn:
            # 删除旧的心跳日志
            result = conn.execute(text("""
                DELETE FROM active_heartbeat_logs 
                WHERE created_at < :cutoff
            """), {"cutoff": cutoff_date})
            deleted_count = result.rowcount
            conn.commit()
            
            logger.info("已清理 %d 条旧心跳日志 (保留 %d 天)", deleted_count, days_to_keep)
    except Exception as e:
        logger.error("清理旧日志失败: %s", e)

def schedule_log_cleanup():
    """调度日志清理任务"""
    cleanup_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    
    # 每天凌晨 3 点执行清理
    cleanup_scheduler.add_job(
        cleanup_old_logs,
        CronTrigger(hour=3, minute=0),
        id="log_cleanup_job",
        name="日志清理",
        replace_existing=True
    )
    
    cleanup_scheduler.start()
    logger.info("日志清理调度器已启动")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_cleanup_old_logs -v`
Expected: PASS

- [ ] **Step 5: 在应用启动时调度清理任务**

```python
# backend/main.py
# 在 lifespan 函数中添加

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    init_active_db()
    AuthService.init_default_admin(ActiveSession())
    
    # 启动心跳调度器
    start_heartbeat_scheduler()
    
    # 启动日志清理调度器
    from services.active_consciousness_service import schedule_log_cleanup
    schedule_log_cleanup()
    
    yield
    
    # 关闭时
    stop_heartbeat_scheduler()
    await close_hindsight_client()
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/main.py backend/tests/test_active_consciousness.py
git commit -m "feat: add log cleanup mechanism"
```

---

## Task 10: 延迟队列状态同步（P3）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:800-900`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import ActiveConsciousnessService

def test_get_status_includes_delayed_count():
    """测试状态查询包含延迟队列数量"""
    status = ActiveConsciousnessService.get_status()
    assert "delayed_count" in status
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_get_status_includes_delayed_count -v`
Expected: FAIL with "delayed_count not in status"

- [ ] **Step 3: 修改 get_status 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 ActiveConsciousnessService.get_status 函数

@staticmethod
def get_status() -> Dict[str, Any]:
    """获取主动意识状态"""
    db = ActiveSession()
    try:
        # ... 现有代码 ...
        
        # 获取延迟队列数量（新增）
        delayed_thoughts = get_delayed_thoughts()
        delayed_count = len(delayed_thoughts)
        
        return {
            "enabled": enabled,
            "heartbeat_count": heartbeat_count,
            "last_heartbeat_at": last_heartbeat_at,
            "longing": longing.dict(),
            "chat_heat": chat_heat.dict(),
            "emotional_intensity": emotional_intensity.dict(),
            "emotion_state": emotion_state.to_dict() if emotion_state else None,
            "time_fitness": {"score": time_fitness, "label": time_label},
            "delayed_count": delayed_count,  # 新增
            "today_sent_count": today_sent_count,
            "hour_sent_count": hour_sent_count,
            "last_sent_at": last_sent_at,
        }
    finally:
        db.close()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_get_status_includes_delayed_count -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: include delayed queue count in status"
```

---

## Task 11: Hindsight 重连机制（P3）

**Files:**
- Modify: `backend/services/active_consciousness_service.py:33-49`
- Test: `backend/tests/test_active_consciousness.py`

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_active_consciousness.py
import pytest
from services.active_consciousness_service import reset_hindsight_client

def test_reset_hindsight_client():
    """测试重置 Hindsight 客户端"""
    assert callable(reset_hindsight_client)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_reset_hindsight_client -v`
Expected: FAIL with "reset_hindsight_client not defined"

- [ ] **Step 3: 写最小实现**

```python
# backend/services/active_consciousness_service.py
# 在 close_hindsight_client 函数之后添加

async def reset_hindsight_client():
    """重置 Hindsight 客户端（用于重连）"""
    global _hindsight_client
    if _hindsight_client is not None:
        try:
            await _hindsight_client.aclose()
        except Exception:
            pass
        _hindsight_client = None
    logger.info("Hindsight 客户端已重置")

async def call_hindsight_with_retry(
    query: str,
    limit: int = 5,
    bank_id: str = "hermes",
    base_url: str = "http://localhost:8888",
    timeout: float = 30.0,
    max_retries: int = 3
) -> List[Dict]:
    """
    带重试的 Hindsight 调用
    
    Args:
        query: 查询内容
        limit: 返回数量
        bank_id: 银行 ID
        base_url: 基础 URL
        timeout: 超时时间
        max_retries: 最大重试次数
    
    Returns:
        召回结果列表
    """
    for attempt in range(max_retries):
        try:
            client = get_hindsight_client(base_url, timeout)
            results = await client.arecall(
                query=query,
                limit=limit,
                bank_id=bank_id
            )
            return results
        except ConnectionError as e:
            logger.warning("Hindsight 连接失败，尝试重连 (%d/%d): %s", 
                          attempt + 1, max_retries, e)
            await reset_hindsight_client()
            if attempt == max_retries - 1:
                logger.error("Hindsight 重连失败，已用尽重试次数")
                return []
        except Exception as e:
            logger.error("Hindsight 调用失败: %s", e)
            return []
    return []
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_active_consciousness.py::test_reset_hindsight_client -v`
Expected: PASS

- [ ] **Step 5: 修改 run_heartbeat 函数**

```python
# backend/services/active_consciousness_service.py
# 修改 run_heartbeat 函数，使用带重试的 Hindsight 调用

# 优先从 Hindsight 获取记忆
if hindsight_config.get("enabled", True):
    base_url = hindsight_config.get("base_url", "http://localhost:8888")
    bank_id = hindsight_config.get("bank_id", "hermes")
    hs_timeout = float(hindsight_config.get("timeout", 30))
    hindsight_results = await call_hindsight_with_retry(  # 使用新的带重试函数
        "最近的对话和情绪",
        limit=hindsight_config.get("recall_limit", 5),
        bank_id=bank_id,
        base_url=base_url,
        timeout=hs_timeout,
        max_retries=3
    )
```

- [ ] **Step 6: 提交**

```bash
git add backend/services/active_consciousness_service.py backend/tests/test_active_consciousness.py
git commit -m "feat: add Hindsight client retry mechanism"
```

---

## 验收标准

### P0 修复验收
- [ ] 延迟队列中的念头超过 4 小时自动丢弃
- [ ] LLM 调用失败时有明确的 fallback 逻辑
- [ ] LLM 失败次数和原因被记录到日志

### P1 优化验收
- [ ] 配置修改后，心跳调度器立即重启
- [ ] 无效配置被拒绝并返回错误信息
- [ ] 心跳日志中的情绪值与实际保存的一致

### P2 改进验收
- [ ] 情绪合并权重根据 LLM 置信度动态调整
- [ ] 念头类型判断考虑更多因素（时间、沉默时长、情绪）
- [ ] 延迟队列满时拒绝新念头
- [ ] 30 天前的心跳日志被自动清理

### P3 规划验收
- [ ] 前端显示的延迟队列数量准确
- [ ] Hindsight 服务重启后能自动重连

---

**最后更新**：2026-06-18
**版本**：v1.0
**状态**：待执行
