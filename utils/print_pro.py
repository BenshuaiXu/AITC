# import re
# import streamlit as st
# from markdown_it import MarkdownIt
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound
#
# # --- SQL Detection ---
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}
#
# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")  # code + trailing SQL comment
# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)"""
# )
#
# # --- HTML ---
# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)
#
# # --- CSS ---
# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")
#
#
# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None
#
#
# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))
#
# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#         stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#         or stripped.startswith((")", "]", "}"))  # closing brackets
#         or line.startswith("    ")  # indentation
#     )
#
#
#
# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None
#
#
#
# # --- Inline code in Markdown ---
# INLINE_CODE_RE = re.compile(r"`([^`]+)`")
#
# def render_text_with_inline_code(line: str):
#     def replacer(match):
#         return f"<code>{match.group(1)}</code>"
#     html_line = INLINE_CODE_RE.sub(replacer, line)
#     html_line = html_line.replace("$", "\\$")
#     st.markdown(html_line, unsafe_allow_html=True)
#
#
# # --- Helpers ---
# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess, width="content")
#         buf.clear()
#
#
# # --- Main function ---
# def render_combined_markdown(text: str):
#     md = MarkdownIt()
#     tokens = md.parse(text)
#
#     for token in tokens:
#         if token.type in ("fence", "code_block"):
#             lang = token.info.strip() or guess_language(token.content) or ""
#             st.code(token.content, language=lang, width="content")
#         else:
#             sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#             in_sql, in_py, in_html, in_css = False, False, False, False
#
#             lines = token.content.splitlines()
#
#             for line in lines:
#                 stripped = line.strip()
#
#                 # --- Python ---
#                 if not in_py and looks_like_python_start(line):
#                     flush_buffer(sql_buffer, "sql")
#                     flush_buffer(html_buffer, "html")
#                     flush_buffer(css_buffer, "css")
#                     in_py = True
#                     py_buffer.append(line)
#                     continue
#                 elif in_py:
#                     if looks_like_python_continuation(line) or stripped == "":
#                         py_buffer.append(line)
#                         continue
#                     else:
#                         flush_buffer(py_buffer, "python")
#                         in_py = False
#
#                 # --- SQL ---
#                 if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#                     flush_buffer(py_buffer, "python")
#                     flush_buffer(html_buffer, "html")
#                     flush_buffer(css_buffer, "css")
#                     in_sql = True
#                     sql_buffer.append(line)
#                     continue
#                 elif in_sql:
#                     if stripped or stripped == "":
#                         sql_buffer.append(line)
#                         continue
#                     else:
#                         flush_buffer(sql_buffer, "sql")
#                         in_sql = False
#
#                 # --- HTML ---
#                 if not in_html and HTML_START_RE.match(line):
#                     flush_buffer(py_buffer, "python")
#                     flush_buffer(sql_buffer, "sql")
#                     flush_buffer(css_buffer, "css")
#                     in_html = True
#                     html_buffer.append(line)
#                     continue
#                 elif in_html:
#                     if stripped or stripped == "":
#                         html_buffer.append(line)
#                         if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                             flush_buffer(html_buffer, "html")
#                             in_html = False
#                         continue
#                     else:
#                         flush_buffer(html_buffer, "html")
#                         in_html = False
#
#                 # --- CSS ---
#                 if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#                     flush_buffer(py_buffer, "python")
#                     flush_buffer(sql_buffer, "sql")
#                     flush_buffer(html_buffer, "html")
#                     in_css = True
#                     css_buffer.append(line)
#                     continue
#                 elif in_css:
#                     css_buffer.append(line)
#                     if "}" in line:
#                         flush_buffer(css_buffer, "css")
#                         in_css = False
#                     continue
#
#                 # --- Regular text ---
#                 if stripped:
#                     render_text_with_inline_code(line)
#
#             # Flush remaining buffers
#             flush_buffer(py_buffer, "python")
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(html_buffer, "html")
#             flush_buffer(css_buffer, "css")
#
#


