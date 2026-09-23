"""防复读粗筛测试"""
from services.thought_engine import _bigram_jaccard, _is_repetitive


class TestAntiRepeat:
    def test_identical_texts_high_overlap(self):
        assert _bigram_jaccard("今天天气不错", "今天天气不错") == 1.0

    def test_different_texts_low_overlap(self):
        assert _bigram_jaccard("今天天气不错", "我想吃火锅了") < 0.3

    def test_similar_topic_flagged(self):
        recent = ["今天天气真好呀", "天气不错适合出门"]
        assert _is_repetitive("今天天气不错", recent, threshold=0.6) is True

    def test_fresh_topic_passes(self):
        recent = ["今天天气真好呀", "天气不错适合出门"]
        assert _is_repetitive("楼下的猫又来了", recent, threshold=0.6) is False

    def test_empty_recent_passes(self):
        assert _is_repetitive("随便什么", [], threshold=0.6) is False
