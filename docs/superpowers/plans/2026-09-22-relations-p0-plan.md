# 关系层 P0 实现计划（tokens 地基 / 防复读 / 冲突修复 / 学习回路）

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。
> **本项目的执行方式（用户指定）：** Claude Code print mode 逐任务后台执行，任务提示词在同目录 `prompts/task-1-tokens.md` … `prompts/task-5-learning-loop.md`，由调度方（Kelly）按序后台启动，每任务验收后 commit + push。
> **规格来源：** `docs/superpowers/specs/2026-09-22-consciousness-relations-design.md`（Part B 审查补丁全部生效中）。

**目标：** 关系层 P0 三件套（冲突修复、学习回路、防复读）+ UI 地基（Design Tokens）。

**架构：** 冲突修复=grievances 表 + RepairState 单例（configs JSON）+ 纯函数状态机 + LLM 事件归因/诚意评分（被动意识注入时机触发，零侵入主系统）；学习回路=message_effects/lessons 表 + state.db 对账批处理 + APScheduler 周总结 + lessons 注入念头 prompt；防复读=prompt 负面样本 + bigram Jaccard 粗筛；tokens=CSS 变量收编 155 行硬编码。

**技术栈：** Python 3.12、FastAPI、SQLAlchemy（models/active.py 类 + database.py 迁移函数）、APScheduler、pytest + MagicMock、Vue 3 + Naive UI。

**测试命令：** `cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -q --tb=no`（基线：**23 failed / 174 passed**，只看新增失败）。

**与 spec 的两处偏差（已批准理由）：**
1. 分词用**字符 bigram Jaccard**而非 jieba（spec A3 写 jieba）——不为 20 行功能引整个分词库（YAGNI），中文短句 bigram 效果等价，零依赖。
2. 用户消息检测**不挂消息钩子**（用户消息路径在 hermes 主系统）——A1 回复检测走 `state.db` 对账批处理（周总结任务顺带），A2 诚意评分在**被动意识注入时机**触发（该 API 被调=用户消息到达的信号），零侵入。

## 文件清单（已 grep 核实 2026-09-22）

**修改：**

| 文件 | 归属任务 | 用途 |
|---|---|---|
| `frontend/src/styles/tokens.css`（新建）+ 18 个 vue/js 文件 | T1 | 颜色硬编码分布：App.vue 31 行、ActiveConsciousness 19、CronJobs 15、Dashboard 11、Layout 10，其余 13 文件 3-9 行 |
| `backend/services/thought_engine.py` | T2/T5 | `_build_messages` 注入负面样本（T2）与 lessons（T5）；`generate` 加粗筛 |
| `backend/services/active_consciousness_service.py` | T3/T4/T5 | `evaluate_emotion_with_llm`（:情绪评估，加 trigger 归因）、`generate_and_send_thought_with_emotion`（发送成功后记 message_effects）、新 `repair_service` 引用点 |
| `backend/services/passive_consciousness_service.py` | T4 | 注入时机触发诚意评分；模板加 `{mood_mode}` |
| `backend/services/repair_service.py`（新建） | T3/T4 | 状态机纯函数 + 诚意评分 + 旧账管理 |
| `backend/services/learning_service.py`（新建） | T5 | 效果对账 + 周总结（质性） |
| `backend/models/active.py` | T3/T5 | 新表：`repair_grievances`（T3）、`message_effects`/`lessons`（T5） |
| `backend/models/database.py` | T3/T5 | `migrate_thought_logs_table` 同款迁移函数建新表 |
| `backend/services/scheduler_service.py` | T5 | `add_job` 注册周总结任务（仿现有 interval 任务） |
| `backend/routers/active_consciousness.py` | T3/T5 | 状态查询端点 + lessons 面板端点（含 retire） |
| `backend/models/active_consciousness.py` | T4 | RepairState pydantic 模式 |
| `frontend/src/views/ActiveConsciousness.vue` | T4 | 关系状态卡（模糊档位） |
| `frontend/src/views/Analysis.vue` | T5 | lessons 面板 + retire 按钮 |
| `frontend/src/i18n/locales/zh-CN|en-US/active-consciousness.json`、`…/analysis.json` | T4/T5 | 文案键 |

