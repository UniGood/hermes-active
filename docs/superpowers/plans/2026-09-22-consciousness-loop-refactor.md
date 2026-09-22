# 意识回路改造 实现计划（念头重试 / 自由意识出口 / 深夜适配 / 情绪统一）

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。
> **本项目的执行方式（用户指定）：** Claude Code print mode 逐任务执行，任务提示词在同目录 `prompts/task-1-retry-thought.md` … `prompts/task-4-emotion-unify.md`，由调度方（Kelly）按序后台启动。

**目标：** 修复第一性原理评审发现的 4 个问题——假功能"念头重试"、自由意识沉思对外零出口、深夜适配死字段、情绪维度双定义。

**架构：** 后端 FastAPI + SQLAlchemy（raw text() SQL 风格），Hindsight 沉淀走 `hindsight_client` SDK（同步 `retain`）；灵感源把自由思考注入 `ContextBundle` 供念头生成；深夜因子按本地小时浮点区间对发送决策打分折减并注入 prompt 气质；情绪统一为单一真相源（EmotionState 管情绪三轴、关系三维 affection/trust/heat 管慢变关系），模板占位符名字不变。

**技术栈：** Python 3.12、FastAPI、pytest + unittest.mock（MagicMock/patch）、Vue 3 + Naive UI、vue-i18n。

**测试命令（全项目统一）：** `cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q`

---

## 文件清单（已 grep 核实 2026-09-22，勿凭空造路径）

**修改（只许动这些，各任务归属见任务内清单）：**

| 文件 | 职责 |
|---|---|
| `backend/services/active_consciousness_service.py` | `retry_thought`（约 1037-1040 行 TODO）、`send_message_to_target`、`check_send_protection`、`get_hindsight_client`、`call_hindsight_recall`、情绪函数 `evolve_emotion/merge_emotion/merge_emotion_dynamic/get_emotion_state/update_emotion_state/evaluate_emotion_with_llm`、`get_recent_thoughts_from_db` |
| `backend/services/free_consciousness_service.py` | `write_log`、`run_contemplation`、`load_sediment`、`test_llm_connection` |
| `backend/services/context_collector.py` | `ContextBundle` dataclass、`collect()`、`_get_structured_conversations()`（写死 `limit=200`） |
| `backend/services/thought_engine.py` | `generate()`、`_build_messages()` |
| `backend/models/active.py` | `FreeConsciousnessLog`（`free_consciousness_logs` 表） |
| `backend/models/active_consciousness.py` | 配置/状态 schema：`max_messages_per_session`（:35）、`deep_night_start/end/fitness`（:57-59）、`temp_change_threshold`（:74）、`time_window`（:94） |
| `backend/services/passive_consciousness_service.py` | 模板注入映射（情绪变量来源） |
| `frontend/src/views/ActiveConsciousness.vue` | 六维滑块 UI、配置 tab |
| `frontend/src/i18n/locales/zh-CN/activeConsciousness.json`、`…/en-US/activeConsciousness.json` | 新增文案键 |

**创建：**

| 文件 | 职责 |
|---|---|
| `backend/tests/test_retry_thought.py` | 任务 1 测试 |
| `backend/tests/test_free_hindsight_export.py` | 任务 2 测试 |
| `backend/tests/test_deep_night.py` | 任务 3 测试 |
| `backend/tests/test_emotion_single_source.py` | 任务 4 测试 |

**DO NOT TOUCH（所有任务通用禁区）：** `backend/config.py`、`backend/main.py`、`backend/routers/**`（除非任务内明确列出）、`backend/database.py`、`frontend/vite.config.js`、`frontend/package.json`、`.env`、`data/`、`docs/images/`、`README*`、`CLAUDE.md`。

---

### 任务 1：念头重试补全（重试发送）

**语义（重要）：** `retry_thought` 的 docstring 是"重试**发送**念头"——对已生成的念头重新执行**发送**，不是重新生成。

**文件：**
- 修改：`backend/services/active_consciousness_service.py`（替换 `retry_thought` TODO 实现，约 :1037-1040）
- 创建：`backend/tests/test_retry_thought.py`

- [ ] **步骤 1：编写失败的测试**

