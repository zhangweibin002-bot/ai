"""
智能体相关的 Pydantic Schema

用于 API 请求/响应的数据验证和序列化
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """创建智能体的请求模型"""
    id: str = Field(..., description="智能体ID（唯一标识）", min_length=1, max_length=50)
    name: str = Field(..., description="显示名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="简短描述", max_length=500)
    system_prompt: str = Field(..., description="系统提示词", min_length=1)
    model_name: Optional[str] = Field(None, description="模型名称")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    tools: Optional[List[str]] = Field(default=None, description="可用工具列表（null 或空则启用所有工具）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "math_helper",
                "name": "数学助手",
                "description": "专门处理数学问题的智能体",
                "system_prompt": "你是一个数学专家，擅长解决各类数学问题。遇到计算问题优先使用工具。",
                "model_name": None,
                "temperature": 0.7,
                "tools": None
            }
        }


class AgentUpdate(BaseModel):
    """更新智能体的请求模型"""
    name: Optional[str] = Field(None, description="显示名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="简短描述", max_length=500)
    system_prompt: Optional[str] = Field(None, description="系统提示词", min_length=1)
    model_name: Optional[str] = Field(None, description="模型名称")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="温度参数")
    tools: Optional[List[str]] = Field(None, description="可用工具列表（null 或空则启用所有工具）")
    is_active: Optional[bool] = Field(None, description="是否启用")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "数学助手 Pro",
                "temperature": 0.5,
                "tools": None
            }
        }


class AgentResponse(BaseModel):
    """智能体响应模型"""
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    model_name: Optional[str]
    temperature: float
    tools: List[str]
    is_system: bool
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True
