"""
HTML 文档解析器

使用 BeautifulSoup 解析 HTML 文件
"""
from typing import Dict, List
from pathlib import Path

from app.services.parsers.base_parser import BaseParser
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class HTMLParser(BaseParser):
    """
    HTML 文档解析器
    
    使用 BeautifulSoup 提取纯文本
    """
    
    def get_supported_extensions(self) -> List[str]:
        """支持 HTML 和 HTM 格式"""
        return ["html", "htm"]
    
    def extract_text(self, file_path: Path) -> str:
        """
        从 HTML 文件中提取纯文本
        
        Args:
            file_path: HTML 文件路径
            
        Returns:
            str: 提取的纯文本内容
        """
        self.validate_file(file_path)
        
        try:
            from bs4 import BeautifulSoup
            
            logger.info(f"开始解析 HTML: {file_path.name}")
            
            # 读取 HTML 内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # 使用 BeautifulSoup 解析
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除 script 和 style 标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 提取文本
            text = soup.get_text()
            
            # 清理多余空白
            import re
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            logger.info(f"✅ HTML 解析完成: {len(text)} 字符")
            
            return text
            
        except ImportError:
            raise ImportError(
                "需要安装 beautifulsoup4: pip install beautifulsoup4\n"
                "或者在 requirements_kb.txt 中已包含，请运行: pip install -r requirements_kb.txt"
            )
        except Exception as e:
            logger.error(f"❌ HTML 解析失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"HTML 解析失败: {str(e)}") from e
    
    def extract_with_structure(self, file_path: Path) -> Dict:
        """
        提取 HTML 的结构化信息
        
        Args:
            file_path: HTML 文件路径
            
        Returns:
            dict: 包含文本、元素信息和元数据
        """
        self.validate_file(file_path)
        
        try:
            from bs4 import BeautifulSoup
            
            logger.info(f"开始结构化解析 HTML: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取纯文本
            text = self.extract_text(file_path)
            
            # 提取标题层级
            headings = []
            for i in range(1, 7):  # h1 到 h6
                for heading in soup.find_all(f'h{i}'):
                    headings.append({
                        "level": i,
                        "text": heading.get_text().strip()
                    })
            
            # 提取链接
            links = []
            for link in soup.find_all('a', href=True):
                links.append({
                    "text": link.get_text().strip(),
                    "href": link['href']
                })
            
            # 提取元数据
            metadata = {
                "file_type": "html",
                "heading_count": len(headings),
                "link_count": len(links),
                "char_count": len(text)
            }
            
            # 尝试提取 HTML meta 标签
            try:
                title = soup.find('title')
                if title:
                    metadata["title"] = title.get_text().strip()
                
                for meta in soup.find_all('meta'):
                    name = meta.get('name', '')
                    property_name = meta.get('property', '')
                    content = meta.get('content', '')
                    
                    if name == 'description':
                        metadata["description"] = content
                    elif name == 'keywords':
                        metadata["keywords"] = content
                    elif name == 'author':
                        metadata["author"] = content
                    elif property_name == 'og:title':
                        metadata["og_title"] = content
            except Exception:
                pass
            
            logger.info(f"✅ HTML 结构化解析完成: {len(headings)} 个标题, {len(links)} 个链接")
            
            return {
                "text": text,
                "pages": [{"page": 1, "text": text}],
                "headings": headings,
                "links": links[:20],  # 只保留前20个链接
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ HTML 结构化解析失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"HTML 结构化解析失败: {str(e)}") from e
