"""
文档分块模型

存储文档的分块信息和向量化状态
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, Enum as SQLEnum, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class EmbeddingStatus(str, enum.Enum):
    """向量化状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentChunk(Base):
    """
    文档分块表
    
    存储文档分块后的文本块及其向量化状态
    """
    __tablename__ = "document_chunks"
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="分块ID")
    
    # 关联关系
    doc_id = Column(Integer, ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    kb_id = Column(String(50), nullable=False, index=True, comment="知识库ID（冗余）")
    
    # 分块内容
    chunk_text = Column(Text, nullable=False, comment="分块文本内容")
    chunk_index = Column(Integer, nullable=False, comment="分块序号（从0开始）")
    chunk_size = Column(Integer, comment="字符数")
    token_count = Column(Integer, comment="Token数量估算")
    
    # 向量信息
    vector_id = Column(String(100), comment="ES中的向量文档ID")
    embedding_status = Column(
        SQLEnum(EmbeddingStatus),
        default=EmbeddingStatus.PENDING,
        nullable=False,
        comment="向量化状态"
    )
    embedding_error = Column(Text, comment="向量化失败的错误信息")
    
    # 位置信息（用于溯源）
    start_page = Column(Integer, comment="PDF起始页码")
    end_page = Column(Integer, comment="PDF结束页码")
    start_position = Column(Integer, comment="在原文中的起始位置")
    end_position = Column(Integer, comment="在原文中的结束位置")
    
    # 元数据（注意：metadata 是 SQLAlchemy 保留字段，改为 chunk_metadata）
    chunk_metadata = Column(JSON, comment="额外元数据（如标题、章节等）")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联
    document = relationship("KBDocument", back_populates="chunks")
    
    # 索引
    __table_args__ = (
        Index('idx_doc_kb', 'doc_id', 'kb_id'),
        Index('idx_embedding_status', 'embedding_status'),
        Index('idx_vector_id', 'vector_id'),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "kb_id": self.kb_id,
            "chunk_text": self.chunk_text,
            "chunk_index": self.chunk_index,
            "chunk_size": self.chunk_size,
            "token_count": self.token_count,
            "vector_id": self.vector_id,
            "embedding_status": self.embedding_status.value if self.embedding_status else None,
            "embedding_error": self.embedding_error,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "chunk_metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, doc_id={self.doc_id}, chunk_index={self.chunk_index}, status={self.embedding_status})>"


class ProcessingTask(Base):
    """
    文档处理任务表
    
    跟踪异步处理任务的状态
    """
    __tablename__ = "processing_tasks"
    
    # 主键
    id = Column(String(50), primary_key=True, comment="任务ID（UUID或Celery task_id）")
    
    # 任务信息
    task_type = Column(
        SQLEnum('parse', 'chunk', 'embed', 'full_pipeline', name='task_type_enum'),
        nullable=False,
        comment="任务类型"
    )
    
    doc_id = Column(Integer, nullable=False, index=True, comment="关联的文档ID")
    kb_id = Column(String(50), nullable=False, index=True, comment="知识库ID")
    
    # 状态
    status = Column(
        SQLEnum('queued', 'running', 'completed', 'failed', 'cancelled', name='task_status_enum'),
        default='queued',
        nullable=False,
        comment="任务状态"
    )
    
    progress = Column(Integer, default=0, comment="进度百分比（0-100）")
    current_step = Column(String(100), comment="当前步骤描述")
    
    # 结果
    result = Column(JSON, comment="任务结果数据")
    error_message = Column(Text, comment="错误信息")
    
    # 时间戳
    started_at = Column(DateTime, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 索引
    __table_args__ = (
        Index('idx_doc_id', 'doc_id'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "doc_id": self.doc_id,
            "kb_id": self.kb_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "result": self.result,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<ProcessingTask(id={self.id}, type={self.task_type}, status={self.status})>"