# import re
# import streamlit as st
# from markdown_it import MarkdownIt
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound
#
#
# # --- SQL Detection ---
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}
#
# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")  # code + trailing SQL comment
# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)"""
# )
#
# # --- HTML ---
# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)
#
# # --- CSS ---
# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")
#
#
# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None
#
#
# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))
#
#
# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#             stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#             or stripped.startswith((")", "]", "}"))  # closing brackets
#             or line.startswith("    ")  # indentation
#     )
#
#
# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None
#
#
# # --- Simplified text rendering with math support ---
# def render_text_with_math(line: str):
#     """Render text with LaTeX math support."""
#     # Don't escape dollar signs - let Streamlit handle them
#     st.markdown(line)
#
#
# # --- Helpers ---
# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess, width="content")
#         buf.clear()
#
#
#
#
# # (Keep all the detection functions as they are...)
#
# def render_combined_markdown(text: str):
#     """Simplified version that properly handles math formulas."""
#
#     # Process the text line by line
#     lines = text.split('\n')
#
#     sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#     in_sql, in_py, in_html, in_css = False, False, False, False
#     in_code_block = False
#     code_block_lang = ""
#     code_block_content = []
#
#     for line in lines:
#         # Check for display math blocks first ($$...$$)
#         stripped = line.strip()
#
#         # Handle display math blocks
#         if stripped.startswith('$$') and stripped.endswith('$$'):
#             math_content = stripped[2:-2].strip()
#             st.latex(math_content)
#             continue
#
#         # Check for code blocks (```)
#         if line.strip().startswith('```'):
#             if not in_code_block:
#                 # Start of code block
#                 in_code_block = True
#                 code_block_lang = line.strip()[3:].strip()  # Get language if specified
#                 code_block_content = []
#             else:
#                 # End of code block
#                 in_code_block = False
#                 if code_block_content:
#                     lang = code_block_lang or guess_language('\n'.join(code_block_content)) or ""
#                     st.code('\n'.join(code_block_content), language=lang)
#                 code_block_content = []
#                 code_block_lang = ""
#             continue
#
#         if in_code_block:
#             code_block_content.append(line)
#             continue
#
#         # Rest of your detection logic for Python, SQL, HTML, CSS...
#         # (Keep your existing detection logic here)
#
#         # --- Python ---
#         if not in_py and looks_like_python_start(line):
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(html_buffer, "html")
#             flush_buffer(css_buffer, "css")
#             in_py = True
#             py_buffer.append(line)
#             continue
#         elif in_py:
#             if looks_like_python_continuation(line) or stripped == "":
#                 py_buffer.append(line)
#                 continue
#             else:
#                 flush_buffer(py_buffer, "python")
#                 in_py = False
#
#         # --- SQL ---
#         if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#             flush_buffer(py_buffer, "python")
#             flush_buffer(html_buffer, "html")
#             flush_buffer(css_buffer, "css")
#             in_sql = True
#             sql_buffer.append(line)
#             continue
#         elif in_sql:
#             if stripped or stripped == "":
#                 sql_buffer.append(line)
#                 continue
#             else:
#                 flush_buffer(sql_buffer, "sql")
#                 in_sql = False
#
#         # --- HTML ---
#         if not in_html and HTML_START_RE.match(line):
#             flush_buffer(py_buffer, "python")
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(css_buffer, "css")
#             in_html = True
#             html_buffer.append(line)
#             continue
#         elif in_html:
#             if stripped or stripped == "":
#                 html_buffer.append(line)
#                 if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                     flush_buffer(html_buffer, "html")
#                     in_html = False
#                 continue
#             else:
#                 flush_buffer(html_buffer, "html")
#                 in_html = False
#
#         # --- CSS ---
#         if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#             flush_buffer(py_buffer, "python")
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(html_buffer, "html")
#             in_css = True
#             css_buffer.append(line)
#             continue
#         elif in_css:
#             css_buffer.append(line)
#             if "}" in line:
#                 flush_buffer(css_buffer, "css")
#                 in_css = False
#             continue
#
#         # --- Regular text ---
#         if stripped:
#             # Use st.markdown for regular text - it handles inline math with $...$
#             st.markdown(line)
#
#     # Flush any remaining buffers
#     flush_buffer(py_buffer, "python")
#     flush_buffer(sql_buffer, "sql")
#     flush_buffer(html_buffer, "html")
#     flush_buffer(css_buffer, "css")
#
#     # Flush any remaining code block
#     if code_block_content:
#         lang = code_block_lang or guess_language('\n'.join(code_block_content)) or ""
#         st.code('\n'.join(code_block_content), language=lang)
#
#
# def process_markdown_with_code(text: str):
#     """Process text that may contain code blocks but not display math."""
#     md = MarkdownIt()
#     tokens = md.parse(text)
#
#     for token in tokens:
#         if token.type in ("fence", "code_block"):
#             lang = token.info.strip() or guess_language(token.content) or ""
#             st.code(token.content, language=lang, width="content")
#         else:
#             sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#             in_sql, in_py, in_html, in_css = False, False, False, False
#
#             lines = token.content.splitlines()
#
#             for line in lines:
#                 stripped = line.strip()
#
#                 # --- Python ---
#                 if not in_py and looks_like_python_start(line):
#                     flush_buffer(sql_buffer, "sql")
#                     flush_buffer(html_buffer, "html")
#                     flush_buffer(css_buffer, "css")
#                     in_py = True
#                     py_buffer.append(line)
#                     continue
#                 elif in_py:
#                     if looks_like_python_continuation(line) or stripped == "":
#                         py_buffer.append(line)
#                         continue
#                     else:
#                         flush_buffer(py_buffer, "python")
#                         in_py = False
#
#                 # --- SQL ---
#                 if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#                     flush_buffer(py_buffer, "python")
#                     flush_buffer(html_buffer, "html")
#                     flush_buffer(css_buffer, "css")
#                     in_sql = True
#                     sql_buffer.append(line)
#                     continue
#                 elif in_sql:
#                     if stripped or stripped == "":
#                         sql_buffer.append(line)
#                         continue
#                     else:
#                         flush_buffer(sql_buffer, "sql")
#                         in_sql = False
#
#                 # --- HTML ---
#                 if not in_html and HTML_START_RE.match(line):
#                     flush_buffer(py_buffer, "python")
#                     flush_buffer(sql_buffer, "sql")
#                     flush_buffer(css_buffer, "css")
#                     in_html = True
#                     html_buffer.append(line)
#                     continue
#                 elif in_html:
#                     if stripped or stripped == "":
#                         html_buffer.append(line)
#                         if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                             flush_buffer(html_buffer, "html")
#                             in_html = False
#                         continue
#                     else:
#                         flush_buffer(html_buffer, "html")
#                         in_html = False
#
#                 # --- CSS ---
#                 if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#                     flush_buffer(py_buffer, "python")
#                     flush_buffer(sql_buffer, "sql")
#                     flush_buffer(html_buffer, "html")
#                     in_css = True
#                     css_buffer.append(line)
#                     continue
#                 elif in_css:
#                     css_buffer.append(line)
#                     if "}" in line:
#                         flush_buffer(css_buffer, "css")
#                         in_css = False
#                     continue
#
#                 # --- Regular text with inline math ---
#                 if stripped:
#                     # Just use st.markdown for text - it supports inline math with $...$
#                     st.markdown(line)
#
#             # Flush remaining buffers
#             flush_buffer(py_buffer, "python")
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(html_buffer, "html")
#             flush_buffer(css_buffer, "css")


# import re
# import streamlit as st
# from markdown_it import MarkdownIt
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound


# # --- SQL Detection ---
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}

# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")  # code + trailing SQL comment
# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)"""
# )

# # --- HTML ---
# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)

# # --- CSS ---
# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")

# # --- Math detection patterns ---
# INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$')  # $...$
# DISPLAY_MATH_RE = re.compile(r'\$\$([^\$]+)\$\$')  # $$...$$


# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None


# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))


# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#             stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#             or stripped.startswith((")", "]", "}"))  # closing brackets
#             or line.startswith("    ")  # indentation
#     )


# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None


# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess)
#         buf.clear()


# # def process_mixed_content(line: str):
# #     """Process a line that may contain mixed text and inline math."""
# #     # Find all inline math expressions
# #     st.markdown(line, unsafe_allow_html=True)


# def process_mixed_content(line: str):
#     parts = INLINE_MATH_RE.split(line)

#     is_math = False
#     for part in parts:
#         if is_math:
#             st.latex(part.strip())
#         else:
#             if part.strip():
#                 st.write(part)
#         is_math = not is_math


# def render_combined_markdown(text: str):
#     """Render markdown with proper LaTeX math support."""

#     # Split by lines for processing
#     lines = text.split('\n')

#     sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#     in_sql, in_py, in_html, in_css = False, False, False, False
#     in_code_block = False
#     code_block_lang = ""
#     code_block_content = []

#     i = 0
#     while i < len(lines):
#         line = lines[i]
#         stripped = line.strip()

#         # Display math enclosed by $$...$$ either multiline or inline
#         if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
#             formula = stripped[2:-2].strip()
#             st.latex(formula)
#             i += 1
#             continue

#         if stripped == "$$":
#             i += 1
#             math_lines = []
#             while i < len(lines) and lines[i].strip() != "$$":
#                 math_lines.append(lines[i])
#                 i += 1
#             formula = "\n".join(math_lines)
#             st.latex(formula)
#             i += 1  # skip closing $$
#             continue

#         # Check for code blocks (```)
#         elif stripped.startswith('```'):
#             if not in_code_block:
#                 # Start of code block
#                 in_code_block = True
#                 code_block_lang = stripped[3:].strip()
#                 code_block_content = []
#             else:
#                 # End of code block
#                 in_code_block = False
#                 if code_block_content:
#                     lang = code_block_lang or guess_language('\n'.join(code_block_content)) or ""
#                     st.code('\n'.join(code_block_content), language=lang)
#                 code_block_content = []
#                 code_block_lang = ""
#             i += 1
#             continue

#         if in_code_block:
#             code_block_content.append(line)
#             i += 1
#             continue

#         # --- Python ---
#         if not in_py and looks_like_python_start(line):
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(html_buffer, "html")
#             flush_buffer(css_buffer, "css")
#             in_py = True
#             py_buffer.append(line)
#             i += 1
#             continue
#         elif in_py:
#             if looks_like_python_continuation(line) or stripped == "":
#                 py_buffer.append(line)
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(py_buffer, "python")
#                 in_py = False

#         # --- SQL ---
#         if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#             flush_buffer(py_buffer, "python")
#             flush_buffer(html_buffer, "html")
#             flush_buffer(css_buffer, "css")
#             in_sql = True
#             sql_buffer.append(line)
#             i += 1
#             continue
#         elif in_sql:
#             if stripped or stripped == "":
#                 sql_buffer.append(line)
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(sql_buffer, "sql")
#                 in_sql = False

#         # --- HTML ---
#         if not in_html and HTML_START_RE.match(line):
#             flush_buffer(py_buffer, "python")
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(css_buffer, "css")
#             in_html = True
#             html_buffer.append(line)
#             i += 1
#             continue
#         elif in_html:
#             if stripped or stripped == "":
#                 html_buffer.append(line)
#                 if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                     flush_buffer(html_buffer, "html")
#                     in_html = False
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(html_buffer, "html")
#                 in_html = False

#         # --- CSS ---
#         if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#             flush_buffer(py_buffer, "python")
#             flush_buffer(sql_buffer, "sql")
#             flush_buffer(html_buffer, "html")
#             in_css = True
#             css_buffer.append(line)
#             i += 1
#             continue
#         elif in_css:
#             css_buffer.append(line)
#             if "}" in line:
#                 flush_buffer(css_buffer, "css")
#                 in_css = False
#             i += 1
#             continue

#         # --- Regular text with possible inline math ---
#         if stripped:
#             # Check if the line contains inline math
#             if INLINE_MATH_RE.search(line):
#                 process_mixed_content(line)
#             else:
#                 st.markdown(line)

#         i += 1

#     # Flush any remaining buffers
#     flush_buffer(py_buffer, "python")
#     flush_buffer(sql_buffer, "sql")
#     flush_buffer(html_buffer, "html")
#     flush_buffer(css_buffer, "css")

#     # Flush any remaining code block
#     if code_block_content:
#         lang = code_block_lang or guess_language('\n'.join(code_block_content)) or ""
#         st.code('\n'.join(code_block_content), language=lang)


# import re
# import streamlit as st
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound

# # SQL detection keywords
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}

# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")

# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|
#     try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)""",
#     re.VERBOSE,
# )

# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)

# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")

# INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$')
# DISPLAY_MATH_RE = re.compile(r'\$\$([^\$]+)\$\$')

# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None


# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))


# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#         stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#         or stripped.startswith((")", "]", "}"))
#         or line.startswith("    ")
#     )


# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None


# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess)
#         buf.clear()


# def process_mixed_content(line: str):
#     """Render text with inline math ($...$) using st.latex()."""
#     parts = INLINE_MATH_RE.split(line)
#     is_math = False

#     for part in parts:
#         if is_math:
#             st.latex(part.strip())
#         else:
#             if part.strip():
#                 st.write(part)
#         is_math = not is_math


# def render_combined_markdown(text: str):
#     lines = text.split("\n")

#     sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#     in_sql = in_py = in_html = in_css = False

#     in_code_block = False
#     code_block_lang = ""
#     code_block_content = []

#     i = 0
#     while i < len(lines):
#         line = lines[i]
#         stripped = line.strip()

#         # Display math: inline $$...$$
#         if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
#             formula = stripped[2:-2].strip()
#             st.latex(formula)
#             i += 1
#             continue

#         # Display math: multi-line
#         if stripped == "$$":
#             i += 1
#             math_lines = []
#             while i < len(lines) and lines[i].strip() != "$$":
#                 math_lines.append(lines[i])
#                 i += 1
#             st.latex("\n".join(math_lines))
#             i += 1
#             continue