```python
# backend/tests/test_retry_thought.py
"""retry_thought 重试发送念头测试"""
from unittest.mock import patch, MagicMock

from services.active_consciousness_service import ActiveConsciousnessService


class TestRetryThought:
    @patch("services.active_consciousness_service.send_message_to_target")
    @patch("services.active_consciousness_service.check_send_protection")
    @patch("services.active_consciousness_service.active_engine")
    def test_retry_sends_existing_thought(self, mock_engine, mock_protect, mock_send):
        """重试 = 用原念头内容重新发送，不重新生成"""
        import asyncio
        mock_protect.return_value = (True, "ok")
        mock_send.return_value = (True, {"platform": "weixin"})
        row = MagicMock()
        row.id, row.content = 7, "测试念头内容"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row

        result = ActiveConsciousnessService.retry_thought(7)
        if asyncio.iscoroutine(result):
            result = asyncio.get_event_loop().run_until_complete(result)

        assert result["success"] is True
        mock_send.assert_called_once()
        assert "测试念头内容" in str(mock_send.call_args)

    @patch("services.active_consciousness_service.active_engine")
    def test_retry_missing_thought(self, mock_engine):
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
        result = ActiveConsciousnessService.retry_thought(999)
        import asyncio
        if asyncio.iscoroutine(result):
            result = asyncio.get_event_loop().run_until_complete(result)
        assert result["success"] is False
        assert "不存在" in result["error"]

    @patch("services.active_consciousness_service.check_send_protection")
    @patch("services.active_consciousness_service.active_engine")
    def test_retry_blocked_by_protection(self, mock_engine, mock_protect):
        """发送保护拦截时返回失败并说明原因"""
        mock_protect.return_value = (False, "夜间免打扰")
        row = MagicMock()
        row.id, row.content = 3, "x"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row
        result = ActiveConsciousnessService.retry_thought(3)
        import asyncio
        if asyncio.iscoroutine(result):
            result = asyncio.get_event_loop().run_until_complete(result)
        assert result["success"] is False
        assert "免打扰" in result["error"] or "保护" in result["error"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_retry_thought.py -x -q`
预期：FAIL——`retry_thought` 返回 `{"success": False, "error": "重试功能待实现"}`，断言不通过。

- [ ] **步骤 3：实现重试发送**

`backend/services/active_consciousness_service.py` 中，将整个 `retry_thought` 替换为（保持 `@staticmethod`，改 async 与 `send_message_to_target` 对齐）：

```python
    @staticmethod
    async def retry_thought(thought_id: int) -> Dict[str, Any]:
        """重试发送念头（对已生成的念头重新执行发送，不重新生成）"""
        with active_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT id, content FROM active_thought_logs WHERE id = :id"
            ), {"id": thought_id}).fetchone()
        if not row:
            return {"success": False, "error": f"念头 {thought_id} 不存在"}

        allowed, reason = ActiveConsciousnessService.check_send_protection()
        if not allowed:
            return {"success": False, "error": f"发送保护拦截：{reason}"}

        ok, send_details = await send_message_to_target(row.content)
        status = "retried:ok" if ok else "retried:failed"
        with active_engine.connect() as conn:
            conn.execute(text(
                "UPDATE active_thought_logs SET message_sending = :s WHERE id = :id"
            ), {"s": status, "id": thought_id})
            conn.commit()
        if ok:
            return {"success": True, "data": {"thought_id": thought_id, "sending": send_details}}
        return {"success": False, "error": f"重试发送失败：{send_details}"}
```

注意：`send_message_to_target` 的真实签名以文件内定义为准（`grep -n "async def send_message_to_target" backend/services/active_consciousness_service.py` 查看参数），按其参数传入目标（念头表的 platform/target 字段若存在则查出来一并传；若该函数只接 content 就按上面写法）。路由层 `POST /thoughts/{id}/retry`（`backend/routers/active_consciousness.py` 中 `retry_thought` 端点）若为同步调用需加 `await`——该文件**仅此一处**允许改动。