**创建：** `backend/tests/test_tokens_placeholder.py` 不建（T1 是纯前端，验证=build+grep）；`backend/tests/test_anti_repeat.py`（T2）、`backend/tests/test_repair_state.py`（T3）、`backend/tests/test_repair_llm.py`（T4）、`backend/tests/test_learning_loop.py`（T5）。

**DO NOT TOUCH（全任务通用禁区）：** `backend/config.py`、`backend/main.py`、`backend/database.py`（**注意：是 models/database.py 可改，根目录 database.py 不在列表内且不存在**）、`backend/models/active.py` 的既有 7 张表定义（只加新类）、`frontend/vite.config.js`、`frontend/package.json`、`.env`、`data/`、`README*`、`CLAUDE.md`、`backend/tests/` 下既有测试文件。

---

### 任务 1：Design Tokens 地基（前端机械收编）

**文件：** 新建 `frontend/src/styles/tokens.css`；修改 18 个含颜色的 vue/js/css 文件（清单见 grep 分布，全在 `frontend/src/`）。

- [ ] **步骤 1：建 tokens.css**（9 个核心 token，色值来自 spec A-UI）：

```css
/* frontend/src/styles/tokens.css — 设计变量（凯莉色情感层 + 技术底座） */
:root {
  /* 情感主色 — 凯莉色（珊瑚橙） */
  --kelly: #FF6B4A;
  --kelly-soft: rgba(255, 107, 74, 0.15);
  /* 底座中性色 */
  --bg-base: #0E1116;
  --bg-card: #161B22;
  --text-primary: #E6EDF3;
  --text-secondary: #8B949E;
  --border: #21262D;
  /* 状态语义色 */
  --ok: #3FB950;
  --warn: #D29922;
  --err: #F85149;
}
```

并在 `frontend/src/main.js`（或 App.vue 的 style 入口，与现有全局样式导入同处）`import './styles/tokens.css'`。

- [ ] **步骤 2：批量收编**。映射规则（近义归并，渐变/功能性色值如 VA 渐变保留原样）：
  - 橙系主色（#FF6B4A、#FF7849、#ff6a00 等珊瑚橙）→ `var(--kelly)`；橙色透明底 → `var(--kelly-soft)`
  - 白/亮白文字（#fff、#ffffff、#E6EDF3、#f5f5f5）→ `var(--text-primary)`（**注意：白底上的深色文字不在此列，保持原样**）
  - 灰文字（#999、#8B949E、#aaa、#666）→ `var(--text-secondary)`
  - 深底（#0E1116、#0d1117、#0a0e14）→ `var(--bg-base)`；卡底（#161B22、#1a1f26）→ `var(--bg-card)`；边框（#21262D、#30363d）→ `var(--border)`
  - 状态红/绿/黄（#F85149/#ff4d4f→`--err`、#3FB950/#52c41a→`--ok`、#D29922/#faad14→`--warn`）
  - **不迁**：渐变 stops 里的 VA 三色功能色（效价红橙绿/唤醒蓝橙红/社交灰橙紫的渐变序列按原值保留）、语义特殊的孤立色
  - 执行：按文件逐个替换（每文件先 `grep -n` 颜色值定位再替换），**禁止盲 sed 全局替换**（误伤渐变）。
- [ ] **步骤 3：验证**：

```bash
cd ~/.hermes/hermes-active/frontend && npm run build   # ✓ built
grep -rn "#FF6B4A\|#0E1116\|#161B22\|#21262D\|#E6EDF3\|#8B949E" src --include=*.vue --include=*.js | grep -v tokens.css | wc -l   # 目标 <10（允许少量误伤风险的保留）
```

- [ ] **步骤 4：Commit（调度方）**：`style: extract design tokens into tokens.css`

---

### 任务 2：防复读（A3）

**文件：** `backend/services/thought_engine.py`、新建 `backend/tests/test_anti_repeat.py`。

- [ ] **步骤 1：失败测试**：

