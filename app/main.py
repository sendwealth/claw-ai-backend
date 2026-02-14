"""
CLAW.AI - Backend Application
主应用程序入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import auth, users, conversations, knowledge, consulting, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    yield
    # 关闭时执行
    print(f"👋 {settings.APP_NAME} 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CLAW.AI - AI 智能咨询服务和智能客服机器人",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }
    )


# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["对话"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识库"])
app.include_router(consulting.router, prefix="/api/v1/consulting", tags=["咨询"])
app.include_router(ws.router, prefix="/api/v1", tags=["WebSocket"])


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
