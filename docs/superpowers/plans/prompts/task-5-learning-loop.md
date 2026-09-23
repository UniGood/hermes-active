# Task: 学习回路（质性总结版）

## STRICT RULES
- ONLY modify: 新建 `backend/services/learning_service.py`、新建 `backend/tests/test_learning_loop.py`、`backend/models/active.py`（只加 2 新类）、`backend/models/database.py`（只加迁移函数）、`backend/services/active_consciousness_service.py`（只加发送成功钩子一处）、`backend/services/thought_engine.py`（只加 lessons 注入）、`backend/services/scheduler_service.py`（只加一个 add_job）、`backend/routers/active_consciousness.py`（只加 2 个 lessons 端点）、`frontend/src/views/Analysis.vue`、`frontend/src/i18n/locales/zh-CN/analysis.json`、`…/en-US/analysis.json`。
- Do NOT touch 其他文件（`backend/config.py`、既有测试不许碰）。Do NOT run git。Do NOT 加 pip 依赖。
- 注释用中文。Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。cwd = 项目根。

## Context
hermes-active 学习回路（设计规格 A1，**质性总结版**——单用户样本稀薄，不做统计调参）。链路：主动消息发送→记效果样本→周对账（读 state.db 找用户回复）→LLM 质性总结教训→lessons 注入念头生成。用户消息路径在 hermes 主系统，检测走 state.db **只读**对账，零侵入。

## Files
### File 1: `backend/tests/test_learning_loop.py`（先写，确认失败）
```python
"""学习回路测试：采集、对账、质性总结、注入"""
from unittest.mock import patch, MagicMock
import asyncio


def _run(r):
    return asyncio.get_event_loop().run_until_complete(r) if asyncio.iscoroutine(r) else r


class TestCollection:
    def test_record_effect_on_send(self):
        from services.learning_service import record_sent
        with patch("services.learning_service.active_engine") as me:
            record_sent(thought_id=9, topic="趣事", tone="chill", sent_at="2026-09-22T21:00:00")
            me.connect.return_value.__enter__.return_value.execute.assert_called()

    @patch("services.learning_service.state_engine")
    def test_reconcile_detects_reply(self, mock_state):
        from services.learning_service import reconcile_effects
        row = MagicMock(); row.created_at = "2026-09-22T21:30:00"; row.role = "user"
        mock_state.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [row]
        labels = reconcile_effects([{"thought_id": 9, "sent_at": "2026-09-22T21:00:00", "topic": "趣事"}])
        assert labels[0]["effect"] == "engaged"


class TestLessons:
    @patch("services.learning_service.call_llm_json")
    def test_weekly_lessons_summary(self, mock_llm):
        from services.learning_service import summarize_lessons
        mock_llm.return_value = {"lessons": ["趣事类回应好于嘘寒问暖"]}
        with patch("services.learning_service.active_engine"), \
             patch("services.learning_service._load_effects") as me:
            me.return_value = [{"topic": "趣事", "effect": "engaged"}] * 5
            new = summarize_lessons(min_samples=3)
            assert any("趣事" in l for l in new)

    def test_small_sample_skips(self):
        from services.learning_service import summarize_lessons
        with patch("services.learning_service._load_effects", return_value=[{"topic": "x", "effect": "ignored"}] * 3):
            assert summarize_lessons(min_samples=10) == []

    def test_lessons_rolling_cap(self):
        from services.learning_service import trim_lessons
        mem = [{"summary": f"教训{i}", "evidence_count": 1} for i in range(30)]
        assert len(trim_lessons(mem)) <= 20

    def test_injection_includes_lessons(self):
        from services.thought_engine import _build_lessons_block
        assert "趣事" in _build_lessons_block([{"summary": "趣事回应好", "retired": False}])
        assert _build_lessons_block([]) == ""
```

### File 2: `backend/models/active.py`
末尾新增（仿现有类风格）：
```python
class MessageEffect(Base):
    """主动消息效果样本（学习回路）"""
    __tablename__ = "message_effects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    thought_id = Column(Integer, nullable=False)
    topic = Column(String, nullable=True)          # 话题标签
    tone = Column(String, nullable=True)           # 语气档位
    sent_at = Column(String, nullable=False)
    effect = Column(String, nullable=True)         # ignored/acknowledged/engaged
    reply_latency = Column(Integer, nullable=True)  # 分钟


class Lesson(Base):
    """经验教训本（质性总结产出）"""
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    summary = Column(Text, nullable=False)          # 一句话教训
    evidence_count = Column(Integer, default=0)
    retired = Column(Integer, default=0)            # 0/1
    created_at = Column(String, nullable=False)
```

