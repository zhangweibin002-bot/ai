"""

负责协调文档处理的完整流程：
1. 解析文档 ✅
2. 文本分块 ✅
3. 保存分块到数据库 ✅
4. 向量化 ✅
5. 存储到 ES ✅
6. 知识库检索 ⏳
"""
from typing import List, Dict, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logger import setup_logger
from app.services.document_processor_service import document_processor
from app.services.chunking_service import ChunkingService, ChunkStrategy
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.embedding_service import embedding_service
from app.core.es_client import es_index_manager
from app.models.knowledge_base import KBDocument
from app.models.document_chunk import DocumentChunk, EmbeddingStatus

logger = setup_logger(__name__)


class DocumentProcessingService:
    """
    
    完整功能：
    - 文档解析（PDF, Word, TXT, MD, HTML）
    - 文本分块（4种策略）
    - 保存分块信息到数据库
    - 向量化（Jina Embeddings v3）
    - 存储到 Elasticsearch（kNN 索引）
    """
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.kb_service = KnowledgeBaseService(db)
        self.embedding_service = embedding_service
    
    def process_document(
        self,
        doc_id: int,
        chunk_strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> Dict:
        """
        处理单个文档（完整流程：解析 → 分块 → 向量化 → ES存储）
        
        Args:
            doc_id: 文档ID
            chunk_strategy: 分块策略
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            
        Returns:
            处理结果
        """
        logger.info(f"=" * 60)
        logger.info(f"📄 开始处理文档: doc_id={doc_id}")
        logger.info(f"=" * 60)
        
        # 获取文档记录
        doc = self.kb_service.get_document(doc_id)
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")
        
        start_time = datetime.now()
        
        try:
            # 更新状态为处理中
            doc.process_start_time = start_time
            self._update_document_status(doc, "parsing")
            
            # 阶段 1: 解析文档
            logger.info(f"📄 阶段 1/4: 解析文档 - {doc.filename}")
            text, metadata = self._parse_document(doc)
            
            # 阶段 2: 文本分块
            self._update_document_status(doc, "chunking")
            logger.info(f"✂️  阶段 2/4: 文本分块")
            chunks = self._chunk_text(
                text=text,
                doc_id=doc.id,
                kb_id=doc.kb_id,
                strategy=chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # 保存分块信息到数据库（不含向量）
            logger.info(f"💾 保存分块信息到数据库")
            db_chunks = self._save_chunks_to_db(chunks, doc)
            
            # 阶段 3: 向量化
            self._update_document_status(doc, "embedding")
            logger.info(f"🤖 阶段 3/4: 向量化 ({len(chunks)} 个分块)")
            embeddings = self._vectorize_chunks(chunks, db_chunks)
            
            # 阶段 4: 存储到 ES
            self._update_document_status(doc, "indexing")
            logger.info(f"📦 阶段 4/4: 存储到 Elasticsearch")
            self._store_to_es(doc.kb_id, db_chunks, embeddings)
            
            # 更新文档状态为完成
            end_time = datetime.now()
            doc.chunk_count = len(chunks)
            doc.process_end_time = end_time
            doc.process_duration = int((end_time - start_time).total_seconds())
            doc.embedding_model = "jina-embeddings-v3"
            self._update_document_status(doc, "completed")
            
            result = {
                "success": True,
                "doc_id": doc.id,
                "filename": doc.filename,
                "text_length": len(text),
                "chunks_count": len(chunks),
                "metadata": metadata,
                "process_duration": doc.process_duration,
                "message": f"✅ 文档处理完成：解析 → 分块({len(chunks)}) → 向量化 → ES存储"
            }
            
            logger.info(f"=" * 60)
            logger.info(f"✅ 文档处理成功: {doc.filename}")
            logger.info(f"   📝 文本长度: {len(text)} 字符")
            logger.info(f"   ✂️  分块数量: {len(chunks)} 个")
            logger.info(f"   🤖 向量维度: 1024")
            logger.info(f"   ⏱️  总耗时: {doc.process_duration}秒")
            logger.info(f"=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 文档处理失败: {str(e)}", exc_info=True)
            
            # 更新状态为失败
            doc.process_status = "failed"
            doc.process_error = str(e)
            doc.process_end_time = datetime.now()
            self.db.commit()
            
            raise
    
    def _parse_document(self, doc: KBDocument) -> tuple[str, Dict]:
        """
        解析文档
        
        Args:
            doc: 文档记录
            
        Returns:
            (文本内容, 元数据)
        """
        file_path = Path(doc.file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查文件类型是否支持
        if not document_processor.is_supported(doc.file_type):
            raise ValueError(
                f"不支持的文件类型: {doc.file_type}，"
                f"支持的类型: {document_processor.get_supported_types()}"
            )
        
        # 提取结构化信息
        result = document_processor.extract_with_structure(str(file_path))
        
        text = result["text"]
        metadata = result.get("metadata", {})
        
        logger.info(f"   ✅ 解析完成: {len(text)} 字符")
        
        return text, metadata
    
    def _chunk_text(
        self,
        text: str,
        doc_id: int,
        kb_id: str,
        strategy: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Dict]:
        """
        文本分块
        
        Args:
            text: 文本内容
            doc_id: 文档ID
            kb_id: 知识库ID
            strategy: 分块策略
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            
        Returns:
            分块列表
        """
        # 创建分块器
        chunker = ChunkingService(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # 转换策略
        strategy_map = {
            "fixed": ChunkStrategy.FIXED,
            "recursive": ChunkStrategy.RECURSIVE,
            "sentence": ChunkStrategy.SENTENCE,
            "semantic": ChunkStrategy.SEMANTIC
        }
        chunk_strategy = strategy_map.get(strategy, ChunkStrategy.RECURSIVE)
        
        # 分块
        chunks = chunker.chunk_text(
            text=text,
            strategy=chunk_strategy,
            metadata={"doc_id": doc_id, "kb_id": kb_id}
        )
        
        logger.info(f"   ✅ 分块完成: {len(chunks)} 个分块")
        
        return chunks
    
    def _save_chunks_to_db(
        self,
        chunks: List[Dict],
        doc: KBDocument
    ) -> List[DocumentChunk]:
        """
        保存分块到数据库（不含向量）
        
        Args:
            chunks: 分块列表
            doc: 文档记录
            
        Returns:
            List[DocumentChunk]: 保存的分块记录列表
        """
        try:
            db_chunks = []
            # 创建 DocumentChunk 记录
            for chunk in chunks:
                db_chunk = DocumentChunk(
                    doc_id=doc.id,
                    kb_id=doc.kb_id,
                    chunk_text=chunk["text"],
                    chunk_index=chunk["index"],
                    chunk_size=chunk["chunk_size"],
                    token_count=None,  # 可以估算
                    start_position=chunk["start_position"],
                    end_position=chunk["end_position"],
                    chunk_metadata=chunk.get("metadata", {}),
                    embedding_status=EmbeddingStatus.PENDING,  # 暂未向量化
                )
                self.db.add(db_chunk)
                db_chunks.append(db_chunk)
            
            self.db.commit()
            
            # 刷新所有 chunk 以获取数据库生成的 ID
            for db_chunk in db_chunks:
                self.db.refresh(db_chunk)
            
            logger.info(f"   ✅ 分块保存完成: {len(chunks)} 条记录")
            return db_chunks
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"   ❌ 分块保存失败: {str(e)}")
            raise
    
    def _vectorize_chunks(
        self,
        chunks: List[Dict],
        db_chunks: List[DocumentChunk]
    ) -> List[List[float]]:
        """
        向量化分块文本
        
        Args:
            chunks: 分块列表
            db_chunks: 数据库分块记录
            
        Returns:
            List[List[float]]: 向量列表
        """
        try:
            # 提取所有分块文本
            texts = [chunk["text"] for chunk in chunks]
            
            # 批量向量化（使用 retrieval.passage 任务）
            logger.info(f"   🤖 开始批量向量化...")
            embeddings = self.embedding_service.embed_batch(
                texts=texts,
                task="retrieval.passage",
                show_progress=True
            )
            
            # 更新数据库中的向量化状态
            for db_chunk in db_chunks:
                db_chunk.embedding_status = EmbeddingStatus.COMPLETED
            
            self.db.commit()
            logger.info(f"   ✅ 向量化完成: {len(embeddings)} 个向量")
            
            return embeddings
            
        except Exception as e:
            # 更新状态为失败
            for db_chunk in db_chunks:
                db_chunk.embedding_status = EmbeddingStatus.FAILED
            self.db.commit()
            
            logger.error(f"   ❌ 向量化失败: {str(e)}")
            raise
    
    def _store_to_es(
        self,
        kb_id: str,
        db_chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ):
        """
        存储向量到 Elasticsearch
        
        Args:
            kb_id: 知识库ID
            db_chunks: 数据库分块记录
            embeddings: 向量列表
        """
        try:
            # 确保索引存在
            es_index_manager.create_index(kb_id, vector_dim=1024)
            
            # 准备批量数据
            chunks_data = []
            for db_chunk, embedding in zip(db_chunks, embeddings):
                chunks_data.append({
                    "chunk_id": db_chunk.id,
                    "doc_id": db_chunk.doc_id,
                    "chunk_text": db_chunk.chunk_text,
                    "chunk_index": db_chunk.chunk_index,
                    "embedding": embedding,
                    "metadata": db_chunk.chunk_metadata or {}
                })
            
            # 批量索引
            result = es_index_manager.bulk_index_chunks(kb_id, chunks_data)
            
            if result["success"]:
                logger.info(f"   ✅ ES 存储完成: {result['success_count']}/{result['total']}")
            else:
                logger.warning(
                    f"   ⚠️  ES 存储部分失败: "
                    f"{result['success_count']}/{result['total']} 成功, "
                    f"{result['error_count']} 失败"
                )
            
        except Exception as e:
            logger.error(f"   ❌ ES 存储失败: {str(e)}")
            raise
    
    def _update_document_status(self, doc: KBDocument, status: str):
        """
        更新文档处理状态
        
        Args:
            doc: 文档记录
            status: 新状态（pending/processing/completed/failed）
        """
        doc.process_status = status
        self.db.commit()
        logger.info(f"   📝 状态更新: {status}")
