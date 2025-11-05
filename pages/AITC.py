import streamlit as st
from openai import OpenAI
from PIL import Image
from utils.graphic_pro import get_base64_image
import json
import re

# =============================
# Setup
# =============================
client = OpenAI(api_key=st.secrets["ai_key"])
OpenAI.api_key = st.secrets["ai_key"]

# client_deepseek = OpenAI(api_key=st.secrets["deepseek_key"], base_url="https://api.deepseek.com")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("You must log in first.")
    st.stop()

st.set_page_config(page_title="AITC", page_icon="photo/ai_logo_4.png", layout="wide")

# Sidebar
st.sidebar.markdown(f"Logged in as: **{st.session_state['username']}**")
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.switch_page("main.py")
st.sidebar.markdown("---")
sidebar_logo = Image.open("photo/ai_logo_4.png")
st.sidebar.image(sidebar_logo, use_container_width=True)


# OpenAI wrapper
def chat_gpt(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            # model="gpt-5-nano",
            model="gpt-5-mini",
            # model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

        # response = client_deepseek.chat.completions.create(
        #     model="deepseek-chat",
        #     messages=[{"role": "user", "content": prompt}],
        #     stream=False
        # )
        # return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"


# Header
logo_base64 = get_base64_image("photo/ai_logo_4.png")
st.markdown(
    f"""
<div style='display: flex; align-items: center; gap: 20px;'>
    <img src='{logo_base64}' width='100'>
    <div>
        <h1>English Teacher</h1>
    </div>
</div>
<hr style='margin-top: 10px;'>
""",
    unsafe_allow_html=True,
)

# =============================
# Mode Toggle (Top of Page)
# =============================
# mode = st.radio(
#     "Choose Mode:",
#     ["Word Learning Mode", "Writing Improving Mode"],
#     horizontal=True,
#     key="mode_toggle"
# )

mode = "Word Learning Mode"
mode_toggle = st.toggle("Switch to Writing Improving Mode", value=False)
if mode_toggle:
    mode = "Writing Improving Mode"

# =============================
# Helpers (robust comparisons)
# =============================
_letters = "abcdefghijklmnopqrstuvwxyz"


def _normalize_text(x) -> str:
    if x is None:
        return ""
    s = str(x).strip().lower()
    s = re.sub(r"[^a-z0-9'\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_any(x):
    if isinstance(x, list):
        return [_normalize_text(i) for i in x]
    return _normalize_text(x)


def _coerce_mc_answer(choices, answer):
    """Map index/letter/raw to an exact choice string."""
    choices_str = [str(c) for c in choices]
    norm_choices = [_normalize_text(c) for c in choices_str]

    if isinstance(answer, int):
        if 0 <= answer < len(choices_str):
            return choices_str[answer]
        if 1 <= answer <= len(choices_str):
            return choices_str[answer - 1]

    a = str(answer).strip()
    an = _normalize_text(a)

    if len(an) == 1 and an in _letters[:len(choices_str)]:
        return choices_str[_letters.index(an)]

    for raw, norm in zip(choices_str, norm_choices):
        if an == norm:
            return raw

    # If still not matched, fall back to first option to keep the bank consistent
    return choices_str[0] if choices_str else a


if mode == "Word Learning Mode":
    # =============================
    # Word Explanation (Left)
    # =============================
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("### ✍️ Word Explanation")
        st.info("请输入一个英语单词。我会跟你一起愉快地学习这个单词，一起进步。")
        # st.markdown("### 📖 Word Explanation")
        # Session state for "single latest" behavior
        if "last_word_input" not in st.session_state:
            st.session_state.last_word_input = None
        if "current_word" not in st.session_state:
            st.session_state.current_word = ""
        if "current_explanation" not in st.session_state:
            st.session_state.current_explanation = ""

        user_input_word = st.text_input("Enter a word to learn:")


        def explain_word(word: str) -> str:
            prompt = f"""
                    You are teaching an 8-year-old Chinese child the English word "{word}".
                    Follow these steps:

                    1. **Meaning 意思**
                    - Explain the meaning of "{word}" in simple English (for a child).
                    - Give the meaning in Chinese.

                    2. **Word Forms 形式**
                    - If it is a noun: give singular and plural forms, with Chinese translations for each.
                    - If it is a verb: give base form, past simple, past participle, present participle, and third-person singular present, each with a Chinese translation.
                    - If it is an adjective/adverb: give common variations (comparative, superlative, etc.) with Chinese translations.

                    3. **Example Sentences 例句**
                    - For each form, give one short, clear English sentence.
                    - Provide the Chinese translation for each sentence.
                    - Keep sentences age-appropriate and easy to understand.

                    Use a friendly and encouraging tone suitable for children.
                    """
            return chat_gpt(prompt)


        # ---------- Build a question bank of 10 items at once ----------
        def build_question_bank_from_explanation(word: str, explanation: str):
            """
            Ask GPT for a bank of 10 questions with increasing difficulty and mixed types.
            Returns a list of dicts: [{type, question, choices, answer}, ...] length 10
            """
            prompt = f"""
                    You are an AI English teacher. The student learned this explanation:

                    EXPLANATION:
                    {explanation}

                    Create exactly 10 questions to help the student consolidate understanding of the word "{word}".
                    Rules:
                    - Base EVERYTHING ONLY on the explanation above.
                    - Difficulty should increase from Q1 (very easy) to Q10 (hard).
                    - Mix of types: use "multiple_choice", "fill_blank", and "short_answer".
                    * Include at least 3 different types across the 10 questions.
                    * Avoid using the same type more than twice in a row.
                    - Keep language simple for an 8-year-old Chinese student.
                    - For multiple choice, include 3–4 options; make the correct answer clear and the "answer" MUST be exactly one of the choices.
                    - For all answers, ALWAYS return a string (even if the answer is a number).
                    - Return STRICT JSON ONLY, no prose, as:
                    [
                    {{
                        "id": 1,
                        "difficulty": 1,
                        "type": "multiple_choice" | "fill_blank" | "short_answer",
                        "question": "string",
                        "choices": ["string","string","string"],   // omit for non-MC
                        "answer": "string"
                    }},
                    ... up to id 10 with difficulty 10
                    ]
                    """
            raw = chat_gpt(prompt)
            if raw.startswith("Error:"):
                return None

            try:
                bank = json.loads(raw)
                if not isinstance(bank, list):
                    return None
            except Exception:
                return None

            # Sanitize / coerce items
            cleaned = []
            for item in bank[:10]:
                try:
                    q_type = str(item.get("type", "short_answer")).strip().lower()
                    if q_type in {"fill-in-the-blank", "fill in the blank", "fill_in_the_blank"}:
                        q_type = "fill_blank"
                    if q_type not in {"multiple_choice", "short_answer", "fill_blank"}:
                        q_type = "short_answer"

                    question = str(item.get("question", "")).strip()
                    choices = item.get("choices", [])
                    choices = [str(c) for c in choices] if isinstance(choices, list) else []

                    ans = str(item.get("answer", "")).strip()
                    if q_type == "multiple_choice" and choices:
                        ans = _coerce_mc_answer(choices, ans)

                    if question:
                        cleaned.append({
                            "type": q_type,
                            "question": question,
                            "choices": choices,
                            "answer": ans,
                        })
                except Exception:
                    continue

            # Ensure exactly 10 questions; if fewer, top up with safe fallbacks
            if len(cleaned) < 10:
                # Simple, generic fallbacks referencing the word
                needed = 10 - len(cleaned)
                n0 = len(cleaned)
                for i in range(needed):
                    idx = n0 + i + 1
                    if idx <= 3:
                        cleaned.append({
                            "type": "multiple_choice",
                            "question": f"What does '{word}' relate to in the explanation?",
                            "choices": [f"It relates to '{word}'", "A color", "A number"],
                            "answer": f"It relates to '{word}'",
                        })
                    elif idx <= 6:
                        cleaned.append({
                            "type": "fill_blank",
                            "question": f"Fill in the blank: This word is about ____ (based on the explanation).",
                            "choices": [],
                            "answer": word,
                        })
                    else:
                        cleaned.append({
                            "type": "short_answer",
                            "question": f"In one or two words, what does '{word}' mean (from the explanation)?",
                            "choices": [],
                            "answer": word,
                        })

            return cleaned[:10]


        # When a new word is entered → explain + reset + build bank
        if user_input_word and user_input_word != st.session_state.last_word_input:
            st.session_state.last_word_input = user_input_word
            st.session_state.current_word = user_input_word

            # Reset quiz state
            st.session_state.question_index = 0  # 0..9
            st.session_state.feedback = ""
            st.session_state.quiz_bank = []  # will fill below
            st.session_state.last_answer_submitted_for = None

            # Get explanation
            explanation = explain_word(user_input_word)
            st.session_state.current_explanation = explanation

            # Build question bank (10 at once)
            bank = build_question_bank_from_explanation(user_input_word, explanation)
            st.session_state.quiz_bank = bank or []

            st.rerun()

        # Display only latest word + explanation
        if st.session_state.current_word:
            st.markdown(f"### Word: **{st.session_state.current_word}**")
            st.markdown(st.session_state.current_explanation)

    # =============================
    # Quiz (Right) — uses 10-question bank
    # =============================
    with right_col:
        st.markdown("### 🎯 Practice (10 questions)")
        if "question_index" not in st.session_state:
            st.session_state.question_index = 0
        if "feedback" not in st.session_state:
            st.session_state.feedback = ""
        if "quiz_bank" not in st.session_state:
            st.session_state.quiz_bank = []

        if not st.session_state.current_word:
            st.info("Please enter a word on the left to start the quiz.")
            st.stop()

        # --------------------------------
        # AFTER 10 QUESTIONS → Free sentence practice
        # --------------------------------
        if st.session_state.question_index >= 10:
            st.success("🎉 You've completed all 10 questions!")
            st.markdown("### ✍️ Now, try making your own sentence with this word!")

            # Reset feedback once when entering this section
            if "sentence_feedback" not in st.session_state or st.session_state.question_index == 10 and not st.session_state.get(
                    "sentence_input_shown", False):
                st.session_state.sentence_feedback = ""
                st.session_state.sentence_input_shown = True

            student_sentence = st.text_area(
                f"Write a sentence using **{st.session_state.current_word}**:",
                key="student_sentence_input"
            )

            if st.button("Complete"):
                if not student_sentence.strip():
                    st.warning("Please enter a sentence before submitting.")
                else:
                    # GPT evaluation prompt
                    prompt = f"""
                        你是一位英语老师。学生刚学了单词 "{st.session_state.current_word}"。
                        学生写的句子是： "{student_sentence}"

                        请用中文给学生解释：
                        1. 句子是否正确、是否使用了目标单词。
                        2. 如果有语法错误或不自然的地方，请指出。
                        3. 给出一个修改后的正确版本。

                        格式：
                        - 中文点评
                        - 修改后的英文句子
                        """
                    assessment = chat_gpt(prompt)
                    st.session_state.sentence_feedback = assessment

            if st.session_state.sentence_feedback:
                st.markdown("#### 📋 评语与修改")
                st.write(st.session_state.sentence_feedback)

            st.stop()

        # --------------------------------
        # Otherwise, continue quiz
        # --------------------------------
        if not st.session_state.quiz_bank:
            if st.button("Generate 10 Questions Now"):
                bank = build_question_bank_from_explanation(
                    st.session_state.current_word, st.session_state.current_explanation
                )
                st.session_state.quiz_bank = bank or []
                st.rerun()
            st.warning("No questions generated yet for this word.")
            st.stop()

        idx = st.session_state.question_index
        q = st.session_state.quiz_bank[idx]
        q_type = q.get("type", "short_answer")
        q_text = q.get("question", "")
        q_choices = [str(c) for c in q.get("choices", [])] if isinstance(q.get("choices", []), list) else []
        q_answer = str(q.get("answer", ""))

        st.markdown(f"#### Question {idx + 1} of 10")

        st.write(q_text)

        user_input = None
        if q_type == "multiple_choice" and q_choices:
            user_input = st.radio("Choose an answer:", q_choices, index=None, key=f"mc_{idx}")
        else:
            user_input = st.text_input("Your answer:", key=f"txt_{idx}")


        def check_answer(user_ans, correct_ans):
            ua = _normalize_any(user_ans)
            if isinstance(correct_ans, str) and re.search(r"[|;,]", correct_ans):
                ca_list = [seg for seg in re.split(r"[|;,]", correct_ans) if seg.strip()]
            elif isinstance(correct_ans, list):
                ca_list = correct_ans
            else:
                ca_list = [correct_ans]
            ca_norm = [_normalize_text(x) for x in ca_list]
            ok = _normalize_text(ua) in ca_norm

            if ok:
                st.session_state.feedback = "✅ Correct!"
                st.balloons()
            else:
                st.session_state.feedback = f"❌ Incorrect! The correct answer was: {ca_list[0]}"
                st.snow()
            return ok


        cols = st.columns(3)
        with cols[0]:
            if st.button("Submit Answer", key=f"submit_{idx}"):
                if user_input is None or (isinstance(user_input, str) and user_input.strip() == ""):
                    st.warning("Please enter or select an answer before submitting.")
                else:
                    if q_type == "multiple_choice" and q_choices:
                        q_answer_display = _coerce_mc_answer(q_choices, q_answer)
                    else:
                        q_answer_display = q_answer

                    check_answer(user_input, q_answer_display)
                    st.session_state.last_answer_submitted_for = idx

        with cols[1]:
            if st.button("Next Question", key=f"next_{idx}"):
                st.session_state.feedback = ""
                st.session_state.question_index = min(9, st.session_state.question_index) + 1
                st.rerun()

        with cols[2]:
            if st.button("End Quiz Now"):
                st.session_state.question_index = 10
                st.rerun()

        if st.session_state.feedback and st.session_state.last_answer_submitted_for == idx:
            st.markdown(f"**{st.session_state.feedback}**")

        remaining = 10 - (idx + 1)

# =============================
# Writing Improving Mode
# =============================
if mode == "Writing Improving Mode":
    # st.markdown("### ✍️ Writing Practice")
    # st.info("Write a sentence or a paragraph in English. I will explain each sentence in Chinese, check grammar and word usage, and give an improved version.")

    left_col, right_col = st.columns([1, 2])  # slightly wider right side for answers

    with left_col:

        st.markdown("### ✍️ Writing Practice")
        st.info("请用英文写一个句子或一段话。我会逐句用中文解释，检查语法和单词用法，并给出改进后的版本。")
        student_text = st.text_area(
            "Your English sentence or paragraph:",
            key="writing_input",
            height=180
        )
        submit_button = st.button("✅ Check & Improve")

    with right_col:
        if submit_button:
            if not student_text.strip():
                st.warning("Please enter a sentence or paragraph.")
            else:
                prompt = f"""
                    你是一位温柔、有耐心的英语老师，要帮助一位9岁的中国孩子学习英语写作。
                    学生写了一段话或多个句子：
                    "{student_text}"

                    请用中文一步一步鼓励并讲解：
                    1. 称赞学生的努力，鼓励他/她继续尝试。
                    2. 逐句解释：每个句子的意思。如果句子较长，请拆成短句再解释。并解释它们是如何组合成长句的。
                    3. 检查单词使用是否正确。
                    4. 指出所用语法，并说明是否正确。
                    5. 如果有错误或不自然的地方，请温柔地指出，并给出改进建议。
                    6. 最后提供一个改进后的完整版本。

                    格式要求：
                    - 话语必须积极鼓励。
                    - 用中文点评（要简单、温和，适合9岁孩子）。
                    """
                feedback = chat_gpt(prompt)
                st.markdown("#### 📋 评语与修改")
                st.write(feedback)

