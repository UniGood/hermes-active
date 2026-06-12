"""
系统日志路由 - 读取后端运行日志
"""
import os
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from models.active import User
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/system", tags=["系统日志"])

# 日志文件路径（uvicorn 输出的日志）
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "backend.log")


@router.get("/logs")
async def get_system_logs(
    lines: Optional[int] = Query(default=200, ge=10, le=2000, description="返回最近多少行"),
    current_user: User = Depends(get_current_user)
):
    """获取后端运行日志（最后 N 行）"""
    # 防御性处理：确保 lines 为有效整数
    if lines is None or lines < 10:
        lines = 200
    lines = min(lines, 2000)

    log_path = os.path.abspath(LOG_FILE_PATH)

    if not os.path.exists(log_path):
        return {"lines": [], "total": 0, "message": "日志文件不存在，后端可能使用标准输出模式"}

    try:
        # 读取最后 N 行（高效方式，不加载整个文件）
        all_lines = _tail_lines(log_path, lines)
        return {
            "lines": all_lines,
            "total": len(all_lines)
        }
    except Exception as e:
        return {"lines": [], "total": 0, "message": f"读取日志失败: {str(e)}"}


@router.get("/logs/stream")
async def stream_system_logs(
    current_user: User = Depends(get_current_user)
):
    """SSE 流式输出日志（用于实时查看）"""
    log_path = os.path.abspath(LOG_FILE_PATH)

    async def log_generator():
        if not os.path.exists(log_path):
            yield f"data: {{\"line\": \"日志文件不存在\"}}\n\n"
            return

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            # 跳到文件末尾
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {{\"line\": {line.strip()!r}}}\n\n"
                else:
                    # 发送心跳保持连接
                    yield ": heartbeat\n\n"
                    import asyncio
                    await asyncio.sleep(1)

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def _tail_lines(filepath: str, n: int) -> list:
    """高效读取文件最后 N 行"""
    with open(filepath, "rb") as f:
        # 从文件末尾开始读取
        f.seek(0, 2)
        file_size = f.tell()

        block_size = 8192
        blocks = []
        remaining = file_size
        lines_found = 0

        while remaining > 0 and lines_found < n:
            read_size = min(block_size, remaining)
            remaining -= read_size
            f.seek(remaining)
            block = f.read(read_size)
            blocks.append(block)
            lines_found += block.count(b"\n")

        # 合并所有块并取最后 n 行
        full_content = b"".join(reversed(blocks))
        all_lines = full_content.decode("utf-8", errors="replace").splitlines()

        return all_lines[-n:] if len(all_lines) > n else all_lines
