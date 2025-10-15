from pydantic import BaseModel
from typing import List, Optional, Dict

class ChatRequest(BaseModel):
    user_id: str
    message: str

class Citation(BaseModel):
    source_id: str
    url: str

class ChatResponse(BaseModel):
    text: str
    citations: List[Citation]
    tier: int               # 1=normal, 2=heightened, 3=crisis
    abstained: bool

# ===================== HITL models =====================  # added by pranav - (HITL review console)
from typing import Literal  

class ReviewListItem(BaseModel):  
    id: int  
    user_id: str  
    created_at: str  
    tier: int  
    abstained: bool  
    user_msg: str  
    model_reply: str | None = None  
    citations: List[Dict] | str | None = None  
    reviewed: bool  
    label: str | None = None  
    rating_empathy: int | None = None  
    rating_factual: int | None = None  
    human_notes: str | None = None  

class ReviewUpdate(BaseModel):  
    reviewed: bool | None = None  
    label: Literal["safe","unsafe","low_empathy","hallucination","other"] | None = None  
    rating_empathy: int | None = None  
    rating_factual: int | None = None  
    human_notes: str | None = None  
