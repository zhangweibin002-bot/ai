.
├── app/
│   ├── api/                    # 接口层 (FastAPI 路由)
│   │   ├── deps.py             # 依赖注入 (如 Auth, DB session)
│   │   └── v1/                 # API 版本控制
│   │       ├── endpoints/      # 具体业务路由
│   │       │   ├── chat.py     # 聊天/流式对话接口
│   │       │   ├── agents.py   # 智能体配置与列表获取
│   │       │   └── users.py    # 用户信息与设置
│   │       └── api.py          # 路由汇总
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 环境变量与全局配置 (Pydantic Settings)
│   │   ├── security.py         # JWT 校验与加密
│   │   └── logging.py          # 日志配置
│   ├── services/               # 业务逻辑层 (核心)
│   │   ├── ai_service.py       # 通用 AI 调用逻辑 (OpenAI/Gemini SDK)
│   │   ├── agent_manager.py    # 智能体身份/Prompt 模板注入逻辑
│   │   └── chat_service.py     # 消息保存、上下文窗口管理
│   ├── schemas/                # 数据校验层 (Pydantic Models)
│   │   ├── chat.py             # 聊天请求/响应格式
│   │   ├── agent.py            # 智能体元数据定义
│   │   └── user.py             # 用户数据模型
│   ├── models/                 # 数据库模型 (SQLAlchemy 或 Tortoise)
│   │   ├── base.py             # 基础模型
│   │   ├── chat_history.py     # 聊天历史记录表
│   │   └── agent_config.py     # 智能体预设配置表
│   ├── db/                     # 数据库连接
│   │   ├── base.py             # 汇总所有模型以便迁移
│   │   └── session.py          # 数据库引擎与会话配置
│   └── main.py                 # 程序入口 (FastAPI App 初始化)
├── migrations/                 # Alembic 数据库迁移脚本
├── tests/                      # 测试用例 (Pytest)
├── scripts/                    # 运维脚本 (如初始化智能体数据)
├── requirements.txt            # 项目依赖
├── .env                        # 环境变量 (API_KEYS, DB_URL)
├── Dockerfile                  # 容器化部署
└── alembic.ini                 # 数据库迁移配置文件

app/
├── graphs/                 # 🆕 LangGraph 图定义
│   ├── __init__.py         # 模块导出
│   ├── states.py           # 状态类型定义 (ChatState, AgentState)
│   ├── nodes.py            # 节点函数 (chat_node, agent_node, tool_node)
│   └── builder.py          # 图构建器 (build_chat_graph, build_agent_graph)
│
├── models/                 # 🔄 数据库模型（已重写）
│   ├── base.py             # SQLAlchemy Base + 通用混入类
│   ├── base_llm.py         # LLM 初始化配置
│   ├── chat_history.py     # 聊天记录表（待实现）
│   └── agent_config.py     # 智能体配置表（待实现）
│
├── services/               # 🔄 业务服务（已更新）
│   ├── ai_service.py       # LLMClient + AgentClient
│   ├── agent_manager.py    # 提示词管理
│   └── chat_service.py     # 聊天业务逻辑（待实现）
│
├── api/                    # API 端点
├── core/                   # 核心配置
├── db/                     # 数据库连接
└── schemas/                # Pydantic 模型


uvicorn app.main:app --reload --port 3001





