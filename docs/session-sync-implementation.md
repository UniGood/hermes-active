# Session 同步问题修复方案

## 问题根因

hermes-active 和 Gateway 各自维护独立的 SessionStore 实例，导致 session 不同步。

```
当前架构（有问题）：
┌─────────────────┐     ┌─────────────────┐
│  hermes-active  │     │    Gateway      │
│  SessionStore A │     │  SessionStore B │
│  (每次新建)      │     │  (长期运行)      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    sessions.json           sessions.json
    (A 写入)                 (B 读取旧缓存)
         │                       │
         ▼                       ▼
    state.db                state.db
    session_060000          session_091252
    (主动消息)              (用户消息)
```

## 方案对比

### 方案 A：hermes-active 调用 Gateway API（推荐）

**原理**：hermes-active 不再自己创建 SessionStore，改为调用 Gateway 的 HTTP API。

```
修复后架构：
┌─────────────────┐     ┌─────────────────┐
│  hermes-active  │     │    Gateway      │
│                 │────▶│  SessionStore   │
│  HTTP 调用      │     │  (唯一权威)      │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                           sessions.json
                           state.db
                           (统一数据源)
```

**优点**：
- Gateway 是唯一权威来源，数据一致性有保障
- 不需要修改 Gateway 代码（已有 API）
- hermes-active 代码改动小

**缺点**：
- 依赖 Gateway 运行状态
- 需要网络调用（本地 localhost，延迟可忽略）

### 方案 B：共享文件锁 + 轮询 reload

**原理**：两个进程通过文件锁同步 SessionStore。

**优点**：不依赖网络
**缺点**：实现复杂，容易死锁，性能差

### 方案 C：Gateway 插件注入

**原理**：通过 Hermes 插件机制，在 Gateway 的 session 创建时通知 hermes-active。

**优点**：实时性好
**缺点**：需要修改 Gateway 代码，耦合度高

---

## 推荐方案：方案 A

### 实施步骤

#### Step 1：Gateway 端 — 确认 API 可用

Gateway 已有 `api_server` 平台，提供 HTTP 接口。需要确认：
- `/api/sessions` 接口是否可用
- 是否支持创建新 session

#### Step 2：hermes-active 端 — 修改 SessionService

**文件**: `backend/services/session_service.py`

**修改内容**：
1. 删除 `get_or_create_active_session()` 中的 SessionStore 创建逻辑
2. 改为调用 Gateway 的 HTTP API

**新方法**：
```python
@staticmethod
async def get_or_create_session_via_gateway(platform: str, user_id: str) -> dict:
    """通过 Gateway API 获取/创建 session"""
    # 1. 调用 Gateway 的 /api/sessions/latest/{platform} 获取最新 session
    # 2. 如果 session 过期或不存在，调用 /api/sessions/create 创建新 session
    # 3. 返回 session 信息
```

#### Step 3：修改调用方

**文件**: `backend/services/scheduler_service.py`, `backend/routers/cron.py`

将所有调用 `get_or_create_active_session()` 的地方改为调用新方法。

#### Step 4：删除旧代码

删除 `session_service.py` 中不再使用的 SessionStore 相关代码。

---

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Gateway 未运行 | 低 | 高 | 检查 Gateway 状态，失败时降级 |
| API 调用超时 | 低 | 中 | 设置超时，重试机制 |
| 数据库并发 | 低 | 低 | Gateway 单线程处理 session |

## 回滚方案

如果新方案有问题，可以快速回滚：
1. 恢复 `session_service.py` 的旧代码
2. 重启 hermes-active

## 测试计划

1. **单元测试**：验证 Gateway API 调用
2. **集成测试**：验证 session 创建和消息写入
3. **端到端测试**：
   - 发送主动消息 → 验证写入正确 session
   - 用户发消息 → 验证使用同一 session
   - 检查 session 不会重复创建

## 已验证信息

### Gateway API 端点
- 地址: `http://localhost:8642`
- 认证: 需要 API Key（Bearer Token）
- 已知端点:
  - `GET /health` → 200（无需认证）
  - `GET /api/sessions` → 401（需要认证）

### 配置文件位置
- 主配置: `~/.hermes/config.yaml`
- 环境变量: `~/.hermes/.env`
- Sessions: `~/.hermes/sessions/sessions.json`
- 状态数据库: `~/.hermes/state.db`

### 当前问题
1. Gateway API 需要认证，但 hermes-active 没有配置 API Key
2. 需要在 `.env` 中添加 `HERMES_API_KEY` 配置
3. 或者在 `config.yaml` 中配置 api_server 的 API Key

