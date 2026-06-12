"""
Pydantic 模型定义
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ============ 认证相关 ============

class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    created_at: Optional[datetime] = None


# ============ Session 相关 ============

class SessionInfo(BaseModel):
    id: str
    source: Optional[str] = None
    user_id: Optional[str] = None
    model: Optional[str] = None
    title: Optional[str] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    message_count: Optional[int] = 0


class SessionListResponse(BaseModel):
    total: int
    items: List[SessionInfo]


class MessageInfo(BaseModel):
    id: Optional[int] = None
    session_id: str
    role: str
    content: Optional[str] = None
    timestamp: Optional[float] = None


class MessageListResponse(BaseModel):
    total: int
    items: List[MessageInfo]


# ============ 消息发送相关 ============

class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    is_test: bool = False


class SendProactiveRequest(BaseModel):
    session_id: str
    message: str
    use_llm: bool = False


# ============ LLM 相关 ============

class LLMConfig(BaseModel):
    mode: str = "hermes"
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LLMTestRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LLMGenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 200


# ============ 提示词相关 ============

class PromptsConfig(BaseModel):
    system: str
    generation: str


class DefaultPromptsConfig(BaseModel):
    system_prompt: str = ""
    user_prompt: str = ""
    append_soul_md: bool = True


class PreviewPromptRequest(BaseModel):
    system_prompt: str = ""
    user_prompt: str = ""
    append_soul_md: bool = True
    context_config: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


# ============ 定时任务相关 ============

class CronJobCreate(BaseModel):
    name: str
    schedule: str
    enabled: bool = True
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    append_soul_md: bool = True
    session_id: Optional[str] = None
    platform: str = "weixin"
    use_llm: bool = True
    write_to_db: bool = True
    with_mark: bool = True
    mark_format: str = "[凯莉主动发送] {timestamp}: {content}"


class CronJobUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    append_soul_md: Optional[bool] = None
    session_id: Optional[str] = None
    platform: Optional[str] = None
    use_llm: Optional[bool] = None
    write_to_db: Optional[bool] = None
    with_mark: Optional[bool] = None
    mark_format: Optional[str] = None


class CronJobInfo(BaseModel):
    id: str
    name: str
    schedule: str
    enabled: bool
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    append_soul_md: bool = True
    session_id: Optional[str] = None
    platform: str = "weixin"
    use_llm: bool = True
    write_to_db: bool = True
    with_mark: bool = True
    mark_format: str = "[凯莉主动发送] {timestamp}: {content}"
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None


class CronJobListResponse(BaseModel):
    items: List[CronJobInfo]


# ============ 任务日志相关 ============

class TaskLogInfo(BaseModel):
    id: int
    task_type: str
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class TaskLogListResponse(BaseModel):
    total: int
    items: List[TaskLogInfo]


# ============ 测试相关 ============

class TestFullRequest(BaseModel):
    platform: str = "weixin"
    use_llm: bool = True


# ============ 统计相关 ============

class StatsOverview(BaseModel):
    total_sessions: int = 0
    total_messages: int = 0
    today_messages: int = 0
    week_messages: int = 0
    month_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0


class TrendPoint(BaseModel):
    time: str
    count: int


class TrendResponse(BaseModel):
    points: List[TrendPoint]


class PlatformStats(BaseModel):
    platform: str
    count: int


class ProactiveStats(BaseModel):
    total: int = 0
    today: int = 0
    success_rate: float = 0.0


# ============ 通用响应 ============

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None
