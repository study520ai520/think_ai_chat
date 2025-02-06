import streamlit as st
from utils import AIModel, format_chat_history
from config import PAGE_CONFIG, PRESET_MODELS, DEFAULT_API_CONFIG

# 配置页面
st.set_page_config(**PAGE_CONFIG)

# 初始化会话状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "api_config" not in st.session_state:
    st.session_state.api_config = DEFAULT_API_CONFIG.copy()
    st.session_state.api_config.update({
        "api_key": "",
        "model": list(PRESET_MODELS.values())[0]  # 默认使用第一个模型
    })

if "custom_models" not in st.session_state:
    st.session_state.custom_models = {}

if "ai_model" not in st.session_state:
    st.session_state.ai_model = AIModel(st.session_state.api_config)

if "current_request" not in st.session_state:
    st.session_state.current_request = None

# 页面标题
st.title("🤖 AI思考推理助手")

# 侧边栏配置
with st.sidebar:
    st.header("🛠️ 模型配置")
    
    # API设置
    with st.expander("API设置", expanded=True):
        # API Base URL
        base_url = st.text_input(
            "API Base URL",
            value=st.session_state.api_config["base_url"],
            help="设置API基础地址"
        )
        
        # API Key
        api_key = st.text_input(
            "API Key",
            value=st.session_state.api_config["api_key"],
            type="password",
            help="输入您的API密钥"
        )
        
        if base_url != st.session_state.api_config["base_url"] or \
           api_key != st.session_state.api_config["api_key"]:
            st.session_state.api_config.update({
                "base_url": base_url,
                "api_key": api_key
            })
            st.session_state.ai_model.update_config(st.session_state.api_config)
    
    # 模型选择
    with st.expander("模型选择", expanded=True):
        # 预设模型
        st.subheader("预设模型")
        selected_preset = st.selectbox(
            "选择预设模型",
            list(PRESET_MODELS.keys()),
            format_func=lambda x: f"📦 {x}",
            help="选择要使用的预设模型"
        )
        
        # 自定义模型
        st.subheader("自定义模型")
        custom_model_name = st.text_input("模型名称", key="new_model_name")
        custom_model_id = st.text_input("模型ID", key="new_model_id")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➕ 添加模型", help="添加自定义模型"):
                if custom_model_name and custom_model_id:
                    st.session_state.custom_models[custom_model_name] = custom_model_id
                    st.success(f"已添加模型: {custom_model_name}")
                else:
                    st.warning("请填写模型名称和ID")
        
        with col2:
            if st.button("🗑️ 清除全部", help="清除所有自定义模型"):
                st.session_state.custom_models = {}
                st.success("已清除所有自定义模型")
        
        # 显示现有的自定义模型
        if st.session_state.custom_models:
            st.subheader("已添加的自定义模型")
            for name, model_id in st.session_state.custom_models.items():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📝 {name}: {model_id}")
                with col2:
                    if st.button("删除", key=f"del_{name}", help=f"删除模型 {name}"):
                        del st.session_state.custom_models[name]
                        st.success(f"已删除模型: {name}")
                        st.experimental_rerun()
        
        # 合并所有模型选项
        all_models = {**PRESET_MODELS, **st.session_state.custom_models}
        selected_model = all_models[selected_preset]
        
        if selected_model != st.session_state.api_config["model"]:
            st.session_state.api_config["model"] = selected_model
            st.session_state.ai_model.update_config(st.session_state.api_config)
    
    # 高级设置
    with st.expander("高级设置"):
        max_tokens = st.number_input(
            "最大生成长度",
            min_value=1,
            max_value=130000,
            value=st.session_state.api_config.get("max_tokens", 8192),
            help="设置生成文本的最大长度"
        )
        
        if max_tokens != st.session_state.api_config.get("max_tokens"):
            st.session_state.api_config["max_tokens"] = max_tokens
            st.session_state.ai_model.update_config(st.session_state.api_config)
    
    # 添加分隔线
    st.divider()
    
    # 清空对话按钮
    if st.button("🗑️ 清空对话历史", type="secondary", help="清除所有对话记录"):
        st.session_state.chat_history = []
        st.session_state.current_request = None
        st.experimental_rerun()

def process_ai_response(prompt, chat_history):
    """处理AI响应的函数"""
    # 检查API配置
    if not st.session_state.api_config.get("api_key"):
        st.error("⚠️ 请先在侧边栏设置API Key")
        return
    
    # 创建占位符
    reasoning_placeholder = st.empty()
    response_placeholder = st.empty()
    
    # 用于累积内容
    full_reasoning = ""
    full_response = ""
    has_error = False
    
    # 显示初始状态
    with reasoning_placeholder.expander("正在思考...", expanded=True):
        reasoning_container = st.empty()
    
    response_container = response_placeholder.empty()
    
    # 处理流式响应
    for chunk in st.session_state.ai_model.generate_response_stream(
        prompt, 
        chat_history
    ):
        if chunk["type"] == "reasoning":
            full_reasoning += chunk["content"]
            with reasoning_placeholder.expander("思考过程", expanded=True):
                reasoning_container.markdown(f"### 🤔 思考过程\n{full_reasoning}")
        
        elif chunk["type"] == "response":
            full_response += chunk["content"]
            response_container.markdown(f"### 💡 回答\n{full_response}")
        
        elif chunk["type"] == "complete":
            # 更新为最终状态
            with reasoning_placeholder.expander("查看思考过程", expanded=False):
                reasoning_container.markdown(f"### 🤔 思考过程\n{chunk['content']['reasoning']}")
            response_container.markdown(f"### 💡 回答\n{chunk['content']['response']}")
            
            # 添加到历史记录
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": chunk["content"]
            })
            # 清除当前请求
            st.session_state.current_request = None
            
        elif chunk["type"] == "error":
            # 显示错误信息
            has_error = True
            with reasoning_placeholder.expander("思考过程出错", expanded=True):
                reasoning_container.error(chunk["content"]["reasoning"])
            response_container.error(chunk["content"]["response"])
            
            # 添加重试按钮
            col1, col2 = response_container.columns([3, 1])
            with col2:
                if st.button("🔄 重试", key="retry_button"):
                    # 保存当前请求信息以供重试
                    st.session_state.current_request = {
                        "prompt": prompt,
                        "chat_history": chat_history
                    }
                    st.experimental_rerun()

    return has_error

# 显示聊天历史
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        # 如果是AI回复，显示思考过程和回答
        if message["role"] == "assistant" and isinstance(message["content"], dict):
            # 创建一个可折叠的区域显示思考过程
            with st.expander("查看思考过程", expanded=False):
                st.markdown("### 🤔 思考过程")
                st.markdown(message["content"]["reasoning"])
            # 显示最终回答
            st.markdown("### 💡 回答")
            st.markdown(message["content"]["response"])
        else:
            st.write(message["content"])

# 检查是否有待重试的请求
if st.session_state.current_request:
    with st.chat_message("assistant"):
        process_ai_response(
            st.session_state.current_request["prompt"],
            st.session_state.current_request["chat_history"]
        )

# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息到历史
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # 显示用户消息
    with st.chat_message("user"):
        st.write(prompt)
    
    # 显示AI思考过程
    with st.chat_message("assistant"):
        process_ai_response(prompt, st.session_state.chat_history[:-1]) 