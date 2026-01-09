"""
用户接口

用户相关操作（暂未实现）
"""

from fastapi import APIRouter

from app.core.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/me")
async def get_current_user():
    """
    获取当前用户信息
    
    TODO: 实现用户认证后完善
    """
    return {
        "id": "guest",
        "name": "访客",
        "message": "用户认证功能待实现",
    }

