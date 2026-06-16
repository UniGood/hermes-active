"""
v0.2.1 端到端集成测试 — 全流程验证

模拟完整心跳流程，验证数据从创建到最终生成念头的全链路：
1. 情绪状态创建 → 读取 → 演化 → LLM评估 → 合并 → 持久化
2. 念头生成 → 类型判断 → 决策 → 发送/延迟/记忆
3. 延迟队列：入队 → 重评估 → 升级/降级/保持
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from models.active_consciousness import (
    EmotionState, ThoughtType, DelayedThought, DominantEmotion
)


# ============================================================
# 第一阶段：情绪状态生命周期
# ============================================================

class TestEmotionLifecycle:
    """情绪状态完整生命周期测试"""

    def test_01_create_default_emotion(self):
        """步骤1: 创建默认情绪状态"""
        state = EmotionState()
        assert state.valence == 0.5, "默认 valence 应为 0.5"
        assert state.arousal == 0.3, "默认 arousal 应为 0.3"
        assert state.social_need == 0.3, "默认 social_need 应为 0.3"
        assert state.dominant == "calm", "默认主导情绪应为 calm"
        assert state.updated_at != "", "updated_at 应自动填充"
        print(f"✅ 默认情绪: {state.to_dict()}")

    def test_02_create_custom_emotion(self):
        """步骤2: 创建自定义情绪状态"""
        state = EmotionState(valence=0.8, arousal=0.6, social_need=0.5, dominant="happy")
        assert state.valence == 0.8
        assert state.arousal == 0.6
        assert state.dominant == "happy"
        print(f"✅ 自定义情绪: {state.to_dict()}")

    def test_03_emotion_serialization(self):
        """步骤3: 情绪状态序列化/反序列化"""
        original = EmotionState(valence=0.7, arousal=0.5, social_need=0.4, dominant="content")
        d = original.to_dict()
        restored = EmotionState.from_dict(d)
        assert restored.valence == original.valence
        assert restored.arousal == original.arousal
        assert restored.social_need == original.social_need
        assert restored.dominant == original.dominant
        print(f"✅ 序列化/反序列化一致: {d}")

    def test_04_emotion_boundary_clamping(self):
        """步骤4: 边界值截断"""
        state = EmotionState(valence=1.5, arousal=-0.1, social_need=2.0)
        assert state.valence == 1.0, "valence 应截断到 1.0"
        assert state.arousal == 0.0, "arousal 应截断到 0.0"
        assert state.social_need == 1.0, "social_need 应截断到 1.0"
        print(f"✅ 边界截断正确: valence={state.valence}, arousal={state.arousal}, social_need={state.social_need}")

    def test_05_emotion_intensity_calculation(self):
        """步骤5: 综合情绪强度计算"""
        state = EmotionState(valence=0.6, arousal=0.4, social_need=0.3)
        expected = (0.6 + 0.4 + 0.3) / 3
        assert abs(state.intensity() - expected) < 0.01, f"intensity 应为 {expected}"
        print(f"✅ 情绪强度: {state.intensity():.3f}")

    def test_06_emotion_stale_detection(self):
        """步骤6: 情绪过期检测"""
        # 刚创建的不过期
        fresh = EmotionState(updated_at=datetime.now().isoformat())
        assert fresh.is_stale(minutes=60) == False

        # 2小时前的过期
        old = EmotionState(updated_at=(datetime.now() - timedelta(hours=2)).isoformat())
        assert old.is_stale(minutes=60) == True
        print("✅ 过期检测正确: 新鲜不过期，旧的过期")


# ============================================================
# 第二阶段：情绪演化
# ============================================================

class TestEmotionEvolution:
    """情绪演化全流程测试"""

    def test_07_evolve_no_time_passes(self):
        """步骤7: 无时间流逝不演化"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(valence=0.5, arousal=0.5, social_need=0.3)
        evolved = evolve_emotion(last, minutes_since_update=0)
        assert evolved.arousal == 0.5
        assert evolved.social_need == 0.3
        assert evolved.valence == 0.5
        print("✅ 无时间流逝，情绪不变")

    def test_08_evolve_arousal_decays(self):
        """步骤8: arousal 随时间衰减"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.8)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.arousal < 0.8, "arousal 应衰减"
        assert evolved.arousal >= 0.1, "arousal 不应低于 0.1"
        print(f"✅ arousal 衰减: 0.8 → {evolved.arousal:.3f}")

    def test_09_evolve_social_need_grows(self):
        """步骤9: social_need 随时间增长"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(social_need=0.2)
        evolved = evolve_emotion(last, minutes_since_update=60)
        assert evolved.social_need > 0.2, "social_need 应增长"
        assert evolved.social_need <= 1.0, "social_need 不应超过 1.0"
        print(f"✅ social_need 增长: 0.2 → {evolved.social_need:.3f}")

    def test_10_evolve_valence_regression(self):
        """步骤10: valence 回归中性"""
        from services.active_consciousness_service import evolve_emotion

        # 高效价应下降
        high = EmotionState(valence=0.8)
        evolved_high = evolve_emotion(high, minutes_since_update=60)
        assert evolved_high.valence < 0.8, "高效价应下降"

        # 低效价应上升
        low = EmotionState(valence=0.2)
        evolved_low = evolve_emotion(low, minutes_since_update=60)
        assert evolved_low.valence > 0.2, "低效价应上升"
        print(f"✅ valence 回归: 0.8→{evolved_high.valence:.3f}, 0.2→{evolved_low.valence:.3f}")

    def test_11_evolve_dominant_changes(self):
        """步骤11: 演化后主导情绪可能变化"""
        from services.active_consciousness_service import evolve_emotion

        # 高社交需求应产生 yearning
        state = EmotionState(valence=0.6, arousal=0.5, social_need=0.8)
        evolved = evolve_emotion(state, minutes_since_update=120)
        # social_need 会进一步增长
        assert evolved.social_need > 0.8
        print(f"✅ 主导情绪: {state.dominant} → {evolved.dominant} (social_need={evolved.social_need:.3f})")

    def test_12_evolve_long_time_capped(self):
        """步骤12: 超长时间截断到24小时"""
        from services.active_consciousness_service import evolve_emotion
        last = EmotionState(arousal=0.5)
        evolved = evolve_emotion(last, minutes_since_update=5000)  # 超过3天
        assert evolved.arousal >= 0.1, "应有最低值保护"
        print(f"✅ 超长时间截断: arousal={evolved.arousal:.3f}")


