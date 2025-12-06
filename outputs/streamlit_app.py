# import streamlit as st
# import requests
# import json
# from typing import Dict, Any

# # Page configuration
# st.set_page_config(
#     page_title="Mental Health Copilot",
#     page_icon="🧠",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS for better styling
# st.markdown("""
#     <style>
#     .main {
#         background-color: #f5f7fa;
#     }
#     .stTextInput > div > div > input {
#         font-size: 16px;
#     }
#     .chat-message {
#         padding: 0.5rem;
#         border-radius: 0.5rem;
#         margin-bottom: 1rem;
#         display: flex;
#         flex-direction: column;
#     }
#     .metric-card {
#         background-color: white;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         box-shadow: 0 2px 4px rgba(0,0,0,0.1);
#         margin-bottom: 0.5rem;
#     }
#     .tier-badge {
#         display: inline-block;
#         padding: 0.25rem 0.75rem;
#         border-radius: 1rem;
#         font-weight: bold;
#         font-size: 0.875rem;
#     }
#     .tier-1 { background-color: #4CAF50; color: white; }
#     .tier-2 { background-color: #FF9800; color: white; }
#     .tier-3 { background-color: #f44336; color: white; }
#     </style>
# """, unsafe_allow_html=True)

# # API Configuration
# API_URL = "http://localhost:8000"

# # Initialize session state
# if "messages" not in st.session_state:
#     st.session_state.messages = []
# if "user_id" not in st.session_state:
#     st.session_state.user_id = "streamlit_user"
# if "history_loaded" not in st.session_state:
#     st.session_state.history_loaded = False

# # ========================================
# # FIX: LOAD CONVERSATION HISTORY FUNCTION
# # ========================================
# def load_conversation_history(user_id: str):
#     """Load conversation history from backend"""
#     try:
#         response = requests.get(f"{API_URL}/conversation/history/{user_id}")
#         if response.status_code == 200:
#             data = response.json()
#             if data.get("has_history"):
#                 history = data["history"]
                
#                 # Clear current messages
#                 st.session_state.messages = []
                
#                 # Load history into session state
#                 for turn in history:
#                     st.session_state.messages.append({
#                         "role": turn["role"],
#                         "content": turn["message"]
#                     })
                
#                 return len(history)
#         return 0
#     except Exception as e:
#         st.error(f"Error loading history: {e}")
#         return 0


# def get_tier_badge(tier: int) -> str:
#     """Generate HTML badge for risk tier"""
#     tier_names = {1: "Normal", 2: "Heightened", 3: "Crisis"}
#     return f'<span class="tier-badge tier-{tier}">Tier {tier}: {tier_names.get(tier, "Unknown")}</span>'

# def get_confidence_color(confidence: float) -> str:
#     """Get color based on confidence level"""
#     if confidence >= 0.7:
#         return "#4CAF50"  # Green
#     elif confidence >= 0.4:
#         return "#FF9800"  # Orange
#     else:
#         return "#f44336"  # Red

# def display_analysis_sidebar(response_data: Dict[str, Any]):
#     """Display detailed analysis in sidebar"""
#     with st.sidebar:
#         st.markdown("### 📊 Response Analysis")
        
#         # Risk Classification
#         st.markdown("#### 🎯 Risk Classification")
#         tier = response_data.get("tier", 1)
#         confidence = response_data.get("confidence", 0)
        
#         st.markdown(get_tier_badge(tier), unsafe_allow_html=True)
#         st.metric("Confidence", f"{confidence:.1%}")
        
#         # Confidence visualization
#         st.progress(confidence)
        
#         # Tier Scores
#         risk_details = response_data.get("risk_details", {})
#         if risk_details and "tier_scores" in risk_details:
#             st.markdown("#### 📈 Tier Scores")
#             tier_scores = risk_details["tier_scores"]
            
#             for t in [1, 2, 3]:
#                 score = tier_scores.get(str(t), tier_scores.get(t, 0))
#                 col1, col2 = st.columns([3, 1])
#                 with col1:
#                     st.text(f"Tier {t}")
#                 with col2:
#                     st.text(f"{score:.1%}")
#                 st.progress(score)
        
#         # Detected Signals
#         if risk_details and "signals" in risk_details:
#             signals = risk_details["signals"]
#             if signals:
#                 st.markdown("#### 🔍 Detected Signals")
#                 for sig in signals:
#                     with st.expander(f"'{sig['text']}'"):
#                         st.text(f"Weight: {sig['weight']:.2f}")
#                         st.text(f"Tier: {sig['tier']}")
        
#         # Reasoning
#         if risk_details and "reasoning" in risk_details:
#             st.markdown("#### 💭 Classification Reasoning")
#             st.info(risk_details["reasoning"])
        
#         # Tone Analysis
#         tone_analysis = response_data.get("tone_analysis", {})
#         if tone_analysis:
#             st.markdown("#### 🎭 Tone Analysis")
            
