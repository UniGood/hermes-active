# 主动消息上下文注入研究报告

## 核心问题

凯莉通过 cron job 发送主动消息后，用户回复时凯莉不知道自己刚才说了什么。

## 技术根因分析

### 当前架构

```
主动消息流程：
  cron scheduler 触发 → 独立 session 生成消息 → delivery 发送到平台
                                                ↓
                                        消息不在主会话历史中 ❌

用户回复流程：
  用户发消息 → gateway 加载主会话历史 → 历史中没有主动消息 ❌
             → LLM 不知道自己说了什么 → 回复脱节
```

### 根本原因

**两条完全独立的数据流，没有任何交叉：**

1. **主动消息**：cron job → 独立 AIAgent session → delivery → 平台发送
2. **用户回复**：gateway → 加载主会话历史（state.db） → AIAgent → 回复

主动消息的 delivery 只是调用平台 API 发送消息，**不会写入主会话的 SQLite 数据库**。

### 关键代码证据

**gateway/run.py:8680-8682**：
```python
# The agent already persisted these messages to SQLite via
# _flush_messages_to_session_db(), so skip the DB write here
agent_persisted = self._session_db is not None
```

**cron/scheduler.py:724-767**：
```python
def _deliver_result(job, content, adapters=None, loop=None):
    # 直接调用平台 API 发送消息
    # 没有任何写入 session DB 的逻辑 ❌
    from tools.send_message_tool import _send_to_platform
    ...
```

**gateway/session.py:1268-1301**：
```python
def append_to_transcript(self, session_id, message, skip_db=False):
    """可以写入 session DB，但 delivery 不调用它"""
    if self._db and not skip_db:
        self._db.append_message(session_id=session_id, ...)
```

---

## 当前方案的问题

### pre_llm_call hook 注入（当前方案）

```
用户发消息
    ↓
pre_llm_call hook 触发
    ↓
读取 cron output 目录中的最新文件
    ↓
注入到 user message 末尾
    ↓
API 调用时 LLM 看到注入内容
```

**问题：**
1. **注入位置不佳**：user message 末尾，LLM 可能忽略
2. **注入强度弱**：只是拼接在消息后面，没有强调指令
3. **不持久化**：只在当前 API 调用有效，下一轮又没了
4. **LLM 忽略**：mimo 模型对末尾注入不敏感（已验证）

---

## 解决方案研究

### 方案 A：写入 Session DB（推荐 ⭐⭐⭐⭐⭐）

**核心思路**：主动消息 delivery 时，同时写入主会话的 SQLite 数据库。

```
cron job 生成消息
    ↓
delivery 发送到平台
    ↓
同时写入主会话的 session DB（assistant 消息）✅
    ↓
用户回复 → load_transcript 加载历史 → 包含主动消息 ✅
    ↓
LLM 自然看到自己之前说的话 ✅
```

**实现方式**：

1. 在 `cron/scheduler.py` 的 `_deliver_result` 函数中添加逻辑：
   - delivery 成功后，找到目标 chat 的主会话 session_id
   - 调用 `session_db.append_message()` 写入 assistant 消息

2. 需要解决的问题：
   - 如何找到目标 chat 对应的 session_id？→ 查 session_store 的 `_entries`
   - cron delivery 和 gateway 可能在不同进程？→ 需要共享 session DB

**代码示例（概念）**：

```python
# 在 _deliver_result 中添加
def _deliver_result(job, content, adapters=None, loop=None):
    # ... 现有的 delivery 逻辑 ...
    
    # delivery 成功后，写入主会话 DB
    if delivery_success and gateway_session_store:
        session_id = find_active_session(platform, chat_id)
        if session_id:
            gateway_session_store.append_to_transcript(
                session_id,
                {"role": "assistant", "content": content, "timestamp": time.time()}
            )
```

**优点**：
- ✅ 彻底解决上下文问题
- ✅ LLM 自然看到主动消息，不需要 hook
- ✅ 会话历史完整
- ✅ 符合 #5712 和 #8793 的提案方向

**缺点**：
- ⚠️ 需要修改 Hermes 核心代码
- ⚠️ 需要考虑 cron 和 gateway 的进程隔离
- ⚠️ 需要处理 session 自动重置的情况

---

### 方案 B：改进 pre_llm_call Hook 注入（次推荐 ⭐⭐⭐⭐）

**核心思路**：改进注入位置和格式，让 LLM 更容易注意到。

**改进点**：

1. **注入到 user message 开头**（而不是末尾）
2. **更强的指令格式**
3. **注入后标记已消费**（避免重复注入）

**改进后的注入格式**：

