import streamlit as st
from openai import OpenAI
from PIL import Image
from utils.graphic_pro import get_base64_image
from utils.print_pro import render_combined_markdown
from utils.pdf_pro import read_pdf, chunk_text, vectorize_text_chunks, find_most_similar_chunks
from google import genai

# Initialize OpenAI client with API key from Streamlit secrets
client_openai = OpenAI(api_key=st.secrets["ai_key"])
OpenAI.api_key = st.secrets["ai_key"]
gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

client_deepseek = OpenAI(api_key=st.secrets["deepseek_key"], base_url="https://api.deepseek.com")

# Authentication check
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("You must log in first.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Quantrade",
    page_icon="photo/ai_logo_4.png",
    layout="wide"
)

# Sidebar
st.sidebar.markdown(f"Logged in as: **{st.session_state['username']}**")
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.switch_page("main.py")

st.sidebar.markdown("---")
sidebar_logo = Image.open("photo/ai_logo_4.png")
st.sidebar.image(sidebar_logo, use_container_width=True)

# ---------------------- Initialize States ----------------------
if "messages_text" not in st.session_state:
    st.session_state.messages_text = []
if "context_input_text" not in st.session_state:
    st.session_state.context_input_text = ""

if "messages_pdf" not in st.session_state:
    st.session_state.messages_pdf = []
if "last_processed_input_pdf" not in st.session_state:
    st.session_state.last_processed_input_pdf = None

# Memory states
if "memory_enabled" not in st.session_state:
    st.session_state.memory_enabled = False
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = []


# ---------------------- System Prompt ----------------------
def get_system_prompt():
    if chat_mode == "Coder":
        return (
            "You are a skilled programmer. "
            "Write clean, well-structured, and well-commented code. "
            "Use consistent formatting, clear variable names, "
            "and explain your approach where useful."
        )
    elif chat_mode == "Pro":
        return (
            "You are a professional consultant. "
            "Provide responses that are clear, concise, and well-structured. "
            "If the content is lengthy, organize it into sections and use bullet points or numbered lists for better readability."
        )
    return ""  # Default Chatty mode


# 1. Define the mapping function
def get_avatar(role):
    if role == "user":
        return "./photo/user.png"

    # Logic for different AI models
    provider = st.session_state.get("provider", "GPT-5.2")

    if "GPT" in provider:
        return "./photo/ai_logo_chatgpt.jpg"
    elif "deepseek" in provider:
        return "./photo/ai_logo_avatat.png"  # Update path as needed
    elif "Gemini" in provider:
        return "./photo/ai_logo_gemini_avatat.png"  # Update path as needed

    return "./photo/ai_logo_avatat.png"  # Default avatar



def chat_gpt(user_prompt, system_prompt=""):
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if st.session_state.memory_enabled and st.session_state.chat_memory:
            messages.extend(st.session_state.chat_memory[-20:])
        messages.append({"role": "user", "content": user_prompt})

        provider = st.session_state["provider"]

        if provider == "GPT-5-mini":
            response = client_openai.chat.completions.create(
                model="gpt-5-mini",
                messages=messages
            )
            return response.choices[0].message.content.strip()

        elif provider == "deepseek-chat":
            response = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content.strip()

        elif provider == "deepseek-reasoner":
            response = client_deepseek.chat.completions.create(
                model="deepseek-reasoner",
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content.strip()

        elif provider == "GPT-5.2-chat":
            response = client_openai.chat.completions.create(
                model="gpt-5.2-chat-latest",
                messages=messages
            )
            return response.choices[0].message.content.strip()

        elif provider == "GPT-5.2":
            response = client_openai.responses.create(
                model="gpt-5.2",
                input=messages
            )
            return response.output_text.strip()

        elif provider == "Gemini-3":
            gemini_system_instruction = ""
            gemini_contents = []
            for message in messages:
                if message["role"] == "system":
                    gemini_system_instruction = message["content"]
                elif message["role"] == "user":
                    gemini_contents.append({"role": "user", "parts": [{"text": message["content"]}]})
                elif message["role"] == "assistant":
                    gemini_contents.append({"role": "model", "parts": [{"text": message["content"]}]})

            config = {}
            if gemini_system_instruction:
                config["system_instruction"] = gemini_system_instruction

            response = gemini_client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=gemini_contents,
                config=config
            )
            return response.text

    except Exception as e:
        return f"Error: {str(e)}"


# ---------------------- Layout ----------------------
logo_base64 = get_base64_image("photo/ai_logo_4.png")

col_left, col_right = st.columns([1, 1.618])

