"""
智能体基类

定义所有智能体必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator, Any, Dict
from langchain_core.tools import BaseTool
import json

from app.core.logger import setup_logger

logger = setup_logger(__name__)


class BaseAgent(ABC):
    """
    智能体基类
    
    所有智能体必须继承此类并实现抽象方法
    """
    
    # ===== 必须定义的属性 =====
    id: str                          # 唯一标识符
    name: str                        # 显示名称
    description: str                 # 描述（用于选择/路由）
    system_prompt: str               # 系统提示词
    
    # ===== 可选属性 =====
    # tools: List[BaseTool]          # 可用工具（在 __init__ 中初始化，避免共享）
    model_name: Optional[str] = None # 指定模型（None 则使用默认）
    temperature: float = 0.7         # 温度参数
    
    def __init__(self):
        """初始化智能体"""
        self._graph = None
        self._llm = None
        # 初始化工具列表（避免类属性共享问题）
        if not hasattr(self, 'tools'):
            self.tools = []
        logger.info(f"智能体初始化: {self.id} - {self.name}")
        logger.info(f"  - 工具数量: {len(self.tools)}")
    
    @property
    def graph(self):
        """懒加载 LangGraph 图"""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    @property
    def llm(self):
        """懒加载 LLM"""
        if self._llm is None:
            self._llm = self._build_llm()
        return self._llm
    
    @abstractmethod
    def _build_graph(self):
        """
        构建 LangGraph 图
        
        子类必须实现此方法
        """
        pass
    
    def _build_llm(self):
        """构建 LLM 实例"""
        from app.models.base_llm import base_llm
        return base_llm()
    
    def chat(self, query: str, thread_id: str) -> str:
        """
        同步对话
        
        Args:
            query: 用户查询
            thread_id: 会话 ID
            
        Returns:
            AI 回复内容
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        try:
            logger.info(f"[{self.id}] 开始处理查询，thread_id: {thread_id}")
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=query),
            ]
            
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "llm": self.llm,
                    "tools": self.tools,
                }
            }
            
            result = self.graph.invoke(
                {"messages": messages},
                config=config,
            )
            
            reply = result["messages"][-1].content
            logger.info(f"[{self.id}] 查询处理完成")
            return reply
            
        except Exception as e:
            logger.error(f"[{self.id}] 处理查询时发生错误", exc_info=True)
            raise RuntimeError(str(e)) from e
    
    async def stream_chat(self, query: str, thread_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话（支持工具调用事件）
        
        Args:
            query: 用户查询
            thread_id: 会话 ID
            
        Yields:
            Dict: 事件字典，包含以下类型:
                - {"type": "content", "content": str}  # 正常回复内容
                - {"type": "tool_call", "tool_name": str, "tool_call_id": str, "arguments": dict}  # 工具调用
                - {"type": "tool_result", "tool_call_id": str, "result": str}  # 工具结果
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        try:
            logger.info(f"[{self.id}] 开始流式处理，thread_id: {thread_id}")
            logger.info(f"[{self.id}] 当前 self.tools 数量: {len(self.tools)}")
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=query),
            ]
            
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "llm": self.llm,
                    "tools": self.tools,
                },
                "recursion_limit": 50  # 增加递归限制，防止复杂任务超限
            }
            
            logger.info(f"[{self.id}] config['configurable']['tools'] 数量: {len(config['configurable']['tools'])}")
            
            # 用于追踪工具调用
            pending_tool_calls = {}
            
            async for event in self.graph.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                event_type = event["event"]
                
                # 1. AI 回复内容（流式输出）
                if event_type == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    
                    # 检查是否有工具调用
                    tool_calls = getattr(chunk, "tool_calls", None)
                    if tool_calls:
                        for tool_call in tool_calls:
                            # 可能是增量的 tool_call，需要累积
                            if "name" in tool_call and tool_call["name"]:
                                tool_call_id = tool_call.get("id", "")
                                pending_tool_calls[tool_call_id] = tool_call
                                
                                yield {
                                    "type": "tool_call",
                                    "tool_name": tool_call["name"],
                                    "tool_call_id": tool_call_id,
                                    "arguments": tool_call.get("args", {}),
                                }
                    
                    # 正常文本内容
                    if content:
                        yield {"type": "content", "content": content}
                
                # 2. 工具执行完成（LangChain 内置工具）
                elif event_type == "on_tool_end":
                    tool_call_id = event["data"].get("tool_call_id", "")
                    output = event["data"].get("output", "")
                    
                    yield {
                        "type": "tool_result",
                        "tool_call_id": tool_call_id,
                        "result": str(output),
                    }
                
                # 3. 自定义 tools 节点执行完成
                elif event_type == "on_chain_end":
                    # 检查是否是 tools 节点
                    node_name = event.get("name", "")
                    if node_name == "tools":
                        # 获取输出的消息列表
                        output = event.get("data", {}).get("output", {})
                        messages = output.get("messages", [])
                        
                        # 解析 ToolMessage
                        from langchain_core.messages import ToolMessage
                        for msg in messages:
                            if isinstance(msg, ToolMessage):
                                logger.info(f"[{self.id}] 发送 tool_result 事件: tool_call_id={msg.tool_call_id}")
                                yield {
                                    "type": "tool_result",
                                    "tool_call_id": msg.tool_call_id,
                                    "result": msg.content,
                                }
            
            logger.info(f"[{self.id}] 流式处理完成")
            
        except Exception as e:
            logger.error(f"[{self.id}] 流式处理时发生错误", exc_info=True)
            raise
    
    def to_dict(self) -> dict:
        """转换为字典（用于 API 响应）"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "has_tools": len(self.tools) > 0,
            "tool_count": len(self.tools),
        }