#         # Code blocks
#         if stripped.startswith("```"):
#             if not in_code_block:
#                 in_code_block = True
#                 code_block_lang = stripped[3:].strip()
#                 code_block_content = []
#             else:
#                 in_code_block = False
#                 lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#                 st.code("\n".join(code_block_content), language=lang)
#             i += 1
#             continue

#         if in_code_block:
#             code_block_content.append(line)
#             i += 1
#             continue

#         # Python block detection
#         if not in_py and looks_like_python_start(line):
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_py = True
#             py_buffer.append(line)
#             i += 1
#             continue
#         elif in_py:
#             if looks_like_python_continuation(line) or stripped == "":
#                 py_buffer.append(line)
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(py_buffer, "python")
#                 in_py = False

#         # SQL detection
#         if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#             flush_buffer(py_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_sql = True
#             sql_buffer.append(line)
#             i += 1
#             continue
#         elif in_sql:
#             sql_buffer.append(line)
#             i += 1
#             continue

#         # HTML detection
#         if not in_html and HTML_START_RE.match(line):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(css_buffer)
#             in_html = True
#             html_buffer.append(line)
#             i += 1
#             continue
#         elif in_html:
#             html_buffer.append(line)
#             if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                 flush_buffer(html_buffer, "html")
#                 in_html = False
#             i += 1
#             continue

#         # CSS detection
#         if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             in_css = True
#             css_buffer.append(line)
#             i += 1
#             continue
#         elif in_css:
#             css_buffer.append(line)
#             if "}" in line:
#                 flush_buffer(css_buffer, "css")
#                 in_css = False
#             i += 1
#             continue

#         # Inline math handling
#         if INLINE_MATH_RE.search(line):
#             process_mixed_content(line)
#         else:
#             st.write(line)

#         i += 1

#     flush_buffer(py_buffer, "python")
#     flush_buffer(sql_buffer, "sql")
#     flush_buffer(html_buffer, "html")
#     flush_buffer(css_buffer, "css")

#     if code_block_content:
#         lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#         st.code("\n".join(code_block_content), language=lang)

# import re
# import streamlit as st
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound

# # SQL detection keywords
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}

# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")

# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|
#     try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)""",
#     re.VERBOSE,
# )

# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)

# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")

# INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$')
# DISPLAY_MATH_RE = re.compile(r'\$\$([^\$]+)\$\$')

# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None

# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))

# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#         stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#         or stripped.startswith((")", "]", "}"))
#         or line.startswith("    ")
#     )

# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None

# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess)
#         buf.clear()

# def process_mixed_content(line: str):
#     """Render text with inline math ($...$) using st.latex()."""
#     parts = INLINE_MATH_RE.split(line)
#     is_math = False

#     for part in parts:
#         if is_math:
#             st.latex(part.strip())
#         else:
#             if part.strip():
#                 st.write(part)
#         is_math = not is_math

# def render_combined_markdown(text: str):
#     lines = text.split("\n")

#     sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#     in_sql = in_py = in_html = in_css = False

#     in_code_block = False
#     code_block_lang = ""
#     code_block_content = []

#     i = 0
#     while i < len(lines):
#         line = lines[i]
#         stripped = line.strip()

#         # Display math: inline $$...$$ (single line)
#         if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             formula = stripped[2:-2].strip()
#             st.latex(formula)
#             i += 1
#             continue

#         # Display math: multi-line $$ block
#         if stripped == "$$":
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             i += 1
#             math_lines = []
#             while i < len(lines) and lines[i].strip() != "$$":
#                 if lines[i].strip():  # Skip empty lines to avoid breaking KaTeX
#                     math_lines.append(lines[i])
#                 i += 1
#             if math_lines:
#                 st.latex("\n".join(math_lines))
#             i += 1
#             continue

#         # Display math: square bracket block [ ... ] (e.g., Gaussian distribution formula)
#         if stripped == "[":
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             i += 1
#             math_lines = []
#             while i < len(lines) and lines[i].strip() != "]":
#                 if lines[i].strip():  # Skip empty lines to avoid breaking KaTeX
#                     math_lines.append(lines[i])
#                 i += 1
#             if math_lines:
#                 st.latex("\n".join(math_lines))
#             i += 1
#             continue

#         # Code blocks
#         if stripped.startswith("```"):
#             if not in_code_block:
#                 in_code_block = True
#                 code_block_lang = stripped[3:].strip()
#                 code_block_content = []
#             else:
#                 in_code_block = False
#                 lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#                 st.code("\n".join(code_block_content), language=lang)
#             i += 1
#             continue

#         if in_code_block:
#             code_block_content.append(line)
#             i += 1
#             continue

#         # Python block detection
#         if not in_py and looks_like_python_start(line):
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_py = True
#             py_buffer.append(line)
#             i += 1
#             continue
#         elif in_py:
#             if looks_like_python_continuation(line) or stripped == "":
#                 py_buffer.append(line)
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(py_buffer, "python")
#                 in_py = False

#         # SQL detection
#         if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#             flush_buffer(py_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_sql = True
#             sql_buffer.append(line)
#             i += 1
#             continue
#         elif in_sql:
#             sql_buffer.append(line)
#             i += 1
#             continue

#         # HTML detection
#         if not in_html and HTML_START_RE.match(line):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(css_buffer)
#             in_html = True
#             html_buffer.append(line)
#             i += 1
#             continue
#         elif in_html:
#             html_buffer.append(line)
#             if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                 flush_buffer(html_buffer, "html")
#                 in_html = False
#             i += 1
#             continue

#         # CSS detection
#         if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             in_css = True
#             css_buffer.append(line)
#             i += 1
#             continue
#         elif in_css:
#             css_buffer.append(line)
#             if "}" in line:
#                 flush_buffer(css_buffer, "css")
#                 in_css = False
#             i += 1
#             continue

#         # Inline math handling
#         if INLINE_MATH_RE.search(line):
#             process_mixed_content(line)
#         else:
#             st.write(line)

#         i += 1

