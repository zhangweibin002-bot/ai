"""
知识库管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from pathlib import Path

from app.core.logger import setup_logger
from app.db.session import get_db
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.kb_retrieval_service import KBRetrievalService, HybridMode
from app.schemas.retrieval import SearchRequest, SearchResponse, SearchResultItem, KBConfig
from app.models.knowledge_base import KBDocument

logger = setup_logger(__name__)
router = APIRouter()


# =====================
# 请求/响应模型
# =====================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str
    description: Optional[str] = None
    icon: str = "📚"
    color: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class RetrievalConfigUpdate(BaseModel):
    """更新检索配置请求"""
    vector_boost: float = 0.7
    text_boost: float = 0.3
    top_k: int = 5
    min_score: float = 0.7
    use_rerank: bool = False
    rerank_top_k: Optional[int] = 10


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    name: str
    description: Optional[str]
    icon: str
    color: Optional[str]
    is_public: bool
    status: str
    file_count: int
    total_chunks: int
    created_by: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """文档响应"""
    id: int
    kb_id: str
    filename: str
    file_type: Optional[str]
    file_size: int
    content_preview: Optional[str]
    upload_status: str
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    chunk_count: int
    process_status: str
    process_error: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AgentKBBindRequest(BaseModel):
    """智能体绑定知识库请求"""
    kb_id: str
    priority: int = 1
    is_active: bool = True
    max_results: int = 5
    similarity_threshold: float = 0.7


class AgentKBBindUpdate(BaseModel):
    """更新绑定配置请求"""
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    max_results: Optional[int] = None
    similarity_threshold: Optional[float] = None


# =====================
# 知识库接口
# =====================

@router.post("", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    db: DBSession = Depends(get_db)
):
    """
    创建知识库
    """
    try:
        service = KnowledgeBaseService(db)
        kb = service.create_knowledge_base(
            name=request.name,
            description=request.description,
            icon=request.icon,
            color=request.color
        )
        return kb.to_dict()
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    limit: int = 50,
    offset: int = 0,
    db: DBSession = Depends(get_db)
):
    """
    获取知识库列表
    """
    try:
        service = KnowledgeBaseService(db)
        kbs = service.list_knowledge_bases(limit=limit, offset=offset)
        return [kb.to_dict() for kb in kbs]
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    db: DBSession = Depends(get_db)
):
    """
    获取知识库详情
    """
    service = KnowledgeBaseService(db)
    kb = service.get_knowledge_base(kb_id)
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    return kb.to_dict()


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdate,
    db: DBSession = Depends(get_db)
):
    """
    更新知识库
    """
    service = KnowledgeBaseService(db)
    kb = service.update_knowledge_base(
        kb_id=kb_id,
        name=request.name,
        description=request.description,
        icon=request.icon,
        color=request.color
    )
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    return kb.to_dict()


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    hard_delete: bool = False,
    db: DBSession = Depends(get_db)
):
    """
    删除知识库
    
    Args:
        kb_id: 知识库ID
        hard_delete: 是否硬删除（默认软删除）
    """
    service = KnowledgeBaseService(db)
    success = service.delete_knowledge_base(kb_id, hard_delete=hard_delete)
    
    if not success:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    return {"message": "知识库已删除", "kb_id": kb_id}


# =====================
# 文档接口
# =====================

@router.post("/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db)
):
    """
    上传文档到知识库（仅上传，不处理）
    
    Args:
        kb_id: 知识库ID
        file: 上传的文件
        
    Returns:
        上传成功的文档信息（status: pending）
        
    Note:
        上传后需要调用 POST /{kb_id}/documents/{doc_id}/process 接口进行处理
    """
    try:
        service = KnowledgeBaseService(db)
        
        # 检查知识库是否存在
        kb = service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 创建上传目录
        upload_dir = Path("uploads") / kb_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件路径
        file_path = upload_dir / file.filename
        
        # 保存文件
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 获取文件大小
        file_size = file_path.stat().st_size
        
        # 提取文件类型
        file_type = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"
        
        # 读取内容预览（前200字符）
        content_preview = None
        try:
            if file_type in ["txt", "md", "py", "js", "json", "csv"]:
                with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(200)
                    content_preview = content if len(content) < 200 else content + "..."
        except Exception as e:
            logger.warning(f"读取文件预览失败: {str(e)}")
        
        # 创建文档记录（使用默认分块参数，后续可在处理时修改）
        doc = service.create_document(
            kb_id=kb_id,
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file_type,
            content_preview=content_preview,
            chunk_strategy="recursive",  # 默认策略
            chunk_size=512,              # 默认大小
            chunk_overlap=50             # 默认重叠
        )
        
        logger.info(f"文档上传成功: {file.filename} -> {kb_id}")
        return doc.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
async def get_kb_documents(
    kb_id: str,
    db: DBSession = Depends(get_db)
):
    """
    获取知识库的文档列表
    """
    service = KnowledgeBaseService(db)
    
    # 检查知识库是否存在
    kb = service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    documents = service.get_documents(kb_id)
    return [doc.to_dict() for doc in documents]


@router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document_detail(
    kb_id: str,
    doc_id: int,
    db: DBSession = Depends(get_db)
):
    """
    获取文档详情
    """
    service = KnowledgeBaseService(db)
    
    # 检查知识库是否存在
    kb = service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 获取文档
    doc = service.get_document(doc_id)
    if not doc or doc.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return doc.to_dict()


@router.post("/{kb_id}/documents/{doc_id}/process")
async def process_document(
    kb_id: str,
    doc_id: int,
    chunk_strategy: str = Form("recursive"),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    db: DBSession = Depends(get_db)
):
    """
    处理文档（解析 + 分块）
    
    在用户上传文档并确认分块策略后，调用此接口开始处理
    
    Args:
        kb_id: 知识库ID
        doc_id: 文档ID
        chunk_strategy: 分块策略（recursive/fixed/sentence/semantic）
        chunk_size: 分块大小（字符数）
        chunk_overlap: 重叠大小（字符数）
    
    Returns:
        处理结果，包含分块数量等信息
    """
    try:
        from app.services.document_processing_service import DocumentProcessingService
        
        service = KnowledgeBaseService(db)
        
        # 检查知识库是否存在
        kb = service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 检查文档是否存在
        doc = service.get_document(doc_id)
        if not doc or doc.kb_id != kb_id:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 检查文档是否已处理
        if doc.process_status == "completed":
            return {
                "message": "文档已处理完成",
                "doc_id": doc_id,
                "chunk_count": doc.chunk_count
            }
        
        # 更新文档的分块参数
        doc.chunk_strategy = chunk_strategy
        doc.chunk_size = chunk_size
        doc.chunk_overlap = chunk_overlap
        db.commit()
        
        # 开始处理
        logger.info(f"⚡ 开始处理文档: doc_id={doc_id}, 策略={chunk_strategy}, 大小={chunk_size}")
        
        processing_service = DocumentProcessingService(db)
        result = processing_service.process_document(
            doc_id=doc.id,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.get("/{kb_id}/documents/{doc_id}/chunks")
async def get_document_chunks(
    kb_id: str,
    doc_id: int,
    limit: int = 100,
    offset: int = 0,
    db: DBSession = Depends(get_db)
):
    """
    获取文档的分块列表（用于前端预览）
    
    Args:
        kb_id: 知识库ID
        doc_id: 文档ID
        limit: 返回数量限制（默认100）
        offset: 偏移量（默认0，用于分页）
    
    Returns:
        {
            "doc_id": 文档ID,
            "filename": 文件名,
            "total_chunks": 总分块数,
            "chunks": [
                {
                    "id": 分块ID,
                    "index": 分块索引,
                    "text": 分块文本,
                    "size": 分块大小,
                    "start_position": 起始位置,
                    "end_position": 结束位置,
                    ...
                }
            ]
        }
    """
    service = KnowledgeBaseService(db)
    
    # 检查知识库是否存在
    kb = service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 检查文档是否存在
    doc = service.get_document(doc_id)
    if not doc or doc.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 检查文档是否已处理
    if doc.process_status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"文档尚未处理完成，当前状态: {doc.process_status}"
        )
    
    # 获取分块列表
    chunks = service.get_document_chunks(doc_id, limit=limit, offset=offset)
    total_chunks = service.get_chunks_count(doc_id)
    
    return {
        "doc_id": doc.id,
        "filename": doc.filename,
        "chunk_strategy": doc.chunk_strategy,
        "chunk_size": doc.chunk_size,
        "chunk_overlap": doc.chunk_overlap,
        "total_chunks": total_chunks,
        "returned_chunks": len(chunks),
        "offset": offset,
        "limit": limit,
        "chunks": [chunk.to_dict() for chunk in chunks]
    }


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(
    kb_id: str,
    doc_id: int,
    db: DBSession = Depends(get_db)
):
    """
    删除文档
    """
    service = KnowledgeBaseService(db)
    
    # 验证文档属于该知识库
    doc = service.get_document(doc_id)
    if not doc or doc.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    success = service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return {"message": "文档已删除", "doc_id": doc_id}


# =====================
# 智能体知识库绑定接口
# =====================

@router.post("/agents/{agent_id}/bind")
async def bind_knowledge_base(
    agent_id: str,
    request: AgentKBBindRequest,
    db: DBSession = Depends(get_db)
):
    """
    绑定知识库到智能体
    """
    try:
        service = KnowledgeBaseService(db)
        
        # 检查知识库是否存在
        kb = service.get_knowledge_base(request.kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        binding = service.bind_knowledge_base_to_agent(
            agent_id=agent_id,
            kb_id=request.kb_id,
            priority=request.priority,
            is_active=request.is_active,
            max_results=request.max_results,
            similarity_threshold=request.similarity_threshold
        )
        
        return binding.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"绑定知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/bindings")
async def get_agent_knowledge_bases(
    agent_id: str,
    active_only: bool = True,
    db: DBSession = Depends(get_db)
):
    """
    获取智能体绑定的知识库列表
    
    Args:
        agent_id: 智能体ID
        active_only: 是否只返回启用的知识库
    """
    try:
        service = KnowledgeBaseService(db)
        bindings = service.get_agent_knowledge_bases(agent_id, active_only=active_only)
        return bindings
    except Exception as e:
        logger.error(f"获取智能体知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/agents/{agent_id}/bindings/{kb_id}")
async def update_binding_config(
    agent_id: str,
    kb_id: str,
    request: AgentKBBindUpdate,
    db: DBSession = Depends(get_db)
):
    """
    更新知识库绑定配置
    """
    service = KnowledgeBaseService(db)
    binding = service.update_binding_config(
        agent_id=agent_id,
        kb_id=kb_id,
        priority=request.priority,
        is_active=request.is_active,
        max_results=request.max_results,
        similarity_threshold=request.similarity_threshold
    )
    
    if not binding:
        raise HTTPException(status_code=404, detail="绑定关系不存在")
    
    return binding.to_dict()


@router.delete("/agents/{agent_id}/bindings/{kb_id}")
async def unbind_knowledge_base(
    agent_id: str,
    kb_id: str,
    db: DBSession = Depends(get_db)
):
    """
    解绑知识库
    """
    service = KnowledgeBaseService(db)
    success = service.unbind_knowledge_base_from_agent(agent_id, kb_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="绑定关系不存在")
    
    return {"message": "知识库已解绑", "agent_id": agent_id, "kb_id": kb_id}


# =====================
# 检索相关接口
# =====================

@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(
    request: SearchRequest,
    db: DBSession = Depends(get_db)
):
    """
    知识库混合检索 - 支持多知识库独立配置
    
    每个知识库可以有自己的检索参数配置：
    - top_k: 该知识库返回的结果数量
    - min_score: 最低置信度阈值（0-1）
    - vector_boost: 向量检索权重（0-1）
    - text_boost: 全文检索权重（0-1）
    
    ## 请求示例
    ```json
    {
        "query": "Python编程最佳实践",
        "kb_configs": [
            {
                "kb_id": "kb_1db122e7",
                "top_k": 3,
                "min_score": 0.8,
                "vector_boost": 0.9,
                "text_boost": 0.1
            },
            {
                "kb_id": "kb_2abc456",
                "top_k": 2,
                "min_score": 0.6,
                "vector_boost": 0.5,
                "text_boost": 0.5
            }
        ],
        "mode": "knn_query"
    }
    ```
    
    ## 响应说明
    - 结果会按照归一化分数（0-1）降序排列
    - 每个结果包含来源知识库和配置信息
    """
    try:
        # 创建检索服务
        retrieval_service = KBRetrievalService(db)
        kb_service = KnowledgeBaseService(db)
        
        logger.info(f"🔍 多知识库检索: query='{request.query[:50]}...', kb_count={len(request.kb_configs)}")
        if request.use_rerank:
            logger.info(f"   🎯 全局 Rerank: 启用 (返回 top {request.rerank_top_k or 'auto'})")
        
        # 验证知识库并准备配置
        valid_configs = []
        for config in request.kb_configs:
            kb = kb_service.get_knowledge_base(config.kb_id)
            if kb:
                valid_configs.append({
                    "kb_id": config.kb_id,
                    "top_k": config.top_k,
                    "min_score": config.min_score,
                    "vector_boost": config.vector_boost,
                    "text_boost": config.text_boost
                })
                logger.info(f"   ✅ 知识库: {config.kb_id} - top_k={config.top_k}, "
                          f"min_score={config.min_score}, v={config.vector_boost}, "
                          f"t={config.text_boost}")
            else:
                logger.warning(f"   ⚠️  知识库不存在: {config.kb_id}")
        
        if not valid_configs:
            return SearchResponse(
                success=False,
                query=request.query,
                mode=request.mode,
                vector_boost=0.0,
                text_boost=0.0,
                total=0,
                results=[],
                error="没有有效的知识库"
            )
        
        # 执行多知识库独立配置检索（可能包含全局 Rerank）
        search_results = retrieval_service.search_with_configs(
            query=request.query,
            kb_configs=valid_configs,
            mode=HybridMode(request.mode),
            use_rerank=request.use_rerank,
            rerank_top_k=request.rerank_top_k
        )
        
        # 使用第一个配置的权重作为响应中的权重（仅用于展示）
        vector_boost = valid_configs[0]["vector_boost"]
        text_boost = valid_configs[0]["text_boost"]
        
        # 从检索结果中获取 Rerank 信息和警告
        use_rerank = search_results.get("use_rerank", False)
        rerank_model = search_results.get("rerank_model")
        warning = search_results.get("warning")
        
        # 增强结果（添加文档名和知识库名）
        enhanced_results = []
        for result in search_results.get("results", []):
            # 查询文档信息
            doc_id = result.get("doc_id")
            doc = db.query(KBDocument).filter(KBDocument.id == doc_id).first()
            
            # 查询知识库信息
            kb_id = result.get("kb_id")
            kb = kb_service.get_knowledge_base(kb_id)
            
            enhanced_results.append(SearchResultItem(
                chunk_id=result.get("chunk_id"),
                doc_id=doc_id,
                kb_id=kb_id,
                chunk_text=result.get("chunk_text"),
                chunk_index=result.get("chunk_index"),
                score=result.get("score"),
                metadata=result.get("metadata", {}),
                doc_name=doc.filename if doc else None,
                kb_name=kb.name if kb else None
            ))
        
        logger.info(f"   ✅ 检索完成: 找到 {len(enhanced_results)} 个结果")
        
        return SearchResponse(
            success=True,
            query=request.query,
            mode=request.mode,
            use_rerank=use_rerank,
            rerank_model=rerank_model,
            vector_boost=vector_boost,
            text_boost=text_boost,
            total=len(enhanced_results),
            results=enhanced_results,
            warning=warning
        )
        
    except Exception as e:
        logger.error(f"   ❌ 检索失败: {str(e)}", exc_info=True)
        return SearchResponse(
            success=False,
            query=request.query,
            mode=request.mode,
            vector_boost=request.vector_boost,
            text_boost=request.text_boost,
            total=0,
            results=[],
            error=str(e)
        )


# =====================
# 检索配置管理 API
# =====================

@router.get("/{kb_id}/retrieval-config")
async def get_retrieval_config(
    kb_id: str,
    db: DBSession = Depends(get_db)
):
    """
    获取知识库的检索配置
    
    - 如果知识库没有配置，返回默认值
    - 配置包括：向量权重、文本权重、Rerank等
    """
    logger.info(f"📖 获取知识库检索配置: {kb_id}")
    
    try:
        kb_service = KnowledgeBaseService(db)
        kb = kb_service.get_knowledge_base(kb_id)
        
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 {kb_id} 不存在")
        
        # 如果没有配置，返回默认配置
        default_config = {
            "vector_boost": 0.7,
            "text_boost": 0.3,
            "top_k": 5,
            "min_score": 0.7,
            "use_rerank": False,
            "rerank_top_k": 10
        }
        
        config = kb.retrieval_config or default_config
        
        logger.info(f"   ✅ 配置获取成功")
        return {
            "success": True,
            "kb_id": kb_id,
            "kb_name": kb.name,
            "config": config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ 获取配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{kb_id}/retrieval-config")
async def update_retrieval_config(
    kb_id: str,
    config: RetrievalConfigUpdate,
    db: DBSession = Depends(get_db)
):
    """
    更新知识库的检索配置
    
    - 配置会持久化到数据库
    - 配置将在对话中自动使用
    - 参数验证：vector_boost + text_boost = 1.0
    """
    logger.info(f"💾 更新知识库检索配置: {kb_id}")
    logger.info(f"   向量权重: {config.vector_boost}, 文本权重: {config.text_boost}")
    logger.info(f"   Top-K: {config.top_k}, Min Score: {config.min_score}")
    logger.info(f"   Rerank: {config.use_rerank}, Rerank Top-K: {config.rerank_top_k}")
    
    try:
        # 参数验证
        if abs(config.vector_boost + config.text_boost - 1.0) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"向量权重 + 文本权重必须等于 1.0，当前值: {config.vector_boost + config.text_boost}"
            )
        
        if config.top_k < 1 or config.top_k > 50:
            raise HTTPException(status_code=400, detail="top_k 必须在 1-50 之间")
        
        if config.min_score < 0 or config.min_score > 1:
            raise HTTPException(status_code=400, detail="min_score 必须在 0-1 之间")
        
        kb_service = KnowledgeBaseService(db)
        kb = kb_service.get_knowledge_base(kb_id)
        
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 {kb_id} 不存在")
        
        # 更新配置（Rerank 强制为 False，由前端运行时动态传递）
        kb.retrieval_config = {
            "vector_boost": config.vector_boost,
            "text_boost": config.text_boost,
            "top_k": config.top_k,
            "min_score": config.min_score,
            "use_rerank": False,        # 强制为 False，不持久化
            "rerank_top_k": 10          # 默认值，不持久化
        }
        
        logger.info(f"   💡 Rerank 参数不持久化，运行时由前端动态传递")
        
        db.commit()
        db.refresh(kb)
        
        logger.info(f"   ✅ 配置更新成功")
        return {
            "success": True,
            "message": "配置更新成功",
            "kb_id": kb_id,
            "kb_name": kb.name,
            "config": kb.retrieval_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ 更新配置失败: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

