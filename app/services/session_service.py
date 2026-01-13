"""
会话管理服务

处理会话的创建、查询、删除等操作
"""

from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from app.core.logger import setup_logger
from app.models.chat_history import Session, ChatMessage

logger = setup_logger(__name__)


class SessionService:
    """会话管理服务"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    # =====================
    # 会话管理
    # =====================
    
    def create_session(
        self, 
        user_id: str = "guest",
        title: Optional[str] = None,
        agent_id: str = "base"
    ) -> Session:
        """创建新会话"""
        session_id = str(uuid4())[:8] + "_" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        session = Session(
            id=session_id,
            user_id=user_id,
            title=title or "新对话",
            agent_id=agent_id,
            status="active",  # 使用字符串
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"创建会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.db.query(Session).filter(
            Session.id == session_id,
            Session.status != "deleted"  # 使用字符串
        ).first()
    
    def get_or_create_session(
        self, 
        session_id: Optional[str],
        user_id: str = "guest"
    ) -> Session:
        """获取或创建会话"""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        # 创建新会话
        return self.create_session(user_id=user_id)
    
    def list_sessions(
        self, 
        user_id: str = "guest",
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            agent_id: 智能体ID（可选，传入则只返回该智能体的会话）
            limit: 返回数量
            offset: 偏移量
        """
        query = self.db.query(Session).filter(
            Session.user_id == user_id,
            Session.status == "active"  # 使用字符串
        )
        
        # 如果指定了 agent_id，则只查询该智能体的会话
        if agent_id:
            query = query.filter(Session.agent_id == agent_id)
            logger.info(f"查询智能体 '{agent_id}' 的会话列表")
        
        return query.order_by(desc(Session.updated_at)).offset(offset).limit(limit).all()
    
    def update_session_title(self, session_id: str, title: str) -> Optional[Session]:
        """更新会话标题"""
        session = self.get_session(session_id)
        if session:
            session.title = title
            self.db.commit()
            self.db.refresh(session)
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话（软删除）"""
        session = self.get_session(session_id)
        if session:
            session.status = "deleted"  # 使用字符串
            self.db.commit()
            logger.info(f"删除会话: {session_id}")
            return True
        return False
    
    # =====================
    # 消息管理
    # =====================
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[dict] = None,
        tool_name: Optional[str] = None,
    ) -> ChatMessage:
        """添加消息"""
        message = ChatMessage(
            session_id=session_id,
            role=role,  # 直接使用字符串
            content=content,
            tool_calls=tool_calls,
            tool_name=tool_name,
        )
        
        self.db.add(message)
        self.db.flush()  # 刷新以获取 ID，但不提交
        
        # 更新会话消息计数
        session = self.get_session(session_id)
        if session:
            session.message_count = (session.message_count or 0) + 1
        
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def update_message_content(
        self,
        message_id: int,
        content: str,
        tool_calls: Optional[dict] = None,
    ) -> Optional[ChatMessage]:
        """
        更新消息内容
        
        Args:
            message_id: 消息ID
            content: 新的内容
            tool_calls: 工具调用记录
            
        Returns:
            更新后的消息
        """
        message = self.db.query(ChatMessage).filter(
            ChatMessage.id == message_id
        ).first()
        
        if message:
            message.content = content
            if tool_calls is not None:
                message.tool_calls = tool_calls
            self.db.commit()
            self.db.refresh(message)
            logger.info(f"更新消息内容: message_id={message_id}")
        
        return message
    
    def get_messages(
        self, 
        session_id: str,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        获取会话的消息列表（包含工具执行记录）
        """
        from app.services.tool_execution_service import ToolExecutionService
        
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).limit(limit).all()
        
        # 为每条消息加载工具执行记录
        tool_service = ToolExecutionService(self.db)
        for msg in messages:
            if msg.role == "assistant":
                msg.tool_executions = tool_service.get_tool_executions_by_message(msg.id)
            else:
                msg.tool_executions = []
        
        return messages
    
    def get_recent_messages(
        self, 
        session_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        """获取最近的消息（用于上下文）"""
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(desc(ChatMessage.created_at)).limit(limit).all()
        
        return list(reversed(messages))  # 返回时间正序
    
    def generate_title(self, first_message: str) -> str:
        """根据第一条消息生成标题"""
        # 简单实现：截取前20个字符
        title = first_message[:20]
        if len(first_message) > 20:
            title += "..."
        return title
    
    def get_sessions_count_by_agent(self, user_id: str = "guest") -> dict:
        """
        获取每个智能体的会话数量统计
        
        Returns:
            {
                "agent_id_1": 5,
                "agent_id_2": 3,
                ...
            }
        """
        from sqlalchemy import func
        
        result = self.db.query(
            Session.agent_id,
            func.count(Session.id).label('count')
        ).filter(
            Session.user_id == user_id,
            Session.status == "active"
        ).group_by(Session.agent_id).all()
        
        # 转换为字典
        return {row.agent_id: row.count for row in result}