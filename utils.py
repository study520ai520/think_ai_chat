import requests
import json
import logging
import time
import re
from config import SYSTEM_PROMPT

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

def extract_think_content(text):
    """提取<think>标签中的内容"""
    think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
    matches = think_pattern.findall(text)
    
    if matches:
        # 提取思考内容
        thinking = '\n'.join(matches)
        # 移除原文中的think标签及其内容
        response = think_pattern.sub('', text).strip()
        return thinking, response
    
    return None, text

class APIError(Exception):
    """API调用相关错误"""
    pass

class AIModel:
    def __init__(self, config):
        """初始化AI模型
        
        Args:
            config (dict): 模型配置，包含api_key、base_url、model等
        """
        self.config = config.copy()
        self.system_prompt = SYSTEM_PROMPT
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试间隔（秒）
        logger.info("初始化AI模型，使用API地址: %s", self.config.get("base_url"))

    def update_config(self, new_config):
        """更新模型配置
        
        Args:
            new_config (dict): 新的配置信息
        """
        self.config.update(new_config)
        logger.info("模型配置已更新")

    def _make_api_request(self, url, headers, data, stream=False):
        """发送API请求，带重试机制"""
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    stream=stream
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:  # 最后一次重试
                    raise APIError(f"API请求失败（已重试{self.max_retries}次）：{str(e)}")
                logger.warning("API请求失败，%d秒后重试（%d/%d）: %s", 
                             self.retry_delay, attempt + 1, self.max_retries, str(e))
                time.sleep(self.retry_delay)

    def _format_message_for_api(self, message):
        """格式化消息以适应API要求"""
        if isinstance(message["content"], dict):
            # 如果是助手的回复，合并思考过程和回答
            content = message["content"]
            formatted_content = ""
            if content.get("reasoning"):
                formatted_content += f"思考过程：\n{content['reasoning']}\n\n"
            if content.get("response"):
                formatted_content += f"回答：\n{content['response']}"
            return {
                "role": message["role"],
                "content": formatted_content.strip()
            }
        else:
            # 用户消息直接返回
            return message

    def generate_response_stream(self, user_input, chat_history=None):
        if chat_history is None:
            chat_history = []
        
        # 检查API配置
        if not self.config.get("api_key"):
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
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config["model"],
            "messages": messages,
            "max_tokens": self.config.get("max_tokens", 8192),
            "stream": True  # 启用流式输出
        }
        
        try:
            logger.info("正在调用API生成回答...")
            response = self._make_api_request(
                f"{self.config['base_url']}/chat/completions",
                headers=headers,
                data=data,
                stream=True
            )
            logger.info("API连接成功，开始接收数据流")
            
            # 用于累积思考过程和最终回答
            reasoning_content = ""
            final_content = ""
            chunk_count = 0
            last_error_time = 0  # 上次错误时间
            error_count = 0  # 连续错误计数
            
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
                        error_count = 0  # 重置错误计数
                    except json.JSONDecodeError as e:
                        current_time = time.time()
                        if current_time - last_error_time > self.retry_delay:
                            error_count = 1
                        else:
                            error_count += 1
                            
                        last_error_time = current_time
                        
                        if error_count >= self.max_retries:
                            logger.error("连续JSON解析错误达到最大重试次数")
                            raise APIError("数据解析失败，请稍后重试")
                            
                        logger.warning("JSON解析错误（%d/%d）: %s, 原始数据: %r", 
                                     error_count, self.max_retries, str(e), line)
                        continue
                        
                    if "choices" not in chunk:
                        logger.warning("数据块中没有choices字段: %r", chunk)
                        continue
                        
                    delta = chunk["choices"][0].get("delta", {})
                    chunk_count += 1
                    
                    # 每100个数据块记录一次进度
                    if chunk_count % 100 == 0:
                        logger.info("已处理 %d 个数据块", chunk_count)
                    
                    # 检查是否有content
                    content_chunk = delta.get("content", "")
                    if content_chunk:
                        final_content += content_chunk
                        # 检查是否包含<think>标签
                        thinking, response = extract_think_content(final_content)
                        if thinking:
                            # 更新思考内容
                            yield {
                                "type": "reasoning",
                                "content": thinking
                            }
                            # 更新回答内容
                            yield {
                                "type": "response",
                                "content": response
                            }
                        else:
                            # 没有<think>标签，直接作为回答内容
                            yield {
                                "type": "response",
                                "content": content_chunk
                            }
                        
                except Exception as e:
                    logger.error("处理数据块时出错: %s, 原始数据: %r", str(e), line, exc_info=True)
                    continue
            
            # 返回完整的响应
            if final_content:
                # 最后再次检查是否有<think>标签
                thinking, response = extract_think_content(final_content)
                logger.info("生成完成，思考过程长度: %d, 回答长度: %d", 
                          len(thinking) if thinking else 0, len(response))
                yield {
                    "type": "complete",
                    "content": {
                        "reasoning": thinking if thinking else "未提供思考过程",
                        "response": response
                    }
                }
            else:
                logger.error("未生成有效内容")
                raise APIError("未能获取有效的响应内容")
            
        except APIError as e:
            error_msg = str(e)
            logger.error(error_msg)
            yield {
                "type": "error",
                "content": {
                    "reasoning": error_msg,
                    "response": f"抱歉，{error_msg}"
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
        """构建完整的消息历史"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # 添加历史对话
        for msg in chat_history:
            formatted_msg = self._format_message_for_api(msg)
            messages.append(formatted_msg)
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        # 记录完整的消息历史用于调试
        logger.debug("完整的消息历史: %s", json.dumps(messages, ensure_ascii=False))
        
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