- [ ] **步骤 4：运行测试验证通过**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_retry_thought.py -x -q`
预期：3 passed。再跑全量 `… -m pytest tests/ -x -q` 确认无回归（既有测试全绿）。

- [ ] **步骤 5：Commit（由调度方执行）**

```bash
git add backend/services/active_consciousness.py backend/routers/active_consciousness.py backend/tests/test_retry_thought.py
git commit -m "feat: implement thought resend on retry"
```

---

### 任务 2：自由意识对外出口（Hindsight 沉淀 + 灵感源）

**背景：** `free_consciousness_logs` 有内部消费（`load_sediment` 供下轮思考）但对外零出口。双回路补上：①沉思沉淀进 Hindsight 成为长期记忆；②最近自由思考进入 `ContextBundle` 供念头生成（"想着想着就想找你说话"）。

**文件：**
- 修改：`backend/services/free_consciousness_service.py`（新增 `retain_to_hindsight`，在 `run_contemplation` 写日志成功后调用）
- 修改：`backend/services/context_collector.py`（`ContextBundle` 加 `free_thoughts`、`collect()` 加采集、`to_dict` 加 key）
- 创建：`backend/tests/test_free_hindsight_export.py`

- [ ] **步骤 1：编写失败的测试**

```python
# backend/tests/test_free_hindsight_export.py
"""自由意识对外出口测试：Hindsight 沉淀 + 灵感源采集"""
from unittest.mock import patch, MagicMock


class TestHindsightExport:
    @patch("services.free_consciousness_service.get_hindsight_client")
    def test_retain_to_hindsight_writes_memory(self, mock_get_client):
        from services.free_consciousness_service import FreeConsciousnessService
        client = MagicMock()
        mock_get_client.return_value = client

        ok = FreeConsciousnessService.retain_to_hindsight(
            round_number=3, thinking="今天的思考",
            summary="一句话总结", discovery="一个发现",
        )
        assert ok is True
        client.retain.assert_called_once()
        kwargs = client.retain.call_args.kwargs
        assert "第3轮" in kwargs["content"] or "第3轮" in client.retain.call_args.args[1]
        assert kwargs.get("metadata", {}).get("source") == "free-consciousness"

    @patch("services.free_consciousness_service.get_hindsight_client", side_effect=RuntimeError("down"))
    def test_retain_failure_does_not_break(self, mock_g):
        """Hindsight 挂了不能影响沉思主流程"""
        from services.free_consciousness_service import FreeConsciousnessService
        ok = FreeConsciousnessService.retain_to_hindsight(1, "t", None, None)
        assert ok is False


class TestInspirationSource:
    def test_context_bundle_carries_free_thoughts(self):
        """ContextBundle 必须携带 free_thoughts 且进 to_dict"""
        from services.context_collector import ContextBundle
        b = ContextBundle(
            conversations=[], memories=[], weather=None,
            emotion={"valence": 0.0, "arousal": 0.0, "social": 0.0, "dominant": "calm"},
            free_thoughts=["昨夜想着搬家的事"],
        )
        assert b.free_thoughts == ["昨夜想着搬家的事"]
        assert "free_thoughts" in b.to_dict()

    @patch("services.context_collector.active_engine")
    def test_collect_pulls_recent_free_thoughts(self, mock_engine):
        """collect() 从 free_consciousness_logs 取最近 3 条"""
        import asyncio
        from services.context_collector import ContextCollector
        r1 = MagicMock(); r1.summary = "想着旅行"; r1.discovery = None
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [r1]
        c = ContextCollector({"hindsight": {"enabled": False}})
        bundle = asyncio.get_event_loop().run_until_complete(c.collect({"longing": 0.1}))
        assert any("旅行" in x for x in bundle.free_thoughts)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_free_hindsight_export.py -x -q`
预期：FAIL——`retain_to_hindsight` 不存在、`ContextBundle` 无 `free_thoughts`。

- [ ] **步骤 3：实现沉淀回路**

`backend/services/free_consciousness_service.py`：文件顶部补 import `from hindsight_client import Hindsight` 同级位置加 `from services.active_consciousness_service import get_hindsight_client`（就近局部 import 也可，与文件现有风格一致），新增方法（放 `write_log` 之后）：

```python
    @staticmethod
    def retain_to_hindsight(round_number: int, thinking: str,
                            summary: str | None = None,
                            discovery: str | None = None) -> bool:
        """把沉思沉淀进 Hindsight 长期记忆（对外出口）。

        失败只记 warning，绝不影响沉思主流程。
        """
        try:
            from services.active_consciousness_service import (
                ActiveConsciousnessService, get_hindsight_client)
            hs = ActiveConsciousnessService.get_config().get("hindsight", {})
            client = get_hindsight_client(
                base_url=hs.get("base_url", "http://localhost:8888"),
                timeout=hs.get("timeout", 30.0))
            content = f"[自由思考·第{round_number}轮] {summary or thinking[:200]}"
            if discovery:
                content += f"\n发现: {discovery}"
            client.retain(
                bank_id=hs.get("store", {}).get("bank_id", "hermes"),
                content=content,
                metadata={"source": "free-consciousness", "round": str(round_number)})
            return True
        except Exception as e:
            import logging
            logging.getLogger("hermes.free").warning(f"沉思沉淀 Hindsight 失败（不影响主流程）: {e}")
            return False
