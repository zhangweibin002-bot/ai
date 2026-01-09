"""
聊天相关数据库模型

包含会话和消息表
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Enum, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class SessionStatus(str, enum.Enum):
    """会话状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(str, enum.Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Session(Base, TimestampMixin):
    """
    会话表
    
    存储用户的对话会话
    """
    __tablename__ = "sessions"
    
    id = Column(String(50), primary_key=True, comment="会话ID")
    user_id = Column(String(50), default="guest", nullable=False, index=True, comment="用户ID")
    title = Column(String(200), comment="会话标题")
    agent_id = Column(String(50), default="general", comment="使用的智能体")
    
    # 状态 - 使用字符串值
    status = Column(
        String(20),
        default="active",
        comment="状态"
    )
    
    # 统计
    message_count = Column(Integer, default=0, comment="消息数量")
    
    # 关联消息
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "agent_id": self.agent_id,
            "status": self.status,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(Base):
    """
    聊天消息表
    
    存储对话中的每条消息
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 消息内容 - 使用字符串值
    role = Column(String(20), nullable=False, comment="角色")
    content = Column(Text, nullable=False, comment="消息内容")
    
    # 工具调用相关（预留）
    tool_calls = Column(JSON, comment="工具调用请求")
    tool_call_id = Column(String(100), comment="工具调用ID")
    tool_name = Column(String(100), comment="工具名称")
    
    # 统计
    tokens_used = Column(Integer, default=0, comment="消耗的token数")
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关联会话
    session = relationship("Session", back_populates="messages")
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_name": self.tool_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