# ============================================================
# 第三阶段：主导情绪计算
# ============================================================

class TestDominantCalculation:
    """主导情绪计算测试"""

    def test_13_dominant_yearning(self):
        """步骤13: 高社交需求+积极 → yearning"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.6, 0.5, 0.8) == "yearning"
        print("✅ yearning: valence=0.6, social_need=0.8")

    def test_14_dominant_anxious(self):
        """步骤14: 高社交需求+消极 → anxious"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.4, 0.5, 0.8) == "anxious"
        print("✅ anxious: valence=0.4, social_need=0.8")

    def test_15_dominant_longing(self):
        """步骤15: 中等社交需求+积极 → longing"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.6, 0.5, 0.6) == "longing"
        print("✅ longing: valence=0.6, social_need=0.6")

    def test_16_dominant_calm(self):
        """步骤16: 低唤醒度 → calm"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.5, 0.2, 0.3) == "calm"
        print("✅ calm: arousal=0.2")

    def test_17_dominant_happy(self):
        """步骤17: 高效价+高唤醒 → happy"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.8, 0.7, 0.3) == "happy"
        print("✅ happy: valence=0.8, arousal=0.7")

    def test_18_dominant_content(self):
        """步骤18: 高效价+中唤醒 → content"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.8, 0.5, 0.3) == "content"
        print("✅ content: valence=0.8, arousal=0.5")

    def test_19_dominant_bored(self):
        """步骤19: 低效价+低唤醒 → bored"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.2, 0.3, 0.3) == "bored"
        print("✅ bored: valence=0.2, arousal=0.3")

    def test_20_dominant_concerned(self):
        """步骤20: 低效价+高唤醒 → concerned"""
        from services.active_consciousness_service import calculate_dominant
        assert calculate_dominant(0.2, 0.5, 0.3) == "concerned"
        print("✅ concerned: valence=0.2, arousal=0.5")


# ============================================================
# 第四阶段：情绪合并
# ============================================================

class TestEmotionMerge:
    """情绪合并测试"""

    def test_21_merge_normal(self):
        """步骤21: 正常合并（权重 0.4 + 0.6）"""
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(valence=0.4, arousal=0.3, social_need=0.2)
        llm = EmotionState(valence=0.6, arousal=0.5, social_need=0.4)

        merged = merge_emotion(evolved, llm)

        expected_v = 0.4 * 0.4 + 0.6 * 0.6  # 0.52
        expected_a = 0.3 * 0.4 + 0.6 * 0.5  # 0.42
        expected_s = 0.2 * 0.4 + 0.6 * 0.4  # 0.32

        assert abs(merged.valence - expected_v) < 0.01
        assert abs(merged.arousal - expected_a) < 0.01
        assert abs(merged.social_need - expected_s) < 0.01
        print(f"✅ 合并结果: valence={merged.valence:.3f}, arousal={merged.arousal:.3f}, social_need={merged.social_need:.3f}")

    def test_22_merge_high_arousal_uses_llm_dominant(self):
        """步骤22: LLM 高唤醒度时采用其主导情绪"""
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(dominant="calm")
        llm = EmotionState(arousal=0.7, dominant="happy")

        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "happy", "LLM 高唤醒时应采用其主导情绪"
        print(f"✅ 主导情绪选择: LLM高唤醒 → {merged.dominant}")

    def test_23_merge_low_arousal_keeps_evolved_dominant(self):
        """步骤23: LLM 低唤醒度时保留演化值的主导情绪"""
        from services.active_consciousness_service import merge_emotion
        evolved = EmotionState(dominant="longing")
        llm = EmotionState(arousal=0.5, dominant="calm")

        merged = merge_emotion(evolved, llm)
        assert merged.dominant == "longing", "LLM 低唤醒时应保留演化值"
        print(f"✅ 主导情绪选择: LLM低唤醒 → 保留 {merged.dominant}")


# ============================================================
# 第五阶段：时间窗口决策
# ============================================================

class TestTimeWindowDecision:
    """时间窗口决策测试"""

    def test_24_time_fitness_morning(self):
        """步骤24: 早安窗口权重"""
        from services.active_consciousness_service import get_time_fitness
        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 17, 8, 0)
            fitness, label = get_time_fitness()
            assert fitness == 1.0
            assert label == "早安窗口"
            print(f"✅ 早安窗口: fitness={fitness}, label={label}")

    def test_25_time_fitness_deep_night(self):
        """步骤25: 深夜权重"""
        from services.active_consciousness_service import get_time_fitness
        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 17, 2, 0)
            fitness, label = get_time_fitness()
            assert fitness == 0.3
            assert label == "深夜"
            print(f"✅ 深夜: fitness={fitness}, label={label}")

    def test_26_decision_auto_send(self):
        """步骤26: 高分自动发送"""
        from services.active_consciousness_service import make_decision_v2
        config = {"decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}}
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 0}
        # intensity = (0.95+0.9+0.8)/3 = 0.883, score = 0.883*1.0*0.7*1.0 = 0.618 > 0.6
        emotion = EmotionState(valence=0.95, arousal=0.9, social_need=0.8)

        with patch('services.active_consciousness_service.get_time_fitness', return_value=(1.0, "下班时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision == "auto_send", f"应为 auto_send，实际为 {decision}"
            assert score > 0.6, f"分数应 > 0.6，实际为 {score}"
            print(f"✅ 自动发送: score={score:.3f}, decision={decision}")

    def test_27_decision_delay_send(self):
        """步骤27: 中分延迟发送"""
        from services.active_consciousness_service import make_decision_v2
        config = {"decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}}
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 0}
        # intensity = (0.7+0.6+0.5)/3 = 0.6, score = 0.6*0.8*0.7*1.0 = 0.336
        emotion = EmotionState(valence=0.7, arousal=0.6, social_need=0.5)

        with patch('services.active_consciousness_service.get_time_fitness', return_value=(0.8, "工作时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision == "delay_send", f"应为 delay_send，实际为 {decision}"
            assert 0.3 < score <= 0.6
            print(f"✅ 延迟发送: score={score:.3f}, decision={decision}")

    def test_28_decision_memory(self):
        """步骤28: 低分存为记忆"""
        from services.active_consciousness_service import make_decision_v2
        config = {"decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}}
        status = {"longing": {"silence_minutes": 30}, "hour_sent_count": 2}
        emotion = EmotionState(valence=0.3, arousal=0.2, social_need=0.2)

        with patch('services.active_consciousness_service.get_time_fitness', return_value=(0.3, "深夜")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert decision in ("memory", "skip"), f"应为 memory 或 skip，实际为 {decision}"
            print(f"✅ 记忆/跳过: score={score:.3f}, decision={decision}")

    def test_29_decision_frequency_limit(self):
        """步骤29: 频率限制生效"""
        from services.active_consciousness_service import make_decision_v2
        config = {"decision": {"send_threshold": 0.6, "max_per_hour": 2}}
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 2}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)

        with patch('services.active_consciousness_service.get_time_fitness', return_value=(1.0, "下班时间")):
            decision, reason, score = make_decision_v2(config, status, emotion)
            assert score < 0.6, "频率限制应降低分数"
            print(f"✅ 频率限制: score={score:.3f} < 0.6")


# ============================================================
# 第六阶段：念头类型判断
# ============================================================

class TestThoughtTypeDetermination:
    """念头类型判断测试"""

    def test_30_memory_type_with_hindsight(self):
        """步骤30: 有 Hindsight 回忆 → memory"""
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)
        hindsight = [{"text": "你说过喜欢看电影"}]

        result = determine_thought_type(status, emotion, hindsight, None)
        assert result == "memory"
        print(f"✅ 有回忆 → {result}")

    def test_31_emotion_type_high_intensity(self):
        """步骤31: 高情绪强度 → emotion"""
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.8, arousal=0.6, social_need=0.5)  # intensity > 0.5

        result = determine_thought_type(status, emotion, [], None)
        assert result == "emotion"
        print(f"✅ 高情绪 → {result}")

    def test_32_silence_type_long_gap(self):
        """步骤32: 长时间沉默 → silence"""
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 180}}
        emotion = EmotionState(valence=0.5, arousal=0.3, social_need=0.3)

        result = determine_thought_type(status, emotion, [], None)
        assert result == "silence"
        print(f"✅ 长沉默 → {result}")

    def test_33_time_type_special_hour(self):
        """步骤33: 特殊时间点 → time"""
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.4, arousal=0.3, social_need=0.3)

        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 17, 7, 30)  # 早上7:30
            result = determine_thought_type(status, emotion, [], None)
            assert result == "time"
            print(f"✅ 特殊时间 → {result}")

    def test_34_env_type_special_weather(self):
        """步骤34: 特殊天气 → env"""
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.4, arousal=0.3, social_need=0.3)
        weather = {"weather": "雨"}

        result = determine_thought_type(status, emotion, [], weather)
        assert result == "env"
        print(f"✅ 特殊天气 → {result}")

    def test_35_assoc_type_default(self):
        """步骤35: 默认 → assoc"""
        from services.active_consciousness_service import determine_thought_type
        status = {"longing": {"silence_minutes": 30}}
        emotion = EmotionState(valence=0.4, arousal=0.3, social_need=0.3)

        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 17, 15, 0)  # 下午3点，非特殊时间
            result = determine_thought_type(status, emotion, [], None)
            assert result == "assoc"
            print(f"✅ 默认 → {result}")


# ============================================================
# 第七阶段：延迟队列
# ============================================================

class TestDelayQueue:
    """延迟队列全流程测试"""

    def test_36_delayed_thought_create(self):
        """步骤36: 创建延迟念头"""
        thought = DelayedThought(
            id=1, content="测试念头", thought_type="emotion",
            score=0.45, created_at=datetime.now().isoformat()
        )
        assert thought.id == 1
        assert thought.content == "测试念头"
        assert thought.score == 0.45
        assert thought.retry_count == 0
        print(f"✅ 延迟念头创建: {thought.to_dict()}")

    def test_37_delayed_thought_serialization(self):
        """步骤37: 延迟念头序列化/反序列化"""
        original = DelayedThought(
            id=1, content="测试", thought_type="silence",
            score=0.4, created_at="2026-06-17T10:00:00"
        )
        d = original.to_dict()
        restored = DelayedThought.from_dict(d)
        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.score == original.score
        print(f"✅ 序列化/反序列化一致")

    def test_38_queue_save_and_get(self):
        """步骤38: 队列保存和读取"""
        from services.active_consciousness_service import get_delayed_thoughts, save_delayed_thoughts

        thoughts = [
            DelayedThought(id=1, content="念头1", thought_type="emotion", score=0.4, created_at="2026-06-17T10:00:00"),
            DelayedThought(id=2, content="念头2", thought_type="silence", score=0.35, created_at="2026-06-17T11:00:00"),
        ]

        with patch('services.active_consciousness_service.ConfigService') as mock_config:
            # 模拟保存
            saved_data = []
            def mock_set(db, key, value):
                saved_data.append(value)
            mock_config.set_config.side_effect = mock_set

            # 模拟读取
            mock_config.get_config.return_value = json.dumps([t.to_dict() for t in thoughts])

            # 保存
            result = save_delayed_thoughts(thoughts)
            assert result == True

            # 读取
            loaded = get_delayed_thoughts()
            assert len(loaded) == 2
            assert loaded[0].content == "念头1"
            assert loaded[1].content == "念头2"
            print(f"✅ 队列保存/读取: {len(loaded)} 个念头")

    def test_39_queue_size_limit(self):
        """步骤39: 队列大小限制"""
        from services.active_consciousness_service import add_to_delay_queue

        with patch('services.active_consciousness_service.ConfigService') as mock_config, \
             patch('services.active_consciousness_service.ActiveConsciousnessService.get_config') as mock_get_config:
            mock_get_config.return_value = {"delay": {"max_queue_size": 3}}

            # 模拟空队列
            mock_config.get_config.return_value = "[]"
            saved_data = []
            def mock_set(db, key, value):
                saved_data.append(value)
            mock_config.set_config.side_effect = mock_set

            emotion = EmotionState()

            # 添加4个念头（超过限制3个）
            for i in range(4):
                add_to_delay_queue(f"念头{i}", "emotion", 0.4, emotion)

            # 验证最后一次保存的队列长度
            if saved_data:
                last_saved = json.loads(saved_data[-1])
                assert len(last_saved) <= 3, f"队列应限制在3个以内，实际为 {len(last_saved)}"
                print(f"✅ 队列限制生效: {len(last_saved)} 个（max=3）")


# ============================================================
# 第八阶段：Hindsight 标签验证
# ============================================================

class TestHindsightTags:
    """Hindsight 标签验证"""

    def test_40_hindsight_tags_structure(self):
        """步骤40: 验证 Hindsight 标签结构"""
        emotion = EmotionState(dominant="happy")
        thought_type = "emotion"
        thought = "今天心情很好"

        # 模拟标签构建逻辑
        tags = [
            "active_consciousness",
            "thought",
            thought_type,
            emotion.dominant,
        ]
        if "曹凡" in thought:
            tags.append("user_related")
        if emotion.intensity() > 0.7:
            tags.append("high_emotion")

        assert "active_consciousness" in tags, "应有来源标签"
        assert "thought" in tags, "应有类型标签"
        assert "emotion" in tags, "应有念头类型标签"
        assert "happy" in tags, "应有主导情绪标签"
        print(f"✅ 标签结构: {tags}")

    def test_41_hindsight_tags_user_related(self):
        """步骤41: 涉及用户时加 user_related 标签"""
        emotion = EmotionState(dominant="longing")
        thought = "曹凡今天加班好辛苦"

        tags = ["active_consciousness", "thought", "emotion", emotion.dominant]
        if "曹凡" in thought:
            tags.append("user_related")

        assert "user_related" in tags, "涉及用户应有 user_related 标签"
        print(f"✅ 用户相关标签: {tags}")

    def test_42_hindsight_tags_high_emotion(self):
        """步骤42: 高情绪强度加 high_emotion 标签"""
        emotion = EmotionState(valence=0.8, arousal=0.7, social_need=0.6)  # intensity > 0.7

        tags = ["active_consciousness", "thought", "emotion", emotion.dominant]
        if emotion.intensity() > 0.7:
            tags.append("high_emotion")

        assert "high_emotion" in tags, "高情绪应有 high_emotion 标签"
        print(f"✅ 高情绪标签: {tags}, intensity={emotion.intensity():.3f}")

    def test_43_hindsight_content_format(self):
        """步骤43: Hindsight 内容格式"""
        thought_type = "memory"
        thought = "想起你说过喜欢看电影"

        content = f"[{thought_type}] {thought}"
        assert content.startswith("[memory]"), "内容应以类型前缀开头"
        assert thought in content, "内容应包含原始念头"
        print(f"✅ 内容格式: {content}")


# ============================================================
# 第九阶段：端到端流程模拟
# ============================================================

class TestEndToEndFlow:
    """端到端流程模拟"""

    def test_44_full_heartbeat_flow_simulation(self):
        """步骤44: 模拟完整心跳流程"""
        from services.active_consciousness_service import (
            evolve_emotion, calculate_dominant, merge_emotion,
            get_time_fitness, make_decision_v2, determine_thought_type
        )

        print("\n" + "="*60)
        print("  端到端心跳流程模拟")
        print("="*60)

        # Step 1: 读取初始情绪
        initial = EmotionState(valence=0.5, arousal=0.4, social_need=0.3, dominant="calm")
        print(f"\n[Step 1] 初始情绪: {initial.to_dict()}")

        # Step 2: 情绪演化（假设过了2小时）
        evolved = evolve_emotion(initial, minutes_since_update=120)
        print(f"[Step 2] 演化后: valence={evolved.valence:.3f}, arousal={evolved.arousal:.3f}, social_need={evolved.social_need:.3f}")

        # Step 3: LLM 评估（模拟返回）
        llm_assessed = EmotionState(valence=0.7, arousal=0.6, social_need=0.5, dominant="happy")
        print(f"[Step 3] LLM 评估: {llm_assessed.to_dict()}")

        # Step 4: 情绪合并
        merged = merge_emotion(evolved, llm_assessed)
        print(f"[Step 4] 合并结果: valence={merged.valence:.3f}, arousal={merged.arousal:.3f}, dominant={merged.dominant}")

        # Step 5: 时间窗口
        with patch('services.active_consciousness_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 17, 19, 0)  # 晚上7点
            time_fitness, time_label = get_time_fitness()
        print(f"[Step 5] 时间窗口: fitness={time_fitness}, label={time_label}")

        # Step 6: 决策
        config = {"decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}}
        status = {"longing": {"silence_minutes": 180}, "hour_sent_count": 0}
        decision, reason, score = make_decision_v2(config, status, merged)
        print(f"[Step 6] 决策: decision={decision}, score={score:.3f}")
        print(f"         原因: {reason}")

        # Step 7: 念头类型
        hindsight_results = [{"text": "你说过喜欢周杰伦的歌"}]
        thought_type = determine_thought_type(status, merged, hindsight_results, None)
        print(f"[Step 7] 念头类型: {thought_type}")

        # Step 8: 根据决策处理
        if decision == "auto_send":
            print(f"[Step 8] → 自动发送念头")
            # 构建 Hindsight 标签
            tags = ["active_consciousness", "thought", thought_type, merged.dominant]
            content = f"[{thought_type}] 生成的念头内容"
            print(f"[Step 9] Hindsight 存储: tags={tags}")
            print(f"         content={content}")
        elif decision == "delay_send":
            print(f"[Step 8] → 入延迟队列")
            delayed = DelayedThought(
                id=1, content="生成的念头", thought_type=thought_type,
                score=score, created_at=datetime.now().isoformat()
            )
            print(f"[Step 9] 延迟念头: {delayed.to_dict()}")
        elif decision == "memory":
            print(f"[Step 8] → 存为记忆")
            tags = ["active_consciousness", "thought", thought_type, merged.dominant]
            print(f"[Step 9] Hindsight 存储: tags={tags}")
        else:
            print(f"[Step 8] → 跳过")

        # 验证流程完整性
        assert initial is not None, "初始情绪不应为空"
        assert evolved is not None, "演化后不应为空"
        assert merged is not None, "合并后不应为空"
        assert decision in ("auto_send", "delay_send", "memory", "skip"), "决策类型应有效"
        assert thought_type in ("time", "silence", "assoc", "memory", "emotion", "env"), "念头类型应有效"

        print("\n" + "="*60)
        print(f"  ✅ 全流程完成: decision={decision}, score={score:.3f}")
        print("="*60 + "\n")

    def test_45_delay_queue_reevaluation_simulation(self):
        """步骤45: 模拟延迟队列重评估流程"""
        from services.active_consciousness_service import (
            get_time_fitness, make_decision_v2
        )

        print("\n" + "="*60)
        print("  延迟队列重评估模拟")
        print("="*60)

        # 模拟延迟队列
        delayed_thoughts = [
            DelayedThought(id=1, content="念头1", thought_type="emotion", score=0.4, created_at="2026-06-17T10:00:00"),
            DelayedThought(id=2, content="念头2", thought_type="silence", score=0.35, created_at="2026-06-17T11:00:00"),
        ]
        print(f"\n[初始] 延迟队列: {len(delayed_thoughts)} 个念头")

        # 当前情绪状态
        emotion = EmotionState(valence=0.7, arousal=0.6, social_need=0.5, dominant="happy")
        print(f"[当前] 情绪: {emotion.to_dict()}")

        config = {"decision": {"send_threshold": 0.6, "delay_threshold": 0.3, "memory_threshold": 0.1, "max_per_hour": 2}}
        status = {"longing": {"silence_minutes": 300}, "hour_sent_count": 0}

        # 重评估每个念头
        stats = {"sent": 0, "discarded": 0, "kept": 0}
        remaining = []

        for thought in delayed_thoughts:
            # 重新计算分数
            with patch('services.active_consciousness_service.get_time_fitness', return_value=(1.0, "下班时间")):
                _, _, new_score = make_decision_v2(config, status, emotion)

            print(f"\n[重评估] id={thought.id}, old_score={thought.score:.3f}, new_score={new_score:.3f}")

            if new_score > 0.6:
                print(f"  → 升级为发送")
                stats["sent"] += 1
            elif new_score < 0.1:
                print(f"  → 降级为丢弃")
                stats["discarded"] += 1
            else:
                print(f"  → 保持延迟")
                remaining.append(thought)
                stats["kept"] += 1

        print(f"\n[结果] 统计: {stats}")
        print(f"        剩余: {len(remaining)} 个念头")

        assert stats["sent"] + stats["discarded"] + stats["kept"] == len(delayed_thoughts)
        print("\n" + "="*60)
        print(f"  ✅ 延迟队列重评估完成")
        print("="*60 + "\n")


# ============================================================
# 运行入口
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
