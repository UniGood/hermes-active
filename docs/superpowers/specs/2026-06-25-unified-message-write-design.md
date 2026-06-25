# 统一消息写入设计规格

**日期**: 2026-06-25
**状态**: 待审批
**作者**: Kelly (AI Assistant)

---

## 背景

hermes-active 项目中存在两种写入 state.db messages 表的方式：

1. **`_write_to_state_db()`** - 自己写的简化版本，只写 6 个字段
2. **`SessionDB.append_message()`** - hermes 核心的公共方法，支持全部 16 个字段

这导致主动发送的消息在数据库中"残缺"——缺少 `reasoning_content`、`token_count` 等关键字段。

**问题**：
- 主动消息的 LLM 推理过程丢失
- 无法统计主动消息的 token 消耗
- 与 hermes 核心的写入方式不统一，维护困难

---

## 目标

1. **统一写入方式**：所有写入 state.db messages 表的地方都使用 `SessionDB.append_message()`
2. **保留完整字段**：主动消息的 `reasoning_content`、`token_count` 等字段都要写入
3. **复用 hermes 核心**：使用 `extract_content_or_reasoning()` 提取推理内容
4. **测试覆盖**：所有调用 send_message() 的地方都要传递缺失字段

---

## 现状分析

### 现有写入方式

| 方法 | 位置 | 字段完整度 | 用途 |
|------|------|-----------|------|
| `_write_to_state_db()` | message_service.py:119 | ❌ 只写 6 字段 | send_message() |
| `db.append_message()` | scripts/proactive_context_gen.py:166,176 | ✅ 全字段 | 独立脚本 |
| `db.append_message()` | scripts/test_send_message.py:50 | ✅ 全字段 | 测试脚本 |

### 调用链分析

```
ThoughtEngine._call_llm()
  → 返回 (raw, llm_details)  # raw 是 content，llm_details 只有 token 信息
    → generate_thought()
      → 返回 (thought, llm_details, want_to_contact)
        → 调用方只用 thought
          → send_message(session_id, thought)
            → _write_to_state_db(session_id, content)  # 只写 content，没有 reasoning
```

### 需要改动的文件

| 文件 | 改动点 |
|------|--------|
| `thought_engine.py` | `_call_llm()` 提取 reasoning_content |
| `active_consciousness_service.py` | 传递 reasoning_content 给 send_message() |
| `message_service.py` | 删除 `_write_to_state_db()`，改用 SessionDB |
| `scheduler_service.py` | 调用 send_message() 时传 reasoning_content |
| `routers/messages.py` | API 调用 send_message() 时传 reasoning_content |
| `routers/test.py` | 测试界面调用 send_message() 时传 reasoning_content |

---

## 设计方案

### 第1层：LLM 调用（thought_engine.py）

**改动**：`_call_llm()` 方法

```python
# 现状
response = await asyncio.to_thread(call_llm, **call_kwargs)
raw = response.choices[0].message.content.strip()
# ❌ 没取 reasoning_content

# 改后
from agent.auxiliary_client import extract_content_or_reasoning

response = await asyncio.to_thread(call_llm, **call_kwargs)
raw = extract_content_or_reasoning(response)  # 统一提取

# 提取 reasoning_content
msg = response.choices[0].message
reasoning_content = getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)
if not reasoning_content:
    # 尝试从 reasoning_details 提取
    details = getattr(msg, 'reasoning_details', None)
    if details and isinstance(details, list):
        reasoning_content = "\n\n".join(
            d.get("summary") or d.get("content") or d.get("text", "")
            for d in details
            if isinstance(d, dict)
        )

llm_details["reasoning_content"] = reasoning_content
return raw, llm_details
```

**自定义模式**（LLMService.generate_message）：

```python
# llm_service.py 改动
response = await client.chat.completions.create(...)
content = response.choices[0].message.content.strip()

# 提取 reasoning_content
msg = response.choices[0].message
reasoning_content = getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)

return {
    "success": True,
    "content": content,
    "reasoning_content": reasoning_content,  # 新增
    "model": model,
    "duration": duration
}
```

---

### 第2层：返回值透传（thought_engine.py）

**改动**：`generate_thought()` 返回值

```python
# 现状
return thought, llm_details, want_to_contact

# 改后（结构不变，llm_details 已包含 reasoning_content）
return thought, llm_details, want_to_contact
```

---

### 第3层：调用链传递（active_consciousness_service.py）

**改动**：所有调用 `send_message()` 的地方

```python
# 现状
result = await MessageService.send_message(
    session_id=session_id,
    message=thought,
)

# 改后
result = await MessageService.send_message(
    session_id=session_id,
    message=thought,
    reasoning_content=llm_details.get("reasoning_content"),  # 新增
)
```

