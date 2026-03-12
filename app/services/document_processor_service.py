"""
文档处理服务

负责从各种格式文件中提取文本内容
使用解析器工厂模式
"""
from typing import Optional, Dict, List
from pathlib import Path
import re

from app.core.logger import setup_logger
from app.services.parsers import (
    BaseParser,
    PDFParser,
    DOCXParser,
    TextParser,
    MarkdownParser,
    HTMLParser
)

logger = setup_logger(__name__)


class DocumentProcessorService:
    """
    文档处理服务
    
    使用解析器工厂模式，支持多种文档格式：
    - PDF (PyMuPDF)
    - Word/DOCX (python-docx)
    - TXT
    - Markdown
    - HTML (BeautifulSoup)
    """
    
    def __init__(self):
        """初始化服务，注册所有解析器"""
        # 解析器注册表
        self._parsers: Dict[str, BaseParser] = {}
        
        # 注册所有解析器
        self._register_parsers()
        
        logger.info(f"✅ 文档处理服务初始化完成，支持 {len(self.get_supported_types())} 种文件类型")
    
    def _register_parsers(self):
        """注册所有可用的解析器"""
        parsers = [
            PDFParser(),
            DOCXParser(),
            TextParser(),
            MarkdownParser(),
            HTMLParser()
        ]
        
        for parser in parsers:
            for ext in parser.get_supported_extensions():
                self._parsers[ext.lower()] = parser
                logger.debug(f"注册解析器: {ext} -> {parser.__class__.__name__}")
    
    def _get_parser(self, file_type: str) -> BaseParser:
        """
        根据文件类型获取对应的解析器
        
        Args:
            file_type: 文件类型/扩展名
            
        Returns:
            BaseParser: 解析器实例
            
        Raises:
            ValueError: 不支持的文件类型
        """
        file_type = file_type.lower()
        
        if file_type not in self._parsers:
            raise ValueError(
                f"不支持的文件类型: {file_type}\n"
                f"支持的类型: {', '.join(self.get_supported_types())}"
            )
        
        return self._parsers[file_type]
    
    def extract_text(self, file_path: str, file_type: Optional[str] = None) -> str:
        """
        从文件中提取纯文本
        
        Args:
            file_path: 文件路径
            file_type: 文件类型（可选，自动检测）
            
        Returns:
            str: 提取的文本内容
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 自动检测文件类型
        if not file_type:
            file_type = file_path.suffix.lstrip('.').lower()
        
        logger.info(f"开始解析文档: {file_path.name}, 类型: {file_type}")
        
        # 获取对应的解析器
        parser = self._get_parser(file_type)
        
        # 提取文本
        text = parser.extract_text(file_path)
        
        # 清理文本
        text = self._clean_text(text)
        
        logger.info(f"✅ 文档解析完成: 提取 {len(text)} 字符")
        return text
    
    def extract_with_structure(
        self, 
        file_path: str, 
        file_type: Optional[str] = None
    ) -> Dict:
        """
        提取带结构信息的文本
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
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
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 自动检测文件类型
        if not file_type:
            file_type = file_path.suffix.lstrip('.').lower()
        
        logger.info(f"开始结构化解析: {file_path.name}")
        
        # 获取对应的解析器
        parser = self._get_parser(file_type)
        
        # 提取结构化信息
        result = parser.extract_with_structure(file_path)
        
        # 清理文本
        if "text" in result:
            result["text"] = self._clean_text(result["text"])
        
        logger.info(f"✅ 结构化解析完成: {len(result.get('pages', []))} 页")
        return result
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本
        
        - 移除多余空白
        - 统一换行符
        - 移除特殊字符
        """
        if not text:
            return ""
        
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除连续空行（保留最多2个换行）
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 移除行首行尾空白
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # 移除多余空格
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()
    
    def get_supported_types(self) -> List[str]:
        """
        获取支持的文件类型列表
        
        Returns:
            List[str]: 支持的文件类型
        """
        return list(self._parsers.keys())
    
    def is_supported(self, file_type: str) -> bool:
        """
        检查文件类型是否支持
        
        Args:
            file_type: 文件类型
            
        Returns:
            bool: 是否支持
        """
        return file_type.lower() in self._parsers
    
    def get_parser_info(self) -> Dict:
        """
        获取所有解析器的信息
        
        Returns:
            Dict: 解析器信息
        """
        info = {}
        
        for file_type, parser in self._parsers.items():
            parser_name = parser.__class__.__name__
            
            if parser_name not in info:
                info[parser_name] = {
                    "name": parser_name,
                    "supported_extensions": parser.get_supported_extensions()
                }
        
        return info


# 单例实例
document_processor = DocumentProcessorService()