```

在 `run_contemplation` 中找到成功路径的 `FreeConsciousnessService.write_log(...)` 调用（`grep -n "write_log(" backend/services/free_consciousness_service.py`），在它之后加一行：

```python
            FreeConsciousnessService.retain_to_hindsight(
                round_number, parsed["thinking"], parsed.get("summary"), parsed.get("discovery"))
```

（变量名以该处实际作用域为准——`round_number`、`parsed` 已在上下文。错误路径的 write_log 后**不**调用。）

- [ ] **步骤 4：实现灵感源采集**

`backend/services/context_collector.py`：

1. `ContextBundle` dataclass 增加字段（放 `memories` 之后）：

```python
    free_thoughts: List[str] = None  # 最近自由思考（对外灵感出口）
```

并在 `__post_init__`（若无则在 `to_dict` 前）保证 `if self.free_thoughts is None: self.free_thoughts = []`；`to_dict()` 的返回 dict 增加 `"free_thoughts": self.free_thoughts`。

2. `collect()` 内（`memories = await self._recall_memories(...)` 之后）加：

```python
        # 4. 最近自由思考（想着想着就想找你说话）
        free_thoughts = self._collect_free_thoughts()
```

并把它传进 `ContextBundle(...)` 构造。

3. 新增方法（放 `_recall_memories` 之后）：

```python
    def _collect_free_thoughts(self, limit: int = 3) -> List[str]:
        """最近的自由思考摘要（free_consciousness_logs 的对外出口）"""
        try:
            from models.database import active_engine
            from sqlalchemy import text
            with active_engine.connect() as conn:
                rows = conn.execute(text(
                    """SELECT summary, discovery, thinking FROM free_consciousness_logs
                       WHERE error IS NULL ORDER BY round_number DESC LIMIT :n"""
                ), {"n": limit}).fetchall()
            out = []
            for r in rows:
                s = r.summary or (r.thinking or "")[:120]
                if r.discovery:
                    s += f"（发现：{r.discovery}）"
                if s:
                    out.append(s)
            return out
        except Exception:
            return []
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_free_hindsight_export.py -x -q`
预期：5 passed。全量 `… -m pytest tests/ -x -q` 无回归。
人工验证（可选）：手动触发一轮自由意识后 `curl -X POST "http://127.0.0.1:18720/api/hindsight/recall?query=自由思考&limit=3" -H "Authorization: Bearer <token>"` 能召回。

- [ ] **步骤 6：Commit（由调度方执行）**

```bash
git add backend/services/free_consciousness_service.py backend/services/context_collector.py backend/tests/test_free_hindsight_export.py
git commit -m "feat: export free-consciousness thoughts to Hindsight and thought inspiration"
```

---

### 任务 3：deep_night 适配激活 + 死字段清理

**背景：** `deep_night_start/end/fitness`（`models/active_consciousness.py:57-59`）schema 预留、UI 无、逻辑无读。`max_messages_per_session`（:35）激活为 context 收集上限（顶掉 `context_collector._get_structured_conversations` 写死的 `limit=200`）。`temp_change_threshold`（:74）与 `time_window`（:94，含 `ActiveConsciousnessTimeConfig` 类）确认零引用后删除。

**文件：**
- 修改：`backend/services/active_consciousness_service.py`（新增 `_deep_night_factor`，念头发送决策的打分处乘该因子——定位：`grep -n "score" backend/services/active_consciousness_service.py` 找 decision 评分段，在分数计算后乘因子）
- 修改：`backend/services/thought_engine.py`（`_build_messages` 深夜注入气质提示）
- 修改：`backend/services/context_collector.py`（`_get_structured_conversations` 的默认 limit 读配置）
- 修改：`backend/models/active_consciousness.py`（删 2 个死字段；`max_messages_per_session` 注释更新）
- 修改：`frontend/src/views/ActiveConsciousness.vue`（配置 tab 加 3 个输入）
- 修改：`frontend/src/i18n/locales/zh-CN/activeConsciousness.json`、`…/en-US/activeConsciousness.json`
- 创建：`backend/tests/test_deep_night.py`

- [ ] **步骤 1：编写失败的测试**

```python
# backend/tests/test_deep_night.py
"""深夜适配因子测试"""
from services.active_consciousness_service import _deep_night_factor


