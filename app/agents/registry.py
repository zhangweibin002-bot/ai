"""
智能体注册中心

管理所有已注册的智能体
"""

from typing import Dict, List, Optional

from app.core.logger import setup_logger
from .base import BaseAgent

logger = setup_logger(__name__)


class AgentRegistry:
    """
    智能体注册中心
    
    单例模式，管理所有智能体的注册和获取
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        logger.info("智能体注册中心初始化")
    
    # =====================
    # 注册/注销
    # =====================
    
    def register(self, agent: BaseAgent) -> None:
        """
        注册智能体
        
        Args:
            agent: 智能体实例
        """
        if agent.id in self._agents:
            logger.warning(f"智能体 '{agent.id}' 已存在，将被覆盖")
        
        self._agents[agent.id] = agent
        logger.info(f"注册智能体: {agent.id} - {agent.name}")
    
    def unregister(self, agent_id: str) -> bool:
        """
        注销智能体
        
        Args:
            agent_id: 智能体 ID
            
        Returns:
            是否成功注销
        """
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            logger.info(f"注销智能体: {agent_id} - {agent.name}")
            return True
        
        logger.warning(f"智能体 '{agent_id}' 不存在，无法注销")
        return False
    
    def clear(self) -> int:
        """
        清空所有智能体
        
        Returns:
            清除的数量
        """
        count = len(self._agents)
        self._agents.clear()
        logger.info(f"已清空所有智能体，共 {count} 个")
        return count
    
    # =====================
    # 查询
    # =====================
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """
        获取智能体
        
        Args:
            agent_id: 智能体 ID
            
        Returns:
            智能体实例，不存在则返回 None
        """
        return self._agents.get(agent_id)
    
    def get_or_default(self, agent_id: Optional[str] = None) -> BaseAgent:
        """
        获取智能体，不存在则返回默认智能体
        
        Args:
            agent_id: 智能体 ID
            
        Returns:
            智能体实例
        """
        if agent_id and agent_id in self._agents:
            return self._agents[agent_id]
        
        # 返回默认智能体（第一个注册的，或 "general"）
        if "general" in self._agents:
            return self._agents["general"]
        
        if self._agents:
            return list(self._agents.values())[0]
        
        raise ValueError("没有注册任何智能体")
    
    def list_all(self) -> List[BaseAgent]:
        """
        列出所有智能体
        
        Returns:
            智能体列表
        """
        return list(self._agents.values())
    
    def list_ids(self) -> List[str]:
        """
        列出所有智能体 ID
        
        Returns:
            ID 列表
        """
        return list(self._agents.keys())
    
    def exists(self, agent_id: str) -> bool:
        """
        检查智能体是否存在
        
        Args:
            agent_id: 智能体 ID
            
        Returns:
            是否存在
        """
        return agent_id in self._agents
    
    def count(self) -> int:
        """
        获取已注册智能体数量
        
        Returns:
            数量
        """
        return len(self._agents)


# 全局单例
agent_registry = AgentRegistry()
