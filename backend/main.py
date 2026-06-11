"""
Hermes Active - 主动会话系统后端
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import SERVER_HOST, SERVER_PORT
from models.database import init_active_db, ActiveSession
from services.auth_service import AuthService
from routers import (
    auth_router,
    sessions_router,
    messages_router,
    config_router,
    llm_router,
    cron_router,
    task_logs_router,
    test_router,
    stats_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("正在初始化数据库...")
    init_active_db()

    # 初始化默认管理员
    db = ActiveSession()
    try:
        AuthService.init_default_admin(db)
    finally:
        db.close()

    print("后端服务启动完成")
    yield

    # 关闭时清理
    print("后端服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Hermes Active API",
    description="Hermes 主动会话系统 API",
    version="0.1.0",
    lifespan=lifespan
)

# 配置 CORS
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
app.include_router(test_router)
app.include_router(stats_router)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "hermes-active"
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Hermes Active API",
        "docs": "/docs",
        "version": "0.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True
    )
