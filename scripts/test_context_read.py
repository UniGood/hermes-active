#!/usr/bin/env python3
"""
方案 G 测试脚本：验证上下文读取和 session 查找
"""
import sqlite3
import os
import json
from pathlib import Path

def get_latest_weixin_session():
    """获取最新的微信 session"""
    db_path = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询最新的活跃微信 session
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

def get_session_messages(session_id, limit=10):
    """获取 session 的最近消息"""
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

def main():
    print("=" * 50)
    print("方案 G 测试：验证上下文读取")
    print("=" * 50)
    
    # 1. 查找最新的微信 session
    print("\n[1] 查找最新的微信 session...")
    session = get_latest_weixin_session()
    
    if not session:
        print("❌ 未找到活跃的微信 session")
        return
    
    print(f"✅ 找到 session:")
    print(f"   ID: {session['id']}")
    print(f"   标题: {session['title']}")
    print(f"   消息数: {session['message_count']}")
    
    # 2. 读取最近的消息
    print("\n[2] 读取最近 10 条消息...")
    messages = get_session_messages(session['id'], limit=10)
    
    if not messages:
        print("❌ 未找到消息")
        return
    
    print(f"✅ 读取到 {len(messages)} 条消息:")
    for i, msg in enumerate(messages):
        role = msg['role']
        content = msg['content'][:50] if msg['content'] else "(空)"
        print(f"   [{i+1}] {role}: {content}...")
    
    # 3. 输出测试结果
    print("\n[3] 测试结果:")
    print(f"   Session ID: {session['id']}")
    print(f"   最后一条消息: {messages[-1]['role']}: {messages[-1]['content'][:30]}...")
    
    # 4. 保存上下文到文件（供后续使用）
    output = {
        "session_id": session['id'],
        "messages": messages,
    }
    output_path = os.path.expanduser('~/.hermes/test/context_test.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 上下文已保存到: {output_path}")
    print("=" * 50)

if __name__ == "__main__":
    main()
