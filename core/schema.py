from pydantic import BaseModel
from typing import List, Optional, Dict

class ChatRequest(BaseModel):
    user_id: str
    message: str

class Citation(BaseModel):
    source_id: str
    url: str

class RiskSignal(BaseModel):
    """Individual risk signal detected in the message"""
    text: str
    pattern: str
    weight: float
    tier: int

class RiskDetails(BaseModel):
    """Detailed risk classification information"""
    signals: List[Dict]
    signal_count: int
    sarcasm_detected: bool
    llm_flagged: bool
    llm_confidence: float
    reasoning: str
    tier_scores: Optional[Dict[int, float]] = None
    alternative_tiers: Optional[Dict] = None

class ToneAnalysis(BaseModel):
    """Tone and emotional cue analysis"""
    empathy_level: int
    cues: List[str]
    template: str
    tone_block: str

class ChatResponse(BaseModel):
    text: str
    citations: List[Citation]
    tier: int
    abstained: bool
    confidence: Optional[float] = None
    risk_details: Optional[RiskDetails] = None
    tone_analysis: Optional[ToneAnalysis] = None  # NEW

# ===================== HITL models =====================
class ReviewListItem(BaseModel):  
    id: int  
    user_id: str  
    created_at: str  
    tier: int  
    abstained: bool  
    user_msg: str  
    model_reply: Optional[str] = None
    citations: Optional[str] = None
    reviewed: bool  
    label: Optional[str] = None
    rating_empathy: Optional[int] = None
    rating_factual: Optional[int] = None
    human_notes: Optional[str] = None
    confidence: Optional[float] = None
    risk_details: Optional[str] = None

class ReviewUpdate(BaseModel):  
    reviewed: Optional[bool] = None
    label: Optional[str] = None
    rating_empathy: Optional[int] = None
    rating_factual: Optional[int] = None
    human_notes: Optional[str] = None