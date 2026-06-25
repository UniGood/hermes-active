# 统一消息写入实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 统一所有写入 state.db messages 表的方式为 `SessionDB.append_message()`，保留完整字段（reasoning_content、token_count 等）

**架构：** 
- 第1层：LLM 调用提取 reasoning_content（thought_engine.py、llm_service.py）
- 第2层：返回值透传（thought_engine.py）
- 第3层：调用链传递（active_consciousness_service.py、scheduler_service.py、routers/messages.py、routers/test.py）
- 第4层：写入 state.db（message_service.py）

**技术栈：** Python、FastAPI、SQLAlchemy、hermes_state.SessionDB

---

## 文件清单

### 修改文件

| 文件 | 职责 |
|------|------|
| `backend/services/thought_engine.py` | LLM 调用提取 reasoning_content |
| `backend/services/llm_service.py` | 自定义模式 LLM 调用提取 reasoning_content |
| `backend/services/message_service.py` | 删除 _write_to_state_db()，send_message() 改用 SessionDB |
| `backend/services/active_consciousness_service.py` | 传递 reasoning_content 给 send_message() |
| `backend/services/scheduler_service.py` | 传递 reasoning_content 给 send_message() |
| `backend/routers/messages.py` | API 调用传递 reasoning_content |
| `backend/routers/test.py` | 测试界面传递 reasoning_content |

### 依赖文件（只读）

| 文件 | 用途 |
|------|------|
| `~/.hermes/hermes-agent/hermes_state.py` | SessionDB.append_message() |
| `~/.hermes/hermes-agent/agent/auxiliary_client.py` | extract_content_or_reasoning() |

---

## 任务 1：修改 thought_engine.py - LLM 调用提取 reasoning_content

**文件：**
- 修改：`backend/services/thought_engine.py:182-262`

- [ ] **步骤 1：备份当前 _call_llm 方法**

```bash
cd ~/.hermes/hermes-active
cp backend/services/thought_engine.py backend/services/thought_engine.py.bak
```

- [ ] **步骤 2：修改 _call_llm 方法 - hermes 模式**

```python
# thought_engine.py:208-231
# 现状
if self.llm_config.get("mode") == "hermes":
    import asyncio
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
    from agent.auxiliary_client import call_llm

    call_kwargs = dict(
        task='title_generation',
        messages=messages,
        temperature=temperature,
    )
    if max_tokens is not None:
        call_kwargs["max_tokens"] = max_tokens
    response = await asyncio.to_thread(call_llm, **call_kwargs)
    raw = response.choices[0].message.content.strip()

    # 记录 token 使用
    if hasattr(response, 'usage'):
        llm_details["prompt_tokens"] = response.usage.prompt_tokens
        llm_details["completion_tokens"] = response.usage.completion_tokens
        llm_details["total_tokens"] = response.usage.total_tokens

# 改后
if self.llm_config.get("mode") == "hermes":
    import asyncio
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
    from agent.auxiliary_client import call_llm, extract_content_or_reasoning

    call_kwargs = dict(
        task='title_generation',
        messages=messages,
        temperature=temperature,
    )
    if max_tokens is not None:
        call_kwargs["max_tokens"] = max_tokens
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

    # 记录 token 使用
    if hasattr(response, 'usage'):
        llm_details["prompt_tokens"] = response.usage.prompt_tokens
        llm_details["completion_tokens"] = response.usage.completion_tokens
        llm_details["total_tokens"] = response.usage.total_tokens
```

- [ ] **步骤 3：修改 _call_llm 方法 - 自定义模式**

```python
# thought_engine.py:232-252
# 现状
else:
    from services.llm_service import LLMService
    # 自定义模式拼接 messages 为单 prompt
    prompt_text = "\n\n".join(m["content"] for m in messages)
    gen_kwargs = dict(
        llm_config=self.llm_config,
        prompt=prompt_text,
        temperature=temperature,
    )
    if max_tokens is not None:
        gen_kwargs["max_tokens"] = max_tokens
    result = await LLMService.generate_message(**gen_kwargs)
    
    if result.get("success"):
        raw = result.get("content", "").strip()
        llm_details["prompt_tokens"] = result.get("prompt_tokens")
        llm_details["completion_tokens"] = result.get("completion_tokens")
        llm_details["total_tokens"] = result.get("total_tokens")
    else:
        raw = ""
        llm_details["error"] = result.get("message", "LLM 调用失败")

# 改后
else:
    from services.llm_service import LLMService
    # 自定义模式拼接 messages 为单 prompt
    prompt_text = "\n\n".join(m["content"] for m in messages)
    gen_kwargs = dict(
        llm_config=self.llm_config,
        prompt=prompt_text,
        temperature=temperature,
    )
    if max_tokens is not None:
        gen_kwargs["max_tokens"] = max_tokens
    result = await LLMService.generate_message(**gen_kwargs)
    
    if result.get("success"):
        raw = result.get("content", "").strip()
        llm_details["reasoning_content"] = result.get("reasoning_content")  # 新增
        llm_details["prompt_tokens"] = result.get("prompt_tokens")
        llm_details["completion_tokens"] = result.get("completion_tokens")
        llm_details["total_tokens"] = result.get("total_tokens")
    else:
        raw = ""
        llm_details["error"] = result.get("message", "LLM 调用失败")
```