```
⚠️⚠️⚠️ 重要上下文 ⚠️⚠️⚠️
你（凯莉）刚刚主动发给曹凡的消息（曹凡正在回复这条消息）：

[凯莉主动发送] 周三 14:22: 嗨曹凡，在忙什么呢？

请基于上面的消息来理解和回复用户，不要答非所问。
--- 以下是用户的回复 ---

用户实际消息内容
```

**实现方式**：

修改 plugin hook 的返回值，使用更强的标记：

```python
def restore_recent_proactive_messages(**kwargs):
    # ... 读取最近的主动消息 ...
    
    context = (
        "⚠️⚠️⚠️ 重要上下文 ⚠️⚠️⚠️\n"
        "你（凯莉）刚刚主动发给曹凡的消息（曹凡正在回复这条消息）：\n\n"
        f"[凯莉主动发送] {timestamp}: {message_content}\n\n"
        "请基于上面的消息来理解和回复用户，不要答非所问。\n"
        "--- 以下是用户的回复 ---"
    )
    return {"context": context}
```

**优点**：
- ✅ 不需要修改 Hermes 核心代码
- ✅ 实现简单，只改 plugin
- ✅ 开头注入比末尾注入更容易被 LLM 注意到

**缺点**：
- ⚠️ 还是依赖 LLM 是否"注意"到注入内容
- ⚠️ 注入不持久化，下一轮又没了
- ⚠️ 增加 token 消耗

---

### 方案 C：Cron Output → Memory（简单方案 ⭐⭐⭐）

**核心思路**：主动消息发送后，写入 Hindsight memory。

```
cron job 发送消息
    ↓
同时写入 Hindsight memory
    ↓
用户回复 → Hindsight recall → 找到最近的主动消息
    ↓
注入到 context → LLM 看到
```

**实现方式**：

在 cron script 或 plugin 中，发送消息后调用 `hindsight_retain`：

```python
# 发送主动消息后
hindsight_retain(
    content=f"凯莉刚刚主动发给曹凡：{message_content}",
    context="proactive message sent",
    tags=["proactive", "conversation"]
)
```

**优点**：
- ✅ 实现简单
- ✅ 跨会话持久化
- ✅ 利用现有的 Hindsight 基础设施

**缺点**：
- ⚠️ Hindsight recall 是语义搜索，可能不精确
- ⚠️ 增加 recall 延迟（2-3秒）
- ⚠️ 消耗 Hindsight token

---

### 方案 D：Agent 感知自己的 Cron 输出（官方方向 ⭐⭐⭐）

**核心思路**：让主会话的 agent 能感知 cron job 的输出。

这就是 #5712 和 #37005 提案的方向：

```yaml
# 新增配置
cron:
  inject_to_gateway: true  # cron 输出注入到主会话
```

**实现方式**：
1. cron job 完成后，scheduler 自动注入摘要到主会话历史
2. 使用 `session_store.append_to_transcript()` 写入

**优点**：
- ✅ 官方方向，可能在未来版本实现
- ✅ 彻底解决 cron 输出的上下文问题

**缺点**：
- ⚠️ 官方还未实现
- ⚠️ 需要修改 Hermes 核心代码

---

## 推荐方案

### 短期（立即可行）：方案 B + C

1. **方案 B**：改进 pre_llm_call hook 注入格式
   - 注入到开头而非末尾
   - 使用更强的标记和指令
   - 添加 `⚠️⚠️⚠️` 强调

2. **方案 C**：主动消息写入 Hindsight memory
   - 发送后立即 retain
   - 利用 recall 注入上下文

### 中期（需要开发）：方案 A

1. 编写一个 plugin 或修改 cron delivery
2. 主动消息 delivery 后写入 session DB
3. 彻底解决上下文问题

### 长期（等待官方）：方案 D

1. 关注 #5712 的进展
2. 等待官方实现 `inject_to_gateway` 配置
3. 或者提 PR 帮助实现

---

## 实验验证计划

### 验证方案 B

1. 修改 plugin hook 注入格式
2. 凯莉发送主动消息
3. 用户回复
4. 检查凯莉是否能正确延续话题

### 验证方案 A

1. 在 cron delivery 后写入 session DB
2. 检查 `load_transcript` 是否包含主动消息
3. 用户回复时检查凯莉的上下文

---

## 参考资料

- #5712: True Autonomy - Automatically Inject Cron Results into Live Gateway Chat Sessions
- #37005: Agent has no awareness of information delivered by its own cron jobs
- #24246: Cron delivery knowledge gap
- #8793: Synchronize Cron Job outputs into interactive session history
- #9645: Optional, Configurable Proactive Check-Ins
- #5250: Feature: one-shot self-nudge tool for gateway sessions
- RickConsole/hermes-proactive-checkins: Hermes 插件参考实现
- gejifeng/Hermes_Soul_patch: hermes-companion 插件
