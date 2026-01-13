"""
计算器工具
支持基本的数学运算
"""
from typing import Any, Dict, Type
from pydantic import Field
import ast
import operator

from app.tools.base import BaseTool, ToolInput, ToolMetadata


class CalculatorInput(ToolInput):
    """计算器输入参数"""
    expression: str = Field(
        ...,
        description="要计算的数学表达式，例如: '2 + 3 * 4'",
        json_schema_extra={"example": "2 + 3 * 4"}
    )


class CalculatorTool(BaseTool):
    """
    安全的数学计算器工具
    支持: +, -, *, /, **, %, //(整除)
    """
    
    # 支持的运算符
    OPERATORS = {
        ast.Add: operator.add,#加法 +
        ast.Sub: operator.sub,#减法 -
        ast.Mult: operator.mul,#乘法 *
        ast.Div: operator.truediv,#除法 /
        ast.Pow: operator.pow,#幂 **
        ast.Mod: operator.mod,#取模 %
        ast.FloorDiv: operator.floordiv,#整除 //
        ast.USub: operator.neg,  # 负号
    }
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calculator",
            display_name="计算器",
            description="执行基本的数学计算，支持加减乘除、幂运算、取模等。例如：'2 + 3 * 4' 或 '10 ** 2'",
            category="math",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        return CalculatorInput
    
    def _safe_eval(self, node):
        """
        安全地求值 AST 节点
        只允许数字和基本运算符
        """
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # 兼容旧版本
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            operator_func = self.OPERATORS.get(type(node.op))
            if operator_func is None:
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            return operator_func(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._safe_eval(node.operand)
            operator_func = self.OPERATORS.get(type(node.op))
            if operator_func is None:
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            return operator_func(operand)
        elif isinstance(node, ast.Expression):
            return self._safe_eval(node.body)
        else:
            raise ValueError(f"不支持的表达式类型: {type(node).__name__}")
    
    async def _run(self, expression: str) -> Dict[str, Any]:
        """
        执行数学计算
        
        Args:
            expression: 数学表达式
            
        Returns:
            Dict: 包含计算结果
        """
        try:
            # 移除空格
            expression = expression.strip()
            
            if not expression:
                return {
                    "success": False,
                    "result": None,
                    "error": "表达式不能为空"
                }
            
            # 解析表达式为 AST
            parsed = ast.parse(expression, mode='eval')
            
            # 安全求值
            result = self._safe_eval(parsed)
            
            # 格式化结果
            if isinstance(result, float):
                # 如果是整数，去掉小数部分
                if result.is_integer():
                    result = int(result)
                else:
                    # 保留最多 8 位小数
                    result = round(result, 8)
            
            return {
                "success": True,
                "result": f"{expression} = {result}",
                "metadata": {
                    "expression": expression,
                    "value": result,
                    "type": type(result).__name__
                }
            }
            
        except ZeroDivisionError:
            return {
                "success": False,
                "result": None,
                "error": "除数不能为零"
            }
        except SyntaxError as e:
            return {
                "success": False,
                "result": None,
                "error": f"表达式语法错误: {str(e)}"
            }
        except ValueError as e:
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"计算失败: {str(e)}"
            }
