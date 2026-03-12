"""
检索相关的 Pydantic Schema
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator, root_validator


class KBConfig(BaseModel):
    """单个知识库的检索配置"""
    kb_id: str = Field(..., description="知识库ID")
    top_k: int = Field(default=5, description="该知识库返回结果数", ge=1, le=50)
    min_score: float = Field(default=0.0, description="最低置信度阈值", ge=0.0, le=1.0)
    vector_boost: float = Field(default=0.7, description="向量检索权重", ge=0.0, le=1.0)
    text_boost: float = Field(default=0.3, description="全文检索权重", ge=0.0, le=1.0)
    
    @validator('text_boost')
    def validate_boost_sum(cls, v, values):
        """验证权重总和"""
        if 'vector_boost' in values:
            total = values['vector_boost'] + v
            if abs(total - 1.0) > 0.01:
                raise ValueError(f"vector_boost + text_boost 必须等于 1.0")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "kb_id": "kb_1db122e7",
                "top_k": 3,
                "min_score": 0.7,
                "vector_boost": 0.8,
                "text_boost": 0.2
            }
        }


class SearchRequest(BaseModel):
    """知识库检索请求"""
    query: str = Field(..., description="查询文本", min_length=1, max_length=500)
    kb_configs: List[KBConfig] = Field(..., description="知识库配置列表", min_items=1)
    mode: str = Field(default="knn_query", description="检索模式: knn_query 或 rrf")
    use_rerank: bool = Field(default=False, description="是否启用 Rerank 重排序（全局）")
    rerank_top_k: Optional[int] = Field(default=None, description="Rerank 返回前 N 个结果", ge=1, le=50)
    
    @validator('mode')
    def validate_mode(cls, v):
        """验证检索模式"""
        if v not in ["knn_query", "rrf"]:
            raise ValueError("mode 必须是 'knn_query' 或 'rrf'")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "query": "氢能报告",
                "kb_configs": [
                    {
                        "kb_id": "kb_1db122e7",
                        "top_k": 3,
                        "min_score": 0.7,
                        "vector_boost": 0.7,
                        "text_boost": 0.3
                    }
                ],
                "mode": "knn_query",
                "use_rerank": True,
                "rerank_top_k": 10
            }
        }


class SearchResultItem(BaseModel):
    """单个检索结果"""
    chunk_id: int = Field(..., description="分块ID")
    doc_id: int = Field(..., description="文档ID")
    kb_id: str = Field(..., description="知识库ID")
    chunk_text: str = Field(..., description="分块文本内容")
    chunk_index: int = Field(..., description="分块索引")
    score: float = Field(..., description="最终相关性分数 (0-1)，Rerank 后为 Rerank 分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    # 可选的增强字段
    original_score: Optional[float] = Field(None, description="ES 原始归一化分数（Rerank 模式下）")
    doc_name: Optional[str] = Field(None, description="文档名称")
    kb_name: Optional[str] = Field(None, description="知识库名称")


class SearchResponse(BaseModel):
    """检索响应"""
    success: bool = Field(default=True, description="是否成功")
    query: str = Field(..., description="原始查询")
    mode: str = Field(..., description="检索模式")
    use_rerank: bool = Field(default=False, description="是否使用了 Rerank 重排序")
    rerank_model: Optional[str] = Field(None, description="Rerank 模型名称（如使用）")
    vector_boost: float = Field(..., description="实际使用的向量权重")
    text_boost: float = Field(..., description="实际使用的文本权重")
    total: int = Field(..., description="返回结果总数")
    results: List[SearchResultItem] = Field(..., description="检索结果列表")
    warning: Optional[str] = Field(None, description="警告信息（如 ES 候选数不足）")
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "query": "Python编程",
                "mode": "knn_query",
                "vector_boost": 0.7,
                "text_boost": 0.3,
                "total": 5,
                "results": [
                    {
                        "chunk_id": 1,
                        "doc_id": 3,
                        "kb_id": "kb_1db122e7",
                        "chunk_text": "Python是一门优秀的编程语言...",
                        "chunk_index": 0,
                        "score": 0.8523,
                        "metadata": {},
                        "doc_name": "Python教程.pdf",
                        "kb_name": "技术文档库"
                    }
                ]
            }
        }
