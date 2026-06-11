#!/usr/bin/env python3
"""
方案 G 测试：发送写死的消息到微信，并写入 session DB
"""
import asyncio
import sqlite3
import os
import sys
import time
from pathlib import Path

# 添加 Hermes 路径
sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))

from gateway.platforms.weixin import send_weixin_direct
from hermes_state import SessionDB

# 测试消息
TEST_MESSAGE = "曹凡，在忙什么呢？刚才聊的那些，你还想继续吗？"

def get_latest_weixin_session():
    """获取最新的微信 session"""
    db_path = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, source, user_id, title, started_at
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
        }
    return None

def write_to_session_db(session_id, content):
    """写入 session DB"""
    db = SessionDB()
    db.append_message(
        session_id=session_id,
        role="assistant",
        content=content,
    )
    print(f"✅ 已写入 session DB: {session_id}")

async def send_test_message():
    """发送测试消息到微信"""
    # 1. 查找最新的微信 session
    print("[1] 查找最新的微信 session...")
    session = get_latest_weixin_session()
    
    if not session:
        print("❌ 未找到活跃的微信 session")
        return False
    
    print(f"✅ 找到 session: {session['id']}")
    
    # 2. 获取微信配置
    print("[2] 获取微信配置...")
    token = os.environ.get('WEIXIN_TOKEN')
    account_id = os.environ.get('WEIXIN_ACCOUNT_ID')
    chat_id = session['user_id']
    
    if not token:
        print("❌ 未找到微信 token（环境变量 WEIXIN_TOKEN）")
        return False
    
    extra = {'account_id': account_id}
    print(f"✅ 微信配置已获取")
    
    # 3. 发送消息
    print(f"[3] 发送测试消息: {TEST_MESSAGE}")
    result = await send_weixin_direct(
        extra=extra,
        token=token,
        chat_id=chat_id,
        message=TEST_MESSAGE,
    )
    
    if result.get('success'):
        print("✅ 消息发送成功！")
    else:
        print(f"❌ 消息发送失败: {result.get('error')}")
        return False
    
    # 4. 写入 session DB
    print("[4] 写入 session DB...")
    write_to_session_db(session['id'], TEST_MESSAGE)
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print(f"消息已发送到微信: {TEST_MESSAGE}")
    print("请在微信回复，测试凯莉对上下文的理解")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = asyncio.run(send_test_message())
    sys.exit(0 if success else 1)