```python
# backend/tests/test_anti_repeat.py
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

- [ ] **步骤 2：跑测试确认失败**（ImportError）。
- [ ] **步骤 3：实现**（`thought_engine.py` 模块级新增）：

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

`generate()` 中：念头生成解析成功后，取最近 3 条已发送念头（`active_thought_logs` 按 decision='send' 取 content，SQL 仿 `get_recent_thoughts_from_db`），调 `_is_repetitive`，命中则**重生成一次**；二次仍命中则接受（防死循环）并标记 `repetitive=True` 进结果。另外 `_build_messages` 的 user content 末尾追加负面样本段：

```python
        # 防复读：最近说过的注入负面样本
        if context.free_thoughts is not None:  # 占位防误改，实际用下面的 recent 计算
            pass
        recent_said = self._recent_sent_topics(limit=5)   # 新增小方法：查最近5条已发送念头的摘要
        if recent_said:
            user_content += "\n\n最近你主动说过这些，换新的，别重复：" + "；".join(recent_said)
```

（`_recent_sent_topics` 查 `active_thought_logs` 最近 5 条 `decision='send'` 的 content 截断 30 字。）

- [ ] **步骤 4：测试过 + 全量回归**（基线 23 failed 不变）。
- [ ] **步骤 5：Commit（调度方）**：`feat: anti-repeat filter for proactive thoughts`

---

### 任务 3：冲突修复·数据层 + 状态机（A2 前半）

**文件：** `backend/models/active.py`（新类）、`backend/models/database.py`（新迁移函数）、`backend/services/repair_service.py`（新建）、`backend/routers/active_consciousness.py`（状态查询端点）、新建 `backend/tests/test_repair_state.py`。

- [ ] **步骤 1：失败测试**（状态机纯函数核心）：

```python
# backend/tests/test_repair_state.py
"""冲突修复状态机测试"""
from services.repair_service import (
    transition, score_goodwill, add_grievance, should_cite_grievance)


class TestTransition:
    def test_upset_by_severe_event(self):
        assert transition("normal", {"type": "trigger", "severity": 4, "valence_drop": 0.5}) == "upset"

    def test_no_transition_on_noise(self):
        # 低严重度+小跌幅 = 噪音，不动
        assert transition("normal", {"type": "trigger", "severity": 1, "valence_drop": 0.1}) == "normal"

    def test_upset_to_cold_after_hours(self):
        assert transition("upset", {"type": "tick", "hours_since": 5}) == "cold"

    def test_goodwill_accumulates_to_softening(self):
        st = {"mode": "cold", "points": 0.0}
        mode = transition("cold", {"type": "goodwill", "points": 2.0}, state=st)
        assert mode == "softening"

    def test_softening_to_reconciled(self):
        st = {"mode": "softening", "points": 5.0}
        assert transition("softening", {"type": "goodwill", "points": 1.5}, state=st) == "reconciled"

    def test_decay_to_grudge(self):
        assert transition("cold", {"type": "tick", "hours_since": 80}) == "grudge"

    def test_self_at_fault_branch(self):
        assert transition("normal", {"type": "self_fault"}) == "self_at_fault"

    def test_reconciled_resets(self):
        assert transition("reconciled", {"type": "tick", "hours_since": 1}) == "normal"


class TestGoodwill:
    def test_sincere_scores_high(self):
        r = score_goodwill(4, is_repeat=False, hours_since_upset=2)
        assert r > 0.5

    def test_repeat_counts_zero(self):
        assert score_goodwill(5, is_repeat=True, hours_since_upset=1) == 0.0

    def test_time_decay(self):
        fast = score_goodwill(4, is_repeat=False, hours_since_upset=1)
        slow = score_goodwill(4, is_repeat=False, hours_since_upset=60)
        assert slow < fast


class TestGrievances:
    def test_add_and_cap(self):
        mem = []
        for i in range(7):
            mem = add_grievance(mem, f"事{i}", severity=2)
        assert len(mem) <= 5  # 上限5笔

    def test_cooldown(self):
        mem = [{"event": "旧事", "severity": 3, "settled_at": "2026-09-01", "last_cited_at": "2026-09-20"}]
        assert should_cite_grievance(mem, "2026-09-22") is False  # 30天冷却内
        assert should_cite_grievance([{"event": "x", "severity": 3, "last_cited_at": None}], "2026-09-22") is True
