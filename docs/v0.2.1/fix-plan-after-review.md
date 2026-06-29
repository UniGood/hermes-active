# 主动意识模块审查修复实施方案（修订版 v2）

**基于 commit b688b0e 全面审查 + 多轮代码验证**
**日期：2026-06-21**
**修订说明：多轮检验后纠正了原方案中的多处误判**

---

## 一、原方案纠正（重要）

### ❌ 误判1：5个函数被错误标记为"死代码"

原方案 P2-1 列出的"死代码"中有5个函数**仍在使用**，不能删除：

| 函数 | 原方案判定 | 实际情况 |
|------|-----------|---------|
| `generate_thought_for_delay()` (L1301) | ❌ 死代码 | ✅ L1664 run_heartbeat delay_send 分支调用 |
| `generate_memory_thought()` (L1353) | ❌ 死代码 | ✅ L1627 run_heartbeat memory 分支调用 |
| `extract_session_context()` (L1005) | ❌ 死代码 | ✅ L1310 被 generate_thought_for_delay 调用 |
| `call_hindsight_recall()` (L1134) | ❌ 死代码 | ✅ context_collector.py L251 调用 |
| `retry_thought()` (L878) | ❌ 死代码 | ✅ routers/active_consciousness.py L99 API端点 |

**真正可以删除的死代码只有4个：**
- `merge_emotion()` (L1960) — 未被调用
- `add_to_delay_queue()` v1 (L2446) — 未被调用
- `get_emotional_intensity_compat()` (L2094) — 未被调用
- `call_hindsight_with_retry()` (L96) — 仅测试引用，生产代码未使用

**预计减少：~150行**（非原方案的~500行）

### ❌ 误判2：变量别名不能删除

原方案 P2-2 建议删除 `_build_prompt` 中的别名。但 _DEFAULTS 模板用的是 `{session_context}`、`{hindsight_context}`、`{time}`，而 ThoughtEngine.PROMPT_TEMPLATE 用的是 `{conversations_json}`、`{memories}`、`{time_display}`。**别名是必要的向后兼容**，删除会导致 _DEFAULTS 模板格式化失败。

### ⚠️ 误判3：P0-2 retry_count 的严重性被高估

keep 分支递增 retry_count 的行为不一定是 bug：
- 念头先进入延迟队列（score 在 delay_threshold 和 memory_threshold 之间）
- 每次心跳重评估，如果 score 仍在中间区间 → keep 分支
- retry_count 递增 + 设置 next_retry_at（30分钟后）
- max_retry=3 × retry_interval=30min = 90分钟后丢弃

**设计意图：** 防止低分念头无限期滞留队列。keep 分支的含义是"有机会但还没到发送时机"，retry_count 在这里是"评估周期计数"而非"发送失败次数"。

**但确实有问题：** 如果用户持续中等情绪（score 一直在 0.1~0.35 之间），念头会在从未尝试发送的情况下被丢弃。建议改为：keep 分支不递增 retry_count，改为单独的 `keep_count`，或者直接用 `max_age_hours` 控制过期。

**降级为 [建议修改]**

### ⚠️ 误判4：SKIP 判断的严重性被高估

原方案 P1-3 认为 `startswith("SKIP")` 过于宽松。但提示词明确说"如果没想到，回复 'SKIP'。直接说，不要解释。"，LLM 几乎不可能回复 "SKIP the details..." 这种内容。`startswith` 反而能处理 "SKIP\n" 或 "SKIP " 等边界情况。

**降级为 [仅供参考]**

---

## 二、改动文件清单（修订版）

| 文件 | 改动类型 | 涉及阶段 |
|------|---------|---------|
| `backend/services/active_consciousness_service.py` | 修改 + 删除少量死代码 | P0 / P1 / P2 |
| `backend/services/thought_engine.py` | 修改 | P1 |
| `backend/services/context_collector.py` | 修改 | P0 |
| `backend/tests/test_active_consciousness.py` | 修改（删除 call_hindsight_with_retry 相关测试） | P2 |

**前端不需改动。**

---

## 三、P0 — 影响正确性（必须修复）

### P0-1: `get_recent_thoughts_from_db` 查询条件不匹配 ✅ 验证通过

**问题：** 查询 `decision IN ('send', 'memory')` 但实际值是 `'auto_send'`/`'delay_send'`/`'memory'`/`'skip'`。`'send'` 不匹配任何实际值。

