"""
高德天气查询工具
直接调用高德地图 API
"""
from typing import Any, Dict, Type
from pydantic import Field
import httpx

from app.tools.base import BaseTool, ToolInput, ToolMetadata
from app.core.config import settings


class GaodeWeatherInput(ToolInput):
    """天气查询参数"""
    city: str = Field(
        ...,
        description="要查询的城市名称，如：北京、上海、深圳、广州等",
        json_schema_extra={"example": "北京"}
    )
    extensions: str = Field(
        default="base",
        description="返回信息类型：base-实况天气，all-天气预报",
        json_schema_extra={"example": "base"}
    )


class GaodeWeatherTool(BaseTool):
    """
    高德天气查询工具
    查询中国城市的实时天气或天气预报
    """
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gaode_weather",
            display_name="天气查询",
            description="查询中国城市的实时天气信息或天气预报。支持查询温度、湿度、风向、风力等信息。",
            category="map_services",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        return GaodeWeatherInput
    
    async def _call_gaode_api(self, city: str, extensions: str) -> dict:
        """
        调用高德天气 API
        
        API 文档：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://restapi.amap.com/v3/weather/weatherInfo",
                    params={
                        "key": settings.GAODE_API_KEY,
                        "city": city,
                        "extensions": extensions,
                        "output": "JSON"
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                # 检查 API 返回状态
                if data.get('status') != '1':
                    error_msg = data.get('info', '未知错误')
                    raise Exception(f"高德API错误: {error_msg}")
                
                return data
                
        except httpx.TimeoutException:
            raise Exception("请求超时，请稍后重试")
        except httpx.HTTPError as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise e
    
    async def _run(self, city: str, extensions: str = "base") -> Dict[str, Any]:
        """
        查询天气
        
        Args:
            city: 城市名称
            extensions: base-实况天气，all-天气预报
            
        Returns:
            天气信息
        """
        try:
            # 调用高德天气 API
            result = await self._call_gaode_api(city, extensions)
            
            # 解析结果
            if not result:
                return {
                    "success": False,
                    "result": None,
                    "error": f"未查询到 '{city}' 的天气信息"
                }
            
            # 格式化天气数据
            # 实况天气
            if extensions == "base" and result.get('lives'):
                weather_data = result['lives'][0]
                formatted = (
                    f"【{weather_data.get('province')} {weather_data.get('city')}】实时天气\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🌡️ 温度：{weather_data.get('temperature')}℃\n"
                    f"☁️ 天气：{weather_data.get('weather')}\n"
                    f"💧 湿度：{weather_data.get('humidity')}%\n"
                    f"🌬️ 风向：{weather_data.get('winddirection')}风\n"
                    f"💨 风力：{weather_data.get('windpower')}级\n"
                    f"📅 更新时间：{weather_data.get('reporttime')}"
                )
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": weather_data
                }
            
            # 天气预报
            elif extensions == "all" and result.get('forecasts'):
                forecast_data = result['forecasts'][0]
                casts = forecast_data.get('casts', [])
                
                formatted = f"【{forecast_data.get('province')} {forecast_data.get('city')}】天气预报\n━━━━━━━━━━━━━━━━\n"
                
                for cast in casts[:4]:  # 显示4天预报
                    formatted += (
                        f"\n📅 {cast.get('date')} {cast.get('week')}\n"
                        f"   白天：{cast.get('dayweather')} {cast.get('daytemp')}℃ {cast.get('daywind')}风{cast.get('daypower')}级\n"
                        f"   夜间：{cast.get('nightweather')} {cast.get('nighttemp')}℃ {cast.get('nightwind')}风{cast.get('nightpower')}级\n"
                    )
                
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": forecast_data
                }
            
            # 无法解析结果
            return {
                "success": False,
                "result": None,
                "error": f"未能解析 '{city}' 的天气数据"
            }
            
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"天气查询失败: {str(e)}"
            }
