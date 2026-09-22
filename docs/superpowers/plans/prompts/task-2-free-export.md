# Task: 自由意识对外出口（Hindsight 沉淀 + 灵感源）

## STRICT RULES
- ONLY modify these 3 files: `backend/services/free_consciousness_service.py`、`backend/services/context_collector.py`、`backend/tests/test_free_hindsight_export.py`（新建）。
- Do NOT touch any other files. Do NOT refactor, restructure, or "improve" anything else.
- Do NOT modify `backend/config.py`、`vite.config.js`、`.env`、`package.json`、`backend/database.py`、`backend/main.py`、`backend/models/active.py`。
- Do NOT run git commands. Do NOT delete files.
- 代码注释用中文。项目 Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。

## Context
项目 hermes-active（FastAPI，cwd 即项目根）。背景：`free_consciousness_logs` 日志有内部消费（`load_sediment` 供下轮思考）但**对外零出口**。本次补双回路：①沉思沉淀进 Hindsight 长期记忆（`hindsight_client` SDK 的同步 `retain(bank_id, content, timestamp=None, context=None, document_id=None, metadata=None)`）；②最近自由思考进 `ContextBundle` 供念头生成。Hindsight 配置在 `ActiveConsciousnessService.get_config()` 的 `hindsight` 键下（`get_hindsight_client(base_url, timeout)` 同文件已有）。

## Files to Modify（EXACTLY these 3）

### File 1: `backend/tests/test_free_hindsight_export.py`（新建，先写并确认失败）
```python
"""自由意识对外出口测试：Hindsight 沉淀 + 灵感源采集"""
from unittest.mock import patch, MagicMock
import asyncio


def _run(result):
    return asyncio.get_event_loop().run_until_complete(result) if asyncio.iscoroutine(result) else result


class TestHindsightExport:
    @patch("services.free_consciousness_service.get_hindsight_client")
    def test_retain_to_hindsight_writes_memory(self, mock_get_client):
        from services.free_consciousness_service import FreeConsciousnessService
        client = MagicMock()
        mock_get_client.return_value = client
        ok = FreeConsciousnessService.retain_to_hindsight(
            round_number=3, thinking="今天的思考",
            summary="一句话总结", discovery="一个发现")
        assert ok is True
        client.retain.assert_called_once()
        args = client.retain.call_args
        content = args.kwargs.get("content") or args.args[1]
        assert "第3轮" in content
        assert (args.kwargs.get("metadata") or {}).get("source") == "free-consciousness"

    @patch("services.free_consciousness_service.get_hindsight_client", side_effect=RuntimeError("down"))
    def test_retain_failure_does_not_break(self, mock_g):
        from services.free_consciousness_service import FreeConsciousnessService
        ok = FreeConsciousnessService.retain_to_hindsight(1, "t", None, None)
        assert ok is False


class TestInspirationSource:
    def test_context_bundle_carries_free_thoughts(self):
        from services.context_collector import ContextBundle
        b = ContextBundle(
            conversations=[], memories=[], weather=None,
            emotion={"valence": 0.0, "arousal": 0.0, "social": 0.0, "dominant": "calm"},
            free_thoughts=["昨夜想着搬家的事"])
        assert b.free_thoughts == ["昨夜想着搬家的事"]
        assert "free_thoughts" in b.to_dict()

    @patch("services.context_collector.active_engine")
    def test_collect_pulls_recent_free_thoughts(self, mock_engine):
        from services.context_collector import ContextCollector
        r1 = MagicMock(); r1.summary = "想着旅行"; r1.discovery = None; r1.thinking = "长文本"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [r1]
        c = ContextCollector({"hindsight": {"enabled": False}})
        bundle = _run(c.collect({"longing": 0.1}))
        assert any("旅行" in x for x in bundle.free_thoughts)
```
注意：`ContextBundle` 的实际构造参数以 `backend/services/context_collector.py` 现有 dataclass 定义为准（可能有更多字段），测试里的构造补上必需参数（看 `__init__`/字段定义），`free_thoughts` 给默认 `None` 时实现方负责转 `[]`。

### File 2: `backend/services/free_consciousness_service.py`
在 `write_log` 方法之后新增（`get_hindsight_client` 从 `services.active_consciousness_service` 局部 import）：
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
`get_hindsight_client` 若不在 `active_consciousness_service` 里（用 `grep -n "def get_hindsight_client" backend/services/*.py` 定位真实位置），import 路径跟着改。
然后 `grep -n "write_log(" backend/services/free_consciousness_service.py` 找 `run_contemplation` 成功路径的 `write_log(...)` 调用，在其后加：
```python
            FreeConsciousnessService.retain_to_hindsight(
                round_number, parsed["thinking"], parsed.get("summary"), parsed.get("discovery"))
```
（变量名以该处实际作用域为准。错误路径的 write_log 后不调用。）

### File 3: `backend/services/context_collector.py`
1) `ContextBundle` dataclass 加字段（放 `memories` 字段后）：`free_thoughts: List[str] = None  # 最近自由思考（对外灵感出口）`；在 `to_dict()` 里保证 None→[] 并输出 `"free_thoughts": self.free_thoughts`。
2) `collect()` 内 `memories = await self._recall_memories(...)` 之后加 `free_thoughts = self._collect_free_thoughts()`，并传入 `ContextBundle(...)` 构造。
3) `_recall_memories` 之后新增：
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
（`active_engine` 的 import 路径以 `models/database.py` 实际导出为准，先 `grep -n "active_engine" backend/models/database.py` 确认。）

## Verification（必须全部通过才算完成）
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_free_hindsight_export.py -x -q  # 5 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q                              # 全绿无回归
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m py_compile services/free_consciousness_service.py services/context_collector.py
```

## After making changes
输出改动摘要（每文件一行）。不跑 git 命令。
