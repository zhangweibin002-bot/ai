
from app.core.config import settings
from app.core.logger import setup_logger
logger = setup_logger(__name__)

class system_prompts:
    def base_llm_prompt():
        '''
        通用模型的系统提示语
        '''
        prompt = '你是小明,一个乐于助人的AI助理。'
        return prompt