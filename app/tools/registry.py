"""
工具注册中心
管理所有可用的工具实例
"""
from typing import Dict, List, Optional, Type
from app.tools.base import BaseTool
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class ToolRegistry:
    """
    工具注册中心（单例模式）
    负责管理所有工具的注册、获取和查询
    """
    
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """
        注册一个工具
        
        Args:
            tool: 工具实例
        """
        tool_name = tool.name
        
        if tool_name in self._tools:
            logger.warning(f"⚠️  工具 [{tool_name}] 已存在，将被覆盖")
        
        self._tools[tool_name] = tool
        logger.info(f"✅ 工具注册成功: {tool.display_name} ({tool_name})")
    
    def register_batch(self, tools: List[BaseTool]) -> None:
        """
        批量注册工具
        
        Args:
            tools: 工具实例列表
        """
        for tool in tools:
            self.register(tool)
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销一个工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否成功注销
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"🗑️  工具已注销: {tool_name}")
            return True
        else:
            logger.warning(f"⚠️  工具不存在: {tool_name}")
            return False
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取指定工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[BaseTool]: 工具实例，如果不存在则返回 None
        """
        return self._tools.get(tool_name)
    
    def get_by_names(self, tool_names: List[str]) -> List[BaseTool]:
        """
        根据名称列表获取多个工具
        
        Args:
            tool_names: 工具名称列表
            
        Returns:
            List[BaseTool]: 工具实例列表（跳过不存在的）
        """
        tools = []
        for name in tool_names:
            tool = self.get(name)
            if tool:
                tools.append(tool)
            else:
                logger.warning(f"⚠️  工具不存在，已跳过: {name}")
        return tools
    
    def list_all(self, category: Optional[str] = None, active_only: bool = True) -> List[BaseTool]:
        """
        列出所有工具
        
        Args:
            category: 可选，按分类筛选
            active_only: 是否只返回启用的工具
            
        Returns:
            List[BaseTool]: 工具实例列表
        """
        tools = list(self._tools.values())
        
        # 筛选分类
        if category:
            tools = [t for t in tools if t.metadata.category == category]
        
        # 筛选启用状态
        if active_only:
            tools = [t for t in tools if t.metadata.is_active]
        
        return tools
    
    def get_categories(self) -> List[str]:
        """
        获取所有工具分类
        
        Returns:
            List[str]: 分类列表
        """
        categories = set()
        for tool in self._tools.values():
            categories.add(tool.metadata.category)
        return sorted(list(categories))
    
    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        logger.info("🗑️  所有工具已清空")
    
    def count(self) -> int:
        """返回工具数量"""
        return len(self._tools)
    
    def exists(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self._tools
    
    def to_langchain_tools(self, tool_names: Optional[List[str]] = None):
        """
        转换为 LangChain 工具列表
        
        Args:
            tool_names: 可选，指定工具名称列表。如果为 None，返回所有工具
            
        Returns:
            List: LangChain 工具列表
        """
        if tool_names:
            tools = self.get_by_names(tool_names)
        else:
            tools = self.list_all(active_only=True)
        
        return [tool.to_langchain_tool() for tool in tools]
    
    def get_summary(self) -> Dict:
        """
        获取注册中心摘要信息
        
        Returns:
            Dict: 包含工具数量、分类等统计信息
        """
        tools = list(self._tools.values())
        active_count = sum(1 for t in tools if t.metadata.is_active)
        
        return {
            "total": len(tools),
            "active": active_count,
            "inactive": len(tools) - active_count,
            "categories": self.get_categories(),
            "tools": [
                {
                    "name": t.name,
                    "display_name": t.display_name,
                    "category": t.metadata.category,
                    "is_active": t.metadata.is_active
                }
                for t in tools
            ]
        }


# 全局工具注册中心实例
tool_registry = ToolRegistry()
