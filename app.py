import streamlit as st
from utils import AIModel, format_chat_history
from config import PAGE_CONFIG

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
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    st.session_state.ai_model.model.config.temperature = temperature
    
    if st.button("清空对话历史"):
        st.session_state.chat_history = []
        st.experimental_rerun()

# 显示聊天历史
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
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
            st.write(response)
            
            # 添加AI回复到历史
            st.session_state.chat_history.append({"role": "assistant", "content": response}) 