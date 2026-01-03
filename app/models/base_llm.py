from app.core.logger import setup_logger
from openai import OpenAI
from langchain.chat_models import init_chat_model
from app.core.config import settings
logger = setup_logger(__name__)

'''
初始化LLM模型配置
'''
def base_llm(client_instance=None):
    """
    创建并返回 llm 对象
    
    Args:
        client_instance: LLMClient实例（可选，用于未来扩展）
    
    Returns:
        LLM模型对象
    """
    try:
        llm = init_chat_model(
            model=settings.OPENAI_MODEL_NAMES,
            model_provider="openai",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_URL,
            temperature=0.7,
            max_tokens=1000,
            streaming=True
        )
        logger.info(f"LLM模型初始化成功: {settings.OPENAI_MODEL_NAMES}")
        return llm
    except Exception as e:
        logger.error(f"LLM模型初始化失败: {str(e)}")
        raise

    # # 通用模型调用
    # def base_llm(query,systrm_prompt):
    #     client = OpenAI(
    #         api_key=settings.OPENAI_API_KEY,
    #         base_url=settings.OPENAI_URL
    #     )
    #     completion = client.chat.completions.create(
    #         model=settings.OPENAI_MODEL_NAMES, 
    #         messages=[{'role': 'system', 'content': systrm_prompt},
    #                     {'role': 'user', 'content': query}],
    #         stream=True,
    #         stream_options={"include_usage": True}
    #         )
    #     returns = ''
    #     for chunk in completion:
    #         for che in chunk.choices:
    #             delta = che.delta.content
    #             returns += delta
    #             print(delta, end='', flush=True)
    #     print()
    #     return returns