with col_left:
    st.markdown(f"""
        <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 10px;'>
            <img src='{logo_base64}' width='70' style='border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>
            <div>
                <h1 style='margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem;'>AIPA</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # st.markdown("""
    # <style>
    # .stCheckbox > label, .stSelectbox > label, .stToggle > label {
    #     word-break: keep-all !important;
    #     white-space: nowrap !important;
    # }
    # </style>
    # """, unsafe_allow_html=True)
    # col_a, col_b, col_c = st.columns([1.618 / 2, 1.618 / 2, 1])
    # with col_c:
    #     if "provider" not in st.session_state:
    #         st.session_state["provider"] = "GPT-5.2"
    #     provider = st.selectbox(
    #         "Select Provider",
    #         ["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"],
    #         index=["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"].index(
    #             st.session_state["provider"])
    #     )
    #     st.session_state["provider"] = provider
    # with col_a:
    #     st.session_state.memory_enabled = st.toggle(
    #         "Memory",
    #         value=st.session_state.memory_enabled,
    #         help="Enable conversation memory for context retention"
    #     )
    # with col_b:
    #     pdf_mode = st.toggle(
    #         "Read PDF",
    #         value=False,
    #         help="Upload and query PDF documents"
    #     )
    # Initialize session state
    if "provider" not in st.session_state:
        st.session_state["provider"] = "GPT-5.2"
    if "memory_enabled" not in st.session_state:
        st.session_state.memory_enabled = False

    # 2026 Best Practice: st.container with horizontal=True
    # This replaces fixed columns and supports automatic wrapping
    # flex_row = st.container(horizontal=True, horizontal_alignment="left")

    # # flex_row = st.container(horizontal=True, vertical_alignment="center")
    flex_row = st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="left")
    #
    with flex_row:
        # 1. Provider Selectbox
        # Setting a width allows it to shrink/grow based on content
        st.session_state["provider"] = st.selectbox(
            "Select Provider",
            ["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"],
            index=["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"].index(
                st.session_state["provider"]),
            label_visibility = "collapsed"
        )
        # 2. Memory Toggle
        st.session_state.memory_enabled = st.toggle(
            "Memory",
            value=st.session_state.memory_enabled,
            help="Enable conversation memory for context retention"
        )
        # 3. PDF Toggle
        pdf_mode = st.toggle(
            "Read PDF",
            value=False,
            help="Upload and query PDF documents"
        )

    # flex_row = st.container(horizontal=True, vertical_alignment="bottom", horizontal_alignment="left")

    # with flex_row:
    #     # 1. Left-aligned Toggles
    #     # Setting label_visibility="collapsed" ensures no extra height is added
    #     st.session_state.memory_enabled = st.toggle("Memory", value=st.session_state.get('memory_enabled', False), key="mem_togl")
    #     pdf_mode=st.toggle("Read PDF", value=False, key="pdf_togl")
    #
    #     # 2. FLEXIBLE SPACER
    #     # This pushes the selectbox to the far right
    #
    #     # 3. Provider Selectbox
    #     # We use a fixed width so it doesn't stretch and "push" the toggles
    #     # st.session_state["provider"] = st.selectbox(
    #     #     "Select Provider",
    #     #     ["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"],
    #     #     index=0,
    #     #     label_visibility="visible",  # Keeps label above for context
    #     #     width=250
    #     # )
    #     st.session_state["provider"] = st.selectbox(
    #         "Select Provider",
    #         ["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"],
    #         index=["GPT-5.2", "GPT-5.2-chat", "deepseek-chat", "deepseek-reasoner", "Gemini-3"].index(
    #             st.session_state["provider"]),
    #         label_visibility = "collapsed"
    #     )

    provider = st.session_state["provider"]
    mode = "PDF Context" if pdf_mode else "Text Context"

    # ---------------------- Context Handling ----------------------
    if mode == "Text Context":
        st.markdown("<style>label[data-testid='stWidgetLabel'] {display: none;}</style>", unsafe_allow_html=True)
        st.text_area(
            "",
            key="context_input_text",
            placeholder=(
                "Add your context here so you can refer to it again.\n\n"
                "This could be:\n"
                "- A Python code snippet to debug\n"
                "- An email you want to revise\n"
                "- A paragraph you want to translate"
            ),
            height=355)
    else:
        st.markdown("<style>label[data-testid='stWidgetLabel'] {display: none;}</style>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload PDF for context", type=["pdf"])

        if uploaded_file is not None and uploaded_file != st.session_state.get("last_uploaded_file"):
            pdf_text = read_pdf(uploaded_file)
            text_chunks = chunk_text(pdf_text)
            vectorizer, tfidf_chunks = vectorize_text_chunks(text_chunks)
            st.session_state.pdf_text_chunks = text_chunks
            st.session_state.pdf_vectorizer = vectorizer
            st.session_state.pdf_tfidf_chunks = tfidf_chunks
            st.session_state.last_uploaded_file = uploaded_file
            st.success("PDF uploaded and processed successfully!")
        elif uploaded_file is None:
            st.session_state.pop("pdf_text_chunks", None)
            st.session_state.pop("pdf_vectorizer", None)
            st.session_state.pop("pdf_tfidf_chunks", None)
            st.session_state.pop("last_uploaded_file", None)

    col_mem1, col_mem2 = st.columns([4, 2])
    with col_mem1:
        chat_mode = st.pills("Expertise Mode", ["Chatty", "Coder", "Pro"], default="Pro")
    with col_mem2:
        if st.button("Clear Chat"):
            st.session_state.messages_text = []
            st.session_state.messages_pdf = []
            st.session_state.chat_memory = []
            st.success("Chat history and memory cleared!")
            st.rerun()
    user_input = st.chat_input("💬  Give AIPA a task or ask a question.")