class TestDeepNightFactor:
    def test_daytime_full_factor(self):
        assert _deep_night_factor(12.0, 23.5, 7.0, 0.3) == 1.0

    def test_midnight_reduced_factor(self):
        assert _deep_night_factor(2.0, 23.5, 7.0, 0.3) == 0.3

    def test_late_evening_reduced(self):
        assert _deep_night_factor(23.75, 23.5, 7.0, 0.3) == 0.3

    def test_early_morning_reduced(self):
        assert _deep_night_factor(6.5, 23.5, 7.0, 0.3) == 0.3

    def test_boundary_start_exclusive(self):
        assert _deep_night_factor(23.5, 23.5, 7.0, 0.3) == 1.0

    def test_no_midnight_cross(self):
        """同日区间（不跨午夜）也正确"""
        assert _deep_night_factor(23.0, 22.0, 23.5, 0.5) == 0.5
        assert _deep_night_factor(10.0, 22.0, 23.5, 0.5) == 1.0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_deep_night.py -x -q`
预期：FAIL——`ImportError: cannot import name '_deep_night_factor'`。

- [ ] **步骤 3：实现因子与应用**

1. `backend/services/active_consciousness_service.py` 模块级新增（放 `evolve_emotion` 之前）：

```python
def _deep_night_factor(hour: float, start: float, end: float, fitness: float) -> float:
    """深夜时段（[start, end)，支持跨午夜）返回 fitness 折减，其余 1.0。"""
    if start <= end:
        in_night = start <= hour < end
    else:  # 跨午夜，如 23.5 → 7.0
        in_night = hour >= start or hour < end
    return fitness if in_night else 1.0
```

2. 定位念头发送决策的打分处（`grep -n "score" backend/services/active_consciousness_service.py`，在 decision="send" 的比较/概率段）：读取配置 `cfg = ActiveConsciousnessService.get_config()`，取 `tn = cfg.get("time", {})` 或直接按 schema 类取 `deep_night_start/deep_night_end/deep_night_fitness`（字段在 `models/active_consciousness.py:57-59` 所属类，`grep -n "class " models/active_consciousness.py` 确认类名后从 config dict 对应键取，默认 `(23.5, 7.0, 0.3)`），然后：

```python
        from datetime import datetime
        factor = _deep_night_factor(
            datetime.now().hour + datetime.now().minute / 60.0,
            deep_night_start, deep_night_end, deep_night_fitness)
        score *= factor
```

3. `backend/services/thought_engine.py` 的 `_build_messages`：构造 user content 的末尾追加（用当前小时判断，同 `_deep_night_factor` 逻辑，`start/end/fitness` 从 `self.config` 读，默认 `(23.5, 7.0, 0.3)`）：

```python
        from datetime import datetime
        now_h = datetime.now().hour + datetime.now().minute / 60.0
        dn_start = self.config.get("deep_night_start", 23.5)
        dn_end = self.config.get("deep_night_end", 7.0)
        if (dn_start <= dn_end and dn_start <= now_h < dn_end) or \
           (dn_start > dn_end and (now_h >= dn_start or now_h < dn_end)):
            user_content += "\n（现在是深夜，想得更轻、更安静，一句就好。）"
```

4. `backend/services/context_collector.py` 的 `_get_structured_conversations(self, limit: int = 200)`：默认值改为从配置读——`collect()` 调用处传 `limit=self.context_config.get("max_messages_per_session", 200)`（`self.context_config` 已在 `__init__` 存在）。

5. `backend/models/active_consciousness.py`：
   - `max_messages_per_session: int = 15` 注释改为 `# 上下文收集的最大消息条数`
   - 删除 `temp_change_threshold: float = 5.0 ...` 一行
   - 删除 `time_window: ActiveConsciousnessTimeConfig = ...` 一行，以及 `ActiveConsciousnessTimeConfig` 整个类（先 `grep -rn "ActiveConsciousnessTimeConfig" backend/ frontend/` 确认仅此两处引用）

- [ ] **步骤 4：前端配置 UI**

