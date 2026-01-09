"""
通用助手智能体

基础的对话智能体，默认启用所有可用工具
"""

from app.graphs import build_chat_graph, build_agent_graph
from .base import BaseAgent


class GeneralAgent(BaseAgent):
    """
    通用助手
    
    一个乐于助人的 AI 助理，可以回答各种问题、进行日常对话
    默认启用所有可用工具
    """
    
    id = "general"
    name = "通用助手"
    description = "一个乐于助人的 AI 助理，可以回答各种问题、进行日常对话"
    
    system_prompt = """你是小明，一个乐于助人的 AI 助理。

你的特点：
- 友好、耐心、专业
- 回答准确、简洁
- 善于解释复杂概念
- 如果不确定，会诚实说明
- 遇到需要工具的任务（如计算、搜索等），优先使用工具

请用中文回答用户的问题。"""
    
    def __init__(self):
        """初始化并加载所有可用工具"""
        self.tools = []
        self._load_all_tools()
        super().__init__()
    
    def _load_all_tools(self):
        """加载所有可用工具"""
        from app.tools import tool_registry
        from app.core.logger import setup_logger
        
        logger = setup_logger(__name__)
        
        all_tools = tool_registry.list_all(active_only=True)
        for tool in all_tools:
            self.tools.append(tool.to_langchain_tool())
        
        logger.info(f"[{self.id}] 已加载 {len(self.tools)} 个工具")
    
    def _build_graph(self):
        """构建对话图"""
        # 如果有工具，使用 agent_graph，否则使用 chat_graph
        if self.tools:
            return build_agent_graph(tools=self.tools)  # ✅ 传入 tools
        else:
            return build_chat_graph()