with col_right:
    with st.container(height=650, border=True):
        if mode == "Text Context":
            for msg in st.session_state.messages_text:
                # Use stored avatar or fallback to get_avatar for safety
                avatar = msg.get("avatar", get_avatar(msg['role']))
                name = "User" if msg['role'] == "user" else "Milliona"
                with st.chat_message(name=name, avatar=avatar):
                    render_combined_markdown(msg['content'])
        else:
            for msg in st.session_state.messages_pdf:
                avatar = msg.get("avatar", get_avatar(msg['role']))
                name = "User" if msg['role'] == "user" else "Milliona"
                with st.chat_message(name=name, avatar=avatar):
                    render_combined_markdown(msg['content'])

    st.markdown(
        """
        <style>
            section[data-testid="stVerticalBlock"] {
                display: flex;
                flex-direction: column-reverse;
                overflow-y: auto;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------------------- Handle User Input ----------------------
if user_input:
    system_prompt = get_system_prompt()
    user_avatar = get_avatar("user")
    bot_avatar = get_avatar("assistant")

    if mode == "Text Context":
        delimiter = "'''"
        if st.session_state.context_input_text:
            user_prompt = f"Answer the following question. Additional materials are delimited by {delimiter} \n\nQuestion:{user_input}\n\n{delimiter}\n{st.session_state.context_input_text}\n{delimiter}"
        else:
            user_prompt = f"Answer the following question.\n\n{delimiter}{user_input}{delimiter}"

        bot_response = chat_gpt(user_prompt, system_prompt)

        # Save both messages with their specific avatars
        st.session_state.messages_text.insert(0, {"role": "assistant", "content": bot_response, "avatar": bot_avatar})
        st.session_state.messages_text.insert(0, {"role": "user", "content": user_input, "avatar": user_avatar})

        if st.session_state.memory_enabled:
            st.session_state.chat_memory.append({"role": "user", "content": user_input})
            st.session_state.chat_memory.append({"role": "assistant", "content": bot_response})
            st.session_state.chat_memory = st.session_state.chat_memory[-20:]

    else:
        if uploaded_file is not None and "pdf_text_chunks" in st.session_state:
            if user_input != st.session_state.last_processed_input_pdf:
                st.session_state.last_processed_input_pdf = user_input
                most_similar_chunk = find_most_similar_chunks(user_input, st.session_state.pdf_vectorizer,
                                                              st.session_state.pdf_tfidf_chunks,
                                                              st.session_state.pdf_text_chunks)
                delimiter = "'''"
                user_prompt = f"Answer the following question using the provided PDF context.\n\nQuestion:\n{delimiter}{user_input}{delimiter}\n\nContext:\n{delimiter}{most_similar_chunk}{delimiter}"

                bot_response = chat_gpt(user_prompt, system_prompt)

                # Save both messages with their specific avatars
                st.session_state.messages_pdf.insert(0, {"role": "assistant", "content": bot_response,
                                                         "avatar": bot_avatar})
                st.session_state.messages_pdf.insert(0, {"role": "user", "content": user_input, "avatar": user_avatar})

                if st.session_state.memory_enabled:
                    st.session_state.chat_memory.append({"role": "user", "content": user_input})
                    st.session_state.chat_memory.append({"role": "assistant", "content": bot_response})
                    st.session_state.chat_memory = st.session_state.chat_memory[-20:]
        else:
            st.warning("Please upload and process a PDF before asking questions.")

    st.rerun()
