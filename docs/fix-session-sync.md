# 修复：hermes-active 与 Gateway SessionStore 不同步

## 问题描述

hermes-active 的 `get_or_create_active_session()` 每次调用都 **新建一个 `SessionStore` 实例**。
这个实例和 Gateway 运行中的 `SessionStore` 是完全独立的两个对象，导致：

1. hermes-active 创建的 session 只更新了 `sessions.json` 和新实例的内存
2. Gateway 运行中的 `SessionStore` 内存从未 reload，仍持有旧 session
3. 用户发消息时，Gateway 用自己的旧 entry 判断 `_should_reset()`，又创建了新 session
4. 主动消息和用户消息被分散到两个不同的 session 中

### 时间线（2026-06-14 实际发生）

```
06:00:00  hermes-active 创建新 SessionStore → daily reset → 创建 session_060000
06:00~08:20  主动消息写入 session_060000（8条 assistant 消息）
09:12:52  用户发消息 → Gateway 的 SessionStore（旧 entry）→ daily reset → 创建 session_091252
          session_060000 的主动消息从此"孤立"，不在用户的对话上下文中
```

## 修改方案

### 核心思路

**Gateway 是 session 的唯一权威来源。** hermes-active 不再自己创建 `SessionStore`，
改为调用 Gateway 已有的 `api_server` HTTP 接口获取/创建 session。

---

### 改动 1：Gateway 端 — APIServerAdapter 注入 gateway_runner

**文件**: `~/.hermes/hermes-agent/gateway/run.py` (line ~6163)

当前代码：
```python
elif platform == Platform.API_SERVER:
    from gateway.platforms.api_server import APIServerAdapter, check_api_server_requirements
    if not check_api_server_requirements():
        logger.warning("API Server: aiohttp not installed")
        return None
    return APIServerAdapter(config)
```

改为（参照 WebhookAdapter 的模式，line 6171）：
```python
elif platform == Platform.API_SERVER:
    from gateway.platforms.api_server import APIServerAdapter, check_api_server_requirements
    if not check_api_server_requirements():
        logger.warning("API Server: aiohttp not installed")
        return None
    adapter = APIServerAdapter(config)
    adapter.gateway_runner = self  # 注入 Gateway 引用，供 session API 使用
    return adapter
```

---

### 改动 2：Gateway 端 — 新增 `get_or_create` API 端点

**文件**: `~/.hermes/hermes-agent/gateway/platforms/api_server.py`

#### 2a. 注册路由（在 line ~4172 的路由注册处）

```python
self._app.router.add_post("/api/sessions/get_or_create", self._handle_get_or_create_session)
```

#### 2b. 新增 handler 方法

```python
async def _handle_get_or_create_session(self, request: "web.Request") -> "web.Response":
    """POST /api/sessions/get_or_create

    使用 Gateway 的 SessionStore 获取现有 session 或创建新 session。
    自动处理 session 过期重置（daily/idle）。

    Request body:
        platform: str  — 平台名，如 "weixin"
        user_id: str   — 用户 ID（微信私聊时 = chat_id）
        chat_type: str — 可选，默认 "dm"

    Response:
        {
            "session_id": "...",
            "session_key": "...",
            "was_auto_reset": false,
            "auto_reset_reason": null
        }
    """
    auth_err = self._check_auth(request)
    if auth_err:
        return auth_err

    body, err = await self._read_json_body(request)
    if err:
        return err

    platform = body.get("platform")
    user_id = body.get("user_id")
    chat_type = body.get("chat_type", "dm")

    if not platform or not user_id:
        return web.json_response(
            _openai_error("platform and user_id are required", code="invalid_params"),
            status=400,
        )

    # 通过 gateway_runner 访问 Gateway 的 SessionStore
    gateway = getattr(self, "gateway_runner", None)
    if not gateway or not getattr(gateway, "session_store", None):
        return web.json_response(
            _openai_error("Gateway session store unavailable", code="internal_error"),
            status=503,
        )

    from gateway.session import SessionSource
    from gateway.config import Platform as GatewayPlatform

    # Platform 枚举转换
    try:
        gw_platform = GatewayPlatform(platform)
    except (ValueError, KeyError):
        return web.json_response(
            _openai_error(f"Unknown platform: {platform}", code="invalid_platform"),
            status=400,
        )

    source = SessionSource(
        platform=gw_platform,
        chat_id=user_id,
        chat_type=chat_type,
        user_id=user_id,
    )

    entry = gateway.session_store.get_or_create_session(source)

    return web.json_response({
        "session_id": entry.session_id,
        "session_key": entry.session_key,
        "was_auto_reset": getattr(entry, "was_auto_reset", False),
        "auto_reset_reason": getattr(entry, "auto_reset_reason", None),
    })
```

