"""
Session Store Fallback — state.db 查询兜底

当 SessionStore.get_or_create_session() 在内存 _entries 中找不到 session 时，
自动查询 state.db 作为 fallback，将找到的 session 注入 _entries。

这解决了 API Server (POST /api/sessions) 创建的 session 不会同步到
Gateway SessionStore 内存的问题。

用法（在 run.py 中）：
    from gateway.extensions.session_fallback import install_fallback
    SessionStore = install_fallback(SessionStore)
    # 之后正常使用 SessionStore 即可
"""

import logging
from datetime import datetime
from typing import Optional, Type

logger = logging.getLogger(__name__)


def _make_fallback_mixin(Base: Type) -> Type:
    """创建一个包含 state.db fallback 行为的 mixin 类。

    通过覆盖 get_or_create_session() 实现：
    在调用 super() 之前，先检查 state.db，
    如果找到了就预注入 _entries，让 super() 自然命中。
    """

    class FallbackSessionStore(Base):
        """带 state.db fallback 的 SessionStore 子类。"""

        def get_or_create_session(self, source, force_new=False):
            """带 fallback 的 get_or_create_session。

            流程：
            1. 如果不是 force_new，先查 state.db 看是否有 API 创建的活跃 session
            2. 如果找到了且不在 _entries 中，注入 _entries
            3. 调用原始逻辑（会从 _entries 命中）
            """
            if not force_new and self._db is not None:
                try:
                    self._inject_from_db_if_needed(source)
                except Exception as e:
                    logger.debug("state.db fallback pre-check failed: %s", e)

            # 调用原始方法（所有原始逻辑不变）
            return super().get_or_create_session(source, force_new=force_new)

        def _inject_from_db_if_needed(self, source):
            """检查 state.db 是否有更新的活跃 session，必要时注入 _entries。

            解决的问题：hermes-active 等外部系统可能直接修改了 state.db
            （标记旧 session ended、创建新 session），但 Gateway 内存中的
            entry.updated_at 被消息刷新过，_is_session_expired 返回 False，
            导致 Gateway 继续使用旧 session。

            修复：即使 _is_session_expired 返回 False，也查 state.db 对比
            session_id。如果不一致，说明 state.db 被外部修改了，替换内存中的 entry。
            """
            from gateway.session import build_session_key

            session_key = build_session_key(
                source,
                group_sessions_per_user=getattr(
                    self.config, "group_sessions_per_user", True
                ),
                thread_sessions_per_user=getattr(
                    self.config, "thread_sessions_per_user", False
                ),
            )

            # 查 state.db 当前活跃 session
            platform_value = source.platform.value
            user_id = source.user_id
            if not user_id:
                return

            db_session = self._db.get_active_session_by_source(
                platform_value, user_id
            )
            if db_session is None:
                return

            db_session_id = db_session["id"]

            # 如果内存中已有 entry，检查 session_id 是否一致
            if session_key in self._entries:
                entry = self._entries[session_key]
                # session_id 一致 → 不需要替换，让 _should_reset 处理过期逻辑
                if entry.session_id == db_session_id:
                    return
                # session_id 不一致 → 需要替换（state.db 被外部修改）
                logger.info(
                    "[session_fallback] Memory entry outdated: "
                    "mem_session_id=%s db_session_id=%s expired=%s",
                    entry.session_id, db_session_id,
                    self._is_session_expired(entry),
                )

            # 注入新的 session entry
            from gateway.session import SessionEntry, _now

            db_started_at = db_session.get("started_at")
            now = _now()

            if isinstance(db_started_at, (int, float)):
                db_started_at = datetime.fromtimestamp(db_started_at)
            elif db_started_at is None:
                db_started_at = now

            entry = SessionEntry(
                session_key=session_key,
                session_id=db_session_id,
                created_at=db_started_at,
                updated_at=now,
                origin=source,
                display_name=getattr(source, "chat_name", None),
                platform=source.platform,
                chat_type=source.chat_type,
            )

            # 加锁注入（替换旧 entry）
            with self._lock:
                self._entries[session_key] = entry
                self._save()
                logger.info(
                    "[session_fallback] Injected session %s from state.db "
                    "for key=%s source=%s user_id=%s",
                    db_session_id, session_key, platform_value, user_id,
                )

    FallbackSessionStore.__name__ = Base.__name__ + "WithFallback"
    FallbackSessionStore.__qualname__ = Base.__qualname__ + "WithFallback"
    return FallbackSessionStore


def install_fallback(session_store_class: Type) -> Type:
    """安装 state.db fallback，返回增强后的 SessionStore 类。

    用法：
        from gateway.extensions.session_fallback import install_fallback
        from gateway.session import SessionStore
        SessionStore = install_fallback(SessionStore)
        store = SessionStore(sessions_dir, config)

    返回的类是原始类的子类，所有原始行为不变，
    只在 get_or_create_session() 中增加了 state.db fallback。
    """
    return _make_fallback_mixin(session_store_class)
