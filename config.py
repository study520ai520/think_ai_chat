"""
配置文件
"""

# 页面配置
PAGE_CONFIG = {
    "page_title": "AI思考推理助手",
    "page_icon": "🤖",
    "layout": "centered",
    "initial_sidebar_state": "expanded"
}

# 默认API配置
DEFAULT_API_CONFIG = {
    "base_url": "https://api.deepseek.com/v1",
    "max_tokens": 8192,
}

# 预设模型列表
PRESET_MODELS = {
    "DeepSeek Chat": "deepseek-chat",
    "DeepSeek Reasoner": "deepseek-reasoner",
    "DeepSeek Code": "deepseek-coder",
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