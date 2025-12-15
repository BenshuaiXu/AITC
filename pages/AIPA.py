import streamlit as st
from openai import OpenAI
from PIL import Image
from utils.graphic_pro import get_base64_image
from utils.print_pro import render_combined_markdown
from utils.pdf_pro import read_pdf, chunk_text, vectorize_text_chunks, find_most_similar_chunks
from google import genai

gemini_client = genai.Client()

# Initialize OpenAI client with API key from Streamlit secrets
client_openai = OpenAI(api_key=st.secrets["ai_key"])
OpenAI.api_key = st.secrets["ai_key"]

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
            # "Use simple, easy-to-read language while maintaining a professional tone. "
            "If the content is lengthy, organize it into sections and use bullet points or numbered lists for better readability."
            #"All math formula is written in Markdown with LaTeX rendering."
        )
    return ""  # Default Chatty mode


# ---------------------- Chat Function ----------------------
# def chat_gpt(user_prompt, system_prompt=""):
#     try:
#         messages = []
#
#         # Add system instructions if needed
#         if system_prompt:
#             messages.append({"role": "system", "content": system_prompt})
#
#         # Add memory context if enabled
#         if st.session_state.memory_enabled and st.session_state.chat_memory:
#             messages.extend(st.session_state.chat_memory[-20:])  # Last 10 Q&A pairs
#
#         # Add current user input
#         messages.append({"role": "user", "content": user_prompt})
#
#         if st.session_state["provider"] == "GPT-5-mini":
#             response = client_openai.chat.completions.create(
#                 model="gpt-5-mini",
#                 messages=messages
#             )
#             return response.choices[0].message.content.strip()
#
#         elif st.session_state["provider"] == "deepseek-chat":
#             response = client_deepseek.chat.completions.create(
#                 model="deepseek-chat",
#                 messages=messages,
#                 stream=False
#             )
#             return response.choices[0].message.content.strip()
#
#         elif st.session_state["provider"] == "deepseek-reasoner":
#             response = client_deepseek.chat.completions.create(
#                 model="deepseek-reasoner",
#                 messages=messages,
#                 stream=False
#             )
#             return response.choices[0].message.content.strip()
#
#         elif st.session_state["provider"] == "GPT-5.1":
#             response = client_openai.chat.completions.create(
#                 model="gpt-5.2-chat-latest",
#                 messages=messages
#             )
#             return response.choices[0].message.content.strip()
#
#         elif st.session_state["provider"] == "GPT-5.2":
#             response = client_openai.chat.completions.create(
#                 model="gpt-5.1-chat-latest",
#                 messages=messages
#             )
#             return response.choices[0].message.content.strip()
#         elif st.session_state["provider"] == "Gemini-2.5":
#             response = gemini_client.models.generate_content(
#                 model="gemini-2.5-flash",
#                 contents=messages,
#             )
#             return response.text
#
#
#     except Exception as e:
#         return f"Error: {str(e)}"


def chat_gpt(user_prompt, system_prompt=""):
    try:
        messages = []

        # Add system instructions if needed
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add memory context if enabled (assuming memory roles are 'user'/'assistant')
        if st.session_state.memory_enabled and st.session_state.chat_memory:
            # Note: The model's response role in memory should be 'assistant' to match OpenAI format,
            # or 'model' if you are consistently using Gemini's format.
            messages.extend(st.session_state.chat_memory[-20:])  # Last 10 Q&A pairs

        # Add current user input
        messages.append({"role": "user", "content": user_prompt})

        # --- EXISTING BLOCKS ---
        if st.session_state["provider"] == "GPT-5-mini":
            response = client_openai.chat.completions.create(
                model="gpt-5-mini",
                messages=messages
            )
            return response.choices[0].message.content.strip()

        elif st.session_state["provider"] == "deepseek-chat":
            response = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content.strip()

        elif st.session_state["provider"] == "deepseek-reasoner":
            response = client_deepseek.chat.completions.create(
                model="deepseek-reasoner",
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content.strip()

        # elif st.session_state["provider"] == "GPT-5.1":
        #     response = client_openai.chat.completions.create(
        #         model="gpt-5.2-chat-latest",
        #         messages=messages
        #     )
        #     return response.choices[0].message.content.strip()

        elif st.session_state["provider"] == "GPT-5.2":
            response = client_openai.chat.completions.create(
                model="gpt-5.2-chat-latest",
                messages=messages
            )
            return response.choices[0].message.content.strip()

        # --- CORRECTED GEMINI BLOCK ---
        elif st.session_state["provider"] == "Gemini-3":
            # Gemini requires content in a specific format and system instructions
            # as a separate config parameter.
            gemini_system_instruction = ""
            gemini_contents = []

            for message in messages:
                if message["role"] == "system":
                    # Extract system instruction
                    gemini_system_instruction = message["content"]
                elif message["role"] == "user":
                    # Convert to Gemini user content format
                    gemini_contents.append({"role": "user", "parts": [{"text": message["content"]}]})
                elif message["role"] == "assistant":
                    # Convert 'assistant' (from memory) to 'model' for Gemini
                    gemini_contents.append({"role": "model", "parts": [{"text": message["content"]}]})
                # If memory is already using 'model' role, the 'assistant' check can be changed.

            config = {}
            if gemini_system_instruction:
                config["system_instruction"] = gemini_system_instruction

            response = gemini_client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=gemini_contents,
                config=config  # Pass the system instruction here
            )
            return response.text

    except Exception as e:
        return f"Error: {str(e)}"


