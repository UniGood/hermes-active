# Task: 念头重试补全（重试发送，不是重新生成）

## STRICT RULES
- ONLY modify these 3 files: `backend/services/active_consciousness_service.py`、`backend/routers/active_consciousness.py`（仅 retry 端点一行加 await）、`backend/tests/test_retry_thought.py`（新建）。
- Do NOT touch any other files. Do NOT refactor, restructure, or "improve" anything else.
- Do NOT modify `backend/config.py`、`vite.config.js`、`.env`、`package.json`、`backend/database.py`、`backend/main.py`。
- Do NOT run git commands（commit 由调度方执行）. Do NOT delete files.
- 代码注释用中文。项目 Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。

## Context
项目 hermes-active（FastAPI 后端，目录即你的 cwd）。`ActiveConsciousnessService.retry_thought`（约 :1037-1040）现在是假实现：`# TODO: 实现重试逻辑` + 返回"重试功能待实现"。语义：**对已生成的念头重新执行发送**（docstring"重试发送念头"），不是重新生成。发送链路已有：`send_message_to_target`（async）与 `check_send_protection`（同文件）。

## Files to Modify（EXACTLY these 3）

### File 1: `backend/tests/test_retry_thought.py`（新建，先写它并运行确认失败）
```python
"""retry_thought 重试发送念头测试"""
from unittest.mock import patch, MagicMock
import asyncio

from services.active_consciousness_service import ActiveConsciousnessService


def _run(result):
    return asyncio.get_event_loop().run_until_complete(result) if asyncio.iscoroutine(result) else result


class TestRetryThought:
    @patch("services.active_consciousness_service.send_message_to_target")
    @patch("services.active_consciousness_service.check_send_protection")
    @patch("services.active_consciousness_service.active_engine")
    def test_retry_sends_existing_thought(self, mock_engine, mock_protect, mock_send):
        mock_protect.return_value = (True, "ok")
        mock_send.return_value = (True, {"platform": "weixin"})
        row = MagicMock()
        row.id, row.content = 7, "测试念头内容"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row
        result = _run(ActiveConsciousnessService.retry_thought(7))
        assert result["success"] is True
        mock_send.assert_called_once()
        assert "测试念头内容" in str(mock_send.call_args)

    @patch("services.active_consciousness_service.active_engine")
    def test_retry_missing_thought(self, mock_engine):
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
        result = _run(ActiveConsciousnessService.retry_thought(999))
        assert result["success"] is False
        assert "不存在" in result["error"]

    @patch("services.active_consciousness_service.check_send_protection")
    @patch("services.active_consciousness_service.active_engine")
    def test_retry_blocked_by_protection(self, mock_engine, mock_protect):
        mock_protect.return_value = (False, "夜间免打扰")
        row = MagicMock()
        row.id, row.content = 3, "x"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row
        result = _run(ActiveConsciousnessService.retry_thought(3))
        assert result["success"] is False
        assert "免打扰" in result["error"] or "保护" in result["error"]
```

### File 2: `backend/services/active_consciousness_service.py`
把整个 `retry_thought`（含 `@staticmethod` 和 docstring，约 :1035-1040）替换为：
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
实现前先 `grep -n "async def send_message_to_target" backend/services/active_consciousness_service.py` 看它的真实参数——若需要 target/platform 参数且念头表里有对应列，则在 SELECT 里带出并传入；若只接 content，按上面写法。

### File 3: `backend/routers/active_consciousness.py`
`retry_thought` 路由端点（`POST /thoughts/{id}/retry`）：由于 service 改为 async，路由处理函数改为 async def 并 `await ActiveConsciousnessService.retry_thought(...)`。只改这一个端点。

## Verification（必须全部通过才算完成）
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_retry_thought.py -x -q   # 3 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q                        # 全绿无回归
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m py_compile services/active_consciousness_service.py routers/active_consciousness.py
```

## After making changes
输出改动摘要（每文件一行）。不跑 git 命令。
