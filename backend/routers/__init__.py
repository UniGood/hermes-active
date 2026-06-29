"""
路由包
"""
from .auth import router as auth_router
from .sessions import router as sessions_router
from .messages import router as messages_router
from .config import router as config_router
from .llm import router as llm_router
from .cron import router as cron_router
from .task_logs import router as task_logs_router
from .test import router as test_router
from .stats import router as stats_router
from .hindsight import router as hindsight_router
from .system_logs import router as system_logs_router
from . import passive_consciousness
from . import active_consciousness

__all__ = [
    "auth_router",
    "sessions_router",
    "messages_router",
    "config_router",
    "llm_router",
    "cron_router",
    "task_logs_router",
    "test_router",
    "stats_router",
    "hindsight_router",
    "system_logs_router",
    "passive_consciousness",
    "active_consciousness"
]