---

### 改动 3：hermes-active 端 — 改用 Gateway API

**文件**: `~/.hermes/hermes-active/backend/services/session_service.py`

将 `get_or_create_active_session()` 从"自己创建 SessionStore"改为"调用 Gateway API"：

```python
@staticmethod
async def get_or_create_active_session(platform: str, user_id: str) -> Optional[Dict[str, Any]]:
    """获取或创建活跃 session（通过 Gateway API）

    调用 Gateway 运行中的 SessionStore，确保 session 状态同步。
    不再自己创建 SessionStore 实例。
    """
    import os
    import httpx

    gateway_url = os.getenv("GATEWAY_API_URL", "http://127.0.0.1:8642")
    api_key = os.getenv("API_SERVER_KEY", "")

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{gateway_url}/api/sessions/get_or_create",
                json={
                    "platform": platform,
                    "user_id": user_id,
                    "chat_type": "dm",
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data["session_id"],
                "source": platform,
                "user_id": user_id,
                "created_at": None,
                "was_auto_reset": data.get("was_auto_reset", False),
                "auto_reset_reason": data.get("auto_reset_reason"),
            }
    except Exception as e:
        logger.error(f"调用 Gateway session API 失败: {e}")
        return None
```

**关键变化**：
- 从同步 → 异步（`async def`）
- 从自己创建 `SessionStore` → 调用 Gateway HTTP API
- 删除了 `import sys, Path, yaml, SessionStore, GatewayConfig` 等依赖

---

### 改动 4：调用方适配

**文件**: `~/.hermes/hermes-active/backend/services/scheduler_service.py` (line 111)

`run_cron_job()` 已经是 `async def`（line 68），直接加 `await`：

```python
# 之前（同步调用）：
session = SessionService.get_or_create_active_session(platform=platform, user_id=user_id)

# 之后（异步调用）：
session = await SessionService.get_or_create_active_session(platform=platform, user_id=user_id)
```

---

### 改动 5：依赖检查

hermes-active 需要 `httpx`。检查是否已安装：

```bash
cd ~/.hermes/hermes-active/backend && pip show httpx
```

如果没有，添加到 requirements.txt：
```
httpx>=0.24.0
```

---

### 不需要改动的部分

- **`MessageService.send_message()`** — 继续直接写 `state.db`。消息写入是 DB 层面的操作，
  Gateway 的 SessionStore 不管理消息内容，只管理 session 生命周期。
- **`_send_to_weixin()` / `_send_to_feishu()`** — 继续通过适配器发送消息。
- **Gateway 的 `SessionStore`** — 不需要加 reload 机制。hermes-active 不再绕过它了。

### 潜在风险

1. **Gateway API Server 未启用**: 如果用户的 config.yaml 没有启用 api_server 平台，
   端口 8642 不会监听，hermes-active 的调用会失败。
   → 需要在 hermes-active 启动时检查并给出提示。
   → 或者在 config.yaml 中默认启用 api_server。

2. **Gateway 重启时短暂不可用**: hermes-active 的定时任务可能在 Gateway 重启期间失败。
   → 已有 try/except，建议加重试（3次，间隔2秒）。

3. **`get_or_create_active_session` 从同步变异步**: 所有调用方都需要改成 `await`。
   → 已确认 `run_cron_job` 是 async 的，影响可控。

### 验证步骤

1. 改完后重启 Gateway：
   ```bash
   hermes restart
   ```
2. 验证新端点可用：
   ```bash
   curl -X POST http://127.0.0.1:8642/api/sessions/get_or_create \
     -H "Content-Type: application/json" \
     -d '{"platform":"weixin","user_id":"o9cq800B700qFq20-npef3QLNKSQ@im.wechat"}'
   ```
3. 重启 hermes-active，触发一个定时任务，检查日志确认调用了 Gateway API
4. 等待下一次 daily reset，确认主动消息和用户消息在同一个 session 中

### 回滚方案

1. 恢复 `session_service.py` 中的 `get_or_create_active_session` 原始实现
2. 恢复 `scheduler_service.py` 中的同步调用
3. Gateway 端的新端点和 `gateway_runner` 注入可以保留（不影响现有功能）

---

## 涉及文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `~/.hermes/hermes-agent/gateway/run.py` | 修改 1 行 | APIServerAdapter 注入 gateway_runner |
| `~/.hermes/hermes-agent/gateway/platforms/api_server.py` | 新增路由 + handler | `POST /api/sessions/get_or_create` |
| `~/.hermes/hermes-active/backend/services/session_service.py` | 重写方法 | 改用 Gateway API |
| `~/.hermes/hermes-active/backend/services/scheduler_service.py` | 改 1 行 | 加 `await` |
