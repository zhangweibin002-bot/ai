"""
聊天接口

处理用户与 AI 的对话请求（流式输出）
"""

import json
import time
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional, AsyncGenerator

from app.core.logger import setup_logger
from app.db.session import get_db
from app.agents import agent_registry
from app.services.session_service import SessionService
from app.services.tool_execution_service import ToolExecutionService

logger = setup_logger(__name__)
router = APIRouter()


# =====================
# 请求模型
# =====================
class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None      # 指定智能体
    system_prompt: Optional[str] = None  # 自定义提示词（覆盖智能体默认）


# =====================
# 流式对话接口
# =====================
@router.post("")
async def chat_stream(
    request: ChatRequest,
    db: DBSession = Depends(get_db)
):
    """
    发送消息并获取 AI 流式回复（SSE）
    
    - **message**: 用户消息内容
    - **session_id**: 会话 ID（可选，不传则创建新会话）
    - **agent_id**: 智能体 ID（可选，默认使用 general）
    - **system_prompt**: 自定义系统提示词（可选，覆盖智能体默认提示词）
    """
    try:
        session_service = SessionService(db)
        is_new_session = False
        
        # 1. 获取智能体
        agent = agent_registry.get_or_default(request.agent_id)
        logger.info(f"使用智能体: {agent.id} - {agent.name}")
        
        # 2. 获取或创建会话
        if request.session_id:
            session = session_service.get_session(request.session_id)
            if not session:
                session = session_service.create_session(agent_id=agent.id)
                is_new_session = True
        else:
            session = session_service.create_session(agent_id=agent.id)
            is_new_session = True
        
        session_id = session.id
        logger.info(f"处理流式聊天请求: session_id={session_id}, agent={agent.id}, is_new={is_new_session}")
        
        # 3. 保存用户消息
        session_service.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
        )
        
        # 4. 如果是新会话，生成标题
        if is_new_session or not session.title or session.title == "新对话":
            title = session_service.generate_title(request.message)
            session_service.update_session_title(session_id, title)
        
        # 5. 创建流式响应生成器
        async def generate() -> AsyncGenerator[str, None]:
            full_response = ""
            tool_calls_record = []  # 记录工具调用
            tool_execution_tracker = {}  # 追踪工具执行（tool_call_id -> {tool_name, arguments, start_time}）
            assistant_message_id = None  # 助手消息ID
            
            try:
                # 创建工具执行服务
                tool_execution_service = ToolExecutionService(db)
                
                # 发送会话信息
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id, 'agent_id': agent.id, 'agent_name': agent.name, 'is_new_session': is_new_session}, ensure_ascii=False)}\n\n"
                
                # 使用智能体的流式对话
                # 如果提供了自定义 system_prompt，临时覆盖
                original_prompt = agent.system_prompt
                if request.system_prompt:
                    agent.system_prompt = request.system_prompt
                
                try:
                    async for event in agent.stream_chat(
                        query=request.message,
                        thread_id=session_id,
                    ):
                        event_type = event["type"]
                        
                        # 内容事件
                        if event_type == "content":
                            content = event["content"]
                            full_response += content
                            yield f"data: {json.dumps({'type': 'content', 'content': content}, ensure_ascii=False)}\n\n"
                        
                        # 工具调用事件
                        elif event_type == "tool_call":
                            # 如果是第一个工具调用，先创建 assistant 消息
                            if assistant_message_id is None:
                                assistant_msg = session_service.add_message(
                                    session_id=session_id,
                                    role="assistant",
                                    content="",  # 先保存空内容
                                )
                                assistant_message_id = assistant_msg.id
                                logger.info(f"创建 assistant 消息: message_id={assistant_message_id}")
                            
                            # 记录工具调用开始时间
                            tool_call_id = event["tool_call_id"]
                            tool_execution_tracker[tool_call_id] = {
                                "tool_name": event["tool_name"],
                                "arguments": event["arguments"],
                                "start_time": time.time()
                            }
                            
                            tool_calls_record.append(event)
                            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        
                        # 工具结果事件
                        elif event_type == "tool_result":
                            tool_call_id = event["tool_call_id"]
                            
                            # 计算执行时间并保存到数据库
                            if tool_call_id in tool_execution_tracker:
                                tracker = tool_execution_tracker[tool_call_id]
                                execution_time = int((time.time() - tracker["start_time"]) * 1000)  # 毫秒
                                
                                try:
                                    # 保存工具执行记录
                                    tool_execution_service.save_tool_execution(
                                        session_id=session_id,
                                        message_id=assistant_message_id,
                                        tool_name=tracker["tool_name"],
                                        tool_call_id=tool_call_id,
                                        input_params=tracker["arguments"],
                                        output_result=event["result"],
                                        execution_time=execution_time,
                                        status="success"
                                    )
                                except Exception as e:
                                    logger.error(f"保存工具执行记录失败: {str(e)}")
                            
                            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
                finally:
                    # 恢复原始 prompt
                    if request.system_prompt:
                        agent.system_prompt = original_prompt
                
                # 更新完整回复到数据库
                if assistant_message_id:
                    # 如果已经创建了消息，更新内容
                    session_service.update_message_content(
                        message_id=assistant_message_id,
                        content=full_response,
                        tool_calls=tool_calls_record if tool_calls_record else None,
                    )
                else:
                    # 如果没有工具调用，直接保存消息
                    session_service.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                        tool_calls=tool_calls_record if tool_calls_record else None,
                    )
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                logger.error(f"流式处理失败: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
        
    except Exception as e:
        logger.error(f"流式聊天处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health():
    """聊天服务健康检查"""
    return {"status": "ok", "service": "chat"}
