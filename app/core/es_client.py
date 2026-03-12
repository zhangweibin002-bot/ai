"""
Elasticsearch 客户端单例

提供全局 ES 客户端实例
"""
from elasticsearch import Elasticsearch
from typing import Optional

from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class ESClient:
    """
    Elasticsearch 客户端单例
    
    提供全局唯一的 ES 连接实例
    """
    _instance: Optional[Elasticsearch] = None
    _initialized: bool = False
    
    @classmethod
    def get_client(cls) -> Elasticsearch:
        """
        获取 ES 客户端实例
        
        Returns:
            Elasticsearch: ES 客户端实例
        """
        if cls._instance is None:
            cls._instance = cls._create_client()
            cls._initialized = True
            logger.info(f"Elasticsearch 客户端已初始化: {settings.ES_URL}")
        
        return cls._instance
    
    @classmethod
    def _create_client(cls) -> Elasticsearch:
        """
        创建 ES 客户端
        
        Returns:
            Elasticsearch: 新的 ES 客户端实例
        """
        # 构建连接参数
        es_params = {
            "hosts": [settings.ES_URL],
            "timeout": settings.ES_TIMEOUT,
            "max_retries": settings.ES_MAX_RETRIES,
            "retry_on_timeout": True,
        }
        
        # 添加认证信息（如果配置了）
        if settings.ES_API_KEY:
            es_params["api_key"] = settings.ES_API_KEY
        elif settings.ES_USERNAME and settings.ES_PASSWORD:
            es_params["basic_auth"] = (settings.ES_USERNAME, settings.ES_PASSWORD)
        
        try:
            client = Elasticsearch(**es_params)
            
            # 测试连接
            if client.ping():
                info = client.info()
                logger.info(f"✅ ES 连接成功: {info['version']['number']}")
            else:
                logger.error("❌ ES 连接失败: ping 不通")
                
            return client
            
        except Exception as e:
            logger.error(f"❌ 创建 ES 客户端失败: {str(e)}")
            raise
    
    @classmethod
    def close(cls):
        """
        关闭 ES 客户端连接
        """
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            cls._initialized = False
            logger.info("Elasticsearch 客户端已关闭")
    
    @classmethod
    def test_connection(cls) -> dict:
        """
        测试 ES 连接
        
        Returns:
            dict: 连接测试结果
        """
        try:
            client = cls.get_client()
            
            if not client.ping():
                return {
                    "success": False,
                    "error": "Elasticsearch ping 失败"
                }
            
            info = client.info()
            cluster_health = client.cluster.health()
            
            return {
                "success": True,
                "version": info["version"]["number"],
                "cluster_name": info["cluster_name"],
                "cluster_status": cluster_health["status"],
                "number_of_nodes": cluster_health["number_of_nodes"],
                "number_of_data_nodes": cluster_health["number_of_data_nodes"],
            }
            
        except Exception as e:
            logger.error(f"ES 连接测试失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


class ESIndexManager:
    """
    Elasticsearch 索引管理器
    
    负责创建、管理知识库的向量索引
    """
    
    @staticmethod
    def get_index_name(kb_id: str) -> str:
        """
        获取知识库对应的 ES 索引名称
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            str: 索引名称
        """
        return f"{settings.ES_INDEX_PREFIX}_{kb_id}"
    
    @staticmethod
    def create_index(kb_id: str, vector_dim: int = 1024) -> dict:
        """
        为知识库创建 ES 索引（带 kNN 向量搜索）
        
        Args:
            kb_id: 知识库ID
            vector_dim: 向量维度（默认 1024，Jina v3）
            
        Returns:
            dict: 创建结果
        """
        client = ESClient.get_client()
        index_name = ESIndexManager.get_index_name(kb_id)
        
        # 检查索引是否已存在
        if client.indices.exists(index=index_name):
            logger.info(f"📦 索引已存在: {index_name}")
            return {"success": True, "message": "索引已存在", "index": index_name}
        
        # 定义索引映射（支持 kNN 向量搜索）
        # ES 8.x 中 kNN 已内置，不需要 index.knn 设置
        index_mapping = {
            "mappings": {
                "properties": {
                    "doc_id": {"type": "integer"},
                    "chunk_id": {"type": "integer"},
                    "kb_id": {"type": "keyword"},
                    "chunk_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "chunk_index": {"type": "integer"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": vector_dim,
                        "index": True,
                        "similarity": "cosine"  # 使用余弦相似度
                    },
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
                # ES 8.x 中 kNN 已内置，不需要 index.knn 配置
            }
        }
        
        try:
            client.indices.create(index=index_name, body=index_mapping)
            logger.info(f"✅ 索引创建成功: {index_name} (维度: {vector_dim})")
            return {"success": True, "message": "索引创建成功", "index": index_name}
        except Exception as e:
            logger.error(f"❌ 索引创建失败: {str(e)}")
            raise
    
    @staticmethod
    def delete_index(kb_id: str) -> dict:
        """
        删除知识库对应的 ES 索引
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            dict: 删除结果
        """
        client = ESClient.get_client()
        index_name = ESIndexManager.get_index_name(kb_id)
        
        try:
            if client.indices.exists(index=index_name):
                client.indices.delete(index=index_name)
                logger.info(f"✅ 索引删除成功: {index_name}")
                return {"success": True, "message": "索引删除成功"}
            else:
                logger.warning(f"⚠️  索引不存在: {index_name}")
                return {"success": False, "message": "索引不存在"}
        except Exception as e:
            logger.error(f"❌ 索引删除失败: {str(e)}")
            raise
    
    @staticmethod
    def bulk_index_chunks(kb_id: str, chunks_data: list) -> dict:
        """
        批量索引分块数据（含向量）
        
        Args:
            kb_id: 知识库ID
            chunks_data: 分块数据列表，格式：
                [
                    {
                        "chunk_id": 1,
                        "doc_id": 10,
                        "chunk_text": "...",
                        "chunk_index": 0,
                        "embedding": [0.1, 0.2, ...],
                        "metadata": {...}
                    },
                    ...
                ]
        
        Returns:
            dict: 索引结果
        """
        client = ESClient.get_client()
        index_name = ESIndexManager.get_index_name(kb_id)
        
        # 确保索引存在
        if not client.indices.exists(index=index_name):
            ESIndexManager.create_index(kb_id)
        
        # 构建批量操作
        from datetime import datetime
        bulk_data = []
        for chunk in chunks_data:
            # 索引操作
            bulk_data.append({
                "index": {
                    "_index": index_name,
                    "_id": chunk["chunk_id"]
                }
            })
            # 文档数据
            bulk_data.append({
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "kb_id": kb_id,
                "chunk_text": chunk["chunk_text"],
                "chunk_index": chunk["chunk_index"],
                "embedding": chunk["embedding"],
                "metadata": chunk.get("metadata", {}),
                "created_at": datetime.now().isoformat()
            })
        
        try:
            response = client.bulk(body=bulk_data, refresh=True)
            
            # 统计结果
            success_count = 0
            error_count = 0
            
            if response.get("errors"):
                for item in response["items"]:
                    if "error" in item.get("index", {}):
                        error_count += 1
                    else:
                        success_count += 1
            else:
                success_count = len(chunks_data)
            
            logger.info(f"📦 批量索引完成: 成功 {success_count}/{len(chunks_data)}")
            
            return {
                "success": error_count == 0,
                "total": len(chunks_data),
                "success_count": success_count,
                "error_count": error_count
            }
        except Exception as e:
            logger.error(f"❌ 批量索引失败: {str(e)}")
            raise


# 便捷函数：获取 ES 客户端
def get_es_client() -> Elasticsearch:
    """
    获取 Elasticsearch 客户端实例
    
    Returns:
        Elasticsearch: ES 客户端
    """
    return ESClient.get_client()


# 全局索引管理器实例
es_index_manager = ESIndexManager()