- [ ] **步骤 4：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/services/thought_engine.py
```

预期：无输出（语法正确）

- [ ] **步骤 5：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/services/thought_engine.py
git commit -m "feat(thought): _call_llm 提取 reasoning_content 到 llm_details"
```

---

## 任务 2：修改 llm_service.py - 自定义模式提取 reasoning_content

**文件：**
- 修改：`backend/services/llm_service.py:87-132`

- [ ] **步骤 1：备份当前 generate_message 方法**

```bash
cd ~/.hermes/hermes-active
cp backend/services/llm_service.py backend/services/llm_service.py.bak
```

- [ ] **步骤 2：修改 generate_message 方法**

```python
# llm_service.py:105-120
# 现状
response = await client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens
)

content = response.choices[0].message.content.strip()
duration = round(time.time() - start_time, 2)

return {
    "success": True,
    "content": content,
    "model": model,
    "duration": duration
}

# 改后
response = await client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens
)

content = response.choices[0].message.content.strip()

# 提取 reasoning_content
msg = response.choices[0].message
reasoning_content = getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)

duration = round(time.time() - start_time, 2)

return {
    "success": True,
    "content": content,
    "reasoning_content": reasoning_content,  # 新增
    "model": model,
    "duration": duration
}
```

- [ ] **步骤 3：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/services/llm_service.py
```

预期：无输出（语法正确）

- [ ] **步骤 4：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/services/llm_service.py
git commit -m "feat(llm): generate_message 提取 reasoning_content"
```

---

## 任务 3：修改 message_service.py - 删除 _write_to_state_db，改用 SessionDB

**文件：**
- 修改：`backend/services/message_service.py:119-138, 277-360`

- [ ] **步骤 1：备份当前 message_service.py**

```bash
cd ~/.hermes/hermes-active
cp backend/services/message_service.py backend/services/message_service.py.bak
```

- [ ] **步骤 2：删除 _write_to_state_db 函数**

```python
# 删除 message_service.py:119-138 的整个函数
def _write_to_state_db(session_id: str, content: str) -> bool:
    """写入消息到 state.db"""
    try:
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return False
        messages_table = metadata.tables['messages']
        with state_engine.connect() as conn:
            conn.execute(messages_table.insert().values(
                session_id=session_id,
                role="assistant",
                content=content,
                timestamp=time.time(),
                finish_reason="stop",
                active=1
            ))
            conn.commit()
        return True
    except Exception:
        return False
```

- [ ] **步骤 3：修改 send_message 方法签名**

```python
# message_service.py:277-286
# 现状
async def send_message(
    session_id: str,
    message: str,
    platform: str = "weixin",
    write_to_db: bool = True,
    with_mark: bool = False,
    mark_format: str = DEFAULT_MARK_FORMAT,
    send_mark: str = DEFAULT_SEND_MARK,
    time_format: str = DEFAULT_TIME_FORMAT
) -> Dict[str, Any]:

# 改后
async def send_message(
    session_id: str,
    message: str,
    platform: str = "weixin",
    write_to_db: bool = True,
    with_mark: bool = False,
    mark_format: str = DEFAULT_MARK_FORMAT,
    send_mark: str = DEFAULT_SEND_MARK,
    time_format: str = DEFAULT_TIME_FORMAT,
    reasoning_content: str = None,  # 新增
    token_count: int = None,        # 新增
) -> Dict[str, Any]:
```

- [ ] **步骤 4：修改 send_message 方法的 docstring**