#     # Flush any remaining buffers at the end
#     flush_buffer(py_buffer, "python")
#     flush_buffer(sql_buffer, "sql")
#     flush_buffer(html_buffer, "html")
#     flush_buffer(css_buffer, "css")

#     if code_block_content:
#         lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#         st.code("\n".join(code_block_content), language=lang)


# import re
# import streamlit as st
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound

# # SQL detection keywords
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}

# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")

# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|
#     try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)""",
#     re.VERBOSE,
# )

# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)

# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")

# INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$')
# DISPLAY_MATH_RE = re.compile(r'\$\$([^\$]+)\$\$')

# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None

# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))

# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#         stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#         or stripped.startswith((")", "]", "}"))
#         or line.startswith("    ")
#     )

# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None

# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess)
#         buf.clear()

# def process_mixed_content(line: str):
#     """Render text with inline math ($...$) using st.latex()."""
#     parts = INLINE_MATH_RE.split(line)
#     is_math = False

#     for part in parts:
#         if is_math:
#             st.latex(part.strip())
#         else:
#             if part.strip():
#                 st.write(part)
#         is_math = not is_math

# def render_combined_markdown(text: str):
#     lines = text.split("\n")

#     sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#     in_sql = in_py = in_html = in_css = False

#     in_code_block = False
#     code_block_lang = ""
#     code_block_content = []

#     i = 0
#     while i < len(lines):
#         line = lines[i]
#         stripped = line.strip()

#         # Display math: single line [ ... ] (e.g., Gaussian distribution formula) <-- NEW BLOCK
#         if stripped.startswith("[") and stripped.endswith("]") and len(stripped) > 2:
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             formula = stripped[1:-1].strip() # Strip off the outer [ and ]
#             if formula:
#                 st.latex(formula)
#             i += 1
#             continue

#         # Display math: inline $$...$$ (single line)
#         if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             formula = stripped[2:-2].strip()
#             # st.latex(formula)
#             st.write(formula)
#             i += 1
#             continue

#         # Display math: multi-line $$ block
#         if stripped == "$$":
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             i += 1
#             math_lines = []
#             while i < len(lines) and lines[i].strip() != "$$":
#                 if lines[i].strip():  # Skip empty lines to avoid breaking KaTeX
#                     math_lines.append(lines[i])
#                 i += 1
#             if math_lines:
#                 # st.latex("\n".join(math_lines))
#                 st.write("\n".join(math_lines))

#             i += 1
#             continue

#         # Display math: square bracket block [ ... ] (e.g., Gaussian distribution formula)
#         if stripped == "[":
#             # Flush any pending code buffers before rendering math
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             i += 1
#             math_lines = []
#             while i < len(lines) and lines[i].strip() != "]":
#                 if lines[i].strip():  # Skip empty lines to avoid breaking KaTeX
#                     math_lines.append(lines[i])
#                 i += 1
#             if math_lines:
#                 st.latex("\n".join(math_lines))
#             i += 1
#             continue

#         # Code blocks
#         if stripped.startswith("```"):
#             if not in_code_block:
#                 in_code_block = True
#                 code_block_lang = stripped[3:].strip()
#                 code_block_content = []
#             else:
#                 in_code_block = False
#                 lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#                 st.code("\n".join(code_block_content), language=lang)
#             i += 1
#             continue

#         if in_code_block:
#             code_block_content.append(line)
#             i += 1
#             continue

#         # Python block detection
#         if not in_py and looks_like_python_start(line):
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_py = True
#             py_buffer.append(line)
#             i += 1
#             continue
#         elif in_py:
#             if looks_like_python_continuation(line) or stripped == "":
#                 py_buffer.append(line)
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(py_buffer, "python")
#                 in_py = False

#         # SQL detection
#         if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#             flush_buffer(py_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_sql = True
#             sql_buffer.append(line)
#             i += 1
#             continue
#         elif in_sql:
#             sql_buffer.append(line)
#             i += 1
#             continue

#         # HTML detection
#         if not in_html and HTML_START_RE.match(line):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(css_buffer)
#             in_html = True
#             html_buffer.append(line)
#             i += 1
#             continue
#         elif in_html:
#             html_buffer.append(line)
#             if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                 flush_buffer(html_buffer, "html")
#                 in_html = False
#             i += 1
#             continue

#         # CSS detection
#         if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             in_css = True
#             css_buffer.append(line)
#             i += 1
#             continue
#         elif in_css:
#             css_buffer.append(line)
#             if "}" in line:
#                 flush_buffer(css_buffer, "css")
#                 in_css = False
#             i += 1
#             continue

#         # Inline math handling
#         if INLINE_MATH_RE.search(line):
#             process_mixed_content(line)
#         else:
#             st.write(line)

#         i += 1

#     # Flush any remaining buffers at the end
#     flush_buffer(py_buffer, "python")
#     flush_buffer(sql_buffer, "sql")
#     flush_buffer(html_buffer, "html")
#     flush_buffer(css_buffer, "css")

#     if code_block_content:
#         lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#         st.code("\n".join(code_block_content), language=lang)


