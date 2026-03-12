"""
文档解析器基类

定义文档解析器的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from pathlib import Path

from app.core.logger import setup_logger

logger = setup_logger(__name__)


class BaseParser(ABC):
    """
    文档解析器基类
    
    所有文档解析器都应该继承此类并实现其抽象方法
    """
    
    def __init__(self):
        """初始化解析器"""
        self.name = self.__class__.__name__
    
    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """
        提取纯文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 提取的文本内容
        """
        pass
    
    @abstractmethod
    def extract_with_structure(self, file_path: Path) -> Dict:
        """
        提取带结构信息的文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 包含文本和结构信息
            {
                "text": "全文",
                "pages": [
                    {"page": 1, "text": "页面文本"},
                    ...
                ],
                "metadata": {...}
            }
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名列表
        
        Returns:
            List[str]: 支持的扩展名列表
        """
        pass
    
    def is_supported(self, file_path: Path) -> bool:
        """
        检查文件是否支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持
        """
        ext = file_path.suffix.lstrip('.').lower()
        return ext in self.get_supported_extensions()
    
    def validate_file(self, file_path: Path) -> None:
        """
        验证文件是否存在且支持
        
        Args:
            file_path: 文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件类型不支持
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not self.is_supported(file_path):
            raise ValueError(
                f"不支持的文件类型: {file_path.suffix}，"
                f"支持的类型: {self.get_supported_extensions()}"
            )