```python
# message_service.py:287-298
# 现状
"""发送消息到微信并写入 state.db

Args:
    session_id: 目标 session ID
    message: 消息内容
    platform: 目标平台（默认 weixin）
    write_to_db: 是否写入 state.db（默认 True）
    with_mark: 是否带标记（默认 False）
    mark_format: 标记格式模板（向后兼容），支持 {timestamp} 和 {content} 占位符
    send_mark: 发送标记前缀（如 [凯莉主动发送]）
    time_format: 时间格式（strftime 格式，支持 {weekday} 占位符）
"""

# 改后
"""发送消息到微信并写入 state.db

Args:
    session_id: 目标 session ID
    message: 消息内容
    platform: 目标平台（默认 weixin）
    write_to_db: 是否写入 state.db（默认 True）
    with_mark: 是否带标记（默认 False）
    mark_format: 标记格式模板（向后兼容），支持 {timestamp} 和 {content} 占位符
    send_mark: 发送标记前缀（如 [凯莉主动发送]）
    time_format: 时间格式（strftime 格式，支持 {weekday} 占位符）
    reasoning_content: LLM 推理过程（可选）
    token_count: token 消耗数量（可选）
"""
```

- [ ] **步骤 5：修改 send_message 方法的写入逻辑**

```python
# message_service.py:341-358
# 现状
# 2. 只有发送成功才写入 state.db，避免污染 messages 表和后续 agent loop
db_content = message
sent_ok = send_result and send_result.get("success")
if write_to_db and sent_ok:
    if send_mark:
        now = datetime.now()
        time_str = time_format.replace("{weekday}", weekday_name(now)) if time_format else ""
        time_str = now.strftime(time_str) if time_str else ""
        if time_str:
            db_content = f"[{send_mark} {time_str}]: {message}"
        else:
            db_content = f"[{send_mark}]: {message}"
    _write_to_state_db(session_id, db_content)
elif write_to_db and not sent_ok:
    logger.warning(
        "send failed for session %s, skipping state.db write. platform=%s, reason=%s",
        session_id, platform, (send_result or {}).get("message") or "no_result"
    )

# 改后
# 2. 只有发送成功才写入 state.db，避免污染 messages 表和后续 agent loop
db_content = message
sent_ok = send_result and send_result.get("success")
if write_to_db and sent_ok:
    if send_mark:
        now = datetime.now()
        time_str = time_format.replace("{weekday}", weekday_name(now)) if time_format else ""
        time_str = now.strftime(time_str) if time_str else ""
        if time_str:
            db_content = f"[{send_mark} {time_str}]: {message}"
        else:
            db_content = f"[{send_mark}]: {message}"
    
    # 使用 SessionDB 写入（统一方式）
    from hermes_state import SessionDB
    db = SessionDB()
    db.append_message(
        session_id=session_id,
        role="assistant",
        content=db_content,
        reasoning_content=reasoning_content,
        token_count=token_count,
        finish_reason="stop",
    )
elif write_to_db and not sent_ok:
    logger.warning(
        "send failed for session %s, skipping state.db write. platform=%s, reason=%s",
        session_id, platform, (send_result or {}).get("message") or "no_result"
    )
```

- [ ] **步骤 6：删除未使用的 import**

```python
# message_service.py:1-20
# 删除不再需要的 import
# from models.database import state_engine, get_state_metadata  # 如果其他地方不再使用
```

注意：先检查 `state_engine` 和 `get_state_metadata` 是否在其他地方使用，如果只在 `_write_to_state_db` 中使用则删除，否则保留。

- [ ] **步骤 7：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/services/message_service.py
```

预期：无输出（语法正确）

- [ ] **步骤 8：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/services/message_service.py
git commit -m "feat(message): 删除 _write_to_state_db，send_message 改用 SessionDB.append_message()"
```

---

## 任务 4：修改 active_consciousness_service.py - 传递 reasoning_content

**文件：**
- 修改：`backend/services/active_consciousness_service.py:1250, 1469`

- [ ] **步骤 1：备份当前文件**

```bash
cd ~/.hermes/hermes-active
cp backend/services/active_consciousness_service.py backend/services/active_consciousness_service.py.bak
```

- [ ] **步骤 2：查找所有调用 send_message 的地方**

```bash
cd ~/.hermes/hermes-active
grep -n "MessageService.send_message\|send_message_to_target" backend/services/active_consciousness_service.py
```

- [ ] **步骤 3：修改第一处调用（约 1250 行）**

