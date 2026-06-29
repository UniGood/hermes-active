# v0.2.1 全面验证 + 日志监控任务

## ⚠️ 严格约束

### 绝对不能动的文件
- `backend/models/passive_consciousness.py`
- `backend/models/passive_consciousness_log.py`
- `backend/services/passive_consciousness_service.py`
- `backend/routers/passive_consciousness.py`
- `frontend/src/views/PassiveConsciousness.vue`
- `frontend/src/api/passive_consciousness.js`

### 可以修改的文件
- `backend/services/active_consciousness_service.py`
- `backend/tests/test_v021_emotion.py`（新建）
- `backend/tests/test_v021_decision.py`（新建）
- `backend/tests/test_v021_delay_queue.py`（新建）

---

## 任务一：验证流程闭环

### 1.1 情绪状态生命周期验证

验证从创建到持久化的完整闭环：

```
读取(get_emotion_state) → 演化(evolve_emotion) → LLM评估(evaluate_emotion_with_llm) 
→ 合并(merge_emotion) → 持久化(update_emotion_state) → 下次心跳读取
```

**需要验证的点：**
- [ ] `get_emotion_state()` 能正确读取存储的情绪
- [ ] `evolve_emotion()` 演化后值在 [0,1] 范围内
- [ ] `evaluate_emotion_with_llm()` 返回 EmotionState 对象
- [ ] `merge_emotion()` 加权计算正确（0.4*演化 + 0.6*LLM）
- [ ] `update_emotion_state()` 能正确持久化到 configs 表
- [ ] 下次心跳能读取到上次保存的情绪
- [ ] 情绪过期检测 `is_stale()` 工作正常

### 1.2 念头系统流程验证

验证念头从生成到存储的完整闭环：

```
生成念头 → 判断类型(determine_thought_type) → 决策(make_decision_v2)
→ auto_send: 生成消息 → 发送 → 存入Hindsight(retain_thought_to_hindsight)
→ delay_send: 入队(add_to_delay_queue)
→ memory: 存入Hindsight
→ skip: 仅日志
```

**需要验证的点：**
- [ ] `determine_thought_type()` 正确判断6种类型
- [ ] `make_decision_v2()` 返回正确的 decision_type
- [ ] `retain_thought_to_hindsight()` 标签包含：active_consciousness, thought, 念头类型, 主导情绪
- [ ] `add_to_delay_queue()` 正确入队
- [ ] 发送成功后自动触发 Hindsight 存储

### 1.3 延迟队列流程验证

验证延迟队列的完整生命周期：

```
入队(add_to_delay_queue) → 心跳时重评估(reevaluate_delayed_thoughts)
→ score > send_threshold: 升级为发送 → 从队列移除
→ score < 0.1: 降级为丢弃 → 从队列移除
→ 否则: 保持延迟 → 更新 score
→ 超过 max_retry: 自动丢弃
```

**需要验证的点：**
- [ ] `get_delayed_thoughts()` 正确读取队列
- [ ] `save_delayed_thoughts()` 正确保存队列
- [ ] `reevaluate_delayed_thoughts()` 返回 {sent, discarded, kept} 统计
- [ ] 发送成功后存入 Hindsight
- [ ] 超过 max_retry 自动丢弃
- [ ] 队列大小限制 max_queue_size 生效

---

## 任务二：完善监控日志

### 2.1 情绪演化日志

**位置**: `evolve_emotion()` 函数

**需要添加的日志：**
```python
logger.info("情绪演化开始: input=(valence=%.3f, arousal=%.3f, social_need=%.3f), minutes=%.1f",
            last_state.valence, last_state.arousal, last_state.social_need, minutes_since_update)

logger.info("情绪演化完成: output=(valence=%.3f, arousal=%.3f, dominant=%s, social_need=%.3f)",
            new_valence, new_arousal, new_dominant, new_social_need)
```

### 2.2 情绪合并日志

**位置**: `merge_emotion()` 函数

