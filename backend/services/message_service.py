"""
消息服务
"""
import sys
import os
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_state_metadata, state_engine, ActiveSession
from models.active import TaskLog

# 加载 hermes 环境
sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))

# 用于标记写入的格式
MARKED_FORMAT = "[凯莉主动发送] {timestamp}: {content}"
UNMARKED_FORMAT = "{content}"


def _get_session_user_id(session_id: str) -> Optional[str]:
    """从 state.db 获取 session 的 user_id"""
    metadata = get_state_metadata()
    if 'sessions' not in metadata.tables:
        return None
    sessions_table = metadata.tables['sessions']
    with state_engine.connect() as conn:
        row = conn.execute(
            sessions_table.select().where(sessions_table.c.id == session_id)
        ).first()
    if row:
        return row._mapping.get('user_id')
    return None


def _get_session_source(session_id: str) -> Optional[str]:
    """从 state.db 获取 session 的 platform（source）"""
    metadata = get_state_metadata()
    if 'sessions' not in metadata.tables:
        return None
    sessions_table = metadata.tables['sessions']
    with state_engine.connect() as conn:
        row = conn.execute(
            sessions_table.select().where(sessions_table.c.id == session_id)
        ).first()
    if row:
        return row._mapping.get('source')
    return None


async def _send_to_weixin(chat_id: str, message: str) -> Dict[str, Any]:
    """真正发送消息到微信"""
    try:
        from gateway.platforms.weixin import send_weixin_direct
        token = os.environ.get('WEIXIN_TOKEN')
        account_id = os.environ.get('WEIXIN_ACCOUNT_ID')
        if not token:
            return {"success": False, "message": "WEIXIN_TOKEN 未配置"}
        extra = {"account_id": account_id}
        result = await send_weixin_direct(
            extra=extra, token=token, chat_id=chat_id, message=message
        )
        if result.get('success'):
            return {"success": True, "message": "消息已发送到微信"}
        else:
            return {"success": False, "message": f"微信发送失败: {result.get('error', '未知错误')}"}
    except ImportError:
        return {"success": False, "message": "hermes-agent 模块未安装"}
    except Exception as e:
        return {"success": False, "message": f"微信发送异常: {str(e)}"}


def _write_to_state_db(session_id: str, content: str) -> bool:
    """写入消息到 state.db"""
    try:
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return False
        messages_table = metadata.tables['messages']
        with state_engine.connect() as conn:
            conn.execute(messages_table.insert().values(
                session_id=session_id,
                role="assistant",
                content=content,
                timestamp=time.time()
            ))
            conn.commit()
        return True
    except Exception:
        return False


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
        platform: str = "weixin",
        write_to_db: bool = True,
        with_mark: bool = False
    ) -> Dict[str, Any]:
        """发送消息到微信并写入 state.db

        Args:
            session_id: 目标 session ID
            message: 消息内容
            platform: 目标平台（默认 weixin）
            write_to_db: 是否写入 state.db（默认 True）
            with_mark: 是否带 [凯莉主动发送] 标记（默认 False）
        """
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

            user_id = session_row._mapping.get('user_id')
            source = session_row._mapping.get('source')

            # 1. 真正发送消息到平台
            send_result = None
            if platform == "weixin" and user_id:
                send_result = await _send_to_weixin(user_id, message)

            # 2. 写入 state.db（带标记或不带标记）
            db_content = message
            if write_to_db:
                if with_mark:
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    db_content = MARKED_FORMAT.format(timestamp=now_str, content=message)
                _write_to_state_db(session_id, db_content)

            duration = round(time.time() - start_time, 2)

            if send_result and send_result.get("success"):
                return {
                    "success": True,
                    "message": f"消息已发送到{platform}",
                    "session_id": session_id,
                    "platform": platform,
                    "db_content": db_content if write_to_db else None,
                    "with_mark": with_mark,
                    "duration": duration
                }
            elif send_result:
                return {
                    "success": False,
                    "message": send_result.get("message", "发送失败"),
                    "session_id": session_id,
                    "platform": platform,
                    "db_content": db_content if write_to_db else None,
                    "with_mark": with_mark,
                    "duration": duration
                }
            else:
                return {
                    "success": write_to_db,
                    "message": "仅写入 DB（无平台发送）" if write_to_db else "未写入也未发送",
                    "session_id": session_id,
                    "platform": platform,
                    "db_content": db_content if write_to_db else None,
                    "with_mark": with_mark,
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
        prompts_config: Optional[Dict[str, str]] = None,
        write_to_db: bool = True,
        with_mark: bool = True
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

            # 发送消息
            send_result = await MessageService.send_message(
                session_id=session_id,
                message=final_message,
                platform="weixin",
                write_to_db=write_to_db,
                with_mark=with_mark
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
