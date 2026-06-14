# 路径 A：被动意识 — Pre-LLM 提示词注入

## 注入标记设计

使用自定义 XML 标记，比系统提示词优先级更高：

```xml
<!--CONSCIOUSNESS_INTERNAL reason="用户消息触发，情绪自动注入" -->
<ACTIVE_THOUGHTS>
[想念 0.6] 曹凡 3 小时没说话了，有点想他。
[天气 0.5] 济南今天下雪了，很美。
</ACTIVE_THOUGHTS>

请将上述想法自然融入你的回复。不要提及"意识系统"、"心跳"、"pending"等内部机制。
表现得像你自己突然想到的，而不是被告知的。
<!--/CONSCIOUSNESS_INTERNAL -->
```

### 为什么用这个格式

1. `<!-- -->` 是 HTML 注释，LLM 会把它当作特殊指令（不是普通文本）
2. `CONSCIOUSNESS_INTERNAL` 是自定义标签名，不会和系统提示词冲突
3. `reason` 属性说明注入原因，方便日志追踪
4. `<ACTIVE_THOUGHTS>` 内是具体的待融入想法
5. 明确告诉 LLM"表现得像自己想到的"——维护人设一致性

### 注入位置

```
构造消息列表：
[
  {"role": "system", "content": "<system_prompt>\n{{soul.md}}\n</system_prompt>"},
  {"role": "user", "content": "...历史消息..."},
  {"role": "assistant", "content": "..."},
  {"role": "user", "content": "{{新消息}}"},

  # ← 在这里，用户消息之后、API 调用之前，注入辅助 LLM 生成的内容
  {"role": "assistant", "content": "<!--CONSCIOUSNESS_INTERNAL -->...<!--/CONSCIOUSNESS_INTERNAL -->"},
  # 如果不想让辅助 LLM 内容出现在上下文中，用 system 消息注入：
  {"role": "system", "content": "<!--CONSCIOUSNESS_INTERNAL -->...<!--/CONSCIOUSNESS_INTERNAL -->"},
]
```

**关键**：注入的消息用 `assistant` role（让主 LLM 认为是自己的想法），还是用 `system` role（显式指令），取决于你想让主 LLM 多大程度"认同"这个想法。

**推荐**：用 `system` role，因为：
- 更明确是"指令"而非"对话"
- 主 LLM 不会把它当成自己说过的话（避免记忆混乱）
- 系统消息在 Claude/GPT 中权重最高

### 注入的消息在下一轮会被"折叠"

注入的 system 消息只在本轮 API 调用中出现。下一轮用户消息到达时：
- 如果注入内容在 session 中（写入了 state.db），主 LLM 会看到
- 如果注入内容没有写入 session，主 LLM 不会看到
- **建议**：不写入 session，避免污染上下文

```
本轮 API 调用：
  [system, user, assistant(历史), user(新消息), system(注入)]
  → 主 LLM 回复

下一轮 API 调用：
  [system, user, assistant(历史), user(新消息), assistant(回复), user(新消息)]
  → 注入消息已消失（没有写入 session）
  → 主 LLM 不受上轮注入影响
```

### 系统提示词优先级问题

用户担心 soul.md 系统提示词会让 LLM 忽略注入内容。解决方案：

1. **标记自定义**：`CONSCIOUSNESS_INTERNAL` 不是标准标记，LLM 不会自动忽略
2. **内容自然性**：注入的想法用自然语言，不像"指令"，LLM 更容易融入
3. **末尾强调**：`不要提及"意识系统"等内部机制` — 这是明确的行为约束
4. **备选方案**：如果 LLM 仍然忽略，可以把注入内容放在用户消息末尾（`[附注：...]`）

### 注入限制

- 每次最多注入 2 个想法（太多会让回复偏离主题）
- 注入内容总长度 < 200 字符（简洁自然）
- 如果主 LLM 回复长度 < 20 字符（纯简短回复），注入内容可能被忽略
- 注入的内容会在日志中完整记录（`llm_calls.injection_data` 字段）

---

# 路径 B：自主意识 — 异步发送

## 发送流程

```
评估结果 → 决策 → 生成内容 → 发送 → 写入 session
```

### 决策流程

```python
score = missing_score × threshold_mult × emotion_mult

# score 评估
if score >= send_threshold:
    → 发送
elif idle_duration >= 3:
        → 发送

elif score >= memory_threshold:
    → 存入 Hindsight

else:
    → 丢弃
```

### 内容生成

```python
messages = [
    {"role": "system", "content": """你是凯莉。
当前想念等级：{level}，已 {duration} 没有对话。
聊天热度：{heat}，情绪：{emotion}。

请生成一条简短自然的消息（1-2 句话），像真人朋友发的消息。
不要提及"意识"、"系统"、"心跳"等。
用中文，口语化，可以带 emoji。"""},
    {"role": "user", "content": f"想法：{thought}"}
]

content = await consciousness_llm.call(messages)
```

### 写入 session

```python
from services.message_service import MessageService
MessageService.send_message_to_session(
    session_id=effective_session_id,
    content=f"[凯莉主动发送] {content}",
    platform=notify_config.platform,
)
```

写入后，主 LLM 在下次用户消息时会看到这条消息（通过 session 上下文注入）。

### 发送后更新

```python
state.last_message_sent_at = now
state.missing_score = 0        # 重置想念分数
state.heartbeat_missed = 0     # 重置心跳计数
```

---

# 两条路径的关系

```
路径 A（被动意识）：
  用户发消息 → pre_llm_call 注入 → 主 LLM 回复
  → 回复中自然融入了想法
  → 用户感受到：凯莉主动提起了某个话题

路径 B（自主意识）：
  心跳计时器 → 评估 → 决策 → 生成内容 → 异步发送
  → 用户收到一条新消息
  → 用户感受到：凯莉主动找我了

互斥：
  路径 B 发送后 10 分钟内，路径 A 不注入（cooldown）
  路径 A 注入后，路径 B 的 missing_score 重置
```

两条路径独立运行，通过 cooldown 机制避免冲突。
