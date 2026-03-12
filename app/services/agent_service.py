"""
智能体服务

处理智能体的 CRUD 操作
"""

import re
import time
from typing import List, Optional

from sqlalchemy.orm import Session as DBSession

from app.core.logger import setup_logger
from app.models.agent_config import AgentConfig
from app.agents.dynamic_agent import DynamicAgent
from app.agents.registry import agent_registry

logger = setup_logger(__name__)


class AgentService:
    """智能体服务"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    # =====================
    # 创建
    # =====================
    
    def create_agent(
        self,
        name: str,
        system_prompt: str,
        description: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        tools: Optional[List[str]] = None,
    ) -> AgentConfig:
        """
        创建智能体
        
        Args:
            name: 显示名称
            system_prompt: 系统提示词
            description: 简短描述
            model_name: 模型名称
            temperature: 温度参数
            tools: 可用工具列表
            
        Returns:
            AgentConfig 实例
        """
        # 生成 ID
        agent_id = self._generate_id(name)
        
        # 创建数据库记录
        config = AgentConfig(
            id=agent_id,
            name=name,
            description=description or name,
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            is_system=False,
            is_active=True,
        )
        
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        
        # 创建动态智能体并注册
        agent = DynamicAgent.from_config(config)
        agent_registry.register(agent)
        
        logger.info(f"创建智能体: {agent_id} - {name}")
        return config
    
    def _generate_id(self, name: str) -> str:
        """生成智能体 ID"""
        # 移除特殊字符，转小写
        clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', name)
        # 添加时间戳
        timestamp = int(time.time())
        return f"{clean_name}_{timestamp}"
    
    # =====================
    # 查询
    # =====================
    
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """获取智能体配置"""
        return self.db.query(AgentConfig).filter(
            AgentConfig.id == agent_id,
            AgentConfig.is_active == True
        ).first()
    
    def list_agents(self, include_inactive: bool = False) -> List[AgentConfig]:
        """获取智能体列表"""
        query = self.db.query(AgentConfig)
        
        if not include_inactive:
            query = query.filter(AgentConfig.is_active == True)
        
        return query.order_by(AgentConfig.is_system.desc(), AgentConfig.created_at).all()
    
    # =====================
    # 更新
    # =====================
    
    def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[AgentConfig]:
        """
        更新智能体
        
        系统预设智能体不能修改
        """
        config = self.get_agent(agent_id)
        
        if not config:
            return None
        
        if config.is_system:
            raise ValueError("系统预设智能体不能修改")
        
        # 更新字段
        if name is not None:
            config.name = name
        if description is not None:
            config.description = description
        if system_prompt is not None:
            config.system_prompt = system_prompt
        if temperature is not None:
            config.temperature = temperature
        if tools is not None:
            config.tools = tools
        if is_active is not None:
            config.is_active = is_active
        
        self.db.commit()
        self.db.refresh(config)
        
        # 更新 Registry 中的智能体
        agent_registry.unregister(agent_id)
        agent = DynamicAgent.from_config(config)
        agent_registry.register(agent)
        
        logger.info(f"更新智能体: {agent_id}")
        return config
    
    # =====================
    # 删除
    # =====================
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        删除智能体
        
        系统预设智能体不能删除
        """
        config = self.get_agent(agent_id)
        
        if not config:
            return False
        
        if config.is_system:
            raise ValueError("系统预设智能体不能删除")
        
        # 软删除
        config.is_active = False
        self.db.commit()
        
        # 从 Registry 注销
        agent_registry.unregister(agent_id)
        
        logger.info(f"删除智能体: {agent_id}")
        return True
    
    # =====================
    # 初始化
    # =====================
    
    def init_system_agents(self) -> int:
        """
        初始化系统预设智能体
        
        如果不存在则创建
        
        Returns:
            创建的数量
        """
        system_agents = [
            {
                "id": "general",
                "name": "通用助手",
                "description": "一个乐于助人的 AI 助理，可以回答各种问题、进行日常对话",
                "system_prompt": """你是小明，一个乐于助人的 AI 助理。

你的特点：
- 友好、耐心、专业
- 善于解释复杂概念
- 如果不确定，会诚实说明

请用中文回答用户的问题。""",
            },
        ]
        
        created_count = 0
        
        for agent_data in system_agents:
            existing = self.db.query(AgentConfig).filter(
                AgentConfig.id == agent_data["id"]
            ).first()
            
            if not existing:
                config = AgentConfig(
                    id=agent_data["id"],
                    name=agent_data["name"],
                    description=agent_data["description"],
                    system_prompt=agent_data["system_prompt"],
                    is_system=True,
                    is_active=True,
                )
                self.db.add(config)
                created_count += 1
                logger.info(f"创建系统智能体: {agent_data['id']}")
        
        self.db.commit()
        return created_count
    
    def load_all_agents(self) -> int:
        """
        从数据库加载所有智能体到 Registry
        
        Returns:
            加载的数量
        """
        configs = self.list_agents()
        
        for config in configs:
            agent = DynamicAgent.from_config(config)
            agent_registry.register(agent)
        
        logger.info(f"从数据库加载 {len(configs)} 个智能体")
        return len(configs)

