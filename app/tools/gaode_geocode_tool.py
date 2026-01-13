"""
高德地理编码工具
将地址转换为经纬度坐标
"""
from typing import Any, Dict, Type, Optional
from pydantic import Field
import httpx

from app.tools.base import BaseTool, ToolInput, ToolMetadata
from app.core.config import settings


class GaodeGeocodeInput(ToolInput):
    """地理编码参数"""
    address: str = Field(
        ...,
        description="要查询的结构化地址信息，支持多关键字按层级查询，如：北京市海淀区中关村大街1号",
        json_schema_extra={"example": "北京市朝阳区望京SOHO"}
    )
    city: Optional[str] = Field(
        default=None,
        description="指定查询的城市（可选），可以是城市名称、adcode或citycode",
        json_schema_extra={"example": "北京"}
    )


class GaodeGeocodeTool(BaseTool):
    """
    高德地理编码工具
    将地址转换为经纬度坐标，可用于定位、导航等场景
    """
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gaode_geocode",
            display_name="地理编码",
            description="将中文地址转换为经纬度坐标。输入地址字符串，返回对应的经纬度、行政区划等信息。适用于地址定位、地图标注等场景。",
            category="map_services",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        return GaodeGeocodeInput
    
    async def _call_gaode_api(self, address: str, city: Optional[str]) -> dict:
        """
        调用高德地理编码 API
        
        API 文档：https://lbs.amap.com/api/webservice/guide/api/georegeo
        """
        try:
            params = {
                "key": settings.GAODE_API_KEY,
                "address": address,
                "output": "JSON"
            }
            
            # 添加城市参数（可选）
            if city:
                params["city"] = city
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://restapi.amap.com/v3/geocode/geo",
                    params=params
                )
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                # 检查 API 返回状态
                if data.get('status') != '1':
                    error_msg = data.get('info', '未知错误')
                    raise Exception(f"高德API错误: {error_msg}")
                
                # 返回第一个匹配结果
                geocodes = data.get('geocodes', [])
                if geocodes:
                    return geocodes[0]
                else:
                    return {}
                
        except httpx.TimeoutException:
            raise Exception("请求超时，请稍后重试")
        except httpx.HTTPError as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise e
    
    async def _run(self, address: str, city: Optional[str] = None) -> Dict[str, Any]:
        """
        地理编码查询
        
        Args:
            address: 地址信息
            city: 城市名称（可选）
            
        Returns:
            经纬度和地理信息
        """
        try:
            # 调用高德地理编码 API
            result = await self._call_gaode_api(address, city)
            
            # 解析结果
            if not result:
                return {
                    "success": False,
                    "result": None,
                    "error": f"未找到地址 '{address}' 的地理编码信息"
                }
            
            # 格式化地理编码数据
            if result.get('location'):
                location = result.get('location', '').split(',')
                
                formatted = (
                    f"【地理编码结果】\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📍 地址：{result.get('formatted_address', address)}\n"
                    f"🌐 经度：{location[0] if len(location) > 0 else '未知'}\n"
                    f"🌐 纬度：{location[1] if len(location) > 1 else '未知'}\n"
                )
                
                # 添加行政区划信息
                if result.get('province'):
                    formatted += f"📌 省份：{result.get('province')}\n"
                if result.get('city'):
                    formatted += f"🏙️ 城市：{result.get('city')}\n"
                if result.get('district'):
                    formatted += f"🏘️ 区县：{result.get('district')}\n"
                if result.get('adcode'):
                    formatted += f"🔢 区划代码：{result.get('adcode')}\n"
                
                # 添加匹配级别
                if result.get('level'):
                    formatted += f"📊 匹配级别：{result.get('level')}"
                
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": {
                        "longitude": location[0] if len(location) > 0 else None,
                        "latitude": location[1] if len(location) > 1 else None,
                        "formatted_address": result.get('formatted_address'),
                        "adcode": result.get('adcode'),
                        "level": result.get('level')
                    }
                }
            
            # 无法解析结果
            return {
                "success": False,
                "result": None,
                "error": f"未找到地址 '{address}' 的有效地理编码"
            }
            
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"地理编码查询失败: {str(e)}"
            }
