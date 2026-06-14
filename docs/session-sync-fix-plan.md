# Session 同步修复 — 实施方案

## 问题根因（源码验证）

Gateway 内部有两条独立的数据通道，互不相通：

```
通道 1: SessionStore (内存 + sessions.json)
  - gateway/session.py:715 — `if self._loaded: return` 只加载一次
  - 用户消息路由用这个：run.py:7761 `session_store.get_or_create_session(source)`

通道 2: API Server 的 SessionDB (直接读写 state.db)
  - api_server.py:986-995 — 自己创建独立的 SessionDB() 实例
  - POST /api/sessions → db.create_session() 只写 state.db
  - 完全不碰 SessionStore 的 _entries 和 sessions.json
```

当 hermes-active 通过 `POST /api/sessions` 创建 session：
- ✅ state.db 里有了记录
- ❌ sessions.json 没更新
- ❌ Gateway 的 _entries 内存里没有
- → 用户发消息时 Gateway 在 _entries 找不到 → 又创建新 session → 分裂

## 解决方案：state.db fallback

**核心思路**：Gateway 的 `get_or_create_session()` 在内存找不到时，自动查 state.db 作为 fallback。

```
修复后流程：
hermes-active 调用 POST /api/sessions → 写入 state.db
用户发消息 → Gateway.get_or_create_session()
  → _entries 找不到 → fallback 查 state.db
  → 找到 → 创建 SessionEntry 加入 _entries → 返回
  → 后续请求直接从 _entries 命中
```

**优点**：
- hermes-active 现有代码只需改一行（调用 API 而非创建 SessionStore）
- Gateway 改动最小：1 个新方法 + 1 个 fallback 逻辑
- 不需要新端点、不需要注入 gateway_runner、不需要 reload

## 改动清单

### 改动 1：hermes_state.py — 新增查询方法（加方法，不改方法）

**文件**: `~/.hermes/hermes-agent/hermes_state.py`

在 SessionDB 类中新增一个方法：

```python
def get_active_session_by_source(self, source: str, user_id: str) -> Optional[Dict[str, Any]]:
    """查找指定平台+用户的活跃 session（ended_at IS NULL）

    用于 Gateway SessionStore 的 state.db fallback。
    """
    with self._lock:
        cursor = self._conn.execute(
            "SELECT id, source, user_id, started_at, ended_at, title "
            "FROM sessions "
            "WHERE source = ? AND user_id = ? AND ended_at IS NULL "
            "ORDER BY started_at DESC LIMIT 1",
            (source, user_id),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return dict(row) if not isinstance(row, dict) else row
```

### 改动 2：gateway/session.py — get_or_create_session 添加 fallback（加逻辑，不改原有逻辑）

**文件**: `~/.hermes/hermes-agent/gateway/session.py`

在 `get_or_create_session()` 方法中，当 `session_key not in self._entries` 且 `force_new=False` 时，在创建新 session 之前，先查 state.db：

```python
# 在 line 929 的 else: 分支内（即 session_key not in self._entries 或 force_new=True）
# 在 "Create new session" (line 934) 之前插入 fallback：

        else:
            was_auto_reset = False
            auto_reset_reason = None
            reset_had_activity = False

            # ── state.db fallback ────────────────────────────────
            # 如果内存中找不到，查 state.db 看是否有 API 创建的活跃 session
            if not force_new and self._db is not None:
                try:
                    db_session = self._db.get_active_session_by_source(
                        source.platform.value, source.user_id
                    )
                    if db_session is not None:
                        # 从 state.db 加载到内存
                        db_session_id = db_session["id"]
                        db_started_at = db_session.get("started_at")
                        if isinstance(db_started_at, (int, float)):
                            db_started_at = datetime.fromtimestamp(db_started_at)
                        elif db_started_at is None:
                            db_started_at = now

                        entry = SessionEntry(
                            session_key=session_key,
                            session_id=db_session_id,
                            created_at=db_started_at,
                            updated_at=now,
                            origin=source,
                            display_name=source.chat_name,
                            platform=source.platform,
                            chat_type=source.chat_type,
                        )
                        self._entries[session_key] = entry
                        self._save()
                        return entry
                except Exception as e:
                    logger.debug("state.db fallback failed: %s", e)

            # ── 原有的 "Create new session" 逻辑继续 ──────────────
```

