"""
知识库相关数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    """
    知识库表
    
    存储知识库的基本信息
    """
    __tablename__ = "knowledge_bases"
    
    id = Column(String(50), primary_key=True, comment="知识库ID")
    name = Column(String(200), nullable=False, comment="知识库名称")
    description = Column(Text, comment="知识库描述")
    icon = Column(String(50), default="📚", comment="图标")
    color = Column(String(20), comment="颜色标记")
    
    # 状态
    is_public = Column(Boolean, default=False, comment="是否公开")
    status = Column(String(20), default="active", comment="状态：active/archived/deleted")
    
    # 检索配置（JSON字段）
    retrieval_config = Column(JSON, comment="检索配置（向量权重、文本权重、Rerank等）")
    
    # 统计信息
    file_count = Column(Integer, default=0, comment="文档数量")
    total_chunks = Column(Integer, default=0, comment="总分块数")
    
    # 创建者
    created_by = Column(String(50), default="guest", comment="创建者")
    
    # 关联
    documents = relationship("KBDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    agent_bindings = relationship("AgentKnowledgeBase", back_populates="knowledge_base", cascade="all, delete-orphan")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "is_public": self.is_public,
            "status": self.status,
            "retrieval_config": self.retrieval_config,  # 检索配置
            "file_count": self.file_count,
            "total_chunks": self.total_chunks,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KBDocument(Base, TimestampMixin):
    """
    知识库文档表
    
    存储上传到知识库的文档信息及分块配置
    """
    __tablename__ = "kb_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 文件信息
    filename = Column(String(500), nullable=False, comment="文件名")
    file_type = Column(String(50), comment="文件类型：pdf/txt/md/docx等")
    file_path = Column(String(1000), comment="文件存储路径")
    file_size = Column(Integer, default=0, comment="文件大小（字节）")
    content_preview = Column(Text, comment="内容预览（前200字符）")
    
    # 上传状态
    upload_status = Column(String(20), default="pending", comment="上传状态：pending/uploaded/failed")
    
    # 分块策略配置
    chunk_strategy = Column(String(50), default="fixed", comment="分块策略：fixed/semantic/paragraph/code")
    chunk_size = Column(Integer, default=512, comment="分块大小（字符数）")
    chunk_overlap = Column(Integer, default=50, comment="重叠大小")
    chunk_count = Column(Integer, default=0, comment="实际分块数量")
    
    # 处理状态（扩展）
    process_status = Column(
        String(20), 
        default="pending", 
        comment="处理状态：pending/parsing/chunking/embedding/indexing/completed/failed"
    )
    process_error = Column(Text, comment="处理错误信息")
    
    # 向量化信息（新增）
    embedding_model = Column(String(100), comment="Embedding模型名称")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    
    # 处理时间（新增）
    process_start_time = Column(DateTime, comment="处理开始时间")
    process_end_time = Column(DateTime, comment="处理完成时间")
    process_duration = Column(Integer, comment="处理耗时（秒）")
    
    # ES索引信息（新增）
    es_index_name = Column(String(200), comment="Elasticsearch索引名称")
    
    # 关联
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "kb_id": self.kb_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "content_preview": self.content_preview,
            "upload_status": self.upload_status,
            "chunk_strategy": self.chunk_strategy,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunk_count": self.chunk_count,
            "process_status": self.process_status,
            "process_error": self.process_error,
            "embedding_model": self.embedding_model,
            "total_tokens": self.total_tokens,
            "process_start_time": self.process_start_time.isoformat() if self.process_start_time else None,
            "process_end_time": self.process_end_time.isoformat() if self.process_end_time else None,
            "process_duration": self.process_duration,
            "es_index_name": self.es_index_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentKnowledgeBase(Base):
    """
    智能体-知识库关联表
    
    多对多关系，支持优先级和配置
    """
    __tablename__ = "agent_knowledge_bases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), nullable=False, index=True, comment="智能体ID")
    kb_id = Column(String(50), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 配置
    priority = Column(Integer, default=1, comment="优先级（数字越小越优先）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 检索配置（可扩展）
    max_results = Column(Integer, default=5, comment="最多返回结果数")
    similarity_threshold = Column(Float, default=0.7, comment="相似度阈值")
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联
    knowledge_base = relationship("KnowledgeBase", back_populates="agent_bindings")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "kb_id": self.kb_id,
            "priority": self.priority,
            "is_active": self.is_active,
            "max_results": self.max_results,
            "similarity_threshold": self.similarity_threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
