"""
应用配置

从环境变量和 .env 文件读取配置
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # ===== OpenAI/LLM 配置 =====
    OPENAI_API_KEY: str
    OPENAI_URL: str
    OPENAI_MODEL_NAMES: str = 'qwen-plus'
    
    # ===== 应用配置 =====
    APP_NAME: str = "ai_agents"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    # ===== MySQL 数据库配置 =====
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "ai_agent"

    # ===== Ollama API 配置 =====
    OLLAMA_API_KEY: str
    
    # ===== 高德地图 API 配置 =====
    GAODE_API_KEY: str = "03b1dacd0f6a0724d6621fb7c1a7c4e3"
    
    # ===== Elasticsearch 配置 =====
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_SCHEME: str = "http"
    ES_USERNAME: Optional[str] = None
    ES_PASSWORD: Optional[str] = None
    ES_API_KEY: Optional[str] = None
    ES_INDEX_PREFIX: str = "kb_vectors_"  # 索引前缀
    ES_TIMEOUT: int = 30  # 超时时间（秒）
    ES_MAX_RETRIES: int = 3  # 最大重试次数
    ES_VECTOR_DIMENSIONS: int = 1024  # 向量维度（Jina v3）
    
    # ===== Jina Embeddings API 配置 =====
    JINA_API_KEY: str = "jina_266f4b8fa6914a5cb26a93264c522ffcTkV4OzObFFHBWdRoCtTyi-xNaVUZ"
    JINA_API_URL: str = "https://api.jina.ai/v1/embeddings"
    JINA_MODEL_NAME: str = "jina-embeddings-v3"
    JINA_TASK_TYPE: str = "text-matching"  # retrieval.query, retrieval.passage, text-matching
    JINA_DIMENSIONS: int = 1024  # jina-embeddings-v3 默认维度
    JINA_BATCH_SIZE: int = 32  # 批量处理大小
    JINA_TIMEOUT: int = 30  # API 超时时间（秒）
    JINA_MAX_RETRIES: int = 3  # 最大重试次数
    JINA_VERIFY_SSL: bool = False  # 是否验证 SSL 证书（False 可避免 SSL 错误）    
    # ===== Rerank 重排序配置 =====
    RERANK_ENABLED: bool = True  # 是否启用 Rerank（全局开关）
    RERANK_API_KEY: str = "sk-35bb2130429a406cb843622f840d0e78"  # 阿里云百练 API Key（请配置）
    RERANK_API_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    RERANK_MODEL_NAME: str = "qwen3-rerank"  # 模型名称
    RERANK_TOP_N: int = 10  # Rerank 返回的最终结果数（默认）
    RERANK_RECALL_MULTIPLIER: int = 3  # ES 召回倍数（召回 top_k * multiplier 个候选）
    RERANK_TIMEOUT: int = 30  # API 超时时间（秒）
    RERANK_MAX_RETRIES: int = 2  # 最大重试次数    
    # ===== 文档处理配置 =====
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = ["pdf", "docx", "txt", "md", "html"]
    
    # 分块配置
    DEFAULT_CHUNK_SIZE: int = 512  # 默认分块大小（字符）
    DEFAULT_CHUNK_OVERLAP: int = 50  # 默认重叠大小
    DEFAULT_CHUNK_STRATEGY: str = "recursive"  # 默认分块策略

    
    
    # ===== Celery 配置（可选）=====
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


    
    @property
    def DATABASE_URL(self) -> str:
        """生成数据库连接 URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    @property
    def ES_URL(self) -> str:
        """完整的 ES 连接 URL"""
        return f"{self.ES_SCHEME}://{self.ES_HOST}:{self.ES_PORT}"

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