### File 3: `backend/models/database.py`
仿 `migrate_thought_logs_table` 加 `migrate_message_effects_table()`、`migrate_lessons_table()`（CREATE TABLE IF NOT EXISTS），注册进现有 migrate 调用链。

### File 4: `backend/services/learning_service.py`（新建）
核心实现：
```python
"""学习回路：效果采集 + state.db 对账 + LLM 质性总结（单用户样本稀薄，不做统计调参）"""
from datetime import datetime
from typing import Any, Dict, List

EFFECT_CAP = 200        # 效果样本上限
LESSON_CAP = 20         # 教训滚动上限
MIN_SAMPLES = 10        # 周总结最小样本
BUSY_HOURS = (9, 18)    # 工作时段（忙时 ignored 降权，spec B4-4）


def record_sent(thought_id: int, topic: str, tone: str, sent_at: str) -> None:
    """发送成功钩子：记效果样本（pending，等对账补 effect）"""
    # INSERT message_effects ... 用 active_engine + text()，仿项目内现有 SQL 风格


def _load_effects() -> List[Dict]:
    """读效果样本（对账/总结共用）"""


def reconcile_effects(sent_rows: List[Dict]) -> List[Dict]:
    """读 state.db（只读！）用户消息对账 reply_latency → effect 标签。

    标签：ignored=2h 无回复；acknowledged=<3 轮短冷；engaged=回复 <10min 或 >=3 轮。
    busy 豁免：发送时刻在 BUSY_HOURS 内的 ignored 降级为 acknowledged（不重罚）。
    """
    # state_engine 仿 database.py 里 hermes 引擎（只读）。查询消息表按时间序找发送后的用户消息。
    # mock 测试下 state_engine.connect().execute().fetchall() 返回 [(created_at, role), ...] 风格行


def summarize_lessons(min_samples: int = MIN_SAMPLES) -> List[str]:
    """质性总结：≥min_samples 条效果样本才跑 LLM，产出一句话教训列表，写 lessons 表 + trim_lessons。
    LLM 调用复用 repair_service.call_llm_json（from services.repair_service import call_llm_json）。
    prompt 喂效果明细（话题×效果），要求只输出 {"lessons": ["一句话教训"]}。失败返回 [] 不抛。
    """


def trim_lessons(mem: List[Dict]) -> List[Dict]:
    """滚动保留最近 LESSON_CAP 条（按 created_at）"""


def weekly_job() -> None:
    """周总结任务（scheduler 每周一 09:00 调）：先 reconcile 再 summarize"""
```
**所有 SQL 用 `active_engine` + `text()` 仿项目风格；state.db 只读。**

### File 5: `backend/services/active_consciousness_service.py`
`generate_and_send_thought_with_emotion` 的**发送成功路径**加一行钩子：
```python
        from services.learning_service import record_sent
        record_sent(thought_id=<念头记录id变量>, topic=<话题标签，取 _result 的 type/topic，无则 "general">, tone=<mood_mode 或 "normal">, sent_at=datetime.now().isoformat())
```
（变量名以该处实际作用域为准；包 try/except 不影响主流程。）

### File 6: `backend/services/thought_engine.py`
1) 模块级新增 `_build_lessons_block(lessons: list) -> str`：空列表返回 ""；否则拼"你总结过的经验（别踩坑）：" + 各教训（retired 的跳过）。
2) `_build_messages` 的 user content 追加该 block（lessons 从 lessons 表取未 retired ≤5 条）。念头结果加 `lesson_applied` 字段（列出本次注入的教训 summary 列表）。

### File 7: `backend/services/scheduler_service.py`
仿现有 `add_job` 注册方式加周任务：`weekly_job` 每周一 09:00（cron）。注册处与现有 interval 任务同段。

### File 8: `backend/routers/active_consciousness.py`
加 2 端点：`GET /lessons`（列表含 retired 标记）、`POST /lessons/{lesson_id}/retire`（置 retired=1）。

### File 9: `frontend/src/views/Analysis.vue`
加"经验教训本"面板：卡片列表（教训一句话+证据数+retire 按钮，retired 的灰显）。api 调用走 api 封装带 token。

### File 10/11: i18n `analysis.json` 两语言加键：`lessons.title`（经验教训本）、`lessons.evidence`（证据）、`lessons.retire`（作废）、`lessons.empty`（还没总结出教训）。

## Verification
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_learning_loop.py -x -q  # 6 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -q --tb=no                  # 基线 23 failed 不新增
cd ../frontend && npm run build                                                                  # ✓ built
```

## After making changes
输出改动摘要。不跑 git。
