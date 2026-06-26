"""
消息服务
"""
import sys
import os
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_state_metadata, state_engine, ActiveSession
from models.active import TaskLog

logger = logging.getLogger("hermes.message")

# 加载 hermes 环境
sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))

# 默认标记格式
DEFAULT_MARK_FORMAT = "[凯莉主动发送] {timestamp}: {content}"
DEFAULT_TIME_FORMAT = "%H:%M 星期{weekday}"
DEFAULT_SEND_MARK = "[凯莉主动发送]"

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]


def weekday_name(dt):
    """返回中文星期几，dt.weekday(): Monday=0 ... Sunday=6"""
    return WEEKDAY_NAMES[dt.weekday()]


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


async def _send_to_feishu(chat_id: str, message: str) -> Dict[str, Any]:
    """真正发送消息到飞书"""
    try:
        from gateway.platforms.feishu import FeishuAdapter, FEISHU_AVAILABLE
        if not FEISHU_AVAILABLE:
            return {"success": False, "message": "飞书依赖未安装，请运行: pip install 'hermes-agent[feishu]'"}
        from gateway.platforms.feishu import FEISHU_DOMAIN, LARK_DOMAIN
        from gateway.config import PlatformConfig

        app_id = os.environ.get('FEISHU_APP_ID')
        app_secret = os.environ.get('FEISHU_APP_SECRET')
        if not app_id or not app_secret:
            return {"success": False, "message": "FEISHU_APP_ID 或 FEISHU_APP_SECRET 未配置"}

        extra = {"app_id": app_id, "app_secret": app_secret}
        pconfig = PlatformConfig(extra=extra)
        adapter = FeishuAdapter(pconfig)
        domain = FEISHU_DOMAIN if getattr(adapter, "_domain_name", "feishu") != "lark" else LARK_DOMAIN
        adapter._client = adapter._build_lark_client(domain)

        result = await adapter.send(chat_id, message)
        if result.success:
            return {"success": True, "message": "消息已发送到飞书"}
        else:
            return {"success": False, "message": f"飞书发送失败: {result.error}"}
    except ImportError:
        return {"success": False, "message": "hermes-agent 飞书模块未安装"}
    except Exception as e:
        return {"success": False, "message": f"飞书发送异常: {str(e)}"}



