"""
智能体模块

包含：
- base: 智能体基类
- registry: 智能体注册中心
- dynamic_agent: 动态创建的智能体
- 各种预设智能体实现
"""

from .base import BaseAgent
from .registry import AgentRegistry, agent_registry
from .dynamic_agent import DynamicAgent
from .general_agent import GeneralAgent

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "agent_registry",
    "DynamicAgent",
    "GeneralAgent",
]
