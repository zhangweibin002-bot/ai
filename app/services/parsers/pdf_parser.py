"""
PDF 文档解析器

使用 PyMuPDF (fitz) 解析 PDF 文件
"""
from typing import Dict, List
from pathlib import Path

from app.services.parsers.base_parser import BaseParser
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class PDFParser(BaseParser):
    """
    PDF 文档解析器
    
    使用 PyMuPDF (fitz) 库进行解析
    """
    
    def get_supported_extensions(self) -> List[str]:
        """支持 PDF 格式"""
        return ["pdf"]
    
    def extract_text(self, file_path: Path) -> str:
        """
        从 PDF 中提取纯文本
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            str: 提取的文本内容
        """
        self.validate_file(file_path)
        
        try:
            import fitz  # PyMuPDF
            
            logger.info(f"开始解析 PDF: {file_path.name}")
            text_parts = []
            
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(text)
                
                logger.info(f"✅ PDF 解析完成: {len(doc)} 页, {len(''.join(text_parts))} 字符")
            
            return "\n\n".join(text_parts)
            
        except ImportError:
            raise ImportError(
                "需要安装 PyMuPDF: pip install pymupdf\n"
                "或者在 requirements_kb.txt 中已包含，请运行: pip install -r requirements_kb.txt"
            )
        except Exception as e:
            logger.error(f"❌ PDF 解析失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"PDF 解析失败: {str(e)}") from e
    
    def extract_with_structure(self, file_path: Path) -> Dict:
        """
        提取 PDF 的结构化信息
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            dict: 包含文本、页面信息和元数据
        """
        self.validate_file(file_path)
        
        try:
            import fitz
            
            logger.info(f"开始结构化解析 PDF: {file_path.name}")
            
            pages = []
            full_text_parts = []
            
            with fitz.open(file_path) as doc:
                # 提取页面内容
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text()
                    if text.strip():
                        pages.append({
                            "page": page_num,
                            "text": text,
                            "char_count": len(text)
                        })
                        full_text_parts.append(text)
                
                # 提取元数据
                metadata = {
                    "file_type": "pdf",
                    "page_count": len(doc),
                    "has_toc": len(doc.get_toc()) > 0,
                    "is_encrypted": doc.is_encrypted,
                    "is_pdf": doc.is_pdf
                }
                
                # 尝试提取 PDF 元信息
                try:
                    pdf_metadata = doc.metadata
                    if pdf_metadata:
                        metadata.update({
                            "title": pdf_metadata.get("title", ""),
                            "author": pdf_metadata.get("author", ""),
                            "subject": pdf_metadata.get("subject", ""),
                            "creator": pdf_metadata.get("creator", "")
                        })
                except Exception:
                    pass
            
            logger.info(f"✅ PDF 结构化解析完成: {len(pages)} 页")
            
            return {
                "text": "\n\n".join(full_text_parts),
                "pages": pages,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ PDF 结构化解析失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"PDF 结构化解析失败: {str(e)}") from e
