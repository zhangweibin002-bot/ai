"""
知识库检索服务（基于 ES 原生混合检索）

支持：
1. ES 原生 kNN + Query 混合检索（推荐）
2. ES 原生 RRF 混合检索
3. 自适应权重（可选）
"""
from typing import List, Optional, Dict, Any
from enum import Enum
from sqlalchemy.orm import Session as DBSession

from app.core.logger import setup_logger
from app.core.config import settings
from app.core.es_client import get_es_client, ESIndexManager
from app.models.knowledge_base import KnowledgeBase, KBDocument
from app.models.document_chunk import DocumentChunk
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.embedding_service import embedding_service
from app.services.rerank_service import get_rerank_service

logger = setup_logger(__name__)


class HybridMode(str, Enum):
    """混合检索模式"""
    KNN_QUERY = "knn_query"  # ES 原生 kNN + Query（推荐）
    RRF = "rrf"              # ES 原生 RRF（需要 ES 8.4+）


class KBRetrievalService:
    """知识库检索服务（基于 ES 原生混合检索）"""
    
    def __init__(self, db: DBSession):
        self.db = db
        self.kb_service = KnowledgeBaseService(db)
        self.es_client = get_es_client()
        self.embedding_service = embedding_service
        self.rerank_service = get_rerank_service()
        self.rerank_enabled = settings.RERANK_ENABLED and bool(settings.RERANK_API_KEY)
    
    def search_with_configs(
        self,
        query: str,
        kb_configs: List[Dict],
        mode: HybridMode = HybridMode.KNN_QUERY,
        use_rerank: bool = False,
        rerank_top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        多知识库独立配置检索 + 全局 Rerank 重排序
        
        流程：
        1. 各知识库独立检索（ES 混合检索）
        2. 合并所有结果
        3. （可选）对合并后的结果进行全局 Rerank 重排序
        
        Args:
            query: 查询文本
            kb_configs: 知识库配置列表
            mode: 混合模式
            use_rerank: 是否启用 Rerank 重排序（全局）
            rerank_top_k: Rerank 返回的最终结果数
            
        Returns:
            合并排序后的检索结果（可能经过 Rerank）
        """
        if not kb_configs or not query:
            return {
                "query": query,
                "mode": mode,
                "total": 0,
                "results": []
            }
        
        logger.info(f"🔍 多知识库独立配置检索: query='{query[:50]}...', kb_count={len(kb_configs)}")
        
        # 1. 向量化查询（只需一次）
        query_vector = self.embedding_service.embed_query(query)
        logger.info(f"   ✅ 查询向量化完成: {len(query_vector)}维")
        
        # 2. 为每个知识库执行独立检索
        all_results = []
        for i, config in enumerate(kb_configs, 1):
            kb_id = config.get("kb_id")
            top_k = config.get("top_k", 5)
            min_score = config.get("min_score", 0.0)
            vector_boost = config.get("vector_boost", 0.7)
            text_boost = config.get("text_boost", 0.3)
            
            logger.info(f"   📚 [{i}/{len(kb_configs)}] 检索知识库: {kb_id}")
            logger.info(f"      配置: top_k={top_k}, min_score={min_score}, v={vector_boost}, t={text_boost}")
            
            # 执行单个知识库检索
            kb_results = self._search_single_kb(
                query=query,
                query_vector=query_vector,
                kb_id=kb_id,
                top_k=top_k,
                mode=mode,
                vector_boost=vector_boost,
                text_boost=text_boost,
                min_score=min_score
            )
            
            # 为结果添加知识库配置信息（可选，用于调试）
            for result in kb_results:
                result["kb_config"] = {
                    "kb_id": kb_id,
                    "top_k": top_k,
                    "min_score": min_score,
                    "vector_boost": vector_boost,
                    "text_boost": text_boost
                }
            
            all_results.extend(kb_results)
            logger.info(f"      ✅ 找到 {len(kb_results)} 个结果")
        
        # 3. 合并排序（按 ES 归一化分数降序）
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"   ✅ ES 检索完成: 合并后共 {len(all_results)} 个候选")
        
        # 4. 检查 Rerank 候选数是否充足
        warning_message = None
        if use_rerank and self.rerank_enabled and rerank_top_k and len(all_results) < rerank_top_k:
            warning_message = f"⚠️  ES 候选数({len(all_results)})小于期望的 rerank_top_k({rerank_top_k})，最多只能返回 {len(all_results)} 个结果"
            logger.warning(f"   {warning_message}")
            logger.warning(f"      建议: 增加各知识库的 top_k 配置，或减少 rerank_top_k")
        
        # 5. 全局 Rerank 重排序（如果启用）
        reranked = False
        rerank_model_name = None
        
        if use_rerank and self.rerank_enabled and len(all_results) > 0:
            logger.info(f"   🎯 开始全局 Rerank 重排序...")
            logger.info(f"      候选数: {len(all_results)} 个")
            logger.info(f"      目标返回数: {rerank_top_k or 'auto'}")
            
            try:
                # 调用 Rerank 服务
                reranked_results = self.rerank_service.rerank(
                    query=query,
                    documents=all_results,
                    top_n=rerank_top_k
                )
                
                # 为 Rerank 后的结果添加 original_score 字段
                for result in reranked_results:
                    if 'es_score' in result:
                        result['original_score'] = result['es_score']
                
                all_results = reranked_results
                reranked = True
                rerank_model_name = settings.RERANK_MODEL_NAME
                
                logger.info(f"      ✅ Rerank 完成: 返回 {len(all_results)} 个结果")
                
            except Exception as rerank_error:
                logger.error(f"      ❌ Rerank 失败，降级为 ES 结果: {str(rerank_error)}")
                # Rerank 失败，保持 ES 原始结果
                if rerank_top_k:
                    all_results = all_results[:rerank_top_k]
        
        return {
            "query": query,
            "mode": mode,
            "use_rerank": reranked,
            "rerank_model": rerank_model_name,
            "total": len(all_results),
            "results": all_results,
            "kb_count": len(kb_configs),
            "warning": warning_message  # 如果候选数不足，返回警告信息
        }
    
    def _search_single_kb(
        self,
        query: str,
        query_vector: List[float],
        kb_id: str,
        top_k: int,
        mode: HybridMode,
        vector_boost: float,
        text_boost: float,
        min_score: float
    ) -> List[Dict]:
        """
        单个知识库检索（内部方法）
        
        Returns:
            结果列表（已归一化和过滤）
        """
        try:
            # 1. 检查索引是否存在
            index_name = ESIndexManager.get_index_name(kb_id)
            if not self.es_client.indices.exists(index=index_name):
                logger.warning(f"      ⚠️  索引不存在: {index_name}")
                return []
            
            # 2. 构建 ES 查询
            if mode == HybridMode.KNN_QUERY:
                es_query = self._build_knn_query_hybrid(
                    query_text=query,
                    query_vector=query_vector,
                    kb_ids=[kb_id],
                    top_k=top_k,
                    vector_boost=vector_boost,
                    text_boost=text_boost
                )
            else:  # RRF
                es_query = self._build_rrf_hybrid(
                    query_text=query,
                    query_vector=query_vector,
                    kb_ids=[kb_id],
                    top_k=top_k
                )
            
            # 3. 执行检索
            results = self.es_client.search(
                index=index_name,
                body=es_query
            )
            
            # 4. 解析 ES 结果
            parsed_results = self._parse_results(
                results, query, mode, 
                min_score=min_score, 
                top_k=top_k
            )
            
            return parsed_results.get("results", [])
            
        except Exception as e:
            logger.error(f"      ❌ 检索失败: {str(e)}")
            return []
    
    def retrieve_context(
        self,
        query: str,
        kb_ids: List[str],
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        从指定的知识库中检索相关内容（兼容接口）
        
        Args:
            query: 用户查询
            kb_ids: 知识库ID列表
            max_results: 最多返回结果数
            similarity_threshold: 相似度阈值（用作 min_score）
            
        Returns:
            检索结果字典，包含：
            - context: 格式化的上下文文本
            - sources: 来源文档列表
            - kb_names: 知识库名称列表
        """
        if not kb_ids or not query:
            return {
                "context": "",
                "sources": [],
                "kb_names": []
            }
        
        logger.info(f"📚 开始检索知识库上下文: kb_ids={kb_ids}, query='{query[:50]}...'")
        
        # 1. 验证知识库是否存在
        valid_kbs = []
        for kb_id in kb_ids:
            kb = self.kb_service.get_knowledge_base(kb_id)
            if kb:
                valid_kbs.append(kb)
            else:
                logger.warning(f"   ⚠️  知识库不存在: {kb_id}")
        
        if not valid_kbs:
            logger.warning("   ❌ 没有有效的知识库")
            return {
                "context": "",
                "sources": [],
                "kb_names": []
            }
        
        kb_names = [kb.name for kb in valid_kbs]
        logger.info(f"   ✅ 有效知识库: {kb_names}")
        
        # 2. 使用 ES 混合检索（多知识库独立配置）
        # 为每个知识库创建相同的配置
        kb_configs = [
            {
                "kb_id": kb.id,
                "top_k": max_results,
                "min_score": similarity_threshold,
                "vector_boost": 0.7,
                "text_boost": 0.3
            }
            for kb in valid_kbs
        ]
        
        search_results = self.search_with_configs(
            query=query,
            kb_configs=kb_configs,
            mode=HybridMode.KNN_QUERY
        )
        
        # 3. 格式化检索结果
        if not search_results.get("results"):
            logger.info("   ℹ️  未检索到相关内容")
            return {
                "context": "",
                "sources": [],
                "kb_names": kb_names
            }
        
        # 4. 构建上下文
        context_parts = []
        sources = []
        
        context_parts.append("=== 知识库参考内容 ===\n")
        
        for i, result in enumerate(search_results["results"], 1):
            kb = next((k for k in valid_kbs if k.id == result.get("kb_id")), None)
            kb_name = kb.name if kb else "未知知识库"
            
            # 查询文档信息
            doc_id = result.get("doc_id")
            doc = self.db.query(KBDocument).filter(KBDocument.id == doc_id).first()
            doc_name = doc.filename if doc else f"文档{doc_id}"
            
            context_parts.append(f"[来源 {i}] {kb_name} - {doc_name} (相关度: {result.get('score', 0):.2f})")
            context_parts.append(result.get("chunk_text", ""))
            context_parts.append("")  # 空行
            
            sources.append({
                "kb_id": result.get("kb_id"),
                "kb_name": kb_name,
                "doc_id": doc_id,
                "chunk_id": result.get("chunk_id"),
                "filename": doc_name,
                "text": result.get("chunk_text"),
                "score": result.get("score")
            })
        
        context_parts.append("=== 请基于以上知识库内容回答用户问题 ===\n")
        
        context = "\n".join(context_parts)
        
        logger.info(f"   ✅ 检索完成: 找到 {len(sources)} 个相关分块")
        
        return {
            "context": context,
            "sources": sources,
            "kb_names": kb_names
        }
    
    def _build_knn_query_hybrid(
        self,
        query_text: str,
        query_vector: List[float],
        kb_ids: List[str],
        top_k: int,
        vector_boost: float,
        text_boost: float
    ) -> Dict:
        """
        构建 ES 原生 kNN + Query 混合查询（推荐）
        
        ES 8.0+ 原生支持，一次请求完成向量检索 + 全文检索
        """
        return {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": top_k * 10,  # 向量召回候选数（通常是最终返回数的10倍）
                "num_candidates": top_k * 20,  # 向量检索候选数
                "boost": vector_boost,
                "filter": {
                    "terms": {"kb_id": kb_ids}
                }
            },
            "query": {
                "bool": {
                    "must": [
                        {"terms": {"kb_id": kb_ids}}
                    ],
                    "should": [
                        {
                            "match": {
                                "chunk_text": {
                                    "query": query_text,
                                    "boost": text_boost
                                }
                            }
                        }
                    ]
                }
            },
            # 注意：多召回一些候选，因为 min_score 过滤在归一化后进行
            # 如果用户设置了 min_score，我们需要确保有足够的候选
            "size": top_k * 2,  # 召回更多候选，确保过滤后仍有足够结果
            "_source": ["chunk_id", "doc_id", "chunk_text", "chunk_index", "metadata", "kb_id"]
        }
    
    def _build_rrf_hybrid(
        self,
        query_text: str,
        query_vector: List[float],
        kb_ids: List[str],
        top_k: int
    ) -> Dict:
        """
        构建 ES 原生 RRF 混合查询
        
        ES 8.4+ 支持，基于排名融合，不依赖原始分数
        """
        return {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        # 向量检索器
                        {
                            "knn": {
                                "field": "embedding",
                                "query_vector": query_vector,
                                "k": top_k * 10,
                                "num_candidates": top_k * 20,
                                "filter": {
                                    "terms": {"kb_id": kb_ids}
                                }
                            }
                        },
                        # 全文检索器
                        {
                            "standard": {
                                "query": {
                                    "bool": {
                                        "must": [
                                            {"terms": {"kb_id": kb_ids}},
                                            {
                                                "match": {
                                                    "chunk_text": query_text
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ],
                    "rank_window_size": top_k * 10,
                    "rank_constant": 60  # RRF 的 k 参数
                }
            },
            # 同样多召回候选，以便 min_score 过滤后仍有足够结果
            "size": top_k * 2,
            "_source": ["chunk_id", "doc_id", "chunk_text", "chunk_index", "metadata", "kb_id"]
        }
    
    def _normalize_scores(
        self, 
        results: List[Dict], 
        max_score: float = 5.0,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
        归一化分数到 0-1 范围，并应用最低分数过滤
        
        策略：
        1. 如果有结果，使用批次内最大分数归一化（相对归一化）
        2. 如果最大分数很小，使用固定上界（绝对归一化）
        3. 归一化后，过滤低于 min_score 的结果
        
        Args:
            results: 结果列表
            max_score: 固定上界（默认5.0）
            min_score: 最低分数阈值（0-1，针对归一化后的分数）
            
        Returns:
            归一化并过滤后的结果列表
        """
        if not results:
            return results
        
        # 获取批次内最大分数
        batch_max_score = max(r["score"] for r in results)
        
        # 选择归一化方法
        if batch_max_score > 0:
            # 使用批次内最大分数归一化（推荐，保持相对差异）
            normalization_base = batch_max_score
            logger.debug(f"   使用相对归一化: max_score={batch_max_score:.4f}")
        else:
            # 使用固定上界（兜底）
            normalization_base = max_score
            logger.debug(f"   使用固定归一化: max_score={max_score}")
        
        # 归一化所有分数
        normalized_results = []
        for result in results:
            raw_score = result["score"]
            # 归一化到 0-1
            normalized = min(raw_score / normalization_base, 1.0)
            result["raw_score"] = raw_score  # 保留原始分数（可选）
            result["score"] = round(normalized, 4)  # 归一化分数，保留4位小数
            
            # 应用 min_score 过滤（针对归一化后的分数）
            if result["score"] >= min_score:
                normalized_results.append(result)
        
        if min_score > 0 and len(normalized_results) < len(results):
            filtered_count = len(results) - len(normalized_results)
            logger.info(f"   ⚡ min_score={min_score} 过滤了 {filtered_count} 个结果")
        
        return normalized_results
    
    def _parse_results(
        self, 
        es_response: Dict, 
        query: str, 
        mode: HybridMode,
        min_score: float = 0.0,
        top_k: int = 5
    ) -> Dict:
        """解析 ES 结果、归一化分数、应用 min_score 过滤并限制返回数量"""
        hits = es_response.get("hits", {}).get("hits", [])
        
        results = []
        for hit in hits:
            source = hit["_source"]
            results.append({
                "chunk_id": source.get("chunk_id"),
                "doc_id": source.get("doc_id"),
                "chunk_text": source.get("chunk_text"),
                "chunk_index": source.get("chunk_index"),
                "score": hit["_score"],  # 原始分数，稍后归一化
                "metadata": source.get("metadata", {}),
                "kb_id": source.get("kb_id")
            })
        
        # 归一化分数并应用 min_score 过滤
        results = self._normalize_scores(results, min_score=min_score)
        
        # 限制返回数量（因为ES召回了更多候选）
        if len(results) > top_k:
            results = results[:top_k]
            logger.debug(f"   截取 top {top_k} 个结果")
        
        return {
            "query": query,
            "mode": mode,
            "total": len(results),
            "results": results
        }
    
    def get_kb_statistics(self, kb_ids: List[str]) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Args:
            kb_ids: 知识库ID列表
            
        Returns:
            统计信息字典
        """
        stats = {
            "total_kbs": len(kb_ids),
            "total_documents": 0,
            "total_chunks": 0,
            "kb_details": []
        }
        
        for kb_id in kb_ids:
            kb = self.kb_service.get_knowledge_base(kb_id)
            if kb:
                stats["total_documents"] += kb.file_count or 0
                stats["total_chunks"] += kb.total_chunks or 0
                stats["kb_details"].append({
                    "id": kb.id,
                    "name": kb.name,
                    "file_count": kb.file_count,
                    "total_chunks": kb.total_chunks
                })
        
        return stats
