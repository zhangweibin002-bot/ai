"""
Markdown 文档解析器

解析 Markdown 文件
"""
from typing import Dict, List
from pathlib import Path

from app.services.parsers.text_parser import TextParser
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class MarkdownParser(TextParser):
    """
    Markdown 文档解析器
    
    继承自 TextParser，因为 Markdown 本质上也是文本文件
    """
    
    def get_supported_extensions(self) -> List[str]:
        """支持 MD 和 Markdown 格式"""
        return ["md", "markdown"]
    
    def extract_text(self, file_path: Path) -> str:
        """
        从 Markdown 文件中读取内容
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            str: Markdown 文本内容（保留格式）
        """
        self.validate_file(file_path)
        
        logger.info(f"开始读取 Markdown: {file_path.name}")
        text = super().extract_text(file_path)
        logger.info(f"✅ Markdown 读取完成: {len(text)} 字符")
        
        # 注意：这里保留 Markdown 语法
        # 如果需要移除 Markdown 语法，可以使用 markdown 库
        return text
    
    def extract_with_structure(self, file_path: Path) -> Dict:
        """
        提取 Markdown 的结构化信息
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            dict: 包含文本、章节信息和元数据
        """
        self.validate_file(file_path)
        
        text = self.extract_text(file_path)
        
        # 解析 Markdown 结构（标题等）
        sections = self._parse_sections(text)
        
        metadata = {
            "file_type": "markdown",
            "section_count": len(sections),
            "char_count": len(text),
            "file_size": file_path.stat().st_size
        }
        
        return {
            "text": text,
            "pages": [{"page": 1, "text": text}],
            "sections": sections,
            "metadata": metadata
        }
    
    def _parse_sections(self, text: str) -> List[Dict]:
        """
        解析 Markdown 章节结构
        
        Args:
            text: Markdown 文本
            
        Returns:
            List[Dict]: 章节列表
        """
        import re
        
        sections = []
        lines = text.split('\n')
        
        # 匹配标题行 (# 标题)
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        
        for i, line in enumerate(lines):
            match = heading_pattern.match(line)
            if match:
                level = len(match.group(1))  # # 数量
                title = match.group(2)
                sections.append({
                    "level": level,
                    "title": title,
                    "line": i + 1
                })
        
        return sections
