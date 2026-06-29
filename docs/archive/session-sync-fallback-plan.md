# Session Sync Fallback — 实施方案 v2

## 问题根因

Gateway 内部有两条独立的数据通道，互不相通：

```
通道 1: SessionStore (内存 + sessions.json)
  - gateway/session.py:715 — `if self._loaded: return` 只加载一次
  - 用户消息路由用这个：get_or_create_session(source)

通道 2: API Server / SessionDB (直接读写 state.db)
  - api_server.py:986-995 — 自己创建独立的 SessionDB() 实例
  - POST /api/sessions → db.create_session() 只写 state.db
  - 完全不碰 SessionStore 的 _entries 和 sessions.json
```

当 hermes-active 通过 `POST /api/sessions` 创建 session：
- ✅ state.db 里有了记录
- ❌ sessions.json 没更新
- ❌ Gateway 的 _entries 内存里没有
- → 用户发消息时 Gateway 在 _entries 找不到 → 又创建新 session → session 分裂

## 设计约束

1. **能不改动 > 改动** — 尽量不修改 hermes-agent 的现有文件
2. **加方法 > 改方法** — 如果必须改，优先新增方法，不改原有方法
3. **新文件 > 改原文件** — 优先创建新文件

## 架构图

### 改动前（有问题）

```
┌──────────────────────┐          ┌──────────────────────┐
│    hermes-active     │          │       Gateway        │
│                      │          │                      │
│  SessionStore(新建)   │          │  SessionStore(长期)   │
│  ├─ 加载 sessions.json│          │  ├─ _entries (内存)   │
│  ├─ 找不到 → 创建新   │          │  ├─ 只加载一次        │
│  └─ 写 sessions.json │          │  └─ 无 fallback      │
│                      │          │         │             │
│  调用 POST /api/     │──────────│  API Server           │
│  sessions            │          │  └─ 写 state.db       │
└──────────────────────┘          └──────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────┐
                    │            state.db                   │
                    │  sessions: api_server + weixin 各一条  │
                    │  (session 分裂！)                      │
                    └──────────────────────────────────────┘
```

### 改动后（fallback 生效）

```
┌──────────────────────┐          ┌──────────────────────────────────┐
│    hermes-active     │          │           Gateway                │
│                      │          │                                  │
│  FallbackSessionSvc  │          │  PatchedSessionStore             │
│  ├─ 直接查 state.db  │          │  ├─ _entries (内存)              │
│  ├─ 找到 → 返回      │          │  ├─ get_or_create_session()      │
│  └─ 没找到 → 跳过    │          │  │   ├─ _entries 找到 → 返回     │
│                      │          │  │   └─ 找不到 → fallback ↓      │
│  (不再创建 SessionStore)         │  │       ├─ 查 state.db          │
│                      │          │  │       ├─ 找到 → 注入 _entries  │
│                      │          │  │       └─ 没找到 → 创建新       │
│                      │          │  └─                            │
└──────────────────────┘          └──────────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────┐
                    │            state.db                   │
                    │  sessions: 只有一条（统一！）            │
                    └──────────────────────────────────────┘
```

## 改动清单

### 总览

| # | 文件 | 改动类型 | 说明 |
|---|------|---------|------|
| 1 | `hermes-agent/hermes_state.py` | **新增方法** | `get_active_session_by_source()` — 按 source+user_id 查活跃 session |
| 2 | `hermes-agent/gateway/extensions/session_fallback.py` | **新建文件** | `PatchedSessionStore` 子类 + `install_fallback()` 函数 |
| 3 | `hermes-agent/gateway/run.py` | **最小修改** (1行) | `SessionStore` → `install_fallback(SessionStore)` |
| 4 | `hermes-active/backend/services/fallback_session_service.py` | **新建文件** | 直接查 state.db 的 session 服务 |
| 5 | `hermes-active/backend/services/scheduler_service.py` | **最小修改** (1行 import + 1行调用) | 改用 FallbackSessionService |
| 6 | `hermes-active/backend/routers/sessions.py` | **最小修改** (1行 import + 1行调用) | 改用 FallbackSessionService |

