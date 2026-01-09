"""
动态智能体

运行时创建的智能体，配置从数据库加载
"""

from typing import Optional, List
from app.graphs import build_chat_graph, build_agent_graph
from .base import BaseAgent


class DynamicAgent(BaseAgent):
    """
    动态智能体
    
    根据数据库配置动态创建的智能体
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        system_prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        is_system: bool = False,
        tool_names: Optional[List[str]] = None,
    ):
        # 设置属性
        self.id = agent_id
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.temperature = temperature
        self.is_system = is_system
        
        # 加载工具（默认加载所有工具）
        self.tools = []
        self._load_tools(tool_names)
        
        # 调用父类初始化
        super().__init__()
    
    def _load_tools(self, tool_names: Optional[List[str]] = None):
        """
        从工具注册中心加载工具
        
        Args:
            tool_names: 工具名称列表。如果为 None 或空列表，则加载所有可用工具
        """
        from app.tools import tool_registry
        from app.core.logger import setup_logger
        
        logger = setup_logger(__name__)
        
        # 调试日志
        registry_count = tool_registry.count()
        logger.info(f"[{self.id}] 工具注册中心当前有 {registry_count} 个工具")
        
        # 如果未指定工具或为空列表，加载所有工具
        if not tool_names:
            logger.info(f"[{self.id}] 未指定工具，自动加载所有可用工具")
            all_tools = tool_registry.list_all(active_only=True)
            logger.info(f"[{self.id}] 找到 {len(all_tools)} 个可用工具")
            for tool in all_tools:
                langchain_tool = tool.to_langchain_tool()
                self.tools.append(langchain_tool)
                logger.info(f"[{self.id}] - 加载工具: {tool.name}")
            logger.info(f"[{self.id}] ✅ 已加载 {len(self.tools)} 个工具")
        else:
            # 加载指定的工具
            logger.info(f"[{self.id}] 加载指定工具: {tool_names}")
            for tool_name in tool_names:
                tool = tool_registry.get(tool_name)
                if tool:
                    self.tools.append(tool.to_langchain_tool())
                    logger.info(f"[{self.id}] - 加载工具: {tool_name}")
                else:
                    logger.warning(f"[{self.id}] ⚠️  工具不存在，跳过: {tool_name}")
            logger.info(f"[{self.id}] ✅ 已加载 {len(self.tools)} 个工具")
    
    def _build_graph(self):
        """构建对话图"""
        from app.core.logger import setup_logger
        logger = setup_logger(__name__)
        
        logger.info(f"[{self.id}] _build_graph: self.tools 数量 = {len(self.tools)}")
        
        # 如果有工具，使用 agent_graph，否则使用 chat_graph
        if self.tools:
            logger.info(f"[{self.id}] 使用 agent_graph（带工具）")
            return build_agent_graph(tools=self.tools)  # ✅ 传入 tools
        else:
            logger.info(f"[{self.id}] 使用 chat_graph（无工具）")
            return build_chat_graph()
    
    def _build_llm(self):
        """构建 LLM 实例"""
        from app.models.base_llm import base_llm
        # TODO: 支持自定义模型和温度
        return base_llm()
    
    @classmethod
    def from_config(cls, config) -> "DynamicAgent":
        """
        从数据库配置创建智能体
        
        Args:
            config: AgentConfig 实例或字典
            
        Returns:
            DynamicAgent 实例
        """
        if hasattr(config, "to_dict"):
            # 是 ORM 对象
            return cls(
                agent_id=config.id,
                name=config.name,
                description=config.description or "",
                system_prompt=config.system_prompt,
                model_name=config.model_name,
                temperature=config.temperature or 0.7,
                is_system=config.is_system or False,
                tool_names=config.tools,
            )
        else:
            # 是字典
            return cls(
                agent_id=config["id"],
                name=config["name"],
                description=config.get("description", ""),
                system_prompt=config["system_prompt"],
                model_name=config.get("model_name"),
                temperature=config.get("temperature", 0.7),
                is_system=config.get("is_system", False),
                tool_names=config.get("tools"),
            )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "has_tools": len(self.tools) > 0,
            "tool_count": len(self.tools),
            "tool_names": [tool.name for tool in self.tools] if self.tools else [],
            "is_system": self.is_system,
        }