`frontend/src/views/ActiveConsciousness.vue` 配置 tab（`deep_night` 无既有 UI）：在"发送时段/时间格式"输入区之后加三行表单（数据绑定 `config.time.deep_night_start` 等——以该页面 config 加载后的实际嵌套键为准，`grep -n "deep_night" backend/services/active_consciousness_service.py` 看 config dict 落点；若配置走嵌套 `time` 对象则绑 `config.time.*`，否则绑 `config.*`）：

```vue
        <n-form-item :label="t('activeConsciousness.configTab.deepNightStart')">
          <n-input-number v-model:value="config.time.deep_night_start" :min="0" :max="24" :step="0.5" style="width: 120px" />
        </n-form-item>
        <n-form-item :label="t('activeConsciousness.configTab.deepNightEnd')">
          <n-input-number v-model:value="config.time.deep_night_end" :min="0" :max="24" :step="0.5" style="width: 120px" />
        </n-form-item>
        <n-form-item :label="t('activeConsciousness.configTab.deepNightFitness')">
          <n-input-number v-model:value="config.time.deep_night_fitness" :min="0" :max="1" :step="0.1" style="width: 120px" />
        </n-form-item>
```

i18n 两文件的 `activeConsciousness.configTab` 节点加：

```json
"deepNightStart": "深夜开始（小时，如 23.5）",
"deepNightEnd": "深夜结束（小时，如 7）",
"deepNightFitness": "深夜活跃度权重（0-1）"
```

（en-US 用英文："Deep night start (hour)", "Deep night end (hour)", "Deep night activity weight (0-1)"。）

- [ ] **步骤 5：运行测试 + 构建验证**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q` 预期全绿（含 6 个新测试）。
运行：`cd ~/.hermes/hermes-active/frontend && npm run build` 预期 `✓ built`。

- [ ] **步骤 6：Commit（由调度方执行）**

```bash
git add backend/services/active_consciousness_service.py backend/services/thought_engine.py backend/services/context_collector.py backend/models/active_consciousness.py frontend/src/views/ActiveConsciousness.vue frontend/src/i18n/locales/ frontend/tests 2>/dev/null; git add backend/tests/test_deep_night.py
git commit -m "feat: activate deep-night factor and context limit; drop dead config fields"
```

---

### 任务 4：情绪维度统一（单一真相源）

**原则：** 情绪三轴（valence/arousal/social）只属于 `EmotionState`（`get_emotion_state()`，`evolve_emotion` 演化）；关系三维 affection/trust/heat 是慢变关系。**模板占位符名字不变**（`{valence}` 等），DB 旧列保留不再写。消除"三轴开心、六维难过"的双定义。

**文件：**
- 修改：`backend/models/active_consciousness.py`（内心六维 schema 类砍成三维——先 `grep -n "affection\\|class " backend/models/active_consciousness.py` 定位六维类）
- 修改：`backend/services/active_consciousness_service.py`（`merge_emotion`/`merge_emotion_dynamic`/`evaluate_emotion_with_llm` 中对六维 valence/arousal/social 的写入删除，情绪更新只走 `update_emotion_state`）
- 修改：`backend/services/passive_consciousness_service.py`（模板渲染变量 `valence/arousal/social` 改从 `get_emotion_state()` 取——`grep -n "valence" backend/services/passive_consciousness_service.py` 定位）
- 修改：`frontend/src/views/ActiveConsciousness.vue`（六维滑块 → affection/trust/heat 三维；valence/arousal/social 改为只读展示当前情绪值）
- 创建：`backend/tests/test_emotion_single_source.py`

- [ ] **步骤 1：编写失败的测试**

```python
# backend/tests/test_emotion_single_source.py
"""情绪单一真相源测试：模板变量的情绪三轴来自 EmotionState"""
from unittest.mock import patch, MagicMock


class TestSingleSource:
    @patch("services.passive_consciousness_service.get_emotion_state")
    def test_template_valence_reads_emotion_state(self, mock_state):
        """模板 {valence} 必须读 EmotionState，而非关系六维"""
        from services.passive_consciousness_service import PassiveConsciousnessService
        st = MagicMock()
        st.to_dict.return_value = {"valence": 0.42, "arousal": 0.1, "social": 0.3, "dominant": "calm", "label": "平静"}
        mock_state.return_value = st
        ctx = PassiveConsciousnessService._build_emotion_context()  # 名称以实际为准，取模板情绪变量的构建函数
        assert abs(ctx["valence"] - 0.42) < 1e-6

    def test_relation_schema_has_no_valence(self):
        """关系维度 schema 不再定义 valence/arousal/social"""
        import inspect
        import models.active_consciousness as m
        names = []
        for obj in vars(m).values():
            if inspect.isclass(obj) and obj.__module__ == m.__name__:
                names += [f for f in getattr(obj, "model_fields", getattr(obj, "__annotations__", {}))]
        rel = [n for n in names if n in ("affection", "trust", "heat")]
        dup = [n for n in names if n in ("valence", "arousal", "social") and "Emotion" not in str(n)]
        assert rel and not dup
