# 修复：hermes-active 与 Gateway SessionStore 不同步

## 问题描述

hermes-active 的 `get_or_create_active_session()` 每次调用都 **新建一个 `SessionStore` 实例**，
导致 Gateway 进程内的内存状态和 state.db 不同步。

## 修改方案（方案 B：Gateway DB fallback）

### 核心思路

只改 **1 个文件**：`gateway/session.py`，约 20 行。

在 `get_or_create_session()` 的 `else` 分支（session_key 不在 _entries 中时），
加一个 state.db 查询 fallback。如果 DB 里有其他进程创建的活跃 session，
直接注入到 _entries 并返回，不创建新 session。

hermes-active 代码 **不需要改动**。

### 具体改动

**文件**: `~/.hermes/hermes-agent/gateway/session.py`

**位置**: `get_or_create_session()` 方法，line 929 的 `else` 分支

**当前代码** (line 929-932):
```python
            else:
                was_auto_reset = False
                auto_reset_reason = None
                reset_had_activity = False
```

**改为**:
```python
            else:
                # ── state.db fallback ──────────────────────────────────────
                # Another process (e.g. hermes-active) may have created an
                # active session that isn't in our in-memory _entries.
                # Query state.db to avoid creating a duplicate session.
                # hermes_state.SessionDB.get_active_session_by_source() was
                # designed for exactly this case (see its docstring).
                if self._db and not force_new:
                    try:
                        db_row = self._db.get_active_session_by_source(
                            source.platform.value, source.user_id,
                        )
                    except Exception:
                        db_row = None
                    if db_row is not None:
                        db_session_id = db_row["id"]
                        _started = db_row.get("started_at")
                        _created = (
                            datetime.fromtimestamp(_started)
                            if isinstance(_started, (int, float))
                            else now
                        )
                        entry = SessionEntry(
                            session_key=session_key,
                            session_id=db_session_id,
                            created_at=_created,
                            updated_at=now,       # ← fresh, prevents _should_reset
                            origin=source,
                            display_name=source.chat_name,
                            platform=source.platform,
                            chat_type=source.chat_type,
                            # no auto-reset notice — this is a recovery, not a reset
                        )
                        self._entries[session_key] = entry
                        self._save()
                        return entry

                # Normal path: create a brand-new session
                was_auto_reset = False
                auto_reset_reason = None
                reset_had_activity = False
```

### 关键设计决策

1. **不走 `_should_reset`** — DB fallback 注入的 entry 直接返回。
   因为 DB 里的 session 是 hermes-active 刚创建的（通常几小时内），
   `_should_reset` 的 daily 检查会因为 `created_at < today_reset` 而立刻触发，
   又创建新 session，违背了 fallback 的目的。

2. **`updated_at = now`** — 标记为"刚刚活跃"，防止 idle reset。
   下次用户真正发消息时，Gateway 的正常流程会接管。

3. **`was_auto_reset = False`** — 不注入"session 已重置"的提示，
   因为对用户来说这不是重置，只是 Gateway 重新发现了已有 session。

4. **`force_new` 保护** — 如果用户发了 `/new` 或 `/reset`，`force_new=True`，
   跳过 DB fallback，强制创建新 session。

### 不需要改动的部分

- **hermes-active** — 不需要改任何代码。它继续用自己的 SessionStore 创建 session、写 state.db。
- **Gateway api_server** — 不需要加新端点。
- **config.yaml** — 不需要改配置。

### 潜在风险

1. **过期 session 复用**: 如果 hermes-active 创建了一个 session 但 Gateway 停了很久才重启，
   DB 里的 session 可能是"过期"的（几天前的）。但因为 `updated_at = now`，
   Gateway 不会触发 reset，会继续用这个旧 session。
   → **风险低**: hermes-active 每天都会创建新 session，旧的会被 ended。

2. **`get_active_session_by_source` 匹配问题**: 需要确保 hermes-active 创建的 session
   的 `source` 和 `user_id` 字段格式与 Gateway 的一致。
   → 已确认：hermes-active 用 `source="weixin"`, `user_id="o9cq800B..."`，
   Gateway 用 `source.platform.value="weixin"`, `source.user_id="o9cq800B..."`，格式一致。

### 验证步骤

1. 改完后重启 Gateway
2. 触发 hermes-active 的一个定时任务（创建 session 并写入 state.db）
3. 从微信发消息 → 检查是否复用了 hermes-active 创建的 session
4. 检查日志确认没有创建新 session

### 回滚

删除 `session.py` 中添加的 20 行代码即可，不影响任何其他逻辑。

---

## 涉及文件清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `~/.hermes/hermes-agent/gateway/session.py` | 加 ~20 行 | else 分支加 DB fallback |

**只改 1 个文件，hermes-active 零改动。**
