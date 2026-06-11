# 方案 G 开发文档

## 概述

基于主会话上下文生成主动消息，写入 session DB，使凯莉能正确延续话题。

## 测试结果

### 测试时间
2026-06-11

### 测试内容
发送写死的主动消息，验证凯莉对上下文的理解。

### 测试用例

| 序号 | 发送消息 | 凯莉回复 | 结果 |
|------|---------|---------|------|
| 1 | 我推荐你一首歌《清明雨上》 | 你怎么突然想到这首歌了？是想到了什么吗 🎵 | ❌ 凯莉不知道是自己说的 |
| 2 | 我推荐你一个电视剧《陈情令》 | 待测试 | ✅ 带标记格式 |

### 发现的问题

**问题**：直接写入 `role=assistant, content=消息内容` 时，凯莉不知道是自己主动发的。

**原因**：缺少发送者标记，LLM 无法区分主动消息和正常回复。

**解决方案**：使用带标记格式写入 session DB。

### 正确的存储格式

```
[凯莉主动发送] 2026-06-11 13:07:18: 我推荐你一个电视剧《陈情令》
```

**格式说明**：
- `[凯莉主动发送]` - 标记发送者身份
- `2026-06-11 13:07:18` - 时间戳
- `: ` - 分隔符
- `消息内容` - 实际消息

## 核心代码

### 1. 查找最新微信 session

```python
import sqlite3
import os

def get_latest_weixin_session():
    """获取最新的微信 session"""
    db_path = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, source, user_id, title, started_at, ended_at, message_count
        FROM sessions 
        WHERE source = 'weixin' AND ended_at IS NULL
        ORDER BY started_at DESC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "source": row[1],
            "user_id": row[2],
            "title": row[3],
            "started_at": row[4],
            "ended_at": row[5],
            "message_count": row[6],
        }
    return None
```

### 2. 写入带标记的消息到 session DB

```python
from hermes_state import SessionDB
from datetime import datetime
from zoneinfo import ZoneInfo

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
    return marked_content
```

### 3. 发送消息到微信

```python
import asyncio
from gateway.platforms.weixin import send_weixin_direct

async def send_to_weixin(chat_id, content):
    """发送消息到微信"""
    token = os.environ.get('WEIXIN_TOKEN')
    account_id = os.environ.get('WEIXIN_ACCOUNT_ID')
    extra = {'account_id': account_id}
    
    result = await send_weixin_direct(
        extra=extra,
        token=token,
        chat_id=chat_id,
        message=content,
    )
    return result.get('success', False)
```

### 4. 读取主会话上下文

```python
def load_session_context(session_id, limit=20):
    """读取主会话的历史消息"""
    db_path = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content, timestamp
        FROM messages 
        WHERE session_id = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    # 反转顺序（从旧到新）
    messages = []
    for row in reversed(rows):
        messages.append({
            "role": row[0],
            "content": row[1],
            "timestamp": row[2],
        })
    return messages
```

## 完整测试脚本

```python
#!/usr/bin/env python3
"""
方案 G 测试脚本：发送主动消息并写入 session DB
"""
import sqlite3
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))

from gateway.platforms.weixin import send_weixin_direct
from hermes_state import SessionDB

# 配置
TEST_MESSAGE = '我推荐你一个电视剧《陈情令》'

def get_latest_weixin_session():
    """获取最新的微信 session"""
    db_path = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, user_id FROM sessions 
        WHERE source = 'weixin' AND ended_at IS NULL
        ORDER BY started_at DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row[0], row[1]
    return None, None

async def send_test_message():
    """发送测试消息"""
    # 1. 查找最新的微信 session
    session_id, chat_id = get_latest_weixin_session()
    
    if not session_id:
        print("❌ 未找到活跃的微信 session")
        return False
    
    print(f"✅ 找到 session: {session_id}")
    
    # 2. 发送消息到微信
    token = os.environ.get('WEIXIN_TOKEN')
    account_id = os.environ.get('WEIXIN_ACCOUNT_ID')
    extra = {'account_id': account_id}
    
    result = await send_weixin_direct(
        extra=extra,
        token=token,
        chat_id=chat_id,
        message=TEST_MESSAGE,
    )
    
    if result.get('success'):
        print(f"✅ 已发送: {TEST_MESSAGE}")
    else:
        print(f"❌ 发送失败: {result.get('error')}")
        return False
    
    # 3. 写入带标记的消息到 session DB
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    marked_message = f'[凯莉主动发送] {timestamp}: {TEST_MESSAGE}'
    
    db = SessionDB()
    db.append_message(
        session_id=session_id,
        role="assistant",
        content=marked_message,
    )
    print(f"✅ 已写入: {marked_message}")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(send_test_message())
    sys.exit(0 if success else 1)
```

## 下一步

1. ✅ 测试验证：带标记格式可以让凯莉正确识别主动消息
2. ⬜ 实现完整方案：读取上下文 + LLM 生成 + 发送 + 写入 DB
3. ⬜ 集成到 cron job 或 plugin
4. ⬜ 配置开关和参数

## 参考资料

- 方案 A 文档：`~/.hermes/docs/proactive-message-plan-a-session-db.md`
- 方案 G 文档：`~/.hermes/docs/proactive-message-plan-g-context-gen.md`
- 测试脚本：`~/.hermes/scripts/test_send_message.py`