```

（步骤 3 里 `_build_emotion_context` 若函数名不同，测试里同步改成实际函数名——先 `grep -n "def .*emotion.*context\\|emotional_label" backend/services/passive_consciousness_service.py` 定位，测试与实现用同一函数名。）

- [ ] **步骤 2：运行测试验证失败**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_emotion_single_source.py -x -q`
预期：FAIL。

- [ ] **步骤 3：实现统一**

1. `backend/models/active_consciousness.py`：六维状态/配置类中**删除** `valence/arousal/social` 三个字段，保留 `affection/trust/heat`（+ `needs`、`longing` 不动）。DB 列不迁移（保留列不再写）。
2. `backend/services/active_consciousness_service.py`：
   - `merge_emotion`、`merge_emotion_dynamic`：删除对关系 valence/arousal/social 的更新逻辑（情绪变化只经 `update_emotion_state` 写 EmotionState）。
   - `evaluate_emotion_with_llm` 返回的情绪值若有写六维的分支，改为只调 `update_emotion_state`。
3. `backend/services/passive_consciousness_service.py`：模板变量构建处，`valence/arousal/social/label` 从 `get_emotion_state().to_dict()` 取（`from services.active_consciousness_service import get_emotion_state`），`affection/trust/heat` 保持原来源。占位符名字**一律不变**。
4. `frontend/src/views/ActiveConsciousness.vue`：六维滑块区改为——affection/trust/heat 保留可编辑滑块；valence/arousal/social 改为只读文本（展示 `status` 接口返回的当前情绪值），删除对应的写入绑定。
5. 全库 grep 校验：`grep -rn "emotion_state.*valence\\|valence.*六维" backend/ | grep -v test` 应无"双写"残留；`grep -rn "\\.valence" backend/services/` 中 valence 只从 EmotionState 流出。

- [ ] **步骤 4：运行测试验证通过 + 全量回归**

运行：`cd ~/.hermes/hermes-active/backend && ~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q` 预期全绿（重点 `tests/test_v021_emotion.py` 与新测试）。
运行：`cd ~/.hermes/hermes-active/frontend && npm run build` 预期 `✓ built`。

- [ ] **步骤 5：Commit（由调度方执行）**

```bash
git add backend/models/active_consciousness.py backend/services/active_consciousness_service.py backend/services/passive_consciousness_service.py frontend/src/views/ActiveConsciousness.vue backend/tests/test_emotion_single_source.py
git commit -m "refactor: unify emotion model to single source of truth"
```

---

## 自检记录（writing-plans 自检，2026-09-22）

1. **规格覆盖度：** 第一性原理评审 5 项 → 任务 1（假功能）、任务 2（自由意识出口，评审项 2 的回路 A+B）、任务 3（评审项 4 深夜激活+死字段）、任务 4（评审项 3 情绪统一）；学习回路（评审项 5）按计划为第三期远期，不在本计划——已显式声明非遗漏。
2. **占位符扫描：** 无"待定/TODO/添加适当的错误处理"；`send_message_to_target` 签名与 `_build_emotion_context` 函数名允许±就近定位（均已给出 grep 定位命令），其余步骤均为完整代码。
3. **类型一致性：** `ContextBundle.free_thoughts: List[str]` 在任务 2 测试/实现/序列化三处一致；`_deep_night_factor(hour, start, end, fitness)` 六处测试与实现签名一致；`retain_to_hindsight(round_number, thinking, summary, discovery)` 测试与实现一致。

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-09-22-consciousness-loop-refactor.md`。执行方式（用户已指定）：**Claude Code print mode 逐任务后台执行**，任务提示词在 `prompts/` 目录（STRICT RULES 防越界），顺序 1→2→3→4，每任务完成由调度方跑验证清单（git diff --stat 核对文件边界、config 未被改、orphaned code 检查、pytest 全绿）后 commit + push，再发下一任务。
