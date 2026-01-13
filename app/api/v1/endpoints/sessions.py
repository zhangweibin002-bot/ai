"""
会话管理接口

处理会话的增删改查
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import List, Optional

from app.core.logger import setup_logger
from app.db.session import get_db
from app.services.session_service import SessionService

logger = setup_logger(__name__)
router = APIRouter()


# =====================
# 请求/响应模型
# =====================
class SessionCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = None
    agent_id: str = "general"


class SessionUpdate(BaseModel):
    """更新会话请求"""
    title: str


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: str
    title: Optional[str]
    agent_id: str
    status: str
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ToolExecutionResponse(BaseModel):
    """工具执行记录响应"""
    id: int
    tool_name: str
    tool_call_id: Optional[str]
    input_params: Optional[dict]
    output_result: Optional[str]
    status: str
    execution_time: int
    created_at: str
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    created_at: str
    tool_executions: List[ToolExecutionResponse] = []  # 工具执行记录

    class Config:
        from_attributes = True


# =====================
# 接口定义
# =====================
@router.post("", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    db: DBSession = Depends(get_db)
):
    """
    创建新会话
    """
    try:
        service = SessionService(db)
        session = service.create_session(
            title=request.title,
            agent_id=request.agent_id,
        )
        
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            agent_id=session.agent_id,
            status=session.status,  # 直接使用字符串
            message_count=session.message_count or 0,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    agent_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: DBSession = Depends(get_db)
):
    """
    获取会话列表
    
    Args:
        agent_id: 智能体ID（可选，传入则只返回该智能体的会话）
        limit: 返回数量（默认50）
        offset: 偏移量（默认0）
    """
    try:
        service = SessionService(db)
        sessions = service.list_sessions(
            agent_id=agent_id,
            limit=limit,
            offset=offset
        )
        
        return [
            SessionResponse(
                id=s.id,
                user_id=s.user_id,
                title=s.title,
                agent_id=s.agent_id,
                status=s.status,  # 直接使用字符串
                message_count=s.message_count or 0,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """
    获取会话详情
    """
    service = SessionService(db)
    session = service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        agent_id=session.agent_id,
        status=session.status,  # 直接使用字符串
        message_count=session.message_count or 0,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    db: DBSession = Depends(get_db)
):
    """
    获取会话的消息历史
    """
    service = SessionService(db)
    
    # 检查会话是否存在
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    messages = service.get_messages(session_id, limit=limit)
    
    return [
        MessageResponse(
            id=m.id,
            role=m.role,  # 直接使用字符串
            content=m.content,
            created_at=m.created_at.isoformat(),
            tool_executions=[
                ToolExecutionResponse(
                    id=te.id,
                    tool_name=te.tool_name,
                    tool_call_id=te.tool_call_id,
                    input_params=te.input_params,
                    output_result=te.output_result,
                    status=te.status,
                    execution_time=te.execution_time,
                    created_at=te.created_at.isoformat(),
                )
                for te in (m.tool_executions if hasattr(m, 'tool_executions') else [])
            ]
        )
        for m in messages
    ]


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: SessionUpdate,
    db: DBSession = Depends(get_db)
):
    """
    更新会话标题
    """
    service = SessionService(db)
    session = service.update_session_title(session_id, request.title)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        agent_id=session.agent_id,
        status=session.status,  # 直接使用字符串
        message_count=session.message_count or 0,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """
    删除会话
    """
    service = SessionService(db)
    success = service.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"message": "会话已删除", "session_id": session_id}


@router.get("/stats/by-agent")
async def get_sessions_stats_by_agent(
    db: DBSession = Depends(get_db)
):
    """
    获取每个智能体的会话数量统计
    
    返回格式：
    {
        "general": 15,
        "coder": 8,
        "weather_expert": 3
    }
    """
    try:
        service = SessionService(db)
        stats = service.get_sessions_count_by_agent()
        return stats
    except Exception as e:
        logger.error(f"获取会话统计失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
