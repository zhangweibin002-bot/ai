"""
网络搜索工具
使用 Ollama 官方的 web_search 功能
"""
from typing import Any, Dict, Type, List
from pydantic import Field
import asyncio
from functools import partial
import os
import re
from bs4 import BeautifulSoup
from readability import Document

from app.tools.base import BaseTool, ToolInput, ToolMetadata
from app.core.config import settings

class SearchInput(ToolInput):
    """搜索输入参数"""
    query: str = Field(
        ...,
        description="要搜索的关键词或问题",
        json_schema_extra={"example": "Python 异步编程教程"}
    )


class SearchTool(BaseTool):
    """
    网络搜索工具
    使用 Ollama 官方的 web_search API
    """
    
    def __init__(self):
        super().__init__()
        # 配置 Ollama API Key
        self.api_key = settings.OLLAMA_API_KEY
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_search",
            display_name="网络搜索",
            description="在互联网上搜索最新信息。当需要查找实时数据、新闻、事实核查或获取网络资源时使用此工具。",
            category="search",
            version="1.0.0",
            author="System"
        )
    
    def get_input_schema(self) -> Type[ToolInput]:
        return SearchInput
    
    def extract_clean_text(self, html: str) -> str:
        """
        从 HTML 中提取干净的文本内容
        
        Args:
            html: HTML 字符串
            
        Returns:
            清理后的纯文本
        """
        try:
            # 1. readability 提取正文
            doc = Document(html)
            content_html = doc.summary()

            # 2. BeautifulSoup 解析
            soup = BeautifulSoup(content_html, "html.parser")

            paragraphs = []
            for p in soup.find_all('p'):  # 只保留 <p> 段落
                text = p.get_text()
                
                # 去掉脚注 [1] [2] 等
                text = re.sub(r'\[\d+\]', '', text)
                
                # 去掉 Markdown 或类似的链接 [文本](url)
                text = re.sub(r'\[.*?\]\(.*?\)', '', text)
                
                text = text.strip()
                if text:  # 只保留非空段落
                    paragraphs.append(text)

            # 合并段落
            clean_text = ' '.join(paragraphs)
            
            # 去掉多余空格
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            return clean_text
        except Exception as e:
            # 如果清理失败，返回原始文本（去掉 HTML 标签）
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text().strip()
    
    def _call_ollama_search(self, query: str) -> str:
        """
        同步调用 Ollama web_search（在线程池中执行）
        """
        # 临时设置环境变量（ollama SDK 会读取它）
        old_key = os.environ.get("OLLAMA_API_KEY")
        os.environ["OLLAMA_API_KEY"] = self.api_key
        
        try:
            import ollama
            response = ollama.web_search(query)
            return response
        finally:
            # 恢复原来的环境变量
            if old_key is not None:
                os.environ["OLLAMA_API_KEY"] = old_key
            elif "OLLAMA_API_KEY" in os.environ:
                del os.environ["OLLAMA_API_KEY"]
    
    async def _run(self, query: str) -> Dict[str, Any]:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            
        Returns:
            Dict: 包含搜索结果（前4条，清理后的内容）
        """
        try:
            if not query or not query.strip():
                return {
                    "success": False,
                    "result": None,
                    "error": "搜索关键词不能为空"
                }
            
            # 在线程池中运行同步的 web_search（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._call_ollama_search,
                query.strip()
            )
            
            # 检查响应
            if not response:
                return {
                    "success": True,
                    "result": f"未找到关于 '{query}' 的相关结果",
                    "metadata": {
                        "query": query,
                        "results_count": 0
                    }
                }
            
            # 解析响应
            results = []
            
            # Ollama web_search 返回的是一个对象，需要转换
            # 检查是否有 results 属性
            if hasattr(response, 'results'):
                results_list = response.results[:4]  # 只取前4条
            elif isinstance(response, str):
                # 尝试解析 JSON
                import json
                try:
                    response_data = json.loads(response)
                    results_list = response_data.get('results', [])[:4]
                except:
                    # 无法解析，返回简化的文本
                    cleaned = self.extract_clean_text(str(response))
                    if len(cleaned) > 1000:
                        cleaned = cleaned[:1000] + "..."
                    return {
                        "success": True,
                        "result": f"搜索 '{query}' 的结果：\n\n{cleaned}",
                        "metadata": {
                            "query": query,
                            "response": cleaned
                        }
                    }
            elif isinstance(response, list):
                results_list = response[:4]
            elif isinstance(response, dict):
                results_list = response.get('results', [])[:4]
            else:
                results_list = []
            
            # 处理前4条结果并清理内容
            for i, item in enumerate(results_list, 1):
                try:
                    # 处理不同的数据结构
                    if hasattr(item, 'title'):  # 对象属性
                        title = getattr(item, 'title', '无标题')
                        url = getattr(item, 'url', '')
                        content_raw = getattr(item, 'content', '') or getattr(item, 'snippet', '')
                    elif isinstance(item, dict):  # 字典
                        title = item.get('title', '无标题')
                        url = item.get('url', '')
                        content_raw = item.get('content', '') or item.get('snippet', '') or item.get('description', '')
                    else:
                        continue
                    
                    # 清理内容中的HTML标签
                    if content_raw:
                        # 转换为字符串
                        content_str = str(content_raw)
                        
                        # 使用 BeautifulSoup 去除HTML标签
                        clean_content = self.extract_clean_text(content_str)
                        
                    else:
                        clean_content = "暂无内容摘要"
                    
                    results.append({
                        "index": i,
                        "title": str(title),  # 标题也限制长度
                        "url": str(url),      # URL限制长度
                        "content": clean_content
                    })
                except Exception as e:
                    # 单条结果处理失败，跳过
                    continue
            
            # 如果没有提取到结果
            if not results:
                return {
                    "success": True,
                    "result": f"搜索 '{query}' 未找到有效结果。可能是搜索API返回了空结果或结果格式无法解析。",
                    "metadata": {
                        "query": query,
                        "results_count": 0
                    }
                }
            
            # 格式化结果（供 AI 总结，已清理HTML）
            formatted_results = []
            for r in results:
                formatted_results.append(
                    f"{r['index']}. 【{r['title']}】\n"
                    f"   来源: {r['url']}\n"
                    f"   内容: {r['content']}"
                )
            
            result_text = (
                f"搜索 '{query}' 找到以下 {len(results)} 条信息：\n\n" + 
                "\n\n".join(formatted_results) +
                "\n\n请基于以上内容回答用户的问题。"
            )
            
            # 最终安全检查：确保结果不超过20KB（数据库TEXT类型限制约64KB，留出余量）
            if len(result_text) > 20000:
                result_text = result_text[:20000] + "\n\n[内容过长已截断]"
            
            return {
                "success": True,
                "result": result_text,
                "metadata": {
                    "query": query,
                    "results_count": len(results),
                    "results": results
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            # 提供更友好的错误信息
            if "Authorization" in error_msg or "Bearer" in error_msg or "token" in error_msg.lower():
                return {
                    "success": False,
                    "result": None,
                    "error": f"API 认证失败，请检查 OLLAMA_API_KEY 配置: {error_msg}"
                }
            elif "timeout" in error_msg.lower():
                return {
                    "success": False,
                    "result": None,
                    "error": "搜索请求超时，请稍后重试"
                }
            else:
                return {
                    "success": False,
                    "result": None,
                    "error": f"搜索失败: {error_msg}"
                }