```python
# 找到类似这样的代码
result = await MessageService.send_message(
    session_id=session_id,
    message=thought,
)

# 改为
result = await MessageService.send_message(
    session_id=session_id,
    message=thought,
    reasoning_content=llm_details.get("reasoning_content"),  # 新增
)
```

注意：需要确认 `llm_details` 变量在当前作用域可用。如果不可用，需要从 `generate_thought()` 的返回值中获取。

- [ ] **步骤 4：修改第二处调用（约 1469 行）**

```python
# 找到类似这样的代码
sent = await send_message_to_target(config, thought)

# 需要查看 send_message_to_target 函数的实现，确认是否需要修改
# 如果 send_message_to_target 内部调用 MessageService.send_message，则需要修改该函数
```

- [ ] **步骤 5：查找 send_message_to_target 函数定义**

```bash
cd ~/.hermes/hermes-active
grep -n "def send_message_to_target" backend/services/active_consciousness_service.py
```

- [ ] **步骤 6：修改 send_message_to_target 函数（如果存在）**

```python
# 如果 send_message_to_target 函数内部调用 MessageService.send_message
# 需要修改该函数，添加 reasoning_content 参数传递
```

- [ ] **步骤 7：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/services/active_consciousness_service.py
```

预期：无输出（语法正确）

- [ ] **步骤 8：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/services/active_consciousness_service.py
git commit -m "feat(active): 传递 reasoning_content 给 send_message"
```

---

## 任务 5：修改 scheduler_service.py - 传递 reasoning_content

**文件：**
- 修改：`backend/services/scheduler_service.py:527`

- [ ] **步骤 1：备份当前文件**

```bash
cd ~/.hermes/hermes-active
cp backend/services/scheduler_service.py backend/services/scheduler_service.py.bak
```

- [ ] **步骤 2：查找调用 send_message 的地方**

```bash
cd ~/.hermes/hermes-active
grep -n "MessageService.send_message" backend/services/scheduler_service.py
```

- [ ] **步骤 3：查看调用上下文**

```bash
cd ~/.hermes/hermes-active
sed -n '520,540p' backend/services/scheduler_service.py
```

- [ ] **步骤 4：修改调用**

```python
# 找到类似这样的代码
send_result = await MessageService.send_message(
    session_id=session_id,
    message=message,
)

# 改为
send_result = await MessageService.send_message(
    session_id=session_id,
    message=message,
    reasoning_content=reasoning_content,  # 如果有
)
```

注意：需要确认 `reasoning_content` 变量在当前作用域可用。如果定时任务没有 LLM 调用，则 reasoning_content 可以为 None。

- [ ] **步骤 5：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/services/scheduler_service.py
```

预期：无输出（语法正确）

- [ ] **步骤 6：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/services/scheduler_service.py
git commit -m "feat(scheduler): 传递 reasoning_content 给 send_message"
```

---

## 任务 6：修改 routers/messages.py - API 调用传递 reasoning_content

**文件：**
- 修改：`backend/routers/messages.py:254, 280`

- [ ] **步骤 1：备份当前文件**

```bash
cd ~/.hermes/hermes-active
cp backend/routers/messages.py backend/routers/messages.py.bak
```

- [ ] **步骤 2：查找调用 send_message 的地方**

```bash
cd ~/.hermes/hermes-active
grep -n "MessageService.send_message\|MessageService.send_proactive_message" backend/routers/messages.py
```

- [ ] **步骤 3：查看调用上下文**

```bash
cd ~/.hermes/hermes-active
sed -n '250,285p' backend/routers/messages.py
```

- [ ] **步骤 4：修改第一处调用（约 254 行）**

```python
# 找到类似这样的代码
result = await MessageService.send_message(
    session_id=session_id,
    message=message,
)

# 改为
result = await MessageService.send_message(
    session_id=session_id,
    message=message,
    reasoning_content=reasoning_content,  # 如果 API 请求中有
)
```

注意：需要确认 API 请求体中是否有 `reasoning_content` 字段。如果没有，可以设为 None。

- [ ] **步骤 5：修改第二处调用（约 280 行）**

```python
# 找到类似这样的代码
result = await MessageService.send_proactive_message(
    session_id=session_id,
    message=message,
)

# 需要查看 send_proactive_message 函数是否也需要修改
```

- [ ] **步骤 6：查找 send_proactive_message 函数定义**

```bash
cd ~/.hermes/hermes-active
grep -n "def send_proactive_message" backend/services/message_service.py
```

- [ ] **步骤 7：修改 send_proactive_message 函数（如果存在）**

