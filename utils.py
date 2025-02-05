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
            response_data = response.json()
            
            # 获取思考过程和最终回答
            reasoning_content = response_data["choices"][0]["message"].get("reasoning_content", "")
            final_content = response_data["choices"][0]["message"]["content"]
            
            return {
                "reasoning": reasoning_content,
                "response": final_content
            }
        except Exception as e:
            return {
                "reasoning": f"思考过程出错：{str(e)}",
                "response": f"抱歉，发生了错误：{str(e)}"
            }

    def generate_response_stream(self, user_input, chat_history=None):
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
            "presence_penalty": self.config["presence_penalty"],
            "stream": True  # 启用流式输出
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                stream=True
            )
            response.raise_for_status()
            
            # 用于累积思考过程和最终回答
            reasoning_content = ""
            final_content = ""
            is_reasoning = True  # 标记当前是否在输出思考过程
            
            for line in response.iter_lines():
                if line:
                    # 移除 "data: " 前缀并解析JSON
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                        
                    try:
                        chunk = response.json()
                        delta = chunk["choices"][0]["delta"]
                        
                        # 检查是否有reasoning_content
                        if "reasoning_content" in delta:
                            is_reasoning = True
                            reasoning_chunk = delta["reasoning_content"]
                            reasoning_content += reasoning_chunk
                            yield {
                                "type": "reasoning",
                                "content": reasoning_chunk
                            }
                        
                        # 检查是否有content
                        if "content" in delta:
                            is_reasoning = False
                            content_chunk = delta["content"]
                            final_content += content_chunk
                            yield {
                                "type": "response",
                                "content": content_chunk
                            }
                            
                    except Exception as e:
                        continue
            
            # 返回完整的响应
            yield {
                "type": "complete",
                "content": {
                    "reasoning": reasoning_content,
                    "response": final_content
                }
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "content": {
                    "reasoning": f"思考过程出错：{str(e)}",
                    "response": f"抱歉，发生了错误：{str(e)}"
                }
            }

    def _build_messages(self, chat_history, user_input):
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # 添加历史对话
        for msg in chat_history:
            if isinstance(msg["content"], dict):
                # 如果是字典格式，只使用response部分
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]["response"]
                })
            else:
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