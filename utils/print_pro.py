import re
import streamlit as st
from markdown_it import MarkdownIt
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

# --- SQL Detection ---
SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}

SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")  # code + trailing SQL comment
PYTHON_START_RE = re.compile(
    r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)"""
)

# --- HTML ---
HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)

# --- CSS ---
CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")


def detect_sql_dialect(text: str) -> str | None:
    if re.search(r"\bSELECT\b", text, re.IGNORECASE):
        for kw in ORACLE_SQL_KEYWORDS:
            if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                return "oracle-sql"
        for kw in MYSQL_SQL_KEYWORDS:
            if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                return "mysql"
        for kw in POSTGRES_SQL_KEYWORDS:
            if re.search(rf"{kw}", text, re.IGNORECASE):
                return "postgresql"
        return "sql"
    return None


def looks_like_python_start(line: str) -> bool:
    return bool(PYTHON_START_RE.match(line))


def looks_like_python_continuation(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and (
            stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
            or stripped.startswith((")", "]", "}"))  # closing brackets
            or line.startswith("    ")  # indentation
    )


def guess_language(text: str) -> str | None:
    dialect = detect_sql_dialect(text)
    if dialect:
        return "sql"
    try:
        lexer = guess_lexer(text)
        return lexer.aliases[0] if lexer.aliases else None
    except ClassNotFound:
        return None


# --- Inline code in Markdown ---
INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def render_text_with_inline_code(line: str):
    def replacer(match):
        return f"<code>{match.group(1)}</code>"

    html_line = INLINE_CODE_RE.sub(replacer, line)
    html_line = html_line.replace("$", "\\$")
    st.markdown(html_line, unsafe_allow_html=True)


# --- Helpers ---
def flush_buffer(buf, lang=None):
    if buf:
        lang_guess = lang or guess_language("\n".join(buf)) or ""
        st.code("\n".join(buf), language=lang_guess, width="content")
        buf.clear()


# --- Main Markdown + code renderer ---
def render_combined_markdown_o(text: str):
    md = MarkdownIt()
    tokens = md.parse(text)

    def flush_sql_buffer(buf):
        if buf:
            st.code("\n".join(buf), language="sql", width="content")
            buf.clear()

    for token in tokens:
        if token.type in ("fence", "code_block"):
            lang = token.info.strip() or guess_language(token.content) or ""
            st.code(token.content, language=lang, width="content")
        else:
            sql_buffer = []
            lines = token.content.splitlines()
            in_sql_block = False

            for line in lines:
                comment_match = SQL_COMMENT_RE.match(line)
                code_part = line
                comment_part = None
                if comment_match:
                    code_part = comment_match.group(1).rstrip()
                    comment_part = comment_match.group(2).lstrip()

                stripped = code_part.strip()

                # Determine if this line starts a SQL block
                if not in_sql_block and stripped.upper().startswith(SQL_START_KEYWORDS):
                    in_sql_block = True
                    sql_buffer.append(code_part)
                # Continue SQL block if we're inside one
                elif in_sql_block:
                    # Treat non-empty lines as part of SQL block
                    if stripped or stripped == "":
                        sql_buffer.append(code_part)
                    else:
                        flush_sql_buffer(sql_buffer)
                        in_sql_block = False
                        if stripped:
                            render_text_with_inline_code(line)
                else:
                    if stripped:
                        render_text_with_inline_code(line)

                # Always render trailing comment separately
                if comment_part:
                    render_text_with_inline_code(comment_part)

            flush_sql_buffer(sql_buffer)


def render_combined_markdown_1(text: str):
    md = MarkdownIt()
    tokens = md.parse(text)

    def flush_buffer(buf, lang=None):
        if buf:
            lang_guess = lang or guess_language("\n".join(buf)) or ""
            st.code("\n".join(buf), language=lang_guess, width="content")
            buf.clear()

    for token in tokens:
        if token.type in ("fence", "code_block"):
            lang = token.info.strip() or guess_language(token.content) or ""
            st.code(token.content, language=lang, width="content")
        else:
            sql_buffer, py_buffer = [], []
            in_sql_block, in_py_block = False, False

            lines = token.content.splitlines()

            for line in lines:
                stripped = line.strip()

                # --- Python detection ---
                if not in_py_block and looks_like_python_start(line):
                    flush_buffer(sql_buffer, "sql")  # close SQL if open
                    in_py_block = True
                    py_buffer.append(line)
                    continue
                elif in_py_block:
                    if looks_like_python_continuation(line) or stripped == "":
                        py_buffer.append(line)
                        continue
                    else:
                        flush_buffer(py_buffer, "python")
                        in_py_block = False

                # --- SQL detection ---
                if not in_sql_block and stripped.upper().startswith(SQL_START_KEYWORDS):
                    flush_buffer(py_buffer, "python")
                    in_sql_block = True
                    sql_buffer.append(line)
                    continue
                elif in_sql_block:
                    if stripped or stripped == "":
                        sql_buffer.append(line)
                        continue
                    else:
                        flush_buffer(sql_buffer, "sql")
                        in_sql_block = False

                # --- Regular text ---
                if stripped:
                    render_text_with_inline_code(line)

            # Flush remaining buffers
            flush_buffer(py_buffer, "python")
            flush_buffer(sql_buffer, "sql")


# --- Main function ---
def render_combined_markdown(text: str):
    md = MarkdownIt()
    tokens = md.parse(text)

    for token in tokens:
        if token.type in ("fence", "code_block"):
            lang = token.info.strip() or guess_language(token.content) or ""
            st.code(token.content, language=lang, width="content")
        else:
            sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
            in_sql, in_py, in_html, in_css = False, False, False, False

            lines = token.content.splitlines()

            for line in lines:
                stripped = line.strip()

                # --- Python ---
                if not in_py and looks_like_python_start(line):
                    flush_buffer(sql_buffer, "sql")
                    flush_buffer(html_buffer, "html")
                    flush_buffer(css_buffer, "css")
                    in_py = True
                    py_buffer.append(line)
                    continue
                elif in_py:
                    if looks_like_python_continuation(line) or stripped == "":
                        py_buffer.append(line)
                        continue
                    else:
                        flush_buffer(py_buffer, "python")
                        in_py = False

                # --- SQL ---
                if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
                    flush_buffer(py_buffer, "python")
                    flush_buffer(html_buffer, "html")
                    flush_buffer(css_buffer, "css")
                    in_sql = True
                    sql_buffer.append(line)
                    continue
                elif in_sql:
                    if stripped or stripped == "":
                        sql_buffer.append(line)
                        continue
                    else:
                        flush_buffer(sql_buffer, "sql")
                        in_sql = False

                # --- HTML ---
                if not in_html and HTML_START_RE.match(line):
                    flush_buffer(py_buffer, "python")
                    flush_buffer(sql_buffer, "sql")
                    flush_buffer(css_buffer, "css")
                    in_html = True
                    html_buffer.append(line)
                    continue
                elif in_html:
                    if stripped or stripped == "":
                        html_buffer.append(line)
                        if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
                            flush_buffer(html_buffer, "html")
                            in_html = False
                        continue
                    else:
                        flush_buffer(html_buffer, "html")
                        in_html = False

                # --- CSS ---
                if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
                    flush_buffer(py_buffer, "python")
                    flush_buffer(sql_buffer, "sql")
                    flush_buffer(html_buffer, "html")
                    in_css = True
                    css_buffer.append(line)
                    continue
                elif in_css:
                    css_buffer.append(line)
                    if "}" in line:
                        flush_buffer(css_buffer, "css")
                        in_css = False
                    continue

                # --- Regular text ---
                if stripped:
                    render_text_with_inline_code(line)

            # Flush remaining buffers
            flush_buffer(py_buffer, "python")
            flush_buffer(sql_buffer, "sql")
            flush_buffer(html_buffer, "html")
            flush_buffer(css_buffer, "css")