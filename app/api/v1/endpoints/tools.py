"""
工具管理接口

提供工具的查询和管理功能
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.core.logger import setup_logger
from app.tools import tool_registry

logger = setup_logger(__name__)
router = APIRouter()


# =====================
# 响应模型
# =====================
from pydantic import BaseModel


class ToolResponse(BaseModel):
    """工具信息"""
    name: str
    display_name: str
    description: str
    category: str
    version: str
    author: Optional[str]
    is_active: bool
    requires_approval: bool
    input_schema: dict


class ToolSummary(BaseModel):
    """工具摘要"""
    total: int
    active: int
    inactive: int
    categories: List[str]
    tools: List[dict]


# =====================
# 工具查询接口
# =====================
@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    category: Optional[str] = None,
    active_only: bool = True
):
    """
    获取所有工具列表
    
    - **category**: 可选，按分类筛选
    - **active_only**: 是否只返回启用的工具（默认 true）
    """
    try:
        tools = tool_registry.list_all(category=category, active_only=active_only)
        return [tool.to_dict() for tool in tools]
    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=ToolSummary)
async def get_tools_summary():
    """
    获取工具注册中心摘要
    
    返回统计信息：总数、启用数、分类等
    """
    try:
        return tool_registry.get_summary()
    except Exception as e:
        logger.error(f"获取工具摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories():
    """获取所有工具分类"""
    try:
        return {"categories": tool_registry.get_categories()}
    except Exception as e:
        logger.error(f"获取工具分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool(tool_name: str):
    """
    获取指定工具的详细信息
    
    - **tool_name**: 工具名称
    """
    try:
        tool = tool_registry.get(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"工具不存在: {tool_name}")
        
        return tool.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工具信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================
# 工具测试接口
# =====================
class ToolTestRequest(BaseModel):
    """工具测试请求"""
    tool_name: str
    parameters: dict


@router.post("/test")
async def test_tool(request: ToolTestRequest):
    """
    测试工具执行
    
    - **tool_name**: 工具名称
    - **parameters**: 工具参数（JSON 对象）
    """
    try:
        tool = tool_registry.get(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"工具不存在: {request.tool_name}")
        
        # 执行工具
        result = await tool.execute(**request.parameters)
        
        return {
            "tool_name": request.tool_name,
            "success": result["success"],
            "result": result["result"],
            "error": result.get("error"),
            "metadata": result.get("metadata")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"工具测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def tools_health():
    """工具服务健康检查"""
    return {
        "status": "ok",
        "service": "tools",
        "tool_count": tool_registry.count()
    }
