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
    
    @property
    def DATABASE_URL(self) -> str:
        """生成数据库连接 URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
