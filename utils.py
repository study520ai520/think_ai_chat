import requests
import json
import logging
from config import API_CONFIG, SYSTEM_PROMPT, DEFAULT_API_KEY

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class AIModel:
    def __init__(self):
        self.api_key = DEFAULT_API_KEY
        self.base_url = API_CONFIG["base_url"]
        self.config = API_CONFIG.copy()
        self.config["api_key"] = self.api_key
        self.system_prompt = SYSTEM_PROMPT
        logger.info("AIModel initialized with base_url: %s", self.base_url)

    def update_api_key(self, new_api_key):
        """更新API Key"""
        self.api_key = new_api_key
        self.config["api_key"] = new_api_key
        logger.info("API Key updated")

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
        
        # 检查API Key
        if not self.api_key:
            logger.error("API Key not set")
            yield {
                "type": "error",
                "content": {
                    "reasoning": "API Key未设置",
                    "response": "请先设置API Key"
                }
            }
            return
        
        # 构建消息历史
        messages = self._build_messages(chat_history, user_input)
        logger.debug("Built messages: %s", json.dumps(messages, ensure_ascii=False))
        
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
        logger.debug("API request data: %s", json.dumps(data, ensure_ascii=False))
        
        try:
            logger.info("Making API request to %s", self.base_url)
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                stream=True
            )
            response.raise_for_status()
            logger.info("API request successful")
            
            # 用于累积思考过程和最终回答
            reasoning_content = ""
            final_content = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                    
                try:
                    # 移除 "data: " 前缀并解析JSON
                    line = line.decode('utf-8')
                    logger.debug("Received line: %s", line)
                    
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        logger.info("Stream completed")
                        break
                        
                    chunk = json.loads(line)
                    if "choices" not in chunk:
                        logger.warning("No choices in chunk: %s", line)
                        continue
                        
                    delta = chunk["choices"][0].get("delta", {})
                    logger.debug("Delta content: %s", json.dumps(delta, ensure_ascii=False))
                    
                    # 检查是否有reasoning_content
                    reasoning_chunk = delta.get("reasoning_content", "")
                    if reasoning_chunk:
                        reasoning_content += reasoning_chunk
                        logger.debug("Added reasoning chunk: %s", reasoning_chunk)
                        yield {
                            "type": "reasoning",
                            "content": reasoning_chunk
                        }
                    
                    # 检查是否有content
                    content_chunk = delta.get("content", "")
                    if content_chunk:
                        final_content += content_chunk
                        logger.debug("Added content chunk: %s", content_chunk)
                        yield {
                            "type": "response",
                            "content": content_chunk
                        }
                        
                except json.JSONDecodeError as e:
                    logger.error("JSON解析错误: %s, 数据: %s", str(e), line)
                    continue
                except Exception as e:
                    logger.error("处理数据块时出错: %s, 数据: %s", str(e), line, exc_info=True)
                    continue
            
            # 返回完整的响应
            if reasoning_content or final_content:
                logger.info("Generation completed successfully")
                yield {
                    "type": "complete",
                    "content": {
                        "reasoning": reasoning_content or "未提供思考过程",
                        "response": final_content or "生成回答时出现问题"
                    }
                }
            else:
                logger.error("No valid content generated")
                raise Exception("未能获取有效的响应内容")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求错误：{str(e)}"
            logger.error(error_msg, exc_info=True)
            yield {
                "type": "error",
                "content": {
                    "reasoning": error_msg,
                    "response": f"抱歉，API请求失败：{str(e)}"
                }
            }
        except Exception as e:
            error_msg = f"API调用出错：{str(e)}"
            logger.error(error_msg, exc_info=True)
            yield {
                "type": "error",
                "content": {
                    "reasoning": error_msg,
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