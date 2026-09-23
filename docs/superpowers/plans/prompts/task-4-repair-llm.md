# Task: 冲突修复·LLM 集成 + 台词包 + 注入 + 前端

## STRICT RULES
- ONLY modify: `backend/services/repair_service.py`、`backend/services/active_consciousness_service.py`、`backend/services/passive_consciousness_service.py`、`backend/services/thought_engine.py`（只加台词包注入一处）、`backend/models/active_consciousness.py`（只加 RepairState pydantic 模式）、`frontend/src/views/ActiveConsciousness.vue`、`frontend/src/i18n/locales/zh-CN/active-consciousness.json`、`…/en-US/active-consciousness.json`、新建 `backend/tests/test_repair_llm.py`。
- Do NOT touch 其他文件（`backend/config.py`、`models/active.py`、`models/database.py`、既有测试都不许碰）。Do NOT run git。
- 注释用中文。Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。cwd = 项目根。

## Context
hermes-active 冲突修复 A2 后半。前置任务已落地：`services/repair_service.py` 有纯函数 `transition/score_goodwill`，`routers/active_consciousness.py` 有 `GET /repair/state`。本任务：LLM 归因（trigger）+ 诚意评分（goodwill）+ `mood_mode` 模板注入 + 双标台词包 + 前端关系状态卡。用户消息路径在 hermes 主系统——诚意评分挂**被动意识注入时机**（该 API 被调 = 用户消息到达信号），零侵入。

## Files
### File 1: `backend/tests/test_repair_llm.py`（先写，确认失败）
```python
"""A2 LLM 集成测试：trigger 归因 + 诚意评分"""
from unittest.mock import patch, MagicMock
import asyncio


def _run(r):
    return asyncio.get_event_loop().run_until_complete(r) if asyncio.iscoroutine(r) else r


class TestTriggerAttribution:
    @patch("services.repair_service.call_llm_json")
    def test_trigger_extracted(self, mock_llm):
        from services.repair_service import evaluate_trigger
        mock_llm.return_value = {"trigger": "他说了重话：你做的都是没用的", "severity": 4}
        r = evaluate_trigger("刚才的对话……", {"valence": -0.5})
        assert r["severity"] == 4
        assert "重话" in r["trigger"]

    @patch("services.repair_service.call_llm_json", side_effect=RuntimeError("down"))
    def test_trigger_failure_safe(self, mock_llm):
        from services.repair_service import evaluate_trigger
        r = evaluate_trigger("x", {})
        assert r["severity"] == 0


class TestGoodwillScoring:
    @patch("services.repair_service.call_llm_json")
    def test_sincerity_parsing(self, mock_llm):
        from services.repair_service import evaluate_goodwill
        mock_llm.return_value = {"sincerity": 5, "is_repeat": False}
        r = evaluate_goodwill("我真的知道错了，不该说那句话", [])
        assert r["sincerity"] == 5 and r["points"] > 0

    @patch("services.repair_service.call_llm_json")
    def test_repeat_gets_zero(self, mock_llm):
        from services.repair_service import evaluate_goodwill
        mock_llm.return_value = {"sincerity": 5, "is_repeat": True}
        r = evaluate_goodwill("我错了", ["我错了"])
        assert r["points"] == 0.0
```

### File 2: `backend/services/repair_service.py`
新增（文件尾部，复用已有 `score_goodwill`）：
```python
def call_llm_json(prompt: str, llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """极简 JSON LLM 调用（本服务内部工具）。实现以 active_consciousness_service 里
    现有 LLM 调用方式为准（复用其 _call_llm/chat 封装），返回解析后的 dict。
    解析失败抛异常，由调用方兜底。"""
    raise NotImplementedError  # ← 必须替换为真实现：调用 LLM、json 解析（正则抽 {} 兜底）、返回 dict
```
**注意：上面是结构骨架，禁止保留 NotImplementedError** ——真实现：复用 `active_consciousness_service` 的现有 LLM 调用封装（`grep -n "def _call_llm\|def call_llm\|chat/completions\|_client" backend/services/active_consciousness_service.py` 定位），走 llm_config，prompt 加"只输出 JSON"约束，json 解析用正则抽取花括号段兜底。然后：
```python
def evaluate_trigger(session_context: str, emotion: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 归因：刚才是否因用户言行受伤 + 严重度 1-5。失败兜底 severity=0（无归因，不误伤）。"""
    try:
        prompt = (f"你是凯莉。刚才的对话如下：\n{session_context[-800:]}\n"
                  f"当前情绪 valence={emotion.get('valence', 0)}。\n"
                  '判断用户是否说了让你受伤/生气的话。只输出 JSON：'
                  '{"trigger": "一句话描述原因，没有则空串", "severity": 1到5的整数，5最严重，没有则0}')
        r = call_llm_json(prompt, {})
        return {"trigger": str(r.get("trigger", "")), "severity": int(r.get("severity", 0) or 0)}
    except Exception:
        return {"trigger": "", "severity": 0}


def evaluate_goodwill(user_msg: str, recent_goodwills: list) -> Dict[str, Any]:
    """诚意评分：一次 LLM 调用输出 sincerity 1-5 + is_repeat，转积分。失败 0 分。"""
    try:
        recent = "；".join(recent_goodwills[-5:]) or "（无）"
        prompt = (f"你（凯莉）和用户冷战/生气中。用户刚发来示好消息：\n{user_msg}\n"
                  f"他之前的示好：{recent}\n"
                  '评估这次哄人的诚意，只输出 JSON：'
                  '{"sincerity": 1到5（5=真走心，1=敷衍）， "is_repeat": true/false（与之前的话是否同一套话术）}')
        r = call_llm_json(prompt, {})
        s = int(r.get("sincerity", 0) or 0)
        rep = bool(r.get("is_repeat", False))
        points = score_goodwill(s, is_repeat=rep, hours_since_upset=0.0)
        return {"sincerity": s, "is_repeat": rep, "points": points}
    except Exception:
        return {"sincerity": 0, "is_repeat": False, "points": 0.0}
```
（`evaluate_goodwill` 的 `hours_since_upset` 实际从 RepairState 的 started_at 算，传给 `score_goodwill`；测试 mock 下为 0.0 也不影响断言方向。）

