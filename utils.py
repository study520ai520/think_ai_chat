import requests
import json
import logging
from config import API_CONFIG, SYSTEM_PROMPT, DEFAULT_API_KEY

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 默认级别改为INFO
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# 设置第三方库的日志级别
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class AIModel:
    def __init__(self):
        self.api_key = DEFAULT_API_KEY
        self.base_url = API_CONFIG["base_url"]
        self.config = API_CONFIG.copy()
        self.config["api_key"] = self.api_key
        self.system_prompt = SYSTEM_PROMPT
        logger.info("初始化AI模型，使用API地址: %s", self.base_url)

    def update_api_key(self, new_api_key):
        """更新API Key"""
        self.api_key = new_api_key
        self.config["api_key"] = new_api_key
        logger.info("API Key已更新")

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
            logger.error("未设置API Key")
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
        logger.info("开始生成回答，输入长度: %d", len(str(messages)))
        
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
            logger.info("正在调用API生成回答...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                stream=True
            )
            response.raise_for_status()
            logger.info("API连接成功，开始接收数据流")
            
            # 用于累积思考过程和最终回答
            reasoning_content = ""
            final_content = ""
            chunk_count = 0
            
            for line in response.iter_lines():
                if not line:
                    continue
                    
                try:
                    # 移除 "data: " 前缀并解析JSON
                    line = line.decode('utf-8')
                    # 打印原始数据
                    logger.debug("原始数据行: %r", line)
                    
                    if line.startswith("data: "):
                        line = line[6:]
                        logger.debug("处理后的数据: %r", line)
                    if line == "[DONE]":
                        logger.info("数据流接收完成")
                        break
                    
                    # 尝试解析前先检查数据是否为空
                    if not line.strip():
                        logger.warning("收到空数据行")
                        continue
                        
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error("JSON解析错误: %s, 原始数据: %r", str(e), line)
                        continue
                        
                    if "choices" not in chunk:
                        logger.warning("数据块中没有choices字段: %r", chunk)
                        continue
                        
                    delta = chunk["choices"][0].get("delta", {})
                    chunk_count += 1
                    
                    # 每100个数据块记录一次进度
                    if chunk_count % 100 == 0:
                        logger.info("已处理 %d 个数据块", chunk_count)
                    
                    # 检查是否有reasoning_content
                    reasoning_chunk = delta.get("reasoning_content", "")
                    if reasoning_chunk:
                        reasoning_content += reasoning_chunk
                        yield {
                            "type": "reasoning",
                            "content": reasoning_chunk
                        }
                    
                    # 检查是否有content
                    content_chunk = delta.get("content", "")
                    if content_chunk:
                        final_content += content_chunk
                        yield {
                            "type": "response",
                            "content": content_chunk
                        }
                        
                except Exception as e:
                    logger.error("处理数据块时出错: %s, 原始数据: %r", str(e), line, exc_info=True)
                    continue
            
            # 返回完整的响应
            if reasoning_content or final_content:
                logger.info("生成完成，思考过程长度: %d, 回答长度: %d", 
                          len(reasoning_content), len(final_content))
                yield {
                    "type": "complete",
                    "content": {
                        "reasoning": reasoning_content or "未提供思考过程",
                        "response": final_content or "生成回答时出现问题"
                    }
                }
            else:
                logger.error("未生成有效内容")
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