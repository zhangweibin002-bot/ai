"""
SQLAlchemy 数据库模型基类

提供所有 ORM 模型的基础类和通用混入
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base, declared_attr

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
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name


class BaseModel(Base, TimestampMixin, TableNameMixin):
    """
    基础模型类
    
    所有 ORM 模型应继承此类，自动包含：
    - id 主键
    - created_at 创建时间
    - updated_at 更新时间
    - 自动表名
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    def to_dict(self):
        """将模型转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"
