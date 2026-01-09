"""
SQLAlchemy 数据库模型基类

提供所有 ORM 模型的基础类和通用混入
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base, declared_attr
import re

# SQLAlchemy Base 类
Base = declarative_base()


class TimestampMixin:
    """
    时间戳混入类
    
    为模型自动添加创建时间和更新时间字段
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )


class TableNameMixin:
    """
    表名混入类
    
    自动根据类名生成表名（小写 + 下划线）
    """
    @declared_attr
    def __tablename__(cls):
        # UserProfile -> user_profile
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name
