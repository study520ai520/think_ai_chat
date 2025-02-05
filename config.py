import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 页面配置
PAGE_CONFIG = {
    "page_title": "AI思考推理助手",
    "page_icon": "🤖",
    "layout": "centered",
    "initial_sidebar_state": "expanded"
}

# DeepSeek API配置
API_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY"),
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 2000,
    "top_p": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 0
}

# 系统提示词
SYSTEM_PROMPT = """你是一个专业的AI思考推理助手。你的主要职责是：
1. 深入分析问题，提供清晰的思考过程
2. 运用逻辑推理能力，给出合理的解决方案
3. 在回答中展示分析、推理的完整过程
4. 保持客观中立，提供多角度的思考
5. 必要时使用图表或结构化形式展示思路

请记住：
- 始终保持逻辑性和条理性
- 说明推理依据和思考过程
- 如有不确定，要明确指出
- 鼓励用户进行深入思考
""" 