```

- [ ] **步骤 2：确认失败**。
- [ ] **步骤 3：实现 `repair_service.py`**（纯函数为主，持久化走 configs JSON + 表）：

```python
"""冲突修复服务：状态机 + 诚意评分 + 旧账管理（纯函数优先，便于测试）"""
from datetime import datetime
from typing import Any, Dict, List, Optional

# 模式集合：normal / upset / cold / softening / reconciled / self_at_fault / grudge
# 状态单例存 configs 键 "active_consciousness.repair_state"（JSON: mode, trigger_event, started_at, points, fault_side）
RECONCILE_POINTS = 6.0   # 和好所需积分
GRIEVANCE_CAP = 5
GRIEVANCE_COOLDOWN_DAYS = 30


def transition(mode: str, event: Dict[str, Any], state: Optional[Dict] = None) -> str:
    """纯函数状态机。event: {type: trigger|tick|goodwill|self_fault, ...}"""
    st = state or {}
    t = event.get("type")
    if t == "self_fault":
        return "self_at_fault"
    if t == "trigger":
        sev = event.get("severity", 0)
        drop = event.get("valence_drop", 0.0)
        if mode == "normal" and sev >= 3 and drop >= 0.3:
            return "upset"
        return mode
    if t == "tick":
        h = event.get("hours_since", 0)
        if mode == "upset" and h >= 4:
            return "cold"
        if mode == "cold" and h >= 72:
            return "grudge"
        if mode == "self_at_fault" and h >= 24:
            return "normal"  # 自省失败 fallback
        return mode
    if t == "goodwill":
        pts = event.get("points", 0.0)
        total = st.get("points", 0.0) + pts
        if mode in ("cold", "upset") and total >= RECONCILE_POINTS * 0.4:
            return "softening"
        if mode == "softening" and total >= RECONCILE_POINTS:
            return "reconciled"
        return mode
    return mode


def score_goodwill(sincerity: int, is_repeat: bool, hours_since_upset: float) -> float:
    """诚意积分：LLM 评 1-5 分 → 积分；重复套话 0 分；时间衰减。"""
    if is_repeat or not (1 <= sincerity <= 5):
        return 0.0
    base = (sincerity - 1) / 4.0          # 0~1
    decay = max(0.3, 1.0 - hours_since_upset / 72.0)  # 72h 线性衰减至 0.3
    return base * decay * 2.0             # 单次上限 2 分


def add_grievance(mem: List[Dict], event: str, severity: int) -> List[Dict]:
    """记旧账（上限 GRIEVANCE_CAP，新的挤掉最旧的）"""
    mem = list(mem) + [{
        "event": event, "severity": severity,
        "settled_at": None, "last_cited_at": None,
        "created_at": datetime.now().isoformat()}]
    return sorted(mem, key=lambda g: g.get("created_at") or "")[-GRIEVANCE_CAP:]


def should_cite_grievance(mem: List[Dict], today: Optional[str] = None) -> bool:
    """翻旧账冷却：任一旧账距上次引用超 30 天才可翻（防祥林嫂）"""
    today = today or datetime.now().strftime("%Y-%m-%d")
    for g in mem:
        last = g.get("last_cited_at")
        if last is None:
            return True
        d = (datetime.fromisoformat(today) - datetime.fromisoformat(last)).days
        if d >= GRIEVANCE_COOLDOWN_DAYS:
            return True
    return False
```

表（`models/active.py` 新增，仿现有类风格）：

```python
class RepairGrievance(Base):
    """冲突旧账（翻旧账机制）"""
    __tablename__ = "repair_grievances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(Text, nullable=False)          # 事件描述
    severity = Column(Integer, default=1)          # 1-5
    settled_at = Column(String, nullable=True)     # 翻篇时间
    last_cited_at = Column(String, nullable=True)  # 上次被翻的时间
    created_at = Column(String, nullable=False)