**需要添加的日志：**
```python
logger.info("情绪合并: evolved=(%.3f,%.3f,%s) + llm=(%.3f,%.3f,%s) → merged=(%.3f,%.3f,%s), weights=(%.1f,%.1f)",
            evolved.valence, evolved.arousal, evolved.dominant,
            llm_assessed.valence, llm_assessed.arousal, llm_assessed.dominant,
            merged_valence, merged_arousal, merged_dominant,
            weight_evolved, weight_llm)
```

### 2.3 决策计算日志

**位置**: `make_decision_v2()` 函数

**需要添加的日志：**
```python
logger.info("决策计算: intensity=%.3f, time_fitness=%.3f(%s), silence_factor=%.3f, frequency_limit=%.3f",
            intensity, time_fitness, time_label, silence_factor, frequency_limit)

logger.info("决策结果: score=%.3f, decision=%s, threshold(send=%.3f, delay=%.3f, memory=%.3f)",
            score, decision, send_threshold, delay_threshold, memory_threshold)
```

### 2.4 Hindsight 存储日志

**位置**: `retain_thought_to_hindsight()` 函数

**需要添加的日志：**
```python
logger.info("Hindsight 存储检查: intensity=%.3f, threshold=%.3f, should_retain=%s",
            intensity, retain_threshold, should_retain)

logger.info("Hindsight 存储成功: tags=%s, content=%s", tags, content[:50])

logger.info("Hindsight 存储跳过: 未达到存储条件")
```

### 2.5 延迟队列日志

**位置**: `add_to_delay_queue()` 和 `reevaluate_delayed_thoughts()` 函数

**需要添加的日志：**
```python
# 入队
logger.info("延迟队列入队: id=%d, type=%s, score=%.3f, content=%s",
            new_thought.id, thought_type, score, content[:50])

# 重评估
logger.info("延迟队列重评估开始: 队列长度=%d", len(delayed_thoughts))

logger.info("延迟队列重评估: id=%d, old_score=%.3f, new_score=%.3f, decision=%s",
            thought.id, thought.score, new_score, decision)

logger.info("延迟队列重评估完成: stats=%s", stats)
```

### 2.6 LLM 调用日志

**位置**: `evaluate_emotion_with_llm()` 函数

**需要添加的日志：**
```python
logger.info("LLM 情绪评估开始")

logger.info("LLM 情绪评估完成: duration=%dms, response=%s", duration_ms, raw[:200])

logger.warning("LLM 情绪评估失败，使用默认值: %s", e)
```

### 2.7 心跳流程日志

**位置**: `run_heartbeat()` 函数

**需要添加的关键日志：**
```python
logger.info("=== 心跳开始 ===")

logger.info("情绪读取: valence=%.3f, arousal=%.3f, dominant=%s",
            emotion_state.valence, emotion_state.arousal, emotion_state.dominant)

logger.info("时间窗口: fitness=%.3f, label=%s", time_fitness, time_label)

logger.info("=== 心跳完成 === duration=%dms, decision=%s", duration_ms, decision_type)
```

---

## 任务三：编写单元测试

### 3.1 情绪演化测试

**文件**: `backend/tests/test_v021_emotion.py`

