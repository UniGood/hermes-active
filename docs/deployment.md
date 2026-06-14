# hermes-active 部署文档

## Session 同步 Fallback 扩展（2026-06-14）

### 问题根因

Gateway 内部有两条独立的数据通道，互不相通：

```
通道 1: SessionStore（内存 + sessions.json）
  - gateway/session.py — `if self._loaded: return` 只加载一次
  - 用户消息路由用这个：session_store.get_or_create_session(source)

通道 2: API Server / SessionDB（直接读写 state.db）
  - POST /api/sessions → db.create_session() 只写 state.db
  - 完全不碰 SessionStore 的 _entries 和 sessions.json
```

当 hermes-active 通过 `POST /api/sessions` 创建 session：
- ✅ state.db 里有了记录
- ❌ sessions.json 没更新
- ❌ Gateway 的 `_entries` 内存里没有
- → 用户发消息时 Gateway 在 `_entries` 找不到 → 又创建新 session → **session 分裂**

### 解决方案：子类继承 + state.db 预注入

创建 `FallbackSessionStore` 子类，在调用原始 `get_or_create_session()` **之前**，先查 state.db 并预注入 `_entries`，让原始逻辑自然命中。

```
用户发消息 → FallbackSessionStore.get_or_create_session(source)
  → _inject_from_db_if_needed(source)
    → 查 state.db → 找到 → 注入 _entries
  → super().get_or_create_session()
    → _entries 命中 → 返回同一个 session ✅
```

**设计原则**：原始方法体不修改，通过子类 + `super()` 继承所有原始行为。

---

### 文件清单

#### hermes-agent（Gateway 侧）

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `hermes_state.py` | **新增方法** | `get_active_session_by_source(source, user_id)` — 按平台+用户查活跃 session |
| `gateway/extensions/__init__.py` | **新建文件** | Python 包标识（空文件） |
| `gateway/extensions/session_fallback.py` | **新建文件** | `FallbackSessionStore` 子类 + `install_fallback()` 工厂函数 |
| `gateway/run.py` | **改 2 行** | `SessionStore` → `install_fallback(SessionStore)` |

#### hermes-active 侧

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/services/fallback_session_service.py` | **新建文件** | 先查 state.db，没有再调 Gateway API |
| `backend/services/scheduler_service.py` | **改 2 行** | 改用 FallbackSessionService |
| `backend/routers/sessions.py` | **改 4 行** | 改用 FallbackSessionService（2 处） |
| `backend/routers/test.py` | **改 2 行** | 改用 FallbackSessionService |
| `backend/routers/cron.py` | **改 4 行** | 改用 FallbackSessionService（2 处） |

**统计**：
- 新建文件：3 个（hermes-agent 2 个 + hermes-active 1 个）
- 新增方法：1 个（hermes_state.py）
- 修改现有方法体：**0 个**
- 现有文件最小改动：6 处（每处 2 行 import + 调用）

---

### 工作原理

#### Gateway 侧：子类预注入

`session_fallback.py` 创建 `FallbackSessionStore` 子类：

```python
class FallbackSessionStore(Base):
    def get_or_create_session(self, source, force_new=False):
        if not force_new and self._db is not None:
            self._inject_from_db_if_needed(source)  # 查 state.db → 注入 _entries
        return super().get_or_create_session(source, force_new=force_new)  # 原始逻辑
```

`run.py` 用子类替换原类：

```python
from gateway.extensions.session_fallback import install_fallback
_SessionStore = install_fallback(SessionStore)
self.session_store = _SessionStore(...)
```

#### hermes-active 侧：直接查库 + API 兜底

`FallbackSessionService.get_or_create_active_session()` 策略：
1. **先查 state.db** → 有活跃 session 直接返回（不创建新的，不走网络）
2. **没有** → 调 Gateway API `POST /api/sessions` 创建（Gateway 内存同步）
3. **409 冲突** → session 已存在，回退到 state.db 查询

所有原调用点（scheduler_service、sessions router、test router、cron router）统一改为调用 `FallbackSessionService`。

---

### 验证方法

```bash
# 1. 检查新文件存在
ls -la ~/.hermes/hermes-agent/gateway/extensions/session_fallback.py
ls -la ~/.hermes/hermes-active/backend/services/fallback_session_service.py

# 2. 验证子类可导入
cd ~/.hermes/hermes-agent && python3 -c "
from gateway.extensions.session_fallback import install_fallback
from gateway.session import SessionStore
Store = install_fallback(SessionStore)
print('子类:', Store.__name__)
print('有 fallback:', hasattr(Store, '_inject_from_db_if_needed'))
"

# 3. 验证 hermes_state.py 新方法
cd ~/.hermes/hermes-agent && python3 -c "
from hermes_state import SessionDB
db = SessionDB()
result = db.get_active_session_by_source('weixin', 'test')
print('查询结果:', result)
"

# 4. 验证 run.py 使用了 install_fallback
grep -n 'install_fallback' ~/.hermes/hermes-agent/gateway/run.py

# 5. 验证 hermes-active 所有调用点已切换
grep -rn 'SessionService.get_or_create_active_session' ~/.hermes/hermes-active/backend/ \
  --include='*.py' | grep -v 'fallback' | grep -v '已废弃' | grep -v 'def get_or_create'
# 应该没有输出（除了原方法定义本身）

# 6. 重启 Gateway 后检查日志
hermes restart
hermes logs | grep 'session_fallback'
```

---

### 回滚方法

#### 快速回滚（1 分钟）

```bash
# 1. 恢复 hermes-agent
cd ~/.hermes/hermes-agent
git checkout gateway/run.py
git checkout hermes_state.py

# 2. 恢复 hermes-active
cd ~/.hermes/hermes-active
git checkout backend/services/scheduler_service.py
git checkout backend/routers/sessions.py
git checkout backend/routers/test.py
git checkout backend/routers/cron.py

# 3. 重启 Gateway
hermes restart
```

#### 完全回滚（删除所有新文件）

```bash
# 在快速回滚基础上
rm ~/.hermes/hermes-agent/gateway/extensions/session_fallback.py
rm ~/.hermes/hermes-agent/gateway/extensions/__init__.py
rm ~/.hermes/hermes-active/backend/services/fallback_session_service.py
```

---

### 注意事项

1. **hermes-agent 是 editable 安装**（`pip install -e .`），源码修改立即生效，不需要重新安装
2. **需要重启 Gateway** 才能加载新代码（Python 模块在进程启动时加载）
3. **向后兼容**：fallback 只在 `_entries` 找不到时触发，正常流程不受影响
4. **线程安全**：注入时使用 `self._lock` + 双重检查
5. **优雅降级**：fallback 失败不影响原始流程（try/except 包裹）
