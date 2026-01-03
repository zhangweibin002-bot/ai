"""
LangGraph 状态定义

定义各种图的状态类型
"""

from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    基础聊天状态
    
    用于简单的对话场景，不涉及工具调用
    """
    messages: Annotated[List[BaseMessage], add_messages]


class AgentState(TypedDict):
    """
    智能体状态
    
    用于带工具调用的 ReAct 智能体
    """
    messages: Annotated[List[BaseMessage], add_messages]
    # 可扩展字段
    # tool_calls: List[dict]
    # intermediate_steps: List[tuple]

