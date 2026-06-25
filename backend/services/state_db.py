"""
State DB 服务 - 统一的 state.db 访问入口

提供 SessionDB 单例，所有写入 state.db 的地方都通过这个模块。
"""
from hermes_state import SessionDB
from pathlib import Path

_state_db = None


def get_state_db() -> SessionDB:
    """获取 state.db 单例"""
    global _state_db
    if _state_db is None:
        _state_db = SessionDB(db_path=Path.home() / ".hermes" / "state.db")
    return _state_db
