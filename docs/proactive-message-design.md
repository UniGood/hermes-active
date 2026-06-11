# 主动消息设计文档

## 目标

定时读取主会话的完整上下文，调用 LLM 生成消息，然后发送到用户并写入 session DB。
这样 LLM 在生成消息时能看到完整的对话历史，消息更自然、更连贯。

## 核心优势

1. **上下文连贯**：LLM 看到完整的对话历史，消息更自然
2. **话题延续**：能自然延续最近的聊天话题
3. **身份一致**：LLM 知道自己是凯莉，知道用户是曹凡
4. **不依赖 hook**：不需要 pre_llm_call hook 注入上下文

## 架构设计

```
定时触发（cron job / heartbeat）
    ↓
找到主会话 session_id
    ↓
读取主会话历史（load_transcript）
    ↓
构建 prompt（系统提示 + 历史 + 生成指令）
    ↓
调用 LLM 生成消息
    ↓
通过平台 API 发送到微信
    ↓
写入 session DB（保持上下文完整）
```

## 实现方案

### 独立 Python 脚本 + Cron Job

**核心思路**：编写一个独立的 Python 脚本，由 cron job 定时调用。

**文件结构**：
```
~/.hermes/hermers-active/
├── docs/
│   ├── proactive-message-design.md    # 设计文档
│   ├── proactive-message-dev-doc.md   # 开发文档
│   └── proactive-message-research.md  # 技术研究
└── scripts/
    ├── proactive_context_gen.py       # 主脚本
    ├── test_context_read.py           # 上下文读取测试
    └── test_send_message.py           # 消息发送测试
```

**脚本逻辑**：

```python
def main():
    # 1. 查找主会话
    session_id = find_main_session()
    
    # 2. 读取上下文
    context = load_session_context(session_id)
    
    # 3. 生成消息
    message = generate_proactive_message(context)
    
    # 4. 发送到微信
    send_to_weixin(chat_id, message)
    
    # 5. 写入 session DB
    write_marked_message(session_id, message)
```

**Cron Job 配置**：
```bash
hermes cron create "0,20,40 6-23 * * *" \
  "运行主动消息生成脚本" \
  --name proactive-context-gen \
  --script proactive_context_gen.py \
  --deliver local
```

## 关键技术点

### 1. 查找主会话

```python
def get_latest_weixin_session():
    """获取最新的微信 session"""
    cursor.execute("""
        SELECT id, user_id FROM sessions 
        WHERE source = 'weixin' AND ended_at IS NULL
        ORDER BY started_at DESC LIMIT 1
    """)
```

### 2. 读取上下文

```python
def load_session_context(session_id, limit=20):
    """读取主会话的历史消息"""
    cursor.execute("""
        SELECT role, content, timestamp
        FROM messages 
        WHERE session_id = ?
        ORDER BY timestamp DESC LIMIT ?
    """, (session_id, limit))
```

### 3. 写入 session DB

```python
def write_marked_message(session_id, content):
    """写入带标记的消息到 session DB"""
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    marked_content = f'[凯莉主动发送] {timestamp}: {content}'
    
    db = SessionDB()
    db.append_message(
        session_id=session_id,
        role="assistant",
        content=marked_content,
    )
```

### 4. 发送到微信

```python
async def send_to_weixin(chat_id, content):
    """发送消息到微信"""
    result = await send_weixin_direct(
        extra=extra,
        token=token,
        chat_id=chat_id,
        message=content,
    )
    return result.get('success', False)
```

## 存储格式

### 带标记格式（推荐）

```
role=assistant
content=[凯莉主动发送] 2026-06-11 13:05:48: 我推荐你一首歌《清明雨上》
```

**优点**：LLM 能明确识别这是主动消息

### 不带标记格式

```
role=assistant
content=我推荐你一首歌《清明雨上》
```

**说明**：需要测试 LLM 是否能正确识别

## 配置项

```python
CONFIG = {
    "platform": "weixin",           # 目标平台
    "max_context_messages": 20,     # 读取的最大消息数
    "model": "mimo-v2.5-pro",       # 使用的模型
    "quiet_hours": "23:00-08:00",   # 安静时间
    "max_per_day": 8,               # 每日最大发送数
    "min_idle_minutes": 15,         # 最小空闲时间
}
```

## 下一步

1. ✅ 测试验证：带标记格式可以让凯莉正确识别主动消息
2. ⬜ 集成到 cron job 或 plugin
3. ⬜ 配置开关和参数
4. ⬜ 添加安静时间、每日上限等防骚扰机制
5. ⬜ 支持多平台（飞书、Telegram 等）
