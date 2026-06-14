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


class FallbackSessionService:
    """直接操作 state.db 的 Session 服务，绕过 SessionStore 同步问题。"""

    @staticmethod
    def get_or_create_active_session(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取或创建活跃 session。

        策略：
        1. 先查 state.db 看是否有活跃 session（ended_at IS NULL）
        2. 如果有 → 直接返回（不创建新的）
        3. 如果没有 → 通过 Gateway API 创建（确保 Gateway 内存同步）

        不再自己创建 SessionStore 实例，彻底避免同步问题。
        """
        # Step 1: 查 state.db
        session = FallbackSessionService._find_active_session(platform, user_id)
        if session:
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
            "creating via Gateway API",
            platform, user_id,
        )
        return FallbackSessionService._create_via_gateway_api(platform, user_id)

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
                    return {
                        "id": row[0],
                        "source": row[1],
                        "user_id": row[2],
                        "started_at": row[3],
                        "title": row[4],
                    }
        except Exception as e:
            logger.warning("Failed to query state.db for active session: %s", e)
        return None

    @staticmethod
    def _create_via_gateway_api(
        platform: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """通过 Gateway API 创建 session。

        Gateway 的 SessionStore (已安装 fallback) 会：
        1. 在 _entries 中查找 → 没有
        2. fallback 查 state.db → 没有
        3. 创建新 session → 写入 state.db + _entries + sessions.json
        """
        import os
        import json as _json
        import urllib.request
        import urllib.error

        gateway_url = os.getenv("GATEWAY_API_URL", "http://127.0.0.1:8642")
        api_key = os.getenv("API_SERVER_KEY", "")

        try:
            payload = _json.dumps({
                "source": platform,
                "user_id": user_id,
            }).encode("utf-8")

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            req = urllib.request.Request(
                f"{gateway_url}/api/sessions",
                data=payload,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
                session = data.get("session", data)
                return {
                    "id": session.get("id") or session.get("session_id"),
                    "source": platform,
                    "user_id": user_id,
                    "created_at": None,
                    "was_auto_reset": False,
                    "auto_reset_reason": None,
                }
        except urllib.error.HTTPError as e:
            if e.code == 409:
                # Session 已存在 — 从 state.db 获取
                logger.info("Session already exists via API (409), querying state.db")
                return FallbackSessionService._find_active_session(platform, user_id)
            logger.error("Gateway session API error: %s", e)
            return None
        except Exception as e:
            logger.error("Gateway session API failed: %s", e)
            return None
