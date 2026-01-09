"""
工具执行记录模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON

from app.models.base import Base


class ToolExecution(Base):
    """
    工具执行记录表
    记录每次工具调用的详细信息
    """
    __tablename__ = "tool_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联信息（使用索引，不使用外键以避免字符集兼容性问题）
    session_id = Column(String(50), nullable=False, index=True, comment="会话ID")
    message_id = Column(Integer, index=True, comment="消息ID")
    
    # 工具信息
    tool_name = Column(String(100), nullable=False, index=True, comment="工具名称")
    tool_call_id = Column(String(100), index=True, comment="工具调用ID")
    
    # 输入输出
    input_params = Column(JSON, comment="输入参数")
    output_result = Column(Text, comment="输出结果")
    
    # 执行状态
    status = Column(String(20), default="success", comment="执行状态: success/failed/pending")
    error_message = Column(Text, comment="错误信息")
    
    # 性能指标
    execution_time = Column(Integer, default=0, comment="执行耗时(毫秒)")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