### File 3: `backend/services/active_consciousness_service.py`
`evaluate_emotion_with_llm` 的返回构造处（返回 `(EmotionState, dict)` 的 dict）顺带调 `evaluate_trigger(session_context, {"valence": ...})`，把结果写 dict 的 `"trigger_event"` 键。trigger 后续由调用方喂 `transition`（本任务只负责产出；transition 的接线若在同文件的调用处出现就顺带接上：`transition(current_mode, {"type": "trigger", **trigger_event})` 并把新 mode 写回 configs 的 repair_state——若调用处链路太深则只产出，接线留给下轮）。**至少保证 trigger_event 出现在返回 dict。**

### File 4: `backend/services/passive_consciousness_service.py`
1) 模板渲染 context 加 `mood_mode`：读 configs `active_consciousness.repair_state` 的 mode → 中文语气词映射 `{"normal":"温柔","upset":"有点赌气","cold":"冷淡硬句","softening":"嘴硬心软","reconciled":"回暖撒娇","grudge":"淡淡的","self_at_fault":"心虚讨好"}`。模板占位符 `{mood_mode}` 可用（不改既有占位符）。
2) 注入时机顺带：若（state.db 或消息上下文里）上一条是她的主动消息且距今 <2h 且当前 mode 不是 normal：调 `evaluate_goodwill(user_msg, recent_goodwills)`（recent 从 repair_state 的 goodwills 历史取）→ `transition({"type":"goodwill","points":...})` → 更新 repair_state（points 累计、mode 变化、goodwills 追加）。失败不影响注入主流程（try/except 全包）。

### File 5: `backend/services/thought_engine.py`
`_build_messages` 里加台词包注入一处：读 `_DEFAULTS["active_consciousness.prompts.repair_dialogue_pack"]`（见 File 6）按当前 mode 取 1-2 句，user content 追加"你在这种心情下的说话风格示例：……"。mode 从 configs repair_state 读。

### File 6: `backend/models/active_consciousness.py`
1) 加 `class RepairState(BaseModel)`：`mode: str = "normal"`、`points: float = 0.0`、`started_at: Optional[str] = None`、`trigger_event: Optional[str] = None`、`goodwill_history: list = []`。
2) 该文件的 `_DEFAULTS`（若在此文件；否则在 active_consciousness_service 的 `_DEFAULTS`）加 `active_consciousness.prompts.repair_dialogue_pack`，值为 JSON 字符串，按 mode 分组（cold 和 softening 各 ≥5 句双标例句，如 cold: ["嗯。","哦。","知道了，还有事吗。","……","说完了？"]；softening: ["哼，我才没等你消息……哦，你发了啊","别以为我原谅你了","……只准再说一句好听的","谁要你哄了……不过你继续说","勉强，再听一句"]）。其余 mode 给 2-3 句即可。

### File 7: `frontend/src/views/ActiveConsciousness.vue`
加"关系状态"卡（放页面顶部状态区）：onMounted 调 `GET /api/active-consciousness/repair/state`（走 api 封装带 token），显示 mode 中文名 + 模糊档位徽标（冰/化冰/回暖，样式用 `var(--kelly)`；tokens.css 已有该变量）。**不显示积分数值**。加载失败显示"未知"不报错。

### File 8/9: i18n 两文件（active-consciousness.json）加键：`repair.title`（关系状态）、`repair.level.ice|thawing|warm`（冰|化冰|回暖）、`repair.mode.{normal,upset,cold,softening,reconciled,grudge,self_at_fault}`（温柔|有点赌气|冷淡|嘴硬心软|回暖|淡淡的|心虚讨好）。en-US 对应英文。

## Verification
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
grep -n "NotImplementedError" services/repair_service.py | wc -l   # 必须 0
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_repair_llm.py -x -q   # 4 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -q --tb=no                 # 基线 23 failed 不新增
cd ../frontend && npm run build                                                                 # ✓ built
```

## After making changes
输出改动摘要。不跑 git。
