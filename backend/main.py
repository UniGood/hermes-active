"""
Hermes Active - 主动会话系统后端
"""
import sys
import logging
from pathlib import Path

# 加载 hermes 环境变量
from dotenv import load_dotenv
load_dotenv(Path.home() / ".hermes" / ".env")

# 添加 hermes-agent 路径（用于 call_llm）
sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志输出到文件
LOG_DIR = Path(__file__).parent.parent / "data"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "backend.log"

# 设置日志：同时输出到文件和控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import SERVER_HOST, SERVER_PORT
from models.database import init_active_db, ActiveSession
from services.auth_service import AuthService
from services.scheduler_service import start_scheduler, stop_scheduler
from services.active_consciousness_service import start_heartbeat_scheduler, stop_heartbeat_scheduler, close_hindsight_client, schedule_log_cleanup, stop_log_cleanup_scheduler
from routers import (
    auth_router,
    sessions_router,
    messages_router,
    config_router,
    llm_router,
    cron_router,
    task_logs_router,
    stats_router,
    test_router,
    hindsight_router,
    system_logs_router,
    passive_consciousness,
    active_consciousness
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    print("正在初始化数据库...")
    init_active_db()

    # 初始化默认管理员
    db = ActiveSession()
    try:
        AuthService.init_default_admin(db)
    finally:
        db.close()

    # 启动定时任务调度器
    print("正在启动定时任务调度器...")
    start_scheduler()

    # 启动主动意识心跳调度器
    print("正在启动主动意识心跳调度器...")
    start_heartbeat_scheduler()

    # 启动日志清理调度器（每天凌晨 3 点清理 30 天前的日志）
    print("正在启动日志清理调度器...")
    schedule_log_cleanup()

    print("后端服务启动完成")
    yield

    # 关闭 Hindsight 客户端（释放 aiohttp 连接）
    await close_hindsight_client()

    # 停止日志清理调度器
    stop_log_cleanup_scheduler()

    # 停止主动意识心跳调度器
    stop_heartbeat_scheduler()

    # 停止调度器
    stop_scheduler()
    print("后端服务关闭")


app = FastAPI(
    title="Hermes Active",
    description="Hermes Agent 主动会话系统",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(messages_router)
app.include_router(config_router)
app.include_router(llm_router)
app.include_router(cron_router)
app.include_router(task_logs_router)
app.include_router(stats_router)
app.include_router(test_router)
app.include_router(hindsight_router)
app.include_router(system_logs_router)
app.include_router(passive_consciousness.router)
app.include_router(active_consciousness.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# 静态文件服务（前端 dist）
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    # API 路由不拦截，其余交给静态文件
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """SPA fallback：非 API 路径返回 index.html"""
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False
    )