**约束满足统计**：
- 新建文件：2 个
- 新增方法：1 个
- 修改现有方法：**0 个**（不改 `get_or_create_session` 本身）
- 现有文件最小修改：3 处（每处 1-2 行）

---

### 改动 1：hermes_state.py — 新增查询方法

**文件**: `~/.hermes/hermes-agent/hermes_state.py`
**改动类型**: 新增方法（不改任何现有方法）
**位置**: 在 `get_session()` 方法（line 1593）之后添加

```python
def get_active_session_by_source(
    self, source: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """查找指定 source + user_id 的活跃 session（ended_at IS NULL）。

    用于 Gateway SessionStore 的 state.db fallback：
    当 _entries 内存中找不到 session 时，从 state.db 查询 API Server
    创建的 session 记录，避免 session 分裂。

    返回最新的一条（started_at DESC），如果没有活跃 session 返回 None。
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

**说明**：
- 只查 `ended_at IS NULL` 的活跃 session
- 按 `started_at DESC` 排序取最新的一条
- 使用 `source + user_id` 而非 `session_key`，因为 state.db 的 sessions 表没有 `session_key` 列
- 线程安全（使用 `self._lock`）

---

### 改动 2：新建 gateway/extensions/session_fallback.py

**文件**: `~/.hermes/hermes-agent/gateway/extensions/session_fallback.py`
**改动类型**: 新建文件

```python
"""
Session Store Fallback — state.db 查询兜底

当 SessionStore.get_or_create_session() 在内存 _entries 中找不到 session 时，
自动查询 state.db 作为 fallback，将找到的 session 注入 _entries。

这解决了 API Server (POST /api/sessions) 创建的 session 不会同步到
Gateway SessionStore 内存的问题。

用法（在 run.py 中）：
    from gateway.extensions.session_fallback import install_fallback
    SessionStore = install_fallback(SessionStore)
    # 之后正常使用 SessionStore 即可
"""

import logging
from datetime import datetime
from typing import Optional, Type

logger = logging.getLogger(__name__)


def _make_fallback_mixin(Base: Type) -> Type:
    """创建一个包含 state.db fallback 行为的 mixin 类。

    通过覆盖 get_or_create_session() 实现：
    1. 先调用原始逻辑（super）
    2. 如果原始逻辑创建了新 session（was_auto_reset=False 且 session 刚创建），
       检查 state.db 是否有已存在的活跃 session
    3. 如果有，用 state.db 的 session_id 替换刚创建的

    但上面的方案需要判断"刚创建"，不够优雅。

    更好的方案：在调用 super() 之前，先检查 state.db，
    如果找到了就预注入 _entries，让 super() 自然命中。
    """

    class FallbackSessionStore(Base):
        """带 state.db fallback 的 SessionStore 子类。"""

        def get_or_create_session(self, source, force_new=False):
            """带 fallback 的 get_or_create_session。

            流程：
            1. 如果不是 force_new，先查 state.db 看是否有 API 创建的活跃 session
            2. 如果找到了且不在 _entries 中，注入 _entries
            3. 调用原始逻辑（会从 _entries 命中）
            """
            if not force_new and self._db is not None:
                try:
                    self._inject_from_db_if_needed(source)
                except Exception as e:
                    logger.debug("state.db fallback pre-check failed: %s", e)

            # 调用原始方法（所有原始逻辑不变）
            return super().get_or_create_session(source, force_new=force_new)

        def _inject_from_db_if_needed(self, source):
            """如果 _entries 中没有此 session，尝试从 state.db 加载。"""
            from gateway.session import build_session_key

            session_key = build_session_key(
                source,
                group_sessions_per_user=getattr(
                    self.config, "group_sessions_per_user", True
                ),
                thread_sessions_per_user=getattr(
                    self.config, "thread_sessions_per_user", False
                ),
            )

            # 已在内存中，无需 fallback
            if session_key in self._entries:
                return

            # 查 state.db
            platform_value = source.platform.value
            user_id = source.user_id
            if not user_id:
                return

            db_session = self._db.get_active_session_by_source(
                platform_value, user_id
            )
            if db_session is None:
                return

            # 找到了！注入 _entries
            from gateway.session import SessionEntry, _now

            db_session_id = db_session["id"]
            db_started_at = db_session.get("started_at")
            now = _now()

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
                display_name=getattr(source, "chat_name", None),
                platform=source.platform,
                chat_type=source.chat_type,
            )

            # 加锁注入
            with self._lock:
                # 双重检查（另一个线程可能已经注入了）
                if session_key not in self._entries:
                    self._entries[session_key] = entry
                    self._save()
                    logger.info(
                        "[session_fallback] Injected session %s from state.db "
                        "for key=%s source=%s user_id=%s",
                        db_session_id, session_key, platform_value, user_id,
                    )

    FallbackSessionStore.__name__ = Base.__name__ + "WithFallback"
    FallbackSessionStore.__qualname__ = Base.__qualname__ + "WithFallback"
    return FallbackSessionStore


