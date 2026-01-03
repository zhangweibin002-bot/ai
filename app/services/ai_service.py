"""
AI 服务封装

存放各种智能体的客户端
"""

from typing import AsyncGenerator
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logger import setup_logger
from app.models.base_llm import base_llm
from app.graphs import build_chat_graph, build_agent_graph

logger = setup_logger(__name__)


class LLMClient:
    """
    基础 LLM 客户端
    
    封装 LangGraph 对话图，提供简单的对话接口
    """
    
    def __init__(self):
        try:
            self.llm = base_llm()
            self.app = build_chat_graph()
            logger.info("LLMClient（LangGraph）初始化成功")
        except Exception as e:
            logger.error(f"LLMClient 初始化失败: {str(e)}")
            raise

    def chat(
        self,
        query: str,
        system_prompt: str,
        thread_id: str,
    ) -> str:
        """
        同步对话
        
        Args:
            query: 用户查询
            system_prompt: 系统提示词
            thread_id: 会话 ID（用于多轮对话）
            
        Returns:
            AI 回复内容
        """
        try:
            logger.info(f"开始处理查询，thread_id: {thread_id}")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query),
            ]

            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "llm": self.llm,
                }
            }

            result = self.app.invoke(
                {"messages": messages},
                config=config,
            )

            reply = result["messages"][-1].content
            logger.info("查询处理完成")
            return reply

        except Exception as e:
            logger.error("处理查询时发生错误", exc_info=True)
            raise RuntimeError(str(e)) from e

    async def stream_chat(
        self,
        query: str,
        system_prompt: str,
        thread_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话
        
        Args:
            query: 用户查询
            system_prompt: 系统提示词
            thread_id: 会话 ID
            
        Yields:
            AI 回复的每个 token
        """
        try:
            logger.info(f"开始流式处理，thread_id: {thread_id}")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query),
            ]

            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "llm": self.llm,
                }
            }

            async for event in self.app.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield content

            logger.info("流式处理完成")

        except Exception as e:
            logger.error("流式处理时发生错误", exc_info=True)
            raise


class AgentClient:
    """
    智能体客户端
    
    支持工具调用的 ReAct 智能体
    """
    
    def __init__(self, tools=None):
        try:
            self.llm = base_llm()
            self.tools = tools or []
            self.app = build_agent_graph(tools=self.tools)
            logger.info(f"AgentClient 初始化成功，工具数量: {len(self.tools)}")
        except Exception as e:
            logger.error(f"AgentClient 初始化失败: {str(e)}")
            raise

    def run(
        self,
        query: str,
        system_prompt: str,
        thread_id: str,
    ) -> str:
        """
        执行智能体
        
        Args:
            query: 用户查询
            system_prompt: 系统提示词
            thread_id: 会话 ID
            
        Returns:
            智能体最终回复
        """
        try:
            logger.info(f"Agent 开始执行，thread_id: {thread_id}")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query),
            ]

            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "llm": self.llm,
                    "tools": self.tools,
                }
            }

            result = self.app.invoke(
                {"messages": messages},
                config=config,
            )

            reply = result["messages"][-1].content
            logger.info("Agent 执行完成")
            return reply

        except Exception as e:
            logger.error("Agent 执行时发生错误", exc_info=True)
            raise RuntimeError(str(e)) from e


# =====================
# 本地测试
# =====================
if __name__ == "__main__":
    client = LLMClient()
    response = client.chat(
        query="你好！请介绍一下你自己。",
        system_prompt="你是小明，一个乐于助人的 AI 助理。",
        thread_id="user_001",
    )
    print(response)