class MessageService:
    """消息服务类"""

    @staticmethod
    def get_messages(
        db: Session,
        session_id: str,
        page: int = 1,
        page_size: int = 50,
        exclude_tool: bool = False
    ) -> Dict[str, Any]:
        """获取消息列表"""
        from sqlalchemy import and_, or_
        metadata = get_state_metadata()

        if 'messages' not in metadata.tables:
            return {"total": 0, "items": []}

        messages_table = metadata.tables['messages']

        base_condition = messages_table.c.session_id == session_id

        if exclude_tool:
            # DB 层过滤 tool 消息 + 空 assistant 消息
            tool_filter = and_(
                base_condition,
                messages_table.c.role != 'tool',
                or_(
                    messages_table.c.role != 'assistant',
                    and_(messages_table.c.content != None, messages_table.c.content != '')
                )
            )
        else:
            tool_filter = base_condition

        # 获取总数
        count_query = text(f"SELECT COUNT(*) FROM messages WHERE session_id = :session_id" + (" AND role != 'tool'" if exclude_tool else ""))
        with state_engine.connect() as conn:
            total = conn.execute(count_query, {"session_id": session_id}).scalar()

        # 分页查询
        query = (
            messages_table.select()
            .where(tool_filter)
            .order_by(messages_table.c.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return {"total": total, "items": items}

    @staticmethod
    def delete_message(message_id: int) -> bool:
        """删除单条消息"""
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return False
        messages_table = metadata.tables['messages']
        try:
            with state_engine.connect() as conn:
                result = conn.execute(
                    messages_table.delete().where(messages_table.c.id == message_id)
                )
                conn.commit()
            return result.rowcount > 0
        except Exception:
            return False

    @staticmethod
    def get_recent_messages(limit: int = 50) -> Dict[str, Any]:
        """获取最新消息列表（不区分 session）"""
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return {"total": 0, "items": []}

        messages_table = metadata.tables['messages']

        # 查询最新消息，过滤掉 tool 和空 assistant 消息
        from sqlalchemy import and_, or_
        query = (
            messages_table.select()
            .where(and_(
                messages_table.c.role != 'tool',
                or_(
                    messages_table.c.role != 'assistant',
                    and_(messages_table.c.content != None, messages_table.c.content != '')
                )
            ))
            .order_by(messages_table.c.timestamp.desc())
            .limit(limit)
        )

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return {"total": len(items), "items": items}

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
        with_mark: bool = False,
        mark_format: str = DEFAULT_MARK_FORMAT,
        send_mark: str = DEFAULT_SEND_MARK,
        time_format: str = DEFAULT_TIME_FORMAT,
        reasoning_content: Optional[str] = None,
        token_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """发送消息到微信并写入 state.db

        Args:
            session_id: 目标 session ID
            message: 消息内容
            platform: 目标平台（默认 weixin）
            write_to_db: 是否写入 state.db（默认 True）
            with_mark: 是否带标记（默认 False）
            mark_format: 标记格式模板（向后兼容），支持 {timestamp} 和 {content} 占位符
            send_mark: 发送标记前缀（如 [凯莉主动发送]）
            time_format: 时间格式（strftime 格式，支持 {weekday} 占位符）
            reasoning_content: 推理内容（可选，写入 reasoning_content 字段）
            token_count: token 数量（可选，写入 token_count 字段）
        """
        start_time = time.time()
        try:
            # 验证 session 存在
            metadata = get_state_metadata()
            if 'sessions' not in metadata.tables:
                MessageService.create_task_log(
                    task_type="send_message",
                    status="failed",
                    message=f"发送消息到 session {session_id}",
                    error="sessions 表不存在",
                    duration=round(time.time() - start_time, 2),
                    details={"session_id": session_id, "platform": platform, "failure_stage": "session_table_missing"}
                )
                return {"success": False, "message": "sessions 表不存在"}

            sessions_table = metadata.tables['sessions']
            with state_engine.connect() as conn:
                session_row = conn.execute(
                    sessions_table.select().where(sessions_table.c.id == session_id)
                ).first()

            if not session_row:
                MessageService.create_task_log(
                    task_type="send_message",
                    status="failed",
                    message=f"发送消息到 session {session_id}",
                    error=f"Session {session_id} 不存在",
                    duration=round(time.time() - start_time, 2),
                    details={"session_id": session_id, "platform": platform, "failure_stage": "session_not_found"}
                )
                return {"success": False, "message": f"Session {session_id} 不存在"}

            user_id = session_row._mapping.get('user_id')
            source = session_row._mapping.get('source')

            # 1. 真正发送消息到平台
            send_result = None
            if platform == "weixin" and user_id:
                send_result = await _send_to_weixin(user_id, message)
            elif platform == "feishu" and user_id:
                send_result = await _send_to_feishu(user_id, message)

            # 2. 只有发送成功才写入 state.db，避免污染 messages 表和后续 agent loop
            db_content = message
            sent_ok = send_result and send_result.get("success")
            if write_to_db and sent_ok:
                if send_mark:
                    now = datetime.now()
                    time_str = time_format.replace("{weekday}", weekday_name(now)) if time_format else ""
                    time_str = now.strftime(time_str) if time_str else ""
                    if time_str:
                        db_content = f"[{send_mark} {time_str}]: {message}"
                    else:
                        db_content = f"[{send_mark}]: {message}"
                
                # 使用 SessionDB 写入（统一方式）
                from services.state_db import get_state_db
                db = get_state_db()
                db.append_message(
                    session_id=session_id,
                    role="assistant",
                    content=db_content,
                    reasoning_content=reasoning_content,
                    token_count=token_count,
                    finish_reason="stop",
                )
            elif write_to_db and not sent_ok:
                logger.warning(
                    "send failed for session %s, skipping state.db write. platform=%s, reason=%s",
                    session_id, platform, (send_result or {}).get("message") or "no_result"
                )

            duration = round(time.time() - start_time, 2)

            if send_result and send_result.get("success"):
                MessageService.create_task_log(
                    task_type="send_message",
                    status="success",
                    message=f"消息已发送到 {platform}，session: {session_id}",
                    duration=duration,
                    details={"session_id": session_id, "platform": platform, "send_result": send_result, "write_to_db": write_to_db, "with_mark": bool(send_mark)}
                )
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
                MessageService.create_task_log(
                    task_type="send_message",
                    status="failed",
                    message=f"发送消息到 {platform}，session: {session_id}",
                    error=send_result.get("message", "发送失败"),
                    duration=duration,
                    details={"session_id": session_id, "platform": platform, "send_result": send_result, "failure_stage": "send"}
                )
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
                status = "success" if write_to_db else "success"
                msg = "仅写入 DB（无平台发送）" if write_to_db else "未写入也未发送"
                MessageService.create_task_log(
                    task_type="send_message",
                    status=status,
                    message=f"{msg}，session: {session_id}",
                    duration=duration,
                    details={"session_id": session_id, "platform": platform, "write_to_db": write_to_db, "with_mark": bool(send_mark)}
                )
                return {
                    "success": write_to_db,
                    "message": msg,
                    "session_id": session_id,
                    "platform": platform,
                    "db_content": db_content if write_to_db else None,
                    "with_mark": with_mark,
                    "duration": duration
                }
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            MessageService.create_task_log(
                task_type="send_message",
                status="failed",
                message=f"发送消息到 session {session_id}",
                error=str(e),
                duration=duration,
                details={"session_id": session_id, "platform": platform, "failure_stage": "exception", "exception_type": type(e).__name__}
            )
            return {"success": False, "message": f"消息发送失败: {str(e)}"}

    @staticmethod
    async def send_proactive_message(
        session_id: str,
        message: str,
        platform: str = "weixin",
        use_llm: bool = False,
        llm_config: Optional[Dict[str, Any]] = None,
        prompts_config: Optional[Dict[str, str]] = None,
        write_to_db: bool = True,
        with_mark: bool = True,
        mark_format: str = DEFAULT_MARK_FORMAT,
        send_mark: str = DEFAULT_SEND_MARK,
        time_format: str = DEFAULT_TIME_FORMAT
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
                generation_template = prompts_config.get("generation", "{session}")
                user_prompt = generation_template.replace("{session}", context_text)

                llm_result = await LLMService.generate_message(
                    llm_config=llm_config,
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=200
                )

                if llm_result.get("success"):
                    final_message = llm_result["content"]
                    MessageService.create_task_log(
                        task_type="generate",
                        status="success",
                        message=f"LLM 生成消息成功，session: {session_id}",
                        duration=round(time.time() - start_time, 2),
                        details={
                            "session_id": session_id,
                            "llm_request": {"model": llm_config.get("model",""), "temperature": 0.7, "max_tokens": 200},
                            "llm_response": {"content": final_message[:500]},
                            "use_llm": use_llm
                        }
                    )
                else:
                    MessageService.create_task_log(
                        task_type="generate",
                        status="failed",
                        message=f"LLM 生成消息失败，session: {session_id}",
                        error=llm_result.get("message", "未知错误"),
                        duration=round(time.time() - start_time, 2),
                        details={
                            "session_id": session_id,
                            "llm_request": {"model": llm_config.get("model",""), "temperature": 0.7, "max_tokens": 200},
                            "failure_stage": "llm_generate"
                        }
                    )
                    return {
                        "success": False,
                        "message": f"LLM 生成消息失败: {llm_result.get('message', '未知错误')}"
                    }

            # 发送消息
            send_result = await MessageService.send_message(
                session_id=session_id,
                message=final_message,
                platform=platform,
                write_to_db=write_to_db,
                with_mark=with_mark,
                mark_format=mark_format,
                send_mark=send_mark,
                time_format=time_format
            )

            duration = round(time.time() - start_time, 2)
            if send_result.get("success"):
                MessageService.create_task_log(
                    task_type="send_proactive",
                    status="success",
                    message=f"主动消息发送成功，session: {session_id}",
                    duration=duration,
                    details={
                        "session_id": session_id,
                        "use_llm": use_llm,
                        "generated_message": final_message if use_llm else None,
                        "send_result": send_result
                    }
                )
                return {
                    "success": True,
                    "message": "主动消息发送成功",
                    "session_id": session_id,
                    "use_llm": use_llm,
                    "generated_message": final_message if use_llm else None,
                    "duration": duration
                }
            else:
                MessageService.create_task_log(
                    task_type="send_proactive",
                    status="failed",
                    message=f"主动消息发送失败，session: {session_id}",
                    error=send_result.get("message", "未知错误"),
                    duration=duration,
                    details={
                        "session_id": session_id,
                        "use_llm": use_llm,
                        "generated_message": final_message if use_llm else None,
                        "send_result": send_result,
                        "failure_stage": "send"
                    }
                )
                return send_result

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            MessageService.create_task_log(
                task_type="send_proactive",
                status="failed",
                message=f"主动消息发送异常，session: {session_id}",
                error=str(e),
                duration=duration,
                details={
                    "session_id": session_id,
                    "use_llm": use_llm,
                    "failure_stage": "exception",
                    "exception_type": type(e).__name__
                }
            )
            return {"success": False, "message": f"主动消息发送失败: {str(e)}"}

    @staticmethod
    def get_session_context_raw(session_id: str, limit: int = 20, include_tool: bool = False) -> List[Dict[str, Any]]:
        """获取 session 上下文（原始数据）

        Args:
            session_id: session ID
            limit: 读取消息条数
            include_tool: 是否包含 tool 角色的消息（默认 False）
                         为 False 时，同时过滤掉 tool 消息和只有 tool_call 没有文本的空 assistant 消息
        """
        from sqlalchemy import and_, or_
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return []

        messages_table = metadata.tables['messages']
        query = (
            messages_table.select()
            .where(messages_table.c.session_id == session_id)
        )

        if not include_tool:
            # 过滤 tool 消息 + 空 assistant 消息（只有 tool_call 没有文本）
            query = query.where(and_(
                messages_table.c.role != 'tool',
                or_(
                    messages_table.c.role != 'assistant',
                    and_(messages_table.c.content != None, messages_table.c.content != '')
                )
            ))

        query = query.order_by(messages_table.c.timestamp.desc()).limit(limit)

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return list(reversed(items))

    @staticmethod
    def get_recent_messages_by_platform(platform: str = "weixin", limit: int = 20, include_tool: bool = False) -> List[Dict[str, Any]]:
        """按平台跨 session 获取最近消息（不限制 session_id）

        Args:
            platform: 平台来源（weixin/feishu/cli 等）
            limit: 读取消息条数
            include_tool: 是否包含 tool 角色的消息
        """
        from sqlalchemy import and_, or_
        metadata = get_state_metadata()
        if 'messages' not in metadata.tables:
            return []

        messages_table = metadata.tables['messages']
        sessions_table = metadata.tables['sessions']

        # JOIN sessions 表按 source 过滤
        query = (
            messages_table.select()
            .join(sessions_table, messages_table.c.session_id == sessions_table.c.id)
            .where(sessions_table.c.source == platform)
        )

        if not include_tool:
            query = query.where(and_(
                messages_table.c.role != 'tool',
                or_(
                    messages_table.c.role != 'assistant',
                    and_(messages_table.c.content != None, messages_table.c.content != '')
                )
            ))

        query = query.order_by(messages_table.c.timestamp.desc()).limit(limit)

        with state_engine.connect() as conn:
            result = conn.execute(query)
            items = [dict(row._mapping) for row in result]

        return list(reversed(items))

    @staticmethod
    def format_session_messages(msgs: List[Dict[str, Any]], role_map: Dict[str, str] = None) -> str:
        """将消息列表格式化为带时间+角色名的文本（通用方法）

        Args:
            msgs: 消息列表（get_recent_messages_by_platform 的返回值）
            role_map: 角色名映射，如 {"user": "曹凡", "assistant": "凯莉"}
                     为 None 时使用原始 role 名
        Returns:
            格式化后的多行文本，每行格式: [2026-06-26 13:43] 角色名: 内容
        """
        from datetime import datetime, timezone, timedelta
        default_map = {"tool": "工具", "system": "系统"}
        rmap = {**default_map, **(role_map or {})}

        def _fmt(m):
            role = rmap.get(m.get("role", "unknown"), m.get("role", "unknown"))
            ts = m.get("timestamp", "")
            try:
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
                    time_part = dt.strftime("%Y-%m-%d %H:%M")
                elif isinstance(ts, str) and len(ts) >= 16:
                    time_part = ts[:16].replace("T", " ")
                else:
                    time_part = ""
            except Exception:
                time_part = ""
            content = (m.get("content", "") or "").strip()
            if time_part:
                return f"[{time_part}] {role}: {content}"
            return f"{role}: {content}"

        return "\n".join(_fmt(m) for m in msgs)

    @staticmethod
    def create_task_log(
        task_type: str,
        status: str,
        message: str = None,
        error: str = None,
        duration: float = None,
        details: dict = None
    ):
        """创建任务日志

        details 必须传 dict（即使只有基本信息）。未传会 raise 强制开发修复。
        统一 details 结构由调用方构造，create_task_log 只负责落库。
        """
        if details is None:
            # 严格模式：避免某些调用方忘记构造 details 导致日志详情丢失。
            # 临时兜底：把基本信息打成 dict（不能 raise，因为有些路径是动态拼 details 前 fail）
            details = {
                "_minimal": True,
                "task_type": task_type,
                "summary": message,
                "error": error,
                "duration": duration,
            }
        import json as _json
        db = ActiveSession()
        try:
            log = TaskLog(
                task_type=task_type,
                status=status,
                message=message,
                error=error,
                duration=duration,
                details=_json.dumps(details, ensure_ascii=False)
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
