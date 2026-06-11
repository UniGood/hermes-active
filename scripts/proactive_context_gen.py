#!/usr/bin/env python3
"""
方案 G 完整实现：基于主会话上下文生成主动消息

功能：
1. 查找最新的微信 session
2. 读取主会话的历史上下文
3. 调用 LLM 生成消息
4. 发送到微信
5. 写入 session DB（带标记）
"""
import sqlite3
import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# 添加 Hermes 路径
sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(Path.home() / '.hermes' / '.env')

from gateway.platforms.weixin import send_weixin_direct
from hermes_state import SessionDB
from agent.auxiliary_client import call_llm

# 配置
CONFIG = {
    "platform": "weixin",
    "max_context_messages": 20,
    "model": "mimo-v2.5-pro",
    "quiet_hours": "23:00-08:00",
    "max_per_day": 8,
    "min_idle_minutes": 15,
}

# 系统提示
SYSTEM_PROMPT = """你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。

要求：
- 基于最近的对话内容，自然地延续话题或发起新话题
- 语气像真人朋友，不要太正式
- 1-2 句话即可，不要太长
- 不要重复之前说过的话
- 直接输出消息内容，不要有其他解释
- 不要使用 markdown 格式

注意：
- 如果最近聊的是音乐/电影/电视剧，可以推荐相关内容
- 如果最近聊的是工作/生活，可以关心一下
- 如果最近聊的是情感话题，可以温柔地延续
"""

def get_latest_weixin_session():
    """获取最新的微信 session"""
    db_path = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, user_id, title, started_at, message_count
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
            "user_id": row[1],
            "title": row[2],
            "started_at": row[3],
            "message_count": row[4],
        }
    return None

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

def generate_proactive_message(context):
    """调用 LLM 生成主动消息"""
    # 构建上下文摘要
    context_summary = []
    for msg in context[-10:]:  # 只用最近 10 条
        role = msg["role"]
        content = msg["content"][:100] if msg["content"] else "(空)"
        context_summary.append(f"{role}: {content}")
    
    context_text = "\n".join(context_summary)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"最近的对话历史：\n{context_text}\n\n请生成一条主动消息："}
    ]
    
    try:
        response = call_llm(
            task="title_generation",  # 使用轻量任务配置
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None

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

def check_quiet_hours():
    """检查是否在安静时间"""
    quiet_hours = CONFIG["quiet_hours"]
    if not quiet_hours:
        return False
    
    start_str, end_str = quiet_hours.split("-")
    start_hour, start_min = map(int, start_str.split(":"))
    end_hour, end_min = map(int, end_str.split(":"))
    
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    current_hour = now.hour
    current_min = now.minute
    
    # 处理跨午夜的情况
    if start_hour > end_hour:
        if current_hour >= start_hour or current_hour < end_hour:
            return True
    else:
        if start_hour <= current_hour < end_hour:
            return True
    
    return False

async def main():
    """主函数"""
    print("=" * 50)
    print("方案 G：基于主会话上下文生成主动消息")
    print("=" * 50)
    
    # 0. 检查安静时间
    if check_quiet_hours():
        print("⏸️ 当前在安静时间，跳过")
        return
    
    # 1. 查找最新的微信 session
    print("\n[1] 查找最新的微信 session...")
    session = get_latest_weixin_session()
    
    if not session:
        print("❌ 未找到活跃的微信 session")
        return
    
    print(f"✅ 找到 session: {session['id']}")
    print(f"   标题: {session['title']}")
    print(f"   消息数: {session['message_count']}")
    
    # 2. 读取上下文
    print("\n[2] 读取上下文...")
    context = load_session_context(session['id'], CONFIG["max_context_messages"])
    
    if not context:
        print("❌ 上下文为空")
        return
    
    print(f"✅ 读取到 {len(context)} 条消息")
    
    # 3. 生成消息
    print("\n[3] 调用 LLM 生成消息...")
    message = generate_proactive_message(context)
    
    if not message:
        print("❌ 生成消息失败")
        return
    
    print(f"✅ 生成消息: {message}")
    
    # 4. 发送到微信
    print("\n[4] 发送到微信...")
    success = await send_to_weixin(session['user_id'], message)
    
    if not success:
        print("❌ 发送失败")
        return
    
    print("✅ 发送成功")
    
    # 5. 写入 session DB
    print("\n[5] 写入 session DB...")
    marked_message = write_marked_message(session['id'], message)
    print(f"✅ 已写入: {marked_message}")
    
    print("\n" + "=" * 50)
    print("✅ 主动消息发送完成！")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
