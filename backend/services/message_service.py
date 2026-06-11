"""
消息服务
"""
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_state_metadata, state_engine, ActiveSession
from models.active import TaskLog


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
        """发送消息（上下文注入到 state.db）"""
        start_time = time.time()
        try:
            # 验证 session 存在
            metadata = get_state_metadata()
            if 'sessions' not in metadata.tables:
                return {"success": False, "message": "sessions 表不存在"}

            sessions_table = metadata.tables['sessions']
            with state_engine.connect() as conn:
                session_row = conn.execute(
                    sessions_table.select().where(sessions_table.c.id == session_id)
                ).first()

            if not session_row:
                return {"success": False, "message": f"Session {session_id} 不存在"}

            # 写入消息到 state.db（上下文注入）
            if 'messages' in metadata.tables:
                messages_table = metadata.tables['messages']
                with state_engine.connect() as conn:
                    conn.execute(messages_table.insert().values(
                        session_id=session_id,
                        role="assistant",
                        content=message,
                        timestamp=time.time()
                    ))
                    conn.commit()

            duration = round(time.time() - start_time, 2)
            return {
                "success": True,
                "message": "消息发送成功",
                "session_id": session_id,
                "platform": platform,
                "duration": duration
            }
        except Exception as e:
            return {"success": False, "message": f"消息发送失败: {str(e)}"}

    @staticmethod
    async def send_proactive_message(
        session_id: str,
        message: str,
        use_llm: bool = False,
        llm_config: Optional[Dict[str, Any]] = None,
        prompts_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送主动消息"""
        start_time = time.time()
        try:
            final_message = message

            # 如果使用 LLM 生成消息
            if use_llm and llm_config and prompts_config:
                from services.llm_service import LLMService

                # 获取 session 上下文
                context_msgs = MessageService.get_session_context_raw(session_id, limit=20)
                context_text = "\n".join(
                    f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                    for m in context_msgs
                )

                system_prompt = prompts_config.get("system", "")
                generation_template = prompts_config.get("generation", "{context}")
                user_prompt = generation_template.replace("{context}", context_text)

                llm_result = await LLMService.generate_message(
                    llm_config=llm_config,
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=200
                )

                if llm_result.get("success"):
                    final_message = llm_result["content"]
                else:
                    return {
                        "success": False,
                        "message": f"LLM 生成消息失败: {llm_result.get('message', '未知错误')}"
                    }

            # 发送消息（上下文注入）
            send_result = await MessageService.send_message(
                session_id=session_id,
                message=final_message,
                platform="weixin"
            )

            duration = round(time.time() - start_time, 2)
            if send_result.get("success"):
                return {
                    "success": True,
                    "message": "主动消息发送成功",
                    "session_id": session_id,
                    "use_llm": use_llm,
                    "generated_message": final_message if use_llm else None,
                    "duration": duration
                }
            else:
                return send_result

        except Exception as e:
            return {"success": False, "message": f"主动消息发送失败: {str(e)}"}

    @staticmethod
    def get_session_context_raw(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取 session 上下文（原始数据）"""
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return []

        messages_table = metadata.tables['messages']
        query = (
            messages_table.select()
            .where(messages_table.c.session_id == session_id)
            .order_by(messages_table.c.timestamp.desc())
            .limit(limit)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return list(reversed(items))

    @staticmethod
    def create_task_log(
        task_type: str,
        status: str,
        message: str = None,
        error: str = None,
        duration: float = None
    ):
        """创建任务日志"""
        db = ActiveSession()
        try:
            log = TaskLog(
                task_type=task_type,
                status=status,
                message=message,
                error=error,
                duration=duration
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
