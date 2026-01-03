from pydantic_settings import BaseSettings
from pathlib import Path
class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_URL: str
    OPENAI_MODEL_NAMES: str = 'qwen-plus'
    APP_NAME: str = "ai_agents"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"



    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        env_file_encoding="utf-8"



settings = Settings()
print(settings.OPENAI_API_KEY)
print(settings.APP_NAME)
print(settings.LOG_LEVEL)
print(settings.LOG_DIR)
print(settings.OPENAI_URL)
print(settings.OPENAI_MODEL_NAMES)
