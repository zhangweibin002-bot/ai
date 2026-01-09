"""
智能体配置数据库模型

存储用户创建的智能体配置
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, JSON

from app.models.base import Base, TimestampMixin


class AgentConfig(Base, TimestampMixin):
    """
    智能体配置表
    
    存储智能体的配置信息
    """
    __tablename__ = "agent_configs"
    
    # 基本信息
    id = Column(String(50), primary_key=True, comment="智能体ID")
    name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(String(500), comment="简短描述")
    system_prompt = Column(Text, nullable=False, comment="系统提示词")
    
    # 模型配置
    model_name = Column(String(100), default=None, comment="模型名称")
    temperature = Column(Float, default=0.7, comment="温度参数")
    
    # 工具配置
    tools = Column(JSON, default=None, comment="可用工具列表 ['calculator', 'search']")
    
    # 分类
    is_system = Column(Boolean, default=False, comment="是否系统预设")
    is_active = Column(Boolean, default=True, index=True, comment="是否启用")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "tools": self.tools or [],  # 确保返回列表
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