### 改动 3：hermes-active session_service.py — 改用 Gateway API（改方法）

**文件**: `~/.hermes/hermes-active/backend/services/session_service.py`

将 `get_or_create_active_session()` 从"自己创建 SessionStore"改为"调用 Gateway API"：

```python
@staticmethod
def get_or_create_active_session(platform: str, user_id: str) -> Optional[Dict[str, Any]]:
    """获取或创建活跃 session（通过 Gateway API）

    调用 Gateway 运行中的 SessionStore，确保 session 状态同步。
    不再自己创建 SessionStore 实例。
    """
    import os
    import json as _json
    import urllib.request
    import urllib.error

    gateway_url = os.getenv("GATEWAY_API_URL", "http://127.0.0.1:8642")
    api_key = os.getenv("API_SERVER_KEY", "")

    # 调用 Gateway 的 POST /api/sessions 创建 session（如果不存在）
    # Gateway API 写入 state.db，Gateway 的 SessionStore fallback 会自动加载
    try:
        payload = _json.dumps({
            "source": platform,
            "user_id": user_id,
        }).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(
            f"{gateway_url}/api/sessions",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            session = data.get("session", data)
            return {
                "id": session.get("id") or session.get("session_id"),
                "source": platform,
                "user_id": user_id,
                "created_at": None,
                "was_auto_reset": False,
                "auto_reset_reason": None,
            }
    except urllib.error.HTTPError as e:
        # 409 = session already exists — 这是正常的，说明已有活跃 session
        if e.code == 409:
            # 从 state.db 获取已存在的 session
            try:
                from models.database import get_state_metadata, state_engine
                from sqlalchemy import text
                metadata = get_state_metadata()
                if 'sessions' in metadata.tables:
                    with state_engine.connect() as conn:
                        result = conn.execute(
                            text("SELECT id FROM sessions WHERE source = :source AND user_id = :user_id AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1"),
                            {"source": platform, "user_id": user_id}
                        )
                        row = result.first()
                        if row:
                            return {
                                "id": row[0],
                                "source": platform,
                                "user_id": user_id,
                                "created_at": None,
                                "was_auto_reset": False,
                                "auto_reset_reason": None,
                            }
            except Exception:
                pass
        import logging
        logging.getLogger("hermes.session").error(f"调用 Gateway session API 失败: {e}")
        return None
    except Exception as e:
        import logging
        logging.getLogger("hermes.session").error(f"调用 Gateway session API 失败: {e}")
        return None
```

**关键变化**：
- 删除了 `import sys, Path, yaml, SessionStore, GatewayConfig, Platform` 等依赖
- 不再创建 SessionStore 实例
- 使用标准库 urllib（不引入新依赖 httpx）
- 409 冲突处理：session 已存在时从 state.db 查询

### 不需要改动的部分

- **Gateway 的 `_create_adapter`** — 不需要注入 gateway_runner
- **Gateway 的 api_server.py** — 不需要新端点
- **MessageService** — 消息写入继续直接写 state.db
- **scheduler_service.py** — 调用方不需要改（get_or_create_active_session 签名不变）

## 验证步骤

1. 重启 Gateway：`hermes restart`
2. 验证 fallback 生效：
   - 通过 API 创建 session：`curl -X POST http://127.0.0.1:8642/api/sessions -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{"source":"weixin","user_id":"o9cq800B700qFq20-npef3QLNKSQ@im.wechat"}'`
   - 检查 Gateway 日志是否显示 fallback 加载
3. 重启 hermes-active，触发定时任务
4. 用户发消息，确认主动消息和用户消息在同一个 session

## 回滚方案

1. 恢复 `session_service.py` 的原始实现
2. 恢复 `session.py` 的原始 get_or_create_session
3. 删除 `hermes_state.py` 的新方法
4. 重启 Gateway

## 涉及文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `~/.hermes/hermes-agent/hermes_state.py` | 新增方法 | `get_active_session_by_source()` |
| `~/.hermes/hermes-agent/gateway/session.py` | 修改方法 | `get_or_create_session()` 添加 fallback |
| `~/.hermes/hermes-active/backend/services/session_service.py` | 重写方法 | 改用 Gateway API |
