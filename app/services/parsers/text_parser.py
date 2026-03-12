"""
纯文本文件解析器

支持多种编码的纯文本文件
"""
from typing import Dict, List
from pathlib import Path

from app.services.parsers.base_parser import BaseParser
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class TextParser(BaseParser):
    """
    纯文本文件解析器
    
    支持多种编码格式
    """
    
    def get_supported_extensions(self) -> List[str]:
        """支持 TXT 格式"""
        return ["txt", "text"]
    
    def extract_text(self, file_path: Path) -> str:
        """
        从文本文件中读取内容
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            str: 文件内容
        """
        self.validate_file(file_path)
        
        try:
            logger.info(f"开始读取文本文件: {file_path.name}")
            
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    logger.info(f"✅ 文本文件读取成功 (编码: {encoding}): {len(text)} 字符")
                    return text
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用 errors='ignore'
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            logger.warning(f"⚠️  使用 UTF-8 + ignore 模式读取: {len(text)} 字符")
            return text
                
        except Exception as e:
            logger.error(f"❌ 文本文件读取失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"文本文件读取失败: {str(e)}") from e
    
    def extract_with_structure(self, file_path: Path) -> Dict:
        """
        提取文本文件的结构化信息
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            dict: 包含文本和元数据
        """
        self.validate_file(file_path)
        
        text = self.extract_text(file_path)
        
        # 统计基本信息
        lines = text.split('\n')
        line_count = len(lines)
        char_count = len(text)
        
        metadata = {
            "file_type": "txt",
            "line_count": line_count,
            "char_count": char_count,
            "file_size": file_path.stat().st_size
        }
        
        return {
            "text": text,
            "pages": [{"page": 1, "text": text}],
            "metadata": metadata
        }