#
# import re
# import streamlit as st
# from pygments.lexers import guess_lexer
# from pygments.util import ClassNotFound
#
# # SQL detection keywords
# SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
# ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
# MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
# POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}
#
# SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")
#
# PYTHON_START_RE = re.compile(
#     r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|
#      try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)""",
#     re.VERBOSE,
# )
#
# HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)
#
# CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
# CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")
#
# # INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$')
# INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$|\\\(([^\)]+)\\\)')
# DISPLAY_MATH_RE = re.compile(r'\$\$([^\$]+)\$\$')
#
# # NEW: Regex to detect raw LaTeX code on a single line (frequently used commands)
# RAW_LATEX_RE = re.compile(r"\\(frac|sqrt|exp|sum|int|mu|sigma|left|right|alpha|beta|pi|text)")
#
# def detect_sql_dialect(text: str) -> str | None:
#     if re.search(r"\bSELECT\b", text, re.IGNORECASE):
#         for kw in ORACLE_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "oracle-sql"
#         for kw in MYSQL_SQL_KEYWORDS:
#             if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
#                 return "mysql"
#         for kw in POSTGRES_SQL_KEYWORDS:
#             if re.search(rf"{kw}", text, re.IGNORECASE):
#                 return "postgresql"
#         return "sql"
#     return None
#
# def looks_like_python_start(line: str) -> bool:
#     return bool(PYTHON_START_RE.match(line))
#
# def looks_like_python_continuation(line: str) -> bool:
#     stripped = line.strip()
#     return bool(stripped) and (
#         stripped.startswith(("#", "else:", "elif", "except", "finally", "return", "yield"))
#         or stripped.startswith((")", "]", "}"))
#         or line.startswith("    ")
#     )
#
# def guess_language(text: str) -> str | None:
#     dialect = detect_sql_dialect(text)
#     if dialect:
#         return "sql"
#     try:
#         lexer = guess_lexer(text)
#         return lexer.aliases[0] if lexer.aliases else None
#     except ClassNotFound:
#         return None
#
# def flush_buffer(buf, lang=None):
#     if buf:
#         lang_guess = lang or guess_language("\n".join(buf)) or ""
#         st.code("\n".join(buf), language=lang_guess)
#         buf.clear()
#
# # def process_mixed_content(line: str):
# #     """Render text with inline math ($...$) using st.latex()."""
# #     parts = INLINE_MATH_RE.split(line)
# #     is_math = False
# #
# #     for part in parts:
# #         if is_math:
# #             st.latex(part.strip())
# #         else:
# #             if part.strip():
# #                 # st.write(part)
# #                 st.markdown(part.strip(), unsafe_allow_html=False)
# #         is_math = not is_math
#
#
# def process_mixed_content(line: str):
#     """Render text with inline math ($...$ or \(...\)) using st.latex() and surrounding text with st.markdown()."""
#
#     # Use finditer to iterate over all matches and surrounding text
#     last_end = 0
#
#     # Iterate through all matches found by the updated regex
#     for match in INLINE_MATH_RE.finditer(line):
#
#         # 1. Process the non-math text before the current match
#         non_math_part = line[last_end:match.start()].strip()
#         if non_math_part:
#             st.markdown(non_math_part)
#
#         # 2. Extract the math content (it could be in group 1 or group 2)
#         # Group 1 is for $...$ match. Group 2 is for \(...\) match.
#         math_content = match.group(1) or match.group(2)
#
#         # 3. Process the math content using st.latex()
#         if math_content:
#             st.latex(math_content.strip())
#
#         # Update the position for the next non-math part
#         last_end = match.end()
#
#     # 4. Process any remaining non-math text after the last match
#     remaining_text = line[last_end:].strip()
#     if remaining_text:
#         st.markdown(remaining_text)
#
# # def process_mixed_content(line: str):
# #     """Render text with inline math ($...$) using st.latex()."""
# #     parts = INLINE_MATH_RE.split(line)
# #     is_math = False
# #
# #     for part in parts:
# #         if is_math:
# #             # Render math content using st.latex()
# #             st.latex(part.strip())
# #         else:
# #             if part.strip():
# #                 # --- FIX: Use st.markdown() instead of st.write() ---
# #                 # This allows standard markdown (bold, italics, etc.)
# #                 # AND renders any single-symbol LaTeX that Streamlit's
# #                 # markdown processor can handle (like $mu$ if outside the
# #                 # INLINE_MATH_RE detection or just standard text).
# #                 st.markdown(part.strip(), unsafe_allow_html=False)
# #                 # Note: st.markdown can also process math symbols
# #                 # like $\mu$ and $\sigma$ if they are passed in simple Markdown.
# #                 # Since we already handle $...$ and $$...$$, this is for
# #                 # everything else.
# #         is_math = not is_math
#
# def render_combined_markdown(text: str):
#     lines = text.split("\n")
#
#     sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
#     in_sql = in_py = in_html = in_css = False
#
#     in_code_block = False
#     code_block_lang = ""
#     code_block_content = []
#
#     # Store the expected closing delimiter when inside a math block
#     math_closing_delimiter = ""
#
#     i = 0
#     while i < len(lines):
#         line = lines[i]
#         stripped = line.strip()
#
#         # Check for closing math delimiter first
#         if math_closing_delimiter and stripped == math_closing_delimiter:
#             # Render the collected math content
#             if code_block_content:
#                 st.latex("\n".join(code_block_content))
#             code_block_content.clear()
#             math_closing_delimiter = "" # Exit math block
#             i += 1
#             continue
#
#         # If currently in a multi-line math block, append the line and continue
#         if math_closing_delimiter:
#              if stripped:
#                 code_block_content.append(line)
#              i += 1
#              continue
#
#         # --- MATH RENDERING FIXES ---
#         # Helper to start a math block
#         def start_math_block(formula_content, closing_delimiter=""):
#             nonlocal math_closing_delimiter
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#
#             if closing_delimiter:
#                 # Start multi-line collection
#                 math_closing_delimiter = closing_delimiter
#                 code_block_content.clear()
#                 if formula_content:
#                     code_block_content.append(formula_content)
#             else:
#                 # Render single-line block immediately
#                 if formula_content:
#                     st.latex(formula_content)
#
#         # 1. Display math: single line [ ... ] (Handles custom single line)
#         if stripped.startswith("[") and stripped.endswith("]") and len(stripped) > 2:
#             formula = stripped[1:-1].strip()
#             start_math_block(formula)
#             i += 1
#             continue
#
#         # 2. Display math: inline $$...$$ (single line)
#         if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
#             formula = stripped[2:-2].strip()
#             start_math_block(formula)
#             i += 1
#             continue
#
#         # 3. Display math: multi-line $$ block
#         if stripped == "$$":
#             start_math_block("", "$$")
#             i += 1
#             continue
#
#         # 4. Display math: multi-line [ or \[ block (Handles custom and Markdown formats)
#         if stripped in ("[", "\\["):
#             closing_delimiter = "]" if stripped == "[" else "\\]"
#             start_math_block("", closing_delimiter)
#             i += 1
#             continue
#
#         # 5. Raw LaTeX Line Detection (Handles standalone formulas without delimiters)
#         if stripped and RAW_LATEX_RE.search(stripped) and not in_code_block:
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#
#             # Use st.latex() directly on the line content
#             st.latex(line)
#             i += 1
#             continue
#
#         # --- END MATH RENDERING FIXES ---
#
#         # Code blocks
#         if stripped.startswith("```"):
#             if not in_code_block:
#                 in_code_block = True
#                 code_block_lang = stripped[3:].strip()
#                 code_block_content = []
#             else:
#                 in_code_block = False
#                 lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#                 st.code("\n".join(code_block_content), language=lang)
#             i += 1
#             continue
#
#         if in_code_block:
#             code_block_content.append(line)
#             i += 1
#             continue
#
#         # Python block detection
#         if not in_py and looks_like_python_start(line):
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_py = True
#             py_buffer.append(line)
#             i += 1
#             continue
#         elif in_py:
#             if looks_like_python_continuation(line) or stripped == "":
#                 py_buffer.append(line)
#                 i += 1
#                 continue
#             else:
#                 flush_buffer(py_buffer, "python")
#                 in_py = False
#
#         # SQL detection
#         if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
#             flush_buffer(py_buffer)
#             flush_buffer(html_buffer)
#             flush_buffer(css_buffer)
#             in_sql = True
#             sql_buffer.append(line)
#             i += 1
#             continue
#         elif in_sql:
#             sql_buffer.append(line)
#             i += 1
#             continue
#
#         # HTML detection
#         if not in_html and HTML_START_RE.match(line):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(css_buffer)
#             in_html = True
#             html_buffer.append(line)
#             i += 1
#             continue
#         elif in_html:
#             html_buffer.append(line)
#             if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
#                 flush_buffer(html_buffer, "html")
#                 in_html = False
#             i += 1
#             continue
#
#         # CSS detection
#         if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
#             flush_buffer(py_buffer)
#             flush_buffer(sql_buffer)
#             flush_buffer(html_buffer)
#             in_css = True
#             css_buffer.append(line)
#             i += 1
#             continue
#         elif in_css:
#             css_buffer.append(line)
#             if "}" in line:
#                 flush_buffer(css_buffer, "css")
#                 in_css = False
#             i += 1
#             continue
#
#         # Inline math handling or general text
#         if INLINE_MATH_RE.search(line):
#             process_mixed_content(line)
#         else:
#             st.write(line)
#
#         i += 1
#
#     # Flush any remaining buffers at the end
#     flush_buffer(py_buffer, "python")
#     flush_buffer(sql_buffer, "sql")
#     flush_buffer(html_buffer, "html")
#     flush_buffer(css_buffer, "css")
#
#     # Final flush for any pending math block content (if the stream ended before the closing delimiter)
#     if code_block_content and math_closing_delimiter:
#         st.latex("\n".join(code_block_content))
#     # Final flush for any pending code block content
#     elif code_block_content:
#         lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
#         st.code("\n".join(code_block_content), language=lang)