# ---------------------- Layout ----------------------
logo_base64 = get_base64_image("photo/ai_logo_4.png")
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 10px;'>
        <img src='{logo_base64}' width='60'>
        <div>
            <h1>AIPA</h1>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Mode & provider toggles
    st.markdown("""
    <style>
    .stCheckbox > label, .stSelectbox > label, .stToggle > label {
        word-break: keep-all !important;
        white-space: nowrap !important;
    }
    </style>
    """, unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([3, 2.5, 2])
    with col_c:
        pdf_mode = st.toggle("PDF  ", value=False)
    with col_a:
        if "provider" not in st.session_state:
            st.session_state["provider"] = "GPT-5.2"
        provider = st.selectbox(
            "Select Provider",
            ["GPT-5.2", "GPT-5-mini", "deepseek-chat", "deepseek-reasoner", "Gemini-3"],
            index=["GPT-5.2", "GPT-5-mini", "deepseek-chat", "deepseek-reasoner", "Gemini-3"].index(st.session_state["provider"])
        )
        st.session_state["provider"] = provider
    with col_b:
        st.session_state.memory_enabled = st.toggle(
            "Memory",
            value=st.session_state.memory_enabled
        )
    provider = st.session_state["provider"]
    mode = "PDF Context" if pdf_mode else "Text Context"

    # ---------------------- Context Handling ----------------------
    if mode == "Text Context":
        st.markdown(
            """
            <style>
            label[data-testid="stWidgetLabel"] {
                display: none;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Optional context input
        st.text_area(
            "",
            key="context_input_text",
            placeholder="Optional context, e.g., background info, constraints, examples, or preferences...",
            height=400,
        )
    else:
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

    # ---------------------- Chat Input ----------------------
    col_mem1, col_mem2 = st.columns([4, 2])
    with col_mem1:
        chat_mode = st.radio(
            "Chat Mode:",
            ["Chatty", "Coder", "Pro"],
            index=0,
            horizontal=True
        )
    with col_mem2:
        if st.button("Clear Chat"):
            st.session_state.messages_text = []
            st.session_state.messages_pdf = []
            st.session_state.chat_memory = []
            st.success("Chat history and memory cleared!")
            st.rerun()
    user_input = st.chat_input("Give AIPA a task or ask a question.")


with col_right:
    with st.container(height=700, border=True):
        if mode == "Text Context":
            for msg in st.session_state.messages_text:
                role = msg['role']
                avatar = "./photo/user.png" if role == "user" else "./photo/ai_logo_avatat.png"
                name = "User" if role == "user" else "Milliona"
                with st.chat_message(name=name, avatar=avatar):
                    render_combined_markdown(msg['content'])
        else:
            for message in st.session_state.messages_pdf:
                avatar = "./photo/user.png" if message['role'] == 'user' else "./photo/ai_logo_avatat.png"
                name = "User" if message['role'] == 'user' else "Milliona"
                with st.chat_message(name=name, avatar=avatar):
                    render_combined_markdown(message['content'])

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

    if mode == "Text Context":
        delimiter = "'''"
        if st.session_state.context_input_text:
            user_prompt = (
                f"Answer the following question. Additional materials are delimited by {delimiter} \n\n"
                f"Question:{user_input}\n\n"
                f"{delimiter}\n{st.session_state.context_input_text}\n{delimiter}"
            )
        else:
            user_prompt = (
                f"Answer the following question.\n\n"
                f"{delimiter}{user_input}{delimiter}"
            )

        bot_response = chat_gpt(user_prompt, system_prompt)

        st.session_state.messages_text.insert(0, {"role": "assistant", "content": bot_response})
        st.session_state.messages_text.insert(0, {"role": "user", "content": user_input})

        # Save memory
        if st.session_state.memory_enabled:
            st.session_state.chat_memory.append({"role": "user", "content": user_input})
            st.session_state.chat_memory.append({"role": "assistant", "content": bot_response})
            st.session_state.chat_memory = st.session_state.chat_memory[-20:]

    else:
        if uploaded_file is not None and "pdf_text_chunks" in st.session_state:
            if user_input != st.session_state.last_processed_input_pdf:
                st.session_state.last_processed_input_pdf = user_input
                most_similar_chunk = find_most_similar_chunks(
                    user_input,
                    st.session_state.pdf_vectorizer,
                    st.session_state.pdf_tfidf_chunks,
                    st.session_state.pdf_text_chunks
                )
                delimiter = "'''"
                user_prompt = (
                    f"Answer the following question using the provided PDF context.\n\n"
                    f"Question:\n{delimiter}{user_input}{delimiter}\n\n"
                    f"Context:\n{delimiter}{most_similar_chunk}{delimiter}"
                )

                bot_response = chat_gpt(user_prompt, system_prompt)
                st.session_state.messages_pdf.insert(0, {"role": "assistant", "content": bot_response})
                st.session_state.messages_pdf.insert(0, {"role": "user", "content": user_input})

                # Save memory
                if st.session_state.memory_enabled:
                    st.session_state.chat_memory.append({"role": "user", "content": user_input})
                    st.session_state.chat_memory.append({"role": "assistant", "content": bot_response})
                    st.session_state.chat_memory = st.session_state.chat_memory[-20:]
        else:
            st.warning("Please upload and process a PDF before asking questions.")

    st.rerun()