```

迁移函数（`models/database.py`，仿 `migrate_thought_logs_table`）建 `repair_grievances`。路由加 `GET /api/active-consciousness/repair/state` 返回 mode/points/档位（**模糊档位**：points 映射 `{"冰","化冰","回暖"}`，不返回数字——防游戏化，spec B4-3）。

- [ ] **步骤 4：测试过 + 全量回归**。
- [ ] **步骤 5：Commit（调度方）**：`feat: conflict-repair state machine and grievances`

---

### 任务 4：冲突修复·LLM 集成 + 台词包 + 注入 + 前端（A2 后半）

**文件：** `backend/services/active_consciousness_service.py`、`backend/services/passive_consciousness_service.py`、`backend/services/repair_service.py`（加 LLM 包装）、`backend/models/active_consciousness.py`、`frontend/src/views/ActiveConsciousness.vue`、i18n 两文件、新建 `backend/tests/test_repair_llm.py`。

- [ ] **步骤 1：失败测试**（mock LLM，断言归因与评分被正确解析）：

```python
# backend/tests/test_repair_llm.py
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
        assert r["severity"] == 0  # 失败=无归因，不误伤


class TestGoodwillScoring:
    @patch("services.repair_service.call_llm_json")
    def test_sincerity_parsing(self, mock_llm):
        from services.repair_service import evaluate_goodwill
        mock_llm.return_value = {"sincerity": 5, "is_repeat": False}
        r = evaluate_goodwill("我真的知道错了，不该说那句话", [])
        assert r["sincerity"] == 5 and r["points"] > 0
```

（`call_llm_json` 是本任务新建的通用 JSON LLM 调用小工具——放 repair_service 内部，prompt 要求输出 JSON；mock 路径按实际模块位置对齐。）

- [ ] **步骤 2：确认失败**。
- [ ] **步骤 3：实现**：
  1. `repair_service.py` 加 `evaluate_trigger(session_context, emotion) -> dict`（LLM 归因"因为什么"+severity 1-5；失败返回 severity=0）与 `evaluate_goodwill(user_msg, recent_goodwills) -> dict`（一次调用输出 `{"sincerity": 1-5, "is_repeat": bool}` → 用 `score_goodwill` 转积分）。二者都走独立 JSON 调用（prompt 自包含），失败兜底不抛。
  2. `active_consciousness_service.py` 的 `evaluate_emotion_with_llm` 返回处**顺带**调 `evaluate_trigger`（同一时机，独立小调用），把 trigger 写进返回 dict 的 `trigger_event` 键——`update_emotion_state` 不变（trigger 进 RepairState 不进 EmotionState）。
  3. `passive_consciousness_service.py`：模板渲染 context 加 `mood_mode`（从 RepairState 读，映射语气词 `{"normal":"温柔","upset":"有点赌气","cold":"冷淡硬句","softening":"嘴硬心软","reconciled":"回暖撒娇","grudge":"淡淡的","self_at_fault":"心虚讨好"}`）；**注入时机顺带**：若上次消息是她的主动消息且距今 <2h，调 `evaluate_goodwill` 记积分并跑 `transition`。
  4. 台词包：`_DEFAULTS` 加 `active_consciousness.prompts.repair_dialogue_pack`（JSON 键值，按 mode 分组的双标例句数组，cold/softening 各 ≥5 句），`thought_engine._build_messages` 按当前 mode 采样 1-2 句进 prompt（"你在这种心情下的说话风格示例：……"）。
  5. `frontend/src/views/ActiveConsciousness.vue` 加"关系状态"卡：调 `/repair/state`，显示 mode 中文名 + 模糊档位（冰/化冰/回暖，样式用 `var(--kelly)`），**不显示数字**。
  6. i18n 两文件补键。
- [ ] **步骤 4：测试过 + 全量回归 + `npm run build`**。
- [ ] **步骤 5：Commit（调度方）**：`feat: repair LLM attribution, goodwill scoring, mood-mode injection`

---

### 任务 5：学习回路（A1，质性总结版）

**文件：** `backend/models/active.py`（2 新表）、`backend/models/database.py`（迁移）、`backend/services/learning_service.py`（新建）、`backend/services/active_consciousness_service.py`（采集钩子）、`backend/services/thought_engine.py`（lessons 注入）、`backend/services/scheduler_service.py`（周任务注册）、`backend/routers/active_consciousness.py`（lessons 面板端点）、`frontend/src/views/Analysis.vue`、i18n、新建 `backend/tests/test_learning_loop.py`。

- [ ] **步骤 1：失败测试**：

```python
# backend/tests/test_learning_loop.py
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
        """state.db 对账：发送后 30 分钟有用户回复 → engaged"""
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
            new = summarize_lessons()
            assert any("趣事" in l for l in new)

    def test_small_sample_skips(self):
        from services.learning_service import summarize_lessons
        with patch("services.learning_service._load_effects", return_value=[{"topic": "x", "effect": "ignored"}] * 3):
            assert summarize_lessons(min_samples=10) == []  # 样本阈值

    def test_lessons_rolling_cap(self):
        from services.learning_service import trim_lessons
        mem = [{"summary": f"教训{i}", "evidence_count": 1} for i in range(30)]
        assert len(trim_lessons(mem)) <= 20

    def test_injection_includes_lessons(self):
        from services.thought_engine import _build_lessons_block
        assert "趣事" in _build_lessons_block([{"summary": "趣事回应好", "retired": False}])
        assert _build_lessons_block([]) == ""
