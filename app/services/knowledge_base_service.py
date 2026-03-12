"""
知识库管理服务
"""
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from app.core.logger import setup_logger
from app.models.knowledge_base import KnowledgeBase, KBDocument, AgentKnowledgeBase

logger = setup_logger(__name__)


class KnowledgeBaseService:
    """知识库管理服务"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    # =====================
    # 知识库管理
    # =====================
    
    def create_knowledge_base(
        self,
        name: str,
        description: Optional[str] = None,
        icon: str = "📚",
        color: Optional[str] = None,
        created_by: str = "guest"
    ) -> KnowledgeBase:
        """
        创建知识库
        
        Args:
            name: 知识库名称
            description: 描述
            icon: 图标
            color: 颜色标记
            created_by: 创建者
            
        Returns:
            创建的知识库对象
        """
        kb_id = "kb_" + str(uuid4())[:8]
        
        kb = KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            created_by=created_by,
            status="active"
        )
        
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        
        logger.info(f"创建知识库: {kb_id} - {name}")
        return kb
    
    def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """
        获取知识库
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            知识库对象或None
        """
        return self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.status != "deleted"
        ).first()
    
    def list_knowledge_bases(
        self,
        created_by: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeBase]:
        """
        获取知识库列表
        
        Args:
            created_by: 创建者（可选）
            status: 状态过滤
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            知识库列表
        """
        query = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.status == status
        )
        
        if created_by:
            query = query.filter(KnowledgeBase.created_by == created_by)
        
        return query.order_by(desc(KnowledgeBase.updated_at)).offset(offset).limit(limit).all()
    
    def update_knowledge_base(
        self,
        kb_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None
    ) -> Optional[KnowledgeBase]:
        """
        更新知识库
        
        Args:
            kb_id: 知识库ID
            name: 新名称（可选）
            description: 新描述（可选）
            icon: 新图标（可选）
            color: 新颜色（可选）
            
        Returns:
            更新后的知识库对象
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            return None
        
        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        if icon is not None:
            kb.icon = icon
        if color is not None:
            kb.color = color
        
        self.db.commit()
        self.db.refresh(kb)
        
        logger.info(f"更新知识库: {kb_id}")
        return kb
    
    def delete_knowledge_base(self, kb_id: str, hard_delete: bool = False) -> bool:
        """
        删除知识库
        
        Args:
            kb_id: 知识库ID
            hard_delete: 是否硬删除（默认软删除）
            
        Returns:
            是否成功
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            return False
        
        if hard_delete:
            # 硬删除（级联删除文档和绑定关系）
            self.db.delete(kb)
        else:
            # 软删除
            kb.status = "deleted"
        
        self.db.commit()
        logger.info(f"删除知识库: {kb_id} (hard={hard_delete})")
        return True
    
    # =====================
    # 文档管理
    # =====================
    
    def get_documents(self, kb_id: str) -> List[KBDocument]:
        """
        获取知识库的文档列表
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            文档列表
        """
        return self.db.query(KBDocument).filter(
            KBDocument.kb_id == kb_id
        ).order_by(KBDocument.created_at).all()
    
    def get_document(self, doc_id: int) -> Optional[KBDocument]:
        """获取单个文档"""
        return self.db.query(KBDocument).filter(
            KBDocument.id == doc_id
        ).first()
    
    def create_document(
        self,
        kb_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: Optional[str] = None,
        content_preview: Optional[str] = None,
        chunk_strategy: str = "fixed",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> KBDocument:
        """
        创建文档记录
        
        Args:
            kb_id: 知识库ID
            filename: 文件名
            file_path: 文件存储路径
            file_size: 文件大小（字节）
            file_type: 文件类型
            content_preview: 内容预览
            chunk_strategy: 分块策略
            chunk_size: 分块大小
            chunk_overlap: 重叠大小
            
        Returns:
            创建的文档对象
        """
        doc = KBDocument(
            kb_id=kb_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            content_preview=content_preview,
            upload_status="uploaded",
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            process_status="pending"
        )
        
        self.db.add(doc)
        
        # 更新知识库的文档计数
        kb = self.get_knowledge_base(kb_id)
        if kb:
            kb.file_count = (kb.file_count or 0) + 1
        
        self.db.commit()
        self.db.refresh(doc)
        
        logger.info(f"创建文档记录: {doc.id} - {filename}")
        return doc
    
    def delete_document(self, doc_id: int) -> bool:
        """
        删除文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            是否成功
        """
        doc = self.get_document(doc_id)
        if not doc:
            return False
        
        kb_id = doc.kb_id
        
        # 删除文档
        self.db.delete(doc)
        
        # 更新知识库统计
        kb = self.get_knowledge_base(kb_id)
        if kb:
            kb.file_count = max(0, (kb.file_count or 0) - 1)
            kb.total_chunks = max(0, (kb.total_chunks or 0) - (doc.chunk_count or 0))
        
        self.db.commit()
        logger.info(f"删除文档: {doc_id}")
        return True
    
    # =====================
    # 智能体知识库绑定
    # =====================
    
    def bind_knowledge_base_to_agent(
        self,
        agent_id: str,
        kb_id: str,
        priority: int = 1,
        is_active: bool = True,
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> AgentKnowledgeBase:
        """
        绑定知识库到智能体
        
        Args:
            agent_id: 智能体ID
            kb_id: 知识库ID
            priority: 优先级
            is_active: 是否启用
            max_results: 最多返回结果数
            similarity_threshold: 相似度阈值
            
        Returns:
            绑定关系对象
        """
        # 检查是否已存在
        existing = self.db.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.agent_id == agent_id,
            AgentKnowledgeBase.kb_id == kb_id
        ).first()
        
        if existing:
            # 更新现有绑定
            existing.priority = priority
            existing.is_active = is_active
            existing.max_results = max_results
            existing.similarity_threshold = similarity_threshold
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"更新绑定: agent={agent_id}, kb={kb_id}")
            return existing
        
        # 创建新绑定
        binding = AgentKnowledgeBase(
            agent_id=agent_id,
            kb_id=kb_id,
            priority=priority,
            is_active=is_active,
            max_results=max_results,
            similarity_threshold=similarity_threshold
        )
        
        self.db.add(binding)
        self.db.commit()
        self.db.refresh(binding)
        
        logger.info(f"绑定知识库到智能体: agent={agent_id}, kb={kb_id}")
        return binding
    
    def get_agent_knowledge_bases(self, agent_id: str, active_only: bool = True) -> List[dict]:
        """
        获取智能体绑定的知识库列表
        
        Args:
            agent_id: 智能体ID
            active_only: 是否只返回启用的
            
        Returns:
            知识库列表（包含绑定配置）
        """
        query = self.db.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.agent_id == agent_id
        )
        
        if active_only:
            query = query.filter(AgentKnowledgeBase.is_active == True)
        
        bindings = query.order_by(AgentKnowledgeBase.priority).all()
        
        # 加载知识库详情
        result = []
        for binding in bindings:
            kb = self.get_knowledge_base(binding.kb_id)
            if kb:
                result.append({
                    "binding": binding.to_dict(),
                    "knowledge_base": kb.to_dict()
                })
        
        return result
    
    def unbind_knowledge_base_from_agent(self, agent_id: str, kb_id: str) -> bool:
        """
        解绑知识库
        
        Args:
            agent_id: 智能体ID
            kb_id: 知识库ID
            
        Returns:
            是否成功
        """
        binding = self.db.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.agent_id == agent_id,
            AgentKnowledgeBase.kb_id == kb_id
        ).first()
        
        if not binding:
            return False
        
        self.db.delete(binding)
        self.db.commit()
        
        logger.info(f"解绑知识库: agent={agent_id}, kb={kb_id}")
        return True
    
    def update_binding_config(
        self,
        agent_id: str,
        kb_id: str,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
        max_results: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> Optional[AgentKnowledgeBase]:
        """
        更新绑定配置
        
        Args:
            agent_id: 智能体ID
            kb_id: 知识库ID
            priority: 优先级（可选）
            is_active: 是否启用（可选）
            max_results: 最多结果数（可选）
            similarity_threshold: 相似度阈值（可选）
            
        Returns:
            更新后的绑定对象
        """
        binding = self.db.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.agent_id == agent_id,
            AgentKnowledgeBase.kb_id == kb_id
        ).first()
        
        if not binding:
            return None
        
        if priority is not None:
            binding.priority = priority
        if is_active is not None:
            binding.is_active = is_active
        if max_results is not None:
            binding.max_results = max_results
        if similarity_threshold is not None:
            binding.similarity_threshold = similarity_threshold
        
        self.db.commit()
        self.db.refresh(binding)
        
        logger.info(f"更新绑定配置: agent={agent_id}, kb={kb_id}")
        return binding
    
    def get_document_chunks(self, doc_id: int, limit: int = None, offset: int = 0) -> List:
        """
        获取文档的分块列表
        
        Args:
            doc_id: 文档ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            分块列表
        """
        from app.models.document_chunk import DocumentChunk
        
        query = self.db.query(DocumentChunk).filter(
            DocumentChunk.doc_id == doc_id
        ).order_by(DocumentChunk.chunk_index)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        chunks = query.all()
        logger.info(f"获取文档分块: doc_id={doc_id}, 数量={len(chunks)}")
        
        return chunks
    
    def get_chunks_count(self, doc_id: int) -> int:
        """
        获取文档的分块总数
        
        Args:
            doc_id: 文档ID
            
        Returns:
            分块总数
        """
        from app.models.document_chunk import DocumentChunk
        
        count = self.db.query(DocumentChunk).filter(
            DocumentChunk.doc_id == doc_id
        ).count()
        
        return count
