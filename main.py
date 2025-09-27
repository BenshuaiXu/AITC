# login.py
from PIL import Image
from utils.graphic_pro import get_base64_image
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import stripe

# USERS = st.secrets["users"]

st.set_page_config(
    page_title="AITC",
    page_icon="photo/ai_logo_4.png",
    layout="wide",
    # initial_sidebar_state="auto"
    initial_sidebar_state="collapsed"  # Options: "auto", "expanded", or "collapsed"

)

sidebar_logo = Image.open("photo/ai_logo_4.png")
st.sidebar.image(sidebar_logo, use_container_width=True)

stripe.api_key = st.secrets["stripe_secret"]
STRIPE_PRICE_ID = st.secrets["stripe_price_id"]
DOMAIN_URL = "http://lucia.streamlit.app"

# Inject custom CSS for darker deep sea blue background
st.markdown("""
    <style>
        body {
            background-color: #121c3b;
            color: #f5f5f5;
        }
        .stApp {
            background-color: #1e2a4c;
        }
        .css-1d391kg, .css-1v0mbdj, .css-1dp5vir, .css-1cpxqw2 {
            background-color: #1e2a4c !important;
            color: #f0f8ff !important;
        }
        .stTextInput > div > div > input {
            background-color: #2f4b7c;
            color: #f0f8ff;
        }
        .stTextInput label {
            color: #ffffff !important;
        }
        .stButton > button {
            background-color: #3b3f73;
            color: white;
        }

        /* TAB LABEL COLORS */
        .stTabs [data-baseweb="tab-list"] button {
            color: white !important; /* Inactive tabs */
        }

        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            color: yellow !important; /* Active tab color */
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- Google Sheets Credentials ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load credentials from Streamlit secrets
credentials_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)

# Google Sheet URL and worksheet
sheet_url = "https://docs.google.com/spreadsheets/d/1nrfVkmUvZbjcZKPGrxvzsubjyHeBEfB0aEiHjknZQMc/edit?gid=0#gid=0"
sheet = client.open_by_url(sheet_url).sheet1  # use first sheet


def get_users_from_sheet():
    """Fetch usernames and passwords from Google Sheets"""
    records = sheet.get_all_records()
    users = {record["username"]: record["password"] for record in records}
    return users


def register_user(username, password):
    """Write a new user to the Google Sheet"""
    sheet.append_row([username, password])
    # sheet.append_row([username.strip(), password.strip()])


def user_exists(email):
    users = get_users_from_sheet()
    return email in users


def login_screen():
    col_left, col_main1, col_right = st.columns([1, 8, 1])

    with col_main1:
        col1, col2 = st.columns([7, 4])

        with col2:
            st.write("")

            st.markdown("""
                <style>
                /* Style all tab labels */
                div[data-baseweb="tab"] {
                    color: white !important;        /* White text for inactive tabs */
                    font-weight: 600;
                }

                /* Style for the active tab */
                div[data-baseweb="tab"][aria-selected="true"] {
                    color: #4CAF50 !important;      /* Green text for active tab */
                }
                </style>
            """, unsafe_allow_html=True)

            # Create two tabs: Login and Register
            tab_login, tab_register = st.tabs(["Login", "Register"])

            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    login_button = st.form_submit_button("Login")

                    if login_button:
                        USERS = get_users_from_sheet()
                        if username.strip() in USERS and USERS[username.strip()] == password.strip():
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = username.strip()
                            st.success("Login successful. Redirecting...")
                            st.switch_page("pages/AITC.py")
                        else:
                            st.error("Incorrect username or password")

            with tab_register:
                with st.form("register_form"):
                    # name = st.text_input("Full Name")
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")

                    if st.form_submit_button("Proceed to Payment"):
                        if user_exists(email):
                            st.error("This email is already registered.")
                        elif not email or not password:
                            st.error("Please fill all fields.")
                        else:
                            try:
                                checkout_session = stripe.checkout.Session.create(
                                    success_url=f"{DOMAIN_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
                                    cancel_url=f"{DOMAIN_URL}",
                                    payment_method_types=["card"],
                                    mode="subscription",
                                    line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
                                    customer_email=email,
                                    metadata={
                                        "email": email,
                                        "password": password
                                    }
                                )
                                st.markdown(f"[Click here to pay and complete registration]({checkout_session.url})")
                            except Exception as e:
                                st.error(f"Error creating payment session: {e}")

        with col1:
            ai_logo = get_base64_image("photo/ai_logo_4.png")
            st.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 16px; margin-bottom: 1px;'>
                        <img src='{ai_logo}' width='900'>
                    </div>
                    """, unsafe_allow_html=True)


# Auth check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {
                display: none;
            }
            div[data-testid="collapsedControl"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    login_screen()
else:
    st.switch_page("pages/AITC.py")





