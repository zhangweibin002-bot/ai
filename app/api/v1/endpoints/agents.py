"""
智能体接口

管理和查询智能体（支持 CRUD）
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional
from pydantic import BaseModel

from app.core.logger import setup_logger
from app.db.session import get_db
from app.agents import agent_registry
from app.services.agent_service import AgentService

logger = setup_logger(__name__)
router = APIRouter()


# =====================
# 请求/响应模型
# =====================
class AgentCreate(BaseModel):
    """创建智能体请求"""
    name: str
    description: Optional[str] = None
    system_prompt: str
    temperature: Optional[float] = 0.7


class AgentUpdate(BaseModel):
    """更新智能体请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None


class AgentResponse(BaseModel):
    """智能体响应"""
    id: str
    name: str
    description: Optional[str]
    has_tools: bool
    tool_count: int
    is_system: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AgentDetailResponse(AgentResponse):
    """智能体详情响应（包含 system_prompt）"""
    system_prompt: str
    temperature: float


# =====================
# 接口定义
# =====================
@router.get("", response_model=List[AgentResponse])
async def list_agents(db: DBSession = Depends(get_db)):
    """
    获取所有可用的智能体列表
    """
    service = AgentService(db)
    configs = service.list_agents()
    
    return [
        AgentResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            has_tools=False,  # 暂时不支持工具
            tool_count=0,
            is_system=c.is_system,
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in configs
    ]


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(agent_id: str, db: DBSession = Depends(get_db)):
    """
    获取指定智能体的详情
    """
    service = AgentService(db)
    config = service.get_agent(agent_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"智能体 '{agent_id}' 不存在")
    
    return AgentDetailResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        system_prompt=config.system_prompt,
        temperature=config.temperature or 0.7,
        has_tools=False,
        tool_count=0,
        is_system=config.is_system,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@router.post("", response_model=AgentResponse)
async def create_agent(
    request: AgentCreate,
    db: DBSession = Depends(get_db)
):
    """
    创建新智能体
    
    - **name**: 智能体名称
    - **description**: 简短描述（可选）
    - **system_prompt**: 系统提示词
    - **temperature**: 温度参数（可选，默认 0.7）
    """
    try:
        service = AgentService(db)
        config = service.create_agent(
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            temperature=request.temperature or 0.7,
        )
        
        return AgentResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            has_tools=False,
            tool_count=0,
            is_system=config.is_system,
            created_at=config.created_at.isoformat() if config.created_at else None,
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
        )
        
    except Exception as e:
        logger.error(f"创建智能体失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: AgentUpdate,
    db: DBSession = Depends(get_db)
):
    """
    更新智能体
    
    注意：系统预设智能体不能修改
    """
    try:
        service = AgentService(db)
        config = service.update_agent(
            agent_id=agent_id,
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
        )
        
        if not config:
            raise HTTPException(status_code=404, detail=f"智能体 '{agent_id}' 不存在")
        
        return AgentResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            has_tools=False,
            tool_count=0,
            is_system=config.is_system,
            created_at=config.created_at.isoformat() if config.created_at else None,
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"更新智能体失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: DBSession = Depends(get_db)):
    """
    删除智能体
    
    注意：系统预设智能体不能删除
    """
    try:
        service = AgentService(db)
        success = service.delete_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"智能体 '{agent_id}' 不存在")
        
        return {"message": "智能体已删除", "agent_id": agent_id}
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"删除智能体失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
