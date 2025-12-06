#core/risk.py
import re
from typing import Tuple, Optional, Dict, List
from openai import OpenAI
import os
from dataclasses import dataclass

@dataclass
class RiskSignal:
    pattern: str
    weight: float
    matched_text: str
    tier: int

# Tier 3: Crisis keywords
CRISIS_PATTERNS = {
    r"\b(?:kill|killing) (?:myself|me)\b": 1.0,
    r"\bsuicid(?:e|al)\b": 1.0,
    r"\bend my life\b": 1.0,
    r"\btake my (?:own )?life\b": 0.95,
    r"\boverdose\b": 0.95,
    r"\bend (?:it all|everything|things)\b": 0.85,
    r"\b(?:check|clock|tap) out\b": 0.80,
    r"\b(?:end|stop) living\b": 0.90,
    r"\b(?:not|no longer|don'?t) want to (?:live|be here|exist)\b": 0.85,
    r"\bcan(?:not|'?t) go on(?: anymore| any longer)?\b": 0.80,
    r"\bself[-\s]?harm(?:ing)?\b": 0.90,
    r"\b(?:cut|cutting|hurt|hurting|harm|harming) (?:myself|me)\b": 0.85,
    r"\bpainless (?:way|method|means)\b": 0.95,
    r"\blethal (?:dose|method|amount)\b": 0.95,
    r"\bhow (?:to|can I) (?:kill|end|overdose)\b": 0.90,
    r"\bjump (?:off|from)\b": 0.75,
    r"\b(?:wish|hope) I (?:was|were) dead\b": 0.80,
    r"\bI don'?t care if I (?:live|die)\b": 0.75,
    r"\bdo something (?:horrible|terrible|stupid|extreme)\b": 0.70,
    r"\bmight (?:hurt|harm) myself\b": 0.80,
}

# Tier 2: Heightened anxiety
HEIGHTENED_PATTERNS = {
    r"\bpanic(?:king|ked| attack)?\b": 0.70,
    r"\b(?:can'?t|cannot) breathe\b": 0.75,
    r"\boverwhelmed\b": 0.60,
    r"\bshaking\b": 0.55,
    r"\blosing my mind\b": 0.65,
    r"\bhopeless(?:ness)?\b": 0.70,
    r"\bnumb\b": 0.60,
    r"\b(?:can'?t|cannot) sleep\b": 0.50,
    r"\bterrified\b": 0.65,
    r"\bbreakdown\b": 0.70,
    r"\bfail(?:ing)? (?:my|the) exam\b": 0.55,
    r"\bextremely anxious\b": 0.65,
    r"\bcompletely stressed\b": 0.55,
}

# Tier 1: Normal anxiety
NORMAL_PATTERNS = {
    r"\banxious\b": 0.40,
    r"\bstressed\b": 0.35,
    r"\bworried\b": 0.35,
    r"\bnervous\b": 0.40,
    r"\bexam\b": 0.30,
    r"\btest\b": 0.30,
    r"\bstudy(?:ing)?\b": 0.35,
}

# Sarcasm detection
NEGATION_PATTERNS = [
    r"\bnot (?:really|actually|seriously)\b",
    r"\bjust kidding\b",
    r"\bjk\b",
    r"\blol\b",
    r"\bhaha\b",
    r"\bjust joking\b",
    r"\bsarcasm\b",
]

USE_LLM_MOD = True
_client: Optional[OpenAI] = None

def _llm_flags_crisis(msg: str) -> Tuple[bool, float]:
    global _client
    if not USE_LLM_MOD:
        return False, 0.0
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        mod = _client.moderations.create(model="omni-moderation-latest", input=msg)
        result = mod.results[0]
        cat = result.categories
        scores = result.category_scores
        is_flagged = bool(getattr(cat, "self_harm", False) or getattr(cat, "violence", False))
        self_harm_score = getattr(scores, "self_harm", 0.0)
        violence_score = getattr(scores, "violence", 0.0)
        llm_confidence = max(self_harm_score, violence_score)
        return is_flagged, llm_confidence
    except Exception:
        return False, 0.0

def detect_sarcasm(msg: str) -> bool:
    m = msg.lower()
    for pattern in NEGATION_PATTERNS:
        if re.search(pattern, m):
            return True
    return False

def extract_signals(msg: str, patterns: Dict[str, float], tier: int) -> List[RiskSignal]:
    signals = []
    m = msg.lower()
    for pattern, weight in patterns.items():
        matches = re.finditer(pattern, m, re.IGNORECASE)
        for match in matches:
            signals.append(RiskSignal(pattern=pattern, weight=weight, 
                                    matched_text=match.group(0), tier=tier))
    return signals

def calculate_tier_scores(tier1_signals: List[RiskSignal], 
                         tier2_signals: List[RiskSignal],
                         tier3_signals: List[RiskSignal],
                         llm_confidence: float,
                         sarcasm_detected: bool) -> Dict[int, float]:
    """
    Calculate scores for each tier.
    Higher score = better match with that tier.
    """
    scores = {1: 0.0, 2: 0.0, 3: 0.0}
    
    # Calculate base scores from signals
    if tier3_signals:
        avg_weight_t3 = sum(s.weight for s in tier3_signals) / len(tier3_signals)
        signal_bonus_t3 = min(0.3, len(tier3_signals) * 0.10)
        scores[3] = avg_weight_t3 + signal_bonus_t3
        scores[3] += llm_confidence * 0.3
    
    if tier2_signals:
        avg_weight_t2 = sum(s.weight for s in tier2_signals) / len(tier2_signals)
        signal_bonus_t2 = min(0.3, len(tier2_signals) * 0.10)
        scores[2] = avg_weight_t2 + signal_bonus_t2
    
    if tier1_signals:
        avg_weight_t1 = sum(s.weight for s in tier1_signals) / len(tier1_signals)
        signal_bonus_t1 = min(0.3, len(tier1_signals) * 0.10)
        scores[1] = avg_weight_t1 + signal_bonus_t1
    
    # SARCASM: If crisis language detected with sarcasm, it's likely Tier 1 (joking)
    if sarcasm_detected and tier3_signals:
        scores[1] = 0.85  # High score for Tier 1 (it's sarcasm)
        scores[3] = 0.05  # Low score for Tier 3 (not serious)
        scores[2] = 0.10  # Low score for Tier 2
    
    # If no signals, default to tier 1 with low score
    if not any([tier1_signals, tier2_signals, tier3_signals]):
        scores[1] = 0.20
    
    # Normalize to 0-1 range
    max_possible = 1.5
    for tier in scores:
        scores[tier] = min(1.0, scores[tier] / max_possible)
    
    return scores

