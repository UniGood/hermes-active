# Task: 防复读（主动念头的重复过滤）

## STRICT RULES
- ONLY modify: `backend/services/thought_engine.py`、新建 `backend/tests/test_anti_repeat.py`。
- Do NOT touch 其他任何文件。Do NOT modify `backend/config.py`、`models/**`、`routers/**`。Do NOT run git. Do NOT add pip dependencies（不用 jieba，字符 bigram 方案零依赖）。
- 注释用中文。Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。cwd = 项目根。

## Context
hermes-active 主动意识的念头生成（`services/thought_engine.py`）会车轱辘话。零依赖防复读：①生成时 prompt 注入最近说过的话题负面样本；②生成后 bigram Jaccard 粗筛，相似则重生成一次（二次仍相似接受，防死循环）。

## Files
### File 1: `backend/tests/test_anti_repeat.py`（先写，确认失败）
```python
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
```

### File 2: `backend/services/thought_engine.py`
1) 模块级新增（需要 `import re` 若无则加）：
```python
def _bigram_jaccard(a: str, b: str) -> float:
    """字符 bigram Jaccard 相似度（零依赖防复读粗筛）"""
    def grams(s: str) -> set:
        s = re.sub(r'\s+', '', s or '')
        return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def _is_repetitive(text: str, recent: list, threshold: float = 0.6) -> bool:
    """与最近话题/句式相似则判复读（threshold 启发式起步值，可配）"""
    return any(_bigram_jaccard(text, r) >= threshold for r in recent if r)
```
2) 类里加小方法 `_recent_sent_topics(self, limit: int = 5) -> list`：查 `active_thought_logs` 最近 `decision='send'` 的 content 各截断 30 字（SQL 风格仿文件内 `get_recent_thoughts_from_db`，用 `active_engine` + `text()`）。
3) `_build_messages` 的 user content 末尾追加：
```python
        # 防复读：最近说过的注入负面样本
        recent_said = self._recent_sent_topics(limit=5)
        if recent_said:
            user_content += "\n\n最近你主动说过这些，换新的，别重复：" + "；".join(recent_said)
```
（user content 的实际变量名以函数内为准。）
4) `generate()` 中念头解析成功后：取最近 3 条已发送念头全文（`_recent_sent_topics(limit=3)` 不截断版或单独查），`_is_repetitive` 命中则**重新生成一次**；二次仍命中接受并置 `result["repetitive"] = True`。重生成复用现有 LLM 调用路径，避免死循环只重试一次。

## Verification
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_anti_repeat.py -x -q   # 5 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -q --tb=no                 # 基线 23 failed 不新增
```

## After making changes
输出改动摘要。不跑 git。
