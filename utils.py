import requests
from config import API_CONFIG, SYSTEM_PROMPT

class AIModel:
    def __init__(self):
        self.api_key = API_CONFIG["api_key"]
        self.base_url = API_CONFIG["base_url"]
        self.config = API_CONFIG
        self.system_prompt = SYSTEM_PROMPT

    def generate_response(self, user_input, chat_history=None):
        if chat_history is None:
            chat_history = []
        
        # 构建消息历史
        messages = self._build_messages(chat_history, user_input)
        
        # 调用API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_tokens"],
            "top_p": self.config["top_p"],
            "frequency_penalty": self.config["frequency_penalty"],
            "presence_penalty": self.config["presence_penalty"]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"抱歉，发生了错误：{str(e)}"

    def _build_messages(self, chat_history, user_input):
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # 添加历史对话
        for msg in chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        return messages

def format_chat_history(chat_history):
    """格式化聊天历史，用于显示"""
    formatted_history = []
    for msg in chat_history:
        formatted_history.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    return formatted_history 