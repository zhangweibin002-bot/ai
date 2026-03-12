"""
文档分块服务

负责将长文本拆分为可管理的分块
"""
from typing import List, Dict, Optional
from enum import Enum

from app.core.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


class ChunkStrategy(str, Enum):
    """分块策略枚举"""
    FIXED = "fixed"  # 固定长度
    RECURSIVE = "recursive"  # 递归分块（推荐）
    SEMANTIC = "semantic"  # 语义分块（高级）
    SENTENCE = "sentence"  # 按句子分块


class ChunkingService:
    """
    文档分块服务
    
    将长文本拆分为适合向量化和检索的分块
    """
    
    def __init__(
        self,
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    ):
        """
        初始化分块服务
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        logger.info(f"分块服务初始化: size={chunk_size}, overlap={chunk_overlap}")
    
    def chunk_text(
        self,
        text: str,
        strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        将文本分块
        
        Args:
            text: 待分块的文本
            strategy: 分块策略
            metadata: 额外的元数据
            
        Returns:
            List[Dict]: 分块列表
            [
                {
                    "text": "分块内容",
                    "index": 0,
                    "chunk_size": 512,
                    "start_position": 0,
                    "end_position": 512,
                    "metadata": {...}
                },
                ...
            ]
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回空列表")
            return []
        
        logger.info(f"开始分块: 文本长度={len(text)}, 策略={strategy}")
        
        # 根据策略选择分块方法
        if strategy == ChunkStrategy.FIXED:
            chunks = self._chunk_fixed(text)
        elif strategy == ChunkStrategy.RECURSIVE:
            chunks = self._chunk_recursive(text)
        elif strategy == ChunkStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(text)
        elif strategy == ChunkStrategy.SEMANTIC:
            chunks = self._chunk_semantic(text)
        else:
            logger.warning(f"未知策略 {strategy}，使用递归分块")
            chunks = self._chunk_recursive(text)
        
        # 添加元数据
        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_dict = {
                "text": chunk_text,
                "index": i,
                "chunk_size": len(chunk_text),
                "start_position": text.find(chunk_text) if chunk_text in text else -1,
                "end_position": -1,
                "metadata": metadata or {}
            }
            
            # 计算结束位置
            if chunk_dict["start_position"] >= 0:
                chunk_dict["end_position"] = chunk_dict["start_position"] + len(chunk_text)
            
            result.append(chunk_dict)
        
        logger.info(f"✅ 分块完成: 生成 {len(result)} 个分块")
        return result
    
    def _chunk_fixed(self, text: str) -> List[str]:
        """
        固定长度分块
        
        简单的滑动窗口方式
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk)
            
            # 移动窗口，考虑重叠
            start = end - self.chunk_overlap
            
            # 防止无限循环
            if self.chunk_overlap >= self.chunk_size:
                start = end
        
        return chunks
    
    def _chunk_recursive(self, text: str) -> List[str]:
        """
        递归分块（推荐）
        
        尝试在合适的分隔符处分割，保持语义完整性
        分隔符优先级: 段落 > 句子 > 词
        """
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=[
                    "\n\n",  # 段落
                    "\n",    # 行
                    "。",    # 中文句号
                    "！",    # 中文感叹号
                    "？",    # 中文问号
                    ".",     # 英文句号
                    "!",     # 英文感叹号
                    "?",     # 英文问号
                    "；",    # 中文分号
                    ";",     # 英文分号
                    "，",    # 中文逗号
                    ",",     # 英文逗号
                    " ",     # 空格
                    ""       # 字符
                ]
            )
            
            chunks = splitter.split_text(text)
            return chunks
            
        except ImportError:
            logger.warning("langchain_text_splitters 未安装，回退到固定分块")
            return self._chunk_fixed(text)
        except Exception as e:
            logger.error(f"递归分块失败: {str(e)}，回退到固定分块")
            return self._chunk_fixed(text)
    
    def _chunk_by_sentence(self, text: str) -> List[str]:
        """
        按句子分块
        
        将文本按句子分割，然后组合成合适大小的分块
        """
        import re
        
        # 句子分隔正则（中英文）
        sentence_pattern = r'[。！？.!?]+[\s]*'
        
        # 分割句子
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            # 如果单个句子就超过 chunk_size，直接作为一个 chunk
            if sentence_len > self.chunk_size:
                # 先保存当前 chunk
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # 大句子单独成块
                chunks.append(sentence)
                continue
            
            # 如果加上当前句子会超过 chunk_size
            if current_length + sentence_len > self.chunk_size:
                # 保存当前 chunk
                if current_chunk:
                    chunks.append("".join(current_chunk))
                
                # 开始新 chunk（考虑重叠）
                if self.chunk_overlap > 0 and current_chunk:
                    # 保留最后几个句子作为重叠
                    overlap_sentences = []
                    overlap_length = 0
                    for prev_sentence in reversed(current_chunk):
                        if overlap_length + len(prev_sentence) <= self.chunk_overlap:
                            overlap_sentences.insert(0, prev_sentence)
                            overlap_length += len(prev_sentence)
                        else:
                            break
                    
                    current_chunk = overlap_sentences
                    current_length = overlap_length
                else:
                    current_chunk = []
                    current_length = 0
            
            # 添加当前句子
            current_chunk.append(sentence)
            current_length += sentence_len
        
        # 保存最后一个 chunk
        if current_chunk:
            chunks.append("".join(current_chunk))
        
        return chunks
    
    def _chunk_semantic(self, text: str) -> List[str]:
        """
        语义分块（高级）
        
        基于语义相似度进行分块，需要向量化支持
        当前暂时回退到递归分块
        """
        logger.warning("语义分块暂未实现，回退到递归分块")
        return self._chunk_recursive(text)
    
    def chunk_with_pages(
        self,
        pages: List[Dict],
        strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    ) -> List[Dict]:
        """
        对带页码的文本进行分块
        
        Args:
            pages: 页面列表 [{"page": 1, "text": "..."}]
            strategy: 分块策略
            
        Returns:
            List[Dict]: 分块列表（包含页码信息）
        """
        all_chunks = []
        
        for page_info in pages:
            page_num = page_info.get("page", 0)
            page_text = page_info.get("text", "")
            
            if not page_text.strip():
                continue
            
            # 对单页文本分块
            chunks = self.chunk_text(
                text=page_text,
                strategy=strategy,
                metadata={"source_page": page_num}
            )
            
            # 添加页码信息
            for chunk in chunks:
                chunk["start_page"] = page_num
                chunk["end_page"] = page_num
                all_chunks.append(chunk)
        
        # 重新编号
        for i, chunk in enumerate(all_chunks):
            chunk["index"] = i
        
        logger.info(f"✅ 跨页分块完成: {len(pages)} 页 → {len(all_chunks)} 个分块")
        return all_chunks
    
    def estimate_token_count(self, text: str) -> int:
        """
        估算文本的 token 数量
        
        粗略估算：中文按字符数，英文按单词数 * 1.3
        
        Args:
            text: 文本
            
        Returns:
            int: 估算的 token 数
        """
        if not text:
            return 0
        
        # 统计中文字符
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        
        # 统计英文单词
        import re
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        # 粗略估算
        estimated_tokens = chinese_chars + int(english_words * 1.3)
        
        return estimated_tokens
    
    def validate_chunks(self, chunks: List[Dict]) -> Dict:
        """
        验证分块质量
        
        Args:
            chunks: 分块列表
            
        Returns:
            Dict: 验证报告
        """
        if not chunks:
            return {
                "valid": False,
                "error": "分块列表为空"
            }
        
        total_chunks = len(chunks)
        total_chars = sum(chunk["chunk_size"] for chunk in chunks)
        avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0
        
        # 检查是否有过大或过小的分块
        oversized = [c for c in chunks if c["chunk_size"] > self.chunk_size * 1.5]
        undersized = [c for c in chunks if c["chunk_size"] < self.chunk_size * 0.1]
        
        report = {
            "valid": True,
            "total_chunks": total_chunks,
            "total_characters": total_chars,
            "avg_chunk_size": round(avg_chunk_size, 2),
            "max_chunk_size": max(c["chunk_size"] for c in chunks),
            "min_chunk_size": min(c["chunk_size"] for c in chunks),
            "oversized_chunks": len(oversized),
            "undersized_chunks": len(undersized),
            "warnings": []
        }
        
        if oversized:
            report["warnings"].append(f"发现 {len(oversized)} 个过大分块（超过 {self.chunk_size * 1.5} 字符）")
        
        if undersized:
            report["warnings"].append(f"发现 {len(undersized)} 个过小分块（小于 {self.chunk_size * 0.1} 字符）")
        
        return report


# 单例实例（使用默认配置）
chunking_service = ChunkingService()
