"""
工具初始化

在应用启动时注册所有内置工具
"""
from app.core.logger import setup_logger
from app.tools.registry import tool_registry
from app.tools.calculator_tool import CalculatorTool

logger = setup_logger(__name__)


def init_tools():
    """
    初始化并注册所有内置工具
    
    在应用启动时调用一次
    """
    logger.info("=" * 50)
    logger.info("🔧 开始注册内置工具...")
    logger.info("=" * 50)
    
    # 注册计算器工具
    tool_registry.register(CalculatorTool())
    
    # TODO: 未来在这里添加更多工具
    # tool_registry.register(SearchTool())
    # tool_registry.register(WeatherTool())
    
    # 显示注册结果
    summary = tool_registry.get_summary()
    logger.info(f"")
    logger.info(f"✅ 工具注册完成")
    logger.info(f"   总数: {summary['total']}")
    logger.info(f"   启用: {summary['active']}")
    logger.info(f"   分类: {', '.join(summary['categories'])}")
    logger.info(f"")
    
    for tool_info in summary["tools"]:
        status = "✅" if tool_info["is_active"] else "❌"
        logger.info(f"   {status} {tool_info['display_name']} ({tool_info['name']}) - {tool_info['category']}")
    
    logger.info("=" * 50)