def classify_tier_with_confidence(msg: str) -> Tuple[int, float, Dict]:
    """
    SIMPLIFIED: Confidence = Score of the assigned tier
    
    Returns: (tier, confidence, details)
    
    Confidence interpretation:
    - High score (0.7-1.0) = Strong match with this tier
    - Medium score (0.4-0.7) = Moderate match
    - Low score (0.0-0.4) = Weak match, uncertain
    """
    m = msg.strip().lower()
    
    # Detect sarcasm
    sarcasm_detected = detect_sarcasm(msg)
    
    # Extract signals
    tier3_signals = extract_signals(msg, CRISIS_PATTERNS, tier=3)
    tier2_signals = extract_signals(msg, HEIGHTENED_PATTERNS, tier=2)
    tier1_signals = extract_signals(msg, NORMAL_PATTERNS, tier=1)
    
    # Get LLM signal
    llm_flagged, llm_confidence = _llm_flags_crisis(msg)
    
    # Calculate scores for all tiers
    tier_scores = calculate_tier_scores(
        tier1_signals, tier2_signals, tier3_signals, 
        llm_confidence, sarcasm_detected
    )
    
    # Assign tier based on highest score
    assigned_tier = max(tier_scores, key=tier_scores.get)
    
    # SIMPLE: Confidence = Score of assigned tier
    confidence = tier_scores[assigned_tier]
    
    # Build reasoning
    if tier3_signals and not sarcasm_detected:
        primary_signals = tier3_signals
        reasoning = f"Crisis (Tier 3): {len(tier3_signals)} crisis patterns detected"
        if llm_flagged:
            reasoning += f" + LLM flagged"
    elif tier2_signals and assigned_tier == 2:
        primary_signals = tier2_signals
        reasoning = f"Heightened anxiety (Tier 2): {len(tier2_signals)} distress patterns"
    else:
        # Tier 1
        primary_signals = tier1_signals if tier1_signals else []
        if sarcasm_detected and tier3_signals:
            reasoning = f"Normal (Tier 1): Crisis language detected BUT sarcasm identified"
        else:
            reasoning = f"Normal (Tier 1): {len(tier1_signals)} mild stress patterns"
    
    # Add confidence interpretation
    if confidence >= 0.70:
        conf_label = "HIGH confidence"
    elif confidence >= 0.40:
        conf_label = "MODERATE confidence"
    else:
        conf_label = "LOW confidence"
    
    reasoning += f" | {conf_label} ({confidence:.0%})"
    
    # Build details
    details = {
        "signals": [
            {"text": s.matched_text, "pattern": s.pattern, 
             "weight": s.weight, "tier": s.tier}
            for s in primary_signals
        ],
        "signal_count": len(primary_signals),
        "sarcasm_detected": sarcasm_detected,
        "llm_flagged": llm_flagged,
        "llm_confidence": llm_confidence,
        "reasoning": reasoning,
        "tier_scores": tier_scores,
    }
    
    return assigned_tier, confidence, details

def classify_tier(msg: str) -> int:
    tier, _, _ = classify_tier_with_confidence(msg)
    return tier

def print_classification_report(msg: str):
    tier, confidence, details = classify_tier_with_confidence(msg)
    
    print(f"\n{'='*70}")
    print(f"Message: {msg}")
    print(f"{'='*70}")
    print(f"TIER: {tier} | CONFIDENCE: {confidence:.3f} ({confidence:.0%})")
    print(f"\nTier Scores (Confidence = Score of assigned tier):")
    for t, score in details['tier_scores'].items():
        marker = "← SELECTED" if t == tier else ""
        print(f"  Tier {t}: {score:.3f} ({score:.0%}) {marker}")
    
    print(f"\nReasoning: {details['reasoning']}")
    
    if details['signals']:
        print(f"\nDetected Signals ({details['signal_count']}):")
        for sig in details['signals']:
            print(f"  - '{sig['text']}' (weight: {sig['weight']:.2f})")
    
    if details['sarcasm_detected']:
        print("\n⚠️  Sarcasm detected")
    if details['llm_flagged']:
        print(f"\n⚠️  LLM flagged (conf: {details['llm_confidence']:.3f})")
    
    print(f"\n💡 Interpretation:")
    print(f"   Confidence = Tier {tier} score = {confidence:.0%}")
    if confidence >= 0.70:
        print(f"   ✅ Strong match with Tier {tier}")
    elif confidence >= 0.40:
        print(f"   ⚠️  Moderate match with Tier {tier}")
    else:
        print(f"   ❓ Weak match - check tier_scores for alternatives")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    test_cases = [
        "I want to kill myself",
        "I just want to kill myself lol jk",
        "I am panicking about my exam tomorrow",
        "I'm very stressed about my exam tomorrow",
        "I'm a little worried about my exam",
    ]
    
    for msg in test_cases:
        print_classification_report(msg)