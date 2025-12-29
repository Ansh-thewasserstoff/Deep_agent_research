import streamlit as st
import asyncio
import uuid
import os
import ast
from dotenv import load_dotenv

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop()  # Do not continue if check_password is not True.

# --- YOUR APP CODE STARTS HERE ---
st.write("👋 Hello! If you can see this, you are logged in.")
# --- Import your actual backend ---
try:
    from modules.core.orchestrator import create_research_system
except ImportError:
    # Fallback Mock
    pass

load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Gemini 3.0 Deep Research",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stStatusWidget { background-color: #1e2329; border: 1px solid #30363d; border-radius: 10px; }
    .stChatMessage { padding: 1rem; border-radius: 0.5rem; }
    .stChatInput { position: fixed; bottom: 3rem; }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "agent" not in st.session_state:
    st.session_state.agent = None
if "current_tier" not in st.session_state:
    st.session_state.current_tier = "free"


# --- THE FIX: HANDLE LIST OBJECTS DIRECTLY ---
def parse_agent_output(raw_content):
    """
    Handles cases where the agent returns a list of dictionaries (objects)
    instead of a simple string.
    """
    # CASE 1: It is already a Python List (The scenario you are facing)
    if isinstance(raw_content, list):
        text_parts = []
        for item in raw_content:
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts)

    # CASE 2: It is a String (Try to parse it if it looks like a list string)
    if isinstance(raw_content, str):
        stripped = raw_content.strip()
        if stripped.startswith("[") and "type" in stripped:
            try:
                # Attempt to turn stringified list back into list
                parsed = ast.literal_eval(stripped)
                if isinstance(parsed, list):
                    return parse_agent_output(parsed)  # Recursive call
            except (ValueError, SyntaxError):
                pass

        return raw_content  # Return plain string if parsing fails

    # Fallback
    return str(raw_content)


# --- Async Agent Interaction ---
async def run_agent_interaction(user_input, tier, thread_id):
    if st.session_state.agent is None or st.session_state.current_tier != tier:
        with st.status(f"🚀 Initializing {tier.upper()} Tier Agent...", expanded=False) as status:
            st.session_state.agent = create_research_system(tier=tier)
            st.session_state.current_tier = tier
            status.update(label=f"Agent Ready ({tier.upper()})", state="complete")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await st.session_state.agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config
        )

        # 1. Get content (which might be a List object)
        raw_content = result["messages"][-1].content

        # 2. Extract clean text
        clean_text = parse_agent_output(raw_content)

        return clean_text

    except Exception as e:
        return f"Error during execution: {str(e)}"


# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_tier = st.selectbox("Research Tier", ["free", "pro", "enterprise"], index=0)
    st.divider()
    st.caption(f"**Thread ID:** `{st.session_state.thread_id}`")
    if st.button("New Research Session", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.agent = None
        st.rerun()

# --- Main Chat Interface ---
st.title("🧠 Gemini 3.0 Deep Research")

# Display History
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🧠"
    with st.chat_message(msg["role"], avatar=avatar):
        # Apply the parser here too, in case history has raw objects
        clean_history = parse_agent_output(msg["content"])

        if msg["role"] == "assistant" and "?" in clean_history and "plan" in clean_history.lower():
            st.warning("⚠️ **Plan Approval Required**")
            st.markdown(clean_history)
        else:
            st.markdown(clean_history)

# Handle Input
if prompt := st.chat_input("Enter your research objective..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧠"):
        status_container = st.status("Thinking & Planning...", expanded=True)
        try:
            # Run Agent
            response_text = asyncio.run(
                run_agent_interaction(prompt, selected_tier, st.session_state.thread_id)
            )

            status_container.update(label="Response Generated", state="complete", expanded=False)

            # Display Logic
            if "?" in response_text and "plan" in response_text.lower():
                st.warning("⚠️ **Plan Approval Required**")
                st.markdown(response_text)
                st.caption("Type 'yes' to proceed or describe changes.")
            else:
                st.markdown(response_text)

            # Save to History
            st.session_state.messages.append({"role": "assistant", "content": response_text})

        except Exception as e:
            status_container.update(label="Error", state="error")
            st.error(f"System Error: {str(e)}")