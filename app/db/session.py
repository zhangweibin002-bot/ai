"""
数据库会话管理

提供数据库连接和会话
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # 自动检测断开的连接
    pool_recycle=3600,       # 1小时回收连接
    echo=False,              # 设为 True 可打印 SQL 语句
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False, # 决定数据库操作是否自动提交事务，False必须手动执行db.commit()生效 db.commit()导入数据库 True 自动提交
    autoflush=False,# 控制会话是否在查询前自动把未提交的修改刷新到数据库 False → 不会自动刷新，需要手动 db.flush()（或者 commit 会自动 flush）
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    
    用于 FastAPI 依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    
    创建所有表（如果不存在）
    """
    from app.models.base import Base
    from app.models import chat_history    # 导入模型以注册
    from app.models import agent_config    # 导入智能体配置模型
    from app.models import tool_execution  # 导入工具执行记录模型
    
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")
