"""
工具基类
所有自定义工具必须继承此类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LangChainBaseTool


class ToolInput(BaseModel):
    """工具输入参数的基类"""
    pass


class ToolMetadata(BaseModel):
    """工具元数据"""
    name: str = Field(..., description="工具名称（唯一标识）")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="工具描述（AI 会根据此描述决定是否调用）")
    category: str = Field(default="general", description="工具分类")
    version: str = Field(default="1.0.0", description="版本号")
    author: Optional[str] = Field(default=None, description="作者")
    is_active: bool = Field(default=True, description="是否启用")
    requires_approval: bool = Field(default=False, description="是否需要用户批准")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "calculator",
                "display_name": "计算器",
                "description": "执行数学计算，支持基本的四则运算",
                "category": "math",
                "version": "1.0.0"
            }
        }


class BaseTool(ABC):
    """
    工具抽象基类
    所有自定义工具都必须继承此类并实现 _run 方法
    """
    
    def __init__(self):
        self._metadata = self.get_metadata()
        self._langchain_tool: Optional[LangChainBaseTool] = None
    
    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """
        返回工具元数据
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def get_input_schema(self) -> Type[ToolInput]:
        """
        返回工具输入参数的 Pydantic 模型
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def _run(self, **kwargs) -> Dict[str, Any]:
        """
        工具的核心执行逻辑（异步）
        子类必须实现此方法
        
        Returns:
            Dict[str, Any]: 包含以下字段
                - success: bool - 是否成功
                - result: Any - 执行结果
                - error: Optional[str] - 错误信息
                - metadata: Optional[Dict] - 额外元数据
        """
        pass
    
    def _run_sync(self, **kwargs) -> Dict[str, Any]:
        """
        工具的核心执行逻辑（同步）
        子类可以选择实现此方法或 _run 方法
        """
        raise NotImplementedError("此工具不支持同步调用")
    
    @property
    def name(self) -> str:
        """工具名称"""
        return self._metadata.name
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        return self._metadata.display_name
    
    @property
    def description(self) -> str:
        """工具描述"""
        return self._metadata.description
    
    @property
    def metadata(self) -> ToolMetadata:
        """完整元数据"""
        return self._metadata
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行工具（带错误处理）
        外部调用此方法，不要直接调用 _run
        """
        try:
            # 验证输入参数
            input_schema = self.get_input_schema()
            validated_input = input_schema(**kwargs)
            
            # 执行工具
            result = await self._run(**validated_input.model_dump())
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"工具执行失败: {str(e)}",
                "metadata": {
                    "tool_name": self.name,
                    "exception_type": type(e).__name__
                }
            }
    
    def to_langchain_tool(self) -> LangChainBaseTool:
        """
        转换为 LangChain 工具格式
        用于集成到 LangGraph 中
        """
        if self._langchain_tool is None:
            from langchain_core.tools import StructuredTool
            
            async def wrapper(**kwargs):
                result = await self.execute(**kwargs)
                # LangChain 工具需要返回字符串或简单类型
                if result["success"]:
                    return result["result"]
                else:
                    return f"错误: {result['error']}"
            
            self._langchain_tool = StructuredTool(
                name=self.name,
                description=self.description,
                coroutine=wrapper,
                args_schema=self.get_input_schema()
            )
        
        return self._langchain_tool
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 返回）"""
        input_schema = self.get_input_schema()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self._metadata.category,
            "version": self._metadata.version,
            "author": self._metadata.author,
            "is_active": self._metadata.is_active,
            "requires_approval": self._metadata.requires_approval,
            "input_schema": input_schema.model_json_schema()
        }
