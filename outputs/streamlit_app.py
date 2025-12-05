import streamlit as st
import requests
import json
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Mental Health Copilot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
    }
    .stTextInput > div > div > input {
        font-size: 16px;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #2196F3;
    }
    .assistant-message {
        background-color: #f1f8e9;
        border-left: 5px solid #8BC34A;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 0.5rem;
    }
    .tier-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.875rem;
    }
    .tier-1 { background-color: #4CAF50; color: white; }
    .tier-2 { background-color: #FF9800; color: white; }
    .tier-3 { background-color: #f44336; color: white; }
    </style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = "http://localhost:8000/chat"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit_user"

def get_tier_badge(tier: int) -> str:
    """Generate HTML badge for risk tier"""
    tier_names = {1: "Normal", 2: "Heightened", 3: "Crisis"}
    return f'<span class="tier-badge tier-{tier}">Tier {tier}: {tier_names.get(tier, "Unknown")}</span>'

def get_confidence_color(confidence: float) -> str:
    """Get color based on confidence level"""
    if confidence >= 0.7:
        return "#4CAF50"  # Green
    elif confidence >= 0.4:
        return "#FF9800"  # Orange
    else:
        return "#f44336"  # Red

def display_analysis_sidebar(response_data: Dict[str, Any]):
    """Display detailed analysis in sidebar"""
    with st.sidebar:
        st.markdown("### 📊 Response Analysis")
        
        # Risk Classification
        st.markdown("#### 🎯 Risk Classification")
        tier = response_data.get("tier", 1)
        confidence = response_data.get("confidence", 0)
        
        st.markdown(get_tier_badge(tier), unsafe_allow_html=True)
        st.metric("Confidence", f"{confidence:.1%}")
        
        # Confidence visualization
        st.progress(confidence)
        
        # Tier Scores
        risk_details = response_data.get("risk_details", {})
        if risk_details and "tier_scores" in risk_details:
            st.markdown("#### 📈 Tier Scores")
            tier_scores = risk_details["tier_scores"]
            
            for t in [1, 2, 3]:
                score = tier_scores.get(str(t), tier_scores.get(t, 0))
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"Tier {t}")
                with col2:
                    st.text(f"{score:.1%}")
                st.progress(score)
        
        # Detected Signals
        if risk_details and "signals" in risk_details:
            signals = risk_details["signals"]
            if signals:
                st.markdown("#### 🔍 Detected Signals")
                for sig in signals:
                    with st.expander(f"'{sig['text']}'"):
                        st.text(f"Weight: {sig['weight']:.2f}")
                        st.text(f"Tier: {sig['tier']}")
        
        # Reasoning
        if risk_details and "reasoning" in risk_details:
            st.markdown("#### 💭 Classification Reasoning")
            st.info(risk_details["reasoning"])
        
        # Tone Analysis
        tone_analysis = response_data.get("tone_analysis", {})
        if tone_analysis:
            st.markdown("#### 🎭 Tone Analysis")
            
            empathy = tone_analysis.get("empathy_level", 1)
            st.metric("Empathy Level", f"{empathy}/3")
            
            cues = tone_analysis.get("cues", [])
            if cues:
                st.markdown("**Detected Cues:**")
                for cue in cues:
                    st.markdown(f"- {cue}")
            
            template = tone_analysis.get("template", "generic")
            st.markdown(f"**Template:** `{template}`")
        
        # Safety Flags
        if risk_details:
            st.markdown("#### ⚠️ Safety Checks")
            sarcasm = risk_details.get("sarcasm_detected", False)
            llm_flagged = risk_details.get("llm_flagged", False)
            
            if sarcasm:
                st.warning("🤪 Sarcasm detected")
            if llm_flagged:
                st.error("🚨 LLM moderation flagged")
            if not sarcasm and not llm_flagged:
                st.success("✅ No safety concerns")

def send_message(user_message: str) -> Dict[str, Any]:
    """Send message to API and return response"""
    try:
        response = requests.post(
            API_URL,
            json={
                "user_id": st.session_state.user_id,
                "message": user_message
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {str(e)}")
        return None

def display_message(role: str, content: str, metadata: Dict[str, Any] = None):
    """Display a chat message with optional metadata"""
    message_class = "user-message" if role == "user" else "assistant-message"
    icon = "👤" if role == "user" else "🤖"
    
    with st.container():
        st.markdown(
            f'<div class="chat-message {message_class}">',
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns([1, 20])
        with col1:
            st.markdown(f"### {icon}")
        with col2:
            st.markdown(f"**{role.title()}**")
            
            # Display analysis metrics ABOVE the message for assistant
            if role == "assistant" and metadata and "full_response" in metadata:
                response_data = metadata["full_response"]
                
                # Create metrics row
                metric_cols = st.columns(4)
                
                # Tier
                tier = response_data.get("tier", 1)
                tier_names = {1: "Normal", 2: "Heightened", 3: "Crisis"}
                tier_colors = {1: "#4CAF50", 2: "#FF9800", 3: "#f44336"}
                with metric_cols[0]:
                    st.markdown(
                        f'<div style="background-color: {tier_colors[tier]}; color: white; padding: 0.5rem; '
                        f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
                        f'Tier {tier}: {tier_names[tier]}</div>',
                        unsafe_allow_html=True
                    )
                
                # Confidence
                confidence = response_data.get("confidence", 0)
                conf_color = get_confidence_color(confidence)
                with metric_cols[1]:
                    st.markdown(
                        f'<div style="background-color: {conf_color}; color: white; padding: 0.5rem; '
                        f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
                        f'Confidence: {confidence:.1%}</div>',
                        unsafe_allow_html=True
                    )
                
                # Empathy Level
                tone_analysis = response_data.get("tone_analysis", {})
                empathy = tone_analysis.get("empathy_level", 1)
                with metric_cols[2]:
                    st.markdown(
                        f'<div style="background-color: #9C27B0; color: white; padding: 0.5rem; '
                        f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
                        f'Empathy: {empathy}/3</div>',
                        unsafe_allow_html=True
                    )
                
                # Template
                template = tone_analysis.get("template", "generic")
                with metric_cols[3]:
                    st.markdown(
                        f'<div style="background-color: #2196F3; color: white; padding: 0.5rem; '
                        f'border-radius: 0.5rem; text-align: center; font-weight: bold;">'
                        f'Template: {template}</div>',
                        unsafe_allow_html=True
                    )
                
                # Reasoning and details
                risk_details = response_data.get("risk_details", {})
                if risk_details:
                    with st.expander("📊 View Analysis Details", expanded=False):
                        
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
                            for idx, t in enumerate([1, 2, 3]):
                                score = tier_scores.get(str(t), tier_scores.get(t, 0))
                                with score_cols[idx]:
                                    st.metric(f"Tier {t}", f"{score:.1%}")
                        
                        # Detected Signals
                        signals = risk_details.get("signals", [])
                        if signals:
                            st.markdown("**🔍 Detected Signals:**")
                            for sig in signals:
                                st.markdown(f"- `{sig['text']}` (weight: {sig['weight']:.2f}, tier: {sig['tier']})")
                        
                        # Emotional Cues
                        cues = tone_analysis.get("cues", [])
                        if cues:
                            st.markdown("**🎭 Emotional Cues:**")
                            st.markdown(", ".join(f"`{cue}`" for cue in cues))
                        
                        # Safety Flags
                        sarcasm = risk_details.get("sarcasm_detected", False)
                        llm_flagged = risk_details.get("llm_flagged", False)
                        if sarcasm or llm_flagged:
                            st.markdown("**⚠️ Safety Flags:**")
                            if sarcasm:
                                st.warning("🤪 Sarcasm detected")
                            if llm_flagged:
                                st.error("🚨 LLM moderation flagged")
                
                st.markdown("---")
            
            # Display the actual message
            st.markdown(content)
            
            # Display citations if available
            if metadata and "citations" in metadata:
                citations = metadata["citations"]
                if citations:
                    st.markdown("---")
                    st.markdown("**📚 Sources:**")
                    cols = st.columns(len(citations))
                    for idx, cite in enumerate(citations):
                        with cols[idx]:
                            st.markdown(f"[{cite['source_id']}]({cite['url']})")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Main UI
st.title("🧠 Safe Mental Health Copilot")
st.markdown("*Your AI companion for exam anxiety support*")

# Sidebar - User Settings
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.session_state.user_id = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Your unique identifier for the session"
    )
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # Quick Info
    st.markdown("### ℹ️ About")
    st.info(
        "This copilot provides evidence-based support for exam anxiety. "
        "It uses AI to detect risk levels and provide appropriate guidance."
    )
    
    st.markdown("### 🆘 Crisis Resources")
    st.error("**988 Suicide & Crisis Lifeline**\nCall or text 988 anytime")

# Display chat history
for msg in st.session_state.messages:
    display_message(
        role=msg["role"],
        content=msg["content"],
        metadata=msg.get("metadata")
    )

# Chat input
user_input = st.chat_input("How are you feeling about your exams?")

if user_input:
    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Display user message
    display_message("user", user_input)
    
    # Show loading spinner
    with st.spinner("Thinking..."):
        # Get response from API
        response_data = send_message(user_input)
    
    if response_data:
        # Extract assistant response
        assistant_text = response_data.get("text", "I apologize, but I couldn't generate a response.")
        citations = response_data.get("citations", [])
        
        # Add assistant message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_text,
            "metadata": {
                "citations": citations,
                "full_response": response_data
            }
        })
        
        # Display assistant message
        display_message(
            "assistant",
            assistant_text,
            metadata={"citations": citations}
        )
        
        # Display analysis in sidebar
        display_analysis_sidebar(response_data)
        
        # Rerun to update UI
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Built with ❤️ for students | Always consult professional help for serious concerns"
    "</div>",
    unsafe_allow_html=True
)