```python
"""v0.2.1 情绪演化单元测试"""
import pytest
from datetime import datetime, timedelta
from models.active_consciousness import EmotionState, DominantEmotion

class TestEmotionState:
    """EmotionState 数据类测试"""
    
    def test_default_values(self):
        state = EmotionState()
        assert state.valence == 0.5
        assert state.arousal == 0.3
        assert state.dominant == "calm"
        assert state.social_need == 0.3
    
    def test_boundary_clamping(self):
        state = EmotionState(valence=1.5, arousal=-0.1, social_need=2.0)
        assert state.valence == 1.0
        assert state.arousal == 0.0
        assert state.social_need == 1.0
    
    def test_to_dict(self):
        state = EmotionState(valence=0.6, arousal=0.4)
        d = state.to_dict()
        assert d["valence"] == 0.6
        assert d["arousal"] == 0.4
        assert "updated_at" in d
    
    def test_from_dict(self):
        d = {"valence": 0.7, "arousal": 0.5, "dominant": "happy"}
        state = EmotionState.from_dict(d)
        assert state.valence == 0.7
        assert state.dominant == "happy"
    
    def test_intensity(self):
        state = EmotionState(valence=0.6, arousal=0.4, social_need=0.3)
        expected = (0.6 + 0.4 + 0.3) / 3
        assert abs(state.intensity() - expected) < 0.01
    
    def test_is_stale_false(self):
        state = EmotionState(updated_at=datetime.now().isoformat())
        assert state.is_stale(minutes=60) == False
    
    def test_is_stale_true(self):
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        state = EmotionState(updated_at=old_time)
        assert state.is_stale(minutes=60) == True


class TestEvolveEmotion:
    """情绪演化测试"""
    
    def test_no_evolution(self):
        """无时间流逝不演化"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5, social_need=0.3)
        evolved = evolve_emotion(last, minutes_since_update=0)
        assert evolved.arousal == 0.5
        assert evolved.social_need == 0.3
    
    def test_arousal_decay(self):
        """arousal 随时间衰减"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.8)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.arousal < 0.8
    
    def test_social_need_growth(self):
        """social_need 随时间增长"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(social_need=0.2)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.social_need > 0.2
    
    def test_valence_regression_high(self):
        """高效价回归中性"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(valence=0.8)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.valence < 0.8
    
    def test_valence_regression_low(self):
        """低效价回归中性"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(valence=0.2)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.valence > 0.2
    
    def test_boundary_minutes_negative(self):
        """负数时间视为0"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5)
        evolved = evolve_emotion(last, minutes_since_update=-10)
        assert evolved.arousal == 0.5
    
    def test_boundary_minutes_max(self):
        """超过24小时截断"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5)
        evolved = evolve_emotion(last, minutes_since_update=2000)
        assert evolved.arousal >= 0.1  # 最低值


class TestCalculateDominant:
    """主导情绪计算测试"""
    
    def test_high_social_need_positive(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.6, 0.5, 0.8) == "yearning"
    
    def test_high_social_need_negative(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.4, 0.5, 0.8) == "anxious"
    
    def test_medium_social_need_positive(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.6, 0.5, 0.6) == "longing"
    
    def test_low_arousal(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.5, 0.2, 0.3) == "calm"
    
    def test_high_valence_high_arousal(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.8, 0.7, 0.3) == "happy"
    
    def test_high_valence_low_arousal(self):
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.8, 0.5, 0.3) == "content"


class TestMergeEmotion:
    """情绪合并测试"""
    
    def test_normal_merge(self):
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(valence=0.4, arousal=0.3, social_need=0.2)
        llm = EmotionState(valence=0.6, arousal=0.5, social_need=0.4)
        merged = merge_emotion(evolved, llm)
        # 权重 0.4 + 0.6
        expected_valence = 0.4 * 0.4 + 0.6 * 0.6
        assert abs(merged.valence - expected_valence) < 0.01
    
    def test_high_arousal_llm_uses_llm_dominant(self):
        """LLM 高唤醒度时采用其主导情绪"""
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(dominant="calm")
        llm = EmotionState(arousal=0.7, dominant="happy")
        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "happy"
    
    def test_low_arousal_llm_keeps_evolved_dominant(self):
        """LLM 低唤醒度时保留演化值的主导情绪"""
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(dominant="longing")
        llm = EmotionState(arousal=0.5, dominant="calm")
        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "longing"
```

### 3.2 决策矩阵测试

**文件**: `backend/tests/test_v021_decision.py`