def install_fallback(session_store_class: Type) -> Type:
    """安装 state.db fallback，返回增强后的 SessionStore 类。

    用法：
        from gateway.extensions.session_fallback import install_fallback
        from gateway.session import SessionStore
        SessionStore = install_fallback(SessionStore)
        store = SessionStore(sessions_dir, config)

    返回的类是原始类的子类，所有原始行为不变，
    只在 get_or_create_session() 中增加了 state.db fallback。
    """
    return _make_fallback_mixin(session_store_class)
```

**设计要点**：
- **不修改原始方法**：通过子类 + `super()` 调用，原始 `get_or_create_session()` 逻辑完全不变
- **预注入策略**：在调用 `super()` 之前，先检查 state.db 并注入 `_entries`，让原始逻辑自然命中
- **线程安全**：注入时使用 `self._lock` + 双重检查
- **幂等**：已存在于 `_entries` 的 session 不会重复注入
- **优雅降级**：fallback 失败不影响原始流程

---

### 改动 3：run.py — 一行引入 fallback

**文件**: `~/.hermes/hermes-agent/gateway/run.py`
**改动类型**: 最小修改（2 行：1 行 import + 1 行替换）
**位置**: line 1942 附近

原始代码（line 1942）：
```python
        self.session_store = SessionStore(
            self.config.sessions_dir, self.config,
            has_active_processes_fn=lambda key: process_registry.has_active_for_session(key),
        )
```

修改为：
```python
        from gateway.extensions.session_fallback import install_fallback
        _SessionStore = install_fallback(SessionStore)
        self.session_store = _SessionStore(
            self.config.sessions_dir, self.config,
            has_active_processes_fn=lambda key: process_registry.has_active_for_session(key),
        )