### 下一步
1. 确定 Gateway API 的认证方式（API Key 来源）
2. 在 hermes-active 中配置 API Key
3. 实现通过 Gateway API 获取/创建 session 的逻辑
4. 测试验证 session 同步是否正常

## 验证结果

### Gateway API 已验证
- **地址**: `http://localhost:8642`
- **认证**: Bearer Token `7b905f959ad54cdc4a0f26216919f1ea4b00c2afae7dcbcd159b38ef5e161871`
- **环境变量**: `API_SERVER_KEY` in `~/.hermes/.env`

### 已验证端点
```bash
# 获取 session 列表（支持 source 和 chat_id 过滤）
GET /api/sessions?source=weixin&chat_id=xxx
Authorization: Bearer $API_KEY

# 创建新 session
POST /api/sessions
Authorization: Bearer $API_KEY
Content-Type: application/json
{"source":"weixin","chat_id":"xxx","user_id":"xxx"}
```

### 验证结论
1. `GET /api/sessions` 返回的数据与 sessions.json 一致
2. Gateway API 是 SessionStore 的真实数据源
3. 可以通过 `source` + `chat_id` 参数获取特定用户的 session
4. `POST /api/sessions` 可以创建新 session

### 实现方案

hermes-active 的 `SessionService` 改为：
1. 先调用 `GET /api/sessions?source=weixin&chat_id=xxx` 获取现有 session
2. 如果找到活跃 session，直接使用
3. 如果没找到，调用 `POST /api/sessions` 创建新 session
4. 不再自己创建 SessionStore 实例

## 关键发现（2026-06-14 验证）

### 架构分析

Gateway 内部有两个独立的数据源：

```
┌─────────────────────────────────────────────────────────────┐
│                     Gateway 进程                            │
│                                                             │
│  ┌─────────────────┐        ┌─────────────────┐           │
│  │  SessionStore   │        │   SessionDB     │           │
│  │  (内存对象)      │        │  (SQLite)       │           │
│  │                 │        │                 │           │
│  │  - 加载         │        │  - 直接读写      │           │
│  │    sessions.json│        │    state.db     │           │
│  │  - 只加载一次    │        │  - 实时查询      │           │
│  │  - 无 reload    │        │                 │           │
│  └────────┬────────┘        └────────┬────────┘           │
│           │                          │                     │
│           ▼                          ▼                     │
│     sessions.json              state.db                    │
│     (session 映射)            (session 元数据)              │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │    API Server         │
        │    (端口 8642)         │
        │                       │
        │  GET /api/sessions    │──▶ 读 state.db（实时）
        │  POST /api/sessions   │──▶ 写 state.db（实时）
        └───────────────────────┘
```

### 数据流对比

| 操作 | SessionStore（内存） | SessionDB（SQLite） | API Server |
|------|---------------------|---------------------|------------|
| 读取 | 从 sessions.json 加载（一次） | 直接查 state.db | 调用 SessionDB |
| 写入 | 更新内存 + sessions.json | 直接写 state.db | 调用 SessionDB |
| 同步 | 启动时加载一次，之后独立 | 实时读写 | 实时读写 |

### 验证结论

**用户假设验证：**
> "Gateway 的 SessionStore 是进程内的内存对象，只在启动时加载一次 sessions.json"

**✅ 正确** — `_ensure_loaded_locked()` 方法有 `if self._loaded: return` 检查，只加载一次。

> "hermes-active 是另一个进程，任何对 session 的操作都无法同步到 Gateway 的内存里"

**✅ 部分正确**：
- hermes-active 通过 API 创建的 session 会写入 state.db
- Gateway 的 SessionStore 不会自动 reload sessions.json
- 但 Gateway 在某些操作时会重新读取 state.db

### 关键问题

`GET /api/sessions` 返回的是 state.db 的数据，不是 Gateway SessionStore 的内存数据。这意味着：

1. ✅ hermes-active 可以通过 API 读取到最新 session
2. ❌ hermes-active 通过 API 创建的 session 不会同步到 Gateway 的 SessionStore
3. ❌ Gateway 使用 SessionStore 判断 session 过期，不是 state.db

### 修正后的方案

**核心原则：** hermes-active 不创建 session，只读取现有 session。

```
hermes-active 需要 session 时：
1. GET /api/sessions?source=weixin&chat_id=xxx
2. 找到活跃 session → 直接使用
3. 没找到 → 不创建，跳过本次操作
4. 用户发消息时，Gateway 自然创建 session
5. 下次 hermes-active 检查时，就能找到新 session
```

**对于主动消息的影响：**
- 如果用户今天还没发过消息，主动消息会跳过
- 用户发第一条消息后，Gateway 创建 session
- 后续的主动消息就能正常写入

这比原来的问题（主动消息写入旧 session）要好得多。
