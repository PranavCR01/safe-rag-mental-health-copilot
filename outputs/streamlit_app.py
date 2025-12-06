#outputs/streamlit_app.py

import streamlit as st
import requests
import json
from typing import Dict, Any

st.set_page_config(
    page_title="Mental Health Copilot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# iMessage-style CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .user-message-container { display: flex; justify-content: flex-end; margin: 1rem 0; }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    .assistant-message-container { display: flex; justify-content: flex-start; margin: 1rem 0; }
    .assistant-message {
        background: #262730;
        color: #e0e0e0;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 18px 4px;
        max-width: 70%;
        word-wrap: break-word;
        border-left: 3px solid #667eea;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stSidebar"] { background: #1a1a2e; }
    </style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit_user"
if "last_loaded_user" not in st.session_state:
    st.session_state.last_loaded_user = None

def load_conversation_history(user_id: str):
    """Load conversation history with metadata from backend"""
    try:
        response = requests.get(f"{API_URL}/conversation/history/{user_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get("has_history"):
                return data["history"], data.get("stats", {})
        return [], {}
    except Exception as e:
        st.error(f"Error loading history: {e}")
        return [], {}

def send_message(user_message: str) -> Dict[str, Any]:
    """Send message to API"""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"user_id": st.session_state.user_id, "message": user_message},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")
        return None

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    current_user_input = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Enter your user ID. Change to switch conversations.",
        key="user_id_input"
    )
    
    user_changed = current_user_input != st.session_state.last_loaded_user
    
    if user_changed:
        st.session_state.user_id = current_user_input
        
        with st.spinner(f"Loading history for '{current_user_input}'..."):
            history, stats = load_conversation_history(current_user_input)
            
            st.session_state.messages = []
            
            # Load history WITH metadata
            if history:
                for turn in history:
                    msg = {
                        "role": turn["role"],
                        "content": turn["message"]
                    }
                    
                    # Include metadata if it exists (for assistant messages)
                    if "metadata" in turn and turn["metadata"]:
                        msg["metadata"] = turn["metadata"]
                    
                    st.session_state.messages.append(msg)
                
                st.success(f"✅ Loaded {len(history)} messages")
                if stats.get('last_conversation'):
                    st.caption(f"Last active: {stats['last_conversation'][:16]}")
            else:
                st.info("📝 New conversation")
            
            st.session_state.last_loaded_user = current_user_input
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_loaded_user = None
        st.rerun()
    
    st.markdown("---")
    
    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
        **Safe Mental Health Copilot**
        
        - 🎯 Risk detection
        - 💬 Evidence-based advice  
        - 🆘 Crisis resources
        - 📚 Study strategies
        """)
    
    st.markdown("### 🆘 Crisis Resources")
    st.error("**988 Suicide & Crisis Lifeline**\nCall or text **988** anytime")

# ========================================
# MAIN CHAT
# ========================================

st.markdown("<h1 style='text-align: center; padding: 1rem 0;'>🧠 Safe Mental Health Copilot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; margin-bottom: 2rem;'>Your AI companion for exam anxiety support</p>", unsafe_allow_html=True)

if len(st.session_state.messages) == 0:
    st.info("👋 **Welcome!** I'm here to help you manage exam anxiety with evidence-based support.")

# Display messages
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(f"""
        <div class="user-message-container">
            <div class="user-message">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown(f"""
        <div class="assistant-message-container">
            <div class="assistant-message">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show analysis if metadata exists
        if "metadata" in message:
            metadata = message["metadata"]
            
            # Extract data (handle both old and new metadata structures)
            tier = metadata.get("tier", 1)
            confidence = metadata.get("confidence", 0)
            
            # Handle tone_analysis
            tone = metadata.get("tone_analysis", {})
            empathy = tone.get("empathy_level", 1)
            template = tone.get("template", "generic")
            
            # Compact display
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            
            tier_names = {1: "Normal", 2: "Heightened", 3: "Crisis"}
            tier_colors = {1: "🟢", 2: "🟠", 3: "🔴"}
            
            with col1:
                st.caption(f"{tier_colors[tier]} Tier {tier}: {tier_names[tier]}")
            with col2:
                st.caption(f"📊 {confidence*100:.0f}%")
            with col3:
                st.caption(f"💜 {empathy}/3")
            with col4:
                st.caption(f"📋 {template}")
            
            # Full analysis
            with st.expander(f"📊 Full Analysis (Message {idx+1})", expanded=False):
                risk_details = metadata.get("risk_details", {})
                
                # Reasoning
                reasoning = risk_details.get("reasoning", "")
                if reasoning:
                    st.markdown("**💭 Reasoning:**")
                    st.info(reasoning)
                
                # Tier Scores
                tier_scores = risk_details.get("tier_scores", {})
                if tier_scores:
                    st.markdown("**📈 Tier Scores:**")
                    score_cols = st.columns(3)
                    for i, t in enumerate([1, 2, 3]):
                        score = tier_scores.get(str(t), tier_scores.get(t, 0))
                        with score_cols[i]:
                            st.metric(f"Tier {t}", f"{score*100:.0f}%")
                
                # Signals
                signals = risk_details.get("signals", [])
                if signals:
                    st.markdown("**🔍 Detected Signals:**")
                    for sig in signals:
                        st.markdown(f"- `{sig.get('text', '')}` (weight: {sig.get('weight', 0):.2f})")
                
                # Cues
                cues = tone.get("cues", [])
                if cues:
                    st.markdown("**🎭 Emotional Cues:**")
                    st.markdown(", ".join(f"`{cue}`" for cue in cues))
            
            # Citations
            citations = metadata.get("citations", [])
            if citations:
                st.markdown("**📚 Sources:**")
                cite_cols = st.columns(min(len(citations), 4))
                for i, cite in enumerate(citations):
                    with cite_cols[i % 4]:
                        st.markdown(f"[{cite.get('source_id', 'Source')}]({cite.get('url', '#')})")
            
            st.markdown("---")

# Chat input
user_input = st.chat_input("How are you feeling about your exams?")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    with st.spinner("💭 Thinking..."):
        response_data = send_message(user_input)
    
    if response_data:
        assistant_text = response_data.get("text", "I apologize, but I couldn't generate a response.")
        
        # Prepare metadata to save in session
        metadata = {
            "tier": response_data.get("tier"),
            "confidence": response_data.get("confidence"),
            "citations": response_data.get("citations", []),
            "tone_analysis": response_data.get("tone_analysis", {}),
            "risk_details": response_data.get("risk_details", {})
        }
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_text,
            "metadata": metadata
        })
        
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem; padding: 1rem;'>
    Remember: This is a support tool, not a replacement for professional care.<br>
    If you're in crisis, call <b style='color: #ef4444;'>988</b> immediately.
</div>
""", unsafe_allow_html=True)