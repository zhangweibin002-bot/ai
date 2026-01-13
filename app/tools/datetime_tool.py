"""
日期时间工具
获取当前实时日期、时间、星期等信息
"""
from typing import Any, Dict, Type
from pydantic import Field
from datetime import datetime
import pytz

from app.tools.base import BaseTool, ToolInput, ToolMetadata


class DateTimeInput(ToolInput):
    """日期时间查询参数"""
    timezone: str = Field(
        default="Asia/Shanghai",
        description="时区，默认为北京时间（Asia/Shanghai）",
        json_schema_extra={"example": "Asia/Shanghai"}
    )
    format_type: str = Field(
        default="full",
        description="返回格式类型：full-完整信息，date-仅日期，time-仅时间，timestamp-时间戳",
        json_schema_extra={"example": "full"}
    )


class DateTimeTool(BaseTool):
    """
    日期时间工具
    获取当前的日期、时间、星期等实时信息
    """
    
    # 中文星期映射
    WEEKDAY_CN = {
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日"
    }
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_datetime",
            display_name="日期时间查询",
            description="获取当前实时的日期和时间信息。可以查询年月日、时分秒、星期几、时间戳等。支持不同时区。",
            category="utility",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        return DateTimeInput
    
    async def _run(self, timezone: str = "Asia/Shanghai", format_type: str = "full") -> Dict[str, Any]:
        """
        获取当前日期时间
        
        Args:
            timezone: 时区（默认：Asia/Shanghai）
            format_type: 格式类型（full/date/time/timestamp）
            
        Returns:
            日期时间信息
        """
        try:
            # 获取指定时区的当前时间
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except:
                # 如果时区无效，使用北京时间
                tz = pytz.timezone("Asia/Shanghai")
                now = datetime.now(tz)
            
            # 获取星期几
            weekday = now.weekday()
            weekday_cn = self.WEEKDAY_CN.get(weekday, "未知")
            
            # 根据不同格式返回
            if format_type == "date":
                # 仅返回日期
                formatted = f"{now.year}年{now.month}月{now.day}日 {weekday_cn}"
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": {
                        "year": now.year,
                        "month": now.month,
                        "day": now.day,
                        "weekday": weekday_cn,
                        "timezone": timezone
                    }
                }
            
            elif format_type == "time":
                # 仅返回时间
                formatted = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": {
                        "hour": now.hour,
                        "minute": now.minute,
                        "second": now.second,
                        "timezone": timezone
                    }
                }
            
            elif format_type == "timestamp":
                # 返回时间戳
                timestamp = int(now.timestamp())
                formatted = f"Unix时间戳: {timestamp}"
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": {
                        "timestamp": timestamp,
                        "timezone": timezone
                    }
                }
            
            else:  # format_type == "full" 或其他
                # 返回完整信息
                formatted = (
                    f"【当前日期时间】\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📅 日期：{now.year}年{now.month}月{now.day}日\n"
                    f"🕐 时间：{now.hour:02d}:{now.minute:02d}:{now.second:02d}\n"
                    f"📆 星期：{weekday_cn}\n"
                    f"🌍 时区：{timezone}\n"
                    f"⏱️ 时间戳：{int(now.timestamp())}\n"
                    f"📝 标准格式：{now.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                return {
                    "success": True,
                    "result": formatted,
                    "metadata": {
                        "year": now.year,
                        "month": now.month,
                        "day": now.day,
                        "hour": now.hour,
                        "minute": now.minute,
                        "second": now.second,
                        "weekday": weekday_cn,
                        "weekday_num": weekday,
                        "timezone": timezone,
                        "timestamp": int(now.timestamp()),
                        "iso_format": now.isoformat(),
                        "standard_format": now.strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
            
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"获取日期时间失败: {str(e)}"
            }
