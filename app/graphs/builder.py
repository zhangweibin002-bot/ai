"""
LangGraph 图构建器

提供不同类型图的构建函数
"""

from typing import List, Optional
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.logger import setup_logger
from .states import ChatState, AgentState
from .nodes import chat_node, agent_node, tool_node

logger = setup_logger(__name__)


def build_chat_graph():
    """
    构建基础对话图
    
    简单的单轮对话，不涉及工具调用
    
    流程: START -> chat -> END
    
    Returns:
        编译后的 LangGraph 应用
    """
    graph = StateGraph(ChatState)
    
    # 添加节点
    graph.add_node("chat", chat_node)
    
    # 设置入口和边
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    
    # 添加内存检查点（支持多轮对话）
    checkpointer = MemorySaver()
    
    logger.info("基础对话图构建完成")
    
    return graph.compile(checkpointer=checkpointer)


def build_agent_graph(tools: Optional[List[BaseTool]] = None):
    """
    构建智能体图（ReAct 模式）
    
    支持工具调用的智能体，会循环执行直到完成
    使用自定义 tool_node，支持详细日志记录
    
    流程: START -> agent -> [tools -> agent]* -> END
    
    Args:
        tools: 可用的工具列表
        
    Returns:
        编译后的 LangGraph 应用
    """
    tools = tools or []
    
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("agent", agent_node)
    
    if tools:
        # 使用自定义 tool_node（带详细日志）
        graph.add_node("tools", tool_node)
    
    # 设置入口
    graph.set_entry_point("agent")
    
    # 定义条件边
    def should_continue(state: AgentState) -> str:
        """判断是否需要继续执行工具"""
        last_message = state["messages"][-1]
        
        # 如果有工具调用，继续执行
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # 否则结束
        return END
    
    # 添加条件边
    if tools:
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
    else:
        graph.add_edge("agent", END)
    
    # 添加内存检查点
    checkpointer = MemorySaver()
    
    logger.info(f"智能体图构建完成，工具数量: {len(tools)}")
    
    return graph.compile(checkpointer=checkpointer)
