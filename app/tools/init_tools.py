"""
工具初始化

在应用启动时注册所有内置工具
"""
from app.core.logger import setup_logger
from app.tools.registry import tool_registry
from app.tools.calculator_tool import CalculatorTool
from app.tools.search_tool import SearchTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.gaode_weather_tool import GaodeWeatherTool
from app.tools.gaode_geocode_tool import GaodeGeocodeTool
from app.tools.gaode_route_tool import GaodeRouteTool

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
    
    # 注册网络搜索工具
    tool_registry.register(SearchTool())
    
    # 注册日期时间工具
    tool_registry.register(DateTimeTool())
    
    # 注册高德地图工具
    tool_registry.register(GaodeWeatherTool())
    tool_registry.register(GaodeGeocodeTool())
    tool_registry.register(GaodeRouteTool())
    
    # TODO: 未来在这里添加更多工具
    
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