import re
import streamlit as st
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

# SQL detection keywords
SQL_START_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
ORACLE_SQL_KEYWORDS = {"DUAL", "NVL", "TO_DATE", "SYSDATE", "ROWNUM"}
MYSQL_SQL_KEYWORDS = {"AUTO_INCREMENT", "ENGINE=", "UNSIGNED", "CHARSET", "COLLATE", "LIMIT"}
POSTGRES_SQL_KEYWORDS = {"SERIAL", "BIGSERIAL", "RETURNING", "ILIKE", "SIMILAR TO", "ARRAY", "JSONB", "::"}

SQL_COMMENT_RE = re.compile(r"(.*?)(--.*)$")

PYTHON_START_RE = re.compile(
    r"""^\s*(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|from\s+\w+|if\s+.+:|for\s+.+:|while\s+.+:|
     try:|except\s+.+:|with\s+.+:|\w+\s*=\s*.+)""",
    re.VERBOSE,
)

HTML_START_RE = re.compile(r"^\s*<(!DOCTYPE|html|head|body|div|span|p|a|ul|ol|li|script|style|!--)", re.IGNORECASE)

CSS_START_RE = re.compile(r"^\s*[.#]?\w[\w\-]*\s*\{|^\s*@[a-z\-]+\s+[^{]*\{", re.IGNORECASE)
CSS_PROP_RE = re.compile(r"^\s*[\w\-]+\s*:\s*[^;]+;?\s*$")

# Standard Markdown/Streamlit inline math detection
INLINE_MATH_RE = re.compile(r'\$([^\$]+)\$')
DISPLAY_MATH_RE = re.compile(r'\$\$([^\$]+)\$\$')

# FIX: Regex to find and capture the content of \( ... \) delimiters for conversion
# LATEX_INLINE_DELIMITER_RE = re.compile(r'\\\(([^\)]+)\\\)')
LATEX_INLINE_DELIMITER_RE = re.compile(r'\\\(\s*([^\)]+?)\s*\\\)')

# Regex to detect raw LaTeX code on a single line (frequently used commands)
RAW_LATEX_RE = re.compile(r"\\(frac|sqrt|exp|sum|int|mu|sigma|left|right|alpha|beta|pi|text)")


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
            or stripped.startswith((")", "]", "}"))
            or line.startswith("    ")
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


def flush_buffer(buf, lang=None):
    if buf:
        lang_guess = lang or guess_language("\n".join(buf)) or ""
        st.code("\n".join(buf), language=lang_guess)
        buf.clear()


# REMOVED: process_mixed_content is no longer needed.
# We rely on st.markdown to handle the entire line including the inline $...$ math.