```

- [ ] **步骤 2：确认失败**。
- [ ] **步骤 3：实现 `learning_service.py`**：
  - `record_sent(thought_id, topic, tone, sent_at)`——发送成功钩子（`generate_and_send_thought_with_emotion` 成功路径调用）。
  - `reconcile_effects(sent_rows)`——读 `state.db`（**只读**，`state_engine` 仿 database.py 的 hermes 引擎）用户消息对账 reply_latency → effect 标签（`ignored`：2h 无回复；`acknowledged`：<3 轮短冷；`engaged`：≥3 轮或回复 <10min）；**busy 豁免双保险**（节律未实现前用工作时段 9-18 点权重减半计 ignored，spec B4-4）。
  - `summarize_lessons(min_samples=10)`——≥10 条效果记录才跑 LLM 质性总结（prompt 喂效果明细，产出 `{"lessons": [一句话教训]}`，每条带 evidence_count），写 `lessons` 表；`trim_lessons` 滚动 20 条；retire 端点。
  - scheduler 注册 `add_job` 周总结（每周一 09:00，仿现有 interval 任务注册方式）。
  - 表：`message_effects`（thought_id, topic, tone, sent_at, effect, reply_latency）、`lessons`（summary, evidence_count, retired, created_at）。
  - `thought_engine._build_messages`：user content 追加 `_build_lessons_block`（未 retire 的教训 ≤5 条："你总结过的经验：…"）；念头结果记 `lesson_applied` 字段（列出引用的教训 id）。
  - 路由：`GET /api/active-consciousness/lessons`、`POST /api/active-consciousness/lessons/{id}/retire`。前端 Analysis.vue 加 lessons 面板（卡片：教训一句话+证据数+retire 按钮）。
- [ ] **步骤 4：测试过 + 全量回归 + `npm run build`**。
- [ ] **步骤 5：Commit（调度方）**：`feat: learning loop with qualitative lessons`

---

## 自检记录（writing-plans 自检）

1. **规格覆盖度**：spec P0 四项（A2/T3+T4、A1/T5、A3/T2、tokens/T1）全覆盖；A2 的 grievances 冷却/上限、防刷分、模糊档位、self_at_fault、grudge 均在 T3/T4；A1 的 busy 豁免、样本阈值、滚动淘汰、retire、透明化在 T5；两偏差已声明理由。
2. **占位符扫描**：无 TODO/待定；`call_llm_json` 为本计划新建工具（T4 步骤 3 内定义）；`_load_effects`/`_build_lessons_block`/`_recent_sent_topics` 均给出实现定义（测试与实现同名）。
3. **类型一致性**：`transition(mode, event, state)` 三处签名一致；`score_goodwill(sincerity, is_repeat, hours_since_upset)` 一致；effect 标签枚举 `ignored/acknowledged/engaged` 在对账与总结一致；`evaluate_trigger`/`evaluate_goodwill` 返回 dict 键与测试一致。

## 执行交接

按用户指令：Claude Code print mode 逐任务后台执行，顺序 T1→T2→T3→T4→T5，每任务完成由调度方跑验收（文件边界、禁区、新测试、全量基线对照 23 failed、build、UI 行为=承诺行为点检）后 commit + push，再发下一任务。
