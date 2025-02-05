import streamlit as st
from utils import AIModel, format_chat_history
from config import PAGE_CONFIG, MODEL_OPTIONS, PARAMETER_RANGES

# 配置页面
st.set_page_config(**PAGE_CONFIG)

# 初始化会话状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "ai_model" not in st.session_state:
    st.session_state.ai_model = AIModel()

# 页面标题
st.title("🤖 AI思考推理助手")

# 侧边栏配置
with st.sidebar:
    st.header("模型配置")
    
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
    # 添加用户消息到历史
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # 显示用户消息
    with st.chat_message("user"):
        st.write(prompt)
    
    # 显示AI思考过程
    with st.chat_message("assistant"):
        with st.spinner("AI正在思考..."):
            response = st.session_state.ai_model.generate_response(
                prompt, 
                st.session_state.chat_history[:-1]
            )
            
            # 创建一个可折叠的区域显示思考过程
            with st.expander("查看思考过程", expanded=False):
                st.markdown("### 🤔 思考过程")
                st.markdown(response["reasoning"])
            
            # 显示最终回答
            st.markdown("### 💡 回答")
            st.markdown(response["response"])
            
            # 添加AI回复到历史
            st.session_state.chat_history.append({"role": "assistant", "content": response}) 