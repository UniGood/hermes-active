"""
消息服务
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_state_metadata, state_engine


class MessageService:
    """消息服务类"""

    @staticmethod
    def get_messages(
        db: Session,
        session_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """获取消息列表"""
        metadata = get_state_metadata()

        if 'messages' not in metadata.tables:
            return {"total": 0, "items": []}

        messages_table = metadata.tables['messages']

        # 获取总数
        count_query = text(f"SELECT COUNT(*) FROM messages WHERE session_id = :session_id")
        with state_engine.connect() as conn:
            total = conn.execute(count_query, {"session_id": session_id}).scalar()

        # 分页查询
        query = (
            messages_table.select()
            .where(messages_table.c.session_id == session_id)
            .order_by(messages_table.c.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return {"total": total, "items": items}

    @staticmethod
    def search_messages(
        db: Session,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """搜索消息"""
        metadata = get_state_metadata()

        if 'messages' not in metadata.tables:
            return {"total": 0, "items": []}

        messages_table = metadata.tables['messages']

        # 搜索查询
        query = (
            messages_table.select()
            .where(messages_table.c.content.like(f"%{keyword}%"))
            .order_by(messages_table.c.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        # 获取总数（简化处理）
        total = len(items)

        return {"total": total, "items": items}

    @staticmethod
    async def send_message(
        session_id: str,
        message: str,
        platform: str = "weixin"
    ) -> Dict[str, Any]:
        """发送消息"""
        # TODO: 实现实际的消息发送逻辑
        # 1. 获取 session 信息
        # 2. 调用平台发送接口
        # 3. 写入 session DB（上下文注入）

        return {
            "success": True,
            "message": "消息发送成功",
            "session_id": session_id,
            "platform": platform
        }

    @staticmethod
    async def send_proactive_message(
        session_id: str,
        message: str,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """发送主动消息"""
        # TODO: 实现主动消息发送逻辑
        # 1. 如果 use_llm，调用 LLM 生成消息
        # 2. 发送消息到平台
        # 3. 写入 session DB（带标记）

        return {
            "success": True,
            "message": "主动消息发送成功",
            "session_id": session_id,
            "use_llm": use_llm
        }
