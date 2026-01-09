"""
AI Agents 应用入口

FastAPI 应用初始化和配置
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import setup_logger
from app.api.v1.api import api_router
from app.db.session import init_db, SessionLocal

logger = setup_logger(__name__)


def init_tools():
    """初始化工具"""
    from app.tools.init_tools import init_tools as _init_tools
    _init_tools()


def init_agents():
    """初始化智能体（从数据库加载）"""
    from app.services.agent_service import AgentService
    from app.agents import agent_registry
    
    db = SessionLocal()
    try:
        service = AgentService(db)
        
        # 1. 初始化系统预设智能体（如果不存在）
        created = service.init_system_agents()
        if created > 0:
            logger.info(f"创建 {created} 个系统预设智能体")
        
        # 2. 从数据库加载所有智能体到 Registry
        loaded = service.load_all_agents()
        logger.info(f"✅ 已加载 {loaded} 个智能体: {agent_registry.list_ids()}")
        
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时初始化资源，关闭时清理资源
    """
    # ===== 启动时 =====
    logger.info("=" * 50)
    logger.info(f"🚀 {settings.APP_NAME} 启动中...")
    logger.info(f"📝 日志级别: {settings.LOG_LEVEL}")
    logger.info(f"🤖 模型: {settings.OPENAI_MODEL_NAMES}")
    
    # 初始化数据库表
    try:
        init_db()
        logger.info("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {str(e)}")
    
    # 初始化工具
    try:
        init_tools()
    except Exception as e:
        logger.error(f"❌ 工具初始化失败: {str(e)}")
    
    # 初始化智能体
    try:
        init_agents()
    except Exception as e:
        logger.error(f"❌ 智能体初始化失败: {str(e)}")
    
    logger.info("=" * 50)
    
    yield  # 应用运行中
    
    # ===== 关闭时 =====
    logger.info("=" * 50)
    logger.info(f"👋 {settings.APP_NAME} 已关闭")
    logger.info("=" * 50)


# =====================
# 创建 FastAPI 应用
# =====================
app = FastAPI(
    title=settings.APP_NAME,
    description="企业级 AI Agent 服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =====================
# 跨域配置
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================
# 注册路由
# =====================
app.include_router(api_router, prefix="/api/v1")


# =====================
# 健康检查
# =====================
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    from app.agents import agent_registry
    from app.tools import tool_registry
    
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "agents_count": agent_registry.count(),
        "tools_count": tool_registry.count(),
    }


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }


# =====================
# 本地运行
# =====================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=3001,
        reload=True,
    )
