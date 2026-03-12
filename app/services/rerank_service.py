"""
Rerank 重排序服务

使用阿里云百练 qwen3-rerank 模型对检索结果进行重排序
"""
from typing import List, Dict, Any, Optional
import httpx
import time

from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class RerankService:
    """
    Rerank 重排序服务
    
    使用阿里云百练 qwen3-rerank 模型
    """
    
    def __init__(self):
        """初始化服务"""
        self.api_url = settings.RERANK_API_URL
        self.api_key = settings.RERANK_API_KEY
        self.model_name = settings.RERANK_MODEL_NAME
        self.timeout = settings.RERANK_TIMEOUT
        self.max_retries = settings.RERANK_MAX_RETRIES
        self.retry_delay = 2  # 秒
        
        # 创建 HTTP 客户端
        self.client = httpx.Client(
            timeout=self.timeout,
            verify=False  # 禁用 SSL 验证
        )
        
        logger.info("=" * 60)
        logger.info(f"🎯 Rerank 重排序服务已初始化")
        logger.info(f"   模型: {self.model_name}")
        logger.info(f"   最大重试次数: {self.max_retries}")
        logger.info("=" * 60)
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_n: Optional[int] = None,
        return_documents: bool = True
    ) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序
        
        Args:
            query: 用户查询
            documents: 候选文档列表，每个文档需包含 'chunk_text' 字段
            top_n: 返回前 N 个结果（默认使用配置值）
            return_documents: 是否返回完整文档（True）或仅返回索引（False）
            
        Returns:
            重排序后的文档列表，包含新的 rerank_score
        """
        if not documents:
            logger.warning("文档列表为空，跳过 Rerank")
            return []
        
        if not self.api_key:
            logger.warning("⚠️  Rerank API Key 未配置，跳过重排序")
            return documents
        
        top_n = top_n or settings.RERANK_TOP_N
        
        logger.info(f"🎯 开始 Rerank 重排序: {len(documents)} 个候选 → top {top_n}")
        
        try:
            # 提取文档文本
            doc_texts = [doc.get('chunk_text', '') for doc in documents]
            
            # 调用 Rerank API
            rerank_results = self._call_rerank_api(
                query=query,
                documents=doc_texts,
                top_n=top_n,
                return_documents=return_documents
            )
            
            # 合并 Rerank 分数到原始文档
            reranked_docs = []
            for result in rerank_results:
                index = result['index']
                rerank_score = result['relevance_score']
                
                # 获取原始文档
                original_doc = documents[index].copy()
                
                # 保存 ES 原始分数
                es_original_score = original_doc.get('score', 0.0)
                
                # 更新为 Rerank 分数
                original_doc['score'] = rerank_score  # 最终分数（Rerank 分数）
                original_doc['original_score'] = es_original_score  # ES 原始分数
                
                # 添加调试字段（可选）
                original_doc['rerank_rank'] = len(reranked_docs) + 1
                original_doc['original_rank'] = index + 1
                original_doc['es_score'] = es_original_score  # 向后兼容
                
                reranked_docs.append(original_doc)
            
            logger.info(f"   ✅ Rerank 完成: 返回 {len(reranked_docs)} 个结果")
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"   ❌ Rerank 失败，降级为 ES 原始结果: {str(e)}")
            # 失败时返回原始结果（取前 top_n 个）
            return documents[:top_n]
    
    def _call_rerank_api(
        self,
        query: str,
        documents: List[str],
        top_n: int,
        return_documents: bool = True,
        retry_count: int = 0
    ) -> List[Dict[str, Any]]:
        """
        调用阿里云百练 Rerank API（带重试机制）
        
        Args:
            query: 查询文本
            documents: 文档文本列表
            top_n: 返回前 N 个结果
            return_documents: 是否返回文档文本
            retry_count: 当前重试次数
            
        Returns:
            Rerank 结果列表
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model_name,
            "input": {
                "query": query,
                "documents": documents
            },
            "parameters": {
                "top_n": top_n,
                "return_documents": return_documents
            }
        }
        
        try:
            response = self.client.post(
                self.api_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 解析结果
            if 'output' in data and 'results' in data['output']:
                results = data['output']['results']
                return results
            else:
                logger.error(f"Rerank API 返回格式异常: {data}")
                raise Exception("Rerank API 返回格式错误")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Rerank API 请求失败: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Rerank API 错误: {e.response.status_code}")
        
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            # 网络相关错误，可以重试
            if retry_count < self.max_retries:
                retry_count += 1
                wait_time = self.retry_delay * retry_count
                logger.warning(f"⚠️  Rerank 网络错误: {type(e).__name__}")
                logger.warning(f"   正在重试 ({retry_count}/{self.max_retries})，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                return self._call_rerank_api(query, documents, top_n, return_documents, retry_count)
            else:
                logger.error(f"❌ Rerank 达到最大重试次数: {str(e)}")
                raise Exception(f"Rerank API 网络错误（已重试 {self.max_retries} 次）")
        
        except Exception as e:
            logger.error(f"调用 Rerank API 失败: {type(e).__name__} - {str(e)}")
            raise
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'client'):
            self.client.close()


# 全局单例实例
_rerank_service: Optional[RerankService] = None


def get_rerank_service() -> RerankService:
    """
    获取 Rerank 服务实例（单例）
    """
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service


# 导出单例实例
rerank_service = get_rerank_service()
