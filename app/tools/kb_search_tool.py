"""
知识库检索工具

允许 AI 智能体自主从知识库中检索相关信息
"""
from typing import Optional, List, Dict, Any, Type
from pydantic import Field

from app.tools.base import BaseTool, ToolInput, ToolMetadata
from app.services.kb_retrieval_service import KBRetrievalService
from app.db.session import SessionLocal
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class KBSearchInput(ToolInput):
    """知识库检索输入参数"""
    query: str = Field(..., description="要检索的问题或关键词，尽量具体明确")
    kb_ids: Optional[List[str]] = Field(
        default=None,
        description="知识库ID列表，不传则搜索所有可用的知识库"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="返回的最大结果数，默认5个"
    )


class KBSearchTool(BaseTool):
    """
    知识库检索工具
    
    功能：
    - 从知识库中检索与用户问题相关的文档内容
    - 支持指定知识库或搜索所有知识库
    - 返回格式化的知识库内容供 LLM 参考
    
    使用场景：
    - 用户问题涉及特定领域知识
    - 需要引用文档或资料
    - 需要基于已有知识库回答问题
    """
    
    def get_metadata(self) -> ToolMetadata:
        """工具元数据"""
        return ToolMetadata(
            name="kb_search",
            display_name="知识库检索",
            description="""从知识库中检索相关信息。

适用场景：
1. 用户明确提到某个知识库或文档
2. 问题涉及专业领域知识（如编程、法律、医学等）
3. 需要引用具体的资料或数据
4. 用户询问"文档中说了什么"、"资料显示什么"等

参数说明：
- query: 要检索的问题或关键词（必填）
- kb_ids: 知识库ID列表（可选，不传则搜索所有）
- max_results: 返回结果数量（默认5个）

返回：格式化的知识库内容，包含来源文档信息""",
            category="knowledge",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        """返回输入参数schema"""
        return KBSearchInput
    
    async def _run(self, query: str, kb_ids: Optional[List[str]] = None, max_results: int = 5) -> Dict[str, Any]:
        """
        执行知识库检索
        
        Args:
            query: 检索查询
            kb_ids: 知识库ID列表
            max_results: 最大结果数
            
        Returns:
            Dict[str, Any]: 包含 success, result, error 等字段
        """
        try:
            logger.info(f"🔍 知识库检索工具被调用: query='{query[:50]}...', kb_ids={kb_ids}, max_results={max_results}")
            
            # 创建数据库会话
            db = SessionLocal()
            try:
                kb_service = KBRetrievalService(db)
                
                # 如果没有指定知识库，获取所有可用的知识库
                if not kb_ids:
                    from app.services.knowledge_base_service import KnowledgeBaseService
                    kb_mgmt_service = KnowledgeBaseService(db)
                    all_kbs = kb_mgmt_service.list_knowledge_bases(status="active", limit=100)
                    kb_ids = [kb.id for kb in all_kbs]
                    
                    if not kb_ids:
                        logger.warning("系统中没有可用的知识库")
                        return {
                            "success": False,
                            "result": "系统中暂无可用的知识库，无法进行检索。请先创建并上传文档到知识库。",
                            "error": "no_knowledge_base_available"
                        }
                    
                    logger.info(f"未指定知识库，将搜索所有 {len(kb_ids)} 个可用知识库")
                
                # 执行检索
                result = kb_service.retrieve_context(
                    query=query,
                    kb_ids=kb_ids,
                    max_results=max_results
                )
                
                if not result["context"]:
                    logger.info(f"未检索到相关内容: query='{query}'")
                    return {
                        "success": True,
                        "result": f"在知识库中未找到与「{query}」相关的内容。\n\n可能原因：\n1. 知识库中没有相关文档\n2. 查询关键词不匹配\n3. 文档尚未上传或处理",
                        "error": None,
                        "metadata": {
                            "sources_count": 0,
                            "kb_names": result["kb_names"]
                        }
                    }
                
                # 构建返回结果
                response_parts = [
                    f"✅ 从知识库检索到 {len(result['sources'])} 个相关文档：",
                    f"📚 知识库：{', '.join(result['kb_names'])}",
                    "",
                    result["context"]
                ]
                
                response = "\n".join(response_parts)
                
                logger.info(f"✅ 检索成功: 找到 {len(result['sources'])} 个文档，来自 {len(result['kb_names'])} 个知识库")
                
                return {
                    "success": True,
                    "result": response,
                    "error": None,
                    "metadata": {
                        "sources_count": len(result['sources']),
                        "kb_names": result['kb_names'],
                        "sources": result['sources']
                    }
                }
                
            finally:
                db.close()
                
        except Exception as e:
            error_msg = f"知识库检索失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": error_msg
            }
