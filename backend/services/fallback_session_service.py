"""
Fallback Session 服务

直接查询 state.db 获取活跃 session，不依赖 Gateway 的 SessionStore。
解决了 hermes-active 自建 SessionStore 与 Gateway 内存不同步的问题。

用法：
    from services.fallback_session_service import FallbackSessionService
    session = FallbackSessionService.get_or_create_active_session("weixin", user_id)
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("hermes.session")


def _get_last_active(session_id: str) -> Optional[float]:
    """从 messages 表获取 session 的最后活动时间（timestamp）。"""
    try:
        from models.database import state_engine
        from sqlalchemy import text

        with state_engine.connect() as conn:
            result = conn.execute(
                text("SELECT MAX(timestamp) FROM messages WHERE session_id = :sid AND role = 'user'"),
                {"sid": session_id},
            )
            row = result.first()
            if row and row[0] is not None:
                return float(row[0])
    except Exception as e:
        logger.warning("Failed to get last active time: %s", e)
    return None


def _is_expired(last_active: float, mode: str, idle_minutes: int, at_hour: int) -> bool:
    """判断 session 是否过期（模拟 Gateway 的 _should_reset 逻辑）。"""
    from datetime import datetime, timedelta

    now = datetime.now()
    last_active_dt = datetime.fromtimestamp(last_active)

    # idle 检查
    if mode in {"idle", "both"}:
        if now > last_active_dt + timedelta(minutes=idle_minutes):
            return True

    # daily 检查
    if mode in {"daily", "both"}:
        today_reset = now.replace(hour=at_hour, minute=0, second=0, microsecond=0)
        if now.hour < at_hour:
            today_reset -= timedelta(days=1)
        if last_active_dt < today_reset:
            return True

    return False


class FallbackSessionService:
    """直接操作 state.db 的 Session 服务，绕过 SessionStore 同步问题。"""

    @staticmethod
    def get_or_create_active_session(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取或创建活跃 session。

        策略：
        1. 先查 state.db 看是否有活跃 session（ended_at IS NULL）
        2. 如果有且未过期 → 直接返回（不创建新的）
        3. 如果过期 → 通过 Gateway API 创建新 session（force_new=True）
        4. 如果没有 → 通过 Gateway API 创建（确保 Gateway 内存同步）

        不再自己创建 SessionStore 实例，彻底避免同步问题。
        """
        # Step 1: 查 state.db
        session = FallbackSessionService._find_active_session(platform, user_id)
        if session:
            # 检查是否过期
            if session.get("expired"):
                # Session 过期了，强制创建新的
                logger.info(
                    "Session expired for source=%s user_id=%s, creating new one",
                    platform, user_id,
                )
                return FallbackSessionService._create_via_session_store(platform, user_id, force_new=True)

            logger.info(
                "Found active session in state.db: %s (source=%s, user_id=%s)",
                session["id"], platform, user_id,
            )
            return {
                "id": session["id"],
                "source": platform,
                "user_id": user_id,
                "created_at": None,
                "was_auto_reset": False,
                "auto_reset_reason": None,
            }

        # Step 2: state.db 没有，通过 Gateway API 创建
        # Gateway 的 SessionStore fallback 会自动从 state.db 加载
        logger.info(
            "No active session in state.db for source=%s user_id=%s, "
            "creating via SessionStore",
            platform, user_id,
        )
        return FallbackSessionService._create_via_session_store(platform, user_id)

    @staticmethod
    def _find_active_session(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """从 state.db 查找活跃 session。"""
        try:
            from models.database import state_engine
            from sqlalchemy import text

            with state_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT id, source, user_id, started_at, title "
                        "FROM sessions "
                        "WHERE source = :source AND user_id = :user_id "
                        "AND ended_at IS NULL "
                        "ORDER BY started_at DESC LIMIT 1"
                    ),
                    {"source": platform, "user_id": user_id},
                )
                row = result.first()
                if row:
                    # 检查是否过期
                    session_id = row[0]
                    last_active = _get_last_active(session_id)
                    if last_active is None:
                        # 没有消息，用 started_at
                        last_active = float(row[3]) if row[3] else None

                    if last_active:
                        # 获取 reset policy 配置
                        import sys
                        sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
                        from gateway.config import GatewayConfig, Platform
                        import yaml

                        config_path = Path.home() / '.hermes' / 'config.yaml'
                        with open(config_path) as f:
                            yaml_cfg = yaml.safe_load(f) or {}
                        # session_reset → default_reset_policy 映射（gateway 启动流程会做，这里手动补）
                        if 'session_reset' in yaml_cfg and 'default_reset_policy' not in yaml_cfg:
                            yaml_cfg['default_reset_policy'] = yaml_cfg['session_reset']
                        config = GatewayConfig.from_dict(yaml_cfg)
                        policy = config.get_reset_policy(
                            platform=Platform(platform), session_type="dm"
                        )

                        if _is_expired(last_active, policy.mode, policy.idle_minutes, policy.at_hour):
                            # 过期，关闭旧 session
                            logger.info("Session %s expired, closing it", session_id)
                            with state_engine.connect() as conn:
                                conn.execute(
                                    text("UPDATE sessions SET ended_at = :now WHERE id = :sid"),
                                    {"now": time.time(), "sid": session_id},
                                )
                                conn.commit()
                            # 返回过期标志，让调用方知道需要 force_new
                            return {"expired": True}

                    return {
                        "id": session_id,
                        "source": row[1],
                        "user_id": row[2],
                        "started_at": row[3],
                        "title": row[4],
                        "expired": False,
                    }
        except Exception as e:
            logger.warning("Failed to query state.db for active session: %s", e)
        return None

    @staticmethod
    def _create_via_session_store(
        platform: str, user_id: str, force_new: bool = False
    ) -> Optional[Dict[str, Any]]:
        """通过 Gateway 的 SessionStore 创建 session。

        调用 SessionService.get_or_create_active_session()，
        使用 Gateway 原生的 SessionStore.get_or_create_session() 方法。
        自动处理 session 过期 + 创建，写入 state.db + sessions.json。

        Gateway 同步：session_fallback 扩展会从 state.db 加载注入内存。
        """
        try:
            from services.session_service import SessionService
            result = SessionService.get_or_create_active_session(platform, user_id, force_new=force_new)
            if result:
                logger.info(
                    "Created session via SessionStore: %s (source=%s, user_id=%s)",
                    result["id"], platform, user_id,
                )
            return result
        except Exception as e:
            logger.error("Failed to create session via SessionStore: %s", e)
            return None
