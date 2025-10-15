#core/ risk.py


# CRISIS_KWS = {"suicide","kill myself","end my life","overdose","die","self-harm","hurt myself"}
# MEANS_KWS  = {"how to","where can I get","most painless","lethal dose"}

# def classify_tier(msg: str) -> int:
#     m = msg.lower()
#     if any(k in m for k in CRISIS_KWS) or ( "kill" in m and "myself" in m ) or any(k in m for k in MEANS_KWS):
#         return 3  # crisis → immediate abstention with resources
#     if "panic" in m or "can’t breathe" in m or "fail my exam" in m:
#         return 2  # heightened anxiety
#     return 1      # normal exam stress


import re
from typing import Tuple, Optional
from openai import OpenAI
import os

# --- Patterns cover euphemisms & indirect phrasing ---
_EUPHEMISMS = [
    r"\bend (?:it|everything|things|my life)\b",
    r"\b(end|stop) living\b",
    r"\b(check|clock|tap) out\b",
    r"\b(off|hurt|harm) myself\b",
    r"\bself[-\s]?harm\b",
    r"\bsuicid(e|al)\b",
    r"\bkill (?:myself|me)\b",
    r"\b(?:take|took) (?:my|their) (?:own )?life\b",
    r"\b(?:not|no longer) want to live\b",
    r"\bcan(?:not|'?t) go on\b",
    r"\boverdose\b",
    r"\bpainless (?:way|method)\b",
    r"\blethal (?:dose|method)\b",
    r"\bjump (?:off|from)\b",
    r"\bcut(?:ting)? (?:myself|me)\b",
    r"\bI might (?:do something|take) (?:stupid|extreme) (?:action|things?)\b",
    r"\bdo something horrible\b",
    r"\bI don'?t care if I live\b",
]

_CRISIS_RE = re.compile("|".join(_EUPHEMISMS), re.IGNORECASE)

# Optional: LLM moderation as a backstop (very low latency)
# If you don't want the extra call, set USE_LLM_MOD = False
USE_LLM_MOD = True
_client: Optional[OpenAI] = None

def _llm_flags_crisis(msg: str) -> bool:
    global _client
    if not USE_LLM_MOD:
        return False
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        mod = _client.moderations.create(
            model="omni-moderation-latest",
            input=msg
        )
        cat = mod.results[0].categories
        # Treat self-harm or violence/self-harm as crisis
        return bool(getattr(cat, "self_harm", False) or getattr(cat, "violence", False))
    except Exception:
        # Fail-safe: don't block on moderation errors; rely on patterns
        return False

def classify_tier(msg: str) -> int:
    """
    Returns risk tier:
    3 = crisis (abstain+resources immediately)
    2 = heightened anxiety
    1 = normal
    """
    m = msg.strip().lower()

    # CRISIS if patterns match OR LLM moderation flags self-harm intent
    if _CRISIS_RE.search(m) or _llm_flags_crisis(msg):
        return 3

    # Heightened anxiety language → Tier 2
    heightened_terms = [
        "panic", "panicking", "overwhelmed", "shaking", "can't breathe",
        "i'm losing my mind", "i am losing my mind", "hopeless", "numb",
        "can't sleep", "cannot sleep", "terrified", "breakdown"
    ]
    if any(t in m for t in heightened_terms):
        return 2

    return 1
