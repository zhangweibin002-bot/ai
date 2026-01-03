"""
LangGraph 节点函数

定义图中各个节点的处理逻辑
"""

import time
from typing import List
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool

from app.core.logger import setup_logger
from .states import ChatState, AgentState

logger = setup_logger(__name__)


def chat_node(state: ChatState, config: RunnableConfig) -> dict:
    """
    基础对话节点
    
    从 config 中获取 LLM 实例，处理消息并返回响应
    
    Args:
        state: 当前聊天状态
        config: 运行时配置，包含 llm 实例
        
    Returns:
        更新后的状态（新增 AI 响应消息）
    """
    llm = config["configurable"]["llm"]
    
    logger.debug(f"chat_node 处理消息，共 {len(state['messages'])} 条")
    
    response = llm.invoke(state["messages"])
    
    return {"messages": [response]}


def agent_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    智能体节点（带工具绑定）
    
    Args:
        state: 当前智能体状态
        config: 运行时配置，包含 llm 和 tools
        
    Returns:
        更新后的状态
    """
    llm = config["configurable"]["llm"]
    tools = config["configurable"].get("tools", [])
    
    # 绑定工具到 LLM
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm
    
    logger.debug(f"agent_node 处理消息，绑定 {len(tools)} 个工具")
    
    response = llm_with_tools.invoke(state["messages"])
    
    return {"messages": [response]}


def tool_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    工具执行节点（自定义版本，带详细日志）
    
    执行 LLM 返回的工具调用，并记录详细日志
    
    Args:
        state: 当前智能体状态
        config: 运行时配置
        
    Returns:
        工具执行结果
    """
    tools: List[BaseTool] = config["configurable"].get("tools", [])
    tools_by_name = {tool.name: tool for tool in tools}
    
    # 获取最后一条消息中的工具调用
    last_message = state["messages"][-1]
    tool_messages = []
    
    # 记录工具调用总数
    tool_calls = getattr(last_message, "tool_calls", [])
    logger.info(f"{'='*50}")
    logger.info(f"🔧 工具调用开始 | 共 {len(tool_calls)} 个工具待执行")
    logger.info(f"{'='*50}")
    
    for idx, tool_call in enumerate(tool_calls, 1):
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        
        logger.info(f"")
        logger.info(f"📌 [{idx}/{len(tool_calls)}] 工具: {tool_name}")
        logger.info(f"   参数: {tool_args}")
        
        tool = tools_by_name.get(tool_name)
        
        if tool:
            try:
                # 记录开始时间
                start_time = time.time()
                
                # 执行工具
                result = tool.invoke(tool_args)
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                
                # 记录成功日志
                result_preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                logger.info(f"   ✅ 执行成功 | 耗时: {elapsed_time:.2f}s")
                logger.info(f"   结果: {result_preview}")
                
                tool_messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_id,
                    )
                )
                
            except Exception as e:
                # 记录失败日志
                logger.error(f"   ❌ 执行失败 | 错误: {str(e)}")
                
                tool_messages.append(
                    ToolMessage(
                        content=f"工具执行失败: {str(e)}",
                        tool_call_id=tool_id,
                    )
                )
        else:
            # 工具不存在
            logger.warning(f"   ⚠️ 工具不存在: {tool_name}")
            logger.warning(f"   可用工具: {list(tools_by_name.keys())}")
            
            tool_messages.append(
                ToolMessage(
                    content=f"工具 '{tool_name}' 不存在",
                    tool_call_id=tool_id,
                )
            )
    
    logger.info(f"")
    logger.info(f"{'='*50}")
    logger.info(f"🔧 工具调用结束 | 成功: {len(tool_messages)}/{len(tool_calls)}")
    logger.info(f"{'='*50}")
    
    return {"messages": tool_messages}