**文件：** `active_consciousness_service.py` L2685
**修改：**
```python
# 修改前
"WHERE decision IN ('send', 'memory') "
# 修改后
"WHERE decision IN ('auto_send', 'delay_send', 'memory') "
```

---

### P0-2: `message_sent` 不考虑保护拦截 ✅ 验证通过

**问题：** L1733 只判断 decision_type，被保护机制拦截后仍报 True。

**文件：** `active_consciousness_service.py` L1733
**修改：** 需要在决策处理阶段记录实际发送结果：

```python
# 在 auto_send 分支处理后（约 L1688），记录到 all_details
if sent:
    all_details["actual_sent"] = True

# L1733 修改为
"message_sent": all_details.get("actual_sent", False),
```

同时删除 L1721 重复的 `duration_ms` 计算。

---

### P0-3: `get_hindsight_client` 参数变化不生效 ✅ 验证通过

**问题：** 注释说"base_url 或 timeout 变化时重建"，但代码未实现。

**文件：** `active_consciousness_service.py` L65-70
**修改：**
```python
def get_hindsight_client(base_url: str = "http://localhost:8888", timeout: float = 30.0) -> Hindsight:
    global _hindsight_client
    if _hindsight_client is not None:
        # 检查参数是否变化
        if getattr(_hindsight_client, '_base_url', None) != base_url or \
           getattr(_hindsight_client, '_timeout', None) != timeout:
            _hindsight_client = None
    if _hindsight_client is None:
        _hindsight_client = Hindsight(base_url=base_url, timeout=timeout)
        _hindsight_client._base_url = base_url
        _hindsight_client._timeout = timeout
    return _hindsight_client
```

> 注：不确定 Hindsight 类是否有 base_url/timeout 属性，用 getattr 安全访问。如果没有，用自定义属性记录。

---

### P0-4: `_get_structured_conversations` 只查单个 session ✅ 验证通过

**问题：** L175 只调用 `get_or_create_active_session` 获取当前活跃 session，如果 session 被重置过，旧 session 的消息会被遗漏。

**文件：** `context_collector.py` L170-196
**修改：** 改为直接查 messages 表，不限制单个 session：

```python
with state_engine.connect() as conn:
    query = text("""
        SELECT m.role, m.content, m.timestamp
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE s.source = :source
        AND m.role IN ('user', 'assistant')
        AND CAST(m.timestamp AS REAL) > :cutoff
        ORDER BY m.timestamp ASC
    """)
    result = conn.execute(query, {
        "source": platform,
        "cutoff": cutoff_timestamp
    })
    messages = [dict(row._mapping) for row in result]
```

---

## 四、P1 — 影响性能/稳定性

### P1-1: hermes 模式 LLM 同步调用阻塞事件循环 ✅ 验证通过

**影响范围：**
- `thought_engine.py` L188 — ThoughtEngine._call_llm
- `active_consciousness_service.py` L1253 — evaluate_emotion_with_llm._call_llm
- `active_consciousness_service.py` L1331 — generate_thought_for_delay
- `active_consciousness_service.py` L1385 — generate_memory_thought

**共4处**需要包装 `asyncio.to_thread()`。

**修改示例（ThoughtEngine）：**
```python
# thought_engine.py L188
import asyncio
raw = await asyncio.to_thread(
    lambda: call_llm(
        task='title_generation',
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
)
raw = raw.choices[0].message.content.strip()
```

---

### P1-2: 配置无缓存 ✅ 验证通过

**问题：** `get_config()` 每次遍历所有 _DEFAULTS key 查 DB，一次心跳调用 3-5 次。

**文件：** `active_consciousness_service.py` get_config() 方法
**修改：** 加模块级缓存，TTL 60秒，set_config 时清除。

---

### P1-3: `_build_prompt` 每次创建新 ActiveSession ⚠️ 降级为 [建议修改]

**问题：** L117 每次调用 `ConfigService.get_config(ActiveSession(), ...)` 创建新 DB session。

**修改：** 优先从 `self.config` 读取，减少 DB 查询：
```python
prompt_template = self.config.get("prompts", {}).get("thought_generation") \
    or _DEFAULTS.get("active_consciousness.prompts.thought_generation") \
    or self.PROMPT_TEMPLATE
```

> 注：`self.config` 在 ThoughtEngine.__init__ 时传入，应该包含 prompts 配置。需验证 run_heartbeat 传给 ThoughtEngine 的 config 是否包含 prompts。

---

### P1-4: `_recall_memories` query 可能为空 ✅ 验证通过

