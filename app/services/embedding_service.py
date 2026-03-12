"""
Embedding 向量化服务

使用 Jina Embeddings v3 API 将文本转换为向量
"""
from typing import List, Optional, Union
import httpx
import time

from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class EmbeddingService:
    """
    Embedding 向量化服务
    
    使用 Jina Embeddings v3 API 进行文本向量化
    """
    
    def __init__(self):
        """初始化服务"""
        self.api_url = settings.JINA_API_URL
        self.api_key = settings.JINA_API_KEY
        self.model_name = settings.JINA_MODEL_NAME
        self.default_task = settings.JINA_TASK_TYPE
        self.dimensions = settings.JINA_DIMENSIONS
        self.timeout = settings.JINA_TIMEOUT
        
        # 重试配置
        self.max_retries = getattr(settings, 'JINA_MAX_RETRIES', 3)
        self.retry_delay = 2  # 秒
        
        # SSL 验证配置
        self.verify_ssl = getattr(settings, 'JINA_VERIFY_SSL', False)
        
        # 创建 HTTP 客户端
        self.client = httpx.Client(
            timeout=self.timeout,
            verify=self.verify_ssl,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        logger.info("=" * 60)
        logger.info(f"🤖 Jina Embeddings v3 服务已初始化")
        logger.info(f"   模型: {self.model_name}")
        logger.info(f"   默认任务类型: {self.default_task}")
        logger.info(f"   向量维度: {self.dimensions}")
        logger.info(f"   最大重试次数: {self.max_retries}")
        logger.info(f"   SSL 验证: {'启用' if self.verify_ssl else '禁用（避免网络错误）'}")
        if not self.verify_ssl:
            logger.warning("⚠️  SSL 验证已禁用，仅用于开发环境或网络不稳定时")
        logger.info("=" * 60)
    
    def _call_api(
        self, 
        texts: Union[str, List[str]], 
        task: Optional[str] = None,
        retry_count: int = 0
    ) -> List[List[float]]:
        """
        调用 Jina API（带重试机制）
        
        Args:
            texts: 单个文本或文本列表
            task: 任务类型（可选）
            retry_count: 当前重试次数
            
        Returns:
            List[List[float]]: 向量列表
        """
        task = task or self.default_task
        
        # 构建请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model_name,
            "task": task,
            "input": texts,
            "dimensions": self.dimensions
        }
        
        try:
            response = self.client.post(
                self.api_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 提取 embeddings
            embeddings = []
            for item in data.get("data", []):
                embeddings.append(item["embedding"])
            
            return embeddings
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Jina API 请求失败: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Jina API 错误: {e.response.status_code}")
            
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            # 网络相关错误，可以重试
            if retry_count < self.max_retries:
                retry_count += 1
                wait_time = self.retry_delay * retry_count
                logger.warning(f"⚠️  网络错误: {type(e).__name__} - {str(e)}")
                logger.warning(f"   正在重试 ({retry_count}/{self.max_retries})，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                return self._call_api(texts, task, retry_count)
            else:
                logger.error(f"❌ 达到最大重试次数，放弃请求: {str(e)}")
                raise Exception(f"Jina API 网络错误（已重试 {self.max_retries} 次）: {str(e)}")
                
        except Exception as e:
            logger.error(f"调用 Jina API 失败: {type(e).__name__} - {str(e)}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        单个文本向量化（用于文档分块）
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 向量表示
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回零向量")
            return [0.0] * self.dimensions
        
        try:
            # 使用 retrieval.passage 任务（用于被检索的文档）
            embeddings = self._call_api(text, task="retrieval.passage")
            return embeddings[0]
            
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise
    
    def embed_query(self, query: str) -> List[float]:
        """
        查询文本向量化（用于检索查询）
        
        Args:
            query: 查询文本
            
        Returns:
            List[float]: 向量表示
        """
        if not query or not query.strip():
            logger.warning("查询文本为空，返回零向量")
            return [0.0] * self.dimensions
        
        try:
            # 使用 retrieval.query 任务（用于查询）
            embeddings = self._call_api(query, task="retrieval.query")
            return embeddings[0]
            
        except Exception as e:
            logger.error(f"查询向量化失败: {str(e)}")
            raise
    
    def embed_batch(
        self, 
        texts: List[str], 
        batch_size: Optional[int] = None,
        show_progress: bool = False,
        task: str = "retrieval.passage"
    ) -> List[List[float]]:
        """
        批量文本向量化
        
        Args:
            texts: 文本列表
            batch_size: 批量大小（默认使用配置值）
            show_progress: 是否显示进度条
            task: 任务类型（默认为 retrieval.passage）
            
        Returns:
            List[List[float]]: 向量列表
        """
        if not texts:
            return []
        
        # 过滤空文本
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            logger.warning("所有文本为空，返回零向量列表")
            return [[0.0] * self.dimensions] * len(texts)
        
        try:
            batch_size = batch_size or settings.JINA_BATCH_SIZE
            
            logger.info(f"批量向量化: {len(valid_texts)} 个文本, batch_size={batch_size}")
            
            all_embeddings = []
            
            # 分批处理
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]
                batch_num = i//batch_size + 1
                total_batches = (len(valid_texts)-1)//batch_size + 1
                
                if show_progress:
                    logger.info(f"处理批次 {batch_num}/{total_batches}")
                
                try:
                    # 调用 API（一次可以传多个文本）
                    batch_embeddings = self._call_api(batch, task=task)
                    all_embeddings.extend(batch_embeddings)
                except Exception as batch_error:
                    logger.error(f"❌ 批次 {batch_num}/{total_batches} 处理失败: {str(batch_error)}")
                    # 如果是网络错误，建议用户检查网络
                    if "SSL" in str(batch_error) or "网络错误" in str(batch_error):
                        logger.error("💡 建议：")
                        logger.error("   1. 检查网络连接是否稳定")
                        logger.error("   2. 如果在国内，可能需要使用代理")
                        logger.error("   3. 稍后重试文档处理")
                    raise
            
            logger.info(f"✅ 批量向量化完成: {len(all_embeddings)} 个向量")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"批量向量化失败: {str(e)}")
            raise
    
    def get_dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            int: 向量维度
        """
        return self.dimensions
    
    def get_model_info(self) -> dict:
        """
        获取模型信息
        
        Returns:
            dict: 模型信息
        """
        return {
            "provider": "Jina AI",
            "model_name": self.model_name,
            "api_url": self.api_url,
            "embedding_dimension": self.dimensions,
            "default_task": self.default_task,
            "supported_tasks": [
                "retrieval.query",
                "retrieval.passage",
                "text-matching",
                "classification",
                "separation"
            ],
            "batch_size": settings.JINA_BATCH_SIZE,
        }
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'client'):
            self.client.close()


# 全局单例实例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取 Embedding 服务实例（单例）
    
    Returns:
        EmbeddingService: Embedding 服务
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


# 导出单例实例（便捷使用）
embedding_service = get_embedding_service()