def render_combined_markdown(text: str):
    # --- FIX: Pre-process the text to convert \( ... \) to $...$ ---
    # This standardizes all inline math notation for Streamlit's Markdown engine.
    text = LATEX_INLINE_DELIMITER_RE.sub(r'$\1$', text)

    lines = text.split("\n")

    sql_buffer, py_buffer, html_buffer, css_buffer = [], [], [], []
    in_sql = in_py = in_html = in_css = False

    in_code_block = False
    code_block_lang = ""
    code_block_content = []

    # Store the expected closing delimiter when inside a math block
    math_closing_delimiter = ""

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for closing math delimiter first
        if math_closing_delimiter and stripped == math_closing_delimiter:
            # Render the collected math content
            if code_block_content:
                st.latex("\n".join(code_block_content))
            code_block_content.clear()
            math_closing_delimiter = ""  # Exit math block
            i += 1
            continue

        # If currently in a multi-line math block, append the line and continue
        if math_closing_delimiter:
            if stripped:
                code_block_content.append(line)
            i += 1
            continue

        # --- MATH RENDERING ---
        # Helper to start a math block
        def start_math_block(formula_content, closing_delimiter=""):
            nonlocal math_closing_delimiter
            flush_buffer(py_buffer)
            flush_buffer(sql_buffer)
            flush_buffer(html_buffer)
            flush_buffer(css_buffer)

            if closing_delimiter:
                # Start multi-line collection
                math_closing_delimiter = closing_delimiter
                code_block_content.clear()
                if formula_content:
                    code_block_content.append(formula_content)
            else:
                # Render single-line block immediately
                if formula_content:
                    st.latex(formula_content)

        # 1. Display math: single line [ ... ] (Handles custom single line)
        if stripped.startswith("[") and stripped.endswith("]") and len(stripped) > 2:
            formula = stripped[1:-1].strip()
            start_math_block(formula)
            i += 1
            continue

        # 2. Display math: inline $$...$$ (single line)
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            formula = stripped[2:-2].strip()
            start_math_block(formula)
            i += 1
            continue

        # 3. Display math: multi-line $$ block
        if stripped == "$$":
            start_math_block("", "$$")
            i += 1
            continue

        # 4. Display math: multi-line [ or \[ block (Handles custom and Markdown formats)
        if stripped in ("[", "\\["):
            closing_delimiter = "]" if stripped == "[" else "\\]"
            start_math_block("", closing_delimiter)
            i += 1
            continue

        # 5. Raw LaTeX Line Detection (Handles standalone formulas without delimiters)
        if stripped and RAW_LATEX_RE.search(stripped) and not in_code_block:
            flush_buffer(py_buffer)
            flush_buffer(sql_buffer)
            flush_buffer(html_buffer)
            flush_buffer(css_buffer)

            # Use st.latex() directly on the line content
            st.markdown(line)
            i += 1
            continue

        # --- END MATH RENDERING ---

        # Code blocks
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_lang = stripped[3:].strip()
                code_block_content = []
            else:
                in_code_block = False
                lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
                st.code("\n".join(code_block_content), language=lang)
            i += 1
            continue

        if in_code_block:
            code_block_content.append(line)
            i += 1
            continue

        # Python block detection
        if not in_py and looks_like_python_start(line):
            flush_buffer(sql_buffer)
            flush_buffer(html_buffer)
            flush_buffer(css_buffer)
            in_py = True
            py_buffer.append(line)
            i += 1
            continue
        elif in_py:
            if looks_like_python_continuation(line) or stripped == "":
                py_buffer.append(line)
                i += 1
                continue
            else:
                flush_buffer(py_buffer, "python")
                in_py = False

        # SQL detection
        if not in_sql and stripped.upper().startswith(SQL_START_KEYWORDS):
            flush_buffer(py_buffer)
            flush_buffer(html_buffer)
            flush_buffer(css_buffer)
            in_sql = True
            sql_buffer.append(line)
            i += 1
            continue
        elif in_sql:
            sql_buffer.append(line)
            i += 1
            continue

        # HTML detection
        if not in_html and HTML_START_RE.match(line):
            flush_buffer(py_buffer)
            flush_buffer(sql_buffer)
            flush_buffer(css_buffer)
            in_html = True
            html_buffer.append(line)
            i += 1
            continue
        elif in_html:
            html_buffer.append(line)
            if stripped.lower().endswith("</html>") or stripped.lower().endswith("</body>"):
                flush_buffer(html_buffer, "html")
                in_html = False
            i += 1
            continue

        # CSS detection
        if not in_css and (CSS_START_RE.match(line) or CSS_PROP_RE.match(line)):
            flush_buffer(py_buffer)
            flush_buffer(sql_buffer)
            flush_buffer(html_buffer)
            in_css = True
            css_buffer.append(line)
            i += 1
            continue
        elif in_css:
            css_buffer.append(line)
            if "}" in line:
                flush_buffer(css_buffer, "css")
                in_css = False
            i += 1
            continue

        # Inline math handling or general text
        if INLINE_MATH_RE.search(line):

            # Flush existing buffers as the content is changing mode
            flush_buffer(py_buffer, "python")
            flush_buffer(sql_buffer, "sql")
            flush_buffer(html_buffer, "html")
            flush_buffer(css_buffer, "css")
            in_py = in_sql = in_html = in_css = False

            # FIX: Render the WHOLE line as Markdown. After pre-conversion,
            # Streamlit handles list/text formatting AND inline $...$ math correctly.
            st.markdown(line)

        else:
            # If line is not in a block/buffer and doesn't have inline math,
            # flush any outstanding buffers and then render the line as standard Markdown.

            flush_buffer(py_buffer, "python")
            flush_buffer(sql_buffer, "sql")
            flush_buffer(html_buffer, "html")
            flush_buffer(css_buffer, "css")
            in_py = in_sql = in_html = in_css = False

            st.markdown(line)

        i += 1

    # Flush any remaining buffers at the end
    flush_buffer(py_buffer, "python")
    flush_buffer(sql_buffer, "sql")
    flush_buffer(html_buffer, "html")
    flush_buffer(css_buffer, "css")

    # Final flush for any pending math block content (if the stream ended before the closing delimiter)
    if code_block_content and math_closing_delimiter:
        st.latex("\n".join(code_block_content))
    # Final flush for any pending code block content
    elif code_block_content:
        lang = code_block_lang or guess_language("\n".join(code_block_content)) or ""
        st.code("\n".join(code_block_content), language=lang)