#             empathy = tone_analysis.get("empathy_level", 1)
#             st.metric("Empathy Level", f"{empathy}/3")
            
#             cues = tone_analysis.get("cues", [])
#             if cues:
#                 st.markdown("**Detected Cues:**")
#                 for cue in cues:
#                     st.markdown(f"- {cue}")
            
#             template = tone_analysis.get("template", "generic")
#             st.markdown(f"**Template:** `{template}`")
        
#         # Safety Flags
#         if risk_details:
#             st.markdown("#### ⚠️ Safety Checks")
#             sarcasm = risk_details.get("sarcasm_detected", False)
#             llm_flagged = risk_details.get("llm_flagged", False)
            
#             if sarcasm:
#                 st.warning("🤪 Sarcasm detected")
#             if llm_flagged:
#                 st.error("🚨 LLM moderation flagged")
#             if not sarcasm and not llm_flagged:
#                 st.success("✅ No safety concerns")

# def send_message(user_message: str) -> Dict[str, Any]:
#     """Send message to API and return response"""
#     try:
#         response = requests.post(
#             f"{API_URL}/chat",
#             json={
#                 "user_id": st.session_state.user_id,
#                 "message": user_message
#             },
#             timeout=30
#         )
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         st.error(f"Error connecting to API: {str(e)}")
#         return None

# def display_message(role: str, content: str, metadata: Dict[str, Any] = None):
#     """Display a chat message with optional metadata"""
#     message_class = "user-message" if role == "user" else "assistant-message"
#     icon = "👤" if role == "user" else "🤖"
    
#     with st.container():
#         st.markdown(
#             f'<div class="chat-message {message_class}">',
#             unsafe_allow_html=True
#         )
        
#         col1, col2 = st.columns([1, 20])
#         with col1:
#             st.markdown(f"### {icon}")
#         with col2:
#             st.markdown(f"**{role.title()}**")
            
#             # Display analysis metrics ABOVE the message for assistant
#             if role == "assistant" and metadata and "full_response" in metadata:
#                 response_data = metadata["full_response"]
                
#                 # Create metrics row
#                 metric_cols = st.columns(4)
                
#                 # Tier
#                 tier = response_data.get("tier", 1)
#                 tier_names = {1: "Normal", 2: "Heightened", 3: "Crisis"}
#                 tier_colors = {1: "#4CAF50", 2: "#FF9800", 3: "#f44336"}
#                 with metric_cols[0]:
#                     st.markdown(
#                         f'<div style="background-color: {tier_colors[tier]}; color: white; padding: 0.5rem; '
#                         f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
#                         f'Tier {tier}: {tier_names[tier]}</div>',
#                         unsafe_allow_html=True
#                     )
                
#                 # Confidence
#                 confidence = response_data.get("confidence", 0)
#                 conf_color = get_confidence_color(confidence)
#                 with metric_cols[1]:
#                     st.markdown(
#                         f'<div style="background-color: {conf_color}; color: white; padding: 0.5rem; '
#                         f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
#                         f'Confidence: {confidence:.1%}</div>',
#                         unsafe_allow_html=True
#                     )
                
#                 # Empathy Level
#                 tone_analysis = response_data.get("tone_analysis", {})
#                 empathy = tone_analysis.get("empathy_level", 1)
#                 with metric_cols[2]:
#                     st.markdown(
#                         f'<div style="background-color: #9C27B0; color: white; padding: 0.5rem; '
#                         f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
#                         f'Empathy: {empathy}/3</div>',
#                         unsafe_allow_html=True
#                     )
                
#                 # Template
#                 template = tone_analysis.get("template", "generic")
#                 with metric_cols[3]:
#                     st.markdown(
#                         f'<div style="background-color: #2196F3; color: white; padding: 0.5rem; '
#                         f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
#                         f'Template: {template}</div>',
#                         unsafe_allow_html=True
#                     )
                
#                 # Reasoning and details
#                 risk_details = response_data.get("risk_details", {})
#                 if risk_details:
#                     with st.expander("📊 View Analysis Details", expanded=False):
                        
#                         # Reasoning
#                         reasoning = risk_details.get("reasoning", "")
#                         if reasoning:
#                             st.markdown("**💭 Reasoning:**")
#                             st.info(reasoning)
                        
#                         # Tier Scores
#                         tier_scores = risk_details.get("tier_scores", {})
#                         if tier_scores:
#                             st.markdown("**📈 Tier Scores:**")
#                             score_cols = st.columns(3)
#                             for idx, t in enumerate([1, 2, 3]):
#                                 score = tier_scores.get(str(t), tier_scores.get(t, 0))
#                                 with score_cols[idx]:
#                                     st.metric(f"Tier {t}", f"{score:.1%}")
                        