```python
"""v0.2.1 决策矩阵单元测试"""
import pytest
from unittest.mock import patch
from models.active_consciousness import EmotionState


class TestTimeFitness:
    """时间权重测试"""
    
    @patch('services.active_consciousness_service.datetime')
    def test_morning_window(self, mock_datetime):
        from services.active_consciousness_service import get_time_fitness
        mock_datetime.now.return_value = datetime(2026, 6, 16, 8, 0)
        fitness, label = get_time_fitness()
        assert fitness == 1.0
        assert label == "早安窗口"
    
    @patch('services.active_consciousness_service.datetime')
    def test_work_time(self, mock_datetime):
        from services.active_consciousness_service import get_time_fitness
        mock_datetime.now.return_value = datetime(2026, 6, 16, 10, 0)
        fitness, label = get_time_fitness()
        assert fitness == 0.8
        assert label == "工作时间"
    
    @patch('services.active_consciousness_service.datetime')
    def test_deep_night(self, mock_datetime):
        from services.active_consciousness_service import get_time_fitness
        mock_datetime.now.return_value = datetime(2026, 6, 16, 23, 30)
        fitness, label = get_time_fitness()
        assert fitness == 0.3
        assert label == "深夜"


class TestDecisionV2:
    """多维度决策测试"""
    
    def test_high_score_auto_send(self):
        """高分自动发送"""
        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 0}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        with patch('services.active_consciousness_service.get_time_fitness', return_value=(1.0, "下班时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision == "auto_send"
            assert score > 0.6
    
    def test_medium_score_delay_send(self):
        """中分延迟发送"""
        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 120}, "hour_sent_count": 1}
        emotion = EmotionState(valence=0.5, arousal=0.4, social_need=0.3)
        
        with patch('services.active_consciousness_service.get_time_fitness', return_value=(0.8, "工作时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision == "delay_send"
            assert 0.3 < score <= 0.6
    
    def test_low_score_memory(self):
        """低分存为记忆"""
        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 30}, "hour_sent_count": 2}
        emotion = EmotionState(valence=0.3, arousal=0.2, social_need=0.2)
        
        with patch('services.active_consciousness_service.get_time_fitness', return_value=(0.3, "深夜")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision in ("memory", "skip")
    
    def test_frequency_limit(self):
        """频率限制生效"""
        from services.active_consciousness_service import make_decision_v2
        config = {
            "decision": {"send_threshold": 0.6, "max_per_hour": 2}
        }
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 2}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        
        with patch('services.active_consciousness_service.get_time_fitness', return_value=(1.0, "下班时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            # 频率限制应该降低分数
            assert score < 0.6
```

### 3.3 延迟队列测试

**文件**: `backend/tests/test_v021_delay_queue.py`

```python
"""v0.2.1 延迟队列单元测试"""
import pytest
from datetime import datetime
from models.active_consciousness import EmotionState, DelayedThought


class TestDelayedThought:
    """DelayedThought 数据类测试"""
    
    def test_to_dict(self):
        thought = DelayedThought(id=1, content="测试", thought_type="emotion", score=0.45, created_at="2026-06-16T10:30:00")
        d = thought.to_dict()
        assert d["id"] == 1
        assert d["content"] == "测试"
        assert d["score"] == 0.45
    
    def test_from_dict(self):
        d = {"id": 1, "content": "测试", "thought_type": "emotion", "score": 0.45, "created_at": "2026-06-16T10:30:00"}
        thought = DelayedThought.from_dict(d)
        assert thought.id == 1
        assert thought.score == 0.45


class TestThoughtType:
    """念头类型测试"""
    
    def test_memory_type(self):
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        hindsight = [{"text": "你说过喜欢看电影"}]
        result = determine_thought_type(status, emotion, hindsight, None)
        assert result == "memory"
    
    def test_emotion_type(self):
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)
        result = determine_thought_type(status, emotion, [], None)
        assert result == "emotion"
    
    def test_silence_type(self):
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 180}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        result = determine_thought_type(status, emotion, [], None)
        assert result == "silence"
```

---

## 验收标准

1. [ ] 所有单元测试通过
2. [ ] 情绪生命周期闭环验证通过
3. [ ] 念头系统流程验证通过
4. [ ] 延迟队列流程验证通过
5. [ ] 日志覆盖所有关键节点
6. [ ] 被动意识文件未被修改
7. [ ] Python 语法检查通过

---

## 执行步骤

1. 添加监控日志到所有关键函数
2. 创建测试文件
3. 运行测试验证
4. 检查日志输出是否完整
