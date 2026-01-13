"""
高德路线规划工具
规划两地之间的驾车或公交路线
"""
from typing import Any, Dict, Type, Optional
from pydantic import Field
import httpx

from app.tools.base import BaseTool, ToolInput, ToolMetadata
from app.core.config import settings


class GaodeRouteInput(ToolInput):
    """路线规划参数"""
    origin: str = Field(
        ...,
        description="起点位置，可以是地址（如：北京市朝阳区）或经纬度坐标（格式：经度,纬度）",
        json_schema_extra={"example": "北京市"}
    )
    destination: str = Field(
        ...,
        description="终点位置，可以是地址（如：上海市浦东新区）或经纬度坐标（格式：经度,纬度）",
        json_schema_extra={"example": "上海市"}
    )
    route_type: str = Field(
        default="driving",
        description="路线类型：driving-驾车路线，transit-公交路线",
        json_schema_extra={"example": "driving"}
    )
    city: Optional[str] = Field(
        default=None,
        description="城市名称（公交查询时必填），可以是城市名称或adcode",
        json_schema_extra={"example": "北京"}
    )


class GaodeRouteTool(BaseTool):
    """
    高德路线规划工具
    规划两地之间的最优路线，支持驾车和公交两种方式
    """
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gaode_route",
            display_name="路线规划",
            description="规划两个地点之间的最优路线。支持驾车导航和公交换乘方案，返回距离、预计时间和详细路径信息。起点和终点可以直接使用地址名称（如：北京市、上海市），工具会自动转换为坐标。",
            category="map_services",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        return GaodeRouteInput
    
    def _is_coordinate(self, location: str) -> bool:
        """
        检查是否为经纬度坐标格式
        格式：经度,纬度（如：116.481028,39.989643）
        """
        try:
            parts = location.split(',')
            if len(parts) != 2:
                return False
            float(parts[0])  # 经度
            float(parts[1])  # 纬度
            return True
        except:
            return False
    
    async def _address_to_coordinate(self, address: str) -> str:
        """
        将地址转换为经纬度坐标
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://restapi.amap.com/v3/geocode/geo",
                    params={
                        "key": settings.GAODE_API_KEY,
                        "address": address,
                        "output": "JSON"
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"地理编码失败: HTTP {response.status_code}")
                
                data = response.json()
                
                if data.get('status') != '1':
                    raise Exception(f"地理编码失败: {data.get('info', '未知错误')}")
                
                geocodes = data.get('geocodes', [])
                if not geocodes:
                    raise Exception(f"未找到地址 '{address}' 的地理编码")
                
                return geocodes[0].get('location', '')
                
        except Exception as e:
            raise Exception(f"地址 '{address}' 转换为坐标失败: {str(e)}")
    
    async def _call_gaode_api(
        self, 
        origin: str, 
        destination: str, 
        route_type: str,
        city: Optional[str]
    ) -> dict:
        """
        调用高德路线规划 API
        
        API 文档：
        - 驾车：https://lbs.amap.com/api/webservice/guide/api/direction
        - 公交：https://lbs.amap.com/api/webservice/guide/api/direction
        """
        try:
            params = {
                "key": settings.GAODE_API_KEY,
                "origin": origin,
                "destination": destination,
                "output": "JSON"
            }
            
            # 根据路线类型选择不同的 API 端点
            if route_type == "driving":
                url = "https://restapi.amap.com/v3/direction/driving"
            elif route_type == "transit":
                url = "https://restapi.amap.com/v3/direction/transit/integrated"
                # 公交路线必须指定城市
                if city:
                    params["city"] = city
            else:
                raise ValueError(f"不支持的路线类型: {route_type}")
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                
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
    
    async def _run(
        self, 
        origin: str, 
        destination: str, 
        route_type: str = "driving",
        city: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        路线规划查询
        
        Args:
            origin: 起点（可以是地址或经纬度）
            destination: 终点（可以是地址或经纬度）
            route_type: 路线类型（driving/transit）
            city: 城市名称（公交查询时必填）
            
        Returns:
            路线规划结果
        """
        try:
            # 验证公交查询必须提供城市
            if route_type == "transit" and not city:
                return {
                    "success": False,
                    "result": None,
                    "error": "公交路线查询必须指定城市参数"
                }
            
            # 转换地址为经纬度坐标（如果不是坐标格式）
            origin_coord = origin
            destination_coord = destination
            
            if not self._is_coordinate(origin):
                origin_coord = await self._address_to_coordinate(origin)
            
            if not self._is_coordinate(destination):
                destination_coord = await self._address_to_coordinate(destination)
            
            # 调用高德路线规划 API
            result = await self._call_gaode_api(
                origin=origin_coord,
                destination=destination_coord,
                route_type=route_type,
                city=city
            )
            
            # 解析结果
            if not result:
                return {
                    "success": False,
                    "result": None,
                    "error": "未找到可用的路线规划结果"
                }
            
            # 格式化路线规划数据
            if isinstance(result, dict):
                # 驾车路线
                if route_type == "driving" and result.get('route'):
                    route_data = result['route']
                    paths = route_data.get('paths', [])
                    
                    if paths:
                        path = paths[0]  # 取第一条路线
                        distance_km = float(path.get('distance', 0)) / 1000
                        duration_min = int(path.get('duration', 0)) / 60
                        
                        formatted = (
                            f"【驾车路线规划】\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"🚗 出发地：{origin}\n"
                            f"🏁 目的地：{destination}\n"
                        )
                        
                        # 如果进行了地址转换，显示坐标信息
                        if origin_coord != origin:
                            formatted += f"   （坐标：{origin_coord}）\n"
                        if destination_coord != destination:
                            formatted += f"   （坐标：{destination_coord}）\n"
                        
                        formatted += (
                            f"📏 总距离：{distance_km:.2f} 公里\n"
                            f"⏱️ 预计时间：{int(duration_min)} 分钟\n"
                        )
                        
                        # 添加路费信息
                        if path.get('tolls'):
                            formatted += f"💰 路费：{float(path.get('tolls', 0))} 元\n"
                        
                        # 添加红绿灯数量
                        if path.get('traffic_lights'):
                            formatted += f"🚦 红绿灯：{path.get('traffic_lights')} 个\n"
                        
                        # 添加步骤说明
                        steps = path.get('steps', [])
                        if steps:
                            formatted += f"\n【详细路线】（共{len(steps)}步）\n"
                            for i, step in enumerate(steps[:5], 1):  # 只显示前5步
                                instruction = step.get('instruction', '')
                                road_name = step.get('road', '')
                                step_distance = float(step.get('distance', 0))
                                formatted += f"{i}. {instruction} ({road_name}, {step_distance}米)\n"
                            
                            if len(steps) > 5:
                                formatted += f"... 还有 {len(steps) - 5} 步（详细路线请查看地图）"
                        
                        return {
                            "success": True,
                            "result": formatted,
                            "metadata": {
                                "distance_km": distance_km,
                                "duration_min": duration_min,
                                "tolls": path.get('tolls'),
                                "traffic_lights": path.get('traffic_lights')
                            }
                        }
                
                # 公交路线
                elif route_type == "transit" and result.get('route'):
                    route_data = result['route']
                    transits = route_data.get('transits', [])
                    
                    if transits:
                        formatted = (
                            f"【公交路线规划】\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"🚌 出发地：{origin}\n"
                            f"🏁 目的地：{destination}\n"
                        )
                        
                        # 如果进行了地址转换，显示坐标信息
                        if origin_coord != origin:
                            formatted += f"   （坐标：{origin_coord}）\n"
                        if destination_coord != destination:
                            formatted += f"   （坐标：{destination_coord}）\n"
                        
                        formatted += f"🏙️ 城市：{city}\n\n"
                        
                        # 显示前3条公交方案
                        for i, transit in enumerate(transits[:3], 1):
                            distance_km = float(transit.get('distance', 0)) / 1000
                            duration_min = int(transit.get('duration', 0)) / 60
                            
                            formatted += f"【方案{i}】\n"
                            formatted += f"   📏 距离：{distance_km:.2f} 公里\n"
                            formatted += f"   ⏱️ 时间：约 {int(duration_min)} 分钟\n"
                            
                            # 步行距离
                            if transit.get('walking_distance'):
                                walk_distance = float(transit.get('walking_distance', 0))
                                formatted += f"   🚶 步行：{walk_distance} 米\n"
                            
                            # 换乘次数
                            segments = transit.get('segments', [])
                            formatted += f"   🔄 换乘：{len(segments) - 1} 次\n"
                            
                            formatted += "\n"
                        
                        return {
                            "success": True,
                            "result": formatted,
                            "metadata": {
                                "transit_count": len(transits),
                                "origin": origin,
                                "destination": destination
                            }
                        }
            
            # 无法解析结果
            return {
                "success": False,
                "result": None,
                "error": "未能解析路线规划结果"
            }
            
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"路线规划失败: {str(e)}"
            }
