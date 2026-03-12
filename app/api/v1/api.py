"""
API 路由汇总

汇总所有 v1 版本的 API 路由
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, agents, users, sessions, tools, knowledge_bases

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(
    chat.router, 
    prefix="/chat", 
    tags=["聊天"]
)

api_router.include_router(
    sessions.router,
    prefix="/sessions",
    tags=["会话管理"]
)

api_router.include_router(
    agents.router, 
    prefix="/agents", 
    tags=["智能体"]
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["用户"]
)

api_router.include_router(
    tools.router,
    prefix="/tools",
    tags=["工具"]
)

api_router.include_router(
    knowledge_bases.router,
    prefix="/knowledge-bases",
    tags=["知识库"]
)