```

**影响范围**：
- 只影响 Gateway 进程的 SessionStore 实例化
- 不影响 hermes-active 的 SessionStore 实例（它自己创建）
- 不影响任何其他代码路径

---

### 改动 4：新建 hermes-active fallback_session_service.py

**文件**: `~/.hermes/hermes-active/backend/services/fallback_session_service.py`
**改动类型**: 新建文件

```python
"""
Fallback Session 服务

直接查询 state.db 获取活跃 session，不依赖 Gateway 的 SessionStore。
解决了 hermes-active 自建 SessionStore 与 Gateway 内存不同步的问题。

用法：
    from services.fallback_session_service import FallbackSessionService
    session = FallbackSessionService.get_or_create_active_session("weixin", user_id)
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("hermes.session")


class FallbackSessionService:
    """直接操作 state.db 的 Session 服务，绕过 SessionStore 同步问题。"""

    @staticmethod
    def get_or_create_active_session(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取或创建活跃 session。

        策略：
        1. 先查 state.db 看是否有活跃 session（ended_at IS NULL）
        2. 如果有 → 直接返回（不创建新的）
        3. 如果没有 → 通过 Gateway API 创建（确保 Gateway 内存同步）

        不再自己创建 SessionStore 实例，彻底避免同步问题。
        """
        # Step 1: 查 state.db
        session = FallbackSessionService._find_active_session(platform, user_id)
        if session:
            logger.info(
                "Found active session in state.db: %s (source=%s, user_id=%s)",
                session["id"], platform, user_id,
            )
            return {
                "id": session["id"],
                "source": platform,
                "user_id": user_id,
                "created_at": None,
                "was_auto_reset": False,
                "auto_reset_reason": None,
            }

        # Step 2: state.db 没有，通过 Gateway API 创建
        # Gateway 的 SessionStore fallback 会自动从 state.db 加载
        logger.info(
            "No active session in state.db for source=%s user_id=%s, "
            "creating via Gateway API",
            platform, user_id,
        )
        return FallbackSessionService._create_via_gateway_api(platform, user_id)

    @staticmethod
    def _find_active_session(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """从 state.db 查找活跃 session。"""
        try:
            from models.database import state_engine
            from sqlalchemy import text

            with state_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT id, source, user_id, started_at, title "
                        "FROM sessions "
                        "WHERE source = :source AND user_id = :user_id "
                        "AND ended_at IS NULL "
                        "ORDER BY started_at DESC LIMIT 1"
                    ),
                    {"source": platform, "user_id": user_id},
                )
                row = result.first()
                if row:
                    return {
                        "id": row[0],
                        "source": row[1],
                        "user_id": row[2],
                        "started_at": row[3],
                        "title": row[4],
                    }
        except Exception as e:
            logger.warning("Failed to query state.db for active session: %s", e)
        return None

    @staticmethod
    def _create_via_gateway_api(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """通过 Gateway API 创建 session。

        Gateway 的 SessionStore (已安装 fallback) 会：
        1. 在 _entries 中查找 → 没有
        2. fallback 查 state.db → 没有
        3. 创建新 session → 写入 state.db + _entries + sessions.json
        """
        import os
        import json as _json
        import urllib.request
        import urllib.error

        gateway_url = os.getenv("GATEWAY_API_URL", "http://127.0.0.1:8642")
        api_key = os.getenv("API_SERVER_KEY", "")

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
            if e.code == 409:
                # Session 已存在 — 从 state.db 获取
                logger.info("Session already exists via API (409), querying state.db")
                return FallbackSessionService._find_active_session(platform, user_id)
            logger.error("Gateway session API error: %s", e)
            return None
        except Exception as e:
            logger.error("Gateway session API failed: %s", e)
            return None
```

**设计要点**：
- **先查 state.db**：大多数情况下 session 已存在，直接返回，无需网络调用
- **后调 Gateway API**：只在 session 不存在时创建，确保 Gateway 内存同步
- **409 处理**：session 已存在时回退到 state.db 查询
- **不依赖 SessionStore**：彻底避免 hermes-active 自建 SessionStore 的同步问题
- **签名兼容**：`get_or_create_active_session(platform, user_id)` 签名不变，调用方无需改动

---

### 改动 5：scheduler_service.py — 改用 FallbackSessionService

**文件**: `~/.hermes/hermes-active/backend/services/scheduler_service.py`
**改动类型**: 最小修改（1 行 import + 1 行调用）

原始代码（line 111）：
```python
            session = SessionService.get_or_create_active_session(
                platform=platform,
                user_id=user_id
            )
```

修改为：
```python
            from services.fallback_session_service import FallbackSessionService
            session = FallbackSessionService.get_or_create_active_session(
                platform=platform,
                user_id=user_id
            )
```

**注意**：import 放在函数内部，避免循环导入，也便于回滚。

---

### 改动 6：routers/sessions.py — 改用 FallbackSessionService

**文件**: `~/.hermes/hermes-active/backend/routers/sessions.py`
**改动类型**: 最小修改（import + 调用）

将 line 62 和 line 81 的：
```python
        session = SessionService.get_or_create_active_session(platform, user_id)
```

改为：
```python
        from services.fallback_session_service import FallbackSessionService
        session = FallbackSessionService.get_or_create_active_session(platform, user_id)
```

---

## 完整数据流（改动后）

### 场景 1：用户通过微信发消息（Gateway 原生流程）

```
用户发消息 → Gateway adapter 收到
  → session_store.get_or_create_session(source)
    → _entries 中查找 → 找到 → 直接返回 ✅
    → (fallback 不触发)
```

### 场景 2：hermes-active 定时任务需要 session

```
定时任务触发
  → FallbackSessionService.get_or_create_active_session("weixin", user_id)
    → _find_active_session() 查 state.db
      → 找到 → 返回 ✅ (不创建新 session)
      → 没找到 → _create_via_gateway_api()
        → POST /api/sessions → Gateway 创建 session
          → SessionStore.get_or_create_session()
            → _entries 没找到 → fallback 查 state.db → 没找到
            → 创建新 session → 写入 _entries + sessions.json + state.db
            → 返回 ✅
```

### 场景 3：API 创建的 session，用户随后发消息

```
hermes-active 通过 POST /api/sessions 创建 session → 写入 state.db

用户发消息 → Gateway session_store.get_or_create_session(source)
  → _entries 没找到
  → fallback: _inject_from_db_if_needed(source)
    → 查 state.db → 找到 → 注入 _entries
  → super().get_or_create_session()
    → _entries 命中 → 返回 ✅ (同一个 session!)
```

## 改动量统计

| 指标 | 数量 |
|------|------|
| 新建文件 | **2 个** |
| 新增方法 | **1 个** (hermes_state.py) |
| 修改现有方法 | **0 个** |
| 现有文件最小修改 | **3 处** (run.py 2行, scheduler_service.py 2行, sessions.py 2行) |
| 总新增代码行数 | ~200 行 |
| 总修改代码行数 | ~6 行 |

## 风险评估

### 改动 1：hermes_state.py 新增方法
- **风险**: 极低
- **影响范围**: 无（新增方法，不影响任何现有代码）
- **回滚**: 删除新方法即可

### 改动 2：session_fallback.py 新建文件
- **风险**: 低
- **影响范围**: 只在 `install_fallback()` 被调用时生效
- **回滚**: 删除文件，恢复 run.py 的 import

### 改动 3：run.py 一行替换
- **风险**: 低
- **影响范围**: Gateway 的 SessionStore 实例（所有平台共享）
- **回滚**: 恢复原始 `SessionStore(` 调用
- **注意**: 子类继承所有原始行为，fallback 只在 `_entries` 找不到时触发

### 改动 4：fallback_session_service.py 新建文件
- **风险**: 极低
- **影响范围**: 无（新文件，不影响任何现有代码）
- **回滚**: 删除文件即可

### 改动 5-6：scheduler_service.py / sessions.py 改调用
- **风险**: 低
- **影响范围**: 定时任务的 session 获取 + API 路由的 session 获取
- **回滚**: 恢复原始 `SessionService.get_or_create_active_session()` 调用
- **降级**: 如果 FallbackSessionService 失败，返回 None，定时任务跳过本次执行

## 回滚方案

### 快速回滚（1 分钟内）

```bash
# 1. 恢复 run.py
cd ~/.hermes/hermes-agent
git checkout gateway/run.py

# 2. 恢复 scheduler_service.py
cd ~/.hermes/hermes-active
git checkout backend/services/scheduler_service.py

# 3. 恢复 sessions.py
git checkout backend/routers/sessions.py

# 4. 重启服务
hermes restart
# 重启 hermes-active
```

### 完全回滚（删除所有新文件）

```bash
# 在快速回滚基础上，删除新文件
rm ~/.hermes/hermes-agent/gateway/extensions/session_fallback.py
rm ~/.hermes/hermes-active/backend/services/fallback_session_service.py

# 可选：删除 hermes_state.py 的新方法
# (手动编辑删除 get_active_session_by_source 方法)
```

### 回滚影响

- 回滚后恢复到原有行为：hermes-active 自建 SessionStore，可能产生 session 分裂
- 不会丢失任何数据（state.db 和 sessions.json 不受影响）

## 验证步骤

### 1. 代码检查

```bash
# 确认新文件存在
ls -la ~/.hermes/hermes-agent/gateway/extensions/session_fallback.py
ls -la ~/.hermes/hermes-active/backend/services/fallback_session_service.py

# 确认 hermes_state.py 有新方法
grep -n "get_active_session_by_source" ~/.hermes/hermes-agent/hermes_state.py

# 确认 run.py 使用了 install_fallback
grep -n "install_fallback" ~/.hermes/hermes-agent/gateway/run.py
```

### 2. 单元测试

```python
# 测试 hermes_state.py 新方法
from hermes_state import SessionDB
db = SessionDB()
result = db.get_active_session_by_source("weixin", "test_user_id")
print(f"Result: {result}")  # 应为 None 或 session dict

# 测试 FallbackSessionStore
from gateway.session import SessionStore, SessionSource
from gateway.config import GatewayConfig, Platform
from gateway.extensions.session_fallback import install_fallback
import yaml
from pathlib import Path

config = GatewayConfig.from_dict(yaml.safe_load(open(Path.home() / '.hermes/config.yaml')))
PatchedStore = install_fallback(SessionStore)
store = PatchedStore(Path.home() / '.hermes/sessions', config)
print(f"Store class: {store.__class__.__name__}")  # 应为 SessionStoreWithFallback
print(f"Has fallback: {hasattr(store, '_inject_from_db_if_needed')}")  # 应为 True
```

### 3. 集成测试

```bash
# Step 1: 确保 Gateway 运行中
hermes status

# Step 2: 通过 API 创建一个 session（模拟 hermes-active 行为）
curl -X POST http://127.0.0.1:8642/api/sessions \
  -H "Authorization: Bearer $API_SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"weixin","user_id":"test_fallback_user"}'

# Step 3: 检查 state.db 中是否有记录
sqlite3 ~/.hermes/state.db "SELECT id, source, user_id, ended_at FROM sessions WHERE user_id='test_fallback_user'"

# Step 4: 检查 Gateway 日志是否有 fallback 注入记录
# 发送一条消息触发 get_or_create_session，观察日志
hermes logs | grep "session_fallback"

# Step 5: 验证 session 一致
# 确认 API 创建的 session_id 和 Gateway 使用的 session_id 相同
```

### 4. 端到端测试

```bash
# 1. 重启 Gateway（确保 fallback 生效）
hermes restart

# 2. 重启 hermes-active
# (根据部署方式重启)

# 3. 触发 hermes-active 定时任务
# 等待定时任务执行，或手动触发

# 4. 用户通过微信发消息

# 5. 检查 session 是否一致
sqlite3 ~/.hermes/state.db "
  SELECT id, source, user_id, started_at
  FROM sessions
  WHERE source='weixin' AND ended_at IS NULL
  ORDER BY started_at DESC
"
# 应该只有一条记录

# 6. 检查 hermes-active 日志
# 应该看到 "Found active session in state.db" 而不是 "Creating via Gateway API"
```

## 附录：为什么选择子类而非猴子补丁

| 方案 | 优点 | 缺点 |
|------|------|------|
| **子类（本方案）** | 类型安全、可调试、继承所有原始行为 | 需要改 run.py 一行 |
| 猴子补丁 | 不改任何现有文件 | 脆弱、难调试、IDE 不识别 |
| 装饰器 | 不改现有文件 | 需要包装所有调用点 |
| 组合/委托 | 完全解耦 | 需要代理所有方法，代码量大 |

子类方案在"最小改动"和"代码质量"之间取得了最佳平衡。

## 附录：与之前方案的对比

| 维度 | v1 方案 (session-sync-fix-plan.md) | v2 方案 (本方案) |
|------|-------------------------------------|-------------------|
| 修改 `get_or_create_session()` | ✅ 直接修改方法体 | ❌ 不修改（子类 + super） |
| 修改现有文件数 | 3 个 | 3 个（但每处只改 1-2 行） |
| 新建文件数 | 0 个 | 2 个 |
| hermes-active 改动 | 重写整个方法 | 新建文件 + 改调用点 |
| 回滚难度 | 需要恢复 3 个文件的原始内容 | 删除 2 个新文件 + git checkout 3 个文件 |
| 可测试性 | 低（嵌入在原方法中） | 高（独立子类 + 独立服务） |