#                         # Detected Signals
#                         signals = risk_details.get("signals", [])
#                         if signals:
#                             st.markdown("**🔍 Detected Signals:**")
#                             for sig in signals:
#                                 st.markdown(f"- `{sig['text']}` (weight: {sig['weight']:.2f}, tier: {sig['tier']})")
                        
#                         # Emotional Cues
#                         cues = tone_analysis.get("cues", [])
#                         if cues:
#                             st.markdown("**🎭 Emotional Cues:**")
#                             st.markdown(", ".join(f"`{cue}`" for cue in cues))
                        
#                         # Safety Flags
#                         sarcasm = risk_details.get("sarcasm_detected", False)
#                         llm_flagged = risk_details.get("llm_flagged", False)
#                         if sarcasm or llm_flagged:
#                             st.markdown("**⚠️ Safety Flags:**")
#                             if sarcasm:
#                                 st.warning("🤪 Sarcasm detected")
#                             if llm_flagged:
#                                 st.error("🚨 LLM moderation flagged")
                
#                 st.markdown("---")
            
#             # Display the actual message
#             st.markdown(content)
            
#             # Display citations if available
#             if metadata and "citations" in metadata:
#                 citations = metadata["citations"]
#                 if citations:
#                     st.markdown("---")
#                     st.markdown("**📚 Sources:**")
#                     cols = st.columns(len(citations))
#                     for idx, cite in enumerate(citations):
#                         with cols[idx]:
#                             st.markdown(f"[{cite['source_id']}]({cite['url']})")
        
#         st.markdown('</div>', unsafe_allow_html=True)

# # Main UI
# st.title("🧠 Safe Mental Health Copilot")
# st.markdown("*Your AI companion for exam anxiety support*")

# # Sidebar - User Settings
# with st.sidebar:
#     st.markdown("### ⚙️ Settings")
    
#     # ========================================
#     # FIX: USER ID INPUT WITH HISTORY LOADING
#     # ========================================
#     new_user_id = st.text_input(
#         "User ID",
#         value=st.session_state.user_id,
#         help="Your unique identifier. Change to load a different conversation."
#     )
    
#     # Check if user ID changed
#     if new_user_id != st.session_state.user_id:
#         st.session_state.user_id = new_user_id
#         st.session_state.history_loaded = False
#         st.session_state.messages = []
#         st.rerun()
    
#     # Load history if not loaded yet
#     if not st.session_state.history_loaded:
#         with st.spinner("Loading conversation history..."):
#             num_loaded = load_conversation_history(st.session_state.user_id)
#             st.session_state.history_loaded = True
            
#             if num_loaded > 0:
#                 st.success(f"✅ Loaded {num_loaded} messages")
#             else:
#                 st.info("📝 New conversation")
    
#     st.markdown("---")
    
#     if st.button("🗑️ Clear Chat History"):
#         st.session_state.messages = []
#         st.session_state.history_loaded = False
#         st.rerun()
    
#     st.markdown("---")
    
#     # Quick Info
#     st.markdown("### ℹ️ About")
#     st.info(
#         "This copilot provides evidence-based support for exam anxiety. "
#         "It uses AI to detect risk levels and provide appropriate guidance."
#     )
    
#     st.markdown("### 🆘 Crisis Resources")
#     st.error("**988 Suicide & Crisis Lifeline**\nCall or text 988 anytime")

# # Display chat history
# for msg in st.session_state.messages:
#     display_message(
#         role=msg["role"],
#         content=msg["content"],
#         metadata=msg.get("metadata")
#     )

# # Chat input
# user_input = st.chat_input("How are you feeling about your exams?")

# if user_input:
#     # Add user message to history
#     st.session_state.messages.append({
#         "role": "user",
#         "content": user_input
#     })
    
#     # Display user message
#     display_message("user", user_input)
    
#     # Show loading spinner
#     with st.spinner("Thinking..."):
#         # Get response from API
#         response_data = send_message(user_input)
    
#     if response_data:
#         # Extract assistant response
#         assistant_text = response_data.get("text", "I apologize, but I couldn't generate a response.")
#         citations = response_data.get("citations", [])
        
#         # Add assistant message to history
#         st.session_state.messages.append({
#             "role": "assistant",
#             "content": assistant_text,
#             "metadata": {
#                 "citations": citations,
#                 "full_response": response_data
#             }
#         })
        
#         # Display assistant message
#         display_message(
#             "assistant",
#             assistant_text,
#             metadata={"citations": citations, "full_response": response_data}
#         )
        
#         # Display analysis in sidebar
#         display_analysis_sidebar(response_data)
        
#         # Rerun to update UI
#         st.rerun()

# # Footer
# st.markdown("---")
# st.markdown(
#     "<div style='text-align: center; color: #666;'>"
#     "Built with ❤️ for students | Always consult professional help for serious concerns"
#     "</div>",
#     unsafe_allow_html=True
# )

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