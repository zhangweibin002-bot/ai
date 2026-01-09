"""
工具执行记录服务

处理工具调用的持久化存储
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from datetime import datetime

from app.core.logger import setup_logger
from app.models.tool_execution import ToolExecution

logger = setup_logger(__name__)


class ToolExecutionService:
    """工具执行记录服务"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    def save_tool_execution(
        self,
        session_id: str,
        tool_name: str,
        tool_call_id: str,
        input_params: Dict[str, Any],
        output_result: str,
        execution_time: int,
        status: str = "success",
        error_message: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> ToolExecution:
        """
        保存工具执行记录
        
        Args:
            session_id: 会话ID
            tool_name: 工具名称
            tool_call_id: 工具调用ID
            input_params: 输入参数
            output_result: 输出结果
            execution_time: 执行耗时(毫秒)
            status: 执行状态 (success/failed)
            error_message: 错误信息
            message_id: 关联的消息ID
            
        Returns:
            ToolExecution 实例
        """
        try:
            execution = ToolExecution(
                session_id=session_id,
                message_id=message_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                input_params=input_params,
                output_result=output_result,
                status=status,
                error_message=error_message,
                execution_time=execution_time,
            )
            
            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)
            
            logger.info(f"保存工具执行记录: tool={tool_name}, call_id={tool_call_id}, time={execution_time}ms")
            return execution
            
        except Exception as e:
            logger.error(f"保存工具执行记录失败: {str(e)}", exc_info=True)
            self.db.rollback()
            raise
    
    def get_tool_executions_by_session(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ToolExecution]:
        """
        获取会话的所有工具执行记录
        
        Args:
            session_id: 会话ID
            limit: 限制返回数量
            
        Returns:
            工具执行记录列表
        """
        query = self.db.query(ToolExecution).filter(
            ToolExecution.session_id == session_id
        ).order_by(ToolExecution.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_tool_executions_by_message(
        self,
        message_id: int
    ) -> List[ToolExecution]:
        """
        获取消息关联的所有工具执行记录
        
        Args:
            message_id: 消息ID
            
        Returns:
            工具执行记录列表
        """
        return self.db.query(ToolExecution).filter(
            ToolExecution.message_id == message_id
        ).order_by(ToolExecution.created_at).all()
    
    def get_tool_execution_stats(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取工具执行统计信息
        
        Args:
            session_id: 可选，指定会话ID
            
        Returns:
            统计信息字典
        """
        query = self.db.query(ToolExecution)
        
        if session_id:
            query = query.filter(ToolExecution.session_id == session_id)
        
        executions = query.all()
        
        if not executions:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_execution_time": 0,
                "tools_used": []
            }
        
        total = len(executions)
        success = sum(1 for e in executions if e.status == "success")
        failed = total - success
        avg_time = sum(e.execution_time for e in executions) / total if total > 0 else 0
        
        # 统计工具使用情况
        tools_count = {}
        for e in executions:
            tools_count[e.tool_name] = tools_count.get(e.tool_name, 0) + 1
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
            "avg_execution_time": round(avg_time, 2),
            "tools_used": [
                {"tool_name": name, "count": count}
                for name, count in sorted(tools_count.items(), key=lambda x: x[1], reverse=True)
            ]
        }
