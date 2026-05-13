import streamlit as st
import requests
import os

# ── Config ──────────────────────────────────────────────────────────────────
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="TailorTalk – Drive Assistant",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem; padding-bottom: 0; }

[data-testid="stSidebar"] {
    background: #0f0f13;
    border-right: 1px solid #1e1e2e;
}
[data-testid="stSidebar"] * { color: #cdd6f4 !important; }

.stApp { background: #13131a; color: #cdd6f4; }

.tt-header {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #cba6f7;
    letter-spacing: -0.02em;
    margin-bottom: 0.25rem;
}
.tt-sub {
    font-size: 0.85rem;
    color: #6c7086;
    margin-bottom: 1.5rem;
}

.msg-user {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px 12px 2px 12px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0 0.5rem 3rem;
    color: #cdd6f4;
    font-size: 0.95rem;
    line-height: 1.6;
}
.msg-ai {
    background: #181825;
    border: 1px solid #313244;
    border-left: 3px solid #cba6f7;
    border-radius: 2px 12px 12px 12px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 3rem 0.5rem 0;
    color: #cdd6f4;
    font-size: 0.95rem;
    line-height: 1.6;
}
.msg-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
    opacity: 0.5;
}

.file-grid { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.75rem; }
.file-card {
    background: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    min-width: 200px;
    max-width: 280px;
    transition: border-color 0.2s;
}
.file-card:hover { border-color: #cba6f7; }
.file-name {
    font-weight: 600;
    font-size: 0.85rem;
    color: #cdd6f4;
    margin-bottom: 0.2rem;
    word-break: break-word;
}
.file-meta { font-size: 0.72rem; color: #6c7086; }
.file-type-badge {
    display: inline-block;
    background: #313244;
    color: #cba6f7;
    border-radius: 4px;
    padding: 0.1rem 0.4rem;
    font-size: 0.68rem;
    font-family: 'Space Mono', monospace;
    margin-bottom: 0.3rem;
}
.file-link {
    display: inline-block;
    margin-top: 0.3rem;
    font-size: 0.75rem;
    color: #89dceb;
    text-decoration: none;
}

.stTextInput input {
    background: #1e1e2e !important;
    border: 1px solid #45475a !important;
    border-radius: 10px !important;
    color: #cdd6f4 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput input:focus {
    border-color: #cba6f7 !important;
    box-shadow: 0 0 0 2px rgba(203,166,247,0.15) !important;
}

.stButton > button {
    background: #cba6f7 !important;
    color: #1e1e2e !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stButton > button:disabled { opacity: 0.4 !important; cursor: not-allowed !important; }

.stSpinner > div { border-top-color: #cba6f7 !important; }

hr { border-color: #1e1e2e !important; }

.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-online { background: #a6e3a1; box-shadow: 0 0 6px #a6e3a1; }
.status-offline { background: #f38ba8; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# ── Helpers ──────────────────────────────────────────────────────────────────
def check_backend():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False


def send_message(user_message: str):
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if m["role"] in ("user", "assistant")
    ]
    try:
        resp = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": user_message, "history": history},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"reply": "⚠️ Cannot connect to backend. Make sure the FastAPI server is running.", "files": []}
    except requests.exceptions.Timeout:
        return {"reply": "⚠️ Request timed out. Please try again.", "files": []}
    except Exception as e:
        return {"reply": f"⚠️ Error: {str(e)}", "files": []}


def render_file_cards(files: list):
    if not files:
        return
    cards_html = '<div class="file-grid">'
    for f in files:
        name = f.get("name", "Unknown")
        ftype = f.get("type", "File")
        link = f.get("link", "#")
        modified = f.get("modified", "")
        link_html = f'<a class="file-link" href="{link}" target="_blank">🔗 Open in Drive</a>' if link and link != "#" else ""
        modified_html = f'<span>📅 {modified}</span>' if modified else ""
        cards_html += f"""
        <div class="file-card">
            <div class="file-type-badge">{ftype}</div>
            <div class="file-name">{name}</div>
            <div class="file-meta">{modified_html}</div>
            {link_html}
        </div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)


def render_message(msg):
    role = msg["role"]
    content = msg["content"]
    files = msg.get("files", [])
    if role == "user":
        st.markdown(
            f'<div class="msg-user"><div class="msg-label">You</div>{content}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="msg-ai"><div class="msg-label">TailorTalk</div>{content}</div>',
            unsafe_allow_html=True,
        )
        if files:
            render_file_cards(files)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ TailorTalk")
    st.markdown("*Your Google Drive AI assistant*")
    st.markdown("---")

    online = check_backend()
    status_cls = "status-online" if online else "status-offline"
    status_txt = "Backend Online" if online else "Backend Offline"
    st.markdown(
        f'<span class="status-dot {status_cls}"></span>{status_txt}',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### 💡 Example Searches")

    suggestions = [
        "Show me all PDFs",
        "Find files named 'report'",
        "Search for spreadsheets",
        "Find images",
        "Show Google Docs",
        "Find files modified this year",
        "Search for files about budget",
        "Find all presentations",
    ]

    for s in suggestions:
        if st.button(s, key=f"sug_{s}", use_container_width=True, disabled=st.session_state.is_processing):
            st.session_state.pending_suggestion = s

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True, disabled=st.session_state.is_processing):
        st.session_state.messages = []
        st.session_state.is_processing = False
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 Query Tips")
    st.markdown("""
- **By name**: *"find report.pdf"*
- **By type**: *"show me all sheets"*
- **By content**: *"files about revenue"*
- **By date**: *"files from last month"*
- **Combined**: *"PDFs about budget"*
""")

# ── Main Chat Area ────────────────────────────────────────────────────────────
st.markdown('<div class="tt-header">🗂️ TailorTalk</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tt-sub">Conversational Google Drive file discovery — powered by Gemini</div>',
    unsafe_allow_html=True,
)

# Welcome message
if not st.session_state.messages:
    st.markdown("""
    <div class="msg-ai">
        <div class="msg-label">TailorTalk</div>
        👋 Hi! I'm TailorTalk, your Google Drive assistant.<br><br>
        I can help you <strong>search, filter, and discover files</strong> in your Drive. Try asking me things like:<br><br>
        • <em>"Show me all PDF files"</em><br>
        • <em>"Find files named 'budget'"</em><br>
        • <em>"Search for spreadsheets modified this month"</em><br>
        • <em>"Find documents containing 'quarterly report'"</em><br><br>
        What are you looking for today?
    </div>
    """, unsafe_allow_html=True)

# Render all existing messages
for msg in st.session_state.messages:
    render_message(msg)

# ── STEP 1: If locked and last message is user → fire the API call ────────────
if (
    st.session_state.is_processing
    and st.session_state.messages
    and st.session_state.messages[-1]["role"] == "user"
):
    msg_to_send = st.session_state.messages[-1]["content"]

    with st.spinner("🔍 Searching your Drive..."):
        result = send_message(msg_to_send)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["reply"],
        "files": result.get("files", []),
    })

    st.session_state.is_processing = False
    st.rerun()

# ── STEP 2: Show input only when not processing ───────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

if st.session_state.is_processing:
    st.info("⏳ Processing your request — please wait...", icon="🔍")
else:
    col1, col2 = st.columns([5, 1])

    with col1:
        user_input = st.text_input(
            "Message",
            key="user_input",
            placeholder="Ask me to find files... e.g. 'Show all PDFs' or 'Find the budget spreadsheet'",
            label_visibility="collapsed",
        )

    with col2:
        send_clicked = st.button("Send ➤", use_container_width=True)

    # Handle sidebar suggestion click
    if st.session_state.pending_suggestion:
        user_input = st.session_state.pending_suggestion
        st.session_state.pending_suggestion = None
        send_clicked = True

    # Lock + append user message + rerun → triggers STEP 1 above
    if send_clicked and (user_input or "").strip():
        st.session_state.is_processing = True
        st.session_state.messages.append({
            "role": "user",
            "content": user_input.strip(),
        })
        st.rerun()