**问题：** L237-241 取最近5条消息拼 query，如果最近5条全是 assistant 回复，query 为空。

**修改：** 从后往前找用户消息：
```python
query = " ".join([
    msg.get("content", "")
    for msg in reversed(conversations)
    if msg.get("role") == "user"
][:5]) or "最近的想法"
```

---

### P1-5: LLM 全 0 判断用精确浮点 ✅ 验证通过

**文件：** `active_consciousness_service.py` L1571
**修改：**
```python
# 修改前
if llm_assessed.valence == 0.0 and llm_assessed.arousal == 0.0 and llm_assessed.social_need == 0.0:
# 修改后
if abs(llm_assessed.valence) < 0.01 and abs(llm_assessed.arousal) < 0.01 and abs(llm_assessed.social_need) < 0.01:
```

---

## 五、P2 — 代码质量

### P2-1: 删除真正的死代码（4个函数）

| 函数 | 行号 | 原因 |
|------|------|------|
| `merge_emotion()` | L1960 | 被 merge_emotion_dynamic 替代，未被调用 |
| `add_to_delay_queue()` v1 | L2446 | 被 add_to_delay_queue_v2 替代，未被调用 |
| `get_emotional_intensity_compat()` | L2094 | 向后兼容函数，未被调用 |
| `call_hindsight_with_retry()` | L96 | 仅测试引用，生产代码未使用 |

**⚠️ 不能删除的：**
- `generate_thought_for_delay` — run_heartbeat delay_send 分支调用
- `generate_memory_thought` — run_heartbeat memory 分支调用
- `extract_session_context` — generate_thought_for_delay 调用
- `call_hindsight_recall` — context_collector.py 调用
- `retry_thought` — API 端点（虽然是 TODO 空实现）

**但** `generate_thought_for_delay` 和 `generate_memory_thought` 的 LLM 调用逻辑与 ThoughtEngine 重复，建议后续重构为复用 ThoughtEngine。本次不动。

---

### P2-2: `duration_ms` 重复计算

**文件：** `active_consciousness_service.py` L1719-1721
```python
duration_ms = round((time.time() - start_time) * 1000)  # L1719
logger.info("=== 心跳完成 === ...")                        # L1720
duration_ms = round((time.time() - start_time) * 1000)  # L1721 重复
```
删除 L1721。

---

### P2-3: `gap_send`/`idle_send`/`long_idle_send` 死分支

`make_decision_v2` 只返回 `auto_send`/`delay_send`/`memory`/`skip`，但代码多处检查已废弃的值。

**清理位置：**
- L1677: `elif decision_type in ("auto_send", "gap_send", "idle_send", "long_idle_send"):`
- L1733: `"message_sent": decision_type in ("auto_send", "gap_send", "idle_send", "long_idle_send"),`

简化为只检查 `"auto_send"`。

---

### P2-4: SKIP 判断 [仅供参考]

`startswith("SKIP")` 在实际场景中不会误判，但可以收紧为 `in ("SKIP", "SKIP.", "SKIP,")` 以增加安全性。优先级低。

---

## 六、实施顺序

### 第一轮（P0，4项，预计30分钟）

1. P0-1: 修复查询条件 `'send'` → `'auto_send', 'delay_send'`
2. P0-2: 修复 message_sent 判断 + 删除重复 duration_ms
3. P0-3: 修复 get_hindsight_client 参数检测
4. P0-4: 修复单 session 查询限制
5. 运行测试验证

### 第二轮（P1，5项，预计30分钟）

1. P1-1: 4处 LLM 同步调用包装 asyncio.to_thread
2. P1-2: 配置缓存
3. P1-3: _build_prompt 减少 DB 查询
4. P1-4: _recall_memories query 修复
5. P1-5: LLM 全 0 判断修复
6. 运行测试验证

### 第三轮（P2，4项，预计20分钟）

1. P2-1: 删除4个真正死代码函数
2. P2-2: 清理死分支
3. P2-3: 删除重复 duration_ms
4. 全量回归测试

---

## 七、风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| P0-4 改查询逻辑可能查到过多消息 | 上下文超长 | 保留 conversation_max_chars 单条截断 |
| P1-1 asyncio.to_thread 行为变化 | LLM 调用异常 | lambda 包装保持参数传递 |
| P1-2 缓存导致配置变更不生效 | 用户改了配置但不生效 | set_config 时清除缓存 |
| P2-1 删除 call_hindsight_with_retry | 测试失败 | 同步删除测试用例 |
