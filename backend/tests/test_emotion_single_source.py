"""情绪单一真相源测试：模板变量的情绪三轴来自 EmotionState"""
from unittest.mock import patch, MagicMock
import inspect

import models.active_consciousness as m


class TestSingleSource:
    @patch("services.passive_consciousness_service.get_emotion_state")
    def test_template_valence_reads_emotion_state(self, mock_state):
        """模板 {valence} 必须读 EmotionState，而非关系六维"""
        from services.passive_consciousness_service import PassiveConsciousnessService
        st = MagicMock()
        st.to_dict.return_value = {"valence": 0.42, "arousal": 0.1, "social": 0.3, "dominant": "calm", "label": "平静"}
        mock_state.return_value = st
        fn = PassiveConsciousnessService._build_emotion_context
        ctx = fn()
        assert abs(ctx["valence"] - 0.42) < 1e-6

    def test_relation_schema_has_no_valence(self):
        """关系维度 schema 不再定义 valence/arousal/social"""
        names = []
        for obj in vars(m).values():
            if not (inspect.isclass(obj) and obj.__module__ == m.__name__):
                continue
            # 情绪三轴只属于 EmotionState，扫描时跳过情绪类
            if "Emotion" in obj.__name__:
                continue
            ann = getattr(obj, "model_fields", None) or getattr(obj, "__annotations__", {})
            names += list(ann)
        rel = [n for n in names if n in ("affection", "trust", "heat")]
        dup = [n for n in names if n in ("valence", "arousal", "social")]
        assert rel and not dup