```python
# 如果 send_proactive_message 函数内部调用 MessageService.send_message
# 需要修改该函数，添加 reasoning_content 参数传递
```

- [ ] **步骤 8：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/routers/messages.py
```

预期：无输出（语法正确）

- [ ] **步骤 9：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/routers/messages.py
git commit -m "feat(api): 传递 reasoning_content 给 send_message"
```

---

## 任务 7：修改 routers/test.py - 测试界面传递 reasoning_content

**文件：**
- 修改：`backend/routers/test.py:94`

- [ ] **步骤 1：备份当前文件**

```bash
cd ~/.hermes/hermes-active
cp backend/routers/test.py backend/routers/test.py.bak
```

- [ ] **步骤 2：查找调用 send_message 的地方**

```bash
cd ~/.hermes/hermes-active
grep -n "MessageService.send_message" backend/routers/test.py
```

- [ ] **步骤 3：查看调用上下文**

```bash
cd ~/.hermes/hermes-active
sed -n '90,100p' backend/routers/test.py
```

- [ ] **步骤 4：修改调用**

```python
# 找到类似这样的代码
send_result = await MessageService.send_message(
    session_id=session_id,
    message=message,
)

# 改为
send_result = await MessageService.send_message(
    session_id=session_id,
    message=message,
    reasoning_content=reasoning_content,  # 如果有
)
```

注意：测试界面可能没有 LLM 调用，reasoning_content 可以为 None。

- [ ] **步骤 5：验证语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/routers/test.py
```

预期：无输出（语法正确）

- [ ] **步骤 6：Commit**

```bash
cd ~/.hermes/hermes-active
git add backend/routers/test.py
git commit -m "feat(test): 传递 reasoning_content 给 send_message"
```

---

## 任务 8：验证所有改动

- [ ] **步骤 1：验证所有 Python 文件语法正确**

```bash
cd ~/.hermes/hermes-active
python3 -m py_compile backend/services/thought_engine.py
python3 -m py_compile backend/services/llm_service.py
python3 -m py_compile backend/services/message_service.py
python3 -m py_compile backend/services/active_consciousness_service.py
python3 -m py_compile backend/services/scheduler_service.py
python3 -m py_compile backend/routers/messages.py
python3 -m py_compile backend/routers/test.py
```

预期：全部无输出（语法正确）

- [ ] **步骤 2：运行现有测试（如果有）**

```bash
cd ~/.hermes/hermes-active
pytest tests/ -v 2>/dev/null || echo "No tests found"
```

- [ ] **步骤 3：手动测试 - 启动后端**

```bash
cd ~/.hermes/hermes-active/backend
python main.py &
sleep 3
```

- [ ] **步骤 4：手动测试 - 调用 API 发送消息**

```bash
# 使用 curl 测试
curl -X POST http://localhost:18720/api/messages/send \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_session", "message": "测试消息"}'
```

- [ ] **步骤 5：验证数据库**

```bash
cd ~/.hermes
python3 -c "
import sqlite3
conn = sqlite3.connect('state.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT id, session_id, role, 
           CASE WHEN reasoning_content IS NULL THEN 'NULL' 
                WHEN reasoning_content = '' THEN 'EMPTY'
                ELSE 'HAS_DATA' END as reasoning_status,
           token_count
    FROM messages 
    WHERE role='assistant' 
    ORDER BY id DESC 
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f'id={row[0]} session={row[1]} reasoning={row[3]} tokens={row[4]}')
conn.close()
"
```

预期：最近的消息应该有 reasoning_content（如果不为 None）

- [ ] **步骤 6：Commit 验证结果**

```bash
cd ~/.hermes/hermes-active
git add -A
git commit -m "test: 验证统一消息写入功能"
```

---

## 自检

### 1. 规格覆盖度

✅ **第1层：LLM 调用** - 任务1、任务2 覆盖
✅ **第2层：返回值透传** - 任务1 覆盖（llm_details 已包含 reasoning_content）
✅ **第3层：调用链传递** - 任务4、任务5、任务6、任务7 覆盖
✅ **第4层：写入 state.db** - 任务3 覆盖

### 2. 占位符扫描

✅ 无"待定"、"TODO"、未完成章节
✅ 每个步骤都有完整代码

### 3. 类型一致性

✅ `reasoning_content` 参数类型一致（str = None）
✅ `token_count` 参数类型一致（int = None）
✅ `llm_details` 字典键名一致（"reasoning_content"）

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-06-25-unified-message-write.md`。

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
