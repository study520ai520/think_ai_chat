import streamlit as st
from utils import AIModel, format_chat_history
from config import PAGE_CONFIG, MODEL_OPTIONS, PARAMETER_RANGES, DEFAULT_API_KEY

# 配置页面
st.set_page_config(**PAGE_CONFIG)

# 初始化会话状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "api_key" not in st.session_state:
    st.session_state.api_key = DEFAULT_API_KEY

if "ai_model" not in st.session_state:
    st.session_state.ai_model = AIModel()

# 页面标题
st.title("🤖 AI思考推理助手")

# 侧边栏配置
with st.sidebar:
    st.header("模型配置")
    
    # API Key输入
    api_key = st.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        help="输入您的DeepSeek API Key，如果不填写则使用环境变量中的默认值"
    )
    
    # 如果API Key发生变化，更新模型配置
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key
        st.session_state.ai_model.update_api_key(api_key if api_key else DEFAULT_API_KEY)
    
    # 模型选择
    selected_model_name = st.selectbox(
        "选择模型",
        list(MODEL_OPTIONS.keys()),
        help="选择要使用的AI模型"
    )
    st.session_state.ai_model.config["model"] = MODEL_OPTIONS[selected_model_name]
    
    # 参数调整
    st.subheader("参数设置")
    for param, config in PARAMETER_RANGES.items():
        if config["type"] == "float":
            value = st.slider(
                f"{param} - {config['description']}",
                min_value=float(config['min']),
                max_value=float(config['max']),
                value=float(config['default']),
                step=float(config['step']),
                help=config['description']
            )
        else:  # int类型
            value = st.slider(
                f"{param} - {config['description']}",
                min_value=int(config['min']),
                max_value=int(config['max']),
                value=int(config['default']),
                step=int(config['step']),
                help=config['description']
            )
        st.session_state.ai_model.config[param] = value
    
    # 添加分隔线
    st.divider()
    
    # 清空对话按钮
    if st.button("清空对话历史", type="secondary"):
        st.session_state.chat_history = []
        st.experimental_rerun()

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

# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    # 检查是否有API Key
    if not st.session_state.api_key:
        st.error("请先在侧边栏设置API Key或在环境变量中配置DEEPSEEK_API_KEY")
    else:
        # 添加用户消息到历史
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # 显示用户消息
        with st.chat_message("user"):
            st.write(prompt)
        
        # 显示AI思考过程
        with st.chat_message("assistant"):
            # 创建占位符
            reasoning_placeholder = st.empty()
            response_placeholder = st.empty()
            
            # 用于累积内容
            full_reasoning = ""
            full_response = ""
            
            # 显示初始状态
            with reasoning_placeholder.expander("正在思考...", expanded=True):
                reasoning_container = st.empty()
            
            response_container = response_placeholder.empty()
            
            # 处理流式响应
            for chunk in st.session_state.ai_model.generate_response_stream(
                prompt, 
                st.session_state.chat_history[:-1]
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
                
                elif chunk["type"] == "error":
                    # 显示错误信息
                    with reasoning_placeholder.expander("思考过程出错", expanded=True):
                        reasoning_container.error(chunk["content"]["reasoning"])
                    response_container.error(chunk["content"]["response"]) 