**需要改的地方**：
- `active_consciousness_service.py:1250` - send_message 调用
- `active_consciousness_service.py:1469` - send_message_to_target 调用
- `scheduler_service.py:527` - 定时任务调用
- `routers/messages.py:254` - API 调用
- `routers/messages.py:280` - 主动消息 API 调用
- `routers/test.py:94` - 测试界面调用

---

### 第4层：写入 state.db（message_service.py）

**改动**：删除 `_write_to_state_db()`，`send_message()` 改用 SessionDB

```python
# 删除 _write_to_state_db() 函数

# send_message() 改动
from hermes_state import SessionDB

async def send_message(
    session_id: str,
    message: str,
    platform: str = "weixin",
    write_to_db: bool = True,
    with_mark: bool = False,
    mark_format: str = DEFAULT_MARK_FORMAT,
    send_mark: str = DEFAULT_SEND_MARK,
    time_format: str = DEFAULT_TIME_FORMAT,
    reasoning_content: str = None,  # 新增参数
    token_count: int = None,        # 新增参数
) -> Dict[str, Any]:
    # ... 现有逻辑 ...

    # 2. 只有发送成功才写入 state.db
    if write_to_db and sent_ok:
        if send_mark:
            # ... 标记逻辑 ...

        # 使用 SessionDB 写入
        db = SessionDB()
        db.append_message(
            session_id=session_id,
            role="assistant",
            content=db_content,
            reasoning_content=reasoning_content,  # 新增
            token_count=token_count,              # 新增
            finish_reason="stop",
        )
```

---

## 测试点

### 单元测试

1. **ThoughtEngine._call_llm()**
   - 验证 reasoning_content 被正确提取
   - 验证 llm_details 包含 reasoning_content

2. **MessageService.send_message()**
   - 验证 SessionDB.append_message() 被调用
   - 验证 reasoning_content、token_count 被传入

### 集成测试

1. **主动意识心跳流程**
   - 心跳触发 → 生成念头 → 发送消息 → 验证 state.db 中消息包含 reasoning_content

2. **定时任务流程**
   - cron 任务触发 → 发送消息 → 验证 state.db 中消息包含 reasoning_content

3. **API 调用流程**
   - POST /messages/send → 验证 state.db 中消息包含 reasoning_content

4. **测试界面流程**
   - 点击"测试发送" → 验证 state.db 中消息包含 reasoning_content

### 数据库验证

```sql
-- 验证主动消息包含 reasoning_content
SELECT id, session_id, role, 
       CASE WHEN reasoning_content IS NULL THEN 'NULL' 
            WHEN reasoning_content = '' THEN 'EMPTY'
            ELSE 'HAS_DATA' END as reasoning_status,
       token_count
FROM messages 
WHERE role='assistant' 
ORDER BY id DESC 
LIMIT 20;
```

---

## 风险评估

### SessionDB 初始化风险

**风险**：SessionDB 初始化时会调用 `_init_schema()` 检查表结构
**缓解**：这是幂等操作（CREATE IF NOT EXISTS、ADD COLUMN IF NOT EXISTS），不会破坏现有数据
**验证**：`scripts/test_send_message.py` 已经在用 SessionDB，证明可行

### 并发写入风险

**风险**：Gateway 和 hermes-active 同时写入 state.db
**缓解**：SessionDB 已经有 `_execute_write()` 重试机制（最多15次，随机抖动20-150ms）
**验证**：WAL 模式支持多进程并发读写

### 字段缺失风险

**风险**：某些调用方没有传 reasoning_content
**缓解**：所有调用 send_message() 的地方都要传入，作为测试点验证
**验证**：数据库查询验证

---

## 实施计划

### 阶段1：核心改动（thought_engine.py + message_service.py）

1. 修改 `thought_engine.py` 的 `_call_llm()` 方法
2. 修改 `llm_service.py` 的 `generate_message()` 方法
3. 删除 `message_service.py` 的 `_write_to_state_db()` 函数
4. 修改 `message_service.py` 的 `send_message()` 方法

### 阶段2：调用链传递（active_consciousness_service.py）

5. 修改 `active_consciousness_service.py` 的 send_message 调用

### 阶段3：其他调用方

6. 修改 `scheduler_service.py` 的 send_message 调用
7. 修改 `routers/messages.py` 的 API 调用
8. 修改 `routers/test.py` 的测试界面调用

### 阶段4：测试验证

9. 运行单元测试
10. 运行集成测试
11. 数据库验证

---

## 成功标准

1. **代码层面**：所有写入 state.db messages 表的地方都使用 `SessionDB.append_message()`
2. **数据层面**：主动消息的 `reasoning_content`、`token_count` 字段不为 NULL
3. **测试层面**：所有调用 send_message() 的地方都传递缺失字段
4. **功能层面**：主动意识、定时任务、API、测试界面都正常工作
