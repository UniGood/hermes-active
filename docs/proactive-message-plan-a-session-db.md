# 方案 A：Cron Delivery 时写入 Session DB

## 目标

当 cron job 发送主动消息时，同时将消息写入目标 chat 的主会话 session DB，
使 agent 在用户回复时能自然看到自己之前发的主动消息。

## 技术可行性：✅ 完全可行

关键发现：
- Cron scheduler 在 gateway 进程内作为后台线程运行
- `_start_cron_ticker` 接收 `adapters` 和 `loop` 参数
- `_deliver_result` 可以访问 gateway 的 `session_store`
- `session_store.append_to_transcript()` 可以写入 session DB

## 架构设计

```
当前流程：
  cron job → run_job() → _deliver_result() → 平台发送
                                                  ↓
                                          不写入 session DB ❌

新流程：
  cron job → run_job() → _deliver_result() → 平台发送
                    ↓
              写入 session DB ✅
                    ↓
              用户回复 → load_transcript → 包含主动消息 → LLM 看到 ✅
```

## 实现方案

### 方案 A1：修改 cron/scheduler.py（最小改动）

在 `_deliver_result` 函数中，delivery 成功后写入 session DB。

**修改文件**: `cron/scheduler.py`

**修改位置**: `_deliver_result` 函数，delivery 成功后

```python
def _deliver_result(job, content, adapters=None, loop=None):
    # ... 现有 delivery 逻辑 ...
    
    for target in targets:
        # ... 现有发送逻辑 ...
        
        if delivery_success:
            # 新增：写入主会话 session DB
            _inject_to_session_db(
                platform=platform_name,
                chat_id=chat_id,
                content=content,
                job_name=job.get("name", job["id"]),
            )
```

**新增函数**: `_inject_to_session_db`

```python
def _inject_to_session_db(platform, chat_id, content, job_name):
    """
    将 cron delivery 的消息写入目标 chat 的主会话 session DB。
    
    这样当用户回复时，agent 能在会话历史中看到自己之前发的主动消息。
    """
    try:
        # 获取 gateway 的 session_store
        # 注意：cron scheduler 在 gateway 进程内运行，可以直接访问
        from gateway.run import _gateway_instance
        
        if not _gateway_instance:
            logger.debug("inject_to_session_db: no gateway instance")
            return
        
        session_store = getattr(_gateway_instance, 'session_store', None)
        if not session_store:
            logger.debug("inject_to_session_db: no session_store")
            return
        
        # 找到目标 chat 的活跃 session
        session_id = _find_active_session(session_store, platform, chat_id)
        if not session_id:
            logger.debug("inject_to_session_db: no active session for %s:%s", platform, chat_id)
            return
        
        # 写入 assistant 消息到 session DB
        message = {
            "role": "assistant",
            "content": f"[主动消息] {content}",
            "timestamp": time.time(),
            "source": f"cron:{job_name}",
        }
        session_store.append_to_transcript(session_id, message)
        logger.info("inject_to_session_db: wrote to session %s (%d chars)", session_id, len(content))
        
    except Exception as e:
        logger.debug("inject_to_session_db failed: %s", e)
```

### 方案 A2：通过 Plugin Hook 实现（不改核心代码）

创建一个 plugin，在 cron delivery 时通过 hook 写入 session DB。

**问题**：当前 plugin API 没有 "post_cron_delivery" hook。

**替代方案**：修改 cron prompt，让 cron job 的 agent 主动调用一个工具来写入 session DB。

```python
# 新增工具：inject_proactive_context
def inject_proactive_context(content, platform, chat_id):
    """将主动消息写入主会话 session DB"""
    # 写入逻辑同上
    ...
```

**问题**：cron job 运行在独立 session，无法直接访问 gateway 的 session_store。

### 方案 A3：文件队列 + Gateway Hook（中等改动）

1. Cron delivery 后写入一个标记文件
2. Gateway 的 pre_llm_call hook 读取标记文件
3. Hook 检查用户回复时间与标记文件时间
4. 如果时间接近，注入更强的上下文

**优点**：不改核心代码
**缺点**：仍然是 hook 注入，效果可能不够好

---

## 推荐方案：A1（修改 cron/scheduler.py）

### 为什么选 A1

| 维度 | A1（改 scheduler） | A2（plugin） | A3（文件队列） |
|------|-------------------|--------------|----------------|
| 效果 | ⭐⭐⭐⭐⭐ 最好 | ⭐⭐⭐ 需要新工具 | ⭐⭐⭐ 依赖 hook |
| 改动范围 | 小（一个函数） | 中（新工具） | 中（新 hook） |
| 可靠性 | 高（直接写 DB） | 中（依赖工具调用） | 中（依赖文件） |
| 维护成本 | 低 | 中 | 中 |

### 具体实现步骤

#### Step 1：找到 gateway 实例的引用

需要让 cron scheduler 能访问 gateway 的 session_store。

```python
# gateway/run.py 中添加全局引用
_gateway_instance = None

class GatewayRunner:
    def __init__(self):
        global _gateway_instance
        _gateway_instance = self
        ...
```

#### Step 2：找到目标 chat 的活跃 session

```python
def _find_active_session(session_store, platform, chat_id):
    """根据 platform + chat_id 找到活跃的 session_id"""
    for key, entry in session_store._entries.items():
        if (entry.platform and entry.platform.value == platform and 
            entry.origin and entry.origin.chat_id == chat_id):
            return entry.session_id
    return None
```

#### Step 3：写入 session DB

```python
def _inject_to_session_db(platform, chat_id, content, job_name):
    """delivery 成功后写入 session DB"""
    ...
```

#### Step 4：在 _deliver_result 中调用

```python
def _deliver_result(job, content, adapters=None, loop=None):
    # ... 现有逻辑 ...
    
    if should_deliver:
        delivery_error = _deliver_result_impl(job, deliver_content, ...)
        
        # 新增：写入 session DB
        if not delivery_error:
            for target in targets:
                _inject_to_session_db(
                    target["platform"],
                    target["chat_id"],
                    deliver_content,
                    job.get("name", job["id"]),
                )
```

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| session 被重置 | 写入失败 | 检查 session 是否存在 |
| 并发写入 | 数据竞争 | 使用 session_store 的锁 |
| 消息格式不对 | LLM 不理解 | 使用明确的 `[主动消息]` 标记 |
| token 消耗增加 | 成本上升 | 可选：限制写入长度 |

## 测试计划

1. **单元测试**：`_find_active_session` 函数
2. **集成测试**：cron delivery 后检查 session DB
3. **端到端测试**：
   - 创建 cron job
   - 等待 delivery
   - 检查 session DB 是否包含主动消息
   - 模拟用户回复
   - 检查 agent 是否能正确延续话题

## 回滚方案

如果出现问题：
1. 在 `_inject_to_session_db` 中添加开关配置
2. 默认关闭，测试通过后开启
3. 配置项：`cron.inject_to_session: true/false`

## 下一步

1. 确认方案 → 用户批准
2. 实现代码 → 修改 cron/scheduler.py
3. 测试验证 → 创建测试 cron job
4. 部署上线 → 